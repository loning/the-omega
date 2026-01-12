# -*- coding: utf-8 -*-
"""
Balanced-chain sweep for finite holonomy and phase-lift CP signal.

We consider the balanced chain m=2n with (n,m) in {(1,2),(2,4),(3,6),(4,8),(5,10),(6,12),(7,14),(8,16)}.
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
from common_progress import ProgressEvery
from common_tex import write_lines


Coord = Tuple[int, int]
Perm = Tuple[int, int, int, int]


def hamming(a: int, b: int) -> int:
    # Hamming distance on m-bit words represented as integers in [0,2^m).
    return (a ^ b).bit_count()


def phase_table(denom: int) -> List[complex]:
    """
    Return phases[k] = exp(2*pi*i*k/denom) for k=0..denom-1.
    Constructed iteratively for determinism and speed.
    """
    if denom <= 0:
        raise ValueError("denom must be positive.")
    step = 2.0 * math.pi / float(denom)
    root = complex(math.cos(step), math.sin(step))
    out = [0j] * denom
    z = 1.0 + 0j
    for k in range(denom):
        out[k] = z
        z *= root
    return out


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
    best: Tuple[int, Perm] | None = None
    for p in itertools.permutations((0, 1, 2, 3), 4):
        cost = 0
        for i in range(4):
            cost += hamming(fa[i], fb[p[i]])
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
    outs = foldm.cached_foldm_outputs(m)
    out: Dict[Coord, str] = {}
    for coord, k in idx_of.items():
        out[coord] = outs[k]
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


def compose_mono(p: Perm, a: List[complex], q: Perm, b: List[complex]) -> Tuple[Perm, List[complex]]:
    """
    Compose two 4x4 monomial unitaries:
      U_p * U_q  ->  U_r
    where U_p has columns mapping i -> p[i] with phase a[i] at row p[i],
    and similarly for (q,b).
    """
    r = compose(p, q)
    c = [a[q[i]] * b[i] for i in range(4)]
    return r, c


def sweep_one(
    n_bits: int, m: int
) -> Tuple[Counter[str], Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, float], int]:
    N = 1 << n_bits
    denom = 1 << m  # denom = 2^m

    labels = grid_labels(n_bits, m)
    fibers = foldm.cached_fiber4_map(m, rank=4)
    phases = phase_table(denom)

    # Undirected edge permutation cache (store only for the canonical ordered endpoints).
    perm_cache: Dict[Tuple[Coord, Coord], Perm] = {}

    def key(a: Coord, b: Coord) -> Tuple[Coord, Coord]:
        return (a, b) if a < b else (b, a)

    # Edge build progress.
    total_edges = 2 * N * (N - 1)
    prog_edges = ProgressEvery(label=f"holonomy_edges n={n_bits} m={m}", total=total_edges, interval_s=60.0)
    prog_edges.start()
    done_edges = 0
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
                fa = fibers[wa]
                fb = fibers[wb]
                perm_cache[(ka, kb)] = best_perm(fa, fb, m=m)
                done_edges += 1
                prog_edges.maybe(done_edges)
    prog_edges.done(extra=f"edges={done_edges}")

    hist = Counter()
    ct_count: Dict[str, int] = defaultdict(int)
    ct_sum_abs: Dict[str, float] = defaultdict(float)
    ct_sum_signed: Dict[str, float] = defaultdict(float)
    ct_sum_W: Dict[str, float] = defaultdict(float)
    ct_sum_A: Dict[str, float] = defaultdict(float)
    failures = 0
    B = basis_B()

    total_plaq = (N - 1) * (N - 1)
    prog_plaq = ProgressEvery(label=f"holonomy_plaquettes n={n_bits} m={m}", total=total_plaq, interval_s=60.0)
    prog_plaq.start()
    done_plaq = 0
    valid_plaq = 0
    for x in range(N - 1):
        for y in range(N - 1):
            done_plaq += 1
            prog_plaq.maybe(done_plaq)
            a = (x, y)
            b = (x + 1, y)
            c = (x + 1, y + 1)
            d = (x, y + 1)

            def edge_mono(u: Coord, v: Coord) -> Tuple[Perm, List[complex]]:
                ku, kv = key(u, v)
                p0 = perm_cache[(ku, kv)]
                p = p0 if (u, v) == (ku, kv) else inv_perm(p0)
                wu = labels[u]
                wv = labels[v]
                fu = fibers[wu]
                fv = fibers[wv]
                a_phase = [phases[fv[p[i]]] * phases[fu[i]].conjugate() for i in range(4)]
                return p, a_phase

            p_ab, a_ab = edge_mono(a, b)
            p_bc, a_bc = edge_mono(b, c)
            p_cd, a_cd = edge_mono(c, d)
            p_da, a_da = edge_mono(d, a)

            hol_p, hol_a = compose_mono(p_bc, a_bc, p_ab, a_ab)
            hol_p, hol_a = compose_mono(p_cd, a_cd, hol_p, hol_a)
            hol_p, hol_a = compose_mono(p_da, a_da, hol_p, hol_a)

            ct = cycle_type(hol_p)
            hist[ct] += 1

            # Phase-lifted unitary holonomy.
            H = [[0j] * 4 for _ in range(4)]
            for i in range(4):
                H[hol_p[i]][i] = hol_a[i]
            M = project_3x3(H, B=B)
            Q = gram_schmidt_unitary(M)
            if Q is None:
                failures += 1
                continue
            J = jarlskog(Q)
            tr = float((Q[0][0] + Q[1][1] + Q[2][2]).real)
            W = tr / 3.0
            A = 1.0 - W
            ct_count[ct] += 1
            ct_sum_abs[ct] += abs(J)
            ct_sum_signed[ct] += J
            ct_sum_W[ct] += W
            ct_sum_A[ct] += A
            valid_plaq += 1
    prog_plaq.done(extra=f"valid={valid_plaq} failures={failures}")

    mean_abs: Dict[str, float] = {}
    mean_signed: Dict[str, float] = {}
    mean_W: Dict[str, float] = {}
    mean_A: Dict[str, float] = {}
    for ct in ["1", "2", "2x2", "3", "4", "other"]:
        nct = ct_count.get(ct, 0)
        if nct <= 0:
            mean_abs[ct] = 0.0
            mean_signed[ct] = 0.0
            mean_W[ct] = 0.0
            mean_A[ct] = 0.0
        else:
            mean_abs[ct] = ct_sum_abs.get(ct, 0.0) / float(nct)
            mean_signed[ct] = ct_sum_signed.get(ct, 0.0) / float(nct)
            mean_W[ct] = ct_sum_W.get(ct, 0.0) / float(nct)
            mean_A[ct] = ct_sum_A.get(ct, 0.0) / float(nct)
    return hist, mean_abs, mean_signed, mean_W, mean_A, failures


def _tv_distance(p: Dict[str, float], q: Dict[str, float]) -> float:
    keys = set(p.keys()) | set(q.keys())
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def main() -> None:
    chain = [(1, 2), (2, 4), (3, 6), (4, 8), (5, 10), (6, 12), (7, 14), (8, 16)]

    rows: List[str] = []
    rows_wilson: List[str] = []
    rows_conv: List[str] = []

    prev_dist: Dict[str, float] | None = None
    for n_bits, m in chain:
        hist, mean_abs, mean_signed, mean_W, mean_A, failures = sweep_one(n_bits, m)
        Np = (1 << n_bits) - 1
        total_plaq = Np * Np
        # Focus cycle-type counts and CP signal on 3/4 cycles.
        c1 = hist.get("1", 0)
        c2 = hist.get("2", 0)
        c22 = hist.get("2x2", 0)
        c3 = hist.get("3", 0)
        c4 = hist.get("4", 0)
        c34 = c3 + c4
        meanJ34 = (float(c3) * mean_abs.get("3", 0.0) + float(c4) * mean_abs.get("4", 0.0)) / float(max(1, c3 + c4))
        meanJ34s = (float(c3) * mean_signed.get("3", 0.0) + float(c4) * mean_signed.get("4", 0.0)) / float(max(1, c3 + c4))
        meanW34 = (float(c3) * mean_W.get("3", 0.0) + float(c4) * mean_W.get("4", 0.0)) / float(max(1, c3 + c4))
        meanA34 = (float(c3) * mean_A.get("3", 0.0) + float(c4) * mean_A.get("4", 0.0)) / float(max(1, c3 + c4))
        rows.append(
            f"{n_bits} & {m} & {total_plaq} & {c1} & {c2} & {c22} & {c3} & {c4} & {meanJ34:.6g} & {meanJ34s:+.6g} & {failures} \\\\"
        )
        rows_wilson.append(
            f"{n_bits} & {m} & {total_plaq} & {c34} & {meanW34:.6g} & {meanA34:.6g} \\\\"
        )

        # CL1-facing convergence audit: cycle-type distribution distances across scales.
        dist = {}
        for ct in ["1", "2", "2x2", "3", "4", "other"]:
            dist[ct] = float(hist.get(ct, 0)) / float(max(1, total_plaq))
        if prev_dist is None:
            rows_conv.append(f"{n_bits} & {m} & -- & -- \\\\")
        else:
            tv = _tv_distance(prev_dist, dist)
            max_abs = max(abs(prev_dist.get(ct, 0.0) - dist.get(ct, 0.0)) for ct in dist.keys())
            rows_conv.append(f"{n_bits} & {m} & {tv:.6g} & {max_abs:.6g} \\\\")
        prev_dist = dist

    rows.append("\\bottomrule")
    rows_wilson.append("\\bottomrule")
    rows_conv.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_balanced_chain_rows.tex", rows)
    write_lines(out_dir / "holonomy_balanced_chain_wilson_rows.tex", rows_wilson)
    write_lines(out_dir / "holonomy_balanced_chain_convergence_rows.tex", rows_conv)
    print("Wrote sections/generated/holonomy_balanced_chain_rows.tex")
    print("Wrote sections/generated/holonomy_balanced_chain_wilson_rows.tex")
    print("Wrote sections/generated/holonomy_balanced_chain_convergence_rows.tex")


if __name__ == "__main__":
    main()


