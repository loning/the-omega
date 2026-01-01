# -*- coding: utf-8 -*-
"""
Multi-anchor calibration sweep for the resolution-uplift step size r_step.

This script extends exp_resolution_calibration_sweep.py by using *multiple*
reference anchors and a deterministic minimax objective, in the same audit style
as other bounded-complexity closures in this paper.

Model:
  r_th(m) = (m-6) * r_step
  mu_th(m) = m_e * phi^{r_th(m)}

Candidate family:
  r_step = k*pi,  1 <= k <= K

Anchors (physical-layer inputs; explicit literals, no network):
  - Z pole mass m_Z at m=10
  - a QCD-scale reference mu_QCD at m=8 (order-of-magnitude anchor)

Objective for each candidate:
  e_i = log(mu_th(m_i) / mu_ref_i)
  E_inf = max_i |e_i|
  E_1   = sum_i |e_i|
Select the unique minimizer by lexicographic ordering (E_inf, E_1, k).

Outputs (LaTeX fragment):
  - sections/generated/resolution_calibration_multianchor_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

from common_constants import M_E_GEV, M_Z_GEV, PHI


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


def mu_threshold(m: int, r_step: float) -> float:
    r_th = float(m - 6) * r_step
    return M_E_GEV * (PHI ** r_th)


def main() -> None:
    K = 10
    anchors: List[Tuple[int, float, str]] = [
        (10, M_Z_GEV, r"$m_Z$"),
        (8, 0.2, r"$\mu_{\mathrm{QCD}}$"),
    ]

    # Evaluate candidates.
    scored: List[Tuple[float, float, int]] = []  # (E_inf, E1, k)
    details = {}
    for k in range(1, K + 1):
        r_step = float(k) * math.pi
        es: List[float] = []
        mus: List[float] = []
        for m, mu_ref, _name in anchors:
            mu_th = mu_threshold(m, r_step=r_step)
            mus.append(mu_th)
            es.append(math.log(mu_th / mu_ref))
        E_inf = max(abs(e) for e in es) if es else 0.0
        E1 = sum(abs(e) for e in es)
        scored.append((E_inf, E1, k))
        details[k] = (mus, es, E_inf, E1)

    scored.sort()
    best_k = scored[0][2]

    out_lines: List[str] = []
    for k in range(1, K + 1):
        r_step = float(k) * math.pi
        mus, es, E_inf, E1 = details[k]
        # Expect exactly two anchors in the intended table layout.
        if len(mus) != 2 or len(es) != 2:
            raise AssertionError("This script expects exactly two anchors.")

        cand = r_step_tex(k)
        r_step_num = f"{r_step:.6g}"
        mu10_tex = f"${fmt_mu(mus[0])}$"
        mu8_tex = f"${fmt_mu(mus[1])}$"
        e10_tex = f"{es[0]:+.4f}"
        e8_tex = f"{es[1]:+.4f}"
        Einf_tex = f"{E_inf:.4f}"
        E1_tex = f"{E1:.4f}"
        if k == best_k:
            cand = rf"\textbf{{{cand}}}"
            r_step_num = rf"\textbf{{{r_step_num}}}"
            mu10_tex = rf"\textbf{{{mu10_tex}}}"
            mu8_tex = rf"\textbf{{{mu8_tex}}}"
            e10_tex = rf"\textbf{{{e10_tex}}}"
            e8_tex = rf"\textbf{{{e8_tex}}}"
            Einf_tex = rf"\textbf{{{Einf_tex}}}"
            E1_tex = rf"\textbf{{{E1_tex}}}"

        out_lines.append(
            f"{cand} & {r_step_num} & {mu10_tex} & {e10_tex} & {mu8_tex} & {e8_tex} & {Einf_tex} & {E1_tex} \\\\"
        )

    out_lines.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "resolution_calibration_multianchor_rows.tex").write_text("\n".join(out_lines), encoding="utf-8")
    print("Wrote sections/generated/resolution_calibration_multianchor_rows.tex")


if __name__ == "__main__":
    main()


