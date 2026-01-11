# -*- coding: utf-8 -*-
"""
Protocol RG operator sanity table (unweighted): build F_n as an explicit 16x16 matrix.

This script produces an auditable summary across n=3..8:
  - constant preservation (row sums ~ 1),
  - basic norm/conditioning summaries,
  - spectral-radius estimate rho(F_n) and the implied pole-barrier radius |z|_* = 1/rho.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_operator_sanity_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import List

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import build_F_matrix, det, power_iteration_rho


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    rows: List[str] = []

    # Columns:
    # n, max_row_sum_err, max_col_sum, rho_est, z_star, |det(I-F)|.
    for n in range(3, 9):
        F = build_F_matrix(n)

        row_sums = [sum(row) for row in F]
        max_row_sum_err = max(abs(s - 1.0) for s in row_sums)

        # 1-norm (max column sum) as a coarse operator-size diagnostic.
        col_sums = [sum(F[i][j] for i in range(16)) for j in range(16)]
        max_col_sum = max(col_sums)

        rho = power_iteration_rho(F, iters=300)
        z_star = 1.0 / rho if rho != 0.0 else float("inf")

        I_minus_F = [[(1.0 if i == j else 0.0) - F[i][j] for j in range(16)] for i in range(16)]
        det_I_minus_F = abs(det(I_minus_F))

        rows.append(
            f"{n} & {_fmt(max_row_sum_err)} & {_fmt(max_col_sum)} & {_fmt(rho)} & {_fmt(z_star)} & {_fmt(det_I_minus_F)} \\\\"
        )

    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_operator_sanity_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_operator_sanity_rows.tex")


if __name__ == "__main__":
    main()

