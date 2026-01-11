# -*- coding: utf-8 -*-
"""
Covariant weighted RG operator: Doob normalization audit (n=3,4).

For each n in {3,4} and t in {0,1} we:
  - build \\hat F_n^∇(t) (nonnegative),
  - compute PF eigenpair (lam, h),
  - build the Doob row-stochastic matrix P_ij = A_ij h_j / (lam h_i),
  - report row-sum error statistics.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_weighted_covariant_doob_rows.tex
"""

from __future__ import annotations

from typing import List

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import build_weighted_F_covariant_anchor, doob_row_stochastic, pf_right_eigenpair, row_sum_stats


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    rows: List[str] = []
    # Columns: n, t, r, dim, lam, row_err, row_min, row_max
    for n in (3, 4):
        for t in (0.0, 1.0):
            A, r = build_weighted_F_covariant_anchor(n, t=t)
            lam, h = pf_right_eigenpair(A, iters=2000)
            P = doob_row_stochastic(A, lam, h)
            row_err, row_min, row_max = row_sum_stats(P)
            rows.append(
                f"{n} & {_fmt(t)} & {r} & {16*r} & {_fmt(lam)} & {row_err:.3e} & {_fmt(row_min)} & {_fmt(row_max)} \\\\"
            )
    rows.append("\\bottomrule")
    out = generated_dir() / "kernel_rg_weighted_covariant_doob_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_weighted_covariant_doob_rows.tex")


if __name__ == "__main__":
    main()

