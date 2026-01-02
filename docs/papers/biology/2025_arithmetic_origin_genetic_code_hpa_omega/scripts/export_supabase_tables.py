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
  - stop_context_pairwise_effects.csv
  - stop_context_means.csv
  - start_context_means.csv
  - dataset_codon_usage_null.csv
  - codon_usage_null_decomp_aa.csv
  - codon_usage_null_decomp_codon.csv
  - recoding_context_effects_multi_k.csv

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
from stats_tools import bh_fdr


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


def export_stop_context_pairwise_effects(
    *,
    refseq_summary_json: Path,
    refseq_effects_tsv: Path,
    refseq_dataset: str,
    panel_summary_json: Path,
    out_csv: Path,
) -> None:
    rows: list[dict[str, object]] = []

    # ---- RefSeq TSV (has q-values already) ----
    if refseq_summary_json.exists() and refseq_effects_tsv.exists():
        ref_obj = json.loads(refseq_summary_json.read_text(encoding="utf-8"))
        if isinstance(ref_obj, dict):
            ref_av = infer_analysis_version(refseq_summary_json, summary_obj=ref_obj)
            if ref_av:
                with refseq_effects_tsv.open("r", encoding="utf-8") as f:
                    reader = csv.DictReader(f, delimiter="\t")
                    for r in reader:
                        window = str((r.get("window") or "")).strip()
                        if window not in ("before", "after"):
                            continue
                        pair = str((r.get("pair") or "")).strip()
                        if not pair:
                            continue
                        try:
                            k = int(float(r.get("k") or 0))
                        except Exception:
                            continue
                        if k <= 0:
                            continue
                        def _f(key: str) -> float | None:
                            s = str((r.get(key) or "")).strip()
                            if not s:
                                return None
                            try:
                                return float(s)
                            except Exception:
                                return None
                        def _i(key: str) -> int | None:
                            s = str((r.get(key) or "")).strip()
                            if not s:
                                return None
                            try:
                                return int(float(s))
                            except Exception:
                                return None
                        rows.append(
                            {
                                "panel": "na",
                                "dataset": str(refseq_dataset),
                                "analysis_version": int(ref_av),
                                "window_side": window,
                                "k": int(k),
                                "pair": pair,
                                "n1": _i("n1"),
                                "n2": _i("n2"),
                                "mean1": _f("mean1"),
                                "mean2": _f("mean2"),
                                "diff": _f("diff"),
                                "ci_low": _f("ci_low"),
                                "ci_high": _f("ci_high"),
                                "cohen_d": _f("cohen_d"),
                                "hedges_g": _f("hedges_g"),
                                "z": None,
                                "p": _f("p_welch"),
                                "q": _f("q_bh"),
                                "payload": r,
                            }
                        )

    # ---- Corpus panel JSON (compute BH q-values per dataset item) ----
    if panel_summary_json.exists():
        pobj = json.loads(panel_summary_json.read_text(encoding="utf-8"))
        if isinstance(pobj, dict):
            panel = str(pobj.get("panel") or "corpus_panel_v1")
            pav = infer_analysis_version(panel_summary_json, summary_obj=pobj) or int(pobj.get("analysis_version", 0) or 0)
            items = pobj.get("items") or []
            if isinstance(items, list) and pav:
                for it in items:
                    if not isinstance(it, dict) or not it.get("present"):
                        continue
                    ds = str(it.get("dataset") or "")
                    summ = it.get("summary") or {}
                    if not ds or not isinstance(summ, dict):
                        continue
                    eff = summ.get("stop_context_effects_multi_k") or {}
                    if not isinstance(eff, dict):
                        continue

                    tmp_rows: list[dict[str, object]] = []
                    pvals: list[float] = []
                    for window_side in ("before", "after"):
                        by_k = eff.get(window_side) or {}
                        if not isinstance(by_k, dict):
                            continue
                        for k_str, by_pair in by_k.items():
                            try:
                                k = int(k_str)
                            except Exception:
                                continue
                            if k <= 0 or not isinstance(by_pair, dict):
                                continue
                            for pair, r in by_pair.items():
                                if not isinstance(r, dict):
                                    continue
                                diff = r.get("diff")
                                p = r.get("p")
                                try:
                                    diff_f = None if diff is None else float(diff)
                                except Exception:
                                    diff_f = None
                                try:
                                    p_f = None if p is None else float(p)
                                except Exception:
                                    p_f = None
                                if diff_f is None or p_f is None:
                                    continue
                                if not (0.0 <= float(p_f) <= 1.0):
                                    continue
                                tmp_rows.append(
                                    {
                                        "panel": panel,
                                        "dataset": ds,
                                        "analysis_version": int(pav),
                                        "window_side": str(window_side),
                                        "k": int(k),
                                        "pair": str(pair),
                                        "n1": r.get("n1"),
                                        "n2": r.get("n2"),
                                        "mean1": r.get("mean1"),
                                        "mean2": r.get("mean2"),
                                        "diff": diff_f,
                                        "ci_low": r.get("ci_low"),
                                        "ci_high": r.get("ci_high"),
                                        "cohen_d": r.get("d"),
                                        "hedges_g": r.get("g"),
                                        "z": r.get("z"),
                                        "p": float(p_f),
                                        "q": None,
                                        "payload": r,
                                    }
                                )
                                pvals.append(float(p_f))
                    if tmp_rows and pvals:
                        qs = bh_fdr(pvals)
                        for row, qv in zip(tmp_rows, qs):
                            row["q"] = float(qv)
                    rows.extend(tmp_rows)

    cols = [
        "panel",
        "dataset",
        "analysis_version",
        "window_side",
        "k",
        "pair",
        "n1",
        "n2",
        "mean1",
        "mean2",
        "diff",
        "ci_low",
        "ci_high",
        "cohen_d",
        "hedges_g",
        "z",
        "p",
        "q",
        "payload",
    ]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f_out:
        w = csv.DictWriter(f_out, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _csv_cell(r.get(k)) for k in cols})
    print("Wrote:", out_csv, f"(rows={len(rows)})")


def export_stop_context_means(*, refseq_summary_json: Path, refseq_dataset: str, panel_summary_json: Path, out_csv: Path) -> None:
    rows: list[dict[str, object]] = []

    # RefSeq: use Welford multi-k (before/after may have distinct n).
    if refseq_summary_json.exists():
        obj = json.loads(refseq_summary_json.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            av = infer_analysis_version(refseq_summary_json, summary_obj=obj) or int(obj.get("analysis_version", 0) or 0)
            w_mk = obj.get("stop_context_welford_multi_k") or {}
            ks = obj.get("stop_window_list") or []
            k_list: list[int] = []
            if isinstance(ks, list):
                for x in ks:
                    try:
                        k_list.append(int(x))
                    except Exception:
                        continue
            k_list = sorted({int(k) for k in k_list if int(k) >= 1})
            if av and isinstance(w_mk, dict):
                for stop_codon, by_k in w_mk.items():
                    if not isinstance(by_k, dict):
                        continue
                    for k in k_list:
                        ent = by_k.get(str(int(k))) or {}
                        if not isinstance(ent, dict):
                            continue
                        b = ent.get("before") or {}
                        a = ent.get("after") or {}
                        if not isinstance(b, dict) or not isinstance(a, dict):
                            continue
                        nb = int(b.get("n", 0) or 0)
                        na = int(a.get("n", 0) or 0)
                        bm = b.get("mean")
                        am = a.get("mean")
                        rows.append(
                            {
                                "panel": "na",
                                "dataset": str(refseq_dataset),
                                "analysis_version": int(av),
                                "k": int(k),
                                "stop_codon": str(stop_codon),
                                "n_before": int(nb),
                                "before_mean": (float(bm) if nb > 0 and bm is not None else None),
                                "n_after": int(na),
                                "after_mean": (float(am) if na > 0 and am is not None else None),
                                "payload": {"before": b, "after": a},
                            }
                        )

    # Panel: stop_context_multi_k (single n stored).
    if panel_summary_json.exists():
        pobj = json.loads(panel_summary_json.read_text(encoding="utf-8"))
        if isinstance(pobj, dict):
            panel = str(pobj.get("panel") or "corpus_panel_v1")
            pav = infer_analysis_version(panel_summary_json, summary_obj=pobj) or int(pobj.get("analysis_version", 0) or 0)
            items = pobj.get("items") or []
            if pav and isinstance(items, list):
                for it in items:
                    if not isinstance(it, dict) or not it.get("present"):
                        continue
                    ds = str(it.get("dataset") or "")
                    summ = it.get("summary") or {}
                    if not ds or not isinstance(summ, dict):
                        continue
                    sc = summ.get("stop_context_multi_k") or {}
                    if not isinstance(sc, dict):
                        continue
                    for k_str, by_stop in sc.items():
                        try:
                            k = int(k_str)
                        except Exception:
                            continue
                        if k <= 0 or not isinstance(by_stop, dict):
                            continue
                        for stop_codon, ent in by_stop.items():
                            if not isinstance(ent, dict):
                                continue
                            n = int(ent.get("n", 0) or 0)
                            bm = ent.get("before_mean")
                            am = ent.get("after_mean")
                            rows.append(
                                {
                                    "panel": panel,
                                    "dataset": ds,
                                    "analysis_version": int(pav),
                                    "k": int(k),
                                    "stop_codon": str(stop_codon),
                                    "n_before": int(n),
                                    "before_mean": (float(bm) if n > 0 and bm is not None else None),
                                    "n_after": int(n if am is not None else 0),
                                    "after_mean": (float(am) if am is not None else None),
                                    "payload": ent,
                                }
                            )

    cols = [
        "panel",
        "dataset",
        "analysis_version",
        "k",
        "stop_codon",
        "n_before",
        "before_mean",
        "n_after",
        "after_mean",
        "payload",
    ]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f_out:
        w = csv.DictWriter(f_out, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _csv_cell(r.get(k)) for k in cols})
    print("Wrote:", out_csv, f"(rows={len(rows)})")


def export_start_context_means(*, refseq_summary_json: Path, refseq_dataset: str, panel_summary_json: Path, out_csv: Path) -> None:
    rows: list[dict[str, object]] = []

    # RefSeq: use Welford multi-k.
    if refseq_summary_json.exists():
        obj = json.loads(refseq_summary_json.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            av = infer_analysis_version(refseq_summary_json, summary_obj=obj) or int(obj.get("analysis_version", 0) or 0)
            sc_mk = obj.get("start_context_welford_multi_k") or {}
            ks = obj.get("stop_window_list") or []
            k_list: list[int] = []
            if isinstance(ks, list):
                for x in ks:
                    try:
                        k_list.append(int(x))
                    except Exception:
                        continue
            k_list = sorted({int(k) for k in k_list if int(k) >= 1})
            if av and isinstance(sc_mk, dict):
                for k in k_list:
                    ent = sc_mk.get(str(int(k))) or {}
                    if not isinstance(ent, dict):
                        continue
                    b = ent.get("before") or {}
                    a = ent.get("after") or {}
                    if not isinstance(b, dict) or not isinstance(a, dict):
                        continue
                    nb = int(b.get("n", 0) or 0)
                    na = int(a.get("n", 0) or 0)
                    bm = b.get("mean")
                    am = a.get("mean")
                    rows.append(
                        {
                            "panel": "na",
                            "dataset": str(refseq_dataset),
                            "analysis_version": int(av),
                            "k": int(k),
                            "start_event": "AUG",
                            "n_before": int(nb),
                            "before_mean": (float(bm) if nb > 0 and bm is not None else None),
                            "n_after": int(na),
                            "after_mean": (float(am) if na > 0 and am is not None else None),
                            "payload": {"before": b, "after": a},
                        }
                    )

    # Panel: start_context_multi_k
    if panel_summary_json.exists():
        pobj = json.loads(panel_summary_json.read_text(encoding="utf-8"))
        if isinstance(pobj, dict):
            panel = str(pobj.get("panel") or "corpus_panel_v1")
            pav = infer_analysis_version(panel_summary_json, summary_obj=pobj) or int(pobj.get("analysis_version", 0) or 0)
            items = pobj.get("items") or []
            if pav and isinstance(items, list):
                for it in items:
                    if not isinstance(it, dict) or not it.get("present"):
                        continue
                    ds = str(it.get("dataset") or "")
                    mode = str(it.get("mode") or "")
                    start_event = "AUG" if mode == "refseq_mrna_best_orf" else ("cds_start" if mode == "cds_fasta" else "start")
                    summ = it.get("summary") or {}
                    if not ds or not isinstance(summ, dict):
                        continue
                    sc = summ.get("start_context_multi_k") or {}
                    if not isinstance(sc, dict):
                        continue
                    for k_str, ent in sc.items():
                        try:
                            k = int(k_str)
                        except Exception:
                            continue
                        if k <= 0 or not isinstance(ent, dict):
                            continue
                        b = ent.get("before") or {}
                        a = ent.get("after") or {}
                        if not isinstance(b, dict) or not isinstance(a, dict):
                            continue
                        nb = int(b.get("n", 0) or 0)
                        na = int(a.get("n", 0) or 0)
                        bm = b.get("mean")
                        am = a.get("mean")
                        rows.append(
                            {
                                "panel": panel,
                                "dataset": ds,
                                "analysis_version": int(pav),
                                "k": int(k),
                                "start_event": str(start_event),
                                "n_before": int(nb),
                                "before_mean": (float(bm) if nb > 0 and bm is not None else None),
                                "n_after": int(na),
                                "after_mean": (float(am) if na > 0 and am is not None else None),
                                "payload": {"before": b, "after": a, "mode": mode},
                            }
                        )

    cols = [
        "panel",
        "dataset",
        "analysis_version",
        "k",
        "start_event",
        "n_before",
        "before_mean",
        "n_after",
        "after_mean",
        "payload",
    ]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f_out:
        w = csv.DictWriter(f_out, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _csv_cell(r.get(k)) for k in cols})
    print("Wrote:", out_csv, f"(rows={len(rows)})")


def export_dataset_codon_usage_null(*, refseq_summary_json: Path, refseq_dataset: str, panel_summary_json: Path, out_csv: Path) -> None:
    rows: list[dict[str, object]] = []

    # RefSeq
    if refseq_summary_json.exists():
        obj = json.loads(refseq_summary_json.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            av = infer_analysis_version(refseq_summary_json, summary_obj=obj) or int(obj.get("analysis_version", 0) or 0)
            cu = obj.get("codon_usage") or {}
            if av and isinstance(cu, dict):
                null = cu.get("null") or {}
                if isinstance(null, dict):
                    rows.append(
                        {
                            "panel": "na",
                            "dataset": str(refseq_dataset),
                            "analysis_version": int(av),
                            "obs_zbar": cu.get("zbar"),
                            "obs_ubar": cu.get("ubar"),
                            "null_mean_zbar": null.get("null_mu_zbar"),
                            "null_sd_zbar": null.get("null_sd_zbar"),
                            "null_mean_ubar": null.get("null_mu_ubar"),
                            "null_sd_ubar": null.get("null_sd_ubar"),
                            "z_zbar": null.get("z_zbar"),
                            "z_ubar": null.get("z_ubar"),
                            "p_zbar": null.get("p_zbar"),
                            "p_ubar": null.get("p_ubar"),
                            "total_codons": null.get("total_codons"),
                            "payload": {"codon_usage": cu},
                        }
                    )

    # Panel
    if panel_summary_json.exists():
        pobj = json.loads(panel_summary_json.read_text(encoding="utf-8"))
        if isinstance(pobj, dict):
            panel = str(pobj.get("panel") or "corpus_panel_v1")
            pav = infer_analysis_version(panel_summary_json, summary_obj=pobj) or int(pobj.get("analysis_version", 0) or 0)
            items = pobj.get("items") or []
            if pav and isinstance(items, list):
                for it in items:
                    if not isinstance(it, dict) or not it.get("present"):
                        continue
                    ds = str(it.get("dataset") or "")
                    cu = it.get("codon_usage_null") or {}
                    summ = it.get("summary") or {}
                    if not ds or not isinstance(cu, dict) or not isinstance(summ, dict):
                        continue
                    u = cu.get("U") or {}
                    z = cu.get("Z") or {}
                    if not isinstance(u, dict) or not isinstance(z, dict):
                        continue
                    rows.append(
                        {
                            "panel": panel,
                            "dataset": ds,
                            "analysis_version": int(pav),
                            "obs_zbar": z.get("obs_mean"),
                            "obs_ubar": u.get("obs_mean"),
                            "null_mean_zbar": z.get("null_mean"),
                            "null_sd_zbar": z.get("null_sd"),
                            "null_mean_ubar": u.get("null_mean"),
                            "null_sd_ubar": u.get("null_sd"),
                            "z_zbar": z.get("z"),
                            "z_ubar": u.get("z"),
                            "p_zbar": z.get("p"),
                            "p_ubar": u.get("p"),
                            "total_codons": summ.get("coding_tokens"),
                            "payload": {"codon_usage_null": cu},
                        }
                    )

    cols = [
        "panel",
        "dataset",
        "analysis_version",
        "obs_zbar",
        "obs_ubar",
        "null_mean_zbar",
        "null_sd_zbar",
        "null_mean_ubar",
        "null_sd_ubar",
        "z_zbar",
        "z_ubar",
        "p_zbar",
        "p_ubar",
        "total_codons",
        "payload",
    ]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f_out:
        w = csv.DictWriter(f_out, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _csv_cell(r.get(k)) for k in cols})
    print("Wrote:", out_csv, f"(rows={len(rows)})")


def export_codon_usage_null_decomp(
    *,
    refseq_summary_json: Path,
    refseq_dataset: str,
    u_aa_tsv: Path,
    u_codon_tsv: Path,
    z_aa_tsv: Path,
    z_codon_tsv: Path,
    out_aa_csv: Path,
    out_codon_csv: Path,
) -> None:
    if not refseq_summary_json.exists():
        raise SystemExit("Missing transcriptome_summary.json (needed to infer analysis_version).")
    obj = json.loads(refseq_summary_json.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit("Malformed transcriptome_summary.json")
    av = infer_analysis_version(refseq_summary_json, summary_obj=obj) or int(obj.get("analysis_version", 0) or 0)
    if not av:
        raise SystemExit("Missing analysis_version for transcriptome_summary.json")

    def _load_tsv(path: Path) -> list[dict[str, str]]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            out: list[dict[str, str]] = []
            for r in reader:
                out.append({str(k): ("" if v is None else str(v)) for k, v in (r or {}).items()})
            return out

    aa_rows: list[dict[str, object]] = []
    codon_rows: list[dict[str, object]] = []

    for metric, path in (("U", u_aa_tsv), ("Z", z_aa_tsv)):
        for r in _load_tsv(path):
            aa = (r.get("aa") or "").strip()
            if not aa:
                continue
            aa_rows.append(
                {
                    "panel": "na",
                    "dataset": str(refseq_dataset),
                    "analysis_version": int(av),
                    "metric": metric,
                    "aa": aa,
                    "n": r.get("n"),
                    "obs_mean": r.get("obs_mean"),
                    "null_mean": r.get("null_mean"),
                    "contrib": r.get("contrib"),
                    "payload": r,
                }
            )

    for metric, path in (("U", u_codon_tsv), ("Z", z_codon_tsv)):
        for r in _load_tsv(path):
            codon = (r.get("codon") or "").strip()
            if not codon:
                continue
            codon_rows.append(
                {
                    "panel": "na",
                    "dataset": str(refseq_dataset),
                    "analysis_version": int(av),
                    "metric": metric,
                    "codon": codon,
                    "aa": r.get("aa"),
                    "obs_count": r.get("obs_count"),
                    "null_count": r.get("null_count"),
                    "contrib": r.get("contrib"),
                    "payload": r,
                }
            )

    aa_cols = ["panel", "dataset", "analysis_version", "metric", "aa", "n", "obs_mean", "null_mean", "contrib", "payload"]
    out_aa_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_aa_csv.open("w", encoding="utf-8", newline="") as f_out:
        w = csv.DictWriter(f_out, fieldnames=aa_cols, extrasaction="ignore")
        w.writeheader()
        for r in aa_rows:
            w.writerow({k: _csv_cell(r.get(k)) for k in aa_cols})
    print("Wrote:", out_aa_csv, f"(rows={len(aa_rows)})")

    codon_cols = [
        "panel",
        "dataset",
        "analysis_version",
        "metric",
        "codon",
        "aa",
        "obs_count",
        "null_count",
        "contrib",
        "payload",
    ]
    out_codon_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_codon_csv.open("w", encoding="utf-8", newline="") as f_out:
        w = csv.DictWriter(f_out, fieldnames=codon_cols, extrasaction="ignore")
        w.writeheader()
        for r in codon_rows:
            w.writerow({k: _csv_cell(r.get(k)) for k in codon_cols})
    print("Wrote:", out_codon_csv, f"(rows={len(codon_rows)})")


def export_recoding_context_effects_multi_k(*, recoding_summary_json: Path, recoding_dataset: str, out_csv: Path) -> None:
    if not recoding_summary_json.exists():
        raise SystemExit("Missing recoding_sites_summary.json")
    obj = json.loads(recoding_summary_json.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit("Malformed recoding_sites_summary.json")
    av = infer_analysis_version(recoding_summary_json, summary_obj=obj) or int(obj.get("analysis_version", 0) or 0)
    if not av:
        raise SystemExit("Missing analysis_version for recoding_sites_summary.json")

    items = obj.get("multi_k_overall") or []
    if not isinstance(items, list):
        items = []

    tmp_rows: list[dict[str, object]] = []
    pvals: list[float] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        label = str(it.get("label") or "").strip()
        k = int(it.get("k", 0) or 0)
        if not label or k <= 0:
            continue
        for window_side in ("before", "after"):
            w0 = it.get(window_side) or {}
            if not isinstance(w0, dict):
                continue
            p = w0.get("p_welch")
            try:
                p_f = None if p is None else float(p)
            except Exception:
                p_f = None
            if p_f is None or not (0.0 <= p_f <= 1.0):
                continue
            tmp_rows.append(
                {
                    "dataset": str(recoding_dataset),
                    "analysis_version": int(av),
                    "k": int(k),
                    "window_side": str(window_side),
                    "label": label,
                    "n1": w0.get("n1"),
                    "n2": w0.get("n2"),
                    "mean1": w0.get("mean1"),
                    "mean2": w0.get("mean2"),
                    "diff": w0.get("diff"),
                    "ci_low": w0.get("ci_low"),
                    "ci_high": w0.get("ci_high"),
                    "cohen_d": w0.get("d"),
                    "hedges_g": w0.get("g"),
                    "p_perm": w0.get("p_perm"),
                    "p_welch": float(p_f),
                    "q_welch": None,
                    "payload": w0,
                }
            )
            pvals.append(float(p_f))

    if tmp_rows and pvals:
        qs = bh_fdr(pvals)
        for row, q in zip(tmp_rows, qs):
            row["q_welch"] = float(q)

    cols = [
        "dataset",
        "analysis_version",
        "k",
        "window_side",
        "label",
        "n1",
        "n2",
        "mean1",
        "mean2",
        "diff",
        "ci_low",
        "ci_high",
        "cohen_d",
        "hedges_g",
        "p_perm",
        "p_welch",
        "q_welch",
        "payload",
    ]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f_out:
        w = csv.DictWriter(f_out, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in tmp_rows:
            w.writerow({k: _csv_cell(r.get(k)) for k in cols})
    print("Wrote:", out_csv, f"(rows={len(tmp_rows)})")


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
        "--refseq-stop-effects-tsv",
        default="data/refseq_hsapiens_mrna/stop_context_pairwise_effects.tsv",
        help="Input RefSeq stop-context pairwise effects TSV path (relative to project root by default).",
    )
    p.add_argument(
        "--refseq-null-decomp-u-aa-tsv",
        default="data/refseq_hsapiens_mrna/codon_usage_null_decomp_U_aa.tsv",
        help="Input RefSeq codon-usage null decomposition TSV (U, per AA).",
    )
    p.add_argument(
        "--refseq-null-decomp-u-codon-tsv",
        default="data/refseq_hsapiens_mrna/codon_usage_null_decomp_U_codon.tsv",
        help="Input RefSeq codon-usage null decomposition TSV (U, per codon).",
    )
    p.add_argument(
        "--refseq-null-decomp-z-aa-tsv",
        default="data/refseq_hsapiens_mrna/codon_usage_null_decomp_Z_aa.tsv",
        help="Input RefSeq codon-usage null decomposition TSV (Z, per AA).",
    )
    p.add_argument(
        "--refseq-null-decomp-z-codon-tsv",
        default="data/refseq_hsapiens_mrna/codon_usage_null_decomp_Z_codon.tsv",
        help="Input RefSeq codon-usage null decomposition TSV (Z, per codon).",
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
    p.add_argument("--no-stop-context-effects", action="store_true", help="Skip exporting stop_context_pairwise_effects.csv.")
    p.add_argument("--no-stop-context-means", action="store_true", help="Skip exporting stop_context_means.csv.")
    p.add_argument("--no-start-context-means", action="store_true", help="Skip exporting start_context_means.csv.")
    p.add_argument("--no-codon-usage-null", action="store_true", help="Skip exporting dataset_codon_usage_null.csv.")
    p.add_argument("--no-codon-usage-decomp", action="store_true", help="Skip exporting codon_usage_null_decomp_*.csv.")
    p.add_argument("--no-recoding-summary", action="store_true", help="Skip exporting recoding_context_effects_multi_k.csv.")
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
            "refseq_stop_effects_tsv": _fingerprint_file((root / str(args.refseq_stop_effects_tsv)).resolve()),
            "refseq_null_decomp_u_aa_tsv": _fingerprint_file((root / str(args.refseq_null_decomp_u_aa_tsv)).resolve()),
            "refseq_null_decomp_u_codon_tsv": _fingerprint_file((root / str(args.refseq_null_decomp_u_codon_tsv)).resolve()),
            "refseq_null_decomp_z_aa_tsv": _fingerprint_file((root / str(args.refseq_null_decomp_z_aa_tsv)).resolve()),
            "refseq_null_decomp_z_codon_tsv": _fingerprint_file((root / str(args.refseq_null_decomp_z_codon_tsv)).resolve()),
            "recoding_summary_json": _fingerprint_file((root / "data" / "recoding_genbank" / "recoding_sites_summary.json").resolve()),
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
            "no_stop_context_effects": bool(args.no_stop_context_effects),
            "no_stop_context_means": bool(args.no_stop_context_means),
            "no_start_context_means": bool(args.no_start_context_means),
            "no_codon_usage_null": bool(args.no_codon_usage_null),
            "no_codon_usage_decomp": bool(args.no_codon_usage_decomp),
            "no_recoding_summary": bool(args.no_recoding_summary),
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
    if not args.no_stop_context_effects:
        expected_outputs.append(out_dir / "stop_context_pairwise_effects.csv")
    if not args.no_stop_context_means:
        expected_outputs.append(out_dir / "stop_context_means.csv")
    if not args.no_start_context_means:
        expected_outputs.append(out_dir / "start_context_means.csv")
    if not args.no_codon_usage_null:
        expected_outputs.append(out_dir / "dataset_codon_usage_null.csv")
    if not args.no_codon_usage_decomp:
        expected_outputs.append(out_dir / "codon_usage_null_decomp_aa.csv")
        expected_outputs.append(out_dir / "codon_usage_null_decomp_codon.csv")
    if not args.no_recoding_summary:
        expected_outputs.append(out_dir / "recoding_context_effects_multi_k.csv")

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

    # Context summary exports (RefSeq + corpus panel combined where available)
    if not args.no_stop_context_effects:
        export_stop_context_pairwise_effects(
            refseq_summary_json=(root / str(args.refseq_summary_json)).resolve(),
            refseq_effects_tsv=(root / str(args.refseq_stop_effects_tsv)).resolve(),
            refseq_dataset=str(args.refseq_dataset),
            panel_summary_json=(root / str(args.panel_summary_json)).resolve(),
            out_csv=out_dir / "stop_context_pairwise_effects.csv",
        )
    if not args.no_stop_context_means:
        export_stop_context_means(
            refseq_summary_json=(root / str(args.refseq_summary_json)).resolve(),
            refseq_dataset=str(args.refseq_dataset),
            panel_summary_json=(root / str(args.panel_summary_json)).resolve(),
            out_csv=out_dir / "stop_context_means.csv",
        )
    if not args.no_start_context_means:
        export_start_context_means(
            refseq_summary_json=(root / str(args.refseq_summary_json)).resolve(),
            refseq_dataset=str(args.refseq_dataset),
            panel_summary_json=(root / str(args.panel_summary_json)).resolve(),
            out_csv=out_dir / "start_context_means.csv",
        )
    if not args.no_codon_usage_null:
        export_dataset_codon_usage_null(
            refseq_summary_json=(root / str(args.refseq_summary_json)).resolve(),
            refseq_dataset=str(args.refseq_dataset),
            panel_summary_json=(root / str(args.panel_summary_json)).resolve(),
            out_csv=out_dir / "dataset_codon_usage_null.csv",
        )

    if not args.no_codon_usage_decomp:
        export_codon_usage_null_decomp(
            refseq_summary_json=(root / str(args.refseq_summary_json)).resolve(),
            refseq_dataset=str(args.refseq_dataset),
            u_aa_tsv=(root / str(args.refseq_null_decomp_u_aa_tsv)).resolve(),
            u_codon_tsv=(root / str(args.refseq_null_decomp_u_codon_tsv)).resolve(),
            z_aa_tsv=(root / str(args.refseq_null_decomp_z_aa_tsv)).resolve(),
            z_codon_tsv=(root / str(args.refseq_null_decomp_z_codon_tsv)).resolve(),
            out_aa_csv=out_dir / "codon_usage_null_decomp_aa.csv",
            out_codon_csv=out_dir / "codon_usage_null_decomp_codon.csv",
        )

    if not args.no_recoding_summary:
        export_recoding_context_effects_multi_k(
            recoding_summary_json=(root / "data" / "recoding_genbank" / "recoding_sites_summary.json").resolve(),
            recoding_dataset="ncbi_recoding_genbank",
            out_csv=out_dir / "recoding_context_effects_multi_k.csv",
        )

    write_json_atomic(cache_file, {"ok": True})
    write_json_atomic(cache_meta_path(cache_file), cache_meta)


if __name__ == "__main__":
    main()


