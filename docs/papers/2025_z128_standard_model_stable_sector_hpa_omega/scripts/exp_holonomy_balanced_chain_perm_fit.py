# -*- coding: utf-8 -*-
"""
Balanced-chain permutation-robust fits for phase-lifted holonomy angles (toy).

We extend the balanced chain sweep (n,m) = (3,6),(4,8),(5,10) by extracting
effective 3x3 unitary holonomy matrices on plaquettes and performing a global
S3xS3 relabeling fit to PMNS/CKM target sines.

At each (n,m):
  - grid size is 2^n x 2^n with 4^n sites, indexed by Hilbert order n,
  - site label is w = Fold_m(k),
  - each stable word w has a preimage fiber under Fold_m over N in {0..2^m-1};
    we truncate/pad each fiber deterministically to rank 4,
  - edge transport is the minimum-cost bijection (4!) under Hamming cost on m-bit words,
    yielding an S4 permutation p per edge,
  - phase-lift the edge transport to a 4x4 unitary permutation matrix with phases
    using denom=2^m,
  - compute plaquette holonomies, project to 3D sum-zero subspace, renormalize to 3x3 unitary,
  - fit (s12,s23,s13) to PMNS and CKM targets allowing a global S3xS3 relabeling.

Outputs (LaTeX fragments):
  - sections/generated/holonomy_balanced_chain_fit_pmns_rows.tex
  - sections/generated/holonomy_balanced_chain_fit_ckm_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import exp_foldm_stats as foldm
import exp_hilbert_chirality_index as hil
import exp_holonomy_phase_lift_angles as ang
import exp_holonomy_phase_lift_cp_invariant as ph
from common_tex import write_lines


Coord = Tuple[int, int]
Perm4 = Tuple[int, int, int, int]
Perm3 = Tuple[int, int, int]


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
    if not xs:
        raise AssertionError("Empty fiber.")
    xs.sort()
    xs = xs[:4]
    while len(xs) < 4:
        xs.append(xs[-1])
    return xs


def best_perm(fa: List[int], fb: List[int], bits: List[str]) -> Perm4:
    a_bits = [bits[x] for x in fa]
    b_bits = [bits[x] for x in fb]
    best: Tuple[int, Perm4] | None = None
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


def inv_perm4(p: Perm4) -> Perm4:
    inv = [0, 0, 0, 0]
    for i, j in enumerate(p):
        inv[j] = i
    return (inv[0], inv[1], inv[2], inv[3])


def compose4(p: Perm4, q: Perm4) -> Perm4:
    return (p[q[0]], p[q[1]], p[q[2]], p[q[3]])


def cycle_type(p: Perm4) -> str:
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


def adjoint(U: List[List[complex]]) -> List[List[complex]]:
    n = len(U)
    return [[U[j][i].conjugate() for j in range(n)] for i in range(n)]


def perm_unitary(p: Perm4, fa: List[int], fb: List[int], denom: int) -> List[List[complex]]:
    U = [[0j] * 4 for _ in range(4)]
    for i in range(4):
        j = p[i]
        theta = 2.0 * math.pi * (float(fb[j] - fa[i]) / float(denom))
        U[j][i] = complex(math.cos(theta), math.sin(theta))
    return U


def permute_3x3(Q: List[List[complex]], r: Perm3, c: Perm3) -> List[List[complex]]:
    return [[Q[r[i]][c[j]] for j in range(3)] for i in range(3)]


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        return float("inf")
    return abs(math.log(pred / ref))


def mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else float("nan")


def best_perm_fit(Qs: List[List[List[complex]]], ref: Tuple[float, float, float]) -> Tuple[float, float, Perm3, Perm3, float, float, float]:
    perms = list(itertools.permutations((0, 1, 2), 3))
    best = None  # (Einf,E1,r,c)
    best_pred = (float("nan"), float("nan"), float("nan"))
    for r in perms:
        for c in perms:
            s12s: List[float] = []
            s23s: List[float] = []
            s13s: List[float] = []
            for Q in Qs:
                Qp = permute_3x3(Q, r=r, c=c)
                s12, s23, s13, _delta_deg, _J = ang.extract_angles(Qp)
                if math.isnan(s12) or math.isnan(s23) or math.isnan(s13):
                    continue
                s12s.append(s12)
                s23s.append(s23)
                s13s.append(s13)
            s12 = mean(s12s)
            s23 = mean(s23s)
            s13 = mean(s13s)
            e12 = abs_log_ratio(s12, ref[0])
            e23 = abs_log_ratio(s23, ref[1])
            e13 = abs_log_ratio(s13, ref[2])
            Einf = max(e12, e23, e13)
            E1 = e12 + e23 + e13
            cand = (Einf, E1, r, c)
            if best is None or cand < best:
                best = cand
                best_pred = (s12, s23, s13)
    if best is None:
        raise AssertionError("No permutations enumerated.")
    Einf, E1, r, c = best
    s12, s23, s13 = best_pred
    return Einf, E1, r, c, s12, s23, s13


def sweep_one(n_bits: int, m: int) -> Tuple[List[List[List[complex]]], float, Dict[str, int]]:
    """
    Return (Q3 list, mean_absJ, cycle-type histogram) for plaquettes at (n,m).
    """
    N = 1 << n_bits
    denom = 1 << m
    bits = [bits_m(k, m) for k in range(1 << m)]

    path = hil.hilbert_curve(n_bits)
    idx_of: Dict[Coord, int] = {}
    for k, c in enumerate(path):
        idx_of[(int(c[0]), int(c[1]))] = k

    labels: Dict[Coord, str] = {}
    for coord, k in idx_of.items():
        labels[coord] = foldm.foldm(k, m)

    pre = preimages(m)

    # Build edge permutation + unitary caches for undirected neighbor edges.
    perm_cache: Dict[Tuple[Coord, Coord], Perm4] = {}
    U_cache: Dict[Tuple[Coord, Coord], List[List[complex]]] = {}

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
                if (ka, kb) in perm_cache:
                    continue
                wa = labels[ka]
                wb = labels[kb]
                fa = fiber4(pre, wa)
                fb = fiber4(pre, wb)
                p = best_perm(fa, fb, bits=bits)
                perm_cache[(ka, kb)] = p
                U_cache[(ka, kb)] = perm_unitary(p, fa, fb, denom=denom)

    def perm_oriented(a: Coord, b: Coord) -> Perm4:
        ka, kb = key(a, b)
        p = perm_cache[(ka, kb)]
        return p if (a, b) == (ka, kb) else inv_perm4(p)

    def U_oriented(a: Coord, b: Coord) -> List[List[complex]]:
        ka, kb = key(a, b)
        U = U_cache[(ka, kb)]
        return U if (a, b) == (ka, kb) else adjoint(U)

    # Plaquettes.
    B = ph.basis_B()
    Qs: List[List[List[complex]]] = []
    Jabs: List[float] = []
    hist: Dict[str, int] = defaultdict(int)
    for x in range(N - 1):
        for y in range(N - 1):
            a = (x, y)
            b = (x + 1, y)
            c = (x + 1, y + 1)
            d = (x, y + 1)
            p_ab = perm_oriented(a, b)
            p_bc = perm_oriented(b, c)
            p_cd = perm_oriented(c, d)
            p_da = perm_oriented(d, a)
            hol_p = compose4(p_da, compose4(p_cd, compose4(p_bc, p_ab)))
            hist[cycle_type(hol_p)] += 1

            U_ab = U_oriented(a, b)
            U_bc = U_oriented(b, c)
            U_cd = U_oriented(c, d)
            U_da = U_oriented(d, a)
            H = matmul(U_da, matmul(U_cd, matmul(U_bc, U_ab)))
            M3 = ph.project_3x3(H, B=B)
            Q3 = ph.gram_schmidt_unitary(M3)
            if Q3 is None:
                continue
            Qs.append(Q3)
            Jabs.append(abs(ph.jarlskog_invariant(Q3)))

    return Qs, mean(Jabs), dict(hist)


def main() -> None:
    chain = [(3, 6), (4, 8), (5, 10)]
    pmns = (math.sqrt(0.307), math.sqrt(0.545), math.sqrt(0.0218))
    ckm = (0.2243, 0.0422, 0.00394)

    pmns_rows: List[str] = []
    ckm_rows: List[str] = []

    for n_bits, m in chain:
        Qs, Jm, hist = sweep_one(n_bits, m)
        Einf, E1, r, c, s12, s23, s13 = best_perm_fit(Qs, ref=pmns)
        pmns_rows.append(
            f"{n_bits} & {m} & {len(Qs)} & \\texttt{{{r}}}/\\texttt{{{c}}} & {s12:.4f} & {s23:.4f} & {s13:.4f} & {Einf:.3f} & {E1:.3f} & {Jm:.6g} \\\\"
        )
        Einf, E1, r, c, s12, s23, s13 = best_perm_fit(Qs, ref=ckm)
        ckm_rows.append(
            f"{n_bits} & {m} & {len(Qs)} & \\texttt{{{r}}}/\\texttt{{{c}}} & {s12:.4f} & {s23:.4f} & {s13:.4f} & {Einf:.3f} & {E1:.3f} & {Jm:.6g} \\\\"
        )

    pmns_rows.append("\\bottomrule")
    ckm_rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_balanced_chain_fit_pmns_rows.tex", pmns_rows)
    print("Wrote sections/generated/holonomy_balanced_chain_fit_pmns_rows.tex")
    write_lines(out_dir / "holonomy_balanced_chain_fit_ckm_rows.tex", ckm_rows)
    print("Wrote sections/generated/holonomy_balanced_chain_fit_ckm_rows.tex")


if __name__ == "__main__":
    main()


