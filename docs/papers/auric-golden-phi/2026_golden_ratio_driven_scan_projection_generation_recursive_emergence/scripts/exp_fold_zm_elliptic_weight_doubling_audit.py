#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit the weight-doubling correspondence on E in (y0,y1)-coordinates.

This script is English-only by repository convention.

We work with the elliptic curve
  E: Y^2 = X^3 - X + 1/4
and the weight coordinate
  y := X^2 + Y - 1/2.

For P in E, write y0 := y(P) and y1 := y([2]P). Then y1 is not a single-valued
function of y0 (since y : E -> P^1 is degree 4). Instead, the (y0,y1)-pairs lie on
an explicit plane curve H(y0,y1)=0, quartic in y1.

We verify:
  - The explicit bivariate elimination polynomial H(y0,y1) with integer coefficients.
  - The discriminant factorization (as a polynomial in y1):
      Disc_{y1}(H(y, y1)) = - y (y-1) P_LY(y) * Q12(y)^2 * Q26(y)^2,
    hence the square-class equals -y(y-1)P_LY(y).
  - The birational inverse Gamma -> E on an open set via X = beta/alpha and
    Y = y0 - X^2 + 1/2 (checked on the generic point coming from E).
  - The norm/resultant certificate for the Lee–Yang kernel:
      Res_X(Pi(X,y), 4X(y - X^2 + 1/2) + 3X^2 - 1) = - y (y-1) P_LY(y),
    where Pi(X,y)=X^4 - X^3 - (2y+1)X^2 + X + y(y+1).

Outputs (default):
  - artifacts/export/fold_zm_elliptic_weight_doubling_audit.json
  - sections/generated/eq_fold_zm_elliptic_weight_doubling_H.tex
  - sections/generated/eq_fold_zm_elliptic_weight_doubling_discriminant.tex
  - sections/generated/eq_fold_zm_elliptic_weight_doubling_inverse.tex
  - sections/generated/eq_fold_zm_elliptic_weight_doubling_norm.tex
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import sympy as sp

from common_paths import export_dir, generated_dir


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _curve_remainder_in_Y(num: sp.Expr, X: sp.Symbol, Y: sp.Symbol) -> sp.Expr:
    """Reduce a polynomial numerator modulo the curve relation in Y.

    Curve: Y^2 = X^3 - X + 1/4  <=>  Y^2 - (X^3 - X + 1/4) = 0.
    Returns the remainder as an expression of degree < 2 in Y.
    """
    f = X**3 - X + sp.Rational(1, 4)
    curve_poly = sp.Poly(Y**2 - f, Y)
    rem = sp.Poly(sp.expand(num), Y).rem(curve_poly).as_expr()
    return sp.factor(rem)


def _is_zero_in_QE(expr: sp.Expr, X: sp.Symbol, Y: sp.Symbol) -> bool:
    """Check expr == 0 in the function field Q(E)=Q(X,Y)/(Y^2 - (X^3-X+1/4)).

    Strategy: take numerator of together(expr), then reduce modulo the curve
    equation as a polynomial in Y; require both Y^0 and Y^1 coefficients to vanish.
    """
    num = sp.together(expr).as_numer_denom()[0]
    rem = _curve_remainder_in_Y(num, X, Y)
    remY = sp.Poly(rem, Y)
    c0 = sp.factor(remY.nth(0))
    c1 = sp.factor(remY.nth(1))
    return c0 == 0 and c1 == 0


def _latex_poly_in(var: sp.Symbol, expr: sp.Expr) -> str:
    P = sp.Poly(sp.expand(expr), var, domain=sp.ZZ)
    return sp.latex(P.as_expr())


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit weight-doubling correspondence polynomial H(y0,y1) on E")
    parser.add_argument("--no-output", action="store_true", help="Skip writing outputs")
    args = parser.parse_args()

    # Function field symbols on E
    X, Y = sp.symbols("X Y")

    # Weight-coordinate symbols
    y0, y1 = sp.symbols("y_0 y_1")

    # Lee–Yang cubic
    def P_LY(t: sp.Expr) -> sp.Expr:
        return 256 * t**3 + 411 * t**2 + 165 * t + 32

    # --- Conclusion 176: explicit H(y0,y1) ---
    A4 = (
        65536 * y0**12
        - 131072 * y0**11
        + 32768 * y0**10
        + 81920 * y0**9
        - 45056 * y0**8
        - 16384 * y0**7
        + 13824 * y0**6
        + 512 * y0**5
        - 1664 * y0**4
        + 192 * y0**3
        + 64 * y0**2
        - 16 * y0
        + 1
    )
    A3 = (
        -16384 * y0**13
        + 61440 * y0**12
        - 454656 * y0**11
        + 82944 * y0**10
        + 1247744 * y0**9
        - 57600 * y0**8
        - 906688 * y0**7
        - 167648 * y0**6
        + 174368 * y0**5
        + 23020 * y0**4
        - 12596 * y0**3
        - 1198 * y0**2
        + 346 * y0
        - 63
    )
    A2 = (
        1536 * y0**14
        - 9216 * y0**13
        + 81792 * y0**12
        - 118976 * y0**11
        + 294336 * y0**10
        + 641648 * y0**9
        - 232314 * y0**8
        - 391280 * y0**7
        - 430462 * y0**6
        - 198332 * y0**5
        + 280857 * y0**4
        + 263078 * y0**3
        + 108044 * y0**2
        + 14594 * y0
        + 698
    )
    A1 = (
        -64 * y0**15
        + 608 * y0**14
        - 5376 * y0**13
        + 15052 * y0**12
        - 37980 * y0**11
        + 75342 * y0**10
        + 75922 * y0**9
        - 208389 * y0**8
        - 257076 * y0**7
        - 198536 * y0**6
        + 143116 * y0**5
        + 199086 * y0**4
        - 37204 * y0**3
        - 57694 * y0**2
        - 26364 * y0
        - 2436
    )
    A0 = (
        y0**16
        - 16 * y0**15
        + 158 * y0**14
        - 872 * y0**13
        + 2243 * y0**12
        - 3190 * y0**11
        + 7024 * y0**10
        - 4728 * y0**9
        - 23757 * y0**8
        - 1652 * y0**7
        + 35994 * y0**6
        + 65440 * y0**5
        + 497 * y0**4
        - 35454 * y0**3
        - 2792 * y0**2
        + 1640 * y0
        + 1800
    )
    H = sp.expand(A4 * y1**4 + A3 * y1**3 + A2 * y1**2 + A1 * y1 + A0)

    H_deg_y1 = sp.Poly(H, y1).degree()
    H_deg_y0 = sp.Poly(H, y0).degree()

    # --- Substitute y0=y(P), y1=y([2]P) and check H=0 in Q(E) ---
    # Curve: Y^2 = X^3 - X + 1/4, a=-1, b=1/4.
    denom_2div = 4 * X**3 - 4 * X + 1
    Phi = (X**4 + 2 * X**2 - 2 * X + 1) / denom_2div
    m = (3 * X**2 - 1) / (2 * Y)
    Y2 = sp.together(m * (X - Phi) - Y)
    y0_expr = X**2 + Y - sp.Rational(1, 2)
    y1_expr = sp.together(Phi**2 + Y2 - sp.Rational(1, 2))

    H_on_E_ok = _is_zero_in_QE(H.subs({y0: y0_expr, y1: y1_expr}), X, Y)

    # --- Conclusion 177: discriminant factorization ---
    Q12 = (
        64 * y0**12
        - 128 * y0**11
        - 2576 * y0**10
        - 2160 * y0**9
        + 10892 * y0**8
        + 32064 * y0**7
        + 28873 * y0**6
        - 11139 * y0**5
        - 31715 * y0**4
        - 8333 * y0**3
        - 958 * y0**2
        - 100 * y0
        + 8
    )
    Q26 = (
        262144 * y0**26
        - 10747904 * y0**25
        + 191954944 * y0**24
        - 1897332736 * y0**23
        + 13439238144 * y0**22
        - 47170043904 * y0**21
        + 30127935488 * y0**20
        + 55661785088 * y0**19
        - 112465192960 * y0**18
        + 135823686656 * y0**17
        + 205179341056 * y0**16
        - 455994979584 * y0**15
        - 230261903040 * y0**14
        + 622458964864 * y0**13
        + 231233432960 * y0**12
        - 451887225664 * y0**11
        - 230891455552 * y0**10
        + 102570870816 * y0**9
        + 95472617744 * y0**8
        + 15921249600 * y0**7
        - 7132590928 * y0**6
        - 3074856528 * y0**5
        - 21077156 * y0**4
        + 227572860 * y0**3
        + 2463184 * y0**2
        - 12256842 * y0
        - 4594975
    )
    disc_H = sp.Poly(H, y1).discriminant()
    disc_expected = -y0 * (y0 - 1) * P_LY(y0) * Q12**2 * Q26**2
    disc_ok = sp.Poly(sp.expand(disc_H - disc_expected), y0, domain=sp.ZZ).is_zero

    # --- Conclusion 178: birational inverse (checked on the generic E-point) ---
    alpha = (
        2 * y0**10
        - 128 * y0**9 * y1
        - 18 * y0**9
        + 2304 * y0**8 * y1**2
        + 344 * y0**8 * y1
        + 269 * y0**8
        - 16384 * y0**7 * y1**3
        - 512 * y0**7 * y1**2
        - 10528 * y0**7 * y1
        - 1644 * y0**7
        + 43008 * y0**6 * y1**3
        + 114944 * y0**6 * y1**2
        - 5880 * y0**6 * y1
        + 2664 * y0**6
        - 43008 * y0**5 * y1**3
        - 155840 * y0**5 * y1**2
        - 114364 * y0**5 * y1
        - 3744 * y0**5
        + 15104 * y0**4 * y1**3
        - 234576 * y0**4 * y1**2
        - 19146 * y0**4 * y1
        + 15013 * y0**4
        + 190016 * y0**3 * y1**2
        + 158988 * y0**3 * y1
        + 20344 * y0**3
        - 256 * y0**2 * y1**3
        + 62942 * y0**2 * y1**2
        - 49226 * y0**2 * y1
        - 29243 * y0**2
        - 192 * y0 * y1**3
        + 11686 * y0 * y1**2
        - 9606 * y0 * y1
        + 4992 * y0
        - 8 * y1**3
        + 409 * y1**2
        - 910 * y1
        - 716
    )
    beta = (
        2 * y0**11
        - 112 * y0**10 * y1
        - 24 * y0**10
        + 2048 * y0**9 * y1**2
        + 560 * y0**9 * y1
        + 172 * y0**9
        - 12288 * y0**8 * y1**3
        - 5376 * y0**8 * y1**2
        - 4776 * y0**8 * y1
        - 604 * y0**8
        + 16384 * y0**7 * y1**3
        + 55040 * y0**7 * y1**2
        - 2564 * y0**7 * y1
        + 256 * y0**7
        + 10240 * y0**6 * y1**3
        + 54624 * y0**6 * y1**2
        - 37832 * y0**6 * y1
        + 435 * y0**6
        - 19968 * y0**5 * y1**3
        - 185312 * y0**5 * y1**2
        - 95724 * y0**5 * y1
        + 65 * y0**5
        + 6400 * y0**4 * y1**3
        - 92560 * y0**4 * y1**2
        + 39344 * y0**4 * y1
        + 18495 * y0**4
        + 1280 * y0**3 * y1**3
        + 126434 * y0**3 * y1**2
        + 69014 * y0**3 * y1
        + 2166 * y0**3
        - 368 * y0**2 * y1**3
        + 55096 * y0**2 * y1**2
        - 37869 * y0**2 * y1
        - 12835 * y0**2
        - 144 * y0 * y1**3
        + 9048 * y0 * y1**2
        - 15369 * y0 * y1
        + 3722 * y0
        - 8 * y1**3
        + 436 * y1**2
        - 1344 * y1
        + 916
    )

    alpha_on_E = alpha.subs({y0: y0_expr, y1: y1_expr})
    beta_on_E = beta.subs({y0: y0_expr, y1: y1_expr})
    inverse_X_ok = _is_zero_in_QE(beta_on_E - X * alpha_on_E, X, Y)

    # --- Conclusion 180: norm/resultant certificate ---
    x, y = sp.symbols("x y")
    Pi_xy = x**4 - x**3 - (2 * y + 1) * x**2 + x + y * (y + 1)
    h_elim = 4 * x * (y - x**2 + sp.Rational(1, 2)) + 3 * x**2 - 1
    res = sp.factor(sp.resultant(Pi_xy, h_elim, x))
    res_expected = -y * (y - 1) * P_LY(y)
    res_ok = sp.factor(res - res_expected) == 0

    payload: Dict[str, object] = {
        "H_deg_y1": int(H_deg_y1),
        "H_deg_y0": int(H_deg_y0),
        "H_on_E_ok": bool(H_on_E_ok),
        "disc_ok": bool(disc_ok),
        "inverse_X_ok": bool(inverse_X_ok),
        "res_ok": bool(res_ok),
    }

    if not args.no_output:
        _write_json(export_dir() / "fold_zm_elliptic_weight_doubling_audit.json", payload)

        # TeX: H and A_i coefficients
        tex_H: List[str] = []
        tex_H.append("% Auto-generated by scripts/exp_fold_zm_elliptic_weight_doubling_audit.py")
        tex_H.append("\\[")
        tex_H.append(
            "\\mathcal H(y_{0},y_{1})=A_{4}(y_{0})y_{1}^{4}+A_{3}(y_{0})y_{1}^{3}+A_{2}(y_{0})y_{1}^{2}+A_{1}(y_{0})y_{1}+A_{0}(y_{0})."
        )
        tex_H.append("\\]")
        tex_H.append("\\[")
        tex_H.append("\\begin{aligned}")
        tex_H.append(f"A_4(y_0)&={_latex_poly_in(y0, A4)}\\\\")
        tex_H.append(f"A_3(y_0)&={_latex_poly_in(y0, A3)}\\\\")
        tex_H.append(f"A_2(y_0)&={_latex_poly_in(y0, A2)}\\\\")
        tex_H.append(f"A_1(y_0)&={_latex_poly_in(y0, A1)}\\\\")
        tex_H.append(f"A_0(y_0)&={_latex_poly_in(y0, A0)}")
        tex_H.append("\\end{aligned}")
        tex_H.append("\\]")
        _write_text(generated_dir() / "eq_fold_zm_elliptic_weight_doubling_H.tex", "\n".join(tex_H) + "\n")

        # TeX: discriminant factorization
        tex_D: List[str] = []
        tex_D.append("% Auto-generated by scripts/exp_fold_zm_elliptic_weight_doubling_audit.py")
        tex_D.append("\\[")
        tex_D.append("P_{\\mathrm{LY}}(y)=256y^{3}+411y^{2}+165y+32.")
        tex_D.append("\\]")
        tex_D.append("\\[")
        tex_D.append(f"Q_{{12}}(y)={sp.latex(sp.Poly(Q12.subs({y0: y}), y, domain=sp.ZZ).as_expr())}.")
        tex_D.append("\\]")
        tex_D.append("\\[")
        tex_D.append(f"Q_{{26}}(y)={sp.latex(sp.Poly(Q26.subs({y0: y}), y, domain=sp.ZZ).as_expr())}.")
        tex_D.append("\\]")
        tex_D.append("\\[")
        tex_D.append(
            "\\mathrm{Disc}_{y_{1}}\\bigl(\\mathcal H(y,y_{1})\\bigr)"
            "=-y(y-1)P_{\\mathrm{LY}}(y)\\,Q_{12}(y)^{2}Q_{26}(y)^{2}."
        )
        tex_D.append("\\]")
        _write_text(
            generated_dir() / "eq_fold_zm_elliptic_weight_doubling_discriminant.tex", "\n".join(tex_D) + "\n"
        )

        # TeX: birational inverse polynomials
        tex_inv: List[str] = []
        tex_inv.append("% Auto-generated by scripts/exp_fold_zm_elliptic_weight_doubling_audit.py")
        tex_inv.append("\\[")
        tex_inv.append(f"\\alpha(y_0,y_1)={sp.latex(sp.Poly(alpha, y0, y1, domain=sp.ZZ).as_expr())}.")
        tex_inv.append("\\]")
        tex_inv.append("\\[")
        tex_inv.append(f"\\beta(y_0,y_1)={sp.latex(sp.Poly(beta, y0, y1, domain=sp.ZZ).as_expr())}.")
        tex_inv.append("\\]")
        _write_text(generated_dir() / "eq_fold_zm_elliptic_weight_doubling_inverse.tex", "\n".join(tex_inv) + "\n")

        # TeX: norm/resultant certificate
        tex_norm: List[str] = []
        tex_norm.append("% Auto-generated by scripts/exp_fold_zm_elliptic_weight_doubling_audit.py")
        tex_norm.append("\\[")
        tex_norm.append(
            "\\Pi(\\lambda,y)=\\lambda^{4}-\\lambda^{3}-(2y+1)\\lambda^{2}+\\lambda+y(y+1),\\qquad "
            "h(\\lambda,y)=4\\lambda\\bigl(y-\\lambda^{2}+\\tfrac12\\bigr)+3\\lambda^{2}-1."
        )
        tex_norm.append("\\]")
        tex_norm.append("\\[")
        tex_norm.append(
            "\\mathrm{Res}_{\\lambda}\\bigl(\\Pi(\\lambda,y),h(\\lambda,y)\\bigr)=-y(y-1)P_{\\mathrm{LY}}(y)."
        )
        tex_norm.append("\\]")
        _write_text(generated_dir() / "eq_fold_zm_elliptic_weight_doubling_norm.tex", "\n".join(tex_norm) + "\n")


if __name__ == "__main__":
    main()

