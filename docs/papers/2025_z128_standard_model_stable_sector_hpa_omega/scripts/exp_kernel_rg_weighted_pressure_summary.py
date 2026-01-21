# -*- coding: utf-8 -*-
"""
Weighted protocol RG operator: pressure/free-energy (finite-dimensional) summary.

For each n=3..8 we build \\hat F_n(t) and report:
  - lambda_n(t) := rho(\\hat F_n(t)) (PF eigenvalue for nonnegative matrices),
  - P_n(t) := log lambda_n(t) (finite-dimensional pressure proxy),
  - |z|_* = 1/lambda_n(t) (pole-barrier radius).

We sweep t over a small deterministic grid.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_weighted_pressure_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import List

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import build_weighted_F_matrix, pf_right_eigenpair


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    rows: List[str] = []
    ts = [0.0, 0.25, 0.5, 0.75, 1.0]

    # Columns: n, t, lambda, log(lambda), |z|_*.
    for n in range(3, 9):
        for t in ts:
            A = build_weighted_F_matrix(n, t)
            lam, _h = pf_right_eigenpair(A, iters=1800)
            rows.append(
                f"{n} & {_fmt(t)} & {_fmt(lam)} & {_fmt(math.log(lam))} & {_fmt(1.0/lam)} \\\\"
            )

    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_weighted_pressure_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_weighted_pressure_rows.tex")


if __name__ == "__main__":
    main()

