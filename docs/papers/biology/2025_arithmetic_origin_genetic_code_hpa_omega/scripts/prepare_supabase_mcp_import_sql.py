# -*- coding: utf-8 -*-
"""
Prepare chunked SQL files for importing paper datasets into a remote Supabase Postgres
via the Supabase MCP "execute_sql" tool (no Docker / no psql required).

This script does NOT connect to the database; it only writes .sql files that you can
feed to MCP in order.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _json_dumps(x: object) -> str:
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"), sort_keys=False)


def _as_int(v: str) -> int | None:
    v = v.strip()
    if not v:
        return None
    return int(v)


def _as_float(v: str) -> float | None:
    v = v.strip()
    if not v:
        return None
    # Accept scientific notation.
    return float(v)


def _as_bool(v: str) -> bool | None:
    v = v.strip()
    if not v:
        return None
    if v in ("t", "true", "True", "1"):
        return True
    if v in ("f", "false", "False", "0"):
        return False
    raise ValueError(f"Invalid boolean cell: {v!r}")


def _as_json(v: str) -> Any | None:
    v = v.strip()
    if not v:
        return None
    return json.loads(v)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise SystemExit(f"Empty CSV or missing header: {path}")
        out: list[dict[str, str]] = []
        for row in r:
            out.append({k: (row.get(k) or "") for k in r.fieldnames})
        return out


def _chunk(xs: list[dict[str, Any]], n: int) -> list[list[dict[str, Any]]]:
    return [xs[i : i + n] for i in range(0, len(xs), n)]


def _write_sql(path: Path, sql: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(sql, encoding="utf-8")


def _prep_refseq_rows(csv_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    float_cols = {"diff", "p", "se", "z", "ci_low", "ci_high"}
    int_cols = {"analysis_version", "k", "bins_used", "n"}
    text_cols = {"dataset", "method", "scheme", "window_side", "pair"}

    out: list[dict[str, Any]] = []
    for r in csv_rows:
        row: dict[str, Any] = {}
        for c in text_cols:
            v = (r.get(c) or "").strip()
            row[c] = v if v else None
        for c in int_cols:
            row[c] = _as_int(r.get(c, ""))
        for c in float_cols:
            row[c] = _as_float(r.get(c, ""))
        # Normalize scheme for safety (should already be non-empty after export).
        if not row.get("scheme"):
            row["scheme"] = "na"
        out.append(row)
    return out


def _prep_recoding_rows(csv_rows: list[dict[str, str]], *, analysis_version: int) -> list[dict[str, Any]]:
    int_cols = {
        "analysis_version",
        "k",
        "cds_start",
        "cds_end",
        "cds_strand",
        "translation_start",
        "pos_start",
        "pos_end",
        "n",
        "v",
        "delta",
    }
    float_cols = {
        "before_mean_delta",
        "after_mean_delta",
        "terminal_before_mean_delta",
        "terminal_after_mean_delta",
        "control_same_codon_before_mean_delta",
        "control_same_codon_after_mean_delta",
        "control_random_cds_before_mean_delta",
        "control_random_cds_after_mean_delta",
        "before_gc",
        "after_gc",
        "before_cpg",
        "after_cpg",
        "before_ta",
        "after_ta",
        "terminal_before_gc",
        "terminal_after_gc",
        "terminal_before_cpg",
        "terminal_after_cpg",
        "terminal_before_ta",
        "terminal_after_ta",
        "nn_ctrl_before_mean_delta",
        "nn_ctrl_after_mean_delta",
        "nn_before_diff",
        "nn_after_diff",
        "nn_before_l1",
        "nn_after_l1",
        "nn_before_gc_diff",
        "nn_after_gc_diff",
        "nn_before_gc_eps",
        "nn_after_gc_eps",
    }
    bool_cols = {"is_boundary"}
    json_cols = {"before_dinuc", "after_dinuc", "terminal_before_dinuc", "terminal_after_dinuc"}

    # Text columns are everything else in the CSV header (excluding id/inserted_at which are not present).
    header_cols = list(csv_rows[0].keys()) if csv_rows else []
    text_cols = [c for c in header_cols if c not in int_cols | float_cols | bool_cols | json_cols]

    out: list[dict[str, Any]] = []
    for r in csv_rows:
        row: dict[str, Any] = {}
        # Force non-null analysis_version (DB enforces NOT NULL).
        row["analysis_version"] = analysis_version

        for c in text_cols:
            v = (r.get(c) or "").strip()
            row[c] = v if v else None
        for c in int_cols:
            if c == "analysis_version":
                continue
            row[c] = _as_int(r.get(c, ""))
        for c in float_cols:
            row[c] = _as_float(r.get(c, ""))
        for c in bool_cols:
            row[c] = _as_bool(r.get(c, ""))
        for c in json_cols:
            row[c] = _as_json(r.get(c, ""))

        out.append(row)
    return out


def _sql_insert_refseq(rows: list[dict[str, Any]]) -> str:
    cols = [
        "dataset",
        "analysis_version",
        "k",
        "method",
        "scheme",
        "window_side",
        "pair",
        "diff",
        "p",
        "se",
        "z",
        "bins_used",
        "n",
        "ci_low",
        "ci_high",
    ]
    json_text = _json_dumps([{c: r.get(c) for c in cols} for r in rows])
    return f"""\
with data as (
  select *
  from jsonb_to_recordset($json${json_text}$json$::jsonb) as x(
    dataset text,
    analysis_version integer,
    k integer,
    method text,
    scheme text,
    window_side text,
    pair text,
    diff double precision,
    p double precision,
    se double precision,
    z double precision,
    bins_used integer,
    n integer,
    ci_low double precision,
    ci_high double precision
  )
)
insert into public.refseq_stop_context_comp_results (
  {", ".join(cols)}
)
select
  {", ".join(cols)}
from data
on conflict (dataset, k, method, scheme, window_side, pair)
do update set
  analysis_version = excluded.analysis_version,
  diff = excluded.diff,
  p = excluded.p,
  se = excluded.se,
  z = excluded.z,
  bins_used = excluded.bins_used,
  n = excluded.n,
  ci_low = excluded.ci_low,
  ci_high = excluded.ci_high;
"""


def _sql_insert_recoding(rows: list[dict[str, Any]]) -> str:
    cols = [
        "analysis_version",
        "k",
        "version",
        "definition",
        "organism",
        "domain",
        "gene",
        "product",
        "cds_location",
        "cds_start",
        "cds_end",
        "cds_strand",
        "translation_start",
        "aa",
        "pos_start",
        "pos_end",
        "codon_dna",
        "codon_rna",
        "n",
        "w",
        "v",
        "delta",
        "is_boundary",
        "before_mean_delta",
        "after_mean_delta",
        "terminal_stop",
        "terminal_before_mean_delta",
        "terminal_after_mean_delta",
        "control_same_codon_before_mean_delta",
        "control_same_codon_after_mean_delta",
        "control_random_cds_before_mean_delta",
        "control_random_cds_after_mean_delta",
        "before_gc",
        "after_gc",
        "before_cpg",
        "after_cpg",
        "before_ta",
        "after_ta",
        "before_dinuc",
        "after_dinuc",
        "terminal_before_gc",
        "terminal_after_gc",
        "terminal_before_cpg",
        "terminal_after_cpg",
        "terminal_before_ta",
        "terminal_after_ta",
        "terminal_before_dinuc",
        "terminal_after_dinuc",
        "nn_ctrl_before_mean_delta",
        "nn_ctrl_after_mean_delta",
        "nn_before_diff",
        "nn_after_diff",
        "nn_before_l1",
        "nn_after_l1",
        "nn_before_gc_diff",
        "nn_after_gc_diff",
        "nn_before_gc_eps",
        "nn_after_gc_eps",
    ]
    json_text = _json_dumps([{c: r.get(c) for c in cols} for r in rows])
    return f"""\
with data as (
  select *
  from jsonb_to_recordset($json${json_text}$json$::jsonb) as x(
    analysis_version integer,
    k integer,
    version text,
    definition text,
    organism text,
    domain text,
    gene text,
    product text,
    cds_location text,
    cds_start integer,
    cds_end integer,
    cds_strand smallint,
    translation_start integer,
    aa text,
    pos_start integer,
    pos_end integer,
    codon_dna text,
    codon_rna text,
    n integer,
    w text,
    v integer,
    delta integer,
    is_boundary boolean,
    before_mean_delta double precision,
    after_mean_delta double precision,
    terminal_stop text,
    terminal_before_mean_delta double precision,
    terminal_after_mean_delta double precision,
    control_same_codon_before_mean_delta double precision,
    control_same_codon_after_mean_delta double precision,
    control_random_cds_before_mean_delta double precision,
    control_random_cds_after_mean_delta double precision,
    before_gc double precision,
    after_gc double precision,
    before_cpg double precision,
    after_cpg double precision,
    before_ta double precision,
    after_ta double precision,
    before_dinuc jsonb,
    after_dinuc jsonb,
    terminal_before_gc double precision,
    terminal_after_gc double precision,
    terminal_before_cpg double precision,
    terminal_after_cpg double precision,
    terminal_before_ta double precision,
    terminal_after_ta double precision,
    terminal_before_dinuc jsonb,
    terminal_after_dinuc jsonb,
    nn_ctrl_before_mean_delta double precision,
    nn_ctrl_after_mean_delta double precision,
    nn_before_diff double precision,
    nn_after_diff double precision,
    nn_before_l1 double precision,
    nn_after_l1 double precision,
    nn_before_gc_diff double precision,
    nn_after_gc_diff double precision,
    nn_before_gc_eps double precision,
    nn_after_gc_eps double precision
  )
)
insert into public.recoding_sites (
  {", ".join(cols)}
)
select
  {", ".join(cols)}
from data
on conflict (analysis_version, k, version, pos_start)
do nothing;
"""


def _sql_insert_analysis_runs(*, transcriptome_summary: dict[str, Any], recoding_meta: dict[str, Any]) -> str:
    # Prefer analysis_version if present; fall back to schema_version for older summaries.
    a_ref = int(transcriptome_summary.get("analysis_version", 0) or 0)
    if a_ref <= 0:
        a_ref = int(transcriptome_summary.get("schema_version", 0) or 0)
    ref_payload = _json_dumps(transcriptome_summary)
    rec_payload = _json_dumps(recoding_meta)
    return f"""\
insert into public.analysis_runs (dataset, analysis, analysis_version, payload)
values
  ('human_refseq_mrna', 'transcriptome_summary', {a_ref}, $json${ref_payload}$json$::jsonb),
  ('ncbi_recoding_genbank', 'recoding_sites', {int(recoding_meta.get("analysis_version", 0) or 0)}, $json${rec_payload}$json$::jsonb)
on conflict (dataset, analysis, analysis_version)
do update set
  payload = excluded.payload,
  inserted_at = now();
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare SQL files for Supabase MCP imports.")
    p.add_argument(
        "--exports-dir",
        default="data/_quick/db_exports_mcp",
        help="Directory containing exported CSV files (relative to project root).",
    )
    p.add_argument(
        "--out-dir",
        default="data/_quick/mcp_sql_import",
        help="Output directory for .sql files (relative to project root).",
    )
    p.add_argument("--chunk-size", type=int, default=200, help="Rows per insert chunk for recoding_sites.")
    p.add_argument("--recoding-analysis-version", type=int, default=5, help="analysis_version to stamp into recoding_sites.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent.parent
    exports_dir = (root / str(args.exports_dir)).resolve()
    out_dir = (root / str(args.out_dir)).resolve()

    rec_csv = exports_dir / "recoding_sites.csv"
    ref_csv = exports_dir / "refseq_stop_context_comp_results.csv"
    if not rec_csv.exists():
        raise SystemExit(f"Missing export: {rec_csv}")
    if not ref_csv.exists():
        raise SystemExit(f"Missing export: {ref_csv}")

    rec_rows_raw = _read_csv(rec_csv)
    ref_rows_raw = _read_csv(ref_csv)

    if not rec_rows_raw:
        raise SystemExit(f"No rows in recoding CSV: {rec_csv}")
    if not ref_rows_raw:
        raise SystemExit(f"No rows in refseq CSV: {ref_csv}")

    rec_rows = _prep_recoding_rows(rec_rows_raw, analysis_version=int(args.recoding_analysis_version))
    ref_rows = _prep_refseq_rows(ref_rows_raw)

    _write_sql(out_dir / "001_refseq_stop_context_comp_results.sql", _sql_insert_refseq(ref_rows))

    for i, chunk_rows in enumerate(_chunk(rec_rows, int(args.chunk_size))):
        _write_sql(out_dir / f"010_recoding_sites_{i:03d}.sql", _sql_insert_recoding(chunk_rows))

    # analysis_runs payloads
    transcriptome_path = root / "data" / "refseq_hsapiens_mrna" / "transcriptome_summary.json"
    if transcriptome_path.exists():
        transcriptome_summary = json.loads(transcriptome_path.read_text(encoding="utf-8"))
        if not isinstance(transcriptome_summary, dict):
            raise SystemExit(f"Malformed transcriptome_summary.json: {transcriptome_path}")
    else:
        transcriptome_summary = {"schema_version": 0, "note": "missing transcriptome_summary.json"}

    # Minimal recoding metadata (kept small; raw rows live in recoding_sites table).
    ks = sorted({int(r["k"]) for r in rec_rows if isinstance(r.get("k"), int)})
    recoding_meta = {
        "analysis_version": int(args.recoding_analysis_version),
        "rows": len(rec_rows),
        "k_list": ks,
        "exports_dir": str(exports_dir),
    }
    _write_sql(out_dir / "900_analysis_runs.sql", _sql_insert_analysis_runs(transcriptome_summary=transcriptome_summary, recoding_meta=recoding_meta))

    print("Wrote SQL dir:", out_dir)
    print("  refseq rows:", len(ref_rows))
    print("  recoding rows:", len(rec_rows), f"(chunks={len(_chunk(rec_rows, int(args.chunk_size)))})")


if __name__ == "__main__":
    main()


