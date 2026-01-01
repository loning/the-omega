# -*- coding: utf-8 -*-
"""
Permutation-robust bounded-complexity fits for phase-lifted holonomy angles (toy).

For each denom = 2^p in a bounded range, we:
  - compute effective 3x3 unitary matrices Q from phase-lifted plaquette holonomies
    (restricted to the nontrivial 3/4-cycle subset),
  - search over a *global* row/column relabeling (S3 x S3) to minimize mismatch
    to a target triple of sines (s12,s23,s13) in PDG parameterization.

Targets:
  - PMNS: s12=sqrt(0.307), s23=sqrt(0.545), s13=sqrt(0.0218)
  - CKM:  s12=0.2243, s23=0.0422, s13=0.00394  (consistent with PDG magnitudes used elsewhere)

Objective (audit form) for each candidate (denom,rperm,cperm):
  e_i = |log(pred_i / ref_i)|,  E_inf=max_i e_i,  E1=sum_i e_i
Tie-break by (E_inf, E1, p, rperm, cperm).

Outputs (LaTeX fragments):
  - sections/generated/holonomy_perm_fit_pmns_rows.tex
  - sections/generated/holonomy_perm_fit_ckm_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path
from typing import Dict, List, Tuple

import exp_holonomy_loops as holo
import exp_holonomy_phase_lift_angles as ang
import exp_holonomy_phase_lift_cp_invariant as ph
from common_tex import write_lines


Perm3 = Tuple[int, int, int]
U3 = List[List[complex]]


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        return float("inf")
    return abs(math.log(pred / ref))


def permute(Q: U3, r: Perm3, c: Perm3) -> U3:
    return [[Q[r[i]][c[j]] for j in range(3)] for i in range(3)]


def collect_Qs_34(denom: int) -> List[U3]:
    Qs: List[U3] = []
    for p, H in ph.plaquette_unitary_holonomies(denom=denom):
        ct = holo.cycle_type(p)
        if ct not in ("3", "4"):
            continue
        M = ph.project_3x3(H, B=ph.basis_B())
        Q = ph.gram_schmidt_unitary(M)
        if Q is None:
            continue
        Qs.append(Q)
    return Qs


def mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else float("nan")


def predict_sines(Qs: List[U3], r: Perm3, c: Perm3) -> Tuple[float, float, float]:
    s12s: List[float] = []
    s23s: List[float] = []
    s13s: List[float] = []
    for Q in Qs:
        Qp = permute(Q, r, c)
        s12, s23, s13, _delta_deg, _J = ang.extract_angles(Qp)
        if math.isnan(s12) or math.isnan(s23) or math.isnan(s13):
            continue
        s12s.append(s12)
        s23s.append(s23)
        s13s.append(s13)
    return mean(s12s), mean(s23s), mean(s13s)


def best_perm_for_target(Qs: List[U3], ref: Tuple[float, float, float]) -> Tuple[Tuple[float, float, int, Perm3, Perm3], Tuple[float, float, float]]:
    perms = list(itertools.permutations((0, 1, 2), 3))
    best = None  # (Einf,E1,pidx,r,c)
    best_pred = (float("nan"), float("nan"), float("nan"))
    for r in perms:
        for c in perms:
            s12, s23, s13 = predict_sines(Qs, r=r, c=c)
            e12 = abs_log_ratio(s12, ref[0])
            e23 = abs_log_ratio(s23, ref[1])
            e13 = abs_log_ratio(s13, ref[2])
            Einf = max(e12, e23, e13)
            E1 = e12 + e23 + e13
            cand = (Einf, E1, 0, r, c)
            if best is None or cand < best:
                best = cand
                best_pred = (s12, s23, s13)
    if best is None:
        raise AssertionError("No permutations enumerated.")
    return best, best_pred


def emit_table(tag: str, ref: Tuple[float, float, float], denoms: List[int], out_path: Path) -> None:
    rows = []
    best_overall = None  # (Einf,E1,denom,r,c)
    cache: Dict[int, Tuple[float, float, Perm3, Perm3, float, float, float]] = {}
    for denom in denoms:
        Qs = collect_Qs_34(denom)
        (Einf, E1, _z, r, c), (s12, s23, s13) = best_perm_for_target(Qs, ref=ref)
        cache[denom] = (Einf, E1, r, c, s12, s23, s13)
        cand = (Einf, E1, denom, r, c)
        if best_overall is None or cand < best_overall:
            best_overall = cand

    best_denom = best_overall[2] if best_overall is not None else denoms[0]
    best_Einf = best_overall[0] if best_overall is not None else float("nan")
    second_Einf = float("nan")
    # Find second-best denom (by best permutation) for a gap diagnostic.
    sorted_denoms = sorted(denoms, key=lambda d: (cache[d][0], cache[d][1], d, cache[d][2], cache[d][3]))
    if len(sorted_denoms) >= 2:
        second_Einf = cache[sorted_denoms[1]][0]
    gap = second_Einf - best_Einf if not math.isnan(second_Einf) and not math.isnan(best_Einf) else float("nan")

    for denom in denoms:
        p = int(round(math.log2(denom)))
        Einf, E1, r, c, s12, s23, s13 = cache[denom]
        denom_tex = str(denom)
        Einf_tex = f"{Einf:.3f}"
        E1_tex = f"{E1:.3f}"
        perm_tex = rf"\texttt{{{r}}}/\texttt{{{c}}}"
        if denom == best_denom:
            denom_tex = rf"\textbf{{{denom_tex}}}"
            Einf_tex = rf"\textbf{{{Einf_tex}}}"
            E1_tex = rf"\textbf{{{E1_tex}}}"
        rows.append(f"{denom_tex} & {p} & {perm_tex} & {s12:.4f} & {s23:.4f} & {s13:.4f} & {Einf_tex} & {E1_tex} \\\\")

    # Summary row.
    gap_tex = f"{gap:.3f}" if not math.isnan(gap) else "$-$"
    rows.append(rf"\texttt{{best/second}} & $-$ & $-$ & $-$ & $-$ & $-$ & {best_Einf:.3f}/{second_Einf:.3f} & $\Delta={gap_tex}$ \\")
    rows.append("\\bottomrule")

    write_lines(out_path, rows)


def main() -> None:
    p_min, p_max = 6, 18
    denoms = [1 << p for p in range(p_min, p_max + 1)]

    # Targets.
    pmns = (math.sqrt(0.307), math.sqrt(0.545), math.sqrt(0.0218))
    ckm = (0.2243, 0.0422, 0.00394)

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    emit_table("pmns", pmns, denoms, out_dir / "holonomy_perm_fit_pmns_rows.tex")
    print("Wrote sections/generated/holonomy_perm_fit_pmns_rows.tex")
    emit_table("ckm", ckm, denoms, out_dir / "holonomy_perm_fit_ckm_rows.tex")
    print("Wrote sections/generated/holonomy_perm_fit_ckm_rows.tex")


if __name__ == "__main__":
    main()


