# -*- coding: utf-8 -*-
"""
Fold_m boundary enrichment: AA-level driver tables (standard library only).

This script complements:
  - foldm_boundary_enrichment_aa_decomp_table.tex (scalar component decomposition)
by identifying which amino-acid groups contribute most to each component.

Components (for a label-defined subset of codon positions):
  - syn(sub):     p_sub - p_null_sub
  - AA:           p_null_sub - p_null_bg
  - syn(bg):      p_null_bg - p_bg

We report top-k amino acids by absolute contribution for:
  - syn(sub) per (label,m)
  - AA term per (label,m)
  - syn(bg) per m (background only)

Dataset (default):
  - data/boundary_enrichment/recoding_cds_orfs.fasta.gz
  - data/boundary_enrichment/recoding_site_sets.tsv

Outputs:
  - sections/generated/foldm_boundary_enrichment_aa_drivers_summary.tex
  - sections/generated/foldm_boundary_enrichment_aa_drivers_synsub_aa_top.tex
  - sections/generated/foldm_boundary_enrichment_aa_drivers_aacomp_aa_top.tex
  - sections/generated/foldm_boundary_enrichment_aa_drivers_synbg_aa_top.tex
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


def codons_by_aa_standard() -> dict[str, list[str]]:
    d: dict[str, list[str]] = defaultdict(list)
    for codon, aa in GENETIC_CODE.items():
        d[str(aa)].append(str(codon))
    for aa in d:
        d[aa].sort()
    return dict(d)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fold_m boundary enrichment AA driver tables (top AA contributors).")
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
    p.add_argument("--top-k", type=int, default=5, help="Top-k AAs by |contrib|.")
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

    out_summary = generated_dir() / "foldm_boundary_enrichment_aa_drivers_summary.tex"
    out_synsub = generated_dir() / "foldm_boundary_enrichment_aa_drivers_synsub_aa_top.tex"
    out_aacomp = generated_dir() / "foldm_boundary_enrichment_aa_drivers_aacomp_aa_top.tex"
    out_synbg = generated_dir() / "foldm_boundary_enrichment_aa_drivers_synbg_aa_top.tex"

    positions_by_label = _read_positions(pos_path, codon_index_base=int(args.codon_index_base))

    cache_key = {
        "analysis": "foldm_boundary_enrichment_aa_drivers",
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
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_synsub, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_synsub}", flush=True)
        return

    coding_codons = [c for c, aa in GENETIC_CODE.items() if aa != "Stop"]
    codons_by_aa = codons_by_aa_standard()

    # Boundary indicator per m (codon_value for null decomposition).
    codon_value_by_m: dict[int, dict[str, float]] = {}
    # Mean boundary rate within AA under uniform synonyms.
    aa_bdry_mean_by_m: dict[int, dict[str, float]] = {}
    for m in m_list:
        cv = {c: float(fold_codon_m(c, MU_STAR, m=int(m)).is_boundary) for c in coding_codons}
        codon_value_by_m[int(m)] = cv
        aa_mean: dict[str, float] = {}
        for aa, syn in codons_by_aa.items():
            if aa == "Stop":
                continue
            vals = [float(cv[c]) for c in syn if c in cv]
            aa_mean[str(aa)] = (sum(vals) / float(len(vals))) if vals else 0.0
        aa_bdry_mean_by_m[int(m)] = aa_mean

    # Background counts.
    bg_codon_counts: Counter[str] = Counter()
    bg_aa_counts: Counter[str] = Counter()
    bg_n = 0

    # Subset counts.
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

    # Background null decomposition for syn(bg) AA contributions.
    bg_decomp_by_m: dict[int, object] = {}
    for m in m_list:
        bg_decomp_by_m[int(m)] = aa_preserving_null_decomposition(
            aa_counts={k: int(v) for k, v in bg_aa_counts.items()},
            codon_counts={k: int(v) for k, v in bg_codon_counts.items()},
            codons_by_aa=codons_by_aa,
            genetic_code=GENETIC_CODE,
            codon_value=codon_value_by_m[int(m)],
            exclude_aas={"Stop"},
        )

    # Summary
    m_str = ",".join(str(int(x)) for x in m_list)
    s_line = (
        "Fold$_m$ AA-level driver tables for boundary enrichment components "
        f"(top-{top_k} by $|\\mathrm{{contrib}}|$; $m\\in\\{{{m_str}\\}}$; background $n={bg_n}$ coding codons)."
    )
    write_text_atomic(out_summary, s_line + "\n")

    # ---- syn(sub): top AA contributors to p_sub - p_null_sub ----
    synsub_lines: list[str] = []
    synsub_lines.append("Top amino-acid contributors to the subset synonymous component $p_{\\mathrm{sub}}-p^{\\mathrm{null}}_{\\mathrm{sub}}$ (Fold$_m$ boundary indicator).")
    synsub_lines.append("")
    synsub_lines.append("\\begingroup")
    synsub_lines.append("\\hbadness=10000")
    synsub_lines.append("\\scriptsize")
    synsub_lines.append("\\setlength{\\tabcolsep}{4pt}")
    synsub_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    synsub_lines.append("\\setlength{\\LTleft}{0pt}")
    synsub_lines.append("\\setlength{\\LTright}{0pt}")
    synsub_lines.append("\\begin{longtable}{r l l r r r r}")
    synsub_lines.append("\\toprule")
    synsub_lines.append("$m$ & label & AA & $n$ & $p_{\\mathrm{obs}|AA}$ & $p_{\\mathrm{null}|AA}$ & contrib \\\\")
    synsub_lines.append("\\midrule")
    for lbl in sorted(sub_codon_counts.keys()):
        n_sub = int(sub_n.get(lbl, 0))
        if n_sub <= 0:
            continue
        for m in m_list:
            de_sub = aa_preserving_null_decomposition(
                aa_counts={k: int(v) for k, v in sub_aa_counts[lbl].items()},
                codon_counts={k: int(v) for k, v in sub_codon_counts[lbl].items()},
                codons_by_aa=codons_by_aa,
                genetic_code=GENETIC_CODE,
                codon_value=codon_value_by_m[int(m)],
                exclude_aas={"Stop"},
            )
            # type: ignore[attr-defined]
            aa_contribs = list(de_sub.aa_contribs)  # type: ignore[attr-defined]
            top = aa_contribs[: int(top_k)]
            for r in top:
                lbl_escaped = str(lbl).replace("_", "\\_")
                synsub_lines.append(
                    f"{int(m)} & {lbl_escaped} & {str(r.aa)} & {int(r.n)} & "
                    f"{_fmt_float(r.obs_mean, nd=5)} & {_fmt_float(r.null_mean, nd=5)} & {_fmt_float_signed(r.contrib, nd=6)} \\\\"
                )
    synsub_lines.append("\\bottomrule")
    synsub_lines.append("\\end{longtable}")
    synsub_lines.append("\\endgroup")
    synsub_lines.append("")
    write_text_atomic(out_synsub, "\n".join(synsub_lines) + "\n")
    write_json_atomic(cache_meta_path(out_synsub), cache_meta)

    # ---- AA composition term: top AA contributors to p_null_sub - p_null_bg ----
    # contribution_aa = (freq_sub_aa - freq_bg_aa) * mean_boundary_within_aa(m)
    bg_total = float(sum(int(v) for aa, v in bg_aa_counts.items() if aa != "Stop"))
    bg_freq_aa = {aa: (float(bg_aa_counts.get(aa, 0)) / bg_total if bg_total > 0 else 0.0) for aa in codons_by_aa if aa != "Stop"}

    aacomp_lines: list[str] = []
    aacomp_lines.append("Top amino-acid contributors to the AA-composition component $p^{\\mathrm{null}}_{\\mathrm{sub}}-p^{\\mathrm{null}}_B$ (Fold$_m$ boundary indicator).")
    aacomp_lines.append("")
    aacomp_lines.append("\\begingroup")
    aacomp_lines.append("\\hbadness=10000")
    aacomp_lines.append("\\scriptsize")
    aacomp_lines.append("\\setlength{\\tabcolsep}{4pt}")
    aacomp_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    aacomp_lines.append("\\setlength{\\LTleft}{0pt}")
    aacomp_lines.append("\\setlength{\\LTright}{0pt}")
    aacomp_lines.append("\\begin{longtable}{r l l r r r r r}")
    aacomp_lines.append("\\toprule")
    aacomp_lines.append("$m$ & label & AA & $n$ & $f_{\\mathrm{sub}}$ & $f_B$ & $\\mathbb{E}[B|AA]$ & contrib \\\\")
    aacomp_lines.append("\\midrule")
    for lbl in sorted(sub_aa_counts.keys()):
        n_sub = int(sub_n.get(lbl, 0))
        if n_sub <= 0:
            continue
        sub_total = float(sum(int(v) for aa, v in sub_aa_counts[lbl].items() if aa != "Stop"))
        sub_freq = {aa: (float(sub_aa_counts[lbl].get(aa, 0)) / sub_total if sub_total > 0 else 0.0) for aa in bg_freq_aa.keys()}
        for m in m_list:
            contribs: list[tuple[str, float]] = []
            for aa in bg_freq_aa.keys():
                mean_b = float(aa_bdry_mean_by_m[int(m)].get(aa, 0.0))
                contrib = (float(sub_freq.get(aa, 0.0)) - float(bg_freq_aa.get(aa, 0.0))) * mean_b
                contribs.append((aa, float(contrib)))
            contribs.sort(key=lambda x: abs(x[1]), reverse=True)
            for aa, contrib in contribs[: int(top_k)]:
                n_aa = int(sub_aa_counts[lbl].get(aa, 0))
                lbl_escaped = str(lbl).replace("_", "\\_")
                aacomp_lines.append(
                    f"{int(m)} & {lbl_escaped} & {aa} & {n_aa} & "
                    f"{_fmt_float(sub_freq.get(aa, 0.0), nd=5)} & {_fmt_float(bg_freq_aa.get(aa, 0.0), nd=5)} & "
                    f"{_fmt_float(aa_bdry_mean_by_m[int(m)].get(aa, 0.0), nd=5)} & {_fmt_float_signed(contrib, nd=6)} \\\\"
                )
    aacomp_lines.append("\\bottomrule")
    aacomp_lines.append("\\end{longtable}")
    aacomp_lines.append("\\endgroup")
    aacomp_lines.append("")
    write_text_atomic(out_aacomp, "\n".join(aacomp_lines) + "\n")
    write_json_atomic(cache_meta_path(out_aacomp), cache_meta)

    # ---- syn(bg): top AA contributors to p_null_bg - p_bg (background only) ----
    synbg_lines: list[str] = []
    synbg_lines.append("Top amino-acid contributors to the background synonymous component $p^{\\mathrm{null}}_B-p_B$ (Fold$_m$ boundary indicator).")
    synbg_lines.append("")
    synbg_lines.append("\\begingroup")
    synbg_lines.append("\\hbadness=10000")
    synbg_lines.append("\\scriptsize")
    synbg_lines.append("\\setlength{\\tabcolsep}{4pt}")
    synbg_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    synbg_lines.append("\\setlength{\\LTleft}{0pt}")
    synbg_lines.append("\\setlength{\\LTright}{0pt}")
    synbg_lines.append("\\begin{longtable}{r l r r r r}")
    synbg_lines.append("\\toprule")
    synbg_lines.append("$m$ & AA & $n$ & $p_{\\mathrm{obs}|AA}$ & $p_{\\mathrm{null}|AA}$ & contrib \\\\")
    synbg_lines.append("\\midrule")
    for m in m_list:
        de_bg = bg_decomp_by_m[int(m)]
        aa_contribs = list(de_bg.aa_contribs)  # type: ignore[attr-defined]
        # Contributions in aa_preserving_null_decomposition are for (obs - null).
        # For syn(bg) we need (null - obs), so we negate contrib.
        top = aa_contribs[: int(top_k)]
        for r in top:
            synbg_lines.append(
                f"{int(m)} & {str(r.aa)} & {int(r.n)} & {_fmt_float(r.obs_mean, nd=5)} & {_fmt_float(r.null_mean, nd=5)} & "
                f"{_fmt_float_signed(-float(r.contrib), nd=6)} \\\\"
            )
    synbg_lines.append("\\bottomrule")
    synbg_lines.append("\\end{longtable}")
    synbg_lines.append("\\endgroup")
    synbg_lines.append("")
    write_text_atomic(out_synbg, "\n".join(synbg_lines) + "\n")
    write_json_atomic(cache_meta_path(out_synbg), cache_meta)

    print("Wrote:", out_summary)
    print("Wrote:", out_synsub)
    print("Wrote:", out_aacomp)
    print("Wrote:", out_synbg)


if __name__ == "__main__":
    main()


