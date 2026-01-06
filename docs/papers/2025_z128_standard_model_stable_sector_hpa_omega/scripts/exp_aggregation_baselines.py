# -*- coding: utf-8 -*-
"""
Systematic aggregation baselines for coupling/CP normalization dictionaries.

This script provides small, explicit counterfactual baselines used in the paper:
  - alternative aggregation rules for the three-stratum alpha impedance,
  - alternative multiplicity counts for the Jarlskog normalization 1/(d*pi^7).

Outputs (LaTeX fragments):
  - sections/generated/alpha_aggregation_baselines_rows.tex
  - sections/generated/j_multiplicity_baselines_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, List, Tuple

from common_constants import ALPHA_INV_CODATA_2022, JARLSKOG_PDG_CENTRAL
from common_paths import generated_dir
from common_tex import write_lines


def _sci_tex(x: float, sig: int = 3) -> str:
    """
    Signed scientific-notation TeX string for x (nonzero):
      +2.22\\times 10^{-6}
    """
    if x == 0.0:
        return "0"
    sign = "+" if x > 0 else "-"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    coeff = ax / (10.0 ** exp)
    # Round to sig digits for coeff in [1,10).
    coeff_str = f"{coeff:.{max(sig - 1, 0)}f}"
    # Handle rounding overflow, e.g. 9.99 -> 10.0
    if float(coeff_str) >= 10.0:
        coeff = coeff / 10.0
        exp += 1
        coeff_str = f"{coeff:.{max(sig - 1, 0)}f}"
    if exp == 0:
        return f"{sign}{coeff_str}"
    return f"{sign}{coeff_str}\\times 10^{{{exp}}}"


def _sci_value_tex(x: float, exp: int, digits: int = 9) -> str:
    """
    TeX string in the form c\\times 10^{exp} with fixed exp and decimal digits in c.
    """
    if x == 0.0:
        return f"0\\times 10^{{{exp}}}"
    coeff = x / (10.0 ** exp)
    coeff_str = f"{coeff:.{digits}f}"
    return f"{coeff_str}\\times 10^{{{exp}}}"


def _sci_value_auto_tex(x: float, digits: int = 9) -> str:
    """
    TeX string in the form c\\times 10^{e} with c in [1,10) (for x>0).
    """
    if x == 0.0:
        return "0"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    coeff = x / (10.0 ** exp)
    coeff_str = f"{coeff:.{digits}f}"
    if float(coeff_str) >= 10.0:
        coeff = coeff / 10.0
        exp += 1
        coeff_str = f"{coeff:.{digits}f}"
    return f"{coeff_str}\\times 10^{{{exp}}}"


@dataclass(frozen=True)
class Agg:
    name: str
    fn: Callable[[float, float, float], float]


def write_alpha_aggregation_baselines() -> None:
    pi = math.pi
    v_bulk = 4.0 * (pi**3)
    v_bdry = pi**2
    v_line = pi
    ref = ALPHA_INV_CODATA_2022

    aggs: List[Agg] = [
        Agg("serial sum", lambda a, b, c: a + b + c),
        Agg("Euclidean", lambda a, b, c: math.sqrt(a * a + b * b + c * c)),
        Agg("max", lambda a, b, c: max(a, b, c)),
        Agg("parallel", lambda a, b, c: 1.0 / (1.0 / a + 1.0 / b + 1.0 / c)),
        Agg("arithmetic mean", lambda a, b, c: (a + b + c) / 3.0),
        Agg("geometric mean", lambda a, b, c: (a * b * c) ** (1.0 / 3.0)),
    ]

    rows: List[str] = []
    for agg in aggs:
        val = agg.fn(v_bulk, v_bdry, v_line)
        lm = math.log(val / ref)
        val_str = f"{val:.10f}"
        lm_str = _sci_tex(lm, sig=3)
        name_cell = agg.name
        val_cell = val_str
        lm_cell = f"${lm_str}$"
        if agg.name == "serial sum":
            name_cell = r"\textbf{serial sum}"
            val_cell = r"\textbf{" + val_str + "}"
            lm_cell = r"\textbf{$" + lm_str + "$}"
        rows.append(f"{name_cell} & {val_cell} & {lm_cell} \\\\")

    rows.append(r"\bottomrule")

    out = generated_dir() / "alpha_aggregation_baselines_rows.tex"
    write_lines(out, rows)
    print(f"Wrote {out}")


def write_j_multiplicity_baselines() -> None:
    pi = math.pi
    ref = JARLSKOG_PDG_CENTRAL

    # Candidate multiplicities (small, explicit, auditable).
    # d=11 is the paper's default: dim(su3)+dim(su2)=8+3.
    candidates: List[Tuple[str, int]] = [
        (r"$\dim(\mathfrak{su}(3))+\dim(\mathfrak{su}(2))$", 11),
        (r"$\dim(\mathfrak{su}(3))+\dim(\mathfrak{su}(2))+\dim(\mathfrak{u}(1))$", 12),
        (r"$\dim(\mathfrak{su}(3))$", 8),
        (r"$\dim(\mathfrak{su}(2))$", 3),
        (r"$\dim(\mathfrak{su}(3))+\dim(\mathfrak{u}(1))$", 9),
        (r"$\dim(\mathfrak{su}(2))+\dim(\mathfrak{u}(1))$", 4),
    ]

    rows: List[str] = []
    for desc, d in candidates:
        val = 1.0 / (float(d) * (pi**7))
        lm = math.log(val / ref)
        val_str = _sci_value_auto_tex(val, digits=9)
        lm_str = _sci_tex(lm, sig=3)
        d_tex = f"{d}"
        val_cell = f"${val_str}$"
        lm_cell = f"${lm_str}$"
        if d == 11:
            desc = r"\textbf{" + desc + "}"
            d_tex = r"\textbf{11}"
            val_cell = r"\textbf{$" + val_str + "$}"
            lm_cell = r"\textbf{$" + lm_str + "$}"
        rows.append(f"{desc} & {d_tex} & {val_cell} & {lm_cell} \\\\")

    rows.append(r"\bottomrule")

    out = generated_dir() / "j_multiplicity_baselines_rows.tex"
    write_lines(out, rows)
    print(f"Wrote {out}")


def main() -> None:
    write_alpha_aggregation_baselines()
    write_j_multiplicity_baselines()


if __name__ == "__main__":
    main()


