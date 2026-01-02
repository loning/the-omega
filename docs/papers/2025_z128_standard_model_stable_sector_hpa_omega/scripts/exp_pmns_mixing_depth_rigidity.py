# -*- coding: utf-8 -*-
"""
PMNS mixing angles as bounded-complexity depth candidates.

We mirror the audit style used for CKM in this paper:
  - define a small discrete candidate family,
  - select a unique minimizer under a bounded-complexity box,
  - report stabilization (rigidity certificate) over B=1..20.

Candidate family (bounded by B):
  - s12 := 1/sqrt(m12), where 1 <= m12 <= B
  - s23 := 1/sqrt(m23), where 1 <= m23 <= B
  - s13 := phi^{-k13/2}, where 1 <= k13 <= 2B

Objective: minimize the maximum absolute log mismatch over (s12,s23,s13),
then the sum mismatch, then coefficient complexity, then lexicographic tie-break.

Outputs (LaTeX fragments):
  - sections/generated/pmns_mixing_rigidity_rows.tex
  - sections/generated/pmns_mixing_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from common_constants import LOG_PHI, PHI, PMNS_SIN2_T12_REF, PMNS_SIN2_T13_REF, PMNS_SIN2_T23_REF


@dataclass(frozen=True)
class BestTriple:
    B: int
    m12: int
    m23: int
    k13: int
    max_abs_log_err: float
    sum_abs_log_err: float


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        raise ValueError("abs_log_ratio requires positive arguments.")
    return abs(math.log(pred / ref))


def triple_objective(m12: int, m23: int, k13: int, s12_ref: float, s23_ref: float, s13_ref: float) -> Tuple[float, float]:
    s12 = 1.0 / math.sqrt(float(m12))
    s23 = 1.0 / math.sqrt(float(m23))
    s13 = PHI ** (-0.5 * float(k13))
    e12 = abs_log_ratio(s12, s12_ref)
    e23 = abs_log_ratio(s23, s23_ref)
    e13 = abs_log_ratio(s13, s13_ref)
    return max(e12, e23, e13), (e12 + e23 + e13)


def best_triple_at_B(B: int, s12_ref: float, s23_ref: float, s13_ref: float) -> BestTriple:
    best: Tuple[float, float, int, int, int, int] | None = None  # (maxe, sume, comp, m12, m23, k13)
    k_max = 2 * B
    for m12 in range(1, B + 1):
        for m23 in range(1, B + 1):
            for k13 in range(1, k_max + 1):
                maxe, sume = triple_objective(m12, m23, k13, s12_ref, s23_ref, s13_ref)
                comp = m12 + m23 + k13
                cand = (maxe, sume, comp, m12, m23, k13)
                if best is None or cand < best:
                    best = cand
    if best is None:
        raise AssertionError("No candidates enumerated.")
    maxe, sume, _comp, m12, m23, k13 = best
    return BestTriple(B=B, m12=m12, m23=m23, k13=k13, max_abs_log_err=maxe, sum_abs_log_err=sume)


def write_rows(best_list: List[BestTriple], s12_ref: float, s23_ref: float, s13_ref: float) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    rig_rows: List[str] = []
    for b in best_list:
        rig_rows.append(
            f"{b.B} & $(m_{{12}},m_{{23}},k_{{13}})=({b.m12},{b.m23},{b.k13})$ & {b.max_abs_log_err:.6f} & {b.sum_abs_log_err:.6f} \\\\"
        )
    rig_rows.append("\\bottomrule")
    (out_dir / "pmns_mixing_rigidity_rows.tex").write_text("\n".join(rig_rows), encoding="utf-8")

    b20 = best_list[-1]
    s12 = 1.0 / math.sqrt(float(b20.m12))
    s23 = 1.0 / math.sqrt(float(b20.m23))
    s13 = PHI ** (-0.5 * float(b20.k13))

    lr_s12 = math.log(s12 / s12_ref)
    lr_s23 = math.log(s23 / s23_ref)
    lr_s13 = math.log(s13 / s13_ref)

    r_s12 = -math.log(s12) / LOG_PHI
    r_s23 = -math.log(s23) / LOG_PHI
    r_s13 = -math.log(s13) / LOG_PHI

    rows: List[str] = []
    rows.append(
        f"$s_{{12}}$ & {s12_ref:.6g} & $1/\\sqrt{{{b20.m12}}}$ & {s12:.9g} & {r_s12:.3f} & {lr_s12:.6f} \\\\"
    )
    rows.append(
        f"$s_{{23}}$ & {s23_ref:.6g} & $1/\\sqrt{{{b20.m23}}}$ & {s23:.9g} & {r_s23:.3f} & {lr_s23:.6f} \\\\"
    )
    rows.append(
        f"$s_{{13}}$ & {s13_ref:.6g} & $\\varphi^{{-{b20.k13}/2}}$ & {s13:.9g} & {r_s13:.3f} & {lr_s13:.6f} \\\\"
    )
    rows.append("\\bottomrule")
    (out_dir / "pmns_mixing_rows.tex").write_text("\n".join(rows), encoding="utf-8")


def main() -> None:
    # Reference inputs (representative global-fit central values; PDG conventions).
    # We store the *sines* of the mixing angles.
    sin2_t12 = PMNS_SIN2_T12_REF
    sin2_t23 = PMNS_SIN2_T23_REF
    sin2_t13 = PMNS_SIN2_T13_REF
    s12_ref = math.sqrt(sin2_t12)
    s23_ref = math.sqrt(sin2_t23)
    s13_ref = math.sqrt(sin2_t13)

    best_list: List[BestTriple] = []
    for B in range(1, 21):
        best_list.append(best_triple_at_B(B, s12_ref, s23_ref, s13_ref))

    write_rows(best_list, s12_ref, s23_ref, s13_ref)
    print("Wrote sections/generated/pmns_mixing_rows.tex and pmns_mixing_rigidity_rows.tex")


if __name__ == "__main__":
    main()


