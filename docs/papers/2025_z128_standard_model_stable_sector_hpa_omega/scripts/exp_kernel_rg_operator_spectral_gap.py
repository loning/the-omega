# -*- coding: utf-8 -*-
"""
Protocol RG operator: spectral gap / mixing diagnostic (balanced chain).

For each n=3..8, we build the explicit 16x16 operator F_n and report:
  - |lambda_2(F_n)| estimated by deflated power iteration on mean-zero subspace,
  - spectral gap := 1 - |lambda_2|,
  - a crude epsilon-mixing estimate t_mix(eps) := ceil(log eps / log |lambda_2|).

Output (LaTeX fragment):
  - sections/generated/kernel_rg_operator_spectral_gap_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import List

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import build_F_matrix, second_eigenvalue_abs


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def _mixing_steps(lam2: float, eps: float) -> int:
    lam2 = float(abs(lam2))
    if eps <= 0.0 or eps >= 1.0:
        raise ValueError("eps must be in (0,1).")
    if lam2 <= 0.0:
        return 1
    if lam2 >= 1.0:
        # No contraction witnessed.
        return -1
    return int(math.ceil(math.log(eps) / math.log(lam2)))


def main() -> None:
    rows: List[str] = []
    eps = 1e-3

    # Columns: n, |lambda2|, gap, t_mix(eps).
    for n in range(3, 9):
        F = build_F_matrix(n)
        lam2 = second_eigenvalue_abs(F, iters=1200)
        gap = 1.0 - float(abs(lam2))
        tmix = _mixing_steps(lam2, eps=eps)
        tmix_str = str(tmix) if tmix >= 0 else r"\text{n/a}"
        rows.append(f"{n} & {_fmt(lam2)} & {_fmt(gap)} & {tmix_str} \\\\")

    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_operator_spectral_gap_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_operator_spectral_gap_rows.tex")


if __name__ == "__main__":
    main()

