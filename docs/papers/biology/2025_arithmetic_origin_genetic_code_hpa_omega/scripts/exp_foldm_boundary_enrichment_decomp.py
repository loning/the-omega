# -*- coding: utf-8 -*-
"""
Fold_m boundary enrichment: codon-level contribution decomposition (standard library only).

Purpose:
  The Fold_m boundary enrichment table reports enrichment ratios by label and m.
  This script decomposes the boundary-rate difference (subset minus background)
  into codon-level contributions to help explain sign flips across m.

Dataset (default):
  - data/boundary_enrichment/recoding_cds_orfs.fasta.gz
  - data/boundary_enrichment/recoding_site_sets.tsv

Outputs (LaTeX fragments):
  - sections/generated/foldm_boundary_enrichment_decomp_summary.tex
  - sections/generated/foldm_boundary_enrichment_decomp_codon_top.tex
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import GENETIC_CODE, fold_codon_m, iter_fasta


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
SCRIPT_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


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


def _parse_int_list(s: str) -> list[int]:
    out: list[int] = []
    for p in str(s or "").split(","):
        p = p.strip()
        if not p:
            continue
        out.append(int(p))
    out = sorted({int(x) for x in out if int(x) > 0})
    if not out:
        raise SystemExit("--m-list must contain positive integers")
    return out


def _read_positions(path: Path, *, codon_index_base: int) -> dict[str, dict[str, set[int]]]:
    """
    Return positions_by_label[label][record_id] = set(codon_index0).
    """
    positions_by_label: dict[str, dict[str, set[int]]] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f, delimiter="\t")
        if not r.fieldnames:
            raise SystemExit(f"Empty/invalid TSV (missing header): {path}")
        if "record_id" not in r.fieldnames or "codon_index" not in r.fieldnames:
            raise SystemExit(f"TSV missing required columns: {path}")
        has_label = "label" in r.fieldnames
        for line_no, row in enumerate(r, start=2):
            rid = (row.get("record_id") or "").strip()
            if not rid:
                continue
            ci = _as_int(row.get("codon_index"))
            if ci is None:
                raise SystemExit(f"Invalid codon_index at {path}:{line_no}")
            ci0 = int(ci) - 1 if int(codon_index_base) == 1 else int(ci)
            if ci0 < 0:
                continue
            lbl = (row.get("label") or "").strip() if has_label else ""
            if not lbl:
                lbl = "default"
            positions_by_label.setdefault(lbl, {}).setdefault(rid, set()).add(int(ci0))
    if not positions_by_label:
        raise SystemExit(f"No usable positions found in TSV: {path}")
    return positions_by_label


def _is_num(x: object) -> bool:
    try:
        v = float(x)  # type: ignore[arg-type]
    except Exception:
        return False
    return (not math.isnan(v)) and math.isfinite(v)


def _fmt_signed(x: object, *, nd: int = 6) -> str:
    if not _is_num(x):
        return "-"
    v = float(x)
    s = f"{v:.{int(nd)}f}"
    return s if s.startswith("-") else ("+" + s)


def _fmt_prob(x: object, *, nd: int = 5) -> str:
    if not _is_num(x):
        return "-"
    return f"{float(x):.{int(nd)}f}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fold_m boundary enrichment decomposition (codon contributions).")
    p.add_argument(
        "--fasta",
        default=str(root_dir() / "data" / "boundary_enrichment" / "recoding_cds_orfs.fasta.gz"),
        help="Input FASTA(.gz) (DNA or RNA).",
    )
    p.add_argument(
        "--positions-tsv",
        default=str(root_dir() / "data" / "boundary_enrichment" / "recoding_site_sets.tsv"),
        help="TSV with record_id, codon_index, label.",
    )
    p.add_argument("--frame", type=int, default=0, choices=(0, 1, 2), help="Frame used for codon_index.")
    p.add_argument("--codon-index-base", type=int, default=0, choices=(0, 1), help="Interpret codon_index as 0-based or 1-based.")
    p.add_argument("--m-list", default="6,7,8,9", help="Comma-separated m values.")
    p.add_argument("--top-k", type=int, default=10, help="Top-k codons by absolute contribution per (label,m).")
    p.add_argument(
        "--out-summary",
        default=str(generated_dir() / "foldm_boundary_enrichment_decomp_summary.tex"),
        help="Output LaTeX summary fragment path.",
    )
    p.add_argument(
        "--out-table",
        default=str(generated_dir() / "foldm_boundary_enrichment_decomp_codon_top.tex"),
        help="Output LaTeX table fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    fasta_path = Path(args.fasta).expanduser()
    pos_path = Path(args.positions_tsv).expanduser()
    if not fasta_path.exists():
        raise SystemExit(f"Missing FASTA: {fasta_path}")
    if not pos_path.exists():
        raise SystemExit(f"Missing positions TSV: {pos_path}")

    m_list = _parse_int_list(str(args.m_list))
    top_k = int(args.top_k)
    if top_k < 1:
        raise SystemExit("--top-k must be >= 1")

    out_summary = Path(args.out_summary)
    out_table = Path(args.out_table)

    positions_by_label = _read_positions(pos_path, codon_index_base=int(args.codon_index_base))

    cache_key = {
        "analysis": "foldm_boundary_enrichment_decomp",
        "version": int(SCRIPT_VERSION),
        "m_list": [int(x) for x in m_list],
        "top_k": int(top_k),
        "frame": int(args.frame),
        "codon_index_base": int(args.codon_index_base),
        "inputs": {
            "fasta": _fingerprint_file(fasta_path),
            "positions_tsv": _fingerprint_file(pos_path),
        },
        "mu_star": MU_STAR,
        "out_summary": str(out_summary),
        "out_table": str(out_table),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_table, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_table}", flush=True)
        return

    # Boundary indicator per m and codon.
    is_bdry: dict[int, dict[str, int]] = {}
    for m in m_list:
        is_bdry[int(m)] = {}
        for codon in GENETIC_CODE:
            is_bdry[int(m)][codon] = int(fold_codon_m(codon, MU_STAR, m=int(m)).is_boundary)

    # Background counts over all coding codons (exclude stops).
    bg_counts: Counter[str] = Counter()
    bg_n = 0

    # Subset counts per label.
    subset_counts: dict[str, Counter[str]] = {lbl: Counter() for lbl in positions_by_label}
    subset_n: dict[str, int] = {lbl: 0 for lbl in positions_by_label}

    referenced_records: set[str] = set()
    for lbl, by_rec in positions_by_label.items():
        for rid in by_rec.keys():
            referenced_records.add(rid)

    for rid, seq in iter_fasta(str(fasta_path)):
        by_label_for_rid: dict[str, set[int]] = {}
        if rid in referenced_records:
            for lbl, by_rec in positions_by_label.items():
                s = by_rec.get(rid)
                if s:
                    by_label_for_rid[lbl] = s

        codon_index = 0
        for pos in range(int(args.frame), len(seq) - 2, 3):
            codon = seq[pos : pos + 3]
            aa = GENETIC_CODE.get(codon)
            if aa is None or aa == "Stop":
                codon_index += 1
                continue

            bg_counts[codon] += 1
            bg_n += 1

            if by_label_for_rid:
                for lbl, idx_set in by_label_for_rid.items():
                    if codon_index in idx_set:
                        subset_counts[lbl][codon] += 1
                        subset_n[lbl] += 1

            codon_index += 1

    if bg_n <= 0:
        raise SystemExit("No valid coding codons found in FASTA.")

    coding_codons = [c for c, aa in GENETIC_CODE.items() if aa != "Stop"]
    bg_freq = {c: (float(bg_counts.get(c, 0)) / float(bg_n)) for c in coding_codons}

    # Background boundary rates per m.
    bg_bdry_rate: dict[int, float] = {}
    for m in m_list:
        hits = sum(int(is_bdry[int(m)].get(c, 0)) * int(bg_counts.get(c, 0)) for c in coding_codons)
        bg_bdry_rate[int(m)] = float(hits) / float(bg_n)

    summary_line = (
        "Fold$_m$ boundary enrichment decomposition on recoding-ORF dataset "
        f"(background $n={bg_n}$ coding codons; "
        + "; ".join([f"$m={int(m)}$: $\\widehat{{p}}_B={bg_bdry_rate[int(m)]:.5f}$" for m in m_list])
        + ")."
    )
    write_text_atomic(out_summary, summary_line + "\n")

    # Contribution rows.
    # Contribution of codon c to (subset boundary rate - background boundary rate):
    #   (p_sub(c) - p_bg(c)) * 1{boundary_m(c)}.
    out_rows: list[tuple[int, str, str, str, int, int, float, float]] = []
    for lbl in sorted(subset_counts.keys()):
        n_sub = int(subset_n.get(lbl, 0))
        if n_sub <= 0:
            continue
        sub_freq = {c: (float(subset_counts[lbl].get(c, 0)) / float(n_sub)) for c in coding_codons}
        for m in m_list:
            contribs: list[tuple[str, float]] = []
            for c in coding_codons:
                if int(is_bdry[int(m)].get(c, 0)) != 1:
                    continue
                d = float(sub_freq.get(c, 0.0) - bg_freq.get(c, 0.0))
                contribs.append((c, d))
            contribs.sort(key=lambda x: abs(x[1]), reverse=True)
            for c, d in contribs[:top_k]:
                out_rows.append(
                    (
                        int(m),
                        str(lbl),
                        str(c),
                        str(GENETIC_CODE.get(c) or "-"),
                        int(n_sub),
                        int(subset_counts[lbl].get(c, 0)),
                        float(sub_freq.get(c, 0.0)),
                        float(d),
                    )
                )

    lines: list[str] = []
    lines.append("Codon-level contributions to Fold$_m$ boundary enrichment differences (subset minus background; top-$k$ by $|\\Delta p|$).")
    lines.append("")
    lines.append("\\begingroup")
    lines.append("\\hbadness=10000")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{4pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\setlength{\\LTleft}{0pt}")
    lines.append("\\setlength{\\LTright}{0pt}")
    lines.append("\\begin{longtable}{r l l l r r r r}")
    lines.append("\\toprule")
    lines.append("$m$ & label & codon & AA & $n$ & $c_{\\mathrm{sub}}$ & $p_{\\mathrm{sub}}$ & $\\Delta p$ \\\\")
    lines.append("\\midrule")
    for m, lbl, codon, aa, n_sub, c_sub, p_sub, d in out_rows:
        lines.append(
            f"{m} & {lbl.replace('_','\\_')} & {codon} & {aa} & {n_sub} & {c_sub} & {_fmt_prob(p_sub, nd=5)} & {_fmt_signed(d, nd=6)} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{longtable}")
    lines.append("\\endgroup")
    lines.append("")

    write_text_atomic(out_table, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_table), cache_meta)
    print("Wrote:", out_summary)
    print("Wrote:", out_table)


if __name__ == "__main__":
    main()


