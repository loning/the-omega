# -*- coding: utf-8 -*-
"""
Fold_m boundary enrichment tests for annotation-aligned codon positions.

This generalizes exp_boundary_enrichment.py (Fold_6 boundary words) to Fold_m
with the canonical boundary condition:
  - admissible word w in X_m (golden-mean grammar)
  - boundary iff w_1 = w_m = 1

Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic
from genetic_code_tools import GENETIC_CODE, fold_codon_m, iter_fasta
from progress_tools import Heartbeat
from stats_tools import bh_fdr


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}

# Bump when analysis logic changes.
ANALYSIS_VERSION = 1
SCHEMA_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    d = root_dir() / "data" / "boundary_enrichment"
    d.mkdir(parents=True, exist_ok=True)
    return d


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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


def _as_int(x: object) -> int | None:
    try:
        return int(x)  # type: ignore[arg-type]
    except Exception:
        return None


def _log_choose(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1.0) - math.lgamma(k + 1.0) - math.lgamma(n - k + 1.0)


def _binom_pmf_log(n: int, k: int, p: float) -> float:
    if p < 0.0 or p > 1.0:
        return float("-inf")
    if n < 0:
        return float("-inf")
    if k < 0 or k > n:
        return float("-inf")
    if n == 0:
        return 0.0 if k == 0 else float("-inf")
    if p == 0.0:
        return 0.0 if k == 0 else float("-inf")
    if p == 1.0:
        return 0.0 if k == n else float("-inf")
    return _log_choose(n, k) + k * math.log(p) + (n - k) * math.log(1.0 - p)


def _logsumexp(log_terms: list[float]) -> float:
    if not log_terms:
        return float("-inf")
    m = max(log_terms)
    if m == float("-inf"):
        return float("-inf")
    s = 0.0
    for t in log_terms:
        s += math.exp(t - m)
    return m + math.log(s)


def binom_two_sided_p_value(*, n: int, k: int, p0: float) -> float | None:
    """
    Two-sided p-value using exact binomial tails:
      2 * min(P(X<=k), P(X>=k)).
    """
    n_i = int(n)
    k_i = int(k)
    if n_i < 1 or k_i < 0 or k_i > n_i:
        return None
    p = float(p0)
    if not (0.0 <= p <= 1.0):
        return None

    if p == 0.0:
        return 1.0 if k_i == 0 else 0.0
    if p == 1.0:
        return 1.0 if k_i == n_i else 0.0

    log_lo = [_binom_pmf_log(n_i, j, p) for j in range(0, k_i + 1)]
    lo = math.exp(_logsumexp(log_lo))
    log_hi = [_binom_pmf_log(n_i, j, p) for j in range(k_i, n_i + 1)]
    hi = math.exp(_logsumexp(log_hi))

    pv = 2.0 * min(lo, hi)
    if pv < 0.0:
        return 0.0
    if pv > 1.0:
        return 1.0
    return float(pv)


@dataclass(frozen=True)
class EnrichmentRow:
    dataset: str
    analysis_version: int
    m: int
    label: str
    method: str
    n_total: int
    n_subset: int
    boundary_rate_total: float | None
    boundary_rate_subset: float | None
    enrichment: float | None
    p: float | None
    q: float | None
    payload: dict[str, object]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fold_m boundary enrichment tests for annotation-aligned codon positions.")
    p.add_argument("--fasta", required=True, help="Input FASTA(.gz) file (DNA or RNA).")
    p.add_argument("--positions-tsv", required=True, help="TSV with columns: record_id, codon_index (0-based by default), optional label.")
    p.add_argument("--dataset", default="", help="Dataset label for outputs (default: derived from FASTA filename).")
    p.add_argument("--label", default="", help="Default label if TSV has no label column (default: derived from positions filename).")
    p.add_argument("--frame", type=int, default=0, choices=(0, 1, 2), help="Reading frame (0,1,2) used for codon_index.")
    p.add_argument("--codon-index-base", type=int, default=0, choices=(0, 1), help="Interpret codon_index as 0-based (default) or 1-based.")
    p.add_argument("--m-list", default="6,7,8,9", help="Comma-separated m values to evaluate.")
    p.add_argument("--heartbeat-s", type=float, default=60.0, help="Progress heartbeat seconds (0 disables).")
    p.add_argument("--no-latex", action="store_true", help="Do not write LaTeX fragments.")
    p.add_argument("--force", action="store_true", help="Force recomputation even if cached outputs exist.")
    p.add_argument("--out-summary-json", default=str(data_dir() / "foldm_boundary_enrichment_summary.json"), help="Output JSON summary path.")
    return p.parse_args()


def _read_positions(path: Path, *, codon_index_base: int, default_label: str) -> tuple[dict[str, dict[str, set[int]]], dict[str, int]]:
    """
    Return (positions_by_label, requested_counts_by_label).
      - positions_by_label[label][record_id] = set(codon_index0)
      - requested_counts_by_label[label] = number of TSV rows requested (including duplicates)
    """
    positions_by_label: dict[str, dict[str, set[int]]] = {}
    requested_counts: dict[str, int] = {}

    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f, delimiter="\t")
        if not r.fieldnames:
            raise SystemExit(f"Empty/invalid TSV (missing header): {path}")
        if "record_id" not in r.fieldnames:
            raise SystemExit(f"TSV missing required column 'record_id': {path}")
        if "codon_index" not in r.fieldnames:
            raise SystemExit(f"TSV missing required column 'codon_index': {path}")
        has_label = "label" in r.fieldnames

        for line_no, row in enumerate(r, start=2):
            rid = (row.get("record_id") or "").strip()
            if not rid:
                continue
            ci_raw = row.get("codon_index")
            ci = _as_int(ci_raw)
            if ci is None:
                raise SystemExit(f"Invalid codon_index at {path}:{line_no}: {ci_raw!r}")
            ci0 = int(ci) - 1 if int(codon_index_base) == 1 else int(ci)
            if ci0 < 0:
                continue

            lbl = (row.get("label") or "").strip() if has_label else ""
            if not lbl:
                lbl = str(default_label)

            requested_counts[lbl] = int(requested_counts.get(lbl, 0)) + 1
            positions_by_label.setdefault(lbl, {}).setdefault(rid, set()).add(int(ci0))

    if not positions_by_label:
        raise SystemExit(f"No usable positions found in TSV: {path}")
    return positions_by_label, requested_counts


def _parse_m_list(s: str) -> list[int]:
    ms: list[int] = []
    for part in str(s).split(","):
        part = part.strip()
        if not part:
            continue
        ms.append(int(part))
    ms = sorted({int(m) for m in ms if int(m) > 0})
    if not ms:
        raise SystemExit("--m-list must contain positive integers")
    return ms


def main() -> None:
    args = parse_args()
    fasta_path = Path(args.fasta).expanduser()
    pos_path = Path(args.positions_tsv).expanduser()
    if not fasta_path.exists():
        raise SystemExit(f"Missing FASTA: {fasta_path}")
    if not pos_path.exists():
        raise SystemExit(f"Missing positions TSV: {pos_path}")

    ms = _parse_m_list(str(args.m_list))

    dataset = str(args.dataset).strip() or fasta_path.stem
    default_label = str(args.label).strip() or pos_path.stem
    out_summary_json = Path(args.out_summary_json)

    positions_by_label, requested_counts = _read_positions(
        pos_path,
        codon_index_base=int(args.codon_index_base),
        default_label=default_label,
    )

    cache_key = {
        "analysis": "foldm_boundary_enrichment",
        "analysis_version": int(ANALYSIS_VERSION),
        "schema_version": int(SCHEMA_VERSION),
        "dataset": dataset,
        "default_label": default_label,
        "frame": int(args.frame),
        "codon_index_base": int(args.codon_index_base),
        "m_list": ms,
        "inputs": {
            "fasta": _fingerprint_file(fasta_path),
            "positions_tsv": _fingerprint_file(pos_path),
        },
        "mu_star": MU_STAR,
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    if (not args.force) and out_summary_json.exists() and cache_hit(out_summary_json, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_summary_json}", flush=True)
        if not args.no_latex:
            try:
                summary_cached = json.loads(out_summary_json.read_text(encoding="utf-8"))
            except Exception:
                summary_cached = None
            if not isinstance(summary_cached, dict):
                raise SystemExit("Cached foldm boundary enrichment summary JSON is malformed; rerun with --force.")
            _emit_latex_from_cached_summary(summary_cached)
        return

    # Precompute boundary indicator per (m,codon) under mu*.
    is_boundary: dict[int, dict[str, int]] = {}
    for m in ms:
        is_boundary[int(m)] = {}
        for codon in GENETIC_CODE:
            f = fold_codon_m(codon, MU_STAR, m=int(m))
            is_boundary[int(m)][codon] = int(f.is_boundary)

    hb = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress] foldm_boundary_enrichment")
    hb.force(f"start dataset={dataset} labels={len(positions_by_label)} m={','.join(str(x) for x in ms)} frame={int(args.frame)}")

    # Background totals and per-label subset counts, per m.
    n_total: dict[int, int] = {int(m): 0 for m in ms}
    k_total: dict[int, int] = {int(m): 0 for m in ms}
    subset_in_range: dict[str, int] = {lbl: 0 for lbl in positions_by_label}
    subset_out_of_range: dict[str, int] = {lbl: 0 for lbl in positions_by_label}
    subset_invalid_codon: dict[str, int] = {lbl: 0 for lbl in positions_by_label}
    subset_valid: dict[int, dict[str, int]] = {int(m): {lbl: 0 for lbl in positions_by_label} for m in ms}
    subset_boundary: dict[int, dict[str, int]] = {int(m): {lbl: 0 for lbl in positions_by_label} for m in ms}

    n_records = 0
    n_records_used = 0

    referenced_records: set[str] = set()
    for lbl, by_rec in positions_by_label.items():
        for rid in by_rec.keys():
            referenced_records.add(rid)
    hb.maybe(f"referenced_records={len(referenced_records)}")

    for rid, seq in iter_fasta(str(fasta_path)):
        n_records += 1
        hb.maybe(f"records={n_records} bg_n_m6={n_total.get(6,0)}")

        by_label_for_rid: dict[str, set[int]] = {}
        if rid in referenced_records:
            for lbl, by_rec in positions_by_label.items():
                s = by_rec.get(rid)
                if s:
                    by_label_for_rid[lbl] = s

        # Track per-record subset validity (set-based) for out-of-range/invalid diagnostics.
        valid_in_record: dict[str, int] = {lbl: 0 for lbl in by_label_for_rid} if by_label_for_rid else {}
        boundary_in_record: dict[int, dict[str, int]] = {int(m): {lbl: 0 for lbl in by_label_for_rid} for m in ms} if by_label_for_rid else {}

        codon_index = 0
        for pos in range(int(args.frame), len(seq) - 2, 3):
            codon = seq[pos : pos + 3]
            aa = GENETIC_CODE.get(codon)
            if aa is None or aa == "Stop":
                codon_index += 1
                continue

            # Background counts.
            for m in ms:
                b = int(is_boundary[int(m)].get(codon, 0))
                n_total[int(m)] += 1
                k_total[int(m)] += b

            if by_label_for_rid:
                for lbl, idx_set in by_label_for_rid.items():
                    if codon_index in idx_set:
                        valid_in_record[lbl] += 1
                        for m in ms:
                            boundary_in_record[int(m)][lbl] += int(is_boundary[int(m)].get(codon, 0))

            codon_index += 1

        if by_label_for_rid:
            n_records_used += 1
            for lbl, idx_set in by_label_for_rid.items():
                in_range = sum(1 for ci0 in idx_set if 0 <= ci0 < codon_index)
                out_range = sum(1 for ci0 in idx_set if ci0 >= codon_index)
                v = int(valid_in_record.get(lbl, 0))
                subset_in_range[lbl] += int(in_range)
                subset_out_of_range[lbl] += int(out_range)
                subset_invalid_codon[lbl] += int(in_range) - v
                for m in ms:
                    subset_valid[int(m)][lbl] += v
                    subset_boundary[int(m)][lbl] += int(boundary_in_record[int(m)].get(lbl, 0))

    hb.force(f"done records={n_records} referenced_records={len(referenced_records)}")

    if any(int(n_total[int(m)]) <= 0 for m in ms):
        raise SystemExit("No valid coding codons found in FASTA for the chosen frame.")

    # Build rows
    raw: list[dict[str, object]] = []
    for m in ms:
        p0 = k_total[int(m)] / float(n_total[int(m)])
        for lbl in sorted(positions_by_label.keys()):
            n_sub = int(subset_valid[int(m)].get(lbl, 0))
            x_sub = int(subset_boundary[int(m)].get(lbl, 0))
            rate_total = float(p0)
            rate_sub = (x_sub / float(n_sub)) if n_sub > 0 else None
            enrich = (rate_sub / rate_total) if (rate_sub is not None and rate_total > 0) else None
            p_val = binom_two_sided_p_value(n=n_sub, k=x_sub, p0=p0) if n_sub > 0 else None
            payload = {
                "dataset": dataset,
                "label": str(lbl),
                "m": int(m),
                "fasta": str(fasta_path),
                "positions_tsv": str(pos_path),
                "frame": int(args.frame),
                "codon_index_base": int(args.codon_index_base),
                "mu_star": MU_STAR,
                "counts": {
                    "records_seen": int(n_records),
                    "records_with_positions": int(n_records_used),
                    "background_total_codons": int(n_total[int(m)]),
                    "background_boundary_codons": int(k_total[int(m)]),
                    "positions_requested": int(requested_counts.get(lbl, 0)),
                    "positions_in_range": int(subset_in_range.get(lbl, 0)),
                    "positions_in_range_and_valid": int(n_sub),
                    "positions_boundary_hits": int(x_sub),
                    "positions_out_of_range": int(subset_out_of_range.get(lbl, 0)),
                    "positions_invalid_codon": int(subset_invalid_codon.get(lbl, 0)),
                },
            }
            raw.append(
                {
                    "dataset": str(dataset),
                    "analysis_version": int(ANALYSIS_VERSION),
                    "m": int(m),
                    "label": str(lbl),
                    "method": "binomial",
                    "n_total": int(n_total[int(m)]),
                    "n_subset": int(n_sub),
                    "boundary_rate_total": float(rate_total),
                    "boundary_rate_subset": (float(rate_sub) if rate_sub is not None else None),
                    "enrichment": (float(enrich) if enrich is not None else None),
                    "p": (float(p_val) if p_val is not None else None),
                    "q": None,
                    "payload": payload,
                }
            )

    # BH-FDR across all tests (labels × m) in this run.
    p_list: list[float] = []
    p_pos: list[int] = []
    for i, r in enumerate(raw):
        p = r.get("p")
        if p is None:
            continue
        try:
            p_list.append(float(p))
            p_pos.append(int(i))
        except Exception:
            continue
    q_list = bh_fdr(p_list) if p_list else []
    for j, i in enumerate(p_pos):
        raw[i]["q"] = float(q_list[j]) if j < len(q_list) else None

    rows: list[EnrichmentRow] = []
    for r in raw:
        try:
            rows.append(EnrichmentRow(**r))  # type: ignore[arg-type]
        except Exception:
            continue

    summary_obj: dict[str, object] = {
        "schema_version": int(SCHEMA_VERSION),
        "analysis_version": int(ANALYSIS_VERSION),
        "dataset": dataset,
        "frame": int(args.frame),
        "codon_index_base": int(args.codon_index_base),
        "m_list": ms,
        "mu_star": MU_STAR,
        "inputs": {
            "fasta": _fingerprint_file(fasta_path),
            "positions_tsv": _fingerprint_file(pos_path),
        },
        "background": {
            str(int(m)): {
                "n_total": int(n_total[int(m)]),
                "n_boundary": int(k_total[int(m)]),
                "p_boundary": float(k_total[int(m)] / float(n_total[int(m)])),
            }
            for m in ms
        },
        "rows": [r.__dict__ for r in rows],
    }
    out_summary_json.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_summary_json, summary_obj)
    write_json_atomic(cache_meta_path(out_summary_json), cache_meta)

    print("Wrote:", out_summary_json)
    if not args.no_latex:
        _emit_latex_from_cached_summary(summary_obj)


def _emit_latex_from_cached_summary(summary: dict[str, object]) -> None:
    rows0 = summary.get("rows") or []
    if not isinstance(rows0, list):
        raise SystemExit("Cached summary is missing rows.")

    dataset = str(summary.get("dataset") or "-")
    ms0 = summary.get("m_list") or []
    ms = [int(x) for x in ms0] if isinstance(ms0, list) else []
    bg = summary.get("background") or {}
    if not isinstance(bg, dict):
        bg = {}

    # Summary paragraph
    parts: list[str] = []
    for m in sorted(ms):
        b = bg.get(str(int(m))) or {}
        if not isinstance(b, dict):
            continue
        p0 = b.get("p_boundary")
        n_total = b.get("n_total")
        k_total = b.get("n_boundary")
        try:
            parts.append(
                f"$m={int(m)}: \\widehat{{p}}_B={(float(p0) if p0 is not None else float('nan')):.5f}$ "
                f"({int(k_total or 0)}/{int(n_total or 0)})"
            )
        except Exception:
            continue
    s_line = (
        "Fold$_m$ boundary enrichment tests under $\\mu^\\ast$ on dataset "
        f"\\path{{{dataset}}} (coding codons only; stops excluded): "
        + "; ".join(parts)
        + "."
    )
    write_text(generated_dir() / "foldm_boundary_enrichment_summary.tex", s_line + "\n")

    # Table rows: m, label, n, boundary rate, enrichment, p, q
    def _fmt(x: object, nd: int = 5) -> str:
        if x is None:
            return "-"
        try:
            v = float(x)
        except Exception:
            return "-"
        if math.isnan(v):
            return "-"
        if abs(v) >= 1e4 or (abs(v) > 0 and abs(v) < 1e-3):
            return f"{v:.2e}"
        return f"{v:.{int(nd)}f}"

    def _fmt_p(x: object) -> str:
        if x is None:
            return "-"
        try:
            v = float(x)
        except Exception:
            return "-"
        if math.isnan(v):
            return "-"
        if v == 0.0:
            return "<1e-300"
        if v < 1e-4:
            return f"{v:.2e}"
        return f"{v:.4f}"

    out_lines: list[str] = []
    out_lines.append("Fold$_m$ boundary enrichment tests (binomial; BH-FDR over all labels and $m$ in this run).")
    out_lines.append("")
    out_lines.append("\\begingroup")
    out_lines.append("\\hbadness=10000")
    out_lines.append("\\scriptsize")
    out_lines.append("\\setlength{\\tabcolsep}{4pt}")
    out_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    out_lines.append("\\setlength{\\LTleft}{0pt}")
    out_lines.append("\\setlength{\\LTright}{0pt}")
    out_lines.append("\\begin{longtable}{r l r r r r r}")
    out_lines.append("\\toprule")
    out_lines.append("$m$ & label & $n$ & boundary rate & enrichment & $p$ & $q$ \\\\")
    out_lines.append("\\midrule")

    # Sort deterministically by (m, label)
    typed: list[dict[str, object]] = []
    for r in rows0:
        if isinstance(r, dict):
            typed.append(r)
    typed.sort(key=lambda d: (int(d.get("m") or 0), str(d.get("label") or "")))

    for r in typed:
        m = int(r.get("m") or 0)
        label = str(r.get("label") or "-").replace("_", "\\_")
        n = int(r.get("n_subset") or 0)
        rate = r.get("boundary_rate_subset")
        enrich = r.get("enrichment")
        p = r.get("p")
        q = r.get("q")
        out_lines.append(f"{m} & {label} & {n} & {_fmt(rate, nd=5)} & {_fmt(enrich, nd=3)} & {_fmt_p(p)} & {_fmt_p(q)} \\\\")

    out_lines.append("\\bottomrule")
    out_lines.append("\\end{longtable}")
    out_lines.append("\\endgroup")
    out_lines.append("")
    write_text(generated_dir() / "foldm_boundary_enrichment_table.tex", "\n".join(out_lines) + "\n")


if __name__ == "__main__":
    main()


