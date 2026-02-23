#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit the two-parameter quartic branch-discriminant family:

  F_t(mu, u) = mu^4 - mu^3 - (t u + 1) mu^2 + mu (t u - u^3) + t u

with

  Disc_mu(F_t) = u * D_t(u),    D_t(u) in Z[t,u], deg_u D_t = 11.

The script certifies:
  1) Closed-form formula for D_t(u).
  2) C3-covariance D_{zeta t}(u) = zeta D_t(zeta u), zeta^3 = 1.
  3) Closed factorization of Delta(t) = Disc_u(D_t).
  4) Real collision loci from Delta(t)=0.
  5) u=1 factorization and strict SOS positivity of the quartic factor.
  6) Singular-locus elimination via Groebner basis:
       <D_t, d_u D_t, d_t D_t> with lex order u > t.

Outputs:
  - artifacts/export/fold_zm_elliptic_translation_t_discriminant_c3_audit.json
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

import sympy as sp

from common_paths import export_dir


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _D_t_poly(t: sp.Symbol, u: sp.Symbol) -> sp.Expr:
    return sp.expand(
        -27 * u**11
        + 90 * t * u**9
        + (4 * t**3 - 22) * u**8
        - 239 * t**2 * u**7
        - (8 * t**4 + 70 * t) * u**6
        + (236 * t**3 + 5) * u**5
        + (20 * t**5 - 164 * t**2) * u**4
        - (120 * t**4 + 108 * t) * u**3
        + 220 * t**3 * u**2
        - 120 * t**2 * u
        + 20 * t
    )


def _P9_poly(s: sp.Symbol) -> sp.Expr:
    return sp.expand(
        17864502295709707825431356157528873283413020214750253582630010725020746370305048576000000 * s**9
        + 1827985552391858929673625577699869358461325615692919356153396939222537398020953119539200000 * s**8
        + 472380765502860761689023714837178856458962674487907763054197839296312918358467091455103488000 * s**7
        + 20669312921272651046479667688582870966622217807989339629125906175063486375887028759114636876800 * s**6
        + 2479717207964943525348394675715513569066639511983825407996293452948613349769192552883221946978496 * s**5
        - 13112777363415463937040364405348120900527714677007038191152130648141031999868546590632040898213488 * s**4
        + 32206159583214755787286512483786868328764234040970721269159053665093307376534469693668131746127017 * s**3
        - 1341350108695509062380855870071374542799221268567807990255827240403545308460434755576190878625288 * s**2
        + 14031773541681724880812976025532230691811442528685420734972982181307286334826738788279124405440 * s
        + 1142522353125628145251947755351541775770680303528808392151252348593203216967111461525699072
    )


def _real_numeric_roots(poly: sp.Expr, var: sp.Symbol, digits: int = 30) -> List[float]:
    roots = sp.nroots(poly)
    out: List[float] = []
    tol = 10 ** (-(digits // 2))
    for r in roots:
        re = float(sp.N(sp.re(r), digits))
        im = float(sp.N(sp.im(r), digits))
        if abs(im) < tol:
            out.append(re)
    out.sort()
    return out


def _reduce_mod_z3_minus_1(expr: sp.Expr, z: sp.Symbol) -> sp.Expr:
    return sp.expand(sp.Poly(sp.expand(expr), z).rem(sp.Poly(z**3 - 1, z)).as_expr())


@dataclass(frozen=True)
class Payload:
    deg_u_D_t: int
    disc_mu_equals_u_D_t: bool
    c3_covariance: bool
    disc_u_factorization_ok: bool
    phi2_has_real_root: bool
    phi1_real_t_roots: List[float]
    phi3_real_t_roots: List[float]
    D_t_at_u1_factorization_ok: bool
    q_sos_identity_ok: bool
    singular_t_elimination_ok: bool
    singular_t_squarefree_ok: bool
    singular_linear_u_relation_ok: bool
    singular_u_formula: str
    elapsed_s: float


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit D_t(u), C3 covariance, and singular-locus elimination.")
    parser.add_argument("--no-output", action="store_true", help="Skip writing JSON output.")
    args = parser.parse_args()

    t0 = time.time()
    mu, t, u, z, s = sp.symbols("mu t u z s")

    # 1) Quartic model and closed D_t(u).
    F_t = mu**4 - mu**3 - (t * u + 1) * mu**2 + mu * (t * u - u**3) + t * u
    D_t = _D_t_poly(t, u)

    disc_mu = sp.expand(sp.discriminant(F_t, mu))
    disc_mu_ok = sp.expand(disc_mu - u * D_t) == 0
    deg_u = int(sp.Poly(D_t, u, domain=sp.QQ[t]).degree())

    # 2) C3 covariance.
    cov_expr = _reduce_mod_z3_minus_1(sp.expand(_D_t_poly(z * t, u) - z * _D_t_poly(t, z * u)), z)
    c3_cov_ok = sp.expand(cov_expr) == 0

    # 3) Discriminant in u and complete factorization.
    Delta = sp.expand(sp.discriminant(sp.Poly(D_t, u), u))
    Phi1 = 80 * t**6 + 16424 * t**3 - 84375
    Phi2 = 256 * t**6 - 1312 * t**3 + 3125
    Phi3 = 8000 * t**12 + 429800 * t**9 + 96378087 * t**6 - 2034256 * t**3 - 64
    Delta_expected = sp.expand(sp.Integer(515978035200) * t**4 * Phi1 * Phi2**2 * Phi3**3)
    Delta_ok = sp.expand(Delta - Delta_expected) == 0

    # 4) Real-collision slices from factorized Delta.
    Phi1_s = 80 * s**2 + 16424 * s - 84375
    Phi2_s = 256 * s**2 - 1312 * s + 3125
    Phi3_s = 8000 * s**4 + 429800 * s**3 + 96378087 * s**2 - 2034256 * s - 64

    phi1_real_s = _real_numeric_roots(Phi1_s, s, digits=40)
    phi3_real_s = _real_numeric_roots(Phi3_s, s, digits=40)
    phi1_real_t = sorted(float(sp.N(sp.real_root(sp.nsimplify(v), 3), 40)) for v in phi1_real_s)
    phi3_real_t = sorted(float(sp.N(sp.real_root(sp.nsimplify(v), 3), 40)) for v in phi3_real_s)
    phi2_disc = int(sp.expand(sp.discriminant(sp.Poly(Phi2_s, s), s)))
    phi2_has_real_root = phi2_disc >= 0

    # 5) u=1 specialization and strict SOS decomposition.
    D_u1 = sp.expand(D_t.subs(u, 1))
    q = 20 * t**4 - 88 * t**3 + 284 * t**2 + 45 * t + 22
    D_u1_ok = sp.expand(D_u1 - (t - 2) * q) == 0
    q_sos = sp.expand(
        20 * (t**2 - sp.Rational(11, 5) * t) ** 2
        + sp.Rational(936, 5) * (t + sp.Rational(25, 208)) ** 2
        + sp.Rational(8027, 416)
    )
    q_sos_ok = sp.expand(q_sos - q) == 0

    # 6) Singular-locus elimination: <D_t, D_u, D_t'> with lex(u > t).
    D_u = sp.diff(D_t, u)
    D_t_der = sp.diff(D_t, t)
    G = sp.groebner([D_t, D_u, D_t_der], u, t, order="lex")

    t_only = [sp.factor(p.as_expr()) for p in G.polys if p.free_symbols <= {t}]
    if len(t_only) != 1:
        raise RuntimeError(f"expected one elimination polynomial in t, got {len(t_only)}")
    t_elim = sp.expand(t_only[0])
    t_elim_expected = sp.expand(Phi2 * Phi3**2)
    t_elim_ok = sp.expand(t_elim - t_elim_expected) == 0

    t_sqf = sp.factor(sp.Poly(t_elim, t, domain=sp.QQ).sqf_part().as_expr())
    t_sqf_expected = sp.factor(sp.expand(Phi2 * Phi3))
    sqf_ratio = sp.simplify(sp.together(sp.expand(t_sqf) / sp.expand(t_sqf_expected)))
    t_sqf_ok = (sqf_ratio.free_symbols == set()) and (sqf_ratio != 0)

    linear_u = []
    for p in G.polys:
        poly_ut = sp.Poly(p.as_expr(), u, t, domain=sp.QQ)
        if poly_ut.degree(u) == 1:
            linear_u.append(poly_ut)
    if len(linear_u) != 1:
        raise RuntimeError(f"expected one linear-in-u eliminant, got {len(linear_u)}")
    Lu = linear_u[0]
    a = sp.expand(Lu.coeff_monomial(u))
    b = sp.expand(Lu.as_expr().subs(u, 0))

    C = sp.Integer(1146919918223400883707609447433426476251203385787440489213053015719484911581940154368000)
    P9 = _P9_poly(s).subs(s, t**3)

    rel_minus = sp.expand(a * u + b - (C * u - t**2 * P9)) == 0
    rel_plus = sp.expand(a * u + b - (C * u + t**2 * P9)) == 0
    linear_u_ok = bool(rel_minus or rel_plus)
    if rel_minus:
        u_formula = "u = t^2 * P9(t^3) / C"
    elif rel_plus:
        u_formula = "u = -t^2 * P9(t^3) / C"
    else:
        u_formula = "unmatched"

    payload = Payload(
        deg_u_D_t=deg_u,
        disc_mu_equals_u_D_t=bool(disc_mu_ok),
        c3_covariance=bool(c3_cov_ok),
        disc_u_factorization_ok=bool(Delta_ok),
        phi2_has_real_root=bool(phi2_has_real_root),
        phi1_real_t_roots=phi1_real_t,
        phi3_real_t_roots=phi3_real_t,
        D_t_at_u1_factorization_ok=bool(D_u1_ok),
        q_sos_identity_ok=bool(q_sos_ok),
        singular_t_elimination_ok=bool(t_elim_ok),
        singular_t_squarefree_ok=bool(t_sqf_ok),
        singular_linear_u_relation_ok=bool(linear_u_ok),
        singular_u_formula=u_formula,
        elapsed_s=float(time.time() - t0),
    )

    if not payload.disc_mu_equals_u_D_t:
        raise AssertionError("Disc_mu(F_t) = u*D_t(u) check failed")
    if payload.deg_u_D_t != 11:
        raise AssertionError(f"deg_u(D_t) expected 11, got {payload.deg_u_D_t}")
    if not payload.c3_covariance:
        raise AssertionError("C3 covariance check failed")
    if not payload.disc_u_factorization_ok:
        raise AssertionError("Disc_u(D_t) factorization check failed")
    if payload.phi2_has_real_root:
        raise AssertionError("Phi2 unexpectedly has real roots")
    if not payload.D_t_at_u1_factorization_ok:
        raise AssertionError("D_t(1) factorization check failed")
    if not payload.q_sos_identity_ok:
        raise AssertionError("q(t) SOS identity check failed")
    if not payload.singular_t_elimination_ok:
        raise AssertionError("Groebner t-elimination polynomial check failed")
    if not payload.singular_t_squarefree_ok:
        raise AssertionError("Groebner squarefree t-elimination check failed")
    if not payload.singular_linear_u_relation_ok:
        raise AssertionError("Groebner linear u-relation check failed")

    if not args.no_output:
        out = export_dir() / "fold_zm_elliptic_translation_t_discriminant_c3_audit.json"
        _write_json(out, asdict(payload))

    print(
        "[fold-zm-elliptic-translation-t-discriminant-c3] "
        f"deg_u={payload.deg_u_D_t} "
        f"disc_mu_ok={payload.disc_mu_equals_u_D_t} "
        f"disc_u_ok={payload.disc_u_factorization_ok} "
        f"singular_elim_ok={payload.singular_t_elimination_ok} "
        f"u_formula='{payload.singular_u_formula}' "
        f"elapsed_s={payload.elapsed_s:.3f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
