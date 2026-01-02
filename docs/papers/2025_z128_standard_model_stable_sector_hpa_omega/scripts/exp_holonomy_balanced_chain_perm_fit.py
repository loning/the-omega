# -*- coding: utf-8 -*-
"""
Balanced-chain permutation-robust fits for phase-lifted holonomy angles (toy).

We extend the balanced chain sweep (n,m) = (3,6),(4,8),(5,10),(6,12),(7,14),(8,16) by extracting
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
import exp_holonomy_phase_lift_cp_invariant as ph
from common_progress import ProgressEvery
from common_tex import write_lines


Coord = Tuple[int, int]
Perm4 = Tuple[int, int, int, int]
Perm3 = Tuple[int, int, int]


def hamming(a: int, b: int) -> int:
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


def compose_mono(p: Perm4, a: List[complex], q: Perm4, b: List[complex]) -> Tuple[Perm4, List[complex]]:
    """
    Compose two 4x4 monomial unitaries:
      U_p * U_q  ->  U_r
    where U_p has columns mapping i -> p[i] with phase a[i] at row p[i],
    and similarly for (q,b).
    """
    r = compose4(p, q)
    c = [a[q[i]] * b[i] for i in range(4)]
    return r, c


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


def best_perm(fa: List[int], fb: List[int]) -> Perm4:
    best: Tuple[int, Perm4] | None = None
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


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        return float("inf")
    return abs(math.log(pred / ref))


def mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else float("nan")


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def sweep_one(n_bits: int, m: int) -> Tuple[List[Tuple[Perm3, Perm3, float, float, float, int]], float, Dict[str, int], int]:
    """
    Return:
      - permutation-pair means: list of (r,c,mean_s12,mean_s23,mean_s13,count)
      - mean_absJ over valid plaquettes
      - cycle-type histogram (over all plaquettes)
      - number of valid plaquettes (rank-pass)
    """
    N = 1 << n_bits
    denom = 1 << m
    phases = phase_table(denom)

    path = hil.hilbert_curve(n_bits)
    idx_of: Dict[Coord, int] = {}
    for k, c in enumerate(path):
        idx_of[(int(c[0]), int(c[1]))] = k

    outs = foldm.cached_foldm_outputs(m)
    labels: Dict[Coord, str] = {}
    for coord, k in idx_of.items():
        labels[coord] = outs[k]

    # Fiber4 map is cached on disk (padded to rank 4).
    fibers = foldm.cached_fiber4_map(m, rank=4)

    # Build undirected edge permutation cache for neighbor edges.
    perm_cache: Dict[Tuple[Coord, Coord], Perm4] = {}

    def key(a: Coord, b: Coord) -> Tuple[Coord, Coord]:
        return (a, b) if a < b else (b, a)

    total_edges = 2 * N * (N - 1)
    prog_edges = ProgressEvery(label=f"permfit_edges n={n_bits} m={m}", total=total_edges, interval_s=60.0)
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
                perm_cache[(ka, kb)] = best_perm(fa, fb)
                done_edges += 1
                prog_edges.maybe(done_edges)
    prog_edges.done(extra=f"edges={done_edges}")

    def edge_mono(a: Coord, b: Coord) -> Tuple[Perm4, List[complex]]:
        ka, kb = key(a, b)
        p0 = perm_cache[(ka, kb)]
        p = p0 if (a, b) == (ka, kb) else inv_perm4(p0)
        wa = labels[a]
        wb = labels[b]
        fa = fibers[wa]
        fb = fibers[wb]
        a_phase = [phases[fb[p[i]]] * phases[fa[i]].conjugate() for i in range(4)]
        return p, a_phase

    # Plaquettes.
    B = ph.basis_B()
    hist: Dict[str, int] = defaultdict(int)
    Jabs_sum = 0.0
    Jabs_n = 0

    perms = list(itertools.permutations((0, 1, 2), 3))
    pair_index: List[Tuple[Perm3, Perm3, int, int, int, int]] = []
    for r in perms:
        for c in perms:
            pair_index.append((r, c, r[0], r[1], c[1], c[2]))
    sums12 = [0.0] * len(pair_index)
    sums23 = [0.0] * len(pair_index)
    sums13 = [0.0] * len(pair_index)
    counts = [0] * len(pair_index)
    valid = 0

    total_plaq = (N - 1) * (N - 1)
    prog_plaq = ProgressEvery(label=f"permfit_plaquettes n={n_bits} m={m}", total=total_plaq, interval_s=60.0)
    prog_plaq.start()
    done_plaq = 0
    for x in range(N - 1):
        for y in range(N - 1):
            done_plaq += 1
            prog_plaq.maybe(done_plaq)
            a = (x, y)
            b = (x + 1, y)
            c = (x + 1, y + 1)
            d = (x, y + 1)
            p_ab, a_ab = edge_mono(a, b)
            p_bc, a_bc = edge_mono(b, c)
            p_cd, a_cd = edge_mono(c, d)
            p_da, a_da = edge_mono(d, a)

            hol_p, hol_a = compose_mono(p_bc, a_bc, p_ab, a_ab)
            hol_p, hol_a = compose_mono(p_cd, a_cd, hol_p, hol_a)
            hol_p, hol_a = compose_mono(p_da, a_da, hol_p, hol_a)
            hist[cycle_type(hol_p)] += 1

            H = [[0j] * 4 for _ in range(4)]
            for i in range(4):
                H[hol_p[i]][i] = hol_a[i]
            M3 = ph.project_3x3(H, B=B)
            Q3 = ph.gram_schmidt_unitary(M3)
            if Q3 is None:
                continue
            valid += 1
            Jabs_sum += abs(ph.jarlskog_invariant(Q3))
            Jabs_n += 1

            absQ = [[abs(Q3[i][j]) for j in range(3)] for i in range(3)]
            for idx, (_r, _c, r0, r1, c1, c2) in enumerate(pair_index):
                s13 = absQ[r0][c2]
                s13 = clamp(s13, 0.0, 1.0)
                c13 = math.sqrt(max(0.0, 1.0 - s13 * s13))
                if c13 == 0.0:
                    continue
                s12 = clamp(absQ[r0][c1] / c13, 0.0, 1.0)
                s23 = clamp(absQ[r1][c2] / c13, 0.0, 1.0)
                sums12[idx] += s12
                sums23[idx] += s23
                sums13[idx] += s13
                counts[idx] += 1

    prog_plaq.done(extra=f"valid={valid}")
    means: List[Tuple[Perm3, Perm3, float, float, float, int]] = []
    for idx, (r, c, _r0, _r1, _c1, _c2) in enumerate(pair_index):
        n = counts[idx]
        if n <= 0:
            continue
        means.append((r, c, sums12[idx] / float(n), sums23[idx] / float(n), sums13[idx] / float(n), n))

    Jm = (Jabs_sum / float(Jabs_n)) if Jabs_n > 0 else float("nan")
    return means, Jm, dict(hist), valid


def best_fit_from_means(
    means: List[Tuple[Perm3, Perm3, float, float, float, int]],
    ref: Tuple[float, float, float],
) -> Tuple[float, float, Perm3, Perm3, float, float, float]:
    best = None  # (Einf,E1,r,c)
    best_pred = (float("nan"), float("nan"), float("nan"))
    for r, c, s12, s23, s13, _n in means:
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
        raise AssertionError("No permutation pairs had any valid samples.")
    Einf, E1, r, c = best
    s12, s23, s13 = best_pred
    return Einf, E1, r, c, s12, s23, s13


def main() -> None:
    chain = [(3, 6), (4, 8), (5, 10), (6, 12), (7, 14), (8, 16)]
    pmns = (math.sqrt(0.307), math.sqrt(0.545), math.sqrt(0.0218))
    ckm = (0.2243, 0.0422, 0.00394)

    pmns_rows: List[str] = []
    ckm_rows: List[str] = []

    for n_bits, m in chain:
        means, Jm, _hist, valid = sweep_one(n_bits, m)
        Einf, E1, r, c, s12, s23, s13 = best_fit_from_means(means, ref=pmns)
        pmns_rows.append(
            f"{n_bits} & {m} & {valid} & \\texttt{{{r}}}/\\texttt{{{c}}} & {s12:.4f} & {s23:.4f} & {s13:.4f} & {Einf:.3f} & {E1:.3f} & {Jm:.6g} \\\\"
        )
        Einf, E1, r, c, s12, s23, s13 = best_fit_from_means(means, ref=ckm)
        ckm_rows.append(
            f"{n_bits} & {m} & {valid} & \\texttt{{{r}}}/\\texttt{{{c}}} & {s12:.4f} & {s23:.4f} & {s13:.4f} & {Einf:.3f} & {E1:.3f} & {Jm:.6g} \\\\"
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


