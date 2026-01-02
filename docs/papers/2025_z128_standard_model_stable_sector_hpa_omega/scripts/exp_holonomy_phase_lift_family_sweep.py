# -*- coding: utf-8 -*-
"""
Phase-denominator sweep for the phase-lifted holonomy CP invariant.

We keep the same finite edge permutation connection on the n=3 grid, but vary the
phase register denominator used in the phase lift:
  phi(k) = 2*pi * k / denom.

For each denom in a bounded candidate family (powers of two), we compute the
phase-lifted plaquette holonomies, project+renormalize to an effective 3x3
unitary, and summarize the induced Jarlskog-type invariant J.

We compare the mean |J| over the nontrivial cycle-type plaquettes (3- and 4-cycles)
to the closed constant-geometry target J_geo = 1/(11*pi^7), using the log mismatch.

Outputs (LaTeX fragment):
  - sections/generated/holonomy_phase_lift_family_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import exp_holonomy_loops as holo
import exp_holonomy_phase_lift_cp_invariant as ph
from common_tex import write_lines


def safe_log_ratio(x: float, y: float) -> float | None:
    if x <= 0.0 or y <= 0.0:
        return None
    return math.log(x / y)


def summarize_J(denom: int) -> Tuple[Dict[str, float], Dict[str, int], int]:
    """
    Return (mean_abs_by_ct, count_by_ct, rank_failures) for the given denom.
    """
    by_ct: Dict[str, List[float]] = {ct: [] for ct in ["1", "2", "2x2", "3", "4", "other"]}
    fails = 0
    for p, H in ph.plaquette_unitary_holonomies(denom=denom):
        ct = holo.cycle_type(p)
        M = ph.project_3x3(H, B=ph.basis_B())
        Q = ph.gram_schmidt_unitary(M)
        if Q is None:
            fails += 1
            continue
        J = ph.jarlskog_invariant(Q)
        by_ct[ct].append(J)

    mean_abs: Dict[str, float] = {}
    cnts: Dict[str, int] = {}
    for ct, xs in by_ct.items():
        cnts[ct] = len(xs)
        if not xs:
            mean_abs[ct] = 0.0
        else:
            mean_abs[ct] = sum(abs(x) for x in xs) / float(len(xs))
    return mean_abs, cnts, fails


def main() -> None:
    # Candidate family: denom = 2^p for p in [6..18].
    p_min, p_max = 6, 18
    denoms = [1 << p for p in range(p_min, p_max + 1)]

    J_geo = 1.0 / (11.0 * (math.pi**7))

    rows: List[Tuple[float, int, int, float, float, float, int]] = []
    # (abs_log_mis, denom, p, mean3, mean4, mean34, fails)
    for denom in denoms:
        mean_abs, _cnts, fails = summarize_J(denom)
        mean3 = mean_abs.get("3", 0.0)
        mean4 = mean_abs.get("4", 0.0)
        # Combine 3/4 cycle types (nontrivial holonomy) with equal weights by sample count.
        # Use actual counts from the fixed n=3 distribution: 3 cycles:3, 4 cycles:2.
        mean34 = (3.0 * mean3 + 2.0 * mean4) / 5.0
        lr = safe_log_ratio(mean34, J_geo)
        abs_mis = float("inf") if lr is None else abs(lr)
        p = int(round(math.log2(denom)))
        rows.append((abs_mis, denom, p, mean3, mean4, mean34, fails))

    rows.sort(key=lambda x: (x[0], x[1]))
    best_denom = rows[0][1]

    out_lines: List[str] = []
    for abs_mis, denom, p, mean3, mean4, mean34, fails in sorted(rows, key=lambda x: x[2]):
        denom_tex = str(denom)
        mean3_tex = f"{mean3:.6g}" if mean3 > 0.0 else "0"
        mean4_tex = f"{mean4:.6g}" if mean4 > 0.0 else "0"
        mean34_tex = f"{mean34:.6g}" if mean34 > 0.0 else "0"
        lr = safe_log_ratio(mean34, J_geo)
        log_tex = f"{lr:+.3f}" if lr is not None else "$-$"
        abs_tex = f"{abs_mis:.3f}" if math.isfinite(abs_mis) else "$\\infty$"
        fail_tex = str(fails)

        if denom == best_denom:
            denom_tex = rf"\textbf{{{denom_tex}}}"
            mean34_tex = rf"\textbf{{{mean34_tex}}}"
            log_tex = rf"\textbf{{{log_tex}}}"
            abs_tex = rf"\textbf{{{abs_tex}}}"

        out_lines.append(
            f"{denom_tex} & {p} & {mean3_tex} & {mean4_tex} & {mean34_tex} & {log_tex} & {abs_tex} & {fail_tex} \\\\"
        )

    out_lines.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_phase_lift_family_rows.tex", out_lines)
    print("Wrote sections/generated/holonomy_phase_lift_family_rows.tex")


if __name__ == "__main__":
    main()


