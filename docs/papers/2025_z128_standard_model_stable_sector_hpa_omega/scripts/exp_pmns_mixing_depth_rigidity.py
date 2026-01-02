# -*- coding: utf-8 -*-
"""
PMNS mixing angles as bounded-complexity depth candidates.

We mirror the audit style used for CKM in this paper:
  - define a small discrete candidate family,
  - select a unique minimizer under a bounded-complexity box,
  - report stabilization (rigidity certificate) over B=1..20.

Candidate family (bounded by B):
  - s12 := sqrt(p12/q12), where 1 <= q12 <= B, 1 <= p12 <= q12-1, gcd(p12,q12)=1
  - s23 := sqrt(p23/q23), where 1 <= q23 <= B, 1 <= p23 <= q23-1, gcd(p23,q23)=1
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
    p12: int
    q12: int
    p23: int
    q23: int
    k13: int
    max_abs_log_err: float
    sum_abs_log_err: float


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        raise ValueError("abs_log_ratio requires positive arguments.")
    return abs(math.log(pred / ref))


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a)


def rational_sine_candidates(B: int) -> List[Tuple[int, int, float]]:
    """
    Enumerate reduced fractions p/q in (0,1] with 1<=q<=B, 1<=p<=q-1 for q>=2
    (and include the degenerate q=1, p=1 candidate to allow B=1),
    gcd(p,q)=1,
    returning tuples (p,q,sqrt(p/q)), sorted by (q,p).
    """
    if B < 1:
        return []
    out: List[Tuple[int, int, float]] = []
    for q in range(1, B + 1):
        if q == 1:
            out.append((1, 1, 1.0))
            continue
        for p in range(1, q):
            if _gcd(p, q) != 1:
                continue
            out.append((p, q, math.sqrt(float(p) / float(q))))
    out.sort(key=lambda t: (t[1], t[0]))
    return out


def triple_objective(s12: float, s23: float, k13: int, s12_ref: float, s23_ref: float, s13_ref: float) -> Tuple[float, float]:
    s13 = PHI ** (-0.5 * float(k13))
    e12 = abs_log_ratio(s12, s12_ref)
    e23 = abs_log_ratio(s23, s23_ref)
    e13 = abs_log_ratio(s13, s13_ref)
    return max(e12, e23, e13), (e12 + e23 + e13)


def best_triple_at_B(B: int, s12_ref: float, s23_ref: float, s13_ref: float) -> BestTriple:
    cand12 = rational_sine_candidates(B)
    cand23 = rational_sine_candidates(B)
    if not cand12 or not cand23:
        raise AssertionError("No rational candidates enumerated.")

    best: Tuple[float, float, int, int, int, int, int, int, int] | None = None
    # (maxe, sume, comp1, comp2, q12, p12, q23, p23, k13)
    k_max = 2 * B
    for p12, q12, s12 in cand12:
        for p23, q23, s23 in cand23:
            for k13 in range(1, k_max + 1):
                maxe, sume = triple_objective(s12, s23, k13, s12_ref, s23_ref, s13_ref)
                comp1 = q12 + q23 + k13
                comp2 = p12 + p23
                cand = (maxe, sume, comp1, comp2, q12, p12, q23, p23, k13)
                if best is None or cand < best:
                    best = cand
    if best is None:
        raise AssertionError("No candidates enumerated.")
    maxe, sume, _c1, _c2, q12, p12, q23, p23, k13 = best
    return BestTriple(
        B=B,
        p12=p12,
        q12=q12,
        p23=p23,
        q23=q23,
        k13=k13,
        max_abs_log_err=maxe,
        sum_abs_log_err=sume,
    )


def write_rows(best_list: List[BestTriple], s12_ref: float, s23_ref: float, s13_ref: float) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    rig_rows: List[str] = []
    for b in best_list:
        rig_rows.append(
            f"{b.B} & $(p_{{12}}/q_{{12}},p_{{23}}/q_{{23}},k_{{13}})=({b.p12}/{b.q12},{b.p23}/{b.q23},{b.k13})$ & {b.max_abs_log_err:.6f} & {b.sum_abs_log_err:.6f} \\\\"
        )
    rig_rows.append("\\bottomrule")
    (out_dir / "pmns_mixing_rigidity_rows.tex").write_text("\n".join(rig_rows), encoding="utf-8")

    b20 = best_list[-1]
    s12 = math.sqrt(float(b20.p12) / float(b20.q12))
    s23 = math.sqrt(float(b20.p23) / float(b20.q23))
    s13 = PHI ** (-0.5 * float(b20.k13))

    lr_s12 = math.log(s12 / s12_ref)
    lr_s23 = math.log(s23 / s23_ref)
    lr_s13 = math.log(s13 / s13_ref)

    r_s12 = -math.log(s12) / LOG_PHI
    r_s23 = -math.log(s23) / LOG_PHI
    r_s13 = -math.log(s13) / LOG_PHI

    rows: List[str] = []
    rows.append(
        f"$s_{{12}}$ & {s12_ref:.6g} & $\\sqrt{{{b20.p12}/{b20.q12}}}$ & {s12:.9g} & {r_s12:.3f} & {lr_s12:.6f} \\\\"
    )
    rows.append(
        f"$s_{{23}}$ & {s23_ref:.6g} & $\\sqrt{{{b20.p23}/{b20.q23}}}$ & {s23:.9g} & {r_s23:.3f} & {lr_s23:.6f} \\\\"
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
    for B in range(2, 21):
        best_list.append(best_triple_at_B(B, s12_ref, s23_ref, s13_ref))

    write_rows(best_list, s12_ref, s23_ref, s13_ref)
    print("Wrote sections/generated/pmns_mixing_rows.tex and pmns_mixing_rigidity_rows.tex")


if __name__ == "__main__":
    main()


