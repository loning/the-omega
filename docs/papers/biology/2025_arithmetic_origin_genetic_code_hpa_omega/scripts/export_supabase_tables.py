# -*- coding: utf-8 -*-
"""
Export paper datasets to CSV for Supabase/Postgres ingestion (standard library only).

Exports:
  - recoding_sites.csv
  - refseq_stop_context_comp_results.csv

Notes:
  - JSON objects are serialized as compact JSON strings (for jsonb columns).
  - Empty string represents NULL; use COPY ... NULL '' when importing.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DINUC_ORDER = [a + b for a in "ACGT" for b in "ACGT"]


def _json_dumps(x: object) -> str:
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _csv_cell(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        # Postgres accepts 't'/'f' for boolean.
        return "t" if v else "f"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (dict, list)):
        return _json_dumps(v)
    return str(v)


def export_recoding_sites(*, in_jsonl: Path, out_csv: Path) -> None:
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

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f_out:
        w = csv.DictWriter(f_out, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        n = 0
        for line in in_jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                continue
            row = {k: _csv_cell(obj.get(k)) for k in cols}
            w.writerow(row)
            n += 1
    print("Wrote:", out_csv, f"(rows={n})")


def export_refseq_stop_context_comp_results(*, in_summary_json: Path, out_csv: Path) -> None:
    obj = json.loads(in_summary_json.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit("Malformed transcriptome_summary.json")

    dataset = "human_refseq_mrna"
    analysis_version = int(obj.get("schema_version", 0) or 0)
    # Note: schema_version != analysis_version in code; keep both if you want.
    k = int(obj.get("stop_window", 0) or 0)
    if k <= 0:
        raise SystemExit("Missing stop_window in transcriptome_summary.json")

    comp = obj.get("stop_context_composition") or {}
    if not isinstance(comp, dict) or not comp:
        raise SystemExit("Missing stop_context_composition in transcriptome_summary.json (run merge with schema v3).")

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

    rows: list[dict[str, object]] = []

    strat = comp.get("stratified") or {}
    if isinstance(strat, dict):
        for scheme, scheme_obj in strat.items():
            if not isinstance(scheme_obj, dict):
                continue
            for window in ("before", "after"):
                w0 = scheme_obj.get(window) or {}
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
                            "window_side": str(window),
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
            for window in ("before", "after"):
                w0 = res.get(window) or {}
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
                            "window_side": str(window),
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

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f_out:
        w = csv.DictWriter(f_out, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _csv_cell(r.get(k)) for k in cols})
    print("Wrote:", out_csv, f"(rows={len(rows)})")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export datasets to CSV for Supabase/Postgres.")
    p.add_argument("--out-dir", default="data/db_exports", help="Output directory (relative to project root).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent.parent
    out_dir = (root / str(args.out_dir)).resolve()

    export_recoding_sites(
        in_jsonl=root / "data" / "recoding_genbank" / "recoding_sites.jsonl",
        out_csv=out_dir / "recoding_sites.csv",
    )
    export_refseq_stop_context_comp_results(
        in_summary_json=root / "data" / "refseq_hsapiens_mrna" / "transcriptome_summary.json",
        out_csv=out_dir / "refseq_stop_context_comp_results.csv",
    )


if __name__ == "__main__":
    main()


