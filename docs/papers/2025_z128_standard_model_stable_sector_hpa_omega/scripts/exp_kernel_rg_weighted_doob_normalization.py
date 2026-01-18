# -*- coding: utf-8 -*-
"""
Weighted protocol RG operator: Doob (Markov) normalization audit.

For each n=3..8 and t in {0,1}, we build the 16x16 weighted operator
  \\hat F_n(t) = P_{n+1} U_n exp(t M_{phi_n}) P_n^*
and compute its Perron-Frobenius dominant eigenpair (lambda, h).

We then form the Doob transform (row-stochastic Markov kernel)
  \\widetilde F_n(t)_{ij} = \\hat F_n(t)_{ij} * h_j / (lambda * h_i),
so each row sums to 1.

We report:
  - lambda and log(lambda),
  - |z|_* = 1/lambda (pole-barrier radius for this finite matrix),
  - max row-sum error after normalization,
  - |lambda_2(\\widetilde F_n(t))| (mean-zero subspace diagnostic),
  - and the effective Doob support size d_eff (PF support).

Output (LaTeX fragment):
  - sections/generated/kernel_rg_weighted_doob_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import List

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import (
    build_weighted_F_matrix,
    doob_row_stochastic,
    pf_right_eigenpair,
    row_sum_stats,
    second_eigenvalue_abs,
)


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    rows: List[str] = []
    ts = [0.0, 1.0]

    # Columns:
    # n, t, lambda, log(lambda), |z|_*, row_sum_err(Doob), |lambda2(Doob)|, d_eff.
    for n in range(3, 9):
        for t in ts:
            A = build_weighted_F_matrix(n, t)
            lam, h = pf_right_eigenpair(A, iters=1600)
            support = [i for i, hi in enumerate(h) if float(hi) > 1e-12]
            d_eff = len(support)

            lam2_str = r"\text{n/a}"
            row_err_str = r"\text{n/a}"
            if d_eff >= 2:
                A_s = [[A[i][j] for j in support] for i in support]
                lam_s, h_s = pf_right_eigenpair(A_s, iters=2000)
                P = doob_row_stochastic(A_s, lam_s, h_s)
                row_err, _, _ = row_sum_stats(P)
                lam2 = second_eigenvalue_abs(P, iters=1200)
                row_err_str = _fmt(row_err)
                lam2_str = _fmt(lam2)

            zstar = 1.0 / float(lam)
            rows.append(
                f"{n} & {_fmt(t)} & {_fmt(lam)} & {_fmt(math.log(lam))} & {_fmt(zstar)}"
                f" & {row_err_str} & {lam2_str} & {d_eff} \\\\"
            )

    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_weighted_doob_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_weighted_doob_rows.tex")


if __name__ == "__main__":
    main()

