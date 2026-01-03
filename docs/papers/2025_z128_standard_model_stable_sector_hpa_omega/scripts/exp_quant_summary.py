#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate the quantitative summary table rows used in the main text.

Outputs (LaTeX fragments):
  - sections/generated/quant_summary_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import List

from common_constants import (
    ALPHA_INV_CODATA_2022,
    ALPHAZ_INV_PDG,
    JARLSKOG_PDG_CENTRAL,
    SIN2_THETAW_PDG,
)
from common_paths import generated_dir
from common_tex import write_lines


def _sci_tex_signed(x: float, sig: int = 3) -> str:
    """
    Signed scientific notation for LaTeX, using '\\times 10^{...}'.
    """
    if x == 0.0:
        return "0"
    sign = "+" if x > 0.0 else "-"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = ax / (10.0**exp)
    mant_str = f"{mant:.{sig}g}"
    # Normalize rounding edge case (e.g., 9.99 -> 10.0).
    if mant_str.startswith("10"):
        exp += 1
        mant = ax / (10.0**exp)
        mant_str = f"{mant:.{sig}g}"
    return rf"{sign}{mant_str}\times 10^{{{exp}}}"


def _sci_tex_pos(x: float, sig: int = 3) -> str:
    """
    Positive scientific notation for LaTeX.
    """
    if x == 0.0:
        return "0"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = ax / (10.0**exp)
    mant_str = f"{mant:.{sig}g}"
    if mant_str.startswith("10"):
        exp += 1
        mant = ax / (10.0**exp)
        mant_str = f"{mant:.{sig}g}"
    return rf"{mant_str}\times 10^{{{exp}}}"


def _sci_tex_pos_fixed(x: float, mant_decimals: int = 2) -> str:
    """
    Positive scientific notation with a fixed number of mantissa decimals.
    """
    if x == 0.0:
        return "0"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = ax / (10.0**exp)
    mant_str = f"{mant:.{mant_decimals}f}"
    if mant_str.startswith("10"):
        exp += 1
        mant = ax / (10.0**exp)
        mant_str = f"{mant:.{mant_decimals}f}"
    return rf"{mant_str}\times 10^{{{exp}}}"


def main() -> None:
    pi = math.pi

    alpha_geo_inv = 4.0 * (pi**3) + (pi**2) + pi
    alphaZ_inv_closed = 13.0 * (pi**2)
    sin2_closed = 3.0 / 13.0
    j_geo = 1.0 / (11.0 * (pi**7))

    rows: List[str] = []

    alpha_ref_str = f"{ALPHA_INV_CODATA_2022:.12f}".rstrip("0").rstrip(".")
    rows.append(
        rf"$\alpha_{{\mathrm{{em}}}}^{{-1}}$ (low energy) & $4\pi^3+\pi^2+\pi$ & ${alpha_ref_str}$ (CODATA 2022) & ${_sci_tex_signed(math.log(alpha_geo_inv / ALPHA_INV_CODATA_2022), sig=3)}$ \\"
    )
    rows.append(
        rf"$\alpha^{{-1}}(\mu_Z)$ & $13\pi^2$ & ${ALPHAZ_INV_PDG:.3f}$ (PDG) & ${_sci_tex_signed(math.log(alphaZ_inv_closed / ALPHAZ_INV_PDG), sig=3)}$ \\"
    )
    rows.append(
        rf"$\sin^2\theta_W(\mu_Z)$ & $3/13$ & ${SIN2_THETAW_PDG:.5f}$ (PDG, $\overline{{\mathrm{{MS}}}}$) & ${_sci_tex_signed(math.log(sin2_closed / SIN2_THETAW_PDG), sig=3)}$ \\"
    )
    rows.append(
        rf"$J$ (CKM) & $1/(11\pi^7)$ & ${_sci_tex_pos_fixed(JARLSKOG_PDG_CENTRAL, mant_decimals=2)}$ (PDG) & ${_sci_tex_signed(math.log(j_geo / JARLSKOG_PDG_CENTRAL), sig=3)}$ \\"
    )
    rows.append(r"\bottomrule")

    out = generated_dir() / "quant_summary_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/quant_summary_rows.tex")


if __name__ == "__main__":
    main()


