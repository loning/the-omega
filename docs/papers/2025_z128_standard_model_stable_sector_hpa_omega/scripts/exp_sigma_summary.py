# -*- coding: utf-8 -*-
"""
Sigma-normalized mismatch summary for key dimensionless targets.

This script is a compact reporting layer: it converts several closed targets and
their reference values into:
  - absolute error,
  - sigma-normalized error (|err|/sigma),
using the explicit sigma scales stored in common_constants.py.

IMPORTANT:
  - The sigma values are those used by audit scripts (either quoted uncertainties
    or explicit deterministic stress-test scales). This is an interpretive summary,
    not a statistical claim about experimental compatibility.

Output (LaTeX fragment):
  - sections/generated/sigma_summary_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from common_constants import (
    ALPHA_INV_CODATA_2022,
    ALPHA_INV_CODATA_2022_SIGMA,
    ALPHAZ_INV_PDG,
    ALPHAZ_INV_PDG_SIGMA,
    CKM_VCB_REF,
    CKM_VCB_SIGMA,
    CKM_VUB_REF,
    CKM_VUB_SIGMA,
    CKM_VUS_REF,
    CKM_VUS_SIGMA,
    JARLSKOG_PDG_CENTRAL,
    JARLSKOG_PDG_SIGMA,
    PHI,
    PMNS_DELTA_REF_DEG,
    PMNS_DELTA_SIGMA_DEG,
    PMNS_SIN2_T12_REF,
    PMNS_SIN2_T12_SIGMA,
    PMNS_SIN2_T13_REF,
    PMNS_SIN2_T13_SIGMA,
    PMNS_SIN2_T23_REF,
    PMNS_SIN2_T23_SIGMA,
    SIN2_THETAW_PDG,
    SIN2_THETAW_PDG_SIGMA,
)
from common_tex import write_lines
from common_paths import generated_dir


def _sci_tex(x: float, sig: int = 3) -> str:
    if x == 0.0:
        return "0"
    sign = "-" if x < 0.0 else ""
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = ax / (10.0**exp)
    mant_str = f"{mant:.{sig}g}"
    if mant_str.startswith("10"):
        exp += 1
        mant = ax / (10.0**exp)
        mant_str = f"{mant:.{sig}g}"
    return rf"{sign}{mant_str}\times 10^{{{exp}}}"


def _fmt(x: float) -> str:
    # Compact numeric format for table cells.
    if x == 0.0:
        return "0"
    ax = abs(x)
    if ax < 1e-3 or ax >= 1e4:
        return _sci_tex(x, sig=4)
    return f"{x:.8g}"


def _sigma_err(err: float, sigma: float) -> float:
    if sigma <= 0.0:
        return float("inf")
    return abs(err) / sigma


def _row(name: str, closed: float, ref: float, sigma: float) -> str:
    err = closed - ref
    se = _sigma_err(err, sigma)
    # Wrap numeric cells in math mode (values may include '\times 10^{...}').
    return rf"{name} & ${_fmt(closed)}$ & ${_fmt(ref)}$ & ${_fmt(sigma)}$ & ${_fmt(err)}$ & ${_fmt(se)}$ \\"


def main() -> None:
    pi = math.pi

    rows: List[str] = []

    # Couplings / electroweak / CKM J
    alpha_geo_inv = 4.0 * (pi**3) + (pi**2) + pi
    rows.append(_row(r"$\alpha_{\mathrm{em}}^{-1}$", alpha_geo_inv, ALPHA_INV_CODATA_2022, ALPHA_INV_CODATA_2022_SIGMA))

    alphaZ_closed = 13.0 * (pi**2)
    rows.append(_row(r"$\alpha^{-1}(\mu_Z)$", alphaZ_closed, ALPHAZ_INV_PDG, ALPHAZ_INV_PDG_SIGMA))

    sin2_closed = 3.0 / 13.0
    rows.append(_row(r"$\sin^2\theta_W(\mu_Z)$", sin2_closed, SIN2_THETAW_PDG, SIN2_THETAW_PDG_SIGMA))

    j_geo = 1.0 / (11.0 * (pi**7))
    rows.append(_row(r"$J$ (CKM)", j_geo, JARLSKOG_PDG_CENTRAL, JARLSKOG_PDG_SIGMA))

    # CKM magnitudes (from the documented B=20 minimizer: d=20, k23=13, k13=23)
    vus_closed = 1.0 / math.sqrt(20.0)
    vcb_closed = PHI ** (-0.5 * 13.0)
    vub_closed = PHI ** (-0.5 * 23.0)
    rows.append(_row(r"$|V_{us}|$", vus_closed, CKM_VUS_REF, CKM_VUS_SIGMA))
    rows.append(_row(r"$|V_{cb}|$", vcb_closed, CKM_VCB_REF, CKM_VCB_SIGMA))
    rows.append(_row(r"$|V_{ub}|$", vub_closed, CKM_VUB_REF, CKM_VUB_SIGMA))

    # PMNS sin^2 values (from the documented B=20 minimizer: 4/13, 6/11, k13=8 -> s13=phi^{-4})
    pmns_s2_12_closed = 4.0 / 13.0
    pmns_s2_23_closed = 6.0 / 11.0
    pmns_s2_13_closed = (PHI ** (-4.0)) ** 2
    rows.append(_row(r"$\sin^2\theta_{12}$ (PMNS)", pmns_s2_12_closed, PMNS_SIN2_T12_REF, PMNS_SIN2_T12_SIGMA))
    rows.append(_row(r"$\sin^2\theta_{23}$ (PMNS)", pmns_s2_23_closed, PMNS_SIN2_T23_REF, PMNS_SIN2_T23_SIGMA))
    rows.append(_row(r"$\sin^2\theta_{13}$ (PMNS)", pmns_s2_13_closed, PMNS_SIN2_T13_REF, PMNS_SIN2_T13_SIGMA))

    # PMNS delta (degrees): closed minimizer in the bounded-denominator family at Q=12 is 13*pi/12 = 195 deg.
    delta_closed_deg = 195.0
    rows.append(_row(r"$\delta$ (PMNS) [deg]", delta_closed_deg, PMNS_DELTA_REF_DEG, PMNS_DELTA_SIGMA_DEG))

    rows.append(r"\bottomrule")

    out = generated_dir() / "sigma_summary_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/sigma_summary_rows.tex")


if __name__ == "__main__":
    main()


