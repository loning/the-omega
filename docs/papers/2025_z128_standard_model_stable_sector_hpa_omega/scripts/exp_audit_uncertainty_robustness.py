# -*- coding: utf-8 -*-
"""
Uncertainty robustness audit for bounded-complexity closures.

We test whether the *selected minimizer* for each closure is stable under
perturbations of the reference targets within a prescribed uncertainty model.

This is an audit-oriented stress test (not a statistical claim about PDG/CODATA):
  - sampling is deterministic (fixed RNG seed),
  - uncertainty bands are explicit in code,
  - for each sample we recompute the minimizer under the same tie-break rules.

Outputs (LaTeX fragment):
  - sections/generated/audit_uncertainty_robustness_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Tuple

import exp_ckm_mixing_depth_rigidity as ckm
import exp_mass_depth_rigidity as mdr
import exp_pmns_matrix_closure as pmns_mat
import exp_pmns_mixing_depth_rigidity as pmns
from common_constants import (
    ALPHAZ_INV_PDG,
    ALPHA_INV_CODATA_2022,
    JARLSKOG_PDG_CENTRAL,
    PMNS_DELTA_REF_DEG,
    PMNS_DELTA_SIGMA_DEG,
    PMNS_SIN2_T12_REF,
    PMNS_SIN2_T12_SIGMA,
    PMNS_SIN2_T13_REF,
    PMNS_SIN2_T13_SIGMA,
    PMNS_SIN2_T23_REF,
    PMNS_SIN2_T23_SIGMA,
    SIN2_THETAW_PDG,
)


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        raise ValueError("abs_log_ratio requires positive arguments.")
    return abs(math.log(pred / ref))


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def alpha_em_minimizer(alpha_inv_ref: float) -> Tuple[int, int, int]:
    best: Tuple[float, int, int, int, int] | None = None  # (e,sum,a,b,c)
    for a in range(0, 11):
        for b in range(0, 11 - a):
            for c in range(0, 11 - a - b):
                if a == 0 and b == 0 and c == 0:
                    continue
                pred = float(a) * (math.pi**3) + float(b) * (math.pi**2) + float(c) * math.pi
                e = abs_log_ratio(pred, alpha_inv_ref)
                cand = (e, a + b + c, a, b, c)
                if best is None or cand < best:
                    best = cand
    if best is None:
        raise AssertionError("No candidates enumerated for alpha_em.")
    _e, _s, a, b, c = best
    return a, b, c


def alphaZ_minimizer(alphaZ_inv_ref: float) -> int:
    best: Tuple[float, int] | None = None
    for n in range(1, 51):
        pred = float(n) * (math.pi**2)
        e = abs_log_ratio(pred, alphaZ_inv_ref)
        cand = (e, n)
        if best is None or cand < best:
            best = cand
    if best is None:
        raise AssertionError("No candidates enumerated for alphaZ.")
    return best[1]


def sin2_minimizer(sin2_ref: float) -> Tuple[int, int]:
    best: Tuple[float, int, int] | None = None  # (e,q,p)
    for q in range(1, 51):
        for p in range(1, q):
            if _gcd(p, q) != 1:
                continue
            pred = float(p) / float(q)
            e = abs_log_ratio(pred, sin2_ref)
            cand = (e, q, p)
            if best is None or cand < best:
                best = cand
    if best is None:
        raise AssertionError("No candidates enumerated for sin2.")
    _e, q, p = best
    return p, q


def jarlskog_minimizer(J_ref: float) -> Tuple[int, int]:
    best: Tuple[float, int, int, int] | None = None  # (e, a+n, a, n)
    for a in range(1, 51):
        for n in range(1, 21):
            pred = 1.0 / (float(a) * (math.pi ** float(n)))
            e = abs_log_ratio(pred, J_ref)
            cand = (e, a + n, a, n)
            if best is None or cand < best:
                best = cand
    if best is None:
        raise AssertionError("No candidates enumerated for J.")
    _e, _c, a, n = best
    return a, n


def ckm_magnitude_minimizer(vus: float, vcb: float, vub: float) -> Tuple[int, int, int]:
    vmax = ckm.v_max_x6()
    best = ckm.best_triple_at_B(B=20, vus_ref=vus, vcb_ref=vcb, vub_ref=vub, vmax=vmax)
    return best.m, best.k23, best.k13


def pmns_magnitude_minimizer(s12: float, s23: float, s13: float) -> Tuple[int, int, int, int, int]:
    best = pmns.best_triple_at_B(B=20, s12_ref=s12, s23_ref=s23, s13_ref=s13)
    return best.p12, best.q12, best.p23, best.q23, best.k13


def pmns_delta_minimizer(s12: float, s23: float, s13: float, delta_ref_deg: float) -> float:
    """
    Discrete delta closure used by exp_pmns_matrix_closure.py, expressed as a minimizer.
    """
    delta_ref = float(delta_ref_deg) * math.pi / 180.0
    J_ref = pmns_mat.J_from_angles(s12, s23, s13, delta_ref)
    # Match the quadrant of the reference phase via sign(cos delta_ref).
    c = math.cos(delta_ref)
    cos_ref_sign = 0 if c == 0.0 else (1 if c > 0.0 else -1)
    # Use the same bounded-denominator candidate family as the main PMNS closure.
    Q_MAX = 12
    cands = pmns_mat.delta_candidates_bounded_denominator(Q_MAX)
    best = pmns_mat.select_delta_discrete(s12=s12, s23=s23, s13=s13, J_ref=J_ref, cos_ref_sign=cos_ref_sign, candidates=cands)
    return float(best.delta)


def mass_depth_minimizer() -> Callable[[float, float], Tuple[int, int, int]]:
    """
    Return a minimizer function for the mass-depth rigidity closure at B=20,
    parametrized by (mu_ref, tau_ref) reference masses in GeV.
    """
    B = 20
    m_e = 5.1099895e-4
    anchors = [
        ("mu", 1.0565838e-1),
        ("tau", 1.77686),
    ]
    word_for = mdr.build_word_for_field()
    w_e = word_for[(1, "e_R")]
    V_e, g_e, wt_e = mdr.invariants_for_word(w_e)
    anchor_words = {
        "mu": word_for[(2, "e_R")],
        "tau": word_for[(3, "e_R")],
    }
    anchor_inv = {}
    for name, _mu in anchors:
        w = anchor_words[name]
        V, g, wt = mdr.invariants_for_word(w)
        anchor_inv[name] = (V - V_e, g - g_e, wt - wt_e)

    def solve(mu_ref: float, tau_ref: float) -> Tuple[int, int, int]:
        r_mu = mdr.r_of_mu(mu_ref, m_e)
        r_tau = mdr.r_of_mu(tau_ref, m_e)
        dV_mu, dg_mu, dwt_mu = anchor_inv["mu"]
        dV_tau, dg_tau, dwt_tau = anchor_inv["tau"]

        best: Tuple[float, float, int, int, int, int] | None = None  # (maxe,sume,mc,as,a,b,c)
        for a in range(-B, B + 1):
            for b in range(-B, B + 1):
                for c in range(-B, B + 1):
                    if a == 0 and b == 0 and c == 0:
                        continue
                    # avoid duplicates under global sign flip
                    if a < 0:
                        continue
                    if a == 0 and b < 0:
                        continue
                    if a == 0 and b == 0 and c < 0:
                        continue

                    rhat_mu = float(a * dV_mu + b * dg_mu + c * dwt_mu)
                    rhat_tau = float(a * dV_tau + b * dg_tau + c * dwt_tau)
                    e_mu = abs(rhat_mu - r_mu) * math.log((1.0 + math.sqrt(5.0)) / 2.0)
                    e_tau = abs(rhat_tau - r_tau) * math.log((1.0 + math.sqrt(5.0)) / 2.0)
                    maxe = max(e_mu, e_tau)
                    sume = e_mu + e_tau
                    mc = max(abs(a), abs(b), abs(c))
                    asum = abs(a) + abs(b) + abs(c)
                    cand = (maxe, sume, mc, asum, a, b, c)
                    if best is None or cand < best:
                        best = cand
        if best is None:
            raise AssertionError("No candidates enumerated for mass-depth minimizer.")
        _maxe, _sume, _mc, _as, a, b, c = best
        return int(a), int(b), int(c)

    return solve


@dataclass(frozen=True)
class Row:
    name: str
    sigma_tex: str
    samples: int
    baseline_tex: str
    stability: float


def truncated_normal(rng: random.Random, mu: float, sigma: float, lo: float, hi: float) -> float:
    for _ in range(10000):
        x = rng.gauss(mu, sigma)
        if lo <= x <= hi:
            return x
    # Fallback: clamp (should not happen in typical settings).
    return max(lo, min(hi, mu))


def main() -> None:
    rng = random.Random(0)
    N = 200

    rows: List[Row] = []

    # alpha_em^{-1} (CODATA-like): alpha_inv_ref ± 2.1e-8 (CODATA 2018/2022-style).
    alpha_sigma = 2.1e-8
    base_alpha = alpha_em_minimizer(ALPHA_INV_CODATA_2022)
    stable = 0
    for _ in range(N):
        ref = rng.gauss(ALPHA_INV_CODATA_2022, alpha_sigma)
        if alpha_em_minimizer(ref) == base_alpha:
            stable += 1
    rows.append(
        Row(
            name=r"$\alpha_{\mathrm{em}}^{-1}$",
            sigma_tex=r"$\sigma=2.1\times 10^{-8}$",
            samples=N,
            baseline_tex=f"$({base_alpha[0]},{base_alpha[1]},{base_alpha[2]})$",
            stability=float(stable) / float(N),
        )
    )

    # alpha^{-1}(mu_Z): heuristic sigma.
    alphaZ_sigma = 1.0e-2
    base_alphaZ = alphaZ_minimizer(ALPHAZ_INV_PDG)
    stable = 0
    for _ in range(N):
        ref = rng.gauss(ALPHAZ_INV_PDG, alphaZ_sigma)
        if alphaZ_minimizer(ref) == base_alphaZ:
            stable += 1
    rows.append(
        Row(
            name=r"$\alpha^{-1}(\mu_Z)$",
            sigma_tex=r"$\sigma=10^{-2}$",
            samples=N,
            baseline_tex=f"$n={base_alphaZ}$",
            stability=float(stable) / float(N),
        )
    )

    # sin^2(theta_W): heuristic sigma.
    sin2_sigma = 3.0e-5
    base_sin2 = sin2_minimizer(SIN2_THETAW_PDG)
    stable = 0
    for _ in range(N):
        ref = truncated_normal(rng, SIN2_THETAW_PDG, sin2_sigma, lo=1e-6, hi=1.0 - 1e-6)
        if sin2_minimizer(ref) == base_sin2:
            stable += 1
    rows.append(
        Row(
            name=r"$\sin^2\theta_W(\mu_Z)$",
            sigma_tex=r"$\sigma=3\times 10^{-5}$",
            samples=N,
            baseline_tex=f"${base_sin2[0]}/{base_sin2[1]}$",
            stability=float(stable) / float(N),
        )
    )

    # CKM J: use the paper-quoted PDG uncertainty (3.00 ± 0.15)×10^{-5}.
    J_sigma = 0.15e-5
    base_J = jarlskog_minimizer(JARLSKOG_PDG_CENTRAL)
    stable = 0
    for _ in range(N):
        ref = truncated_normal(rng, JARLSKOG_PDG_CENTRAL, J_sigma, lo=1e-12, hi=1.0)
        if jarlskog_minimizer(ref) == base_J:
            stable += 1
    rows.append(
        Row(
            name=r"$J$ (CKM)",
            sigma_tex=r"$\sigma=1.5\times 10^{-6}$",
            samples=N,
            baseline_tex=f"$({base_J[0]},{base_J[1]})$",
            stability=float(stable) / float(N),
        )
    )

    # CKM magnitudes: representative sigma values.
    vus_mu, vus_sigma = 0.2243, 5.0e-4
    vcb_mu, vcb_sigma = 0.0422, 8.0e-4
    vub_mu, vub_sigma = 0.00394, 3.6e-4
    base_ckm = ckm_magnitude_minimizer(vus_mu, vcb_mu, vub_mu)
    stable = 0
    for _ in range(N):
        vus = truncated_normal(rng, vus_mu, vus_sigma, lo=1e-6, hi=1.0)
        vcb = truncated_normal(rng, vcb_mu, vcb_sigma, lo=1e-6, hi=1.0)
        vub = truncated_normal(rng, vub_mu, vub_sigma, lo=1e-6, hi=1.0)
        if ckm_magnitude_minimizer(vus, vcb, vub) == base_ckm:
            stable += 1
    rows.append(
        Row(
            name=r"CKM magnitudes",
            sigma_tex=r"$\sigma=(5,8,36)\times 10^{-4}$",
            samples=N,
            baseline_tex=f"$({base_ckm[0]},{base_ckm[1]},{base_ckm[2]})$",
            stability=float(stable) / float(N),
        )
    )

    # PMNS sines: representative sigma on sin^2 values.
    sin2_t12_mu, sin2_t12_sigma = PMNS_SIN2_T12_REF, PMNS_SIN2_T12_SIGMA
    sin2_t23_mu, sin2_t23_sigma = PMNS_SIN2_T23_REF, PMNS_SIN2_T23_SIGMA
    sin2_t13_mu, sin2_t13_sigma = PMNS_SIN2_T13_REF, PMNS_SIN2_T13_SIGMA
    s12_mu = math.sqrt(sin2_t12_mu)
    s23_mu = math.sqrt(sin2_t23_mu)
    s13_mu = math.sqrt(sin2_t13_mu)
    base_pmns = pmns_magnitude_minimizer(s12_mu, s23_mu, s13_mu)
    stable = 0
    for _ in range(N):
        s2_12 = truncated_normal(rng, sin2_t12_mu, sin2_t12_sigma, lo=1e-8, hi=1.0 - 1e-8)
        s2_23 = truncated_normal(rng, sin2_t23_mu, sin2_t23_sigma, lo=1e-8, hi=1.0 - 1e-8)
        s2_13 = truncated_normal(rng, sin2_t13_mu, sin2_t13_sigma, lo=1e-10, hi=1.0 - 1e-10)
        s12 = math.sqrt(s2_12)
        s23 = math.sqrt(s2_23)
        s13 = math.sqrt(s2_13)
        if pmns_magnitude_minimizer(s12, s23, s13) == base_pmns:
            stable += 1
    rows.append(
        Row(
            name=r"PMNS sines",
            sigma_tex=rf"$\sigma(\sin^2\theta)=({sin2_t12_sigma:.3g},{sin2_t23_sigma:.3g},{sin2_t13_sigma:.3g})$",
            samples=N,
            baseline_tex=rf"$(p_{{12}}/q_{{12}},p_{{23}}/q_{{23}},k_{{13}})=({base_pmns[0]}/{base_pmns[1]},{base_pmns[2]}/{base_pmns[3]},{base_pmns[4]})$",
            stability=float(stable) / float(N),
        )
    )

    # PMNS delta (Dirac phase): dyadic sign-anchored discrete closure.
    # We perturb delta_ref in degrees under a truncated-normal model on [0,360].
    delta_mu = PMNS_DELTA_REF_DEG
    delta_sigma = PMNS_DELTA_SIGMA_DEG
    base_delta = pmns_delta_minimizer(s12_mu, s23_mu, s13_mu, delta_ref_deg=delta_mu)
    stable = 0
    for _ in range(N):
        d = truncated_normal(rng, delta_mu, delta_sigma, lo=0.0, hi=360.0)
        if pmns_delta_minimizer(s12_mu, s23_mu, s13_mu, delta_ref_deg=d) == base_delta:
            stable += 1
    base_deg = base_delta * 180.0 / math.pi
    rows.append(
        Row(
            name=r"PMNS $\delta$ (bounded denom.)",
            sigma_tex=rf"$\sigma_\delta={delta_sigma:.0f}^\circ$",
            samples=N,
            baseline_tex=rf"$\delta={base_deg:.0f}^\circ$",
            stability=float(stable) / float(N),
        )
    )

    # Mass depth rigidity (leptons): perturb mu and tau reference masses (GeV) by a small relative sigma.
    solve_depth = mass_depth_minimizer()
    mu0, tau0 = 1.0565838e-1, 1.77686
    rel_sigma = 5.0e-4  # 0.05% (audit stress test)
    base_depth = solve_depth(mu0, tau0)
    stable = 0
    for _ in range(N):
        mu_ref = truncated_normal(rng, mu0, rel_sigma * mu0, lo=1e-9, hi=1e3)
        tau_ref = truncated_normal(rng, tau0, rel_sigma * tau0, lo=1e-9, hi=1e3)
        if solve_depth(mu_ref, tau_ref) == base_depth:
            stable += 1
    rows.append(
        Row(
            name=r"mass depth (leptons)",
            sigma_tex=r"$\sigma/\mu=5\times 10^{-4}$",
            samples=N,
            baseline_tex=f"$({base_depth[0]},{base_depth[1]},{base_depth[2]})$",
            stability=float(stable) / float(N),
        )
    )

    # Write LaTeX rows.
    out_rows: List[str] = []
    for r in rows:
        out_rows.append(
            f"{r.name} & {r.sigma_tex} & {r.samples} & {r.baseline_tex} & {r.stability:.3f} \\\\"
        )
    out_rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit_uncertainty_robustness_rows.tex").write_text("\n".join(out_rows), encoding="utf-8")
    print("Wrote sections/generated/audit_uncertainty_robustness_rows.tex")


if __name__ == "__main__":
    main()


