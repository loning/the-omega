#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compute closed-form Taylor coefficients for the pure-collision cubic pressure.

We work with the 4x4 input-skeleton matrix:
  A_xi(u) = D(u) (F ⊗ F),  D(u)=diag(1,1,1,u),
whose characteristic polynomial factors as:
  det(λI - A_xi(u)) = (λ+1)(λ^3 - 2λ^2 - (u+1)λ + u).

Define u = exp(z) and the principal Perron branch ρ(z) solving the cubic
with ρ(0)=φ^2, then define the pressure:
  P_xi(z) = log ρ(z).

This script computes exact closed forms for P_xi''(0) and P_xi^{(4)}(0),
exports a small LaTeX table, and writes a JSON artifact.

All output is English-only by repository convention.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

import sympy as sp

from common_paths import export_dir, generated_dir


@dataclass(frozen=True)
class Coeffs:
    P2: str
    P4: str
    kappa_inf: str
    beta: str


def _series_perron_branch(order: int = 6) -> sp.SeriesBase:
    z = sp.Symbol("z")
    u = sp.exp(z)
    # Perron root at u=1 is φ^2.
    phi = (1 + sp.sqrt(5)) / 2
    rho0 = sp.simplify(phi**2)

    # Unknown power series rho(z) = sum_{n>=0} a_n z^n
    a = sp.symbols(f"a0:{order}")
    rho = sum(a[n] * z**n for n in range(order))
    eq = sp.expand(rho**3 - 2 * rho**2 - (u + 1) * rho + u)
    eqs = []
    # impose a0=rho0
    eqs.append(sp.Eq(a[0], rho0))
    # match coefficients of z^n for n=0..order-1 in cubic equation
    series_eq = sp.series(eq, z, 0, order).removeO()
    for n in range(order):
        eqs.append(sp.Eq(sp.expand(series_eq).coeff(z, n), 0))
    # Solve sequentially; sympy can do a direct solve because it's triangular.
    sol = sp.solve(eqs, list(a), dict=True)
    if not sol:
        raise RuntimeError("Failed to solve series coefficients for Perron branch.")
    rho_series = sp.expand(rho.subs(sol[0]))
    return sp.series(rho_series, z, 0, order)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute closed-form P_xi''(0), P_xi^{(4)}(0) for pure-collision cubic.")
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "arity_pure_collision_cubic_asymp_coeffs.json"),
    )
    parser.add_argument(
        "--tex-out",
        type=str,
        default=str(generated_dir() / "tab_arity_pure_collision_cubic_asymp_coeffs.tex"),
    )
    args = parser.parse_args()

    z = sp.Symbol("z")
    rho_ser = _series_perron_branch(order=8).removeO()
    P_ser = sp.series(sp.log(rho_ser), z, 0, 8).removeO()

    # Extract derivatives via series coefficients.
    c2 = sp.expand(P_ser).coeff(z, 2)
    c4 = sp.expand(P_ser).coeff(z, 4)
    P2 = sp.simplify(2 * c2)  # 2! * c2
    P4 = sp.simplify(24 * c4)  # 4! * c4

    kappa_inf = sp.simplify(P2 / 2)
    beta = sp.simplify(P4 / 24)

    coeffs = Coeffs(P2=sp.latex(P2), P4=sp.latex(P4), kappa_inf=sp.latex(kappa_inf), beta=sp.latex(beta))

    jout = Path(args.json_out)
    jout.parent.mkdir(parents=True, exist_ok=True)
    jout.write_text(json.dumps({"coeffs": asdict(coeffs)}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[pure-collision-asymp] wrote {jout}", flush=True)

    tout = Path(args.tex_out)
    tout.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append(
        "\\caption{Closed-form Taylor data for the pure-collision cubic pressure "
        "$P_\\xi(z)=\\log\\rho(A_\\xi(e^{z}))$ at $z=0$ (Perron branch).}"
    )
    lines.append("\\label{tab:arity_pure_collision_cubic_asymp_coeffs}")
    lines.append("\\begin{tabular}{l l}")
    lines.append("\\toprule")
    lines.append("$P_\\xi''(0)$ & $" + coeffs.P2 + "$\\\\")
    lines.append("$P_\\xi^{(4)}(0)$ & $" + coeffs.P4 + "$\\\\")
    lines.append("$\\kappa_\\infty=P_\\xi''(0)/2$ & $" + coeffs.kappa_inf + "$\\\\")
    lines.append("$\\beta=P_\\xi^{(4)}(0)/24$ & $" + coeffs.beta + "$\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    tout.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[pure-collision-asymp] wrote {tout}", flush=True)


if __name__ == "__main__":
    main()

