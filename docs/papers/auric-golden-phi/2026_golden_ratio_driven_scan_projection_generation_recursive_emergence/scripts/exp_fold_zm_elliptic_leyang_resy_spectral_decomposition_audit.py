#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit the Lee–Yang branch elimination image in the spectral variable lambda.

This script is English-only by repository convention.

We verify, over Q[lambda]:
  - The exact factorization
      Res_y(Pi(lambda,y), P_LY(y))
        = (16 lambda^3 - 9 lambda^2 + 1)^2
          * (256 lambda^6 - 480 lambda^5 + 201 lambda^4 + 750 lambda^3
             - 921 lambda^2 - 78 lambda + 704),
    where Pi(lambda,y)=lambda^4-lambda^3-(2y+1)lambda^2+lambda+y(y+1)
    and P_LY(y)=256y^3+411y^2+165y+32.

We also verify the refined double-root branch rigidity on the Lee–Yang locus:
  - In the quotient ring Q[y,lambda]/(P_LY(y)), the system Pi=0 and dPi/dlambda=0
    implies the linear relation
        279 lambda + 512 y^2 + 518 y + 5 = 0,
    and the Lee–Yang cubic factor 16 lambda^3 - 9 lambda^2 + 1 reduces to 0.
  - Under the elliptic weight convention y = lambda^2 + Y - 1/2 (so Y = y - lambda^2 + 1/2),
    the ramification point over the Lee–Yang cubic field K=Q(y) admits the closed coordinates
        lambda = -(512 y^2 + 518 y + 5)/279,
        Y      =  (512 y^2 + 1262 y + 377)/558,
    and satisfies the ramification equation 4 lambda Y + 3 lambda^2 - 1 = 0.
  - A hidden square identity holds in K:
        ((-512 y^2 + 226 y + 367)/93)^2 = 64 y^2 + 64 y + 25.

Outputs:
  - artifacts/export/fold_zm_elliptic_leyang_resy_spectral_decomposition_audit.json
  - sections/generated/eq_fold_zm_elliptic_leyang_resy_spectral_decomposition_audit.tex
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Tuple

import sympy as sp

from common_paths import export_dir, generated_dir


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _clear_denominators_linear_in_lam(poly: sp.Poly, lam: sp.Symbol, y: sp.Symbol) -> Tuple[int, sp.Expr]:
    """Given poly(lam,y) with deg_lam==1 over QQ, clear denominators to ZZ and return (content, prim)."""
    if poly.degree(lam) != 1:
        raise ValueError("expected a polynomial linear in lam")
    # Determine a common denominator for all rational coefficients.
    lcm = 1
    for c in poly.coeffs():
        lcm = (lcm * int(sp.denom(c))) // sp.igcd(lcm, int(sp.denom(c)))
    prim = sp.expand(lcm * poly.as_expr())
    P = sp.Poly(prim, lam, y, domain=sp.ZZ)  # coefficients now integral
    content, prim_poly = P.primitive()
    return int(content), prim_poly.as_expr()


@dataclass(frozen=True)
class Payload:
    resultant_ok: bool
    resultant_degree: int
    groebner_linear_ok: bool
    groebner_linear_prim: str
    cubic_reduces_ok: bool
    branch_Y_formula_ok: bool
    branch_ramification_ok: bool
    branch_curve_eq_ok: bool
    hidden_square_ok: bool


def _is_zero_mod_univariate(expr: sp.Expr, *, y: sp.Symbol, modulus: sp.Expr) -> bool:
    """Return True iff expr == 0 in QQ[y]/(modulus)."""
    num = sp.together(expr).as_numer_denom()[0]
    P = sp.Poly(modulus, y, domain=sp.QQ)
    rem = sp.Poly(sp.expand(num), y, domain=sp.QQ).rem(P)
    return bool(rem.is_zero)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Res_y(Pi,P_LY) factorization and the Lee–Yang double-root branch.")
    parser.add_argument("--no-output", action="store_true", help="Skip writing JSON/TeX outputs.")
    args = parser.parse_args()

    t0 = time.time()
    print("[fold-zm-elliptic-leyang-resy] start", flush=True)

    lam, y = sp.symbols("lam y")
    Pi = lam**4 - lam**3 - (2 * y + 1) * lam**2 + lam + y * (y + 1)
    dPi = sp.diff(Pi, lam)
    P_LY = 256 * y**3 + 411 * y**2 + 165 * y + 32

    # --- Resultant factorization ---
    Res = sp.factor(sp.resultant(Pi, P_LY, y))
    cubic = 16 * lam**3 - 9 * lam**2 + 1
    sextic = 256 * lam**6 - 480 * lam**5 + 201 * lam**4 + 750 * lam**3 - 921 * lam**2 - 78 * lam + 704
    expected = sp.factor(cubic**2 * sextic)
    resultant_ok = bool(sp.factor(Res - expected) == 0)
    resultant_degree = int(sp.Poly(Res, lam, domain=sp.ZZ).degree())

    # --- Groebner elimination on the Lee–Yang locus ---
    G = sp.groebner([Pi, dPi, P_LY], [lam, y], order="lex", domain=sp.QQ)
    # Expect a basis containing a linear-in-lam eliminant and the cubic relation P_LY(y)=0.
    groebner_linear_ok = False
    groebner_linear_prim = ""
    for g in G.polys:
        Pg = sp.Poly(g, lam, y, domain=sp.QQ)
        if Pg.degree(lam) == 1:
            _content, prim = _clear_denominators_linear_in_lam(Pg, lam, y)
            # Normalize sign to match the paper statement with positive leading coefficient in lam.
            primP = sp.Poly(prim, lam, y, domain=sp.ZZ)
            if primP.LC() < 0:
                prim = -prim
            groebner_linear_prim = sp.sstr(sp.expand(prim))
            target = 279 * lam + 512 * y**2 + 518 * y + 5
            groebner_linear_ok = bool(sp.factor(sp.expand(prim - target)) == 0)
            break

    # The cubic factor should reduce to zero modulo the ideal (Pi, dPi, P_LY).
    rem = G.reduce(cubic)[1]
    cubic_reduces_ok = bool(sp.simplify(rem) == 0)

    # --- Closed coordinate formulas on the Lee–Yang cubic field K=Q(y)/(P_LY) ---
    lam_branch = -sp.Rational(1, 279) * (512 * y**2 + 518 * y + 5)
    Y_branch = sp.simplify(y - lam_branch**2 + sp.Rational(1, 2))
    Y_target = sp.Rational(1, 558) * (512 * y**2 + 1262 * y + 377)
    branch_Y_formula_ok = _is_zero_mod_univariate(Y_branch - Y_target, y=y, modulus=P_LY)

    branch_ramification_ok = _is_zero_mod_univariate(
        4 * lam_branch * Y_branch + 3 * lam_branch**2 - 1, y=y, modulus=P_LY
    )
    branch_curve_eq_ok = _is_zero_mod_univariate(
        Y_branch**2 - (lam_branch**3 - lam_branch + sp.Rational(1, 4)), y=y, modulus=P_LY
    )

    s = sp.Rational(1, 93) * (-512 * y**2 + 226 * y + 367)
    hidden_square_ok = _is_zero_mod_univariate(s**2 - (64 * y**2 + 64 * y + 25), y=y, modulus=P_LY)

    payload = Payload(
        resultant_ok=resultant_ok,
        resultant_degree=resultant_degree,
        groebner_linear_ok=groebner_linear_ok,
        groebner_linear_prim=groebner_linear_prim,
        cubic_reduces_ok=cubic_reduces_ok,
        branch_Y_formula_ok=branch_Y_formula_ok,
        branch_ramification_ok=branch_ramification_ok,
        branch_curve_eq_ok=branch_curve_eq_ok,
        hidden_square_ok=hidden_square_ok,
    )

    if not args.no_output:
        out_json = export_dir() / "fold_zm_elliptic_leyang_resy_spectral_decomposition_audit.json"
        _write_json(out_json, asdict(payload))

        tex_lines = [
            "% Auto-generated by scripts/exp_fold_zm_elliptic_leyang_resy_spectral_decomposition_audit.py",
            "\\[",
            "\\mathrm{Res}_{y}\\bigl(\\Pi(\\lambda,y),P_{\\mathrm{LY}}(y)\\bigr)",
            "=(16\\lambda^{3}-9\\lambda^{2}+1)^{2}"
            "\\bigl(256\\lambda^{6}-480\\lambda^{5}+201\\lambda^{4}+750\\lambda^{3}-921\\lambda^{2}-78\\lambda+704\\bigr).",
            "\\]",
            "\\[",
            "279\\lambda+512y^{2}+518y+5=0\\quad(\\mathrm{mod}\\ P_{\\mathrm{LY}}(y)).",
            "\\]",
            "\\[",
            "Y=\\frac{512y^{2}+1262y+377}{558}\\quad(\\mathrm{mod}\\ P_{\\mathrm{LY}}(y)).",
            "\\]",
            "\\[",
            "\\left(\\frac{-512y^{2}+226y+367}{93}\\right)^{2}=64y^{2}+64y+25\\quad(\\mathrm{mod}\\ P_{\\mathrm{LY}}(y)).",
            "\\]",
            "",
        ]
        out_tex = generated_dir() / "eq_fold_zm_elliptic_leyang_resy_spectral_decomposition_audit.tex"
        _write_text(out_tex, "\n".join(tex_lines))

        print(f"[fold-zm-elliptic-leyang-resy] wrote {out_json}", flush=True)
        print(f"[fold-zm-elliptic-leyang-resy] wrote {out_tex}", flush=True)

    dt = time.time() - t0
    print(
        "[fold-zm-elliptic-leyang-resy] checks:"
        f" res={resultant_ok} deg={resultant_degree} lin={groebner_linear_ok} cubic_red={cubic_reduces_ok}"
        f" Y={branch_Y_formula_ok} ram={branch_ramification_ok} curve={branch_curve_eq_ok} sq={hidden_square_ok}"
        f" seconds={dt:.3f}",
        flush=True,
    )
    print("[fold-zm-elliptic-leyang-resy] done", flush=True)


if __name__ == "__main__":
    main()

