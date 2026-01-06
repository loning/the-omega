# -*- coding: utf-8 -*-
"""
Fold_m boundary enrichment: AA-preserving decomposition (standard library only).

We decompose the subset-vs-background boundary-rate difference into components:
  p_sub - p_bg
    = (p_sub - p_null_sub) + (p_null_sub - p_null_bg) + (p_null_bg - p_bg)

where p_null_* is the AA-preserving null expectation (uniform among synonymous codons
in the standard code), and p_bg is the observed corpus background boundary rate.

This separates:
  - synonymous effect in subset (relative to uniform within-AA)
  - AA composition effect (difference of AA counts under uniform-within-AA)
  - synonymous effect in background

Dataset (default):
  - data/boundary_enrichment/recoding_cds_orfs.fasta.gz
  - data/boundary_enrichment/recoding_site_sets.tsv

Outputs:
  - sections/generated/foldm_boundary_enrichment_aa_decomp_summary.tex
  - sections/generated/foldm_boundary_enrichment_aa_decomp_table.tex
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


def codons_by_aa_standard() -> dict[str, list[str]]:
    d: dict[str, list[str]] = defaultdict(list)
    for codon, aa in GENETIC_CODE.items():
        d[str(aa)].append(str(codon))
    for aa in d:
        d[aa].sort()
    return dict(d)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fold_m boundary enrichment AA-preserving decomposition.")
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
    p.add_argument(
        "--out-summary",
        default=str(generated_dir() / "foldm_boundary_enrichment_aa_decomp_summary.tex"),
        help="Output LaTeX summary fragment path.",
    )
    p.add_argument(
        "--out-table",
        default=str(generated_dir() / "foldm_boundary_enrichment_aa_decomp_table.tex"),
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
    out_summary = Path(args.out_summary)
    out_table = Path(args.out_table)

    positions_by_label = _read_positions(pos_path, codon_index_base=int(args.codon_index_base))

    cache_key = {
        "analysis": "foldm_boundary_enrichment_aa_decomp",
        "version": int(SCRIPT_VERSION),
        "m_list": [int(x) for x in m_list],
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

    # Boundary indicator per m and codon (coding codons only).
    coding_codons = [c for c, aa in GENETIC_CODE.items() if aa != "Stop"]
    codon_value_by_m: dict[int, dict[str, float]] = {}
    for m in m_list:
        codon_value_by_m[int(m)] = {c: float(fold_codon_m(c, MU_STAR, m=int(m)).is_boundary) for c in coding_codons}

    codons_by_aa = codons_by_aa_standard()

    # Background counts across whole FASTA (coding codons only).
    bg_codon_counts: Counter[str] = Counter()
    bg_aa_counts: Counter[str] = Counter()
    bg_n = 0

    # Subset counts per label.
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

    # Background observed boundary rates per m.
    bg_p: dict[int, float] = {}
    for m in m_list:
        hits = 0.0
        for c in coding_codons:
            hits += float(bg_codon_counts.get(c, 0)) * float(codon_value_by_m[int(m)][c])
        bg_p[int(m)] = float(hits) / float(bg_n)

    # AA-preserving null expectation for background per m.
    bg_null_p: dict[int, float] = {}
    for m in m_list:
        de_bg = aa_preserving_null_decomposition(
            aa_counts={k: int(v) for k, v in bg_aa_counts.items()},
            codon_counts={k: int(v) for k, v in bg_codon_counts.items()},
            codons_by_aa=codons_by_aa,
            genetic_code=GENETIC_CODE,
            codon_value=codon_value_by_m[int(m)],
            exclude_aas={"Stop"},
        )
        bg_null_p[int(m)] = float(de_bg.null_mean)

    # Build output rows.
    out_rows: list[dict[str, object]] = []
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
            p_sub = float(de_sub.obs_mean)
            p_null_sub = float(de_sub.null_mean)
            p_bg = float(bg_p[int(m)])
            p_null_bg = float(bg_null_p[int(m)])

            diff_total = p_sub - p_bg
            diff_syn_sub = p_sub - p_null_sub
            diff_aa = p_null_sub - p_null_bg
            diff_syn_bg = p_null_bg - p_bg

            out_rows.append(
                {
                    "m": int(m),
                    "label": str(lbl),
                    "n": int(n_sub),
                    "p_sub": p_sub,
                    "p_bg": p_bg,
                    "p_null_sub": p_null_sub,
                    "p_null_bg": p_null_bg,
                    "diff_total": diff_total,
                    "diff_syn_sub": diff_syn_sub,
                    "diff_aa": diff_aa,
                    "diff_syn_bg": diff_syn_bg,
                }
            )

    # Summary line.
    m_str = ",".join(str(int(x)) for x in m_list)
    s_line = (
        "Fold$_m$ AA-preserving decomposition of boundary-rate differences for recoding-window position sets "
        f"($m\\in\\{{{m_str}\\}}$; background $n={bg_n}$ coding codons)."
    )
    write_text_atomic(out_summary, s_line + "\n")

    # LaTeX table.
    out_rows.sort(key=lambda r: (int(r["m"]), str(r["label"])))
    lines: list[str] = []
    lines.append("\\begingroup")
    lines.append("\\hbadness=10000")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{4pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\setlength{\\LTleft}{0pt}")
    lines.append("\\setlength{\\LTright}{0pt}")
    lines.append("\\begin{longtable}{r l r r r r r r r r r}")
    lines.append("\\toprule")
    lines.append(
        "$m$ & label & $n$ & $p_{\\mathrm{sub}}$ & $p_B$ & $p^{\\mathrm{null}}_{\\mathrm{sub}}$ & "
        "$p^{\\mathrm{null}}_B$ & $(p_{\\mathrm{sub}}-p_B)$ & syn(sub) & AA & syn(bg) \\\\"
    )
    lines.append("\\midrule")
    for r in out_rows:
        lines.append(
            f"{int(r['m'])} & {str(r['label']).replace('_','\\_')} & {int(r['n'])} & "
            f"{_fmt_float(r['p_sub'], nd=5)} & {_fmt_float(r['p_bg'], nd=5)} & {_fmt_float(r['p_null_sub'], nd=5)} & {_fmt_float(r['p_null_bg'], nd=5)} & "
            f"{_fmt_float_signed(r['diff_total'], nd=6)} & {_fmt_float_signed(r['diff_syn_sub'], nd=6)} & {_fmt_float_signed(r['diff_aa'], nd=6)} & {_fmt_float_signed(r['diff_syn_bg'], nd=6)} \\\\"
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


