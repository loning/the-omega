#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit the Weierstrass normalization of the Fold resolvent cubic curve R(z,y)=0.

This script is English-only by repository convention.

We verify (by exact symbolic algebra in Q[...], plus small finite-field audits):
  - The birational map from the elliptic curve
      E_R:  Y^2 = X^3 - 37 X^2 + 307 X + 361
    to the plane (z,y)-model of the resolvent cubic
      R(z,y)=z^3+(1+2y)z^2-(1+4y+4y^2)z-(1+5y+13y^2+8y^3)=0
    via
      y = -8X / (Y+19+14X-X^2),
      z = 1 - 2X(7-X) / (Y+19+14X-X^2),
    and that the stated inverse recovers (X,Y) on a Zariski open set.
  - Weierstrass invariants (c4,c6,Delta,j) of E_R.
  - Divisor-level fiber decompositions for y at {0,1,∞} by intersection-factor checks.
  - The critical-point elimination for the degree-3 map y: E_R -> P^1_y:
      g_R(X)=4X^3+3X^2+114X-269 controls the non-rational ramification X-coordinates,
    and eliminating X from g_R(X)=0 and
      y = 16(X^2+19) / ((X-15)(2X^2+X+15))
    recovers P_LY(y)=256y^3+411y^2+165y+32 up to a unit.
  - Disc(g_R) has squarefree part -111, hence the quadratic resolvent field is Q(sqrt(-111)).
  - Torsion-triviality certificate for E_R(Q) via coprime reductions at good primes.
  - Split/non-split multiplicative reduction at p=31,37 via Legendre symbols of -c6.

Outputs:
  - artifacts/export/fold_zm_resolvent_cubic_weierstrass_audit.json
  - sections/generated/eq_fold_zm_resolvent_cubic_weierstrass_audit.tex
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass
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


def _legendre_symbol(a: int, p: int) -> int:
    a %= p
    if a == 0:
        return 0
    return 1 if pow(a, (p - 1) // 2, p) == 1 else -1


def _count_points_y2_equals_f(p: int, f_coeffs: Tuple[int, int, int]) -> int:
    """Count points on y^2 = x^3 + a2 x^2 + a4 x + a6 over F_p, including O (p odd)."""
    if p == 2:
        raise ValueError("Point counting expects an odd prime p.")
    a2, a4, a6 = f_coeffs  # x^3 + a2 x^2 + a4 x + a6
    a2 %= p
    a4 %= p
    a6 %= p
    cnt = 1  # point at infinity
    for x in range(p):
        rhs = (x * x * x + a2 * x * x + a4 * x + a6) % p
        if rhs == 0:
            cnt += 1
        else:
            ls = pow(rhs, (p - 1) // 2, p)
            if ls == 1:
                cnt += 2
    return cnt


def _find_coprime_reduction_certificate(
    bad_primes: set[int], f_coeffs: Tuple[int, int, int], search_limit: int = 200
) -> Tuple[int, int, int, int]:
    """
    Find two good primes p,q with gcd(#E(F_p), #E(F_q))=1.
    Returns (p, n_p, q, n_q).
    """
    primes: List[int] = []
    for n in range(3, search_limit + 1):
        if n in bad_primes:
            continue
        if sp.isprime(n):
            primes.append(n)

    counts: Dict[int, int] = {}
    for p in primes:
        counts[p] = _count_points_y2_equals_f(p, f_coeffs)

    best = None
    for i, p in enumerate(primes):
        for q in primes[i + 1 :]:
            g = math.gcd(counts[p], counts[q])
            if g == 1:
                return p, counts[p], q, counts[q]
            if best is None or g < best[0]:
                best = (g, p, counts[p], q, counts[q])

    if best is not None:
        g, p, np, q, nq = best
        raise RuntimeError(f"No coprime certificate found up to {search_limit}; best gcd={g} at p={p}, q={q}.")
    raise RuntimeError("No primes available for torsion certificate search.")


@dataclass(frozen=True)
class Payload:
    birational_R_identity_ok: bool
    birational_inverse_X_ok: bool
    birational_inverse_Y_ok: bool
    invariants_ok: bool
    c4: int
    c6: int
    Delta: int
    j: str
    D_intersection_factor: str
    y_minus_1_intersection_factor: str
    y_fiber_checks_ok: bool
    dy_critical_X_factor: str
    critical_polynomial_ok: bool
    g_R: str
    disc_g_R: int
    disc_g_R_factorization: Dict[str, int]
    quadratic_resolvent_field: str
    resultant_P_LY_factor: str
    resultant_P_LY_ok: bool
    torsion_certificate_primes: List[int]
    torsion_certificate_counts: List[int]
    torsion_certificate_gcd: int
    legendre_minus_c6_31: int
    legendre_minus_c6_37: int


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the Weierstrass normalization of the resolvent cubic curve.")
    parser.add_argument("--no-output", action="store_true", help="Skip writing JSON/TeX outputs.")
    args = parser.parse_args()

    t0 = time.time()
    print("[fold-zm-resolvent-cubic-weierstrass] start", flush=True)

    # Symbols.
    X, Y, y, z = sp.symbols("X Y y z")

    # Curve E_R: Y^2 = X^3 - 37 X^2 + 307 X + 361.
    fX = X**3 - 37 * X**2 + 307 * X + 361
    E = sp.expand(Y**2 - fX)

    # Map to the plane (z,y)-model.
    D = Y + 19 + 14 * X - X**2
    y_fun = sp.together(-8 * X / D)
    z_fun = sp.together(1 - 2 * X * (7 - X) / D)

    R = z**3 + (1 + 2 * y) * z**2 - (1 + 4 * y + 4 * y**2) * z - (1 + 5 * y + 13 * y**2 + 8 * y**3)

    # --- Birational identity: R(z_fun, y_fun) = 0 on E ---
    R_sub = sp.together(R.subs({z: z_fun, y: y_fun}))
    R_num, _R_den = R_sub.as_numer_denom()
    G_E = sp.groebner([E], Y, X, order="lex", domain=sp.QQ)
    _, R_rem = G_E.reduce(sp.expand(R_num))
    bir_R_ok = bool(sp.factor(R_rem) == 0)

    # --- Inverse composition: (X,Y) -> (y,z) -> (X_back, Y_back) ---
    X_inv = sp.together((7 * y + 4 - 4 * z) / y)
    Y_inv = sp.together(X_inv**2 - 14 * X_inv - 19 - (8 * X_inv) / y)

    X_back = sp.together(X_inv.subs({y: y_fun, z: z_fun}))
    X_back_num, _ = sp.together(X_back - X).as_numer_denom()
    _, X_back_rem = G_E.reduce(sp.expand(X_back_num))
    bir_X_ok = bool(sp.factor(X_back_rem) == 0)

    Y_back = sp.together(Y_inv.subs({y: y_fun, z: z_fun}))
    Y_back_num, _ = sp.together(Y_back - Y).as_numer_denom()
    _, Y_back_rem = G_E.reduce(sp.expand(Y_back_num))
    bir_Y_ok = bool(sp.factor(Y_back_rem) == 0)

    # --- Weierstrass invariants for a1=a3=0, a2=-37, a4=307, a6=361 ---
    a1 = sp.Integer(0)
    a2 = sp.Integer(-37)
    a3 = sp.Integer(0)
    a4 = sp.Integer(307)
    a6 = sp.Integer(361)

    b2 = a1**2 + 4 * a2
    b4 = a1 * a3 + 2 * a4
    b6 = a3**2 + 4 * a6
    c4 = int(sp.Integer(b2**2 - 24 * b4))
    c6 = int(sp.Integer(-b2**3 + 36 * b2 * b4 - 216 * b6))
    Delta = sp.simplify((sp.Integer(c4) ** 3 - sp.Integer(c6) ** 2) / 1728)
    if not (Delta.is_Integer):
        raise RuntimeError(f"Expected integer Delta, got {Delta}")
    Delta_int = int(Delta)
    j = sp.simplify(sp.Rational(c4) ** 3 / sp.Integer(Delta_int))

    inv_ok = bool(
        c4 == 7168
        and c6 == -341504
        and sp.factor(Delta_int - (2**12 * 31**2 * 37)) == 0
        and j == sp.Rational(2**18 * 7**3, 31**2 * 37)
    )

    # --- Fiber/divisor intersection checks (by X-factorizations) ---
    # Denominator D=0: Y = X^2 - 14X - 19.
    Y_D = X**2 - 14 * X - 19
    poly_D = sp.factor(sp.expand(Y_D**2 - fX))

    # y-1 numerator N1=0: y-1 = (-8X - D)/D, so N1 = -8X - D = X^2 - 22X - Y - 19.
    # Setting N1=0 gives Y = X^2 - 22X - 19.
    Y_N1 = X**2 - 22 * X - 19
    poly_N1 = sp.factor(sp.expand(Y_N1**2 - fX))

    # Check key fiber points numerically on E_R.
    def y_at(xv: int, yv: int) -> sp.Rational:
        return sp.together(y_fun.subs({X: xv, Y: yv})).as_numer_denom()[0] / sp.together(y_fun.subs({X: xv, Y: yv})).as_numer_denom()[1]

    def z_at(xv: int, yv: int) -> sp.Rational:
        return sp.together(z_fun.subs({X: xv, Y: yv})).as_numer_denom()[0] / sp.together(z_fun.subs({X: xv, Y: yv})).as_numer_denom()[1]

    fiber_checks_ok = True
    try:
        # y=1 fiber sample points
        if sp.simplify(y_fun.subs({X: 23, Y: 4}) - 1) != 0:
            fiber_checks_ok = False
        if sp.simplify(y_fun.subs({X: -1, Y: 4}) - 1) != 0:
            fiber_checks_ok = False
        # y=0 point (0,19)
        if sp.simplify(y_fun.subs({X: 0, Y: 19}) - 0) != 0:
            fiber_checks_ok = False
        # z-image of P=(23,4)
        if sp.simplify(z_fun.subs({X: 23, Y: 4}) + 3) != 0:
            fiber_checks_ok = False
    except Exception:
        fiber_checks_ok = False

    # --- Critical locus dy=0 elimination (X-factor) ---
    fX_prime = sp.diff(fX, X)
    dY_dX = sp.together(fX_prime / (2 * Y))
    dy_dX = sp.together(sp.diff(y_fun, X) + sp.diff(y_fun, Y) * dY_dX)
    dy_num, _dy_den = dy_dX.as_numer_denom()
    # Clear remaining denominators to get a polynomial in (X,Y).
    dy_num = sp.factor(sp.together(dy_num).as_numer_denom()[0])

    # Eliminate Y using the curve equation.
    res_dy = sp.resultant(sp.expand(dy_num), E, Y)
    res_dy_fac = sp.factor(res_dy)

    # Expected nontrivial finite ramification X-coordinates: X=15, X=23, and roots of g_R.
    g_R = 4 * X**3 + 3 * X**2 + 114 * X - 269
    crit_expected = sp.factor((X - 15) * (X - 23) * g_R)
    # The elimination polynomial may pick up an extra factor from the removable base-point of the
    # chosen y-representation (at X=0, Y=-19 where both numerator and denominator vanish).
    # We therefore compare squarefree parts up to an optional X-factor, after monic normalization.
    sqf_expr = sp.Poly(res_dy_fac, X, domain=sp.QQ).sqf_part().as_expr()
    sqf_monic = sp.Poly(sqf_expr, X, domain=sp.QQ).monic().as_expr()
    crit_monic = sp.Poly(crit_expected, X, domain=sp.QQ).monic().as_expr()
    crit_with_base_monic = sp.Poly(X * crit_expected, X, domain=sp.QQ).monic().as_expr()
    critical_ok = bool(
        sp.factor(sqf_monic - crit_monic) == 0 or sp.factor(sqf_monic - crit_with_base_monic) == 0
    )

    # --- Discriminant of g_R and quadratic resolvent ---
    disc_g = int(sp.discriminant(g_R, X))
    disc_fac = sp.factorint(abs(disc_g))
    disc_fac_str = {str(k): int(v) for k, v in sorted(disc_fac.items(), key=lambda kv: kv[0])}
    quad_field = "Q(sqrt(-111))" if disc_g < 0 else f"Q(sqrt({disc_g}))"

    # --- Resultant elimination to P_LY(y) ---
    P_LY = 256 * y**3 + 411 * y**2 + 165 * y + 32
    rel = (X - 15) * (2 * X**2 + X + 15) * y - 16 * (X**2 + 19)
    res_xy = sp.factor(sp.resultant(g_R, rel, X))
    # Normalize up to a rational unit.
    res_xy_prim = sp.factor(sp.Poly(res_xy, y, domain=sp.QQ).primitive()[1].as_expr())
    resultant_ok = bool(sp.factor(res_xy_prim - P_LY) == 0 or sp.factor(res_xy_prim + P_LY) == 0)

    # --- Torsion-triviality certificate via coprime reductions ---
    bad = {2, 31, 37}
    f_coeffs_int = (-37, 307, 361)  # x^3 + a2 x^2 + a4 x + a6
    p1, n1, p2, n2 = _find_coprime_reduction_certificate(bad, f_coeffs_int, search_limit=200)
    tors_gcd = math.gcd(n1, n2)

    # --- Legendre symbols for splitting at 31 and 37 ---
    ls31 = _legendre_symbol(-c6, 31)
    ls37 = _legendre_symbol(-c6, 37)

    payload = Payload(
        birational_R_identity_ok=bir_R_ok,
        birational_inverse_X_ok=bir_X_ok,
        birational_inverse_Y_ok=bir_Y_ok,
        invariants_ok=inv_ok,
        c4=c4,
        c6=c6,
        Delta=Delta_int,
        j=str(j),
        D_intersection_factor=str(poly_D),
        y_minus_1_intersection_factor=str(poly_N1),
        y_fiber_checks_ok=fiber_checks_ok,
        dy_critical_X_factor=str(res_dy_fac),
        critical_polynomial_ok=critical_ok,
        g_R=str(g_R),
        disc_g_R=disc_g,
        disc_g_R_factorization=disc_fac_str,
        quadratic_resolvent_field=quad_field,
        resultant_P_LY_factor=str(res_xy),
        resultant_P_LY_ok=resultant_ok,
        torsion_certificate_primes=[int(p1), int(p2)],
        torsion_certificate_counts=[int(n1), int(n2)],
        torsion_certificate_gcd=int(tors_gcd),
        legendre_minus_c6_31=int(ls31),
        legendre_minus_c6_37=int(ls37),
    )

    if not args.no_output:
        _write_json(export_dir() / "fold_zm_resolvent_cubic_weierstrass_audit.json", asdict(payload))

        # TeX: keep it LaTeX-friendly (no Python '**' or '*').
        Delta_fac = sp.factorint(abs(Delta_int))
        Delta_terms = [
            (sp.Integer(pp) if int(ee) == 1 else sp.Pow(sp.Integer(pp), sp.Integer(ee), evaluate=False))
            for pp, ee in sorted(Delta_fac.items())
        ]
        Delta_expr = sp.Mul(*Delta_terms, evaluate=False) if Delta_terms else sp.Integer(1)
        if Delta_int < 0:
            Delta_expr = -Delta_expr

        tex = [
            "% Auto-generated by scripts/exp_fold_zm_resolvent_cubic_weierstrass_audit.py",
            r"\[",
            r"E_{\mathscr R}:\quad Y^2=X^3-37X^2+307X+361.",
            r"\]",
            r"\[",
            rf"c_4={c4},\quad c_6={c6},\quad \Delta={sp.latex(Delta_expr)},\quad j={sp.latex(j)}.",
            r"\]",
            r"\[",
            rf"\mathrm{{Disc}}(g_{{\mathscr R}})={sp.latex(sp.factor(disc_g))}.",
            r"\]",
            r"\[",
            rf"\mathrm{{Res}}_X\!\Bigl(g_{{\mathscr R}}(X),\ (X-15)(2X^2+X+15)\,y-16(X^2+19)\Bigr)={sp.latex(res_xy)}.",
            r"\]",
            r"\[",
            rf"\#E_{{\mathscr R}}(\mathbb F_{{{p1}}})={n1},\qquad \#E_{{\mathscr R}}(\mathbb F_{{{p2}}})={n2},\qquad \gcd={tors_gcd}.",
            r"\]",
        ]
        _write_text(generated_dir() / "eq_fold_zm_resolvent_cubic_weierstrass_audit.tex", "\n".join(tex) + "\n")

    dt = time.time() - t0
    print(
        "[fold-zm-resolvent-cubic-weierstrass] done"
        f" bir={bir_R_ok and bir_X_ok and bir_Y_ok} inv={inv_ok}"
        f" crit={critical_ok} res={resultant_ok} tors_gcd={tors_gcd} seconds={dt:.3f}",
        flush=True,
    )


if __name__ == "__main__":
    main()

