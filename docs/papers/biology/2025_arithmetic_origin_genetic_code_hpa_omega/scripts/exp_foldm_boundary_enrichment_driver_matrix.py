# -*- coding: utf-8 -*-
"""
Fold_m boundary enrichment: compact cross-m driver matrix (standard library only).

For each label-defined subset of codon positions, and for each m:
  total diff:     p_sub - p_B
  syn(sub):       p_sub - p_null_sub
  AA(comp):       p_null_sub - p_null_B
  syn(bg):        p_null_B - p_B        (label-independent; depends only on background corpus)

We also report the top-K amino-acid contributors (by |contrib|) for:
  - syn(sub) component (from AA-preserving null decomposition)
  - AA(comp) component (from AA-frequency difference times uniform-within-AA boundary means)

Dataset (default):
  - data/boundary_enrichment/recoding_cds_orfs.fasta.gz
  - data/boundary_enrichment/recoding_site_sets.tsv

Outputs:
  - sections/generated/foldm_boundary_enrichment_driver_matrix_summary.tex
  - sections/generated/foldm_boundary_enrichment_driver_matrix_table.tex
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import GENETIC_CODE, fold_codon_m, iter_fasta
from stats_tools import aa_preserving_null_decomposition


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
SCRIPT_VERSION = 2


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


def _fmt_float(x: object, *, nd: int = 6) -> str:
    if not _is_num(x):
        return "-"
    return f"{float(x):.{int(nd)}f}"


def _fmt_float_signed(x: object, *, nd: int = 6) -> str:
    if not _is_num(x):
        return "-"
    v = float(x)
    s = f"{v:.{int(nd)}f}"
    return s if s.startswith("-") else ("+" + s)


def _fmt_driver_list(items: list[tuple[str, float]], *, k: int, nd: int = 4) -> str:
    # items: [(AA, contrib)], already sorted by |contrib| desc.
    parts: list[str] = []
    for aa, c in items[: int(k)]:
        parts.append(f"{aa}({_fmt_float_signed(c, nd=nd)})")
    return ", ".join(parts) if parts else "-"


def codons_by_aa_standard() -> dict[str, list[str]]:
    d: dict[str, list[str]] = defaultdict(list)
    for codon, aa in GENETIC_CODE.items():
        d[str(aa)].append(str(codon))
    for aa in d:
        d[aa].sort()
    return dict(d)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fold_m boundary enrichment cross-m driver matrix.")
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
    p.add_argument("--top-k", type=int, default=3, help="Top-k AA drivers listed for syn(sub) and AA(comp).")
    p.add_argument(
        "--out-summary",
        default=str(generated_dir() / "foldm_boundary_enrichment_driver_matrix_summary.tex"),
        help="Output LaTeX summary fragment path.",
    )
    p.add_argument(
        "--out-table",
        default=str(generated_dir() / "foldm_boundary_enrichment_driver_matrix_table.tex"),
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
        "analysis": "foldm_boundary_enrichment_driver_matrix",
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

    coding_codons = [c for c, aa in GENETIC_CODE.items() if aa != "Stop"]
    codons_by_aa = codons_by_aa_standard()

    # Boundary indicator per m and codon (coding only), plus uniform-within-AA mean.
    codon_value_by_m: dict[int, dict[str, float]] = {}
    aa_mean_by_m: dict[int, dict[str, float]] = {}
    for m in m_list:
        cv = {c: float(fold_codon_m(c, MU_STAR, m=int(m)).is_boundary) for c in coding_codons}
        codon_value_by_m[int(m)] = cv
        aa_mean: dict[str, float] = {}
        for aa, syn in codons_by_aa.items():
            if aa == "Stop":
                continue
            vals = [float(cv[c]) for c in syn if c in cv]
            aa_mean[str(aa)] = (sum(vals) / float(len(vals))) if vals else 0.0
        aa_mean_by_m[int(m)] = aa_mean

    # Background and subset counts.
    bg_codon_counts: Counter[str] = Counter()
    bg_aa_counts: Counter[str] = Counter()
    bg_n = 0

    sub_codon_counts: dict[str, Counter[str]] = {lbl: Counter() for lbl in positions_by_label}
    sub_aa_counts: dict[str, Counter[str]] = {lbl: Counter() for lbl in positions_by_label}
    sub_n: dict[str, int] = {lbl: 0 for lbl in positions_by_label}

    referenced_records: set[str] = set()
    for lbl, by_rec in positions_by_label.items():
        referenced_records.update(by_rec.keys())

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

            bg_codon_counts[codon] += 1
            bg_aa_counts[str(aa)] += 1
            bg_n += 1

            if by_label_for_rid:
                for lbl, idx_set in by_label_for_rid.items():
                    if codon_index in idx_set:
                        sub_codon_counts[lbl][codon] += 1
                        sub_aa_counts[lbl][str(aa)] += 1
                        sub_n[lbl] += 1

            codon_index += 1

    if bg_n <= 0:
        raise SystemExit("No valid coding codons found in FASTA.")

    # Background observed boundary rate per m.
    bg_p: dict[int, float] = {}
    for m in m_list:
        hits = 0.0
        for c in coding_codons:
            hits += float(bg_codon_counts.get(c, 0)) * float(codon_value_by_m[int(m)][c])
        bg_p[int(m)] = float(hits) / float(bg_n)

    # Background AA-preserving null mean per m.
    bg_null_p: dict[int, float] = {}
    bg_decomp_by_m: dict[int, object] = {}
    for m in m_list:
        de_bg = aa_preserving_null_decomposition(
            aa_counts={k: int(v) for k, v in bg_aa_counts.items()},
            codon_counts={k: int(v) for k, v in bg_codon_counts.items()},
            codons_by_aa=codons_by_aa,
            genetic_code=GENETIC_CODE,
            codon_value=codon_value_by_m[int(m)],
            exclude_aas={"Stop"},
        )
        bg_decomp_by_m[int(m)] = de_bg
        bg_null_p[int(m)] = float(de_bg.null_mean)  # type: ignore[attr-defined]

    # Background AA frequencies for AA(comp) contributions.
    bg_total_aa = float(sum(int(v) for aa, v in bg_aa_counts.items() if aa != "Stop"))
    bg_freq_aa = {aa: (float(bg_aa_counts.get(aa, 0)) / bg_total_aa if bg_total_aa > 0 else 0.0) for aa in codons_by_aa if aa != "Stop"}

    # Summary.
    m_str = ",".join(str(int(x)) for x in m_list)
    s_line = (
        "Fold$_m$ cross-resolution driver matrix for recoding-window boundary enrichment "
        f"(top-{top_k} AA drivers for syn(sub) and AA(comp); $m\\in\\{{{m_str}\\}}$; background $n={bg_n}$ coding codons)."
    )
    write_text_atomic(out_summary, s_line + "\n")

    # Table.
    rows: list[dict[str, object]] = []
    for lbl in sorted(sub_codon_counts.keys()):
        n_sub = int(sub_n.get(lbl, 0))
        if n_sub <= 0:
            continue
        sub_total_aa = float(sum(int(v) for aa, v in sub_aa_counts[lbl].items() if aa != "Stop"))
        sub_freq = {aa: (float(sub_aa_counts[lbl].get(aa, 0)) / sub_total_aa if sub_total_aa > 0 else 0.0) for aa in bg_freq_aa.keys()}
        for m in m_list:
            de_sub = aa_preserving_null_decomposition(
                aa_counts={k: int(v) for k, v in sub_aa_counts[lbl].items()},
                codon_counts={k: int(v) for k, v in sub_codon_counts[lbl].items()},
                codons_by_aa=codons_by_aa,
                genetic_code=GENETIC_CODE,
                codon_value=codon_value_by_m[int(m)],
                exclude_aas={"Stop"},
            )
            p_sub = float(de_sub.obs_mean)  # type: ignore[attr-defined]
            p_null_sub = float(de_sub.null_mean)  # type: ignore[attr-defined]
            p_bg = float(bg_p[int(m)])
            p_null_bg = float(bg_null_p[int(m)])

            diff_total = p_sub - p_bg
            syn_sub = p_sub - p_null_sub
            aa_comp = p_null_sub - p_null_bg
            syn_bg = p_null_bg - p_bg

            # syn(sub) AA drivers from decomposition (already obs-null; contributions sum to syn_sub).
            aa_contribs_synsub = [(str(r.aa), float(r.contrib)) for r in list(de_sub.aa_contribs)]  # type: ignore[attr-defined]
            aa_contribs_synsub.sort(key=lambda x: abs(x[1]), reverse=True)

            # AA(comp) AA drivers from freq difference * mean boundary-within-AA.
            aa_contribs_aacomp: list[tuple[str, float]] = []
            for aa in bg_freq_aa.keys():
                mean_b = float(aa_mean_by_m[int(m)].get(aa, 0.0))
                contrib = (float(sub_freq.get(aa, 0.0)) - float(bg_freq_aa.get(aa, 0.0))) * mean_b
                aa_contribs_aacomp.append((aa, float(contrib)))
            aa_contribs_aacomp.sort(key=lambda x: abs(x[1]), reverse=True)

            rows.append(
                {
                    "m": int(m),
                    "label": str(lbl),
                    "n": int(n_sub),
                    "diff_total": float(diff_total),
                    "syn_sub": float(syn_sub),
                    "syn_sub_drivers": _fmt_driver_list(aa_contribs_synsub, k=top_k, nd=4),
                    "aa_comp": float(aa_comp),
                    "aa_comp_drivers": _fmt_driver_list(aa_contribs_aacomp, k=top_k, nd=4),
                    "syn_bg": float(syn_bg),
                }
            )

    rows.sort(key=lambda r: (int(r["m"]), str(r["label"])))

    lines: list[str] = []
    lines.append("\\begingroup")
    lines.append("\\hbadness=10000")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{2pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\setlength{\\LTleft}{0pt}")
    lines.append("\\setlength{\\LTright}{0pt}")
    lines.append(
        "\\begin{longtable}{r >{\\raggedright\\arraybackslash}p{1.9cm} r r "
        ">{\\raggedright\\arraybackslash}p{3.7cm} r >{\\raggedright\\arraybackslash}p{3.7cm} r}"
    )
    lines.append("\\toprule")
    lines.append("$m$ & label & $n$ & total & syn(sub) drivers & AA(comp) & AA drivers & syn(bg) \\\\")
    lines.append("\\midrule")
    for r in rows:
        lbl = str(r["label"])
        # Allow wrapping in narrow table columns: insert discretionary breaks after "_" and ":".
        lbl = lbl.replace("_", "\\_\\allowbreak{}").replace(":", ":\\allowbreak{}")
        syn_sub = str(r["syn_sub_drivers"]).replace("_", "\\_")
        aa_comp_dr = str(r["aa_comp_drivers"]).replace("_", "\\_")
        lines.append(
            f"{int(r['m'])} & {lbl} & {int(r['n'])} & "
            f"{_fmt_float_signed(r['diff_total'], nd=6)} & {syn_sub} & "
            f"{_fmt_float_signed(r['aa_comp'], nd=6)} & {aa_comp_dr} & "
            f"{_fmt_float_signed(r['syn_bg'], nd=6)} \\\\"
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


