# -*- coding: utf-8 -*-
"""
Neutrino mass-scale interface in the golden resolution coordinate.

This script provides a minimal, auditable conversion from a representative
neutrino mass scale to the (phi-based) resolution depth language used in the
paper's mass-spectrum closure.

We work with a reference mass scale m_nu_ref (GeV) and select the nearest
integer depth r_hat such that:
  m_pred = m_e * phi^{r_hat}

This yields a deterministic "best integer depth" interface, together with the
depth mismatch Δr = r(m_ref) - r_hat and the multiplicative matching factor.

Outputs (LaTeX fragment):
  - sections/generated/neutrino_mass_interface_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

from common_constants import LOG_PHI, M_E_GEV, PHI


def r_of_mu(mu: float, mu0: float) -> float:
    return math.log(mu / mu0) / LOG_PHI


def nearest_int(x: float) -> int:
    # Deterministic rounding to nearest integer with ties to +infinity.
    lo = math.floor(x)
    hi = lo + 1
    if abs(x - float(lo)) < abs(float(hi) - x):
        return int(lo)
    if abs(x - float(lo)) > abs(float(hi) - x):
        return int(hi)
    return int(hi)


def main() -> None:
    # Representative neutrino mass scales (eV) inferred from oscillation splittings.
    # These are not used as premises in the mathematical layer; they are interface inputs.
    dm21 = 7.42e-5  # eV^2
    dm31_no = 2.517e-3  # eV^2 (normal ordering)
    dm31_io = 2.498e-3  # eV^2 (inverted ordering, absolute value)

    # Minimal-mass approximations (m_lightest = 0) for both orderings.
    # Convert eV -> GeV: 1 eV = 1e-9 GeV.
    m_no = {
        "m1": 0.0,
        "m2": math.sqrt(dm21),
        "m3": math.sqrt(dm31_no),
    }
    m_io = {
        "m3": 0.0,
        "m1": math.sqrt(dm31_io),
        "m2": math.sqrt(dm31_io + dm21),
    }

    def to_GeV(x_eV: float) -> float:
        return x_eV * 1.0e-9

    def row_for(ordering: str, label: str, mu_ref: float) -> str:
        if mu_ref <= 0.0:
            return f"{ordering} & {label} & $0$ & $-$ & $-$ & $-$ & $-$ \\\\"
        r_ref = r_of_mu(mu_ref, M_E_GEV)
        r_hat = nearest_int(r_ref)
        mu_pred = M_E_GEV * (PHI ** float(r_hat))
        delta_r = r_ref - float(r_hat)
        ratio = mu_ref / mu_pred
        return f"{ordering} & {label} & ${mu_ref:.6g}$ & {r_ref:.3f} & {r_hat:d} & {delta_r:.3f} & ${ratio:.6g}$ \\\\"

    rows: List[str] = []
    rows.append(row_for("NO", "$m_1$", to_GeV(m_no["m1"])))
    rows.append(row_for("NO", "$m_2$", to_GeV(m_no["m2"])))
    rows.append(row_for("NO", "$m_3$", to_GeV(m_no["m3"])))
    rows.append(row_for("IO", "$m_1$", to_GeV(m_io["m1"])))
    rows.append(row_for("IO", "$m_2$", to_GeV(m_io["m2"])))
    rows.append(row_for("IO", "$m_3$", to_GeV(m_io["m3"])))
    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "neutrino_mass_interface_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/neutrino_mass_interface_rows.tex")


if __name__ == "__main__":
    main()


