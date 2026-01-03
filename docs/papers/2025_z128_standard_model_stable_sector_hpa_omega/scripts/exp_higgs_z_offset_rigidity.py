# -*- coding: utf-8 -*-
"""
Bounded-denominator rigidity sweep for the Higgs--Z depth offset in the phi-resolution coordinate.

Motivation (paper context)
-------------------------
The paper uses the Fibonacci resolution coordinate
  r(mu) = log(mu/m_e) / log(phi),
so ratios of scales can be expressed as phi-powers:
  mu_2 / mu_1 = phi^{Delta r}.

For electroweak scales, a minimal scalar-sector closure can be phrased as a
bounded-complexity approximation for the depth offset between the Higgs and Z
reference masses:
  Delta r_HZ := log_phi(m_H / m_Z).

This script performs a bounded-denominator sweep over reduced rationals
  Delta r = p/q,  1 <= q <= Q,
and, for each Q, selects the unique minimizer of the absolute log mismatch
  e(p/q) = |log( (m_Z * phi^{p/q}) / m_H )|,
with deterministic tie-break rules:
  minimize e, then minimize q, then minimize p.

Outputs (LaTeX fragment)
-----------------------
  - sections/generated/higgs_z_offset_sweep_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from math import gcd
from typing import List, Tuple

from common_constants import M_H_GEV, M_Z_GEV, PHI
from common_paths import generated_dir
from common_tex import write_lines


def _abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        raise ValueError("abs log ratio requires positive arguments")
    return abs(math.log(pred / ref))


def _fmt_float(x: float, nd: int = 6) -> str:
    return f"{x:.{nd}f}"


def _best_rational(Q: int) -> Tuple[int, int, float, float, float]:
    """
    Return (p, q, delta, pred, log_mis) for the best reduced rational p/q with q<=Q.
    """
    best: Tuple[float, int, int, float, float] | None = None
    # (abs_mis, q, p, pred, log_mis)
    for q in range(1, Q + 1):
        for p in range(0, q + 1):
            if gcd(p, q) != 1:
                continue
            delta = p / q
            pred = M_Z_GEV * (PHI ** delta)
            log_mis = math.log(pred / M_H_GEV)
            abs_mis = abs(log_mis)
            cand = (abs_mis, q, p, pred, log_mis)
            if best is None or cand < best:
                best = cand
    assert best is not None
    abs_mis, q, p, pred, log_mis = best
    return p, q, p / q, pred, log_mis


def main() -> None:
    Q_max = 20
    results: List[Tuple[int, int, int, float, float, float]] = []
    # (Q, p, q, delta, pred, log_mis)
    for Q in range(1, Q_max + 1):
        p, q, delta, pred, log_mis = _best_rational(Q)
        results.append((Q, p, q, delta, pred, log_mis))

    # Stabilization index: first Q where minimizer equals the Q_max minimizer and stays constant.
    p_star, q_star = results[-1][1], results[-1][2]
    Q_star = Q_max
    for i in range(len(results)):
        ok = True
        for j in range(i, len(results)):
            if results[j][1] != p_star or results[j][2] != q_star:
                ok = False
                break
        if ok:
            Q_star = results[i][0]
            break

    out_lines: List[str] = []
    for Q, p, q, delta, pred, log_mis in results:
        abs_mis = abs(log_mis)
        Q_tex = str(Q)
        frac_tex = rf"$\Delta r={p}/{q}$"
        delta_tex = _fmt_float(delta, nd=6)
        pred_tex = f"{pred:.6g}"
        log_tex = f"{log_mis:+.6f}"
        abs_tex = f"{abs_mis:.6f}"
        if Q == Q_star:
            Q_tex = rf"\textbf{{{Q_tex}}}"
            frac_tex = rf"\textbf{{{frac_tex}}}"
            delta_tex = rf"\textbf{{{delta_tex}}}"
            pred_tex = rf"\textbf{{{pred_tex}}}"
            log_tex = rf"\textbf{{{log_tex}}}"
            abs_tex = rf"\textbf{{{abs_tex}}}"
        out_lines.append(f"{Q_tex} & {frac_tex} & {delta_tex} & {pred_tex} & {log_tex} & {abs_tex} \\\\")
    out_lines.append("\\bottomrule")

    write_lines(generated_dir() / "higgs_z_offset_sweep_rows.tex", out_lines)
    print("Wrote sections/generated/higgs_z_offset_sweep_rows.tex")


if __name__ == "__main__":
    main()


