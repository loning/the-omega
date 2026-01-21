# -*- coding: utf-8 -*-
"""
Covariant weighted RG operator: pole-barrier summary (n=3,4).

We build the covariant weighted operator \\hat F_n^∇(t) (dimension 16*r_{2(n+1)})
and report:
  - rho(\\hat F_n^∇(t)) and z_star = 1/rho,
  - row-sum min/max as a normalization diagnostic under weighting.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_weighted_covariant_pole_barrier_rows.tex
"""

from __future__ import annotations

from typing import List

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import build_weighted_F_covariant_anchor, power_iteration_rho


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    rows: List[str] = []
    # Columns: n, t, r, dim, rho, z_star, row_sum_min, row_sum_max
    for n in (3, 4):
        for t in (0.0, 1.0):
            Fw, r = build_weighted_F_covariant_anchor(n, t=t)
            rho = power_iteration_rho(Fw, iters=500)
            z_star = 1.0 / rho if rho != 0.0 else float("inf")
            row_sums = [sum(row) for row in Fw]
            rows.append(
                f"{n} & {_fmt(t)} & {r} & {16*r} & {_fmt(rho)} & {_fmt(z_star)} & {_fmt(min(row_sums))} & {_fmt(max(row_sums))} \\\\"
            )
    rows.append("\\bottomrule")
    out = generated_dir() / "kernel_rg_weighted_covariant_pole_barrier_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_weighted_covariant_pole_barrier_rows.tex")


if __name__ == "__main__":
    main()

