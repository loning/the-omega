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

Output (LaTeX fragment):
  - sections/generated/kernel_rg_covariant_transport_anchor_rows.tex

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


def main() -> None:
    # Build deterministic anchor edge transport on 8x8.
    labels = hol.grid_labels(n_bits=3)
    pre = hol.preimages()
    edge_p = hol.edge_perm_cache(labels, pre)

    # Baseline covariant transport.
    T = build_T_covariant(edge_p, p_stay=0.5)

    # Gauge covariance check under deterministic pseudo-random block relabelings.
    rng = random.Random(1337)
    all_perms = list(__import__("itertools").permutations((0, 1, 2, 3), 4))
    g_block: Dict[int, Perm4] = {b: all_perms[rng.randrange(len(all_perms))] for b in range(16)}

    edge_p2 = blockwise_gauge_relabel(edge_p, g_block)
    T2 = build_T_covariant(edge_p2, p_stay=0.5)

    G = block_diag_G(g_block)
    Ginv = mat_transpose(G)
    conj = mat_mul(mat_mul(G, T), Ginv)

    err = max_abs_diff(T2, conj)

    rows = [
        f"anchor & 0.5 & {err:.3e} \\\\",
        "\\bottomrule",
    ]
    out = generated_dir() / "kernel_rg_covariant_transport_anchor_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_covariant_transport_anchor_rows.tex")


if __name__ == "__main__":
    main()

