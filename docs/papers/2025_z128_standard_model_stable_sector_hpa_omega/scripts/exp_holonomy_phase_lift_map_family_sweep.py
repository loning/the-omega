# -*- coding: utf-8 -*-
"""
Phase-map family sweep for phase-lifted holonomy fits (toy).

We extend the phase-lifted transport by allowing a small family of low-complexity
index maps on microstate indices k in {0..63}:
  - id, gray, bitrev, not

For each map_name and each denom=2^p (bounded range), we:
  - build effective 3x3 unitary holonomy matrices on the 3/4-cycle plaquettes,
  - search over a global S3xS3 relabeling to fit target sines (PMNS or CKM),
  - record the best denom and its objective values.

We also report the log mismatch of the 3/4-cycle mean |J| to J_geo=1/(11*pi^7)
at the selected best denom (diagnostic only).

Outputs (LaTeX fragments):
  - sections/generated/holonomy_map_family_pmns_rows.tex
  - sections/generated/holonomy_map_family_ckm_rows.tex

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


MAPS = ["id", "gray", "bitrev", "not"]


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        return float("inf")
    return abs(math.log(pred / ref))


def safe_log_ratio(x: float, y: float) -> float | None:
    if x <= 0.0 or y <= 0.0:
        return None
    return math.log(x / y)


def permute(Q: U3, r: Perm3, c: Perm3) -> U3:
    return [[Q[r[i]][c[j]] for j in range(3)] for i in range(3)]


def collect_Qs_34(denom: int, map_name: str) -> List[U3]:
    Qs: List[U3] = []
    for p, H in ph.plaquette_unitary_holonomies(denom=denom, map_name=map_name):
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


def mean_absJ_34(denom: int, map_name: str) -> float:
    Js: List[float] = []
    for p, H in ph.plaquette_unitary_holonomies(denom=denom, map_name=map_name):
        ct = holo.cycle_type(p)
        if ct not in ("3", "4"):
            continue
        M = ph.project_3x3(H, B=ph.basis_B())
        Q = ph.gram_schmidt_unitary(M)
        if Q is None:
            continue
        Js.append(abs(ph.jarlskog_invariant(Q)))
    return mean(Js)


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


def best_perm(Qs: List[U3], ref: Tuple[float, float, float]) -> Tuple[float, float, Perm3, Perm3, float, float, float]:
    perms = list(itertools.permutations((0, 1, 2), 3))
    best = None  # (Einf,E1,r,c)
    best_pred = (float("nan"), float("nan"), float("nan"))
    for r in perms:
        for c in perms:
            s12, s23, s13 = predict_sines(Qs, r=r, c=c)
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


def run_target(ref: Tuple[float, float, float]) -> List[str]:
    p_min, p_max = 6, 18
    denoms = [1 << p for p in range(p_min, p_max + 1)]
    J_geo = 1.0 / (11.0 * (math.pi**7))

    rows: List[str] = []
    for map_name in MAPS:
        best_all = None  # (Einf,E1,denom,r,c,s12,s23,s13)
        for denom in denoms:
            Qs = collect_Qs_34(denom, map_name=map_name)
            Einf, E1, r, c, s12, s23, s13 = best_perm(Qs, ref=ref)
            cand = (Einf, E1, denom, r, c, s12, s23, s13)
            if best_all is None or cand < best_all:
                best_all = cand
        if best_all is None:
            raise AssertionError("No denom candidates enumerated.")
        Einf, E1, denom, r, c, s12, s23, s13 = best_all
        p = int(round(math.log2(denom)))
        Jm = mean_absJ_34(denom, map_name=map_name)
        lr = safe_log_ratio(Jm, J_geo)
        lr_tex = f"{lr:+.3f}" if lr is not None else "$-$"
        rows.append(
            f"\\texttt{{{map_name}}} & {denom} & {p} & \\texttt{{{r}}}/\\texttt{{{c}}} & {s12:.4f} & {s23:.4f} & {s13:.4f} & {Einf:.3f} & {E1:.3f} & {lr_tex} \\\\"
        )

    rows.append("\\bottomrule")
    return rows


def main() -> None:
    pmns = (math.sqrt(0.307), math.sqrt(0.545), math.sqrt(0.0218))
    ckm = (0.2243, 0.0422, 0.00394)

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    write_lines(out_dir / "holonomy_map_family_pmns_rows.tex", run_target(pmns))
    print("Wrote sections/generated/holonomy_map_family_pmns_rows.tex")
    write_lines(out_dir / "holonomy_map_family_ckm_rows.tex", run_target(ckm))
    print("Wrote sections/generated/holonomy_map_family_ckm_rows.tex")


if __name__ == "__main__":
    main()


