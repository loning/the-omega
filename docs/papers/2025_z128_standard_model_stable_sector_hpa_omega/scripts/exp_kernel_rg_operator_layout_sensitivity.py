# -*- coding: utf-8 -*-
"""
Protocol RG operator: D4 layout sensitivity audit (with transport).

We treat a layout as a D4 symmetry g acting on the Hilbert screen coordinates:
  H_n^g(k) := g(H_n(k)).
The block partition remains axis-aligned in the transformed coordinates.

For each n=3..8 and each g in a fixed D4 family, we:
  - build the 16x16 operator F_n^g from the transformed addressing, including
    the same protocol-local transport step (lazy random walk on the screen graph),
  - compute the induced permutation pi_g on the 4x4 block grid,
  - check the conjugacy identity: F_n^g ≈ P(pi_g) F_n P(pi_g)^{-1},
  - report the maximum absolute entry error of that conjugacy check.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_operator_layout_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

import exp_hilbert_chirality_index as hil
from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import _n_micro, block_size, det, mat_mul, mat_transpose, power_iteration_rho

Mat = List[List[float]]


def _block_id_from_xy(x: int, y: int, *, bsz: int) -> int:
    bx = x // bsz
    by = y // bsz
    return by * 4 + bx


def _build_block_ids(n_bits: int, g: Callable[[int, int, int], Tuple[int, int]]) -> List[int]:
    bsz = block_size(n_bits)
    L = (1 << n_bits) - 1
    path = hil.hilbert_curve(n_bits)
    out: List[int] = []
    for (x, y) in path:
        xg, yg = g(int(x), int(y), L)
        out.append(_block_id_from_xy(xg, yg, bsz=bsz))
    return out


def _inv_map_from_path(n_bits: int, g: Callable[[int, int, int], Tuple[int, int]]) -> Dict[Tuple[int, int], int]:
    L = (1 << n_bits) - 1
    path = hil.hilbert_curve(n_bits)
    out: Dict[Tuple[int, int], int] = {}
    for k, (x, y) in enumerate(path):
        xg, yg = g(int(x), int(y), L)
        out[(xg, yg)] = k
    return out


def _parent_map_layout(n_bits: int, g: Callable[[int, int, int], Tuple[int, int]]) -> List[int]:
    inv_n = _inv_map_from_path(n_bits, g)
    Lnp1 = (1 << (n_bits + 1)) - 1
    path_np1 = hil.hilbert_curve(n_bits + 1)
    out: List[int] = []
    for (x2, y2) in path_np1:
        xg2, yg2 = g(int(x2), int(y2), Lnp1)
        xp = xg2 >> 1
        yp = yg2 >> 1
        out.append(inv_n[(xp, yp)])
    return out


def _neighbors_4(x: int, y: int, *, L: int) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    if x > 0:
        out.append((x - 1, y))
    if x < L:
        out.append((x + 1, y))
    if y > 0:
        out.append((x, y - 1))
    if y < L:
        out.append((x, y + 1))
    return out


def _build_F_from_layout(n_bits: int, g: Callable[[int, int, int], Tuple[int, int]]) -> Mat:
    """
    Build F_n^{(g)} with the same transport-upgraded rule:
      F_n^{(g)} = P_{n+1}^{(g)} T_{n+1}^{(g)} U_n^{(g)} (P_n^{(g)})^*,
    realized as a 16x16 matrix on the block quotient in transformed coordinates.
    """
    p_stay = 0.5
    bids_n = _build_block_ids(n_bits, g)
    bids_np1 = _build_block_ids(n_bits + 1, g)
    parents_np1 = _parent_map_layout(n_bits, g)
    inv_np1 = _inv_map_from_path(n_bits + 1, g)
    Lnp1 = (1 << (n_bits + 1)) - 1

    Np1 = len(bids_np1)
    denom = float(Np1 // 16)
    counts: Mat = [[0.0] * 16 for _ in range(16)]

    # Iterate destinations in the Hilbert index order; use transformed coordinates via inv_np1 keys.
    # Reuse the transformed path for coordinate access.
    path_np1 = hil.hilbert_curve(n_bits + 1)
    for k_dest, (x, y) in enumerate(path_np1):
        xg, yg = g(int(x), int(y), Lnp1)
        i = bids_np1[k_dest]
        neigh = _neighbors_4(int(xg), int(yg), L=Lnp1)
        deg = len(neigh)
        # self
        j_self = bids_n[parents_np1[k_dest]]
        counts[i][j_self] += float(p_stay)
        if deg > 0 and p_stay < 1.0:
            w = (1.0 - float(p_stay)) / float(deg)
            for (xn, yn) in neigh:
                k_src = inv_np1[(xn, yn)]
                j = bids_n[parents_np1[k_src]]
                counts[i][j] += w

    return [[c / denom for c in row] for row in counts]


def _perm_from_layout(n_bits: int, g: Callable[[int, int, int], Tuple[int, int]]) -> List[int]:
    """
    Induced permutation on the 4x4 block grid (0..15).
    """
    bsz = block_size(n_bits)
    L = (1 << n_bits) - 1
    pi = [0] * 16
    for by in range(4):
        for bx in range(4):
            x = bx * bsz
            y = by * bsz
            xg, yg = g(x, y, L)
            b2 = _block_id_from_xy(xg, yg, bsz=bsz)
            b1 = by * 4 + bx
            pi[b1] = b2
    return pi


def _perm_matrix(pi: List[int]) -> Mat:
    n = len(pi)
    P: Mat = [[0.0] * n for _ in range(n)]
    for i, j in enumerate(pi):
        P[j][i] = 1.0  # (P v)_j = v_i
    return P


def _max_abs_entry(A: Mat, B: Mat) -> float:
    m = 0.0
    for rA, rB in zip(A, B, strict=True):
        for a, b in zip(rA, rB, strict=True):
            d = abs(float(a) - float(b))
            if d > m:
                m = d
    return m


def _I_minus(A: Mat) -> Mat:
    n = len(A)
    out: Mat = [[float(A[i][j]) for j in range(n)] for i in range(n)]
    for i in range(n):
        out[i][i] = 1.0 - out[i][i]
    return out


def _fmt(x: float) -> str:
    return f"{x:.6e}"


def _g_id(x: int, y: int, L: int) -> Tuple[int, int]:
    return (x, y)


def _g_rot90(x: int, y: int, L: int) -> Tuple[int, int]:
    return (y, L - x)


def _g_rot180(x: int, y: int, L: int) -> Tuple[int, int]:
    return (L - x, L - y)


def _g_rot270(x: int, y: int, L: int) -> Tuple[int, int]:
    return (L - y, x)


def _g_refx(x: int, y: int, L: int) -> Tuple[int, int]:
    return (L - x, y)


def _g_refy(x: int, y: int, L: int) -> Tuple[int, int]:
    return (x, L - y)


def _g_diag(x: int, y: int, L: int) -> Tuple[int, int]:
    return (y, x)


def _g_antidiag(x: int, y: int, L: int) -> Tuple[int, int]:
    return (L - y, L - x)


def main() -> None:
    layouts: List[Tuple[str, Callable[[int, int, int], Tuple[int, int]]]] = [
        ("id", _g_id),
        ("rot90", _g_rot90),
        ("rot180", _g_rot180),
        ("rot270", _g_rot270),
        ("refx", _g_refx),
        ("refy", _g_refy),
        ("diag", _g_diag),
        ("antidiag", _g_antidiag),
    ]

    rows: List[str] = []
    # Columns: n, layout, conj_max_abs, rho, |det(I-F)|.
    for n in range(3, 9):
        # Baseline (with transport).
        F0 = _build_F_from_layout(n, _g_id)
        rho0 = power_iteration_rho(F0)
        det0 = abs(det(_I_minus(F0)))

        for name, g in layouts:
            Fg = _build_F_from_layout(n, g)

            pi = _perm_from_layout(n, g)
            P = _perm_matrix(pi)
            Pinv = mat_transpose(P)
            F_conj = mat_mul(mat_mul(P, F0), Pinv)

            conj_err = _max_abs_entry(Fg, F_conj)
            rho = power_iteration_rho(Fg)
            detv = abs(det(_I_minus(Fg)))

            # Report with baseline invariants as a cross-check (they should match).
            rows.append(
                f"{n} & {name} & {_fmt(conj_err)} & {_fmt(abs(rho - rho0))} & {_fmt(abs(detv - det0))} \\\\"
            )

    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_operator_layout_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_operator_layout_rows.tex")


if __name__ == "__main__":
    main()

