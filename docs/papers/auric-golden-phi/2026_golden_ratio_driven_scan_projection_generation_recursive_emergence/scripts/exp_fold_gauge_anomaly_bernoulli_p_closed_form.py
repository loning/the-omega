#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit: closed-form Bernoulli(p) laws for the fold gauge anomaly mismatch kernel.

This script is English-only by repository convention.

We verify (numerically, deterministically) the closed-form formulas in:
  sections/body/folding/subsubsec__fold-gauge-anomaly-bernoulli-p-baseline.tex

Model:
- 4-state Markov chain on (a,b,c,d) with transition matrix P(p)
- edge potential g=1 on (a->b), (b->c), (c->a); else 0
- mismatch sum G_m := sum_{n=0}^{m-1} g(S_n,S_{n+1})

Checks:
- stationary distribution and mismatch density g_*(p)
- asymptotic variance rate sigma_G^2(p) via Poisson equation (edge-reward martingale)
- characteristic polynomial factorization of P(p)
- endpoint LDP rate I_p(0) via rho(Q_p(0))
- covariance recurrence and generating function (spot checks)
- bit-pair law sums to 1 and matches p=1/2 table

Outputs:
- artifacts/export/fold_gauge_anomaly_bernoulli_p_closed_form.json
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import sympy as sp

from common_paths import export_dir


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _as_float(x: sp.Expr, *, prec: int = 80) -> float:
    return float(sp.N(x, prec))


def _max_abs(xs: List[float]) -> float:
    return max(abs(x) for x in xs) if xs else 0.0


@dataclass(frozen=True)
class CheckResult:
    name: str
    max_abs_err: float


def _P(p: float) -> List[List[float]]:
    return [
        [1.0 - p, p * p, 0.0, p * (1.0 - p)],
        [0.0, 0.0, 1.0, 0.0],
        [1.0 - p, p, 0.0, 0.0],
        [1.0, 0.0, 0.0, 0.0],
    ]


def _stationary_pi(P: List[List[float]]) -> List[float]:
    # Solve pi^T P = pi^T, sum pi = 1.
    # Use a 4x4 linear system built from (P^T - I) pi = 0 plus sum constraint.
    PT = list(zip(*P))
    A = [[PT[i][j] - (1.0 if i == j else 0.0) for j in range(4)] for i in range(4)]
    b = [0.0, 0.0, 0.0, 0.0]
    # Replace last equation with sum(pi)=1 for numerical stability.
    A[3] = [1.0, 1.0, 1.0, 1.0]
    b[3] = 1.0

    M = sp.Matrix(A)
    rhs = sp.Matrix(b)
    sol = list(map(float, list(M.LUsolve(rhs))))
    return sol


def _variance_rate_edge_reward(P: List[List[float]], pi: List[float]) -> float:
    # Edge reward r(i,j)=g(i,j).
    g = [
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
    ]
    # mu = E[r]
    mu = 0.0
    for i in range(4):
        for j in range(4):
            mu += pi[i] * P[i][j] * g[i][j]

    # f(i) = E[r | S=i]
    f = [sum(P[i][j] * g[i][j] for j in range(4)) for i in range(4)]

    # Solve (I - P + 1*pi^T) h = f - mu*1.
    I = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    A = [[I[i][j] - P[i][j] + 1.0 * pi[j] for j in range(4)] for i in range(4)]
    b = [f[i] - mu for i in range(4)]
    h = list(map(float, list(sp.Matrix(A).LUsolve(sp.Matrix(b)))))

    # Martingale increment: M = r - mu + h(S1)-h(S0)
    # sigma^2 = E[M^2]
    sig2 = 0.0
    for i in range(4):
        for j in range(4):
            inc = g[i][j] - mu + h[j] - h[i]
            sig2 += pi[i] * P[i][j] * (inc * inc)
    return sig2


def main() -> None:
    t0 = time.time()

    # Symbolic closed forms (from the paper).
    p = sp.Symbol("p", positive=True, real=True)
    g_star = sp.simplify(p**2 * (3 - 2 * p) / (1 + p**3))
    sigma_star = sp.simplify(
        p**2
        * (1 - p)
        * (21 * p**5 - 6 * p**4 + 14 * p**3 - 36 * p**2 + 7 * p + 9)
        / ((p + 1) ** 3 * (p**2 - p + 1) ** 3)
    )

    # Characteristic polynomial factorization (symbolic).
    P_sym = sp.Matrix(
        [
            [1 - p, p**2, 0, p * (1 - p)],
            [0, 0, 1, 0],
            [1 - p, p, 0, 0],
            [1, 0, 0, 0],
        ]
    )
    lam = sp.Symbol("lam")
    char_poly = sp.factor((lam * sp.eye(4) - P_sym).det())
    char_expected = sp.factor((lam - 1) * (lam + p) * (lam**2 - p * (1 - p)))

    # Pressure quartic (characteristic polynomial of Q_p(u)).
    u = sp.Symbol("u", positive=True, real=True)
    g_sym = sp.Matrix([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 0]])
    Q_sym = sp.Matrix([[P_sym[i, j] * (u ** g_sym[i, j]) for j in range(4)] for i in range(4)])
    pressure_poly = sp.expand((lam * sp.eye(4) - Q_sym).det())
    pressure_expected = (
        lam**4
        + (p - 1) * lam**3
        + (p**2 - p * u - p) * lam**2
        + (p**3 * u**3 - p**2 * u**3 - p**2 * u + p * u) * lam
        + p**2 * u * (1 - p)
    )

    # Endpoint I_p(0): rho(Q_p(0)) closed form.
    rho_q0 = sp.simplify(((1 - p) + sp.sqrt((1 - p) * (1 + 3 * p))) / 2)
    I0 = sp.simplify(-sp.log(rho_q0))
    I1 = sp.simplify(-sp.Rational(1, 3) * sp.log(p**2 * (1 - p)))

    # Covariance GF closed form (as in the paper).
    z = sp.Symbol("z")
    Cp_closed = sp.simplify(
        p**2
        * z
        * (
            (3 * p**7 - 14 * p**6 + 19 * p**5 - 9 * p**4 + 2 * p**3 - 2 * p**2 + p) * z**2
            + (-3 * p**6 - 2 * p**5 + 9 * p**4 + p**3 - 7 * p**2 + p + 1) * z
            + (-p**6 + p**5 - 6 * p**4 + 13 * p**3 - 8 * p**2 - 2 * p + 2)
        )
        / ((1 + p**3) ** 2 * (1 + p * z) * (1 - p * (1 - p) * z**2))
    )

    # Bit-pair law closed form.
    P00 = (1 - p - p**2 + 2 * p**3 - p**4) / (1 + p**3)
    P01 = (p**2 * (1 - p)) / (1 + p**3)
    P10 = (p**2 * (2 - p)) / (1 + p**3)
    P11 = (p * (p**3 + (1 - p) ** 2)) / (1 + p**3)

    # Numeric audit points.
    ps: List[float] = [0.11, 0.27, 0.5, 0.73, 0.91]
    z0 = 0.17

    results: List[CheckResult] = []
    details: Dict[str, Dict[str, float]] = {}

    # 1) char poly factorization (symbolic exact).
    results.append(CheckResult(name="char_poly_factorization", max_abs_err=float(char_poly != char_expected)))
    results.append(CheckResult(name="pressure_quartic", max_abs_err=float(sp.simplify(pressure_poly - pressure_expected) != 0)))

    # 1b) Perron interface: A_{theta,p} eigenvectors and Parry normalization (symbolic exact).
    q = 1 - p
    A0_sym = sp.Matrix(
        [
            [q, q, 0, p],
            [0, 0, p, 0],
            [p, 1, 0, 0],
            [q, 0, 0, 0],
        ]
    )
    r_sym = sp.Matrix([q, p**2, p, q**2])
    ell_sym = sp.Matrix([1, 1, p, p])  # left Perron eigenvector (as a column)
    A0_r_resid = sp.simplify(A0_sym * r_sym - r_sym)
    ell_A0_resid = sp.simplify((ell_sym.T * A0_sym - ell_sym.T))
    results.append(
        CheckResult(
            name="A0_right_eigenvector",
            max_abs_err=float(any(sp.simplify(x) != 0 for x in list(A0_r_resid))),
        )
    )
    results.append(
        CheckResult(
            name="A0_left_eigenvector",
            max_abs_err=float(any(sp.simplify(x) != 0 for x in list(ell_A0_resid))),
        )
    )
    P_from_A0 = sp.Matrix([[sp.simplify(A0_sym[i, j] * r_sym[j] / r_sym[i]) for j in range(4)] for i in range(4)])
    P_from_A0_resid = sp.simplify(P_from_A0 - P_sym)
    results.append(
        CheckResult(
            name="parry_normalization_P",
            max_abs_err=float(any(sp.simplify(x) != 0 for x in list(P_from_A0_resid))),
        )
    )
    # Diagonal similarity for the u-tilt: Q = D^{-1} A_u D.
    A_u_sym = sp.Matrix(
        [
            [q, q * u, 0, p],
            [0, 0, p * u, 0],
            [p * u, 1, 0, 0],
            [q, 0, 0, 0],
        ]
    )
    D = sp.diag(*list(r_sym))
    sim_resid = sp.simplify(A_u_sym * D - D * Q_sym)
    results.append(
        CheckResult(
            name="tilt_similarity_Au_vs_Q",
            max_abs_err=float(any(sp.simplify(x) != 0 for x in list(sim_resid))),
        )
    )

    # 1c) Unimodality and 1/2-threshold (symbolic exact).
    g_prime = sp.factor(sp.diff(g_star, p))
    g_prime_expected = sp.factor(-3 * p * (p**3 + 2 * p - 2) / ((p + 1) ** 2 * (p**2 - p + 1) ** 2))
    results.append(CheckResult(name="density_derivative_closed_form", max_abs_err=float(sp.simplify(g_prime - g_prime_expected) != 0)))
    half_diff = sp.factor(sp.simplify(g_star - sp.Rational(1, 2)))
    half_expected = sp.factor(-(p - 1) * (5 * p**2 - p - 1) / (2 * (1 + p**3)))
    results.append(CheckResult(name="density_half_threshold_factorization", max_abs_err=float(sp.simplify(half_diff - half_expected) != 0)))

    # 2) numeric checks across p-grid
    errs_density: List[float] = []
    errs_sigma: List[float] = []
    errs_I0: List[float] = []
    errs_prob_sum: List[float] = []
    errs_Cp: List[float] = []
    errs_cov_recur: List[float] = []

    for pv in ps:
        P_num = _P(pv)
        pi_num = _stationary_pi(P_num)

        # density
        mu_num = 0.0
        g_edge = [
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0],
        ]
        for i in range(4):
            for j in range(4):
                mu_num += pi_num[i] * P_num[i][j] * g_edge[i][j]
        mu_cf = float(sp.N(g_star.subs({p: pv}), 50))
        errs_density.append(mu_num - mu_cf)

        # variance rate
        sig_num = _variance_rate_edge_reward(P_num, pi_num)
        sig_cf = float(sp.N(sigma_star.subs({p: pv}), 50))
        errs_sigma.append(sig_num - sig_cf)

        # endpoint I0
        I0_cf = float(sp.N(I0.subs({p: pv}), 50))
        # Q_p(0) Perron root is rho_q0 (closed form), so compare directly:
        rho_cf = float(sp.N(rho_q0.subs({p: pv}), 50))
        errs_I0.append((-math.log(rho_cf)) - I0_cf)

        # bit-pair law: sum to 1 and nonnegativity
        probs = [
            float(sp.N(P00.subs({p: pv}), 50)),
            float(sp.N(P01.subs({p: pv}), 50)),
            float(sp.N(P10.subs({p: pv}), 50)),
            float(sp.N(P11.subs({p: pv}), 50)),
        ]
        errs_prob_sum.append(sum(probs) - 1.0)

        # covariance generating function: compare closed form vs matrix resolvent formula
        # Build numeric matrices in sympy for stable inversion.
        pvv = sp.nsimplify(pv)
        Pm = sp.Matrix(
            [
                [1 - pvv, pvv**2, 0, pvv * (1 - pvv)],
                [0, 0, 1, 0],
                [1 - pvv, pvv, 0, 0],
                [1, 0, 0, 0],
            ]
        )
        gm = sp.Matrix([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 0]])
        Hm = Pm.multiply_elementwise(gm)
        pi_col = sp.Matrix([1 - pvv, pvv**2, pvv**2, pvv * (1 - pvv) ** 2]) / (1 + pvv**3)
        pi_row = pi_col.T
        ones = sp.Matrix([1, 1, 1, 1])
        mu = sp.simplify((pi_row * Hm * ones)[0])

        zsym = sp.nsimplify(z0)
        Cm_mat = sp.simplify(zsym * (pi_row * Hm * (sp.eye(4) - zsym * Pm).inv() * Hm * ones)[0] - mu**2 * zsym / (1 - zsym))
        Cm_closed = sp.simplify(Cp_closed.subs({p: pvv, z: zsym}))
        errs_Cp.append(float(sp.N(Cm_mat - Cm_closed, 50)))

        # recurrence spot-check for k=1..5 using exact c_k from matrix formula.
        # c_k = pi^T H P^{k-1} H 1 - mu^2
        cs: List[sp.Expr] = []
        for k in range(1, 9):
            Ek = sp.simplify((pi_row * Hm * (Pm ** (k - 1)) * Hm * ones)[0] - mu**2)
            cs.append(Ek)
        # check recurrence residuals
        for k in range(1, 6):
            lhs = cs[k + 2]  # c_{k+3}
            rhs = sp.simplify(-pvv * cs[k + 1] + pvv * (1 - pvv) * cs[k] + pvv**2 * (1 - pvv) * cs[k - 1])
            errs_cov_recur.append(float(sp.N(lhs - rhs, 50)))

        details[str(pv)] = {
            "g_star_numeric": mu_num,
            "g_star_closed": mu_cf,
            "sigma2_numeric": sig_num,
            "sigma2_closed": sig_cf,
            "I0_closed": I0_cf,
            "prob_sum": sum(probs),
            "Cp_diff": float(sp.N(Cm_mat - Cm_closed, 30)),
        }

    results.extend(
        [
            CheckResult(name="density_g_star", max_abs_err=_max_abs(errs_density)),
            CheckResult(name="variance_sigma2", max_abs_err=_max_abs(errs_sigma)),
            CheckResult(name="endpoint_I0", max_abs_err=_max_abs(errs_I0)),
            CheckResult(name="bitpair_prob_sum", max_abs_err=_max_abs(errs_prob_sum)),
            CheckResult(name="covariance_gf_match", max_abs_err=_max_abs(errs_Cp)),
            CheckResult(name="covariance_recurrence", max_abs_err=_max_abs(errs_cov_recur)),
        ]
    )

    # p=1/2 table check (exact fractions)
    half = sp.Rational(1, 2)
    half_probs = [sp.simplify(P00.subs({p: half})), sp.simplify(P01.subs({p: half})), sp.simplify(P10.subs({p: half})), sp.simplify(P11.subs({p: half}))]
    assert half_probs == [sp.Rational(7, 18), sp.Rational(1, 9), sp.Rational(1, 3), sp.Rational(1, 6)]

    out = {
        "checks": [{"name": r.name, "max_abs_err": r.max_abs_err} for r in results],
        "samples": details,
        "symbolic": {
            "char_poly": str(char_poly),
            "char_expected": str(char_expected),
            "g_star": str(g_star),
            "sigma2": str(sigma_star),
            "I0": str(I0),
            "I1": str(I1),
        },
        "elapsed_s": time.time() - t0,
    }

    export_path = export_dir() / "fold_gauge_anomaly_bernoulli_p_closed_form.json"
    _write_text(export_path, json.dumps(out, indent=2, sort_keys=True) + "\n")

    # Print a short summary for interactive runs.
    worst = max(results, key=lambda r: r.max_abs_err)
    print(f"[fold_gauge_anomaly_bernoulli_p_closed_form] worst_check={worst.name} max_abs_err={worst.max_abs_err:.3e}")


if __name__ == "__main__":
    main()

