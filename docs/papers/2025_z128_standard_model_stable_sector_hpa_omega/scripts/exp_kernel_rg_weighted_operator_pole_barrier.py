# -*- coding: utf-8 -*-
"""
Weighted protocol RG operator: pole-barrier summary.

We build the 16x16 weighted operator \\hat{F}_n(t) for the balanced chain m=2n:
  \\hat{F}_n(t) = P_{n+1} U_n exp(t * phi_n) P_n^*,
  phi_n(k) = log g_{2n}(Fold_{2n}(k)).

For each n=3..8 and t in {0, 1} we report:
  - rho(\\hat{F}_n(t)) and |z|_* = 1/rho,
  - basic row-sum diagnostics (how far from stochastic normalization under weighting).

Output (LaTeX fragment):
  - sections/generated/kernel_rg_weighted_pole_barrier_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from typing import List

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import build_weighted_F_matrix, power_iteration_rho


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    rows: List[str] = []

    # Columns:
    # n, t, rho, z_star, row_sum_min, row_sum_max.
    for n in range(3, 9):
        for t in (0.0, 1.0):
            F = build_weighted_F_matrix(n, t=t)
            rho = power_iteration_rho(F, iters=400)
            z_star = 1.0 / rho if rho != 0.0 else float("inf")

            row_sums = [sum(row) for row in F]
            rs_min = min(row_sums)
            rs_max = max(row_sums)

            rows.append(
                f"{n} & {_fmt(t)} & {_fmt(rho)} & {_fmt(z_star)} & {_fmt(rs_min)} & {_fmt(rs_max)} \\\\"
            )

    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_weighted_pole_barrier_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_weighted_pole_barrier_rows.tex")


if __name__ == "__main__":
    main()

