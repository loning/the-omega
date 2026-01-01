# -*- coding: utf-8 -*-
"""
Loop-scale sweep for phase-lifted holonomy diagnostics (toy).

We generalize the unit-plaquette holonomy to k×k square loops on the n=3 (8×8) grid,
using the same deterministic S4 edge transport and the same phase-lifted unitary
edge transport at denom=64 by default.

For each k in {1,2,3}:
  - enumerate all k×k square loops (lower-left corners) on the 8×8 grid,
  - compute the S4 holonomy permutation (cycle type summary),
  - compute the phase-lifted 4×4 unitary holonomy, project to 3×3, renormalize to unitary,
  - restrict to nontrivial 3/4-cycle loops and run a global S3×S3 relabeling fit to
    PMNS/CKM target sines.

Outputs (LaTeX fragments):
  - sections/generated/holonomy_loop_scale_cycle_rows.tex
  - sections/generated/holonomy_loop_scale_fit_pmns_rows.tex
  - sections/generated/holonomy_loop_scale_fit_ckm_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import exp_holonomy_loops as holo
import exp_holonomy_phase_lift_angles as ang
import exp_holonomy_phase_lift_cp_invariant as ph
from common_tex import write_lines


Coord = Tuple[int, int]
Perm4 = Tuple[int, int, int, int]
Perm3 = Tuple[int, int, int]
U3 = List[List[complex]]


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


def eye(n: int) -> List[List[complex]]:
    return [[1.0 + 0j if i == j else 0j for j in range(n)] for i in range(n)]


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        return float("inf")
    return abs(math.log(pred / ref))


def mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else float("nan")


def perm_identity() -> Perm4:
    return (0, 1, 2, 3)


def compose4(p: Perm4, q: Perm4) -> Perm4:
    return (p[q[0]], p[q[1]], p[q[2]], p[q[3]])


def loop_edges_square(x: int, y: int, k: int) -> List[Tuple[Coord, Coord]]:
    """
    Return the ordered directed edges along the boundary of the k×k square with
    lower-left corner (x,y): go right, up, left, down.
    """
    edges: List[Tuple[Coord, Coord]] = []
    # Bottom: (x+i,y)->(x+i+1,y)
    for i in range(k):
        edges.append(((x + i, y), (x + i + 1, y)))
    # Right: (x+k,y+i)->(x+k,y+i+1)
    for i in range(k):
        edges.append(((x + k, y + i), (x + k, y + i + 1)))
    # Top: (x+k-i,y+k)->(x+k-i-1,y+k)
    for i in range(k):
        edges.append(((x + k - i, y + k), (x + k - i - 1, y + k)))
    # Left: (x,y+k-i)->(x,y+k-i-1)
    for i in range(k):
        edges.append(((x, y + k - i), (x, y + k - i - 1)))
    return edges


def collect_Qs_for_k(k: int, denom: int = 64) -> Tuple[List[U3], Counter]:
    labels = holo.grid_labels(n_bits=3)
    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)

    B = ph.basis_B()
    Qs: List[U3] = []
    hist = Counter()

    max_xy = 8 - k - 1  # last lower-left coordinate is 7-k
    for x in range(max_xy + 1):
        for y in range(max_xy + 1):
            edges = loop_edges_square(x, y, k=k)
            hol_p = perm_identity()
            H = eye(4)
            for a, b in edges:
                p_ab = edge_p[(a, b)]
                hol_p = compose4(p_ab, hol_p)
                U_ab = ph.edge_unitary_with_denom(a, b, labels, pre, edge_p, denom=denom, map_name="id", bits=6)
                H = matmul(U_ab, H)
            ct = holo.cycle_type(hol_p)
            hist[ct] += 1
            if ct not in ("3", "4"):
                continue
            M3 = ph.project_3x3(H, B=B)
            Q = ph.gram_schmidt_unitary(M3)
            if Q is None:
                continue
            Qs.append(Q)
    return Qs, hist


def best_perm_fit(Qs: List[U3], ref: Tuple[float, float, float]) -> Tuple[float, float, Perm3, Perm3, float, float, float]:
    perms = list(itertools.permutations((0, 1, 2), 3))
    best = None  # (Einf,E1,r,c)
    best_pred = (float("nan"), float("nan"), float("nan"))
    for r in perms:
        for c in perms:
            s12s: List[float] = []
            s23s: List[float] = []
            s13s: List[float] = []
            for Q in Qs:
                Qp = [[Q[r[i]][c[j]] for j in range(3)] for i in range(3)]
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


def main() -> None:
    ks = list(range(1, 8))
    denom = 64

    pmns = (math.sqrt(0.307), math.sqrt(0.545), math.sqrt(0.0218))
    ckm = (0.2243, 0.0422, 0.00394)

    cycle_rows: List[str] = []
    pmns_rows: List[str] = []
    ckm_rows: List[str] = []

    for k in ks:
        Qs, hist = collect_Qs_for_k(k=k, denom=denom)
        total = (8 - k) * (8 - k)
        count34 = hist.get("3", 0) + hist.get("4", 0)
        mean_absJ = mean([abs(ph.jarlskog_invariant(Q)) for Q in Qs])

        cycle_rows.append(
            f"{k} & {total} & {hist.get('1',0)} & {hist.get('2',0)} & {hist.get('2x2',0)} & {hist.get('3',0)} & {hist.get('4',0)} & {hist.get('other',0)} \\\\"
        )

        Einf, E1, r, c, s12, s23, s13 = best_perm_fit(Qs, ref=pmns)
        pmns_rows.append(
            f"{k} & {total} & {count34} & \\texttt{{{r}}}/\\texttt{{{c}}} & {s12:.4f} & {s23:.4f} & {s13:.4f} & {Einf:.3f} & {E1:.3f} & {mean_absJ:.6g} \\\\"
        )

        Einf, E1, r, c, s12, s23, s13 = best_perm_fit(Qs, ref=ckm)
        ckm_rows.append(
            f"{k} & {total} & {count34} & \\texttt{{{r}}}/\\texttt{{{c}}} & {s12:.4f} & {s23:.4f} & {s13:.4f} & {Einf:.3f} & {E1:.3f} & {mean_absJ:.6g} \\\\"
        )

    cycle_rows.append("\\bottomrule")
    pmns_rows.append("\\bottomrule")
    ckm_rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_loop_scale_cycle_rows.tex", cycle_rows)
    print("Wrote sections/generated/holonomy_loop_scale_cycle_rows.tex")
    write_lines(out_dir / "holonomy_loop_scale_fit_pmns_rows.tex", pmns_rows)
    print("Wrote sections/generated/holonomy_loop_scale_fit_pmns_rows.tex")
    write_lines(out_dir / "holonomy_loop_scale_fit_ckm_rows.tex", ckm_rows)
    print("Wrote sections/generated/holonomy_loop_scale_fit_ckm_rows.tex")


if __name__ == "__main__":
    main()


