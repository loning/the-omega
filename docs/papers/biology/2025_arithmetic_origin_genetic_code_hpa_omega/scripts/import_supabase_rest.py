# -*- coding: utf-8 -*-
"""
Import paper datasets into a Supabase (cloud) Postgres via PostgREST (REST API).

Standard library only.

Required env vars (loaded from supabase.env by default):
  - SUPABASE_URL
  - SUPABASE_KEY

Optional:
  - DATABASE_URL (not used here; provided for manual psql/driver workflows)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, read_json, write_json_atomic
from progress_tools import Heartbeat
from supabase_env import load_env_file
from provenance_tools import infer_analysis_version


IMPORT_VERSION = 1


def _now_ms() -> int:
    return int(time.time() * 1000)


def _http_json(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    body: object | None = None,
    timeout_s: float = 60.0,
    ssl_context: ssl.SSLContext | None = None,
) -> tuple[int, dict[str, str], object | None]:
    data: bytes | None
    if body is None:
        data = None
    else:
        data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers = dict(headers)
        headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s, context=ssl_context) as resp:
            status = int(getattr(resp, "status", 0) or 0)
            resp_headers = {k: v for k, v in resp.headers.items()}
            raw = resp.read()
    except urllib.error.HTTPError as e:
        status = int(getattr(e, "code", 0) or 0)
        resp_headers = {k: v for k, v in getattr(e, "headers", {}).items()}
        raw = e.read() if hasattr(e, "read") else b""
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error calling Supabase: {e}") from e

    if not raw:
        return status, resp_headers, None

    # Try JSON decode; fallback to text.
    try:
        return status, resp_headers, json.loads(raw.decode("utf-8"))
    except Exception:
        return status, resp_headers, raw.decode("utf-8", errors="replace")


def _retry_sleep_s(attempt: int) -> float:
    # Exponential backoff with cap.
    return min(8.0, 0.5 * (2 ** max(0, attempt - 1)))


def _postgrest_base(url: str) -> str:
    return url.rstrip("/") + "/rest/v1"


def _headers_with_key(key: str) -> dict[str, str]:
    # Supabase expects both headers.
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def upsert_rows(
    *,
    supabase_url: str,
    supabase_key: str,
    table: str,
    rows: list[dict[str, Any]],
    on_conflict: str,
    batch_size: int = 200,
    ssl_context: ssl.SSLContext | None = None,
    heartbeat: Heartbeat | None = None,
) -> None:
    if not rows:
        return
    base = _postgrest_base(supabase_url)
    common_headers = _headers_with_key(supabase_key)
    common_headers["Prefer"] = "resolution=merge-duplicates,return=minimal"

    for i in range(0, len(rows), int(batch_size)):
        if heartbeat is not None:
            heartbeat.maybe(f"{table}: upserting {min(i + int(batch_size), len(rows))}/{len(rows)} rows")
        chunk = rows[i : i + int(batch_size)]
        qs = urllib.parse.urlencode({"on_conflict": on_conflict})
        url = f"{base}/{urllib.parse.quote(table)}?{qs}"

        for attempt in range(1, 8):
            status, _, payload = _http_json(method="POST", url=url, headers=common_headers, body=chunk, ssl_context=ssl_context)
            if status in (200, 201, 204):
                break
            if status in (429, 500, 502, 503, 504):
                time.sleep(_retry_sleep_s(attempt))
                continue
            raise RuntimeError(f"Upsert failed for {table} (status={status}): {payload}")


def count_rows(
    *,
    supabase_url: str,
    supabase_key: str,
    table: str,
    pk: str = "id",
    ssl_context: ssl.SSLContext | None = None,
) -> int | None:
    """
    Best-effort row count using PostgREST Content-Range.
    """
    base = _postgrest_base(supabase_url)
    url = f"{base}/{urllib.parse.quote(table)}?select={urllib.parse.quote(pk)}"
    headers = _headers_with_key(supabase_key)
    headers["Prefer"] = "count=exact"
    headers["Range"] = "0-0"

    status, resp_headers, _ = _http_json(method="GET", url=url, headers=headers, body=None, ssl_context=ssl_context)
    if status not in (200, 206):
        return None
    cr = resp_headers.get("Content-Range") or resp_headers.get("content-range")
    if not cr or "/" not in cr:
        return None
    tail = cr.split("/", 1)[1].strip()
    try:
        return int(tail)
    except Exception:
        return None


def load_recoding_sites(
    jsonl_path: Path, *, analysis_version: int | None = None, heartbeat: Heartbeat | None = None
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    n = 0
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                continue

            # Minimal validation for DB constraints and conflict keys.
            av = obj.get("analysis_version")
            k = obj.get("k")
            ver = obj.get("version")
            pos_start = obj.get("pos_start")
            try:
                av_i = int(av)  # type: ignore[arg-type]
            except Exception as e:
                raise SystemExit(f"Invalid analysis_version at {jsonl_path}:{line_no}") from e
            if av_i <= 0:
                raise SystemExit(f"Invalid analysis_version at {jsonl_path}:{line_no}: {av_i}")
            if analysis_version is not None and int(av_i) != int(analysis_version):
                raise SystemExit(
                    f"Mismatched analysis_version at {jsonl_path}:{line_no}: {av_i} vs expected {int(analysis_version)}"
                )
            try:
                k_i = int(k)  # type: ignore[arg-type]
            except Exception as e:
                raise SystemExit(f"Invalid k at {jsonl_path}:{line_no}") from e
            if k_i <= 0:
                raise SystemExit(f"Invalid k at {jsonl_path}:{line_no}: {k_i}")
            if not isinstance(ver, str) or not ver.strip():
                raise SystemExit(f"Invalid version at {jsonl_path}:{line_no}")
            try:
                int(pos_start)  # type: ignore[arg-type]
            except Exception as e:
                raise SystemExit(f"Invalid pos_start at {jsonl_path}:{line_no}") from e

            rows.append(obj)
            n += 1
            if heartbeat is not None and (line_no % 5000) == 0:
                heartbeat.maybe(f"recoding_sites JSONL: parsed {n} rows")
    return rows, n


def load_boundary_enrichment_results(
    jsonl_path: Path, *, analysis_version: int | None = None, heartbeat: Heartbeat | None = None
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    n = 0
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                continue

            av = obj.get("analysis_version")
            ds = obj.get("dataset")
            lbl = obj.get("label")
            method = obj.get("method")
            try:
                av_i = int(av)  # type: ignore[arg-type]
            except Exception as e:
                raise SystemExit(f"Invalid analysis_version at {jsonl_path}:{line_no}") from e
            if av_i <= 0:
                raise SystemExit(f"Invalid analysis_version at {jsonl_path}:{line_no}: {av_i}")
            if analysis_version is not None and int(av_i) != int(analysis_version):
                raise SystemExit(
                    f"Mismatched analysis_version at {jsonl_path}:{line_no}: {av_i} vs expected {int(analysis_version)}"
                )
            if not isinstance(ds, str) or not ds.strip():
                raise SystemExit(f"Invalid dataset at {jsonl_path}:{line_no}")
            if not isinstance(lbl, str) or not lbl.strip():
                raise SystemExit(f"Invalid label at {jsonl_path}:{line_no}")
            if not isinstance(method, str) or not method.strip():
                raise SystemExit(f"Invalid method at {jsonl_path}:{line_no}")

            rows.append(obj)
            n += 1
            if heartbeat is not None and (line_no % 2000) == 0:
                heartbeat.maybe(f"boundary_enrichment JSONL: parsed {n} rows")
    return rows, n


def load_refseq_stop_context_candidates(
    jsonl_path: Path, *, analysis_version: int | None = None, heartbeat: Heartbeat | None = None
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    n = 0
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                continue

            av = obj.get("analysis_version")
            ds = obj.get("dataset")
            cand_set = obj.get("candidate_set")
            stop_codon = obj.get("stop_codon")
            group_label = obj.get("group_label")
            record_id = obj.get("record_id")
            stop_base = obj.get("stop_base")
            k = obj.get("k")

            try:
                av_i = int(av)  # type: ignore[arg-type]
            except Exception as e:
                raise SystemExit(f"Invalid analysis_version at {jsonl_path}:{line_no}") from e
            if av_i <= 0:
                raise SystemExit(f"Invalid analysis_version at {jsonl_path}:{line_no}: {av_i}")
            if analysis_version is not None and int(av_i) != int(analysis_version):
                raise SystemExit(
                    f"Mismatched analysis_version at {jsonl_path}:{line_no}: {av_i} vs expected {int(analysis_version)}"
                )
            if not isinstance(ds, str) or not ds.strip():
                raise SystemExit(f"Invalid dataset at {jsonl_path}:{line_no}")
            if not isinstance(cand_set, str) or not cand_set.strip():
                raise SystemExit(f"Invalid candidate_set at {jsonl_path}:{line_no}")
            if not isinstance(stop_codon, str) or not stop_codon.strip():
                raise SystemExit(f"Invalid stop_codon at {jsonl_path}:{line_no}")
            if not isinstance(group_label, str) or not group_label.strip():
                raise SystemExit(f"Invalid group_label at {jsonl_path}:{line_no}")
            if not isinstance(record_id, str) or not record_id.strip():
                raise SystemExit(f"Invalid record_id at {jsonl_path}:{line_no}")
            try:
                int(stop_base)  # type: ignore[arg-type]
            except Exception as e:
                raise SystemExit(f"Invalid stop_base at {jsonl_path}:{line_no}") from e
            try:
                k_i = int(k)  # type: ignore[arg-type]
            except Exception as e:
                raise SystemExit(f"Invalid k at {jsonl_path}:{line_no}") from e
            if k_i <= 0:
                raise SystemExit(f"Invalid k at {jsonl_path}:{line_no}: {k_i}")

            rows.append(obj)
            n += 1
            if heartbeat is not None and (line_no % 2000) == 0:
                heartbeat.maybe(f"refseq_stop_context_candidates JSONL: parsed {n} rows")
    return rows, n


def _artifact_digest(path: Path) -> str:
    """
    Stable-ish digest for caching import steps without re-reading large artifacts.
    Prefer cache sidecar meta when present; fallback to sha256 for small files; otherwise file stat.
    """
    mp = cache_meta_path(path)
    if mp.exists():
        try:
            meta = read_json(mp)
        except Exception:
            meta = None
        if isinstance(meta, dict):
            cd = meta.get("cache_digest")
            if isinstance(cd, str) and cd.strip():
                return cd.strip()

    # Fallback: avoid hashing huge JSONL; use file stat.
    try:
        st = path.stat()
        if st.st_size > 64 * 1024 * 1024:
            return f"stat:{int(st.st_size)}:{int(getattr(st, 'st_mtime_ns', int(st.st_mtime * 1e9)))}"
    except Exception:
        pass

    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                b = f.read(1024 * 1024)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()
    except Exception:
        return ""


def _import_cache_file(root: Path, *, table: str) -> Path:
    return root / "data" / "_cache" / "import_supabase_rest" / f"{table}.json"


def load_refseq_comp_results(*, summary_path: Path, summary_obj: dict[str, Any], dataset: str) -> list[dict[str, Any]]:
    analysis_version = infer_analysis_version(summary_path, summary_obj=summary_obj)
    if not analysis_version:
        raise SystemExit(f"Missing analysis_version for transcriptome summary: {summary_path}")
    k = int(summary_obj.get("stop_window", 0) or 0)
    if k <= 0:
        raise SystemExit("Missing stop_window in transcriptome_summary.json")

    comp = summary_obj.get("stop_context_composition") or {}
    if not isinstance(comp, dict) or not comp:
        raise SystemExit("Missing stop_context_composition in transcriptome_summary.json")

    rows: list[dict[str, Any]] = []

    strat = comp.get("stratified") or {}
    if isinstance(strat, dict):
        for scheme, scheme_obj in strat.items():
            if not isinstance(scheme_obj, dict):
                continue
            for window_side in ("before", "after"):
                w0 = scheme_obj.get(window_side) or {}
                if not isinstance(w0, dict):
                    continue
                for pair, r in w0.items():
                    if not isinstance(r, dict):
                        continue
                    rows.append(
                        {
                            "dataset": dataset,
                            "analysis_version": analysis_version,
                            "k": k,
                            "method": "stratified",
                            "scheme": str(scheme),
                            "window_side": str(window_side),
                            "pair": str(pair),
                            "diff": r.get("diff"),
                            "p": r.get("p"),
                            "se": r.get("se"),
                            "z": r.get("z"),
                            "bins_used": r.get("bins_used"),
                            "n": None,
                            "ci_low": None,
                            "ci_high": None,
                        }
                    )

    nn = comp.get("nn_samples") or {}
    if isinstance(nn, dict):
        res = nn.get("results") or {}
        if isinstance(res, dict):
            for window_side in ("before", "after"):
                w0 = res.get(window_side) or {}
                if not isinstance(w0, dict):
                    continue
                for pair, r in w0.items():
                    if not isinstance(r, dict):
                        continue
                    rows.append(
                        {
                            "dataset": dataset,
                            "analysis_version": analysis_version,
                            "k": k,
                            "method": "nn",
                            "scheme": "na",
                            "window_side": str(window_side),
                            "pair": str(pair),
                            "diff": r.get("mean_diff"),
                            "p": r.get("p"),
                            "se": None,
                            "z": None,
                            "bins_used": None,
                            "n": r.get("n"),
                            "ci_low": r.get("ci_low"),
                            "ci_high": r.get("ci_high"),
                        }
                    )

    return rows


def load_corpus_panel_items(*, summary_path: Path, summary_obj: dict[str, Any]) -> list[dict[str, Any]]:
    analysis_version = infer_analysis_version(summary_path, summary_obj=summary_obj)
    if not analysis_version:
        raise SystemExit(f"Missing analysis_version for corpus panel summary: {summary_path}")
    panel = str(summary_obj.get("panel") or "corpus_panel_v1")

    items = summary_obj.get("items") or []
    if not isinstance(items, list):
        items = []

    rows: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        present = bool(it.get("present"))
        summary = it.get("summary") or {}
        if not isinstance(summary, dict):
            summary = {}
        rows.append(
            {
                "panel": panel,
                "analysis_version": analysis_version,
                "dataset": it.get("dataset"),
                "code_id": it.get("code_id"),
                "label": it.get("label"),
                "domain": it.get("domain"),
                "mode": it.get("mode"),
                "present": present,
                "records": summary.get("records") if present else None,
                "records_with_orf": summary.get("records_with_orf") if present else None,
                "coding_tokens": summary.get("coding_tokens") if present else None,
                "boundary_token_count": summary.get("boundary_token_count") if present else None,
                "boundary_rate": summary.get("boundary_rate") if present else None,
                "payload": it,
            }
        )
    return rows


def load_nonstandard_sequence_tests_items(*, summary_path: Path, summary_obj: dict[str, Any]) -> list[dict[str, Any]]:
    analysis_version = infer_analysis_version(summary_path, summary_obj=summary_obj)
    if not analysis_version:
        raise SystemExit(f"Missing analysis_version for nonstandard sequence tests: {summary_path}")
    panel = str(summary_obj.get("panel") or "nonstandard_examples_v1")

    items = summary_obj.get("items") or []
    if not isinstance(items, list):
        items = []

    rows: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        present = bool(it.get("present"))
        tests = it.get("tests") or {}
        if not isinstance(tests, dict):
            tests = {}
        st = tests.get("start_boundary") or {}
        sp = tests.get("stop_boundary") or {}
        if not isinstance(st, dict):
            st = {}
        if not isinstance(sp, dict):
            sp = {}
        rows.append(
            {
                "panel": panel,
                "analysis_version": analysis_version,
                "dataset": it.get("dataset"),
                "code_id": it.get("code_id"),
                "label": it.get("label"),
                "domain": it.get("domain"),
                "present": present,
                "records_seen": it.get("records_seen") if present else None,
                "records_used": it.get("records_used") if present else None,
                "records_invalid": it.get("records_invalid") if present else None,
                "start_boundary_rate": st.get("rate") if present else None,
                "start_boundary_z": st.get("z") if present else None,
                "start_boundary_p": st.get("p_two_sided") if present else None,
                "stop_boundary_rate": sp.get("rate") if present else None,
                "stop_boundary_z": sp.get("z") if present else None,
                "stop_boundary_p": sp.get("p_two_sided") if present else None,
                "payload": it,
            }
        )
    return rows


def load_analysis_runs(
    *,
    transcriptome_summary_path: Path,
    transcriptome_summary_obj: dict[str, Any],
    recoding_summary_path: Path,
    recoding_summary_obj: dict[str, Any],
    panel_summary_path: Path | None = None,
    panel_summary_obj: dict[str, Any] | None = None,
    nonstandard_summary_path: Path | None = None,
    nonstandard_summary_obj: dict[str, Any] | None = None,
    nonstandard_codes_path: Path | None = None,
    nonstandard_codes_obj: dict[str, Any] | None = None,
    refseq_dataset: str,
    recoding_dataset: str,
    nonstandard_codes_dataset: str,
) -> list[dict[str, Any]]:
    ref_av = infer_analysis_version(transcriptome_summary_path, summary_obj=transcriptome_summary_obj)
    if not ref_av:
        raise SystemExit(f"Missing analysis_version for transcriptome summary: {transcriptome_summary_path}")

    rec_av = infer_analysis_version(recoding_summary_path, summary_obj=recoding_summary_obj)
    if not rec_av:
        raise SystemExit(f"Missing analysis_version for recoding summary: {recoding_summary_path}")

    out = [
        {
            "dataset": refseq_dataset,
            "analysis": "transcriptome_summary",
            "analysis_version": ref_av,
            "payload": transcriptome_summary_obj,
        },
        {
            "dataset": recoding_dataset,
            "analysis": "recoding_sites_summary",
            "analysis_version": rec_av,
            "payload": recoding_summary_obj,
        },
    ]

    if panel_summary_path is not None and panel_summary_obj is not None:
        pav = infer_analysis_version(panel_summary_path, summary_obj=panel_summary_obj)
        if not pav:
            raise SystemExit(f"Missing analysis_version for corpus panel summary: {panel_summary_path}")
        panel_name = str(panel_summary_obj.get("panel") or "corpus_panel_v1")
        out.append(
            {
                "dataset": panel_name,
                "analysis": "corpus_panel_summary",
                "analysis_version": pav,
                "payload": panel_summary_obj,
            }
        )

    if nonstandard_summary_path is not None and nonstandard_summary_obj is not None:
        nav = infer_analysis_version(nonstandard_summary_path, summary_obj=nonstandard_summary_obj)
        if not nav:
            raise SystemExit(f"Missing analysis_version for nonstandard sequence tests: {nonstandard_summary_path}")
        panel_name = str(nonstandard_summary_obj.get("panel") or "nonstandard_examples_v1")
        out.append(
            {
                "dataset": panel_name,
                "analysis": "nonstandard_sequence_tests",
                "analysis_version": nav,
                "payload": nonstandard_summary_obj,
            }
        )

    if nonstandard_codes_path is not None and nonstandard_codes_obj is not None:
        cav = infer_analysis_version(nonstandard_codes_path, summary_obj=nonstandard_codes_obj)
        if not cav:
            raise SystemExit(f"Missing analysis_version for nonstandard codes summary: {nonstandard_codes_path}")
        out.append(
            {
                "dataset": str(nonstandard_codes_dataset),
                "analysis": "nonstandard_codes",
                "analysis_version": cav,
                "payload": nonstandard_codes_obj,
            }
        )

    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import datasets into Supabase via REST (PostgREST).")
    p.add_argument(
        "--env-file",
        default="supabase.env",
        help="Env file path (relative to project root). Copy from supabase.env.template.",
    )
    p.add_argument("--batch-size", type=int, default=200, help="Rows per request (default: 200).")
    p.add_argument("--heartbeat-s", type=int, default=60, help="Progress heartbeat interval seconds (0 disables).")
    p.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification (use only if your Python cert store is missing).",
    )
    p.add_argument("--force", action="store_true", help="Force import even if local import cache hits.")
    p.add_argument("--no-recoding", action="store_true", help="Skip importing recoding_sites.")
    p.add_argument("--no-refseq", action="store_true", help="Skip importing refseq_stop_context_comp_results.")
    p.add_argument("--no-refseq-stop-candidates", action="store_true", help="Skip importing refseq_stop_context_candidates.")
    p.add_argument("--no-panel", action="store_true", help="Skip importing corpus_panel_items.")
    p.add_argument("--no-nonstandard", action="store_true", help="Skip importing nonstandard_sequence_tests_items.")
    p.add_argument("--no-boundary-enrichment", action="store_true", help="Skip importing boundary_enrichment_results.")
    p.add_argument("--no-analysis-runs", action="store_true", help="Skip importing analysis_runs payloads.")
    p.add_argument(
        "--recoding-jsonl",
        default="data/recoding_genbank/recoding_sites.jsonl",
        help="Input recoding JSONL path (relative to project root by default).",
    )
    p.add_argument(
        "--recoding-summary-json",
        default="data/recoding_genbank/recoding_sites_summary.json",
        help="Input recoding summary JSON path (relative to project root by default).",
    )
    p.add_argument(
        "--refseq-summary-json",
        default="data/refseq_hsapiens_mrna/transcriptome_summary.json",
        help="Input RefSeq merged transcriptome summary JSON path (relative to project root by default).",
    )
    p.add_argument(
        "--refseq-stop-candidates-jsonl",
        default="data/refseq_hsapiens_mrna/stop_context_candidates.jsonl",
        help="Input RefSeq stop-context candidates JSONL path (relative to project root by default).",
    )
    p.add_argument(
        "--panel-summary-json",
        default="data/panel/corpus_panel_summary.json",
        help="Input corpus panel summary JSON path (relative to project root by default).",
    )
    p.add_argument(
        "--nonstandard-seqtests-json",
        default="data/nonstandard_sequence_tests.json",
        help="Input nonstandard sequence tests JSON path (relative to project root by default).",
    )
    p.add_argument(
        "--nonstandard-codes-json",
        default="data/nonstandard_codes_summary.json",
        help="Input nonstandard codes summary JSON path (relative to project root by default).",
    )
    p.add_argument(
        "--boundary-enrichment-jsonl",
        default="data/boundary_enrichment/boundary_enrichment_results.jsonl",
        help="Input boundary enrichment results JSONL path (relative to project root by default).",
    )
    p.add_argument("--recoding-dataset", default="ncbi_recoding_genbank", help="Dataset label for analysis_runs.")
    p.add_argument("--refseq-dataset", default="human_refseq_mrna", help="Dataset label for analysis_runs / refseq results.")
    p.add_argument("--nonstandard-codes-dataset", default="ncbi_gc_prt", help="Dataset label for analysis_runs (nonstandard codes).")
    return p.parse_args()


def _read_json_dict(path: Path, *, label: str) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"Failed to read {label}: {path}") from e
    if not isinstance(obj, dict):
        raise SystemExit(f"Malformed {label}: {path}")
    return obj


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent.parent
    env_path = (root / str(args.env_file)).resolve()
    if not env_path.exists():
        raise SystemExit(f"Missing env file: {env_path} (copy from supabase.env.template)")

    env = load_env_file(env_path)
    supabase_url = (env.get("SUPABASE_URL") or "").strip()
    supabase_key = (env.get("SUPABASE_KEY") or "").strip()
    if not supabase_url:
        raise SystemExit("Missing SUPABASE_URL in env file.")
    if not supabase_key:
        raise SystemExit("Missing SUPABASE_KEY in env file.")

    ssl_context: ssl.SSLContext | None
    if args.insecure:
        ssl_context = ssl._create_unverified_context()  # noqa: SLF001
    else:
        ssl_context = None

    hb = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress]")

    recoding_jsonl_path = (root / str(args.recoding_jsonl)).resolve()
    recoding_summary_path = (root / str(args.recoding_summary_json)).resolve()
    refseq_summary_path = (root / str(args.refseq_summary_json)).resolve()
    refseq_candidates_jsonl_path = (root / str(args.refseq_stop_candidates_jsonl)).resolve()
    panel_summary_path = (root / str(args.panel_summary_json)).resolve()
    nonstandard_summary_path = (root / str(args.nonstandard_seqtests_json)).resolve()
    nonstandard_codes_path = (root / str(args.nonstandard_codes_json)).resolve()
    boundary_enrichment_jsonl_path = (root / str(args.boundary_enrichment_jsonl)).resolve()

    transcriptome_obj: dict[str, Any] | None = None
    recoding_summary_obj: dict[str, Any] | None = None
    panel_obj: dict[str, Any] | None = None
    nonstandard_obj: dict[str, Any] | None = None
    nonstandard_codes_obj: dict[str, Any] | None = None

    if (not args.no_refseq) or (not args.no_analysis_runs):
        if not refseq_summary_path.exists():
            raise SystemExit(f"Missing RefSeq transcriptome summary JSON: {refseq_summary_path}")
        transcriptome_obj = _read_json_dict(refseq_summary_path, label="transcriptome_summary.json")

    if (not args.no_analysis_runs) or (not args.no_recoding):
        if recoding_summary_path.exists():
            recoding_summary_obj = _read_json_dict(recoding_summary_path, label="recoding_sites_summary.json")
        elif not args.no_analysis_runs:
            raise SystemExit(f"Missing recoding summary JSON: {recoding_summary_path}")

    if (not args.no_panel) or (not args.no_analysis_runs):
        if panel_summary_path.exists():
            panel_obj = _read_json_dict(panel_summary_path, label="corpus_panel_summary.json")
        elif not args.no_panel:
            raise SystemExit(f"Missing corpus panel summary JSON: {panel_summary_path}")

    if (not args.no_nonstandard) or (not args.no_analysis_runs):
        if nonstandard_summary_path.exists():
            nonstandard_obj = _read_json_dict(nonstandard_summary_path, label="nonstandard_sequence_tests.json")
        elif not args.no_nonstandard:
            raise SystemExit(f"Missing nonstandard sequence tests JSON: {nonstandard_summary_path}")

    if not args.no_analysis_runs:
        if nonstandard_codes_path.exists():
            nonstandard_codes_obj = _read_json_dict(nonstandard_codes_path, label="nonstandard_codes_summary.json")

    # 1) RefSeq comp results (small upsert)
    if not args.no_refseq:
        assert transcriptome_obj is not None
        cache_file = _import_cache_file(root, table="refseq_stop_context_comp_results")
        ref_cache_key = {
            "analysis": "import_supabase_rest",
            "import_version": int(IMPORT_VERSION),
            "table": "refseq_stop_context_comp_results",
            "supabase_url": supabase_url,
            "refseq_dataset": str(args.refseq_dataset),
            "refseq_summary_digest": _artifact_digest(refseq_summary_path),
        }
        ref_cache_meta = {"cache_key": ref_cache_key, "cache_digest": cache_key_digest(ref_cache_key)}
        if (not args.force) and cache_hit(cache_file, expected_meta=ref_cache_meta, require_meta=True):
            print(f"[cache] hit: {cache_file}")
        else:
            ref_rows = load_refseq_comp_results(
                summary_path=refseq_summary_path,
                summary_obj=transcriptome_obj,
                dataset=str(args.refseq_dataset),
            )
            upsert_rows(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                table="refseq_stop_context_comp_results",
                rows=ref_rows,
                on_conflict="dataset,k,method,scheme,window_side,pair",
                batch_size=int(args.batch_size),
                ssl_context=ssl_context,
                heartbeat=hb,
            )
            write_json_atomic(cache_file, {"ok": True})
            write_json_atomic(cache_meta_path(cache_file), ref_cache_meta)

    # 1b) RefSeq stop-context candidates (JSONL; small)
    if not args.no_refseq_stop_candidates:
        if not refseq_candidates_jsonl_path.exists():
            print(f"[skip] refseq_stop_context_candidates: missing {refseq_candidates_jsonl_path}")
        else:
            cache_file = _import_cache_file(root, table="refseq_stop_context_candidates")
            cand_cache_key = {
                "analysis": "import_supabase_rest",
                "import_version": int(IMPORT_VERSION),
                "table": "refseq_stop_context_candidates",
                "supabase_url": supabase_url,
                "candidates_digest": _artifact_digest(refseq_candidates_jsonl_path),
            }
            cand_cache_meta = {"cache_key": cand_cache_key, "cache_digest": cache_key_digest(cand_cache_key)}
            if (not args.force) and cache_hit(cache_file, expected_meta=cand_cache_meta, require_meta=True):
                print(f"[cache] hit: {cache_file}")
            else:
                cand_rows, n_cand = load_refseq_stop_context_candidates(refseq_candidates_jsonl_path, heartbeat=hb)
                if cand_rows:
                    upsert_rows(
                        supabase_url=supabase_url,
                        supabase_key=supabase_key,
                        table="refseq_stop_context_candidates",
                        rows=cand_rows,
                        on_conflict="dataset,analysis_version,candidate_set,k,stop_codon,group_label,record_id,stop_base",
                        batch_size=int(args.batch_size),
                        ssl_context=ssl_context,
                        heartbeat=hb,
                    )
                    write_json_atomic(cache_file, {"ok": True, "rows": int(len(cand_rows))})
                    write_json_atomic(cache_meta_path(cache_file), cand_cache_meta)
                else:
                    raise SystemExit(f"No refseq stop-context candidates rows found in JSONL (n={n_cand}).")

    # 2) Recoding sites (JSONL; larger)
    if not args.no_recoding:
        if not recoding_jsonl_path.exists():
            raise SystemExit(f"Missing recoding JSONL: {recoding_jsonl_path}")
        cache_file = _import_cache_file(root, table="recoding_sites")
        rec_av_hint: int | None = None
        if recoding_summary_obj is not None:
            rec_av_hint = infer_analysis_version(recoding_summary_path, summary_obj=recoding_summary_obj)
        rec_cache_key = {
            "analysis": "import_supabase_rest",
            "import_version": int(IMPORT_VERSION),
            "table": "recoding_sites",
            "supabase_url": supabase_url,
            "recoding_summary_digest": _artifact_digest(recoding_summary_path),
            "recoding_jsonl_stat": {
                "bytes": int(recoding_jsonl_path.stat().st_size),
                "mtime_ns": int(getattr(recoding_jsonl_path.stat(), "st_mtime_ns", int(recoding_jsonl_path.stat().st_mtime * 1e9))),
            },
            "analysis_version_hint": int(rec_av_hint) if rec_av_hint is not None else None,
        }
        rec_cache_meta = {"cache_key": rec_cache_key, "cache_digest": cache_key_digest(rec_cache_key)}
        if (not args.force) and cache_hit(cache_file, expected_meta=rec_cache_meta, require_meta=True):
            print(f"[cache] hit: {cache_file}")
        else:
            hb.force("Loading recoding JSONL (may take a while)...")
            rec_rows, n_rec = load_recoding_sites(recoding_jsonl_path, analysis_version=rec_av_hint, heartbeat=hb)
            if rec_rows:
                upsert_rows(
                    supabase_url=supabase_url,
                    supabase_key=supabase_key,
                    table="recoding_sites",
                    rows=rec_rows,
                    on_conflict="analysis_version,k,version,pos_start",
                    batch_size=int(args.batch_size),
                    ssl_context=ssl_context,
                    heartbeat=hb,
                )
                write_json_atomic(cache_file, {"ok": True, "rows": int(len(rec_rows))})
                write_json_atomic(cache_meta_path(cache_file), rec_cache_meta)
            else:
                raise SystemExit(f"No recoding rows found in JSONL (n={n_rec}).")

    # 3) Provenance payloads (2 rows)
    if not args.no_analysis_runs:
        assert transcriptome_obj is not None
        assert recoding_summary_obj is not None
        cache_file = _import_cache_file(root, table="analysis_runs")
        runs_cache_key = {
            "analysis": "import_supabase_rest",
            "import_version": int(IMPORT_VERSION),
            "table": "analysis_runs",
            "supabase_url": supabase_url,
            "refseq_summary_digest": _artifact_digest(refseq_summary_path),
            "recoding_summary_digest": _artifact_digest(recoding_summary_path),
            "panel_summary_digest": _artifact_digest(panel_summary_path) if panel_obj is not None else None,
            "nonstandard_summary_digest": _artifact_digest(nonstandard_summary_path) if nonstandard_obj is not None else None,
            "nonstandard_codes_digest": _artifact_digest(nonstandard_codes_path) if nonstandard_codes_obj is not None else None,
            "refseq_dataset": str(args.refseq_dataset),
            "recoding_dataset": str(args.recoding_dataset),
            "nonstandard_codes_dataset": str(args.nonstandard_codes_dataset),
        }
        runs_cache_meta = {"cache_key": runs_cache_key, "cache_digest": cache_key_digest(runs_cache_key)}
        if (not args.force) and cache_hit(cache_file, expected_meta=runs_cache_meta, require_meta=True):
            print(f"[cache] hit: {cache_file}")
        else:
            run_rows = load_analysis_runs(
                transcriptome_summary_path=refseq_summary_path,
                transcriptome_summary_obj=transcriptome_obj,
                recoding_summary_path=recoding_summary_path,
                recoding_summary_obj=recoding_summary_obj,
                panel_summary_path=panel_summary_path if panel_obj is not None else None,
                panel_summary_obj=panel_obj,
                nonstandard_summary_path=nonstandard_summary_path if nonstandard_obj is not None else None,
                nonstandard_summary_obj=nonstandard_obj,
                nonstandard_codes_path=nonstandard_codes_path if nonstandard_codes_obj is not None else None,
                nonstandard_codes_obj=nonstandard_codes_obj,
                refseq_dataset=str(args.refseq_dataset),
                recoding_dataset=str(args.recoding_dataset),
                nonstandard_codes_dataset=str(args.nonstandard_codes_dataset),
            )
            upsert_rows(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                table="analysis_runs",
                rows=run_rows,
                on_conflict="dataset,analysis,analysis_version",
                batch_size=int(args.batch_size),
                ssl_context=ssl_context,
                heartbeat=hb,
            )
            write_json_atomic(cache_file, {"ok": True, "rows": int(len(run_rows))})
            write_json_atomic(cache_meta_path(cache_file), runs_cache_meta)

    # 4) Corpus panel items
    if not args.no_panel:
        assert panel_obj is not None
        cache_file = _import_cache_file(root, table="corpus_panel_items")
        panel_cache_key = {
            "analysis": "import_supabase_rest",
            "import_version": int(IMPORT_VERSION),
            "table": "corpus_panel_items",
            "supabase_url": supabase_url,
            "panel_summary_digest": _artifact_digest(panel_summary_path),
        }
        panel_cache_meta = {"cache_key": panel_cache_key, "cache_digest": cache_key_digest(panel_cache_key)}
        if (not args.force) and cache_hit(cache_file, expected_meta=panel_cache_meta, require_meta=True):
            print(f"[cache] hit: {cache_file}")
        else:
            panel_rows = load_corpus_panel_items(summary_path=panel_summary_path, summary_obj=panel_obj)
            upsert_rows(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                table="corpus_panel_items",
                rows=panel_rows,
                on_conflict="panel,analysis_version,dataset,code_id",
                batch_size=int(args.batch_size),
                ssl_context=ssl_context,
                heartbeat=hb,
            )
            write_json_atomic(cache_file, {"ok": True, "rows": int(len(panel_rows))})
            write_json_atomic(cache_meta_path(cache_file), panel_cache_meta)

    # 5) Nonstandard sequence tests items
    if not args.no_nonstandard:
        assert nonstandard_obj is not None
        cache_file = _import_cache_file(root, table="nonstandard_sequence_tests_items")
        ns_cache_key = {
            "analysis": "import_supabase_rest",
            "import_version": int(IMPORT_VERSION),
            "table": "nonstandard_sequence_tests_items",
            "supabase_url": supabase_url,
            "nonstandard_seqtests_digest": _artifact_digest(nonstandard_summary_path),
        }
        ns_cache_meta = {"cache_key": ns_cache_key, "cache_digest": cache_key_digest(ns_cache_key)}
        if (not args.force) and cache_hit(cache_file, expected_meta=ns_cache_meta, require_meta=True):
            print(f"[cache] hit: {cache_file}")
        else:
            ns_rows = load_nonstandard_sequence_tests_items(summary_path=nonstandard_summary_path, summary_obj=nonstandard_obj)
            upsert_rows(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                table="nonstandard_sequence_tests_items",
                rows=ns_rows,
                on_conflict="panel,analysis_version,dataset,code_id",
                batch_size=int(args.batch_size),
                ssl_context=ssl_context,
                heartbeat=hb,
            )
            write_json_atomic(cache_file, {"ok": True, "rows": int(len(ns_rows))})
            write_json_atomic(cache_meta_path(cache_file), ns_cache_meta)

    # 6) Boundary enrichment results (JSONL; small)
    if not args.no_boundary_enrichment:
        if not boundary_enrichment_jsonl_path.exists():
            print(f"[skip] boundary_enrichment_results: missing {boundary_enrichment_jsonl_path}")
        else:
            cache_file = _import_cache_file(root, table="boundary_enrichment_results")
            be_cache_key = {
                "analysis": "import_supabase_rest",
                "import_version": int(IMPORT_VERSION),
                "table": "boundary_enrichment_results",
                "supabase_url": supabase_url,
                "boundary_enrichment_digest": _artifact_digest(boundary_enrichment_jsonl_path),
            }
            be_cache_meta = {"cache_key": be_cache_key, "cache_digest": cache_key_digest(be_cache_key)}
            if (not args.force) and cache_hit(cache_file, expected_meta=be_cache_meta, require_meta=True):
                print(f"[cache] hit: {cache_file}")
            else:
                be_rows, n_be = load_boundary_enrichment_results(boundary_enrichment_jsonl_path, heartbeat=hb)
                if be_rows:
                    upsert_rows(
                        supabase_url=supabase_url,
                        supabase_key=supabase_key,
                        table="boundary_enrichment_results",
                        rows=be_rows,
                        on_conflict="dataset,analysis_version,label,method",
                        batch_size=int(args.batch_size),
                        ssl_context=ssl_context,
                        heartbeat=hb,
                    )
                    write_json_atomic(cache_file, {"ok": True, "rows": int(len(be_rows))})
                    write_json_atomic(cache_meta_path(cache_file), be_cache_meta)
                else:
                    raise SystemExit(f"No boundary enrichment rows found in JSONL (n={n_be}).")

    # 6) Quick verification (best-effort counts)
    for t in (
        "recoding_sites",
        "refseq_stop_context_comp_results",
        "refseq_stop_context_candidates",
        "corpus_panel_items",
        "nonstandard_sequence_tests_items",
        "boundary_enrichment_results",
        "analysis_runs",
    ):
        pk = "run_id" if t == "analysis_runs" else "id"
        n = count_rows(supabase_url=supabase_url, supabase_key=supabase_key, table=t, pk=pk, ssl_context=ssl_context)
        if n is not None:
            print(f"{t}: {n}")
        else:
            print(f"{t}: (count unavailable)")


if __name__ == "__main__":
    main()


