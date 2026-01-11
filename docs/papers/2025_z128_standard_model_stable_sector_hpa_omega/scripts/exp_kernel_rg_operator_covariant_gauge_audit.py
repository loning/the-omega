# -*- coding: utf-8 -*-
"""
Covariant RG gauge covariance audit (anchor, construction-level).

We pick a deterministic blockwise gauge field g_B ∈ S_{r_8} (one permutation per
coarse 4x4 block) and:
  1) construct F_3^{∇,g} directly by conjugating each block-to-block slot transport
     during the build (construction-level),
  2) compare it to the conjugated operator G F_3^∇ G^{-1},
  3) certify that the scalar reduction S F_3^{∇,g} E equals the scalar F_3.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_operator_covariant_gauge_rows.tex

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
    build_F_matrix,
    block_diag_perm_matrix,
    mat_mul,
    mat_vec,
)


def _inv_perm(p: Tuple[int, ...]) -> Tuple[int, ...]:
    r = len(p)
    inv = [0] * r
    for i, j in enumerate(p):
        inv[int(j)] = int(i)
    return tuple(inv)


def max_abs_diff_mat(A: List[List[float]], B: List[List[float]]) -> float:
    m = 0.0
    for ra, rb in zip(A, B, strict=True):
        for a, b in zip(ra, rb, strict=True):
            d = abs(float(a) - float(b))
            if d > m:
                m = d
    return m


def lift_E(v: List[float], r: int) -> List[float]:
    out: List[float] = []
    for b in range(16):
        for _ in range(r):
            out.append(float(v[b]))
    return out


def proj_S(x: List[float], r: int) -> List[float]:
    out = [0.0] * 16
    for b in range(16):
        s = 0.0
        for j in range(r):
            s += float(x[b * r + j])
        out[b] = s / float(r)
    return out


def max_abs_diff_vec(a: List[float], b: List[float]) -> float:
    return max(abs(float(x) - float(y)) for x, y in zip(a, b, strict=True))


def main() -> None:
    rows: List[str] = []
    tests = [
        [1.0] * 16,
        [float((i % 7) - 3) for i in range(16)],
        [0.0] * 8 + [1.0] * 8,
    ]

    for n in (3, 4):
        F, r = build_F_covariant_anchor(n)
        rng = random.Random(20260111 + n)
        perms = list(itertools.permutations(range(r), r))
        g_block = [perms[rng.randrange(len(perms))] for _ in range(16)]
        Fg, _ = build_F_covariant_anchor_block_gauge(n, g_block=g_block)

        G = block_diag_perm_matrix(g_block, r)
        Ginv = block_diag_perm_matrix([_inv_perm(p) for p in g_block], r)
        conj = mat_mul(mat_mul(G, F), Ginv)
        gauge_err = max_abs_diff_mat(Fg, conj)

        # Scalar reduction invariance: S Fg E = F_n.
        Fsc = build_F_matrix(n)
        red_err = 0.0
        for v in tests:
            x = lift_E(v, r)
            y = mat_vec(Fg, x)
            Sv = proj_S(y, r)
            Fv = mat_vec(Fsc, v)
            red_err = max(red_err, max_abs_diff_vec(Sv, Fv))

        rows.append(f"{n} & {2*(n+1)} & {r} & {16*r} & {gauge_err:.3e} & {red_err:.3e} \\\\")
    rows.append("\\bottomrule")
    out = generated_dir() / "kernel_rg_operator_covariant_gauge_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_operator_covariant_gauge_rows.tex")


if __name__ == "__main__":
    main()

