# -*- coding: utf-8 -*-
"""
End-to-end kernel demo: mu/r -> m_eff(mu) -> kernel quantities at that m.

This script implements the closed staircase calibration used in the paper:
  r(mu) = log(mu/m_e) / log(phi),
  r_step = 2*pi,
  r_th(m) = (m-6)*r_step,
  mu_th(m) = m_e * phi^{r_th(m)},
  m_eff(mu) = 6 + floor(r(mu)/r_step).

We report, at the threshold energies mu_th(m) (so that m_eff(mu_th(m)) = m),
selected kernel quantities at that m, including the folding maximal degeneracy r_m.

Output (LaTeX fragment):
  - sections/generated/kernel_mu_r_bridge_rows.tex

Only the Python standard library is required.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from common_constants import M_E_GEV, PHI
from common_paths import generated_dir
from common_tex import write_lines
from protocol_kernel import all_xm, cached_degeneracy_map, split_cyc_bdry


def r_of_mu(mu: float) -> float:
    if mu <= 0.0:
        raise ValueError("mu must be positive.")
    return math.log(mu / M_E_GEV) / math.log(PHI)


def m_eff(mu: float, r_step: float) -> int:
    r = r_of_mu(mu)
    return 6 + int(math.floor(r / r_step))


def mu_threshold(m: int, r_step: float) -> Tuple[float, float]:
    r_th = float(m - 6) * r_step
    mu = M_E_GEV * (PHI ** r_th)
    return r_th, mu


def fmt_mu(mu: float) -> str:
    if mu == 0.0:
        return "0"
    if mu < 1.0e-3 or mu >= 1.0e4:
        exp = int(math.floor(math.log10(abs(mu))))
        mant = mu / (10.0**exp)
        return f"{mant:.6g}\\times 10^{{{exp}}}"
    return f"{mu:.6g}"


def main() -> None:
    r_step = 2.0 * math.pi

    # Keep the demo small and aligned with the paper's visible spectrum range.
    m_list = [6, 7, 8, 9, 10, 11, 12]

    rows: List[str] = []
    for m in m_list:
        r_th, mu_th = mu_threshold(m, r_step=r_step)
        m_sel = m_eff(mu_th, r_step=r_step)
        if m_sel != m:
            raise AssertionError("m_eff(mu_th(m)) should equal m by construction.")

        Xm = all_xm(m)
        cyc, bdry = split_cyc_bdry(Xm)

        gm = cached_degeneracy_map(m)
        g_values = [gm[w] for w in Xm]
        g_min = min(g_values)
        g_max = max(g_values)

        rows.append(
            f"{m} & {r_th:.3f} & ${fmt_mu(mu_th)}$ & {m_sel} & {len(Xm)} & {len(cyc)} & {len(bdry)} & {g_min} & {g_max} \\\\"
        )

    rows.append("\\bottomrule")

    out_path = generated_dir() / "kernel_mu_r_bridge_rows.tex"
    write_lines(out_path, rows)
    print("Wrote sections/generated/kernel_mu_r_bridge_rows.tex")


if __name__ == "__main__":
    main()

