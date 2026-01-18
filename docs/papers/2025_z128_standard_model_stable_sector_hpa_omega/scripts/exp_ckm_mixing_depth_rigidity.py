# -*- coding: utf-8 -*-
"""
CKM mixing magnitudes as bounded-complexity depth candidates.

We treat the three small CKM magnitudes (|V_us|, |V_cb|, |V_ub|) as
dimensionless protocol amplitudes and search for a low-complexity
representation in the golden-resolution coordinate.

Candidate family (bounded by B):
  - |V_us|  := 1/sqrt(d), where 1 <= d <= min(B, V_max) and V_max = max_{w in X6} V(w).
  - |V_cb|  := phi^{-k23/2}, where 1 <= k23 <= 2B.
  - |V_ub|  := phi^{-k13/2}, where 1 <= k13 <= 2B.

Objective: minimize the maximum absolute log mismatch over the three targets,
then the sum mismatch, then coefficient complexity, then lexicographic tie-break.

Outputs (LaTeX fragments):
  - sections/generated/ckm_mixing_rigidity_rows.tex
  - sections/generated/ckm_mixing_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import exp_fold6_stats as fold


PHI = (1.0 + math.sqrt(5.0)) / 2.0
LOG_PHI = math.log(PHI)


@dataclass(frozen=True)
class BestTriple:
    B: int
    d: int
    k23: int
    k13: int
    max_abs_log_err: float
    sum_abs_log_err: float


def v_max_x6() -> int:
    X6 = fold.all_x6()
    vmax = 0
    for w in X6:
        vmax = max(vmax, fold.zeckendorf_value_of_word(w))
    return vmax


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        raise ValueError("abs_log_ratio requires positive arguments.")
    return abs(math.log(pred / ref))


def triple_objective(
    d: int,
    k23: int,
    k13: int,
    vus_ref: float,
    vcb_ref: float,
    vub_ref: float,
) -> Tuple[float, float]:
    vus = 1.0 / math.sqrt(float(d))
    vcb = PHI ** (-0.5 * float(k23))
    vub = PHI ** (-0.5 * float(k13))
    e12 = abs_log_ratio(vus, vus_ref)
    e23 = abs_log_ratio(vcb, vcb_ref)
    e13 = abs_log_ratio(vub, vub_ref)
    return max(e12, e23, e13), (e12 + e23 + e13)


def best_triple_at_B(
    B: int,
    vus_ref: float,
    vcb_ref: float,
    vub_ref: float,
    vmax: int,
) -> BestTriple:
    best: Tuple[float, float, int, int, int] | None = None  # (maxe, sume, comp, d, k23, k13)
    d_max = min(B, vmax)
    k_max = 2 * B
    for d in range(1, d_max + 1):
        for k23 in range(1, k_max + 1):
            for k13 in range(1, k_max + 1):
                maxe, sume = triple_objective(d, k23, k13, vus_ref, vcb_ref, vub_ref)
                comp = d + k23 + k13
                cand = (maxe, sume, comp, d, k23, k13)
                if best is None or cand < best:
                    best = cand
    if best is None:
        raise AssertionError("No candidates enumerated.")
    maxe, sume, _comp, d, k23, k13 = best
    return BestTriple(B=B, d=d, k23=k23, k13=k13, max_abs_log_err=maxe, sum_abs_log_err=sume)


def write_rows(
    best_list: List[BestTriple],
    vus_ref: float,
    vcb_ref: float,
    vub_ref: float,
    vmax: int,
) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Rigidity table (20 iterations).
    rig_rows: List[str] = []
    for b in best_list:
        rig_rows.append(
            f"{b.B} & $(d,k_{{23}},k_{{13}})=({b.d},{b.k23},{b.k13})$ & {b.max_abs_log_err:.6f} & {b.sum_abs_log_err:.6f} \\\\"
        )
    rig_rows.append("\\bottomrule")
    (out_dir / "ckm_mixing_rigidity_rows.tex").write_text("\n".join(rig_rows), encoding="utf-8")

    # Final predicted values at B=20.
    b20 = best_list[-1]
    vus = 1.0 / math.sqrt(float(b20.d))
    vcb = PHI ** (-0.5 * float(b20.k23))
    vub = PHI ** (-0.5 * float(b20.k13))
    # Signed log ratios (diagnostic).
    lr_vus = math.log(vus / vus_ref)
    lr_vcb = math.log(vcb / vcb_ref)
    lr_vub = math.log(vub / vub_ref)

    # Depth coordinate r(x) = -log(x)/log(phi).
    r_vus = -math.log(vus) / LOG_PHI
    r_vcb = -math.log(vcb) / LOG_PHI
    r_vub = -math.log(vub) / LOG_PHI

    rows: List[str] = []
    rows.append(
        f"$|V_{{us}}|$ & {vus_ref:.6g} & $1/\\sqrt{{{b20.d}}}$ & {vus:.9g} & {r_vus:.3f} & {lr_vus:.6f} \\\\"
    )
    rows.append(
        f"$|V_{{cb}}|$ & {vcb_ref:.6g} & $\\varphi^{{-{b20.k23}/2}}$ & {vcb:.9g} & {r_vcb:.3f} & {lr_vcb:.6f} \\\\"
    )
    rows.append(
        f"$|V_{{ub}}|$ & {vub_ref:.6g} & $\\varphi^{{-{b20.k13}/2}}$ & {vub:.9g} & {r_vub:.3f} & {lr_vub:.6f} \\\\"
    )
    rows.append("\\bottomrule")
    (out_dir / "ckm_mixing_rows.tex").write_text("\n".join(rows), encoding="utf-8")


def main() -> None:
    # PDG reference magnitudes (central values; conventions per PDG RPP).
    # These are the standard small CKM magnitudes used for mixing-angle scale.
    vus_ref = 0.2243
    vcb_ref = 0.0422
    vub_ref = 0.00394

    vmax = v_max_x6()
    if vmax != 20:
        raise AssertionError(f"Expected V_max(X6)=20 at m=6, got {vmax}.")

    best_list: List[BestTriple] = []
    for B in range(1, 21):
        best_list.append(best_triple_at_B(B, vus_ref, vcb_ref, vub_ref, vmax))

    write_rows(best_list, vus_ref, vcb_ref, vub_ref, vmax)
    print("Wrote sections/generated/ckm_mixing_rows.tex and ckm_mixing_rigidity_rows.tex")


if __name__ == "__main__":
    main()


