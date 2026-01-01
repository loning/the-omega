# -*- coding: utf-8 -*-
"""
Single-loop best-fit scan for holonomy→mixing diagnostics (toy).

Instead of averaging angles over a loop family, we scan individual k×k square loops
(k=1..7) on the n=3 grid, together with a bounded phase-denominator family
denom=2^p (p=6..18) and a global S3×S3 relabeling, to find the best-fitting single
effective holonomy matrix for PMNS- and CKM-style target sines.

This is a bounded-complexity selection problem over a finite search space.

Outputs (LaTeX fragment):
  - sections/generated/holonomy_single_loop_bestfit_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path
from typing import List, Tuple, Optional

import exp_holonomy_loops as holo
import exp_holonomy_loop_scale_sweep as ls
import exp_holonomy_phase_lift_angles as ang
import exp_holonomy_phase_lift_cp_invariant as ph
from common_tex import write_lines


Coord = Tuple[int, int]
Perm3 = Tuple[int, int, int]


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0 or math.isnan(pred):
        return float("inf")
    return abs(math.log(pred / ref))


def eye4() -> List[List[complex]]:
    return [[1.0 + 0j if i == j else 0j for j in range(4)] for i in range(4)]


def best_two_for_target(
    ref: Tuple[float, float, float],
) -> Tuple[
    Tuple[float, float, int, str, int, int, int, int, str, Perm3, Perm3],
    Tuple[float, float, float, float],
    Tuple[float, float, int, str, int, int, int, int, str, Perm3, Perm3],
    Tuple[float, float, float, float],
]:
    """
    Return (best_key, best_pred, second_key, second_pred), where keys are:
      key = (Einf,E1, map_rank, map_name, denom,k,x,y, ct, rperm, cperm)
    """
    labels = holo.grid_labels(n_bits=3)
    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)
    B = ph.basis_B()

    map_rank = {"id": 0, "gray": 1, "bitrev": 2, "not": 3}
    map_names = ["id", "gray", "bitrev", "not"]
    denoms = [1 << p for p in range(6, 19)]
    perms = list(itertools.permutations((0, 1, 2), 3))

    best: Optional[Tuple[float, float, int, str, int, int, int, int, str, Perm3, Perm3]] = None
    second: Optional[Tuple[float, float, int, str, int, int, int, int, str, Perm3, Perm3]] = None
    best_pred: Optional[Tuple[float, float, float, float]] = None
    second_pred: Optional[Tuple[float, float, float, float]] = None

    for map_name in map_names:
        mr = map_rank[map_name]
        for denom in denoms:
            for k in range(1, 8):
                max_xy = 8 - k - 1
                for x in range(max_xy + 1):
                    for y in range(max_xy + 1):
                        hol_p = (0, 1, 2, 3)
                        H = eye4()
                        for a, b in ls.loop_edges_square(x, y, k=k):
                            p_ab = edge_p[(a, b)]
                            hol_p = holo.compose(p_ab, hol_p)
                            U_ab = ph.edge_unitary_with_denom(
                                a, b, labels, pre, edge_p, denom=denom, map_name=map_name, bits=6
                            )
                            H = ph.matmul(U_ab, H)
                        ct = holo.cycle_type(hol_p)

                        M3 = ph.project_3x3(H, B=B)
                        Q = ph.gram_schmidt_unitary(M3)
                        if Q is None:
                            continue

                        # Global permutation search.
                        for r in perms:
                            for c in perms:
                                Qp = [[Q[r[i]][c[j]] for j in range(3)] for i in range(3)]
                                s12, s23, s13, _delta_deg, J = ang.extract_angles(Qp)
                                e12 = abs_log_ratio(s12, ref[0])
                                e23 = abs_log_ratio(s23, ref[1])
                                e13 = abs_log_ratio(s13, ref[2])
                                Einf = max(e12, e23, e13)
                                E1 = e12 + e23 + e13
                                cand = (Einf, E1, mr, map_name, denom, k, x, y, ct, r, c)
                                pred = (s12, s23, s13, abs(J))
                                if best is None or cand < best:
                                    if best is not None:
                                        second = best
                                        second_pred = best_pred
                                    best = cand
                                    best_pred = pred
                                    continue
                                if best is not None and cand == best:
                                    continue
                                if second is None or cand < second:
                                    second = cand
                                    second_pred = pred

    if best is None or best_pred is None:
        raise AssertionError("No candidates enumerated.")
    if second is None or second_pred is None:
        second = best
        second_pred = best_pred
    return best, best_pred, second, second_pred


def main() -> None:
    pmns = (math.sqrt(0.307), math.sqrt(0.545), math.sqrt(0.0218))
    ckm = (0.2243, 0.0422, 0.00394)

    rows: List[str] = []
    for name, ref in [("PMNS", pmns), ("CKM", ckm)]:
        best, pred, second, _pred2 = best_two_for_target(ref)
        Einf, E1, _mr, map_name, denom, k, x, y, ct, r, c = best
        s12, s23, s13, Jabs = pred
        Einf2, E1_2, _mr2, map_name2, denom2, k2, x2, y2, ct2, r2, c2 = second
        gap = Einf2 - Einf
        rows.append(
            f"\\texttt{{{name}}} & \\texttt{{{map_name}}} & {denom} & {k} & ({x},{y}) & \\texttt{{{ct}}} & \\texttt{{{r}}}/\\texttt{{{c}}} & {s12:.4f} & {s23:.4f} & {s13:.6g} & {Jabs:.6g} & {Einf:.3f} & {E1:.3f} & {Einf2:.3f} & {gap:.3f} \\\\"
        )
    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_single_loop_bestfit_rows.tex", rows)
    print("Wrote sections/generated/holonomy_single_loop_bestfit_rows.tex")


if __name__ == "__main__":
    main()


