# -*- coding: utf-8 -*-
"""
Denominator sweep for phase-lifted angle extraction (toy).

For denom = 2^p in a bounded range, we compute phase-lifted plaquette holonomies,
project+renormalize to an effective 3x3 unitary, extract PDG-style sines
(s12,s23,s13) and a principal delta from J, and summarize the *3/4-cycle* subset.

We report:
  - mean s12,s23,s13 on 3/4 cycles (weighted by their counts),
  - mean |J| on 3/4 cycles,
  - log mismatch of mean |J| vs J_geo = 1/(11*pi^7).

Outputs (LaTeX fragment):
  - sections/generated/holonomy_phase_lift_angles_denom_sweep_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import exp_holonomy_loops as holo
import exp_holonomy_phase_lift_angles as ang
import exp_holonomy_phase_lift_cp_invariant as ph
from common_tex import write_lines


def mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else float("nan")


def safe_log_ratio(x: float, y: float) -> float | None:
    if x <= 0.0 or y <= 0.0:
        return None
    return math.log(x / y)


def summarize_34(denom: int) -> Tuple[float, float, float, float]:
    """
    Return (mean_s12, mean_s23, mean_s13, mean_absJ) on the 3/4-cycle subset.
    """
    s12s: List[float] = []
    s23s: List[float] = []
    s13s: List[float] = []
    Js: List[float] = []
    for p, H in ph.plaquette_unitary_holonomies(denom=denom):
        ct = holo.cycle_type(p)
        if ct not in ("3", "4"):
            continue
        M = ph.project_3x3(H, B=ph.basis_B())
        Q = ph.gram_schmidt_unitary(M)
        if Q is None:
            continue
        s12, s23, s13, _delta_deg, J = ang.extract_angles(Q)
        if math.isnan(s12) or math.isnan(s23) or math.isnan(s13) or math.isnan(J):
            continue
        s12s.append(s12)
        s23s.append(s23)
        s13s.append(s13)
        Js.append(J)
    return mean(s12s), mean(s23s), mean(s13s), mean([abs(x) for x in Js])


def main() -> None:
    p_min, p_max = 6, 18
    denoms = [1 << p for p in range(p_min, p_max + 1)]
    J_geo = 1.0 / (11.0 * (math.pi**7))

    rows = []
    best = None  # (abs_log_mis, denom, p)
    cache = {}
    for denom in denoms:
        p = int(round(math.log2(denom)))
        s12, s23, s13, meanJ = summarize_34(denom)
        lr = safe_log_ratio(meanJ, J_geo)
        abs_mis = float("inf") if lr is None else abs(lr)
        cache[denom] = (p, s12, s23, s13, meanJ, lr, abs_mis)
        cand = (abs_mis, denom, p)
        if best is None or cand < best:
            best = cand

    best_denom = best[1] if best is not None else denoms[0]

    for denom in denoms:
        p, s12, s23, s13, meanJ, lr, abs_mis = cache[denom]
        denom_tex = str(denom)
        lr_tex = f"{lr:+.3f}" if lr is not None else "$-$"
        abs_tex = f"{abs_mis:.3f}" if math.isfinite(abs_mis) else "$\\infty$"
        if denom == best_denom:
            denom_tex = rf"\textbf{{{denom_tex}}}"
            lr_tex = rf"\textbf{{{lr_tex}}}"
            abs_tex = rf"\textbf{{{abs_tex}}}"
        rows.append(f"{denom_tex} & {p} & {s12:.4f} & {s23:.4f} & {s13:.4f} & {meanJ:.6g} & {lr_tex} & {abs_tex} \\\\")

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_phase_lift_angles_denom_sweep_rows.tex", rows)
    print("Wrote sections/generated/holonomy_phase_lift_angles_denom_sweep_rows.tex")


if __name__ == "__main__":
    main()


