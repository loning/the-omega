# -*- coding: utf-8 -*-
"""
Reproducible mass-spectrum table generator for the Z128 stable-sector SM interface.

This script:
  - reconstructs the closed labeling map L_SM (via exp_sm_labeling_solver),
  - computes the normalized depth r_hat for selected fields,
  - outputs a LaTeX table-row fragment into sections/generated/mass_spectrum_rows.tex.

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import exp_sm_labeling_solver as sml


PHI = (1.0 + math.sqrt(5.0)) / 2.0
LOG_PHI = math.log(PHI)


def r_of_mu(mu: float, mu0: float) -> float:
    return math.log(mu / mu0) / LOG_PHI


def latex_sci_sig(x: float, sig: int = 6) -> str:
    """Format positive x as LaTeX scientific notation with sig significant digits."""
    if x == 0.0:
        return "0"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = ax / (10.0**exp)
    mant_s = f"{mant:.{sig}g}"
    try:
        mant_f = float(mant_s)
    except ValueError:
        mant_f = mant
    if mant_f >= 10.0:
        mant_f /= 10.0
        exp += 1
        mant_s = f"{mant_f:.{sig}g}"
    return f"{mant_s}\\times 10^{{{exp}}}"


def latex_number_GeV(mu: float) -> str:
    """Format a positive GeV-scale number for LaTeX tables."""
    if mu == 0.0:
        return "0"
    if mu < 1.0e-3 or mu >= 1.0e3:
        return latex_sci_sig(mu, sig=6)
    return f"{mu:.10g}"


def fmt_fixed(x: float, decimals: int = 3) -> str:
    return f"{x:.{decimals}f}"


@dataclass(frozen=True)
class Row:
    field_tex: str
    mu_ref: Optional[float]
    r_ref: Optional[float]
    r_hat: Optional[int]
    mu_pred: Optional[float]
    ratio: Optional[float]


def build_word_for_field() -> Dict[Tuple[int, str], str]:
    """
    Return a mapping (generation, name) -> stable word w in X6 for fermion multiplets.
    """
    X6 = sml.all_x6()
    boundary = [w for w in X6 if sml.is_boundary_word(w)]
    cyclic = [w for w in X6 if not sml.is_boundary_word(w)]
    if len(boundary) != 3 or len(cyclic) != 18:
        raise AssertionError("Expected split |cyc|=18, |bdry|=3.")

    cyclic_sorted = sorted(cyclic, key=lambda w: sml.stable_type_sort_key(w))
    fields = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
    if len(cyclic_sorted) != len(fields):
        raise AssertionError("Cyclic set and fermion target list must match in size.")

    out: Dict[Tuple[int, str], str] = {}
    for w, f in zip(cyclic_sorted, fields):
        out[(f.generation, f.name)] = w
    return out


def r_star_of_word(w: str, n_hilbert: int = 3) -> int:
    V = sml.zeckendorf_value(w)
    g = sml.degeneracy_g(w)
    return V + n_hilbert * (g - 2)


def main() -> None:
    # Reference masses (GeV). Quark values are scheme-dependent PDG conventions (illustrative).
    m_e = 5.1099895e-4
    ref: Dict[str, float] = {
        "e": m_e,
        "mu": 1.0565838e-1,
        "tau": 1.77686,
        # light quarks at 2 GeV (MSbar) are scheme-dependent; kept as reference inputs
        "u": 2.16e-3,
        "d": 4.67e-3,
        "s": 9.30e-2,
        "c": 1.27,
        "b": 4.18,
        "t": 172.76,
        "W": 80.377,
        "Z": 91.1876,
        "H": 125.25,
    }

    word_for = build_word_for_field()

    # Electron reference field for normalization: e_R^(1)
    w_e = word_for[(1, "e_R")]
    r_star_e = r_star_of_word(w_e)

    kappa = 2  # m/n = 2 for (m,n)=(6,3)

    def r_hat_from_word(w: str) -> int:
        return kappa * (r_star_of_word(w) - r_star_e)

    def mu_pred_from_rhat(rh: int) -> float:
        return m_e * (PHI**rh)

    rows: List[Row] = []

    # Charged leptons from e_R^(g)
    leptons = [
        ("$e$", "e", (1, "e_R")),
        ("$\\mu$", "mu", (2, "e_R")),
        ("$\\tau$", "tau", (3, "e_R")),
    ]
    for field_tex, key, fkey in leptons:
        w = word_for[fkey]
        rh = r_hat_from_word(w)
        mu_ref = ref[key]
        mu_p = mu_pred_from_rhat(rh)
        rows.append(
            Row(
                field_tex=field_tex,
                mu_ref=mu_ref,
                r_ref=r_of_mu(mu_ref, m_e),
                r_hat=rh,
                mu_pred=mu_p,
                ratio=mu_ref / mu_p,
            )
        )

    # Quarks from u_R^(g) and d_R^(g), with generation->(u,c,t) and (d,s,b)
    up = [
        ("$u$", "u", (1, "u_R")),
        ("$c$", "c", (2, "u_R")),
        ("$t$", "t", (3, "u_R")),
    ]
    down = [
        ("$d$", "d", (1, "d_R")),
        ("$s$", "s", (2, "d_R")),
        ("$b$", "b", (3, "d_R")),
    ]
    for field_tex, key, fkey in up + down:
        w = word_for[fkey]
        rh = r_hat_from_word(w)
        mu_ref = ref[key]
        mu_p = mu_pred_from_rhat(rh)
        rows.append(
            Row(
                field_tex=field_tex,
                mu_ref=mu_ref,
                r_ref=r_of_mu(mu_ref, m_e),
                r_hat=rh,
                mu_pred=mu_p,
                ratio=mu_ref / mu_p,
            )
        )

    # Neutrinos: record a reference scale (normal ordering, minimal m1) but do not fix prediction here.
    nu_scale = 5.0e-11  # 0.05 eV ~ 5e-11 GeV (order-of-magnitude scale)
    rows.append(
        Row(
            field_tex="$\\nu$ (scale)",
            mu_ref=nu_scale,
            r_ref=r_of_mu(nu_scale, m_e),
            r_hat=None,
            mu_pred=None,
            ratio=None,
        )
    )

    # Electroweak bosons and Higgs: use nearest-integer depth anchors at the Z scale.
    ew = [
        ("$W$", "W", 25),
        ("$Z$", "Z", 25),
        ("$H$", "H", 26),
    ]
    for field_tex, key, rh in ew:
        mu_ref = ref[key]
        mu_p = mu_pred_from_rhat(rh)
        rows.append(
            Row(
                field_tex=field_tex,
                mu_ref=mu_ref,
                r_ref=r_of_mu(mu_ref, m_e),
                r_hat=rh,
                mu_pred=mu_p,
                ratio=mu_ref / mu_p,
            )
        )

    # Sort rows by reference r where available, else push to end.
    def sort_key(row: Row) -> Tuple[int, float, str]:
        if row.r_ref is None:
            return (1, 0.0, row.field_tex)
        return (0, row.r_ref, row.field_tex)

    rows_sorted = sorted(rows, key=sort_key)

    out_lines: List[str] = []
    for row in rows_sorted:
        mu_ref_tex = "$-$" if row.mu_ref is None else f"${latex_number_GeV(row.mu_ref)}$"
        r_ref_tex = "$-$" if row.r_ref is None else f"{fmt_fixed(row.r_ref, 3)}"
        r_hat_tex = "$-$" if row.r_hat is None else f"{row.r_hat:d}"
        mu_pred_tex = "$-$" if row.mu_pred is None else f"${latex_number_GeV(row.mu_pred)}$"
        ratio_tex = "$-$" if row.ratio is None else f"${row.ratio:.6g}$"
        out_lines.append(
            f"{row.field_tex} & {mu_ref_tex} & {r_ref_tex} & {r_hat_tex} & {mu_pred_tex} & {ratio_tex} \\\\"
        )

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "mass_spectrum_rows.tex"
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print("Wrote sections/generated/mass_spectrum_rows.tex")


if __name__ == "__main__":
    main()


