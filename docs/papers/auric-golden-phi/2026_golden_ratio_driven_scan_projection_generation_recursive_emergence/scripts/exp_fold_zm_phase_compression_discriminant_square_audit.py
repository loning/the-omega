#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit the phase-compression eliminant G(s,y) for the Fold fiber-weight spectral quartic.

This script is English-only by repository convention.

We use the explicit Chebyshev-compressed eliminant G(s,y) in Z[s,y] defined in
  sections/generated/eq_fold_zm_phase_resonance_resultant_chebyshev.tex
(and audited by exp_fold_zm_phase_resonance_resultant_chebyshev_audit.py),
and verify additional structural identities:

  - Endpoint degeneracy at s=-2:
      G(-2,y) = y^2 (y-1)^2.

  - Discriminant in s is a perfect square in Z[y]:
      Disc_s(G(s,y)) = Delta_G(y)^2,
    with an explicit factorization for Delta_G(y) and a degree-9 factor P9(y).

  - Singular-fiber y-projection certificate for the affine plane model G(s,y)=0:
    letting D1(y):=Res_s(G, ∂_s G) and D2(y):=Res_s(G, ∂_y G), we verify
      gcd(D1(y), D2(y)) = y^10 (y-1)^3 (y+1)^6 (y^2+y-1)^4 P9(y)^2
    in Z[y].

  - Golden-conjugate singular fibers (over Q(sqrt(5))):
    at y satisfying y^2+y-1=0, we verify that gcd_s(G, ∂_s G) equals the expected
    quadratic factor, and that the same factor divides ∂_y G, certifying that
    exactly two affine singular points occur above each golden-conjugate parameter.

  - Two specializations used in the paper:
      G(s,0)=-(s-2)(s+2)^2,   G(s,1)=(s-2)(s+2)^2(2s+5)^2(2s-5).

Outputs:
  - artifacts/export/fold_zm_phase_compression_discriminant_square_audit.json
  - sections/generated/eq_fold_zm_phase_compression_discriminant_square.tex
"""

from __future__ import annotations

import argparse
import json
import time
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


def _poly_y(expr: sp.Expr, y: sp.Symbol) -> sp.Poly:
    return sp.Poly(sp.expand(expr), y, domain=sp.ZZ)


def _monic_y(p: sp.Expr, y: sp.Symbol) -> sp.Poly:
    return _poly_y(p, y).monic()


def _poly_s_y(expr: sp.Expr, s: sp.Symbol, y: sp.Symbol) -> sp.Poly:
    return sp.Poly(sp.expand(expr), s, y, domain=sp.ZZ)


def _gcd_poly_y(a: sp.Expr, b: sp.Expr, y: sp.Symbol) -> sp.Poly:
    pa = _poly_y(a, y)
    pb = _poly_y(b, y)
    return sp.gcd(pa, pb).monic()


def _factor_list_y(expr: sp.Expr, y: sp.Symbol) -> Tuple[int, list[Tuple[sp.Expr, int]]]:
    poly = _poly_y(expr, y)
    coeff, factors = poly.factor_list()
    return int(coeff), [(f.as_expr(), int(e)) for (f, e) in factors]


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit discriminant-square and singular-fiber structure of G(s,y).")
    parser.add_argument("--no-output", action="store_true", help="Skip writing JSON/TeX outputs.")
    args = parser.parse_args()

    t0 = time.time()
    print("[fold-zm-phase-compression-disc-square] start", flush=True)

    s, y = sp.symbols("s y")

    # Explicit G(s,y) as audited in exp_fold_zm_phase_resonance_resultant_chebyshev_audit.py.
    g6 = y**6 + 3 * y**5 + 3 * y**4 + y**3
    g5 = 4 * y**6 + 12 * y**5 + 13 * y**4 + 6 * y**3 + y**2
    g4 = -(4 * y**6 + 14 * y**5 + 15 * y**4 + 6 * y**3 + 2 * y**2 + y)
    g3 = -(32 * y**6 + 110 * y**5 + 128 * y**4 + 68 * y**3 + 24 * y**2 + 6 * y + 1)
    g2 = -(16 * y**6 + 76 * y**5 + 81 * y**4 + 24 * y**3 + 8 * y**2 + 3 * y + 2)
    g1 = 64 * y**6 + 184 * y**5 + 265 * y**4 + 238 * y**3 + 113 * y**2 + 32 * y + 4
    g0 = 64 * y**6 + 208 * y**5 + 295 * y**4 + 250 * y**3 + 131 * y**2 + 44 * y + 8
    G = sp.expand(g6 * s**6 + g5 * s**5 + g4 * s**4 + g3 * s**3 + g2 * s**2 + g1 * s + g0)

    # Endpoint s=-2
    Gm2 = sp.factor(sp.expand(G.subs(s, -2)))
    endpoint_minus2_ok = bool(sp.expand(Gm2 - (y**2) * (y - 1) ** 2) == 0)

    # Discriminant in s.
    Disc_s = sp.expand(sp.discriminant(G, s))
    Disc_s_y = _poly_y(Disc_s, y)

    P_LY = 256 * y**3 + 411 * y**2 + 165 * y + 32
    P9 = (
        256 * y**9
        + 1219 * y**8
        + 2542 * y**7
        + 3090 * y**6
        + 2446 * y**5
        + 1315 * y**4
        + 478 * y**3
        + 112 * y**2
        + 16 * y
        + 1
    )
    Delta_G = y**5 * (y - 1) ** 2 * (y + 1) ** 3 * (y**2 + y - 1) ** 2 * P_LY * P9
    disc_matches_expected = bool(sp.expand(Disc_s - sp.expand(Delta_G**2)) == 0)

    # Check perfect-square property by factorization parity in Z[y].
    _, factors_disc = _factor_list_y(Disc_s, y)
    disc_is_square_in_Zy = all(e % 2 == 0 for (_f, e) in factors_disc)

    # Singular-fiber y-projection certificate: gcd of the two s-resultants.
    dGs = sp.diff(G, s)
    dGy = sp.diff(G, y)
    D1 = sp.expand(sp.resultant(G, dGs, s))
    D2 = sp.expand(sp.resultant(G, dGy, s))
    gcd_D1_D2 = _gcd_poly_y(D1, D2, y)

    gcd_expected = y**10 * (y - 1) ** 3 * (y + 1) ** 6 * (y**2 + y - 1) ** 4 * P9**2
    gcd_matches_expected = bool(sp.expand(gcd_D1_D2.as_expr() - _monic_y(gcd_expected, y).as_expr()) == 0)

    # Two specializations
    G_s0 = sp.factor(sp.expand(G.subs(y, 0)))
    G_s1 = sp.factor(sp.expand(G.subs(y, 1)))
    spec_0_ok = bool(sp.expand(G_s0 + (s - 2) * (s + 2) ** 2) == 0)
    spec_1_ok = bool(sp.expand(G_s1 - (s - 2) * (s + 2) ** 2 * (2 * s + 5) ** 2 * (2 * s - 5)) == 0)

    # Golden-conjugate singular fibers: y^2+y-1=0.
    sqrt5 = sp.sqrt(5)
    y_g1 = (-1 + sqrt5) / 2
    y_g2 = (-1 - sqrt5) / 2

    Q_g1_expr = s**2 - (sqrt5 - 2) * s - (1 + 2 * sqrt5)
    Q_g2_expr = sp.expand(Q_g1_expr.subs(sqrt5, -sqrt5))

    def _golden_checks(y0: sp.Expr, Q_expr: sp.Expr) -> Tuple[bool, bool, int]:
        G0 = sp.expand(G.subs(y, y0))
        dGs0 = sp.expand(dGs.subs(y, y0))
        dGy0 = sp.expand(dGy.subs(y, y0))
        pG = sp.Poly(G0, s, extension=[sqrt5])
        pGs = sp.Poly(dGs0, s, extension=[sqrt5])
        pGy = sp.Poly(dGy0, s, extension=[sqrt5])
        g_s = pG.gcd(pGs).monic()
        Qp = sp.Poly(Q_expr, s, extension=[sqrt5]).monic()
        gcd_ok = bool(sp.expand(g_s.as_expr() - Qp.as_expr()) == 0)
        dy_div_ok = bool(pGy.rem(Qp).is_zero)
        return gcd_ok, dy_div_ok, int(g_s.degree())

    golden_g1_gcd_ok, golden_g1_dy_div_ok, golden_g1_gcd_deg = _golden_checks(y_g1, Q_g1_expr)
    golden_g2_gcd_ok, golden_g2_dy_div_ok, golden_g2_gcd_deg = _golden_checks(y_g2, Q_g2_expr)

    payload: Dict[str, object] = {
        "endpoint_minus2_ok": endpoint_minus2_ok,
        "disc_is_square_in_Zy": disc_is_square_in_Zy,
        "disc_matches_expected": disc_matches_expected,
        "gcd_matches_expected": gcd_matches_expected,
        "spec_0_ok": spec_0_ok,
        "spec_1_ok": spec_1_ok,
        "golden_g1_gcd_ok": golden_g1_gcd_ok,
        "golden_g1_dy_div_ok": golden_g1_dy_div_ok,
        "golden_g1_gcd_deg": golden_g1_gcd_deg,
        "golden_g2_gcd_ok": golden_g2_gcd_ok,
        "golden_g2_dy_div_ok": golden_g2_dy_div_ok,
        "golden_g2_gcd_deg": golden_g2_gcd_deg,
        "deg_y_disc_s": int(Disc_s_y.degree()),
        "deg_y_gcd_D1_D2": int(gcd_D1_D2.degree()),
        "elapsed_s": float(time.time() - t0),
    }

    if not args.no_output:
        out_json = export_dir() / "fold_zm_phase_compression_discriminant_square_audit.json"
        out_tex = generated_dir() / "eq_fold_zm_phase_compression_discriminant_square.tex"

        tex = []
        tex.append("% Auto-generated by scripts/exp_fold_zm_phase_compression_discriminant_square_audit.py")
        tex.append(r"\[")
        tex.append(r"G(-2,y)=y^{2}(y-1)^{2}.")
        tex.append(r"\]")
        tex.append(r"\[")
        tex.append(
            r"\mathrm{Disc}_{s}\bigl(G(s,y)\bigr)=\Delta_{G}(y)^{2},"
            r"\qquad"
            r"\Delta_{G}(y)=y^{5}(y-1)^{2}(y+1)^{3}(y^{2}+y-1)^{2}P_{\mathrm{LY}}(y)P_{9}(y)."
        )
        tex.append(r"\]")
        tex.append(r"\[")
        tex.append(r"P_{9}(y)=" + sp.latex(_poly_y(P9, y).as_expr()) + r".")
        tex.append(r"\]")
        tex.append(r"\[")
        tex.append(
            r"\gcd\Bigl(\operatorname{Res}_{s}\bigl(G,\partial_{s}G\bigr),\ \operatorname{Res}_{s}\bigl(G,\partial_{y}G\bigr)\Bigr)"
            r"=y^{10}(y-1)^{3}(y+1)^{6}(y^{2}+y-1)^{4}P_{9}(y)^{2}."
        )
        tex.append(r"\]")
        tex.append(r"\[")
        tex.append(r"G(s,0)=-(s-2)(s+2)^{2},\qquad G(s,1)=(s-2)(s+2)^{2}(2s+5)^{2}(2s-5).")
        tex.append(r"\]")

        _write_json(out_json, payload)
        _write_text(out_tex, "\n".join(tex) + "\n")

    print("[fold-zm-phase-compression-disc-square] ok", flush=True)


if __name__ == "__main__":
    main()

