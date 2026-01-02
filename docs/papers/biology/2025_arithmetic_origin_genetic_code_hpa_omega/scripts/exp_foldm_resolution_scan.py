#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fold_m resolution scan for codon-scale integers N in {0..63}.

This experiment keeps the nucleotide encoding mu fixed (or scans over all 24 encodings),
and varies the Zeckendorf window length m to study how:
  - the boundary subset X_m^{bdry} changes,
  - the control-boundary objective behaves across m,
  - the (AUG,UAA) homology behaves across m.

Outputs LaTeX fragments into sections/generated/.
Standard library only.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic
from genetic_code_tools import all_encodings, boundary_words_m, fold_codon_m, x_m


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
ANALYSIS_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    return root_dir() / "sections" / "generated"


def data_root() -> Path:
    return root_dir() / "data"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _parse_int_list(s: str) -> list[int]:
    out: list[int] = []
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return sorted({int(x) for x in out})


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fold_m resolution scan (codon-scale N in 0..63)")
    p.add_argument("--m-list", default="6,7,8,9", help="Comma-separated m values to scan (default: 6,7,8,9).")
    p.add_argument("--no-latex", action="store_true", help="Do not write LaTeX fragments.")
    p.add_argument("--force", action="store_true", help="Force recomputation even if cached outputs exist.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    m_list = _parse_int_list(str(args.m_list))
    if not m_list:
        raise SystemExit("Empty --m-list")
    if any(int(m) <= 0 for m in m_list):
        raise SystemExit("All m must be positive")

    out_table = generated_dir() / "foldm_resolution_scan_table.tex"
    out_summary = generated_dir() / "foldm_resolution_scan_summary.tex"

    # ---- Cache short-circuit ----
    cache_file = data_root() / "_cache" / f"foldm_resolution_scan_v{int(ANALYSIS_VERSION)}.json"
    cache_key = {
        "analysis": "foldm_resolution_scan",
        "analysis_version": int(ANALYSIS_VERSION),
        "m_list": [int(x) for x in m_list],
        "mu_star": MU_STAR,
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and out_table.exists() and out_summary.exists() and cache_hit(cache_file, expected_meta=cache_meta, require_meta=True):
        if not args.no_latex:
            print(f"[cache] hit: {cache_file}")
            print("Wrote LaTeX fragments into:", generated_dir())
        return

    control_codons = ("AUG", "UAA", "UAG", "UGA")

    # Build table.
    lines: list[str] = []
    lines.append("\\begin{center}")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{4pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\resizebox{\\textwidth}{!}{%")
    lines.append("\\begin{tabular}{rrrrrrllrrllrr}")
    lines.append("\\toprule")
    lines.append(
        "$m$ & $|X_m|$ & $|X_m^{\\mathrm{bdry}}|$ & $S_m(\\mu^\\ast)$ & $\\max S_m$ & \\#argmax & "
        "$w_m(\\mathrm{AUG})$ & $w_m(\\mathrm{UAA})$ & "
        "$\\Delta_m(\\mathrm{AUG})$ & $\\Delta_m(\\mathrm{UAA})$ & "
        "$\\mathbf{1}\\{w_m(\\mathrm{AUG})=w_m(\\mathrm{UAA})\\}$ & "
        "$\\mathbf{1}\\{w_m(\\mathrm{AUG})\\in X_m^{\\mathrm{bdry}}\\}$ & "
        "$V_m(\\mathrm{AUG})$ & $V_m(\\mathrm{UAA})$ \\\\"
    )
    lines.append("\\midrule")

    summary_lines: list[str] = []
    summary_lines.append(
        "Resolution scan over Zeckendorf windows $m\\in\\{%s\\}$ (codon-scale $N\\in\\{0,\\dots,63\\}$)."
        % (",".join(str(int(m)) for m in m_list))
    )

    for m in m_list:
        xm = x_m(int(m))
        bdry = boundary_words_m(int(m))

        # Control-boundary objective S_m(mu) over all 24 encodings.
        hist: Counter[int] = Counter()
        best_score = -1
        best_count = 0
        mu_star_score = None
        for mu in all_encodings():
            s = 0
            for c in control_codons:
                if fold_codon_m(c, mu, m=int(m)).is_boundary:
                    s += 1
            hist[int(s)] += 1
            if s > best_score:
                best_score = int(s)
                best_count = 1
            elif s == best_score:
                best_count += 1
            if mu == MU_STAR:
                mu_star_score = int(s)
        if mu_star_score is None:
            raise AssertionError("mu* score not computed")

        aug = fold_codon_m("AUG", MU_STAR, m=int(m))
        uaa = fold_codon_m("UAA", MU_STAR, m=int(m))
        same_word = int(aug.w == uaa.w)
        aug_is_bdry = int(aug.is_boundary)

        lines.append(
            f"{int(m)} & {len(xm)} & {len(bdry)} & {mu_star_score} & {best_score} & {best_count} & "
            f"\\texttt{{{aug.w}}} & \\texttt{{{uaa.w}}} & "
            f"{int(aug.delta)} & {int(uaa.delta)} & "
            f"{same_word} & {aug_is_bdry} & "
            f"{int(aug.v)} & {int(uaa.v)} \\\\"
        )

        summary_lines.append(f"For $m={int(m)}$, histogram of $S_m(\\mu)$ over 24 encodings: {dict(hist)}.")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}%")
    lines.append("}")
    lines.append("\\end{center}")

    if not args.no_latex:
        write_text(out_table, "\n".join(lines) + "\n")
        write_text(out_summary, "\n".join(summary_lines) + "\n")
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(cache_file, {"ok": True})
        write_json_atomic(cache_meta_path(cache_file), cache_meta)
        print("Wrote LaTeX fragments into:", generated_dir())


if __name__ == "__main__":
    main()


