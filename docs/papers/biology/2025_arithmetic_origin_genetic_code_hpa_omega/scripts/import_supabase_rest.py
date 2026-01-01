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


def load_recoding_sites(jsonl_path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    n = 0
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            continue
        rows.append(obj)
        n += 1
    return rows, n


def load_refseq_comp_results(summary_json: Path) -> list[dict[str, Any]]:
    obj = json.loads(summary_json.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit("Malformed transcriptome_summary.json")
    dataset = "human_refseq_mrna"
    analysis_version = int(obj.get("analysis_version", 0) or 0)
    if analysis_version <= 0:
        # Back-compat: older merged summaries did not carry analysis_version.
        analysis_version = int(obj.get("schema_version", 0) or 0)
    if analysis_version <= 0:
        raise SystemExit("Missing analysis_version/schema_version in transcriptome_summary.json")
    k = int(obj.get("stop_window", 0) or 0)
    if k <= 0:
        raise SystemExit("Missing stop_window in transcriptome_summary.json")

    comp = obj.get("stop_context_composition") or {}
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


def load_analysis_runs(
    *,
    transcriptome_summary_path: Path,
    recoding_summary_path: Path,
) -> list[dict[str, Any]]:
    ref_obj = json.loads(transcriptome_summary_path.read_text(encoding="utf-8"))
    if not isinstance(ref_obj, dict):
        raise SystemExit("Malformed transcriptome_summary.json")
    rec_obj = json.loads(recoding_summary_path.read_text(encoding="utf-8"))
    if not isinstance(rec_obj, dict):
        raise SystemExit("Malformed recoding_sites_summary.json")

    ref_av = int(ref_obj.get("analysis_version", 0) or 0)
    if ref_av <= 0:
        ref_av = int(ref_obj.get("schema_version", 0) or 0)
    if ref_av <= 0:
        raise SystemExit("Missing analysis_version/schema_version in transcriptome_summary.json")

    return [
        {
            "dataset": "human_refseq_mrna",
            "analysis": "transcriptome_summary",
            "analysis_version": ref_av,
            "payload": ref_obj,
        },
        {
            "dataset": "ncbi_recoding_genbank",
            "analysis": "recoding_sites_summary",
            "analysis_version": int(rec_obj.get("analysis_version", 0) or 0),
            "payload": rec_obj,
        },
    ]


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
    p.add_argument("--no-analysis-runs", action="store_true", help="Skip importing analysis_runs payloads.")
    return p.parse_args()


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

    # 1) RefSeq comp results (small upsert)
    if not args.no_refseq:
        ref_rows = load_refseq_comp_results(root / "data" / "refseq_hsapiens_mrna" / "transcriptome_summary.json")
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
        rec_rows, n_rec = load_recoding_sites(root / "data" / "recoding_genbank" / "recoding_sites.jsonl")
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
        run_rows = load_analysis_runs(
            transcriptome_summary_path=root / "data" / "refseq_hsapiens_mrna" / "transcriptome_summary.json",
            recoding_summary_path=root / "data" / "recoding_genbank" / "recoding_sites_summary.json",
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

    # 4) Quick verification (best-effort counts)
    for t in ("recoding_sites", "refseq_stop_context_comp_results", "analysis_runs"):
        pk = "run_id" if t == "analysis_runs" else "id"
        n = count_rows(supabase_url=supabase_url, supabase_key=supabase_key, table=t, pk=pk, ssl_context=ssl_context)
        if n is not None:
            print(f"{t}: {n}")
        else:
            print(f"{t}: (count unavailable)")


if __name__ == "__main__":
    main()


