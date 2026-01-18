# -*- coding: utf-8 -*-
"""
Weighted pressure toy for the golden-mean shift via a 2x2 weighted transfer matrix.

We consider the weighted matrix
  B_beta = [[1, exp(-beta)],
            [1, 0]],
whose spectral radius lambda(beta) gives a toy pressure P(beta)=log lambda(beta).

This provides a fully computable illustration of how the pole barrier (dominant
singularity radius 1/lambda) moves under a simple weight family, while remaining
within the same golden-mean combinatorial skeleton.

Outputs (LaTeX fragment):
  - sections/generated/weighted_pressure_sweep_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import List

from common_paths import generated_dir
from common_tex import write_lines


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    beta_list = [0.0, 0.5, 1.0, 2.0, 4.0]
    rows: List[str] = []

    log2 = math.log(2.0)
    for beta in beta_list:
        a = math.exp(-beta)
        lam = 0.5 * (1.0 + math.sqrt(1.0 + 4.0 * a))
        P = math.log(lam)
        z_star = 1.0 / lam
        gap = log2 - P
        rows.append(
            f"{_fmt(beta)} & {_fmt(a)} & {_fmt(lam)} & {_fmt(P)} & {_fmt(z_star)} & {_fmt(gap)} \\\\"
        )

    rows.append("\\bottomrule")

    out = generated_dir() / "weighted_pressure_sweep_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/weighted_pressure_sweep_rows.tex")


if __name__ == "__main__":
    main()

