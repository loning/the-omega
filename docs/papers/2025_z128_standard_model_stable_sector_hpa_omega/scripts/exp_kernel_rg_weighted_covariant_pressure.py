# -*- coding: utf-8 -*-
"""
Covariant weighted RG operator: pressure proxy (log spectral radius) (n=3,4).

We report log rho(\\hat F_n^∇(t)) for a small t-grid.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_weighted_covariant_pressure_rows.tex
"""

from __future__ import annotations

import math
from typing import List

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import build_weighted_F_covariant_anchor, power_iteration_rho


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    rows: List[str] = []
    # Columns: n, t, r, dim, log_rho
    t_grid = [0.0, 0.5, 1.0]
    for n in (3, 4):
        for t in t_grid:
            A, r = build_weighted_F_covariant_anchor(n, t=t)
            rho = power_iteration_rho(A, iters=600)
            log_rho = math.log(rho) if rho > 0.0 else float("-inf")
            rows.append(f"{n} & {_fmt(t)} & {r} & {16*r} & {_fmt(log_rho)} \\\\")
    rows.append("\\bottomrule")
    out = generated_dir() / "kernel_rg_weighted_covariant_pressure_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_weighted_covariant_pressure_rows.tex")


if __name__ == "__main__":
    main()

