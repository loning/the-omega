#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit Lattès doubling, y-quadratic extension, and rational point denominator law
on the Fold weight elliptic curve

  E:  Y^2 = X^3 - X + 1/4.

This script is English-only by repository convention.

We verify:
  - Lattès map on x-coordinate induced by [2]:
      Phi(X) = x([2]P) = (X^4 + 2 X^2 - 2 X + 1) / (4 X^3 - 4 X + 1).
  - Critical polynomial of Phi:
      Phi'(X)=0  <=>  2X^6 - 10X^4 + 10X^3 - 10X^2 + 2X + 1 = 0.
  - Quadratic minimal polynomial of the physical weight parameter
      y = X^2 - Y - 1/2
    over Q(X), with discriminant 4X^3 - 4X + 1 = 4Y^2.
  - Torsion triviality via gcd of #E(F_p) over several good primes p.
  - For the physical point P = (2, 5/2), the denominator law:
      if x(nP) = u_n / v_n^2 in lowest terms with v_n>0, then
      den(y(nP)) = v_n^4,
    and we reproduce the first six terms.

Outputs:
  - artifacts/export/fold_zm_elliptic_lattes_rational_points_audit.json
  - sections/generated/eq_fold_zm_elliptic_lattes_rational_points_audit.tex
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import sympy as sp

from common_paths import export_dir, generated_dir


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


Point = Optional[Tuple[sp.Rational, sp.Rational]]  # None denotes the point at infinity O


def _add(P: Point, Q: Point, *, a: sp.Rational) -> Point:
    """Group law on short Weierstrass: Y^2 = X^3 + aX + b (b unused for formulas)."""
    if P is None:
        return Q
    if Q is None:
        return P
    x1, y1 = P
    x2, y2 = Q

    if x1 == x2 and y1 == -y2:
        return None

    if x1 == x2 and y1 == y2:
        # doubling
        m = sp.simplify((3 * x1 * x1 + a) / (2 * y1))
    else:
        m = sp.simplify((y2 - y1) / (x2 - x1))

    x3 = sp.together(m * m - x1 - x2)
    y3 = sp.together(m * (x1 - x3) - y1)
    # With rational inputs, SymPy keeps exact rationals (avoid nsimplify here).
    return (sp.simplify(x3), sp.simplify(y3))


def _mul(n: int, P: Point, *, a: sp.Rational) -> Point:
    if n < 0:
        if P is None:
            return None
        x, y = P
        return _mul(-n, (x, -y), a=a)
    if n == 0:
        return None
    if n == 1:
        return P
    # double-and-add
    Q: Point = None
    R: Point = P
    k = n
    while k > 0:
        if k & 1:
            Q = _add(Q, R, a=a)
        R = _add(R, R, a=a)
        k >>= 1
    return Q


def _fraction_to_uv2(x: sp.Rational) -> Tuple[int, int, int, bool]:
    """Return (u, v, den, is_square_den) for x = u / den, and try den = v^2."""
    num, den = sp.fraction(sp.together(x))
    num_i = int(num)
    den_i = int(den)
    v, exact = sp.integer_nthroot(den_i, 2)
    return num_i, int(v), den_i, bool(exact)


def _denominator(q: sp.Rational) -> int:
    return int(sp.denom(sp.together(q)))


def _count_points_mod_p(p: int) -> int:
    """
    Count #E(F_p) for the model y^2 = 4x^3 - 4x + 1.

    For odd p, this is F_p-isomorphic to Y^2 = X^3 - X + 1/4 (map y=2Y).
    """
    if p == 2:
        raise ValueError("Use odd primes only.")
    cnt = 1  # point at infinity
    for x in range(p):
        rhs = (4 * x * x * x - 4 * x + 1) % p
        # count solutions y^2 = rhs
        if rhs == 0:
            cnt += 1
        else:
            # Legendre symbol via Euler criterion
            ls = pow(rhs, (p - 1) // 2, p)
            if ls == 1:
                cnt += 2
            # ls == p-1 => nonresidue, add 0
    return int(cnt)


@dataclass(frozen=True)
class TableRow:
    n: int
    x: str
    u_n: int
    v_n: int
    x_den: int
    x_den_is_square: bool
    y_weight: str
    den_y: int
    v_n_pow4: int
    den_law_ok: bool


@dataclass(frozen=True)
class Payload:
    phi_formula_ok: bool
    phi_prime_critical_poly_ok: bool
    y_minpoly_ok: bool
    y_discriminant_ok: bool
    torsion_primes: List[int]
    torsion_group_orders: List[int]
    torsion_gcd: int
    torsion_trivial: bool
    base_point: Dict[str, str]
    table_first6: List[TableRow]


def main() -> None:
    t0 = time.time()
    print("[fold-zm-elliptic-lattes] start", flush=True)

    X = sp.Symbol("X")
    Y = sp.Symbol("Y")

    # Curve: Y^2 = X^3 - X + 1/4.
    a = sp.Integer(-1)
    b = sp.Rational(1, 4)

    # --- Lattès doubling map on x ---
    Phi = sp.simplify(((3 * X**2 + a) / (2 * Y)) ** 2 - 2 * X)
    Phi = sp.simplify(Phi.subs({Y**2: X**3 + a * X + b}))
    Phi = sp.together(Phi)
    N, D = Phi.as_numer_denom()
    N = sp.factor(N)
    D = sp.factor(D)

    Phi_expected = sp.together((X**4 + 2 * X**2 - 2 * X + 1) / (4 * X**3 - 4 * X + 1))
    phi_ok = bool(sp.factor(Phi - Phi_expected) == 0)

    # --- Critical polynomial for Phi'(X)=0 (affine chart) ---
    Phi_prime = sp.diff(Phi_expected, X)
    nump, denp = sp.together(Phi_prime).as_numer_denom()
    nump = sp.factor(nump)
    crit_expected = 2 * X**6 - 10 * X**4 + 10 * X**3 - 10 * X**2 + 2 * X + 1
    # Normalize by removing content (overall integer factor).
    poly_nump = sp.Poly(nump, X, domain="ZZ")
    _, prim_nump = poly_nump.primitive()
    nump_prim = sp.factor(prim_nump.as_expr())
    crit_ok = bool(sp.factor(nump_prim - crit_expected) == 0 or sp.factor(nump_prim + crit_expected) == 0)

    # --- y quadratic minimal polynomial over Q(X) ---
    y = sp.Symbol("y")
    y_def = X**2 - Y - sp.Rational(1, 2)
    # Eliminate Y using Y = X^2 - y - 1/2.
    elim = sp.expand((X**2 - y - sp.Rational(1, 2)) ** 2 - (X**3 + a * X + b))
    minpoly = sp.factor(elim)
    minpoly_expected = y**2 - (2 * X**2 - 1) * y + X * (X - 1) ** 2 * (X + 1)
    y_minpoly_ok = bool(sp.factor(minpoly - minpoly_expected) == 0)

    disc = sp.factor(sp.discriminant(minpoly_expected, y))
    disc_expected = 4 * X**3 - 4 * X + 1
    y_disc_ok = bool(sp.factor(disc - disc_expected) == 0)

    # --- Torsion audit via reduction mod p ---
    primes = [3, 5, 7, 11, 13, 17, 19]
    good_primes = [p for p in primes if p not in (2, 37)]
    orders = [_count_points_mod_p(p) for p in good_primes]
    g = 0
    for n in orders:
        g = math.gcd(g, n)
    torsion_trivial = bool(g == 1)

    # --- Rational point orbit and denominator law ---
    P: Point = (sp.Integer(2), sp.Rational(5, 2))
    # sanity check P on curve
    if sp.simplify(P[1] ** 2 - (P[0] ** 3 + a * P[0] + b)) != 0:
        raise RuntimeError("Base point P is not on the curve.")

    def y_weight(pt: Point) -> sp.Rational:
        if pt is None:
            raise ValueError("y(weight) undefined at O.")
        xpt, ypt = pt
        return sp.together(xpt**2 - ypt - sp.Rational(1, 2))

    rows: List[TableRow] = []
    for n in range(1, 7):
        pt = _mul(n, P, a=a)
        if pt is None:
            raise RuntimeError("Unexpected: nP hit O for small n (would contradict torsion triviality).")
        xpt, ypt = pt
        u_n, v_n, x_den, den_is_square = _fraction_to_uv2(sp.together(xpt))
        yw = sp.together(y_weight(pt))
        den_y = _denominator(yw)
        v4 = int(v_n) ** 4
        ok = bool(den_is_square and den_y == v4)
        rows.append(
            TableRow(
                n=n,
                x=sp.sstr(sp.Rational(xpt)),
                u_n=int(u_n),
                v_n=int(v_n),
                x_den=int(x_den),
                x_den_is_square=bool(den_is_square),
                y_weight=sp.sstr(yw),
                den_y=int(den_y),
                v_n_pow4=int(v4),
                den_law_ok=bool(ok),
            )
        )

    payload = Payload(
        phi_formula_ok=bool(phi_ok),
        phi_prime_critical_poly_ok=bool(crit_ok),
        y_minpoly_ok=bool(y_minpoly_ok),
        y_discriminant_ok=bool(y_disc_ok),
        torsion_primes=[int(p) for p in good_primes],
        torsion_group_orders=[int(n) for n in orders],
        torsion_gcd=int(g),
        torsion_trivial=bool(torsion_trivial),
        base_point={"P": "(2,5/2)", "minus_P": "(2,-5/2)", "y(P)": sp.sstr(y_weight(P))},
        table_first6=rows,
    )

    out_json = export_dir() / "fold_zm_elliptic_lattes_rational_points_audit.json"
    _write_json(out_json, asdict(payload))

    # TeX snippet (keep it short; full table is in JSON).
    tex_lines: List[str] = [
        "% Auto-generated by scripts/exp_fold_zm_elliptic_lattes_rational_points_audit.py",
        "\\[",
        "\\Phi(X)=\\frac{X^{4}+2X^{2}-2X+1}{4X^{3}-4X+1},\\qquad \\Phi'(X)=0\\iff 2X^{6}-10X^{4}+10X^{3}-10X^{2}+2X+1=0.",
        "\\]",
        "\\[",
        "y:=X^{2}-Y-\\frac12,\\qquad y^{2}-(2X^{2}-1)y+X(X-1)^{2}(X+1)=0,\\qquad \\Delta=4X^{3}-4X+1=4Y^{2}.",
        "\\]",
        "\\[",
        "E(\\mathbb{Q})_{\\mathrm{tors}}=\\{O\\}\\ \\text{(gcd of }\\#E(\\mathbb{F}_p)\\text{ over small good primes equals }1).",
        "\\]",
        "",
    ]
    out_tex = generated_dir() / "eq_fold_zm_elliptic_lattes_rational_points_audit.tex"
    _write_text(out_tex, "\n".join(tex_lines))

    dt = time.time() - t0
    print(
        "[fold-zm-elliptic-lattes] checks:"
        f" phi={phi_ok} crit={crit_ok} minpoly={y_minpoly_ok} disc={y_disc_ok} tors_gcd={g} denlaw={all(r.den_law_ok for r in rows)}"
        f" seconds={dt:.3f}",
        flush=True,
    )
    print(f"[fold-zm-elliptic-lattes] wrote {out_json}", flush=True)
    print(f"[fold-zm-elliptic-lattes] wrote {out_tex}", flush=True)
    print("[fold-zm-elliptic-lattes] done", flush=True)


if __name__ == "__main__":
    main()

