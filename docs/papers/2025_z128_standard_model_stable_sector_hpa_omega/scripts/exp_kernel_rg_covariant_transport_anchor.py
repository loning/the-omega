# -*- coding: utf-8 -*-
"""
Covariant (S4) transport lift on the 4x4 block quotient at the (m,n)=(6,3) anchor.

This script constructs a block-level covariant transport operator T^∇ on the
4x4 block grid (16 blocks), with an internal 4-slot fiber per block (S4 gauge).

Inputs are fully protocol-internal:
  - the deterministic S4 edge transport rule p_{a->b} on the 8x8 n=3 Hilbert grid
    from Section I_21 (implemented by exp_holonomy_loops.py),
  - an axis-aligned coarse 4x4 block partition of the 8x8 grid into 2x2 blocks.

We define a block-to-block transport weight by averaging the 4x4 permutation
matrices across micro-edges crossing between adjacent blocks, then use a lazy
nearest-neighbor Markov mixing at the block graph level.

We audit gauge covariance under blockwise relabelings g_B∈S4:
  T^{∇}[p'] = G T^{∇}[p] G^{-1}, where p'_{a->b} = g_{B(b)} p_{a->b} g_{B(a)}^{-1},
and G is block-diagonal with ρ(g_B).

Output (LaTeX fragments):
  - sections/generated/kernel_rg_covariant_transport_anchor_rows.tex
  - sections/generated/kernel_rg_covariant_transport_reduction_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

import exp_holonomy_loops as hol
from common_paths import generated_dir
from common_tex import write_lines

Perm4 = Tuple[int, int, int, int]
Coord = Tuple[int, int]


def inv_perm(p: Perm4) -> Perm4:
    inv = [0, 0, 0, 0]
    for i, j in enumerate(p):
        inv[j] = i
    return (inv[0], inv[1], inv[2], inv[3])


def compose(p: Perm4, q: Perm4) -> Perm4:
    # p ∘ q (apply q then p)
    return (p[q[0]], p[q[1]], p[q[2]], p[q[3]])


def perm_matrix(p: Perm4) -> List[List[float]]:
    # Convention: slot i at source maps to slot p[i] at target, so M[p[i], i]=1.
    M = [[0.0] * 4 for _ in range(4)]
    for i, j in enumerate(p):
        M[j][i] = 1.0
    return M


def perm_sign(p: Perm4) -> int:
    # Sign of permutation (parity) via inversion count.
    inv = 0
    for i in range(4):
        for j in range(i + 1, 4):
            if p[i] > p[j]:
                inv += 1
    return -1 if (inv % 2 == 1) else 1


def project_sum_zero_basis() -> List[List[float]]:
    """
    Return a fixed 4x3 matrix whose columns form a basis of
    H = {x in R^4 : sum x = 0}.
    Basis vectors: e1-e4, e2-e4, e3-e4.
    """
    return [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [-1.0, -1.0, -1.0],
    ]


def gram_matrix(B: List[List[float]]) -> List[List[float]]:
    # G = B^T B (3x3)
    Bt = mat_transpose(B)
    return mat_mul(Bt, B)


def mat_inv_3x3(A: List[List[float]]) -> List[List[float]]:
    a, b, c = A[0]
    d, e, f = A[1]
    g, h, i = A[2]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if det == 0.0:
        raise ValueError("Singular 3x3 matrix.")
    inv_det = 1.0 / det
    return [
        [(e * i - f * h) * inv_det, (c * h - b * i) * inv_det, (b * f - c * e) * inv_det],
        [(f * g - d * i) * inv_det, (a * i - c * g) * inv_det, (c * d - a * f) * inv_det],
        [(d * h - e * g) * inv_det, (b * g - a * h) * inv_det, (a * e - b * d) * inv_det],
    ]


def rep_H_twisted(p: Perm4) -> List[List[float]]:
    """
    3x3 twisted standard representation \\tilde rho on the sum-zero subspace H:
      - rho(p) is the 4x4 permutation matrix on R^4,
      - restrict to H in the basis B (4x3) by coordinate projection
        M_H = (B^T B)^{-1} B^T rho(p) B,
      - twist by sign(p) to land in SO(3): \\tilde rho = sign(p) * M_H.
    """
    R = perm_matrix(p)  # 4x4
    B = project_sum_zero_basis()  # 4x3
    Bt = mat_transpose(B)  # 3x4
    G = gram_matrix(B)  # 3x3
    Ginv = mat_inv_3x3(G)
    MH = mat_mul(Ginv, mat_mul(Bt, mat_mul(R, B)))  # 3x3
    s = float(perm_sign(p))
    return [[s * float(MH[i][j]) for j in range(3)] for i in range(3)]


def mat_mul(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    n = len(A)
    m = len(B[0])
    k = len(B)
    out = [[0.0] * m for _ in range(n)]
    for i in range(n):
        for t in range(k):
            a = float(A[i][t])
            if a == 0.0:
                continue
            for j in range(m):
                out[i][j] += a * float(B[t][j])
    return out


def mat_transpose(A: List[List[float]]) -> List[List[float]]:
    return [[A[i][j] for i in range(len(A))] for j in range(len(A[0]))]


def max_abs_diff(A: List[List[float]], B: List[List[float]]) -> float:
    m = 0.0
    for rA, rB in zip(A, B, strict=True):
        for a, b in zip(rA, rB, strict=True):
            d = abs(float(a) - float(b))
            if d > m:
                m = d
    return m


def block_id_4x4(coord: Coord) -> int:
    x, y = coord
    return (y // 2) * 4 + (x // 2)


def block_neighbors(b: int) -> List[int]:
    bx = b % 4
    by = b // 4
    out: List[int] = []
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nx, ny = bx + dx, by + dy
        if 0 <= nx < 4 and 0 <= ny < 4:
            out.append(ny * 4 + nx)
    return out


def micro_edges_between_blocks(b_from: int, b_to: int) -> List[Tuple[Coord, Coord]]:
    # Adjacent blocks only; collect directed micro-edges a->b crossing the boundary.
    bx1, by1 = b_from % 4, b_from // 4
    bx2, by2 = b_to % 4, b_to // 4
    if abs(bx1 - bx2) + abs(by1 - by2) != 1:
        return []
    edges: List[Tuple[Coord, Coord]] = []
    # Each block is a 2x2 region in the 8x8 grid.
    xs1 = [2 * bx1, 2 * bx1 + 1]
    ys1 = [2 * by1, 2 * by1 + 1]
    xs2 = [2 * bx2, 2 * bx2 + 1]
    ys2 = [2 * by2, 2 * by2 + 1]
    # Edges across the interface are nearest-neighbor micro edges.
    for x in xs1:
        for y in ys1:
            a = (x, y)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                b = (x + dx, y + dy)
                if b[0] in xs2 and b[1] in ys2:
                    edges.append((a, b))
    return edges


def block_edge_operator(edge_p: Dict[Tuple[Coord, Coord], Perm4], b_from: int, b_to: int) -> List[List[float]]:
    edges = micro_edges_between_blocks(b_from, b_to)
    if not edges:
        return [[0.0] * 4 for _ in range(4)]
    acc = [[0.0] * 4 for _ in range(4)]
    for a, b in edges:
        M = perm_matrix(edge_p[(a, b)])
        for i in range(4):
            for j in range(4):
                acc[i][j] += float(M[i][j])
    inv = 1.0 / float(len(edges))
    return [[acc[i][j] * inv for j in range(4)] for i in range(4)]


def build_T_covariant(edge_p: Dict[Tuple[Coord, Coord], Perm4], *, p_stay: float = 0.5) -> List[List[float]]:
    # 64x64 matrix on blocks×slots.
    if not (0.0 <= p_stay <= 1.0):
        raise ValueError("p_stay must be in [0,1].")
    dim = 16 * 4
    T = [[0.0] * dim for _ in range(dim)]
    for b_to in range(16):
        neigh = block_neighbors(b_to)
        deg = len(neigh)
        # stay on the same block (identity on slots)
        for s in range(4):
            T[4 * b_to + s][4 * b_to + s] += float(p_stay)
        if deg == 0 or p_stay == 1.0:
            continue
        w_nb = (1.0 - float(p_stay)) / float(deg)
        for b_from in neigh:
            A = block_edge_operator(edge_p, b_from, b_to)  # 4x4
            for i in range(4):
                for j in range(4):
                    T[4 * b_to + i][4 * b_from + j] += w_nb * float(A[i][j])
    return T


def build_T_covariant_H(edge_p: Dict[Tuple[Coord, Coord], Perm4], *, p_stay: float = 0.5) -> List[List[float]]:
    # 48x48 matrix on blocks×H (16 blocks × 3).
    if not (0.0 <= p_stay <= 1.0):
        raise ValueError("p_stay must be in [0,1].")
    dim = 16 * 3
    T = [[0.0] * dim for _ in range(dim)]
    for b_to in range(16):
        neigh = block_neighbors(b_to)
        deg = len(neigh)
        # stay on the same block (identity on H)
        for s in range(3):
            T[3 * b_to + s][3 * b_to + s] += float(p_stay)
        if deg == 0 or p_stay == 1.0:
            continue
        w_nb = (1.0 - float(p_stay)) / float(deg)
        for b_from in neigh:
            edges = micro_edges_between_blocks(b_from, b_to)
            if not edges:
                continue
            acc = [[0.0] * 3 for _ in range(3)]
            for a, b in edges:
                M = rep_H_twisted(edge_p[(a, b)])
                for i in range(3):
                    for j in range(3):
                        acc[i][j] += float(M[i][j])
            inv = 1.0 / float(len(edges))
            for i in range(3):
                for j in range(3):
                    acc[i][j] *= inv
            for i in range(3):
                for j in range(3):
                    T[3 * b_to + i][3 * b_from + j] += w_nb * float(acc[i][j])
    return T


def blockwise_gauge_relabel(edge_p: Dict[Tuple[Coord, Coord], Perm4], g_block: Dict[int, Perm4]) -> Dict[Tuple[Coord, Coord], Perm4]:
    out: Dict[Tuple[Coord, Coord], Perm4] = {}
    for (a, b), p in edge_p.items():
        ga = g_block[block_id_4x4(a)]
        gb = g_block[block_id_4x4(b)]
        # p' = gb ∘ p ∘ ga^{-1}
        out[(a, b)] = compose(gb, compose(p, inv_perm(ga)))
    return out


def block_diag_G(g_block: Dict[int, Perm4]) -> List[List[float]]:
    dim = 16 * 4
    G = [[0.0] * dim for _ in range(dim)]
    for b in range(16):
        M = perm_matrix(g_block[b])
        for i in range(4):
            for j in range(4):
                G[4 * b + i][4 * b + j] = float(M[i][j])
    return G


def block_diag_G_H(g_block: Dict[int, Perm4]) -> List[List[float]]:
    dim = 16 * 3
    G = [[0.0] * dim for _ in range(dim)]
    for b in range(16):
        M = rep_H_twisted(g_block[b])
        for i in range(3):
            for j in range(3):
                G[3 * b + i][3 * b + j] = float(M[i][j])
    return G


def block_diag_G_H_inv(g_block: Dict[int, Perm4]) -> List[List[float]]:
    dim = 16 * 3
    Ginv = [[0.0] * dim for _ in range(dim)]
    for b in range(16):
        M = rep_H_twisted(g_block[b])
        Minv = mat_inv_3x3(M)
        for i in range(3):
            for j in range(3):
                Ginv[3 * b + i][3 * b + j] = float(Minv[i][j])
    return Ginv


def scalar_block_kernel_4x4(*, p_stay: float = 0.5) -> List[List[float]]:
    # 16x16 lazy random-walk kernel on the 4x4 block grid.
    if not (0.0 <= p_stay <= 1.0):
        raise ValueError("p_stay must be in [0,1].")
    K = [[0.0] * 16 for _ in range(16)]
    for b_to in range(16):
        neigh = block_neighbors(b_to)
        deg = len(neigh)
        K[b_to][b_to] += float(p_stay)
        if deg > 0 and p_stay < 1.0:
            w = (1.0 - float(p_stay)) / float(deg)
            for b_from in neigh:
                K[b_to][b_from] += w
    return K


def lift_scalar_to_slots(v: List[float]) -> List[float]:
    # E: R^16 -> R^(16*4) by replicating into 4 slots.
    out: List[float] = []
    for b in range(16):
        for _ in range(4):
            out.append(float(v[b]))
    return out


def project_slots_to_scalar(x: List[float]) -> List[float]:
    # S: R^(16*4) -> R^16 by averaging over slots.
    if len(x) != 16 * 4:
        raise ValueError("Expected length 64.")
    out = [0.0] * 16
    for b in range(16):
        s = 0.0
        for j in range(4):
            s += float(x[4 * b + j])
        out[b] = s / 4.0
    return out


def mat_vec_mul(A: List[List[float]], x: List[float]) -> List[float]:
    return [
        sum(float(aij) * float(xj) for aij, xj in zip(row, x, strict=True)) for row in A
    ]


def main() -> None:
    # Build deterministic anchor edge transport on 8x8.
    labels = hol.grid_labels(n_bits=3)
    pre = hol.preimages()
    edge_p = hol.edge_perm_cache(labels, pre)

    p_stay = 0.5
    # Baseline covariant transport (4-slot rep) and 3-dim standard lift.
    T = build_T_covariant(edge_p, p_stay=p_stay)
    TH = build_T_covariant_H(edge_p, p_stay=p_stay)

    # Gauge covariance check under deterministic pseudo-random block relabelings.
    rng = random.Random(1337)
    all_perms = list(__import__("itertools").permutations((0, 1, 2, 3), 4))
    g_block: Dict[int, Perm4] = {b: all_perms[rng.randrange(len(all_perms))] for b in range(16)}

    edge_p2 = blockwise_gauge_relabel(edge_p, g_block)
    T2 = build_T_covariant(edge_p2, p_stay=p_stay)
    TH2 = build_T_covariant_H(edge_p2, p_stay=p_stay)

    G = block_diag_G(g_block)
    Ginv = mat_transpose(G)
    conj = mat_mul(mat_mul(G, T), Ginv)

    err = max_abs_diff(T2, conj)
    GH = block_diag_G_H(g_block)
    GHinv = block_diag_G_H_inv(g_block)
    conjH = mat_mul(mat_mul(GH, TH), GHinv)
    errH = max_abs_diff(TH2, conjH)

    # Scalar reduction (trivial rep): S T E should match the scalar block kernel.
    K = scalar_block_kernel_4x4(p_stay=p_stay)
    v = [float((i % 5) - 2) for i in range(16)]
    lhs = project_slots_to_scalar(mat_vec_mul(T, lift_scalar_to_slots(v)))
    rhs = mat_vec_mul(K, v)
    red_err = max(abs(float(a) - float(b)) for a, b in zip(lhs, rhs, strict=True))

    rows = [
        f"anchor & {p_stay:.2f} & {err:.3e} \\\\",
        "\\bottomrule",
    ]
    out = generated_dir() / "kernel_rg_covariant_transport_anchor_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_covariant_transport_anchor_rows.tex")

    rows2 = [
        f"gauge4d & {p_stay:.2f} & {err:.3e} \\\\",
        f"gauge3d & {p_stay:.2f} & {errH:.3e} \\\\",
        f"scalar_reduction & {p_stay:.2f} & {red_err:.3e} \\\\",
        "\\bottomrule",
    ]
    out2 = generated_dir() / "kernel_rg_covariant_transport_reduction_rows.tex"
    write_lines(out2, rows2)
    print("Wrote sections/generated/kernel_rg_covariant_transport_reduction_rows.tex")


if __name__ == "__main__":
    main()

