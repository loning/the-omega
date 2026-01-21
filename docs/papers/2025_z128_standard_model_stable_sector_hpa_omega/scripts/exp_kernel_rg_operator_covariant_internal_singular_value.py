# -*- coding: utf-8 -*-
"""
Internal-mode contraction certificate via singular value (anchor and n=4).

For each n in {3,4} we:
  - build the covariant operator F_n^∇ (dim 16*r_{2(n+1)}),
  - project to internal orthonormal coordinates F_std (dim 16*(r-1)),
  - estimate the spectral norm ||F_std||_2 by power iteration on (F_std^T F_std),
    which upper-bounds all contraction rates for Euclidean quadratic readouts.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_operator_covariant_internal_sigma_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import List

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import build_F_covariant_anchor, build_F_covariant_internal_orthonormal_from_full, mat_mul, mat_transpose, mat_vec


def _norm2(v: List[float]) -> float:
    return math.sqrt(sum(float(x) * float(x) for x in v))


def spectral_norm_est(A: List[List[float]], iters: int = 250) -> float:
    """
    Estimate ||A||_2 by power iteration on A^T A.
    """
    At = mat_transpose(A)
    n = len(A)
    if n == 0 or any(len(row) != n for row in A):
        raise ValueError("A must be square.")
    # deterministic seed
    x = [float((i % 11) - 5) for i in range(n)]
    nx = _norm2(x)
    if nx == 0.0:
        x[0] = 1.0
        nx = 1.0
    x = [v / nx for v in x]
    lam = 0.0
    for _ in range(max(1, iters)):
        y = mat_vec(A, x)
        z = mat_vec(At, y)
        nz = _norm2(z)
        if nz == 0.0:
            return 0.0
        lam = nz
        x = [v / nz for v in z]
    # For A^T A, eigenvalue approx is lam; sigma = sqrt(lam).
    return float(math.sqrt(abs(lam)))


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    rows: List[str] = []
    # Columns: n, m=2(n+1), r_m, dim_int, sigma_est
    for n in (3, 4):
        F_full, r = build_F_covariant_anchor(n)
        F_std = build_F_covariant_internal_orthonormal_from_full(F_full, r)
        sigma = spectral_norm_est(F_std, iters=300)
        rows.append(f"{n} & {2*(n+1)} & {r} & {16*(r-1)} & {_fmt(sigma):s} \\\\")
    rows.append("\\bottomrule")
    out = generated_dir() / "kernel_rg_operator_covariant_internal_sigma_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_operator_covariant_internal_sigma_rows.tex")


if __name__ == "__main__":
    main()

