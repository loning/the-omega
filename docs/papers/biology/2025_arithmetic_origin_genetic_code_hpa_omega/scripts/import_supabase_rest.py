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
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from supabase_env import load_env_file
from provenance_tools import infer_analysis_version


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
) -> None:
    if not rows:
        return
    base = _postgrest_base(supabase_url)
    common_headers = _headers_with_key(supabase_key)
    common_headers["Prefer"] = "resolution=merge-duplicates,return=minimal"

    for i in range(0, len(rows), int(batch_size)):
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


def load_recoding_sites(jsonl_path: Path, *, analysis_version: int | None = None) -> tuple[list[dict[str, Any]], int]:
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
    return rows, n


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
    refseq_dataset: str,
    recoding_dataset: str,
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

    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import datasets into Supabase via REST (PostgREST).")
    p.add_argument(
        "--env-file",
        default="supabase.env",
        help="Env file path (relative to project root). Copy from supabase.env.template.",
    )
    p.add_argument("--batch-size", type=int, default=200, help="Rows per request (default: 200).")
    p.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification (use only if your Python cert store is missing).",
    )
    p.add_argument("--no-recoding", action="store_true", help="Skip importing recoding_sites.")
    p.add_argument("--no-refseq", action="store_true", help="Skip importing refseq_stop_context_comp_results.")
    p.add_argument("--no-panel", action="store_true", help="Skip importing corpus_panel_items.")
    p.add_argument("--no-nonstandard", action="store_true", help="Skip importing nonstandard_sequence_tests_items.")
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
        "--panel-summary-json",
        default="data/panel/corpus_panel_summary.json",
        help="Input corpus panel summary JSON path (relative to project root by default).",
    )
    p.add_argument(
        "--nonstandard-seqtests-json",
        default="data/nonstandard_sequence_tests.json",
        help="Input nonstandard sequence tests JSON path (relative to project root by default).",
    )
    p.add_argument("--recoding-dataset", default="ncbi_recoding_genbank", help="Dataset label for analysis_runs.")
    p.add_argument("--refseq-dataset", default="human_refseq_mrna", help="Dataset label for analysis_runs / refseq results.")
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

    recoding_jsonl_path = (root / str(args.recoding_jsonl)).resolve()
    recoding_summary_path = (root / str(args.recoding_summary_json)).resolve()
    refseq_summary_path = (root / str(args.refseq_summary_json)).resolve()
    panel_summary_path = (root / str(args.panel_summary_json)).resolve()
    nonstandard_summary_path = (root / str(args.nonstandard_seqtests_json)).resolve()

    transcriptome_obj: dict[str, Any] | None = None
    recoding_summary_obj: dict[str, Any] | None = None
    panel_obj: dict[str, Any] | None = None
    nonstandard_obj: dict[str, Any] | None = None

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

    # 1) RefSeq comp results (small upsert)
    if not args.no_refseq:
        assert transcriptome_obj is not None
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
        )

    # 2) Recoding sites (JSONL; larger)
    if not args.no_recoding:
        if not recoding_jsonl_path.exists():
            raise SystemExit(f"Missing recoding JSONL: {recoding_jsonl_path}")
        rec_av_hint: int | None = None
        if recoding_summary_obj is not None:
            rec_av_hint = infer_analysis_version(recoding_summary_path, summary_obj=recoding_summary_obj)
        rec_rows, n_rec = load_recoding_sites(recoding_jsonl_path, analysis_version=rec_av_hint)
        if rec_rows:
            upsert_rows(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
                table="recoding_sites",
                rows=rec_rows,
                on_conflict="analysis_version,k,version,pos_start",
                batch_size=int(args.batch_size),
                ssl_context=ssl_context,
            )
        else:
            raise SystemExit(f"No recoding rows found in JSONL (n={n_rec}).")

    # 3) Provenance payloads (2 rows)
    if not args.no_analysis_runs:
        assert transcriptome_obj is not None
        assert recoding_summary_obj is not None
        run_rows = load_analysis_runs(
            transcriptome_summary_path=refseq_summary_path,
            transcriptome_summary_obj=transcriptome_obj,
            recoding_summary_path=recoding_summary_path,
            recoding_summary_obj=recoding_summary_obj,
            panel_summary_path=panel_summary_path if panel_obj is not None else None,
            panel_summary_obj=panel_obj,
            nonstandard_summary_path=nonstandard_summary_path if nonstandard_obj is not None else None,
            nonstandard_summary_obj=nonstandard_obj,
            refseq_dataset=str(args.refseq_dataset),
            recoding_dataset=str(args.recoding_dataset),
        )
        upsert_rows(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            table="analysis_runs",
            rows=run_rows,
            on_conflict="dataset,analysis,analysis_version",
            batch_size=int(args.batch_size),
            ssl_context=ssl_context,
        )

    # 4) Corpus panel items
    if not args.no_panel:
        assert panel_obj is not None
        panel_rows = load_corpus_panel_items(summary_path=panel_summary_path, summary_obj=panel_obj)
        upsert_rows(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            table="corpus_panel_items",
            rows=panel_rows,
            on_conflict="panel,analysis_version,dataset,code_id",
            batch_size=int(args.batch_size),
            ssl_context=ssl_context,
        )

    # 5) Nonstandard sequence tests items
    if not args.no_nonstandard:
        assert nonstandard_obj is not None
        ns_rows = load_nonstandard_sequence_tests_items(summary_path=nonstandard_summary_path, summary_obj=nonstandard_obj)
        upsert_rows(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            table="nonstandard_sequence_tests_items",
            rows=ns_rows,
            on_conflict="panel,analysis_version,dataset,code_id",
            batch_size=int(args.batch_size),
            ssl_context=ssl_context,
        )

    # 6) Quick verification (best-effort counts)
    for t in (
        "recoding_sites",
        "refseq_stop_context_comp_results",
        "corpus_panel_items",
        "nonstandard_sequence_tests_items",
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


