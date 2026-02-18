#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit the ramification geometry of the y-projection on the elliptic normalization
of the Fold fiber-weight spectral curve Pi(lambda,y)=0.

This script is English-only by repository convention.

We verify (symbolically, with SymPy):
  - On E: Y^2 = X^3 - X + 1/4, for y = X^2 + Y - 1/2 and omega = dX/(2Y),
      dy = (4 X Y + 3 X^2 - 1) * omega.
  - Abel–Jacobi algebraic ODE: with du=omega and p=dy/du, eliminating X yields
      p^4 + (8y-3)p^3 + (2y^2-34y-4)p^2 - y(y-1)P_LY(y) = 0.
  - Finite ramification points satisfy 4XY + 3X^2 - 1 = 0; eliminating Y yields
      (X-1)(X+1)(16X^3 - 9X^2 + 1) = 0.
  - The nontrivial ramification images satisfy the Lee–Yang cubic
      P_LY(y) = 256 y^3 + 411 y^2 + 165 y + 32
    via a pure elimination certificate (resultant), with the exact constant:
      Res_X(16X^3-9X^2+1, 4Xy-(4X^3-3X^2-2X+1)) = -64 * P_LY(y).
  - Norm / different bridge: for F(X,y)=X^4-X^3-(2y+1)X^2+X+y(y+1) and
      delta = 4Xy - (4X^3 - 3X^2 - 2X + 1) = -dF/dX,
    we have Res_X(F, delta) = -y(y-1)P_LY(y).
  - 2-division norm square compression:
      Res_X(F, 4X^3-4X+1) = (16y^3 - 8y^2 - 4y + 1)^2,
      Res_X(F, 2y-2X^2+1) = -(16y^3 - 8y^2 - 4y + 1).
  - Cubic-field generator mapping: if alpha solves 16X^3-9X^2+1=0, then
      beta=(4alpha^3-3alpha^2-2alpha+1)/(4alpha) solves P_LY(beta)=0,
    and Disc(16X^3-9X^2+1)=-2^2*3^3*37.
  - Puiseux expansions at y=0,1 (checked to O(t^4)), and the general formula
      c0^2 = -2 F_y / F_xx = (2/3)*(3alpha^2-1)/(alpha^2-1)
    at the Lee–Yang branch points.
  - The next Puiseux jet coefficient on the Lee–Yang branch points:
      beta = -F_xy/F_xx + (F_xxx*F_y)/(3 F_xx^2),
    reduced to a closed rational function of the critical eigenvalue.
  - Riemann–Hurwitz genus numbers for the S4 splitting cover and its A4/V4 quotients.

Outputs:
  - artifacts/export/fold_zm_elliptic_leyang_cover_geometry_audit.json
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Tuple

import sympy as sp

from common_paths import export_dir


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _is_constant_in(expr: sp.Expr, sym: sp.Symbol) -> bool:
    expr = sp.together(sp.simplify(expr))
    num, den = expr.as_numer_denom()
    try:
        deg_num = sp.Poly(num, sym, domain=sp.QQ).degree()
        deg_den = sp.Poly(den, sym, domain=sp.QQ).degree()
    except Exception:
        return False
    return deg_num == 0 and deg_den == 0


def _series_order_at_least(expr: sp.Expr, t: sp.Symbol, order: int) -> bool:
    """Return True iff expr = O(t^order) at t=0."""
    s = sp.series(expr, t, 0, order).removeO()
    return bool(sp.simplify(s) == 0)


def _reduce_mod(poly_expr: sp.Expr, var: sp.Symbol, modulus: sp.Expr) -> sp.Expr:
    """Polynomial remainder of poly_expr modulo modulus in QQ[var]."""
    P = sp.Poly(sp.expand(poly_expr), var, domain=sp.QQ)
    M = sp.Poly(sp.expand(modulus), var, domain=sp.QQ)
    return sp.rem(P, M).as_expr()


@dataclass(frozen=True)
class Payload:
    dy_identity_ok: bool
    abel_jacobi_ode_ok: bool
    abel_jacobi_ode_constant: str
    abel_jacobi_ode_exact_ok: bool
    critical_x_factor_ok: bool
    resy_F_Fx_factor_ok: bool
    resy_F_Fx_constant: str
    res_F_cubicx_factor_ok: bool
    res_F_cubicx_constant: str
    leyang_resultant_ok: bool
    leyang_resultant_constant: int
    leyang_resultant_exact_ok: bool
    norm_identity_ok: bool
    norm_2division_ok: bool
    norm_2Y_ok: bool
    disc_ctrl_cubic_y: int
    disc_ctrl_cubic_y_factorization: Dict[str, int]
    disc_conj_cubic_y: int
    disc_conj_cubic_y_factorization: Dict[str, int]
    mod37_ctrl_cubic_y: str
    mod37_leyang_cubic_y: str
    mod37_conj_cubic_y: str
    y_of_minus_P: int
    disc_cubic_x: int
    disc_cubic_x_factorization: Dict[str, int]
    disc_leyang: int
    puiseux_y0_0_ok: bool
    puiseux_y0_1_ok: bool
    c0_sq_formula_ok: bool
    beta_formula_ok: bool
    genus_s4_splitting: int
    genus_sign_quadratic: int
    genus_v4_quotient: int


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit ramification geometry for the elliptic y-cover (Fold Z_m).")
    parser.add_argument("--no-output", action="store_true", help="Skip writing JSON output.")
    args = parser.parse_args()

    t0 = time.time()
    print("[fold-zm-elliptic-leyang-cover-geom] start", flush=True)

    X, Y, y, p, t = sp.symbols("X Y y p t")

    # Elliptic curve E and weight function y(X,Y)
    E = Y**2 - (X**3 - X + sp.Rational(1, 4))
    y_map = X**2 + Y - sp.Rational(1, 2)

    # Differential identity: dy = (4XY + 3X^2 - 1) * (dX/(2Y))
    dy_dx = sp.simplify(2 * X + (3 * X**2 - 1) / (2 * Y))
    dy_identity_ok = bool(sp.simplify(dy_dx - (4 * X * Y + 3 * X**2 - 1) / (2 * Y)) == 0)

    # Critical locus in affine chart: 4XY + 3X^2 - 1 = 0
    crit = 4 * X * Y + 3 * X**2 - 1
    res_X = sp.factor(sp.resultant(E, crit, Y))
    target_X = (X - 1) * (X + 1) * (16 * X**3 - 9 * X**2 + 1)
    q = sp.together(res_X / target_X)
    critical_x_factor_ok = _is_constant_in(q, X)

    # Lee–Yang cubic from elimination: Res_X(16X^3-9X^2+1, 4Xy-(4X^3-3X^2-2X+1)) ∝ P_LY(y)
    cubicX = 16 * X**3 - 9 * X**2 + 1
    rel = 4 * X * y - (4 * X**3 - 3 * X**2 - 2 * X + 1)
    res_y = sp.factor(sp.resultant(cubicX, rel, X))
    P_LY = 256 * y**3 + 411 * y**2 + 165 * y + 32
    q2 = sp.together(res_y / P_LY)
    leyang_resultant_ok = _is_constant_in(q2, y)
    leyang_resultant_constant = int(sp.factor(q2))
    leyang_resultant_exact_ok = bool(sp.factor(res_y - leyang_resultant_constant * P_LY) == 0)

    # Norm identity via resultant of F and delta=-dF/dX
    F = X**4 - X**3 - (2 * y + 1) * X**2 + X + y * (y + 1)
    delta = 4 * X * y - (4 * X**3 - 3 * X**2 - 2 * X + 1)
    if sp.simplify(delta + sp.diff(F, X)) != 0:
        raise RuntimeError("Expected delta = -dF/dX identity failed (internal).")
    Res_norm = sp.factor(sp.resultant(F, delta, X))
    norm_expected = -y * (y - 1) * P_LY
    norm_identity_ok = bool(sp.factor(Res_norm - norm_expected) == 0)

    # 2-division norm square compression.
    D2 = 4 * X**3 - 4 * X + 1
    Res_D2 = sp.factor(sp.resultant(F, D2, X))
    ctrl = 16 * y**3 - 8 * y**2 - 4 * y + 1
    norm_2division_ok = bool(sp.factor(Res_D2 - ctrl**2) == 0)

    twoY = 2 * y - 2 * X**2 + 1  # since Y = y - X^2 + 1/2
    Res_twoY = sp.factor(sp.resultant(F, twoY, X))
    norm_2Y_ok = bool(sp.factor(Res_twoY + ctrl) == 0)

    # Abel–Jacobi ODE closure in (y,p): with du = dX/(2Y) and p = dy/du.
    # Since dy = (4XY+3X^2-1) * (dX/(2Y)), we have p = 4XY + 3X^2 - 1.
    # Eliminating Y via Y = y - X^2 + 1/2 yields a cubic constraint in X:
    #   4X^3 - 3X^2 - (4y+2)X + (1+p) = 0.
    cubic_p = 4 * X**3 - 3 * X**2 - (4 * y + 2) * X + (1 + p)
    Res_ode = sp.factor(sp.resultant(F, cubic_p, X))
    ode_expected = (
        p**4
        + (8 * y - 3) * p**3
        + (2 * y**2 - 34 * y - 4) * p**2
        - y * (y - 1) * P_LY
    )
    q_ode = sp.together(Res_ode / ode_expected)
    abel_jacobi_ode_ok = _is_constant_in(q_ode, y) and _is_constant_in(q_ode, p)
    abel_jacobi_ode_constant = str(sp.factor(q_ode)) if abel_jacobi_ode_ok else "nan"
    abel_jacobi_ode_exact_ok = (
        bool(sp.factor(Res_ode - sp.factor(q_ode) * ode_expected) == 0) if abel_jacobi_ode_ok else False
    )

    # Discriminants
    disc_cubic_x = int(sp.discriminant(cubicX, X))
    disc_cubic_x_fac = sp.factorint(disc_cubic_x)
    disc_leyang = int(sp.discriminant(P_LY, y))

    # --- Additional eliminations used in the manuscript text ---
    # 1) Ramification in the (X,y)-plane quartic model: Res_y(F, dF/dX).
    Fx = sp.diff(F, X)
    resy_F_Fx = sp.factor(sp.resultant(F, Fx, y))
    target_resy = -(X - 1) * (X + 1) * cubicX
    q_resy = sp.together(resy_F_Fx / target_resy)
    resy_F_Fx_factor_ok = _is_constant_in(q_resy, X)
    resy_F_Fx_constant = str(sp.factor(q_resy)) if resy_F_Fx_factor_ok else "nan"

    # 2) Conjugate cubic factor from eliminating X between F and cubicX.
    res_F_cubicx = sp.factor(sp.resultant(F, cubicX, X))
    Q_LY = 256 * y**3 + 195 * y**2 + 93 * y - 48
    target_res_F = P_LY * Q_LY
    q_res_F = sp.together(res_F_cubicx / target_res_F)
    res_F_cubicx_factor_ok = _is_constant_in(q_res_F, y)
    res_F_cubicx_constant = str(sp.factor(q_res_F)) if res_F_cubicx_factor_ok else "nan"

    # Discriminants and mod-37 factorizations for the three cubic controls.
    ctrl_cubic_y = 16 * y**3 - 8 * y**2 - 4 * y + 1
    disc_ctrl_cubic_y = int(sp.discriminant(ctrl_cubic_y, y))
    disc_ctrl_cubic_y_fac = sp.factorint(disc_ctrl_cubic_y)

    disc_conj_cubic_y = int(sp.discriminant(Q_LY, y))
    disc_conj_cubic_y_fac = sp.factorint(disc_conj_cubic_y)

    def _factor_mod(expr: sp.Expr, modulus: int) -> str:
        Pm = sp.Poly(sp.expand(expr), y, modulus=modulus)
        return str(sp.factor(Pm.as_expr(), modulus=modulus))

    mod37_ctrl = _factor_mod(ctrl_cubic_y, 37)
    mod37_leyang = _factor_mod(P_LY, 37)
    mod37_conj = _factor_mod(Q_LY, 37)

    # Special rational point label: y(-P)=6 for P=(2,-5/2).
    y_of_minus_P = int(sp.together(y_map.subs({X: sp.Integer(2), Y: sp.Rational(5, 2)})))

    # Puiseux checks near y0=0 and y0=1 (to O(t^4))
    X_series_0_plus = (
        1
        + (1 / sp.sqrt(2)) * t
        + sp.Rational(5, 8) * t**2
        - sp.Rational(43, 64) * (1 / sp.sqrt(2)) * t**3
    )
    X_series_0_minus = (
        1
        - (1 / sp.sqrt(2)) * t
        + sp.Rational(5, 8) * t**2
        + sp.Rational(43, 64) * (1 / sp.sqrt(2)) * t**3
    )
    expr0p = sp.expand(F.subs({X: X_series_0_plus, y: t**2}))
    expr0m = sp.expand(F.subs({X: X_series_0_minus, y: t**2}))
    puiseux_y0_0_ok = _series_order_at_least(expr0p, t, 4) and _series_order_at_least(expr0m, t, 4)

    X_series_1_plus = (
        -1
        + (1 / sp.sqrt(6)) * t
        + sp.Rational(29, 72) * t**2
        + sp.Rational(245, 1728) * (1 / sp.sqrt(6)) * t**3
    )
    X_series_1_minus = (
        -1
        - (1 / sp.sqrt(6)) * t
        + sp.Rational(29, 72) * t**2
        - sp.Rational(245, 1728) * (1 / sp.sqrt(6)) * t**3
    )
    expr1p = sp.expand(F.subs({X: X_series_1_plus, y: 1 - t**2}))
    expr1m = sp.expand(F.subs({X: X_series_1_minus, y: 1 - t**2}))
    puiseux_y0_1_ok = _series_order_at_least(expr1p, t, 4) and _series_order_at_least(expr1m, t, 4)

    # General coefficient formula at Lee–Yang branch points.
    a = sp.Symbol("a")
    ycrit_a = (4 * a**3 - 3 * a**2 - 2 * a + 1) / (4 * a)
    Fy = sp.diff(F, y).subs({X: a, y: ycrit_a})
    Fxx = sp.diff(F, X, 2).subs({X: a, y: ycrit_a})
    c0_sq = sp.simplify(-2 * Fy / Fxx)
    expected_c0_sq = sp.Rational(2, 3) * (3 * a**2 - 1) / (a**2 - 1)
    diff_c = sp.together(c0_sq - expected_c0_sq)
    num_c, den_c = diff_c.as_numer_denom()
    # Reduce numerator modulo the cubic certificate (valid on the LY branch points).
    num_red = _reduce_mod(num_c, a, 16 * a**3 - 9 * a**2 + 1)
    c0_sq_formula_ok = bool(sp.simplify(num_red) == 0)

    # Next Puiseux jet coefficient (linear term in y-y0): beta = -F_xy/F_xx + (F_xxx*F_y)/(3 F_xx^2).
    Fxy = sp.diff(F, X, y).subs({X: a, y: ycrit_a})
    Fxxx = sp.diff(F, X, 3).subs({X: a, y: ycrit_a})
    beta_coeff = sp.simplify(-Fxy / Fxx + sp.Rational(1, 3) * (Fxxx * Fy) / (Fxx**2))
    expected_beta = 8 * (283 * a**2 + 80 * a - 3) / (3879 * a**2 + 144 * a - 2223)
    diff_b = sp.together(beta_coeff - expected_beta)
    num_b, den_b = diff_b.as_numer_denom()
    num_b_red = _reduce_mod(num_b, a, 16 * a**3 - 9 * a**2 + 1)
    beta_formula_ok = bool(sp.simplify(num_b_red) == 0)

    # Genus computations by Riemann–Hurwitz (pure integers).
    # S4-splitting cover: degree 24, branch e = [4,2,2,2,2,2].
    n_s4 = 24
    e_list = [4, 2, 2, 2, 2, 2]
    ram = sum(n_s4 * (1 - sp.Rational(1, e)) for e in e_list)
    genus_s4 = int(((-2) * n_s4 + ram + 2) / 2)

    # Sign quadratic quotient: degree 2, 6 branch points (odd degree 5 polynomial => infinity branches).
    n2 = 2
    e_list2 = [2, 2, 2, 2, 2, 2]
    ram2 = sum(n2 * (1 - sp.Rational(1, e)) for e in e_list2)
    genus2 = int(((-2) * n2 + ram2 + 2) / 2)

    # V4 quotient (S3-cover): degree 6, 6 branch points all of index 2.
    n6 = 6
    e_list6 = [2, 2, 2, 2, 2, 2]
    ram6 = sum(n6 * (1 - sp.Rational(1, e)) for e in e_list6)
    genus6 = int(((-2) * n6 + ram6 + 2) / 2)

    payload = Payload(
        dy_identity_ok=dy_identity_ok,
        abel_jacobi_ode_ok=abel_jacobi_ode_ok,
        abel_jacobi_ode_constant=abel_jacobi_ode_constant,
        abel_jacobi_ode_exact_ok=abel_jacobi_ode_exact_ok,
        critical_x_factor_ok=critical_x_factor_ok,
        resy_F_Fx_factor_ok=resy_F_Fx_factor_ok,
        resy_F_Fx_constant=resy_F_Fx_constant,
        res_F_cubicx_factor_ok=res_F_cubicx_factor_ok,
        res_F_cubicx_constant=res_F_cubicx_constant,
        leyang_resultant_ok=leyang_resultant_ok,
        leyang_resultant_constant=leyang_resultant_constant,
        leyang_resultant_exact_ok=leyang_resultant_exact_ok,
        norm_identity_ok=norm_identity_ok,
        norm_2division_ok=norm_2division_ok,
        norm_2Y_ok=norm_2Y_ok,
        disc_ctrl_cubic_y=disc_ctrl_cubic_y,
        disc_ctrl_cubic_y_factorization={str(int(p)): int(e) for p, e in disc_ctrl_cubic_y_fac.items()},
        disc_conj_cubic_y=disc_conj_cubic_y,
        disc_conj_cubic_y_factorization={str(int(p)): int(e) for p, e in disc_conj_cubic_y_fac.items()},
        mod37_ctrl_cubic_y=mod37_ctrl,
        mod37_leyang_cubic_y=mod37_leyang,
        mod37_conj_cubic_y=mod37_conj,
        y_of_minus_P=y_of_minus_P,
        disc_cubic_x=int(disc_cubic_x),
        disc_cubic_x_factorization={str(int(p)): int(e) for p, e in disc_cubic_x_fac.items()},
        disc_leyang=int(disc_leyang),
        puiseux_y0_0_ok=puiseux_y0_0_ok,
        puiseux_y0_1_ok=puiseux_y0_1_ok,
        c0_sq_formula_ok=c0_sq_formula_ok,
        beta_formula_ok=beta_formula_ok,
        genus_s4_splitting=genus_s4,
        genus_sign_quadratic=genus2,
        genus_v4_quotient=genus6,
    )

    if not args.no_output:
        out = export_dir() / "fold_zm_elliptic_leyang_cover_geometry_audit.json"
        _write_json(out, asdict(payload))
        print(f"[fold-zm-elliptic-leyang-cover-geom] wrote {out}", flush=True)

    dt = time.time() - t0
    print(
        "[fold-zm-elliptic-leyang-cover-geom] checks:"
        f" dy={dy_identity_ok} ajode={abel_jacobi_ode_ok} ajode_c={abel_jacobi_ode_constant}"
        f" ajode_exact={abel_jacobi_ode_exact_ok} critX={critical_x_factor_ok} leyang_res={leyang_resultant_ok}"
        f" leyang_c={leyang_resultant_constant} leyang_exact={leyang_resultant_exact_ok}"
        f" norm={norm_identity_ok} norm2div={norm_2division_ok} norm2Y={norm_2Y_ok}"
        f" resy={resy_F_Fx_factor_ok} resFg={res_F_cubicx_factor_ok} y(-P)={y_of_minus_P}"
        f" puiseux0={puiseux_y0_0_ok} puiseux1={puiseux_y0_1_ok}"
        f" c0sq={c0_sq_formula_ok} beta={beta_formula_ok} genusS4={genus_s4} genus2={genus2} genus6={genus6} seconds={dt:.3f}",
        flush=True,
    )
    print("[fold-zm-elliptic-leyang-cover-geom] done", flush=True)


if __name__ == "__main__":
    main()

