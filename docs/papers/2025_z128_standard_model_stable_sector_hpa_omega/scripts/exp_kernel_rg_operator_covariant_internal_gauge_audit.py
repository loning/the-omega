# -*- coding: utf-8 -*-
"""
Internal-mode gauge covariance audit for the covariant RG operator (anchor).

We audit construction-level gauge covariance in the orthonormal internal coordinates:
  F_std,g  =  H F_std H^{-1},
where
  - F_std = (I⊗B^T) F^∇ (I⊗B) is the internal standard representation (B orthonormal basis of sum-zero),
  - g_B ∈ S_r is a blockwise local relabeling on the full slot space,
  - H is the induced block-diagonal orthogonal action H_b = B^T P(g_b) B on internal coordinates.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_operator_covariant_internal_gauge_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
import random
from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import (
    build_F_covariant_anchor,
    build_F_covariant_anchor_block_gauge,
    build_F_covariant_internal_orthonormal_from_full,
    build_sum_zero_orthonormal_basis,
    block_diag_internal_gauge,
    mat_mul,
    mat_transpose,
)


def max_abs_diff_mat(A: List[List[float]], B: List[List[float]]) -> float:
    m = 0.0
    for ra, rb in zip(A, B, strict=True):
        for a, b in zip(ra, rb, strict=True):
            d = abs(float(a) - float(b))
            if d > m:
                m = d
    return m


def orth_err(H: List[List[float]]) -> float:
    # max abs of (H H^T - I)
    Ht = mat_transpose(H)
    HHt = mat_mul(H, Ht)
    n = len(HHt)
    m = 0.0
    for i in range(n):
        for j in range(n):
            target = 1.0 if i == j else 0.0
            d = abs(float(HHt[i][j]) - target)
            if d > m:
                m = d
    return m


def main() -> None:
    F_full, r = build_F_covariant_anchor(3)

    rng = random.Random(20260111)
    perms = list(itertools.permutations(range(r), r))
    g_block: List[Tuple[int, ...]] = [perms[rng.randrange(len(perms))] for _ in range(16)]

    Fg_full, _ = build_F_covariant_anchor_block_gauge(3, g_block=g_block)

    # Internal orthonormal projection
    F_std = build_F_covariant_internal_orthonormal_from_full(F_full, r)
    F_std_g = build_F_covariant_internal_orthonormal_from_full(Fg_full, r)

    B = build_sum_zero_orthonormal_basis(r)
    H = block_diag_internal_gauge(g_block, B)

    # In orthonormal coordinates H^{-1} = H^T
    Ht = mat_transpose(H)
    conj = mat_mul(mat_mul(H, F_std), Ht)

    gauge_err = max_abs_diff_mat(F_std_g, conj)
    ortho = orth_err(H)

    dim_int = 16 * (r - 1)
    rows = [
        f"3 & 8 & {r} & {dim_int} & {gauge_err:.3e} & {ortho:.3e} \\\\",
        "\\bottomrule",
    ]
    out = generated_dir() / "kernel_rg_operator_covariant_internal_gauge_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_operator_covariant_internal_gauge_rows.tex")


if __name__ == "__main__":
    main()

