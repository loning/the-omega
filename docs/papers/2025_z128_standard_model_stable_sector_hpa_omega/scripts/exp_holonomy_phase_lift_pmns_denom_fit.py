# -*- coding: utf-8 -*-
"""
Bounded-complexity selection of denom=2^p to fit PMNS mixing sines (toy).

We use the 3/4-cycle aggregated mean extracted angles from the phase-lifted
effective holonomy matrices (n=3) and compare them to representative PMNS sines:
  s12_ref = sqrt(0.307), s23_ref = sqrt(0.545), s13_ref = sqrt(0.0218).

Candidate family:
  denom = 2^p,  p_min <= p <= p_max

Objective (audit form):
  e_i = |log(pred_i / ref_i)|,
  E_inf = max_i e_i,  E_1 = sum_i e_i,
tie-break by (E_inf, E_1, p).

Outputs (LaTeX fragment):
  - sections/generated/holonomy_phase_lift_pmns_denom_fit_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import exp_holonomy_phase_lift_angles_denom_sweep as sweep
from common_tex import write_lines


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        return float("inf")
    return abs(math.log(pred / ref))


def main() -> None:
    # PMNS reference sines (representative central values; PDG conventions).
    s12_ref = math.sqrt(0.307)
    s23_ref = math.sqrt(0.545)
    s13_ref = math.sqrt(0.0218)

    p_min, p_max = 6, 18
    denoms = [1 << p for p in range(p_min, p_max + 1)]

    scored: List[Tuple[float, float, int, float, float, float]] = []
    # (Einf,E1,p, s12,s23,s13)
    for denom in denoms:
        p = int(round(math.log2(denom)))
        s12, s23, s13, _meanJ = sweep.summarize_34(denom)
        e12 = abs_log_ratio(s12, s12_ref)
        e23 = abs_log_ratio(s23, s23_ref)
        e13 = abs_log_ratio(s13, s13_ref)
        Einf = max(e12, e23, e13)
        E1 = e12 + e23 + e13
        scored.append((Einf, E1, p, s12, s23, s13))

    scored.sort()
    best = scored[0]
    second = scored[1] if len(scored) > 1 else scored[0]
    best_p = best[2]
    best_Einf, best_E1, _p, best_s12, best_s23, best_s13 = best
    sec_Einf, sec_E1, sec_p, *_ = second

    out_lines: List[str] = []
    for Einf, E1, p, s12, s23, s13 in sorted(scored, key=lambda x: x[2]):
        denom = 1 << p
        denom_tex = str(denom)
        Einf_tex = f"{Einf:.3f}"
        E1_tex = f"{E1:.3f}"
        if p == best_p:
            denom_tex = rf"\textbf{{{denom_tex}}}"
            Einf_tex = rf"\textbf{{{Einf_tex}}}"
            E1_tex = rf"\textbf{{{E1_tex}}}"
        out_lines.append(f"{denom_tex} & {p} & {s12:.4f} & {s23:.4f} & {s13:.4f} & {Einf_tex} & {E1_tex} \\\\")

    # Append a compact best/second summary row (pseudo row tag).
    gap = sec_Einf - best_Einf
    out_lines.append(
        rf"\texttt{{best/second}} & $p={best_p}/{sec_p}$ & $-$ & $-$ & $-$ & {best_Einf:.3f}/{sec_Einf:.3f} & $\Delta={gap:.3f}$ \\"
    )
    out_lines.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_phase_lift_pmns_denom_fit_rows.tex", out_lines)
    print("Wrote sections/generated/holonomy_phase_lift_pmns_denom_fit_rows.tex")


if __name__ == "__main__":
    main()


