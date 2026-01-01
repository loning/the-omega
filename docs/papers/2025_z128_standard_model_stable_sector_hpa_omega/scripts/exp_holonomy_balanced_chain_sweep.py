# -*- coding: utf-8 -*-
"""
Balanced-chain sweep for toy holonomy and phase-lift CP signal.

We consider the balanced chain m=2n with (n,m) in {(3,6),(4,8),(5,10)}.
For each pair we:
  - embed indices k in {0..4^n-1} on a 2^n x 2^n grid via Hilbert addressing,
  - label each site by the stable word w = Fold_m(k),
  - define an S4-valued edge transport using a fixed fiber rank D=4:
      - for each stable type w, take the first 4 preimages of Fold_m (pad if <4),
      - choose the minimum-cost bijection (4! exhaustive) under Hamming cost on m-bit words,
  - compute plaquette holonomies and summarize cycle types,
  - compute a phase-lifted CP-odd invariant J on plaquettes at denom = 2^m.

Outputs (LaTeX fragment):
  - sections/generated/holonomy_balanced_chain_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import exp_foldm_stats as foldm
import exp_hilbert_chirality_index as hil
from common_tex import write_lines


Coord = Tuple[int, int]
Perm = Tuple[int, int, int, int]


def bits_m(n: int, m: int) -> str:
    return format(n, f"0{m}b")


def hamming(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)


def preimages(m: int) -> Dict[str, List[int]]:
    pre: Dict[str, List[int]] = defaultdict(list)
    for k in range(1 << m):
        pre[foldm.foldm(k, m)].append(k)
    for w in pre:
        pre[w] = sorted(pre[w])
    return dict(pre)


def fiber4(pre: Dict[str, List[int]], w: str) -> List[int]:
    xs = list(pre[w])
    xs.sort()
    if len(xs) >= 4:
        return xs[:4]
    while len(xs) < 4:
        xs.append(xs[-1])
    return xs


def best_perm(fa: List[int], fb: List[int], m: int) -> Perm:
    a_bits = [bits_m(x, m) for x in fa]
    b_bits = [bits_m(x, m) for x in fb]
    best: Tuple[int, Perm] | None = None
    for p in itertools.permutations((0, 1, 2, 3), 4):
        cost = 0
        for i in range(4):
            cost += hamming(a_bits[i], b_bits[p[i]])
        cand = (cost, p)
        if best is None or cand < best:
            best = cand
    if best is None:
        raise AssertionError("No permutations enumerated.")
    return best[1]


def inv_perm(p: Perm) -> Perm:
    inv = [0, 0, 0, 0]
    for i, j in enumerate(p):
        inv[j] = i
    return (inv[0], inv[1], inv[2], inv[3])


def compose(p: Perm, q: Perm) -> Perm:
    # p ∘ q (apply q then p)
    return (p[q[0]], p[q[1]], p[q[2]], p[q[3]])


def cycle_type(p: Perm) -> str:
    seen = [False, False, False, False]
    lengths: List[int] = []
    for i in range(4):
        if seen[i]:
            continue
        j = i
        k = 0
        while not seen[j]:
            seen[j] = True
            j = p[j]
            k += 1
        lengths.append(k)
    lengths.sort(reverse=True)
    if lengths == [1, 1, 1, 1]:
        return "1"
    if lengths == [2, 1, 1]:
        return "2"
    if lengths == [2, 2]:
        return "2x2"
    if lengths == [3, 1]:
        return "3"
    if lengths == [4]:
        return "4"
    return "other"


def grid_labels(n_bits: int, m: int) -> Dict[Coord, str]:
    path = hil.hilbert_curve(n_bits)
    idx_of: Dict[Coord, int] = {}
    for k, c in enumerate(path):
        idx_of[(int(c[0]), int(c[1]))] = k
    out: Dict[Coord, str] = {}
    for coord, k in idx_of.items():
        out[coord] = foldm.foldm(k, m)
    return out


def edge_perm_cache(n_bits: int, m: int, labels: Dict[Coord, str], pre: Dict[str, List[int]]) -> Dict[Tuple[Coord, Coord], Perm]:
    N = 1 << n_bits
    cache: Dict[Tuple[Coord, Coord], Perm] = {}

    def key(a: Coord, b: Coord) -> Tuple[Coord, Coord]:
        return (a, b) if a < b else (b, a)

    for x in range(N):
        for y in range(N):
            a = (x, y)
            for dx, dy in [(1, 0), (0, 1)]:
                nx, ny = x + dx, y + dy
                if nx >= N or ny >= N:
                    continue
                b = (nx, ny)
                ka, kb = key(a, b)
                wa = labels[ka]
                wb = labels[kb]
                pa = fiber4(pre, wa)
                pb = fiber4(pre, wb)
                p = best_perm(pa, pb, m=m)
                cache[(ka, kb)] = p

    out: Dict[Tuple[Coord, Coord], Perm] = {}
    for (a, b), p in cache.items():
        out[(a, b)] = p
        out[(b, a)] = inv_perm(p)
    return out


def basis_B() -> List[List[float]]:
    s2 = math.sqrt(2.0)
    s6 = math.sqrt(6.0)
    s12 = math.sqrt(12.0)
    v1 = [1.0 / s2, -1.0 / s2, 0.0, 0.0]
    v2 = [1.0 / s6, 1.0 / s6, -2.0 / s6, 0.0]
    v3 = [1.0 / s12, 1.0 / s12, 1.0 / s12, -3.0 / s12]
    return [[v1[i], v2[i], v3[i]] for i in range(4)]


def transpose_real(B: List[List[float]]) -> List[List[float]]:
    return [list(row) for row in zip(*B)]


def matmul(A: List[List[complex]], B: List[List[complex]]) -> List[List[complex]]:
    ra = len(A)
    ca = len(A[0]) if A else 0
    rb = len(B)
    cb = len(B[0]) if B else 0
    if ca != rb:
        raise ValueError("Incompatible matrix shapes.")
    out = [[0j] * cb for _ in range(ra)]
    for i in range(ra):
        for k in range(ca):
            aik = A[i][k]
            if aik == 0j:
                continue
            for j in range(cb):
                out[i][j] += aik * B[k][j]
    return out


def project_3x3(H: List[List[complex]], B: List[List[float]]) -> List[List[complex]]:
    Bc = [[complex(x, 0.0) for x in row] for row in B]
    Bt = transpose_real(B)
    Btc = [[complex(x, 0.0) for x in row] for row in Bt]
    HB = matmul(H, Bc)
    return matmul(Btc, HB)


def gram_schmidt_unitary(M: List[List[complex]], eps: float = 1e-12) -> List[List[complex]] | None:
    cols = [[M[i][j] for i in range(3)] for j in range(3)]
    Qcols: List[List[complex]] = []

    def inner(u: List[complex], v: List[complex]) -> complex:
        return sum(u[i].conjugate() * v[i] for i in range(3))

    def norm(v: List[complex]) -> float:
        return math.sqrt(float(inner(v, v).real))

    for v in cols:
        w = list(v)
        for q in Qcols:
            wproj = inner(q, w)
            for i in range(3):
                w[i] -= wproj * q[i]
        n = norm(w)
        if n < eps:
            return None
        for i in range(3):
            w[i] /= n
        Qcols.append(w)
    return [[Qcols[j][i] for j in range(3)] for i in range(3)]


def jarlskog(U: List[List[complex]]) -> float:
    return float((U[0][0] * U[1][1] * U[0][1].conjugate() * U[1][0].conjugate()).imag)


def phase(k: int, denom: int) -> float:
    return 2.0 * math.pi * (float(k) / float(denom))


def edge_unitary(a: Coord, b: Coord, labels: Dict[Coord, str], pre: Dict[str, List[int]], edge_p: Dict[Tuple[Coord, Coord], Perm], m: int, denom: int) -> List[List[complex]]:
    p = edge_p[(a, b)]
    wa = labels[a]
    wb = labels[b]
    fa = fiber4(pre, wa)
    fb = fiber4(pre, wb)
    U = [[0j] * 4 for _ in range(4)]
    for i in range(4):
        j = p[i]
        theta = phase(fb[j], denom=denom) - phase(fa[i], denom=denom)
        U[j][i] = complex(math.cos(theta), math.sin(theta))
    return U


def sweep_one(n_bits: int, m: int) -> Tuple[Counter[str], Dict[str, float], Dict[str, float], int]:
    labels = grid_labels(n_bits, m)
    pre = preimages(m)
    edge_p = edge_perm_cache(n_bits, m, labels, pre)
    N = 1 << n_bits

    hist = Counter()
    J_by_ct: Dict[str, List[float]] = defaultdict(list)
    failures = 0
    B = basis_B()
    denom = 1 << m  # denom = 2^m

    for x in range(N - 1):
        for y in range(N - 1):
            a = (x, y)
            b = (x + 1, y)
            c = (x + 1, y + 1)
            d = (x, y + 1)

            p_ab = edge_p[(a, b)]
            p_bc = edge_p[(b, c)]
            p_cd = edge_p[(c, d)]
            p_da = edge_p[(d, a)]
            hol_p = compose(p_da, compose(p_cd, compose(p_bc, p_ab)))
            ct = cycle_type(hol_p)
            hist[ct] += 1

            # Phase-lifted unitary holonomy.
            U_ab = edge_unitary(a, b, labels, pre, edge_p, m=m, denom=denom)
            U_bc = edge_unitary(b, c, labels, pre, edge_p, m=m, denom=denom)
            U_cd = edge_unitary(c, d, labels, pre, edge_p, m=m, denom=denom)
            U_da = edge_unitary(d, a, labels, pre, edge_p, m=m, denom=denom)
            H = matmul(U_da, matmul(U_cd, matmul(U_bc, U_ab)))
            M = project_3x3(H, B=B)
            Q = gram_schmidt_unitary(M)
            if Q is None:
                failures += 1
                continue
            J_by_ct[ct].append(jarlskog(Q))

    mean_abs: Dict[str, float] = {}
    mean_signed: Dict[str, float] = {}
    for ct in ["1", "2", "2x2", "3", "4", "other"]:
        xs = J_by_ct.get(ct, [])
        if not xs:
            mean_abs[ct] = 0.0
            mean_signed[ct] = 0.0
        else:
            mean_abs[ct] = sum(abs(x) for x in xs) / float(len(xs))
            mean_signed[ct] = sum(xs) / float(len(xs))
    return hist, mean_abs, mean_signed, failures


def main() -> None:
    chain = [(3, 6), (4, 8), (5, 10)]

    rows: List[str] = []
    for n_bits, m in chain:
        hist, mean_abs, mean_signed, failures = sweep_one(n_bits, m)
        Np = (1 << n_bits) - 1
        total_plaq = Np * Np
        # Focus cycle-type counts and CP signal on 3/4 cycles.
        c1 = hist.get("1", 0)
        c2 = hist.get("2", 0)
        c22 = hist.get("2x2", 0)
        c3 = hist.get("3", 0)
        c4 = hist.get("4", 0)
        meanJ34 = (float(c3) * mean_abs.get("3", 0.0) + float(c4) * mean_abs.get("4", 0.0)) / float(max(1, c3 + c4))
        meanJ34s = (float(c3) * mean_signed.get("3", 0.0) + float(c4) * mean_signed.get("4", 0.0)) / float(max(1, c3 + c4))
        rows.append(
            f"{n_bits} & {m} & {total_plaq} & {c1} & {c2} & {c22} & {c3} & {c4} & {meanJ34:.6g} & {meanJ34s:+.6g} & {failures} \\\\"
        )

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_balanced_chain_rows.tex", rows)
    print("Wrote sections/generated/holonomy_balanced_chain_rows.tex")


if __name__ == "__main__":
    main()


