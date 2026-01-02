# -*- coding: utf-8 -*-
"""
Export paper datasets to CSV for Supabase/Postgres ingestion (standard library only).

Exports:
  - recoding_sites.csv
  - refseq_stop_context_comp_results.csv
  - refseq_stop_context_candidates.csv
  - corpus_panel_items.csv
  - nonstandard_sequence_tests_items.csv
  - boundary_enrichment_results.csv

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

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic
from progress_tools import Heartbeat
from provenance_tools import infer_analysis_version


DINUC_ORDER = [a + b for a in "ACGT" for b in "ACGT"]

# Bump this when changing exported column sets or output formatting in a way that
# should invalidate the export cache.
EXPORT_VERSION = 1


def _fingerprint_file(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    st = path.stat()
    return {
        "path": str(path),
        "exists": True,
        "bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


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


def export_recoding_sites(*, in_jsonl: Path, out_csv: Path, heartbeat: Heartbeat | None = None) -> None:
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
        "plus4_nt",
        "after_codon1",
        "after_nt6",
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
        "before_seq_dna",
        "after_seq_dna",
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
        with in_jsonl.open("r", encoding="utf-8") as f_in:
            for line_no, line in enumerate(f_in, start=1):
                if not line.strip():
                    continue
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    continue
                row = {k: _csv_cell(obj.get(k)) for k in cols}
                w.writerow(row)
                n += 1
                if heartbeat is not None and (line_no % 5000) == 0:
                    heartbeat.maybe(f"export recoding_sites.csv: wrote {n} rows")
    print("Wrote:", out_csv, f"(rows={n})")


def export_corpus_panel_items(*, in_panel_json: Path, out_csv: Path) -> None:
    obj = json.loads(in_panel_json.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit("Malformed corpus_panel_summary.json")

    panel = str(obj.get("panel") or "corpus_panel_v1")
    analysis_version = infer_analysis_version(in_panel_json, summary_obj=obj)
    if not analysis_version:
        raise SystemExit("Missing analysis_version for corpus_panel_summary.json")

    items = obj.get("items") or []
    if not isinstance(items, list):
        items = []

    cols = [
        "panel",
        "analysis_version",
        "dataset",
        "code_id",
        "label",
        "domain",
        "mode",
        "present",
        "records",
        "records_with_orf",
        "coding_tokens",
        "boundary_token_count",
        "boundary_rate",
        "payload",
    ]

    rows: list[dict[str, object]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        summary = it.get("summary") or {}
        if not isinstance(summary, dict):
            summary = {}
        present = bool(it.get("present"))
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

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f_out:
        w = csv.DictWriter(f_out, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _csv_cell(r.get(k)) for k in cols})
    print("Wrote:", out_csv, f"(rows={len(rows)})")


def export_nonstandard_sequence_tests_items(*, in_json: Path, out_csv: Path) -> None:
    obj = json.loads(in_json.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit("Malformed nonstandard_sequence_tests.json")

    panel = str(obj.get("panel") or "nonstandard_examples_v1")
    analysis_version = infer_analysis_version(in_json, summary_obj=obj)
    if not analysis_version:
        raise SystemExit("Missing analysis_version for nonstandard_sequence_tests.json")

    items = obj.get("items") or []
    if not isinstance(items, list):
        items = []

    cols = [
        "panel",
        "analysis_version",
        "dataset",
        "code_id",
        "label",
        "domain",
        "present",
        "records_seen",
        "records_used",
        "records_invalid",
        "start_boundary_rate",
        "start_boundary_z",
        "start_boundary_p",
        "stop_boundary_rate",
        "stop_boundary_z",
        "stop_boundary_p",
        "payload",
    ]

    rows: list[dict[str, object]] = []
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

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f_out:
        w = csv.DictWriter(f_out, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _csv_cell(r.get(k)) for k in cols})
    print("Wrote:", out_csv, f"(rows={len(rows)})")


def export_refseq_stop_context_comp_results(*, in_summary_json: Path, out_csv: Path, dataset: str) -> None:
    obj = json.loads(in_summary_json.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit("Malformed transcriptome_summary.json")

    analysis_version = infer_analysis_version(in_summary_json, summary_obj=obj)
    if not analysis_version:
        raise SystemExit("Missing analysis_version for transcriptome_summary.json")
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


def export_boundary_enrichment_results(*, in_jsonl: Path, out_csv: Path, heartbeat: Heartbeat | None = None) -> None:
    cols = [
        "dataset",
        "analysis_version",
        "label",
        "method",
        "n_total",
        "n_subset",
        "boundary_rate_total",
        "boundary_rate_subset",
        "enrichment",
        "p",
        "q",
        "payload",
    ]

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f_out:
        w = csv.DictWriter(f_out, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        n = 0
        with in_jsonl.open("r", encoding="utf-8") as f_in:
            for line_no, line in enumerate(f_in, start=1):
                if not line.strip():
                    continue
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    continue
                row = {k: _csv_cell(obj.get(k)) for k in cols}
                w.writerow(row)
                n += 1
                if heartbeat is not None and (line_no % 2000) == 0:
                    heartbeat.maybe(f"export boundary_enrichment_results.csv: wrote {n} rows")
    print("Wrote:", out_csv, f"(rows={n})")


def export_refseq_stop_context_candidates(*, in_jsonl: Path, out_csv: Path, heartbeat: Heartbeat | None = None) -> None:
    cols = [
        "dataset",
        "analysis_version",
        "candidate_set",
        "k",
        "stop_codon",
        "group_label",
        "rank",
        "record_id",
        "frame",
        "start_base",
        "stop_base",
        "before_seq_dna",
        "stop_codon_dna",
        "after_seq_dna",
        "plus4_nt",
        "after_nt6",
        "before_mean_delta",
        "after_mean_delta",
        "diff",
        "before_gc",
        "after_gc",
        "before_dinuc",
        "after_dinuc",
        "payload",
    ]

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f_out:
        w = csv.DictWriter(f_out, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        n = 0
        with in_jsonl.open("r", encoding="utf-8") as f_in:
            for line_no, line in enumerate(f_in, start=1):
                if not line.strip():
                    continue
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    continue
                row = {k: _csv_cell(obj.get(k)) for k in cols}
                w.writerow(row)
                n += 1
                if heartbeat is not None and (line_no % 2000) == 0:
                    heartbeat.maybe(f"export refseq_stop_context_candidates.csv: wrote {n} rows")
    print("Wrote:", out_csv, f"(rows={n})")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export datasets to CSV for Supabase/Postgres.")
    p.add_argument("--out-dir", default="data/db_exports", help="Output directory (relative to project root).")
    p.add_argument("--heartbeat-s", type=int, default=60, help="Progress heartbeat interval seconds (0 disables).")
    p.add_argument(
        "--recoding-jsonl",
        default="data/recoding_genbank/recoding_sites.jsonl",
        help="Input recoding JSONL path (relative to project root by default).",
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
    p.add_argument(
        "--boundary-enrichment-jsonl",
        default="data/boundary_enrichment/boundary_enrichment_results.jsonl",
        help="Input boundary enrichment results JSONL path (relative to project root by default).",
    )
    p.add_argument(
        "--refseq-stop-candidates-jsonl",
        default="data/refseq_hsapiens_mrna/stop_context_candidates.jsonl",
        help="Input RefSeq stop-context candidates JSONL path (relative to project root by default).",
    )
    p.add_argument("--refseq-dataset", default="human_refseq_mrna", help="Dataset label written into refseq CSV.")
    p.add_argument("--no-recoding", action="store_true", help="Skip exporting recoding_sites.csv.")
    p.add_argument("--no-refseq", action="store_true", help="Skip exporting refseq_stop_context_comp_results.csv.")
    p.add_argument("--no-refseq-stop-candidates", action="store_true", help="Skip exporting refseq_stop_context_candidates.csv.")
    p.add_argument("--no-panel", action="store_true", help="Skip exporting corpus_panel_items.csv.")
    p.add_argument("--no-nonstandard", action="store_true", help="Skip exporting nonstandard_sequence_tests_items.csv.")
    p.add_argument("--no-boundary-enrichment", action="store_true", help="Skip exporting boundary_enrichment_results.csv.")
    p.add_argument("--force", action="store_true", help="Force export even if cached outputs exist.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent.parent
    out_dir = (root / str(args.out_dir)).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    hb = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress]")

    boundary_enrichment_in = (root / str(args.boundary_enrichment_jsonl)).resolve()
    boundary_enrichment_enabled = (not args.no_boundary_enrichment) and boundary_enrichment_in.exists()

    refseq_cand_in = (root / str(args.refseq_stop_candidates_jsonl)).resolve()
    refseq_cand_enabled = (not args.no_refseq_stop_candidates) and refseq_cand_in.exists()

    # ---- Cache short-circuit (export-level) ----
    cache_file = out_dir / "_export_supabase_tables_cache.json"
    cache_key = {
        "analysis": "export_supabase_tables",
        "export_version": int(EXPORT_VERSION),
        "out_dir": str(out_dir),
        "inputs": {
            "recoding_jsonl": _fingerprint_file((root / str(args.recoding_jsonl)).resolve()),
            "refseq_summary_json": _fingerprint_file((root / str(args.refseq_summary_json)).resolve()),
            "panel_summary_json": _fingerprint_file((root / str(args.panel_summary_json)).resolve()),
            "nonstandard_seqtests_json": _fingerprint_file((root / str(args.nonstandard_seqtests_json)).resolve()),
            "boundary_enrichment_jsonl": _fingerprint_file((root / str(args.boundary_enrichment_jsonl)).resolve()),
            "refseq_stop_candidates_jsonl": _fingerprint_file((root / str(args.refseq_stop_candidates_jsonl)).resolve()),
        },
        "flags": {
            "no_recoding": bool(args.no_recoding),
            "no_refseq": bool(args.no_refseq),
            "refseq_cand_enabled": bool(refseq_cand_enabled),
            "no_panel": bool(args.no_panel),
            "no_nonstandard": bool(args.no_nonstandard),
            "boundary_enrichment_enabled": bool(boundary_enrichment_enabled),
            "refseq_dataset": str(args.refseq_dataset),
        },
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    expected_outputs: list[Path] = []
    if not args.no_recoding:
        expected_outputs.append(out_dir / "recoding_sites.csv")
    if not args.no_refseq:
        expected_outputs.append(out_dir / "refseq_stop_context_comp_results.csv")
    if refseq_cand_enabled:
        expected_outputs.append(out_dir / "refseq_stop_context_candidates.csv")
    if not args.no_panel:
        expected_outputs.append(out_dir / "corpus_panel_items.csv")
    if not args.no_nonstandard:
        expected_outputs.append(out_dir / "nonstandard_sequence_tests_items.csv")
    if boundary_enrichment_enabled:
        expected_outputs.append(out_dir / "boundary_enrichment_results.csv")

    if (
        (not args.force)
        and expected_outputs
        and all(p.exists() for p in expected_outputs)
        and cache_hit(cache_file, expected_meta=cache_meta, require_meta=True)
    ):
        print(f"[cache] hit: {cache_file}")
        return

    if not args.no_recoding:
        export_recoding_sites(
            in_jsonl=(root / str(args.recoding_jsonl)).resolve(),
            out_csv=out_dir / "recoding_sites.csv",
            heartbeat=hb,
        )
    if not args.no_refseq:
        export_refseq_stop_context_comp_results(
            in_summary_json=(root / str(args.refseq_summary_json)).resolve(),
            out_csv=out_dir / "refseq_stop_context_comp_results.csv",
            dataset=str(args.refseq_dataset),
        )
    if refseq_cand_enabled:
        export_refseq_stop_context_candidates(
            in_jsonl=refseq_cand_in,
            out_csv=out_dir / "refseq_stop_context_candidates.csv",
            heartbeat=hb,
        )
    if not args.no_panel:
        export_corpus_panel_items(
            in_panel_json=(root / str(args.panel_summary_json)).resolve(),
            out_csv=out_dir / "corpus_panel_items.csv",
        )
    if not args.no_nonstandard:
        export_nonstandard_sequence_tests_items(
            in_json=(root / str(args.nonstandard_seqtests_json)).resolve(),
            out_csv=out_dir / "nonstandard_sequence_tests_items.csv",
        )
    if boundary_enrichment_enabled:
        export_boundary_enrichment_results(
            in_jsonl=boundary_enrichment_in,
            out_csv=out_dir / "boundary_enrichment_results.csv",
            heartbeat=hb,
        )

    write_json_atomic(cache_file, {"ok": True})
    write_json_atomic(cache_meta_path(cache_file), cache_meta)


if __name__ == "__main__":
    main()


