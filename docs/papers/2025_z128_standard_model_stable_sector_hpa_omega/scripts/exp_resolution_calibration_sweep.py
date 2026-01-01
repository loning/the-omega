# -*- coding: utf-8 -*-
"""
Calibration sweep for the resolution-uplift step size r_step in P3 (falsifiability).

Section P3 proposes a minimal mapping between window-length uplifts m->m+1 and
an additive depth increment r_step in the golden resolution coordinate:
  r(mu) = log(mu/m_e) / log(phi).

This script compares a small bounded-complexity candidate family
  r_step = k*pi,  k = 1..K
against a single reference anchor: the Z scale, using m=10 as the template
threshold (four steps above the base m=6).

We report:
  - the implied mu_th(10) = m_e * phi^{(10-6)*r_step},
  - the log mismatch log(mu_th(10)/m_Z),
  - the absolute log mismatch.

This is an audit-oriented comparison: it does not claim any physical necessity
for this family; it makes the calibration choice explicit and checkable.

Outputs (LaTeX fragment):
  - sections/generated/resolution_calibration_sweep_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

from common_constants import M_E_GEV, M_Z_GEV, PHI


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        raise ValueError("abs_log_ratio requires positive arguments.")
    return abs(math.log(pred / ref))


def fmt_mu(mu: float) -> str:
    if mu == 0.0:
        return "0"
    if mu < 1.0e-3 or mu >= 1.0e4:
        exp = int(math.floor(math.log10(abs(mu))))
        mant = mu / (10.0**exp)
        return f"{mant:.6g}\\times 10^{{{exp}}}"
    return f"{mu:.6g}"


def r_step_tex(k: int) -> str:
    if k == 1:
        return r"$\pi$"
    return rf"${k}\pi$"


def main() -> None:
    K = 10
    m_anchor = 10
    steps = m_anchor - 6
    if steps <= 0:
        raise AssertionError("Expected m_anchor > 6.")

    rows: List[Tuple[float, int, float, float, float]] = []
    # (abs_mismatch, k, r_step, mu_th, log_mismatch)
    for k in range(1, K + 1):
        r_step = float(k) * math.pi
        r_th = float(steps) * r_step
        mu_th = M_E_GEV * (PHI ** r_th)
        log_mis = math.log(mu_th / M_Z_GEV)
        abs_mis = abs(log_mis)
        rows.append((abs_mis, k, r_step, mu_th, log_mis))

    rows.sort(key=lambda x: (x[0], x[1]))
    best_k = rows[0][1]

    out_lines: List[str] = []
    for abs_mis, k, r_step, mu_th, log_mis in sorted(rows, key=lambda x: x[1]):
        cand = r_step_tex(k)
        r_step_num = f"{r_step:.6g}"
        mu_tex = f"${fmt_mu(mu_th)}$"
        log_tex = f"{log_mis:+.4f}"
        abs_tex = f"{abs_mis:.4f}"
        if k == best_k:
            cand = rf"\textbf{{{cand}}}"
            r_step_num = rf"\textbf{{{r_step_num}}}"
            mu_tex = rf"\textbf{{{mu_tex}}}"
            log_tex = rf"\textbf{{{log_tex}}}"
            abs_tex = rf"\textbf{{{abs_tex}}}"
        out_lines.append(f"{cand} & {r_step_num} & {mu_tex} & {log_tex} & {abs_tex} \\\\")
    out_lines.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "resolution_calibration_sweep_rows.tex").write_text("\n".join(out_lines), encoding="utf-8")
    print("Wrote sections/generated/resolution_calibration_sweep_rows.tex")


if __name__ == "__main__":
    main()


