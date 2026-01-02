# -*- coding: utf-8 -*-
"""
Extract PDG-style angles from phase-lifted effective U(3) holonomy (finite diagnostic).

Given the phase-lifted plaquette holonomy H (4x4 unitary) on the n=3 grid:
  - project to sum-zero subspace -> M (3x3),
  - renormalize columns by Gram-Schmidt -> Q (3x3 unitary),
we define the PDG-style sines by the standard identities:
  s13 := |Q_{0,2}|,
  c13 := sqrt(1 - s13^2),
  s12 := |Q_{0,1}| / c13,
  s23 := |Q_{1,2}| / c13.

Using the rephasing-invariant Jarlskog combination
  J := Im(Q00 Q11 Q01^* Q10^*),
we extract a principal Dirac phase delta via:
  sin(delta) = J / (s12 s23 s13 c12 c23 c13^2),
with delta in [0,pi] when possible.

This is a diagnostic bridge script; it does not claim a unique identification of
rows/columns with SM generations. It reports cycle-type aggregated summaries.

Outputs (LaTeX fragment):
  - sections/generated/holonomy_phase_lift_angles_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import exp_holonomy_loops as holo
import exp_holonomy_phase_lift_cp_invariant as ph
from common_tex import write_lines


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def extract_angles(Q: List[List[complex]]) -> Tuple[float, float, float, float, float]:
    """
    Return (s12,s23,s13,delta_deg,J).
    delta is returned in degrees in [0,180] when defined, else NaN.
    """
    s13 = abs(Q[0][2])
    s13 = clamp(s13, 0.0, 1.0)
    c13 = math.sqrt(max(0.0, 1.0 - s13 * s13))
    if c13 == 0.0:
        return float("nan"), float("nan"), s13, float("nan"), float("nan")
    s12 = abs(Q[0][1]) / c13
    s23 = abs(Q[1][2]) / c13
    s12 = clamp(s12, 0.0, 1.0)
    s23 = clamp(s23, 0.0, 1.0)
    c12 = math.sqrt(max(0.0, 1.0 - s12 * s12))
    c23 = math.sqrt(max(0.0, 1.0 - s23 * s23))

    J = ph.jarlskog_invariant(Q)
    denom = s12 * s23 * s13 * c12 * c23 * (c13 * c13)
    if denom <= 0.0:
        return s12, s23, s13, float("nan"), J
    x = clamp(J / denom, -1.0, 1.0)
    delta = math.asin(x)
    # Principal phase in [0,pi].
    if delta < 0.0:
        delta = -delta
    delta_deg = delta * 180.0 / math.pi
    return s12, s23, s13, delta_deg, J


def mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else float("nan")


def main() -> None:
    denom = 64  # keep consistent with the main phase-lift table by default
    by_ct: Dict[str, List[Tuple[float, float, float, float, float]]] = defaultdict(list)
    failures = 0

    for p, H in ph.plaquette_unitary_holonomies(denom=denom):
        ct = holo.cycle_type(p)
        M = ph.project_3x3(H, B=ph.basis_B())
        Q = ph.gram_schmidt_unitary(M)
        if Q is None:
            failures += 1
            continue
        by_ct[ct].append(extract_angles(Q))

    rows: List[str] = []
    for ct in ["1", "2", "2x2", "3", "4", "other"]:
        xs = by_ct.get(ct, [])
        if not xs:
            rows.append(f"\\texttt{{{ct}}} & 0 & $-$ & $-$ & $-$ & $-$ & $-$ \\\\")
            continue
        s12s = [t[0] for t in xs]
        s23s = [t[1] for t in xs]
        s13s = [t[2] for t in xs]
        deltas = [t[3] for t in xs if not math.isnan(t[3])]
        Js = [t[4] for t in xs if not math.isnan(t[4])]
        rows.append(
            f"\\texttt{{{ct}}} & {len(xs)} & {mean(s12s):.4f} & {mean(s23s):.4f} & {mean(s13s):.4f} & {mean(deltas):.2f} & {mean([abs(j) for j in Js]):.6g} \\\\"
        )

    if failures:
        rows.append(f"\\texttt{{rank-fail}} & {failures} & $-$ & $-$ & $-$ & $-$ & $-$ \\\\")
    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_phase_lift_angles_rows.tex", rows)
    print("Wrote sections/generated/holonomy_phase_lift_angles_rows.tex")


if __name__ == "__main__":
    main()


