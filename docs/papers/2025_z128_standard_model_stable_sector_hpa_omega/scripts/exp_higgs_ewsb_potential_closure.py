# -*- coding: utf-8 -*-
"""
Interface-level EWSB / Higgs-potential closure on a bounded candidate family.

This script closes (within a declared bounded family):
  - the minimal renormalizable Higgs potential form needed for EWSB and stability,
  - and reports the derived parameter pair (mu^2, lambda) using the paper's
    existing Z/H reference masses and the closed electroweak normalization.

Layer discipline:
  - The potential form selection is a CAP-style choice in a finite family.
  - Numeric values are reported only as derived interface dictionary quantities,
    consistent with the existing paper constants and propositions.

Outputs (LaTeX fragments)
  - sections/generated/higgs_ewsb_potential_rows.tex
  - sections/generated/higgs_ewsb_potential_summary.tex

Only Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

from common_constants import M_H_GEV, M_Z_GEV
from common_paths import generated_dir
from common_tex import write_lines


@dataclass(frozen=True)
class Cand:
    name: str
    # Model flags for a bounded family of scalar potentials V(H):
    #   V = s2 * mu^2 H†H + s4 * lambda (H†H)^2 + sextic * kappa (H†H)^3
    s2: int  # +1 or -1
    has_quartic: bool
    s4: int  # +1 or -1 (only used if has_quartic)
    has_sextic: bool

    def tex(self) -> str:
        parts: List[str] = []
        mu_term = r"\mu^2 H^\dagger H"
        if self.s2 == -1:
            parts.append(rf"-{mu_term}")
        else:
            parts.append(rf"+{mu_term}")
        if self.has_quartic:
            lam_term = r"\lambda (H^\dagger H)^2"
            if self.s4 == -1:
                parts.append(rf"-{lam_term}")
            else:
                parts.append(rf"+{lam_term}")
        if self.has_sextic:
            parts.append(r"+\kappa (H^\dagger H)^3")
        return "$" + " ".join(parts).lstrip("+") + "$"


def _cand_family() -> List[Cand]:
    # Explicit bounded family (no free knobs):
    return [
        Cand(name="V0", s2=+1, has_quartic=False, s4=+1, has_sextic=False),
        Cand(name="V2(+)", s2=+1, has_quartic=False, s4=+1, has_sextic=False),
        Cand(name="V2(-)", s2=-1, has_quartic=False, s4=+1, has_sextic=False),
        Cand(name="V4(++)", s2=+1, has_quartic=True, s4=+1, has_sextic=False),
        Cand(name="V4(+-)", s2=+1, has_quartic=True, s4=-1, has_sextic=False),
        Cand(name="V4(-+)", s2=-1, has_quartic=True, s4=+1, has_sextic=False),
        Cand(name="V4(--)", s2=-1, has_quartic=True, s4=-1, has_sextic=False),
        Cand(name="V6", s2=-1, has_quartic=True, s4=+1, has_sextic=True),
    ]


def _closed_v_from_mz() -> float:
    """
    Closed electroweak interface dictionary for v (as used in Appendix 48):
      v = 2 m_Z sqrt(15 pi / 26).
    """
    return 2.0 * float(M_Z_GEV) * math.sqrt(15.0 * math.pi / 26.0)


def _derived_lambda_mu2(v: float) -> Tuple[float, float]:
    """
    Using standard tree-level relation m_h^2 = 2 lambda v^2 and convention
    V = -mu^2 |H|^2 + lambda |H|^4 (mu^2>0, lambda>0):
      lambda = m_h^2 / (2 v^2)
      mu^2    = lambda v^2 = m_h^2 / 2
    """
    mh = float(M_H_GEV)
    lam = (mh * mh) / (2.0 * v * v)
    mu2 = 0.5 * mh * mh
    return lam, mu2


def _gates(c: Cand) -> Tuple[bool, bool, bool, bool]:
    """
    Return (renormalizable, stable, ewsb, higgs_mass_supported).
    - renormalizable: no sextic term (deg<=4)
    - stable: quartic present with +lambda sign (s4=+1)
    - ewsb: negative mass term (s2=-1) AND stable quartic present
    - higgs_mass_supported: quartic present with + sign (tree-level m_h^2=2 lambda v^2)
    """
    ren = not c.has_sextic
    stable = c.has_quartic and (c.s4 == +1)
    ewsb = (c.s2 == -1) and stable
    higgs_mass = stable  # in this minimal family we use the standard quartic relation
    return ren, stable, ewsb, higgs_mass


def _cap_key(c: Cand) -> tuple:
    """
    Deterministic CAP key:
      minimize missing gates, then prefer renormalizable, then minimal terms, then fixed lex order.
    """
    ren, stable, ewsb, hm = _gates(c)
    miss = sum(1 for ok in (ren, stable, ewsb, hm) if not ok)
    # Complexity proxies (bounded family): number of terms, and whether sextic appears.
    n_terms = 1 + (1 if c.has_quartic else 0) + (1 if c.has_sextic else 0)
    sext = 1 if c.has_sextic else 0
    # Tie-break by (miss, sext, n_terms, name).
    return (miss, sext, n_terms, c.name)


def main() -> None:
    v = _closed_v_from_mz()
    lam, mu2 = _derived_lambda_mu2(v)

    fam = _cand_family()
    fam_sorted = sorted(fam, key=_cap_key)
    best = fam_sorted[0]

    out_rows: List[str] = []
    for c in fam_sorted:
        ren, stable, ewsb, hm = _gates(c)
        k = _cap_key(c)
        status = "\\textbf{min}" if c == best else ""
        out_rows.append(
            f"{c.name} & {c.tex()} & "
            f"{'yes' if ren else 'no'} & {'yes' if stable else 'no'} & {'yes' if ewsb else 'no'} & "
            f"{'yes' if hm else 'no'} & "
            f"({k[0]},{k[1]},{k[2]}) & {status} \\\\"
        )

    write_lines(generated_dir() / "higgs_ewsb_potential_rows.tex", out_rows)

    summary = [
        "\\noindent "
        "Bounded-family CAP closure of the electroweak scalar potential (interface): "
        "within an explicit finite family of low-degree $V(H)$ templates, the unique minimizer "
        "is the renormalizable Mexican-hat form "
        "$V(H)=-\\mu^2 H^\\dagger H+\\lambda (H^\\dagger H)^2$ with $\\mu^2>0$ and $\\lambda>0$, "
        "as it is the minimal candidate that is simultaneously stable and admits EWSB "
        "($\\langle H\\rangle\\neq 0$) in the standard EFT embedding. "
        f"Using the closed $Z$-scale electroweak normalization, $v=2m_Z\\sqrt{{15\\pi/26}}\\approx {v:.6f}\\,\\mathrm{{GeV}}$, "
        f"and with the paper's Higgs reference mass $m_H={M_H_GEV:.4g}\\,\\mathrm{{GeV}}$ one obtains "
        f"$\\lambda=m_H^2/(2v^2)\\approx {lam:.6f}$ and $\\mu^2=m_H^2/2\\approx {mu2:.6f}\\,\\mathrm{{GeV}}^2$."
    ]
    write_lines(generated_dir() / "higgs_ewsb_potential_summary.tex", summary)

    print("Wrote sections/generated/higgs_ewsb_potential_rows.tex")
    print("Wrote sections/generated/higgs_ewsb_potential_summary.tex")


if __name__ == "__main__":
    main()

