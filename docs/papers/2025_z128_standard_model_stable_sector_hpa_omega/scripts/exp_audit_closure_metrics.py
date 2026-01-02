# -*- coding: utf-8 -*-
"""
Audit metrics for bounded-complexity closures used across the paper.

This script produces *auditable* "look-elsewhere" context for several closures:
  - alpha_em^{-1} coefficient rigidity (a*pi^3 + b*pi^2 + c*pi)
  - electroweak alpha^{-1}(mu_Z) ~ n*pi^2 and sin^2(theta_W) ~ p/q
  - CKM Jarlskog rigidity J ~ 1/(a*pi^n)
  - CKM magnitude closure (m,k23,k13) at B=20
  - PMNS mixing-sine closure (p12/q12, p23/q23, k13) at B=20
  - PMNS Dirac-phase closure delta = (k*pi)/q at Q=12 (bounded denominator, sign/quadrant anchored)
  - Mass-depth rigidity (a,b,c) at B=20

We summarize, for each closure:
  - candidate-domain size |Theta|
  - best and second-best max abs log mismatch E_inf
  - a simple gap (second - best)
  - counts of candidates within two fixed mismatch thresholds (<=1%, <=5%)

We also report E_inf distribution quantiles for the two large-domain closures
(CKM magnitudes, PMNS sines, and mass-depth rigidity) at B=20.

Outputs (LaTeX fragments):
  - sections/generated/audit_closure_metrics_rows.tex
  - sections/generated/audit_closure_quantiles_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import exp_ckm_mixing_depth_rigidity as ckm
import exp_mass_depth_rigidity as mdr
import exp_pmns_matrix_closure as pmns_mat
import exp_pmns_mixing_depth_rigidity as pmns
from common_constants import PMNS_DELTA_REF_DEG, PMNS_SIN2_T12_REF, PMNS_SIN2_T13_REF, PMNS_SIN2_T23_REF


PHI = (1.0 + math.sqrt(5.0)) / 2.0
LOG_PHI = math.log(PHI)


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        raise ValueError("abs_log_ratio requires positive arguments.")
    return abs(math.log(pred / ref))


def quantile(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        raise ValueError("quantile requires a non-empty list.")
    if not (0.0 <= q <= 1.0):
        raise ValueError("q must be in [0,1].")
    n = len(sorted_vals)
    idx = int(round(q * float(n - 1)))
    return sorted_vals[idx]


@dataclass(frozen=True)
class MetricRow:
    name: str
    family_tex: str
    domain_size: int
    best_params_tex: str
    best_e: float
    second_e: float
    count_le_001: int
    count_le_005: int


def _best_two_by_key(candidates: Iterable[Tuple[Tuple, float]]) -> Tuple[Tuple, float, Tuple, float]:
    """
    Given candidates as (key, e_inf), return (best_key,best_e, second_key,second_e),
    where ordering is by key.
    """
    best: Optional[Tuple[Tuple, float]] = None
    second: Optional[Tuple[Tuple, float]] = None
    for key, e in candidates:
        if best is None or key < best[0]:
            second = best
            best = (key, e)
        elif key != best[0]:
            if second is None or key < second[0]:
                second = (key, e)
    if best is None or second is None:
        raise AssertionError("Need at least two distinct candidates.")
    return best[0], best[1], second[0], second[1]


def audit_alpha_em() -> MetricRow:
    # CODATA 2022 recommended inverse fine-structure constant (dimensionless).
    # Reference value used as a fixed audit target (PDG/CODATA conventions).
    alpha_inv_ref = 137.035999084

    # Candidate family: a*pi^3 + b*pi^2 + c*pi with a,b,c>=0 and a+b+c<=10.
    cand: List[Tuple[Tuple, float]] = []
    e_vals: List[float] = []
    for a in range(0, 11):
        for b in range(0, 11 - a):
            for c in range(0, 11 - a - b):
                if a == 0 and b == 0 and c == 0:
                    continue
                pred = float(a) * (math.pi**3) + float(b) * (math.pi**2) + float(c) * math.pi
                e = abs_log_ratio(pred, alpha_inv_ref)
                # Deterministic tie-break: minimize e, then (a+b+c), then lexicographic (a,b,c).
                key = (e, a + b + c, a, b, c)
                cand.append((key, e))
                e_vals.append(e)
    best_key, best_e, second_key, second_e = _best_two_by_key(cand)
    _e, _sum, a, b, c = best_key
    best_params_tex = f"$({a},{b},{c})$"

    le001 = sum(1 for e in e_vals if e <= 0.01)
    le005 = sum(1 for e in e_vals if e <= 0.05)
    return MetricRow(
        name=r"$\alpha_{\mathrm{em}}^{-1}$",
        family_tex=r"$a\pi^3+b\pi^2+c\pi,\ a{+}b{+}c\le 10$",
        domain_size=len(e_vals),
        best_params_tex=best_params_tex,
        best_e=best_e,
        second_e=second_e,
        count_le_001=le001,
        count_le_005=le005,
    )


def audit_alpha_Z() -> MetricRow:
    # PDG reference value used in the paper (dimensionless).
    alphaZ_inv_ref = 127.955
    cand: List[Tuple[Tuple, float]] = []
    e_vals: List[float] = []
    for n in range(1, 51):
        pred = float(n) * (math.pi**2)
        e = abs_log_ratio(pred, alphaZ_inv_ref)
        key = (e, n)
        cand.append((key, e))
        e_vals.append(e)
    best_key, best_e, second_key, second_e = _best_two_by_key(cand)
    _e, n = best_key
    best_params_tex = f"$n={n}$"
    return MetricRow(
        name=r"$\alpha^{-1}(\mu_Z)$",
        family_tex=r"$n\pi^2,\ 1\le n\le 50$",
        domain_size=len(e_vals),
        best_params_tex=best_params_tex,
        best_e=best_e,
        second_e=second_e,
        count_le_001=sum(1 for e in e_vals if e <= 0.01),
        count_le_005=sum(1 for e in e_vals if e <= 0.05),
    )


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def audit_sin2_thetaW() -> MetricRow:
    sin2_ref = 0.23122
    cand: List[Tuple[Tuple, float]] = []
    e_vals: List[float] = []
    # Candidate family: reduced rationals p/q, 1<=q<=50, 0<p<q.
    for q in range(1, 51):
        for p in range(1, q):
            if _gcd(p, q) != 1:
                continue
            pred = float(p) / float(q)
            e = abs_log_ratio(pred, sin2_ref)
            # Tie-break: minimize e, then denominator q, then numerator p.
            key = (e, q, p)
            cand.append((key, e))
            e_vals.append(e)
    best_key, best_e, second_key, second_e = _best_two_by_key(cand)
    _e, q, p = best_key
    best_params_tex = f"${p}/{q}$"
    return MetricRow(
        name=r"$\sin^2\theta_W(\mu_Z)$",
        family_tex=r"$p/q,\ 1\le q\le 50$",
        domain_size=len(e_vals),
        best_params_tex=best_params_tex,
        best_e=best_e,
        second_e=second_e,
        count_le_001=sum(1 for e in e_vals if e <= 0.01),
        count_le_005=sum(1 for e in e_vals if e <= 0.05),
    )


def audit_jarlskog() -> MetricRow:
    J_ref = 3.00e-5
    cand: List[Tuple[Tuple, float]] = []
    e_vals: List[float] = []
    for a in range(1, 51):
        for n in range(1, 21):
            pred = 1.0 / (float(a) * (math.pi ** float(n)))
            e = abs_log_ratio(pred, J_ref)
            # Tie-break: minimize e, then a+n, then (a,n).
            key = (e, a + n, a, n)
            cand.append((key, e))
            e_vals.append(e)
    best_key, best_e, second_key, second_e = _best_two_by_key(cand)
    _e, _comp, a, n = best_key
    best_params_tex = f"$({a},{n})$"
    return MetricRow(
        name=r"$J$ (CKM)",
        family_tex=r"$1/(a\pi^n),\ a\le 50,\ n\le 20$",
        domain_size=len(e_vals),
        best_params_tex=best_params_tex,
        best_e=best_e,
        second_e=second_e,
        count_le_001=sum(1 for e in e_vals if e <= 0.01),
        count_le_005=sum(1 for e in e_vals if e <= 0.05),
    )


def audit_ckm_magnitudes_B20() -> Tuple[MetricRow, List[float]]:
    # PDG reference magnitudes used by exp_ckm_mixing_depth_rigidity.py.
    vus_ref = 0.2243
    vcb_ref = 0.0422
    vub_ref = 0.00394

    vmax = ckm.v_max_x6()
    if vmax != 20:
        raise AssertionError(f"Expected V_max(X6)=20, got {vmax}.")

    B = 20
    m_max = min(B, vmax)
    k_max = 2 * B

    e_list: List[float] = []
    cand: List[Tuple[Tuple, float]] = []
    for m in range(1, m_max + 1):
        for k23 in range(1, k_max + 1):
            for k13 in range(1, k_max + 1):
                maxe, sume = ckm.triple_objective(m, k23, k13, vus_ref, vcb_ref, vub_ref)
                comp = m + k23 + k13
                key = (maxe, sume, comp, m, k23, k13)
                cand.append((key, maxe))
                e_list.append(maxe)

    best_key, best_e, second_key, second_e = _best_two_by_key(cand)
    _maxe, _sume, _comp, m, k23, k13 = best_key
    best_params_tex = f"$(m,k_{{23}},k_{{13}})=({m},{k23},{k13})$"

    return (
        MetricRow(
            name=r"CKM magnitudes",
            family_tex=r"$|V_{us}|{=}1/\sqrt{m},\ |V_{cb}|{=}\varphi^{-k_{23}/2},\ |V_{ub}|{=}\varphi^{-k_{13}/2}$",
            domain_size=len(e_list),
            best_params_tex=best_params_tex,
            best_e=best_e,
            second_e=second_e,
            count_le_001=sum(1 for e in e_list if e <= 0.01),
            count_le_005=sum(1 for e in e_list if e <= 0.05),
        ),
        e_list,
    )


def audit_pmns_sines_B20() -> Tuple[MetricRow, List[float]]:
    # Reference targets (sines of angles), consistent with exp_pmns_mixing_depth_rigidity.py.
    s12_ref = math.sqrt(PMNS_SIN2_T12_REF)
    s23_ref = math.sqrt(PMNS_SIN2_T23_REF)
    s13_ref = math.sqrt(PMNS_SIN2_T13_REF)

    B = 20
    k_max = 2 * B
    cand12 = pmns.rational_sine_candidates(B)
    cand23 = pmns.rational_sine_candidates(B)

    e_list: List[float] = []
    cand: List[Tuple[Tuple, float]] = []
    for p12, q12, s12 in cand12:
        for p23, q23, s23 in cand23:
            for k13 in range(1, k_max + 1):
                maxe, sume = pmns.triple_objective(s12, s23, k13, s12_ref, s23_ref, s13_ref)
                comp1 = q12 + q23 + k13
                comp2 = p12 + p23
                # Tie-break compatible with exp_pmns_mixing_depth_rigidity.py.
                key = (maxe, sume, comp1, comp2, q12, p12, q23, p23, k13)
                cand.append((key, maxe))
                e_list.append(maxe)

    best_key, best_e, _second_key, second_e = _best_two_by_key(cand)
    _maxe, _sume, _c1, _c2, q12, p12, q23, p23, k13 = best_key
    best_params_tex = rf"$(p_{{12}}/q_{{12}},p_{{23}}/q_{{23}},k_{{13}})=({p12}/{q12},{p23}/{q23},{k13})$"
    return (
        MetricRow(
            name=r"PMNS sines",
            family_tex=r"$s_{12}{=}\sqrt{p_{12}/q_{12}},\ s_{23}{=}\sqrt{p_{23}/q_{23}},\ s_{13}{=}\varphi^{-k_{13}/2}$",
            domain_size=len(e_list),
            best_params_tex=best_params_tex,
            best_e=best_e,
            second_e=second_e,
            count_le_001=sum(1 for e in e_list if e <= 0.01),
            count_le_005=sum(1 for e in e_list if e <= 0.05),
        ),
        e_list,
    )


def _sgn(x: float) -> int:
    if x > 0.0:
        return 1
    if x < 0.0:
        return -1
    return 0


def audit_pmns_delta_Q12() -> MetricRow:
    """
    Audit the bounded-denominator delta-closure used in exp_pmns_matrix_closure.py.
    We treat the CP-odd sign and quadrant anchors as constraints and measure mismatch
    by eJ := |log(|J_pred|/|J_ref|)|.
    """
    # Reference reconstruction (global-fit style inputs).
    s12_ref = math.sqrt(PMNS_SIN2_T12_REF)
    s23_ref = math.sqrt(PMNS_SIN2_T23_REF)
    s13_ref = math.sqrt(PMNS_SIN2_T13_REF)
    delta_ref = float(PMNS_DELTA_REF_DEG) * math.pi / 180.0
    cos_ref_sign = _sgn(math.cos(delta_ref))
    J_ref = pmns_mat.J_from_angles(s12_ref, s23_ref, s13_ref, delta_ref)

    # Closed predicted angles from the PMNS sines closure at B=20.
    best20 = pmns.best_triple_at_B(B=20, s12_ref=s12_ref, s23_ref=s23_ref, s13_ref=s13_ref)
    s12_pred = math.sqrt(float(best20.p12) / float(best20.q12))
    s23_pred = math.sqrt(float(best20.p23) / float(best20.q23))
    s13_pred = PHI ** (-0.5 * float(best20.k13))

    Q = 12
    cands = pmns_mat.delta_candidates_bounded_denominator(Q)

    e_list: List[float] = []
    cand: List[Tuple[Tuple, float]] = []
    for c in cands:
        Jp = pmns_mat.J_from_angles(s12_pred, s23_pred, s13_pred, c.delta)
        if _sgn(Jp) != _sgn(J_ref):
            continue
        if _sgn(math.cos(c.delta)) != cos_ref_sign:
            continue
        eJ = abs_log_ratio(abs(Jp), abs(J_ref)) if (Jp != 0.0 and J_ref != 0.0) else float("inf")
        key = (eJ, c.q, c.k)
        cand.append((key, eJ))
        e_list.append(eJ)

    best_key, best_e, _second_key, second_e = _best_two_by_key(cand)
    _eJ, q, k = best_key
    best_params_tex = rf"$\delta={k}\pi/{q}$"
    return MetricRow(
        name=r"PMNS $\delta$",
        family_tex=r"$\delta=k\pi/q,\ 1\le q\le 12$",
        domain_size=len(cands),
        best_params_tex=best_params_tex,
        best_e=best_e,
        second_e=second_e,
        count_le_001=sum(1 for e in e_list if e <= 0.01),
        count_le_005=sum(1 for e in e_list if e <= 0.05),
    )


def audit_mass_depth_B20() -> Tuple[MetricRow, List[float]]:
    # Reproduce the candidate enumeration domain used in exp_mass_depth_rigidity.py at B=20,
    # but compute the primary objective as a log-mismatch on the {mu, tau} anchors.
    #
    # Error in r-coordinate: |r_ref - r_hat|; convert to log mismatch in mu:
    #   |log(mu_pred/mu_ref)| = |r_hat - r_ref| * log(phi).
    B = 20

    # Scheme-stable reference masses (GeV).
    m_e = 5.1099895e-4
    anchors = [
        ("mu", 1.0565838e-1),
        ("tau", 1.77686),
    ]

    word_for = mdr.build_word_for_field()
    w_e = word_for[(1, "e_R")]
    V_e, g_e, wt_e = mdr.invariants_for_word(w_e)

    # Map anchors to stable words under the closed labeling map.
    anchor_words = {
        "mu": word_for[(2, "e_R")],
        "tau": word_for[(3, "e_R")],
    }

    anchor_depths: List[Tuple[str, float, Tuple[int, int, int]]] = []
    for name, mu in anchors:
        w = anchor_words[name]
        r_ref = mdr.r_of_mu(mu, m_e)
        inv = mdr.invariants_for_word(w)
        anchor_depths.append((name, r_ref, inv))

    e_list: List[float] = []
    cand: List[Tuple[Tuple, float]] = []
    for a in range(-B, B + 1):
        for b in range(-B, B + 1):
            for c in range(-B, B + 1):
                if a == 0 and b == 0 and c == 0:
                    continue
                # Same sign convention as exp_mass_depth_rigidity.py (avoid duplicates under global sign flip).
                if a < 0:
                    continue
                if a == 0 and b < 0:
                    continue
                if a == 0 and b == 0 and c < 0:
                    continue

                errs_lep: List[float] = []
                for _name, r_ref, inv in anchor_depths:
                    V, g, wt = inv
                    dV = V - V_e
                    dg = g - g_e
                    dwt = wt - wt_e
                    r_hat = a * dV + b * dg + c * dwt
                    # Convert to log mismatch in mu:
                    errs_lep.append(abs(float(r_hat) - r_ref) * LOG_PHI)

                maxe = max(errs_lep)
                sume = sum(errs_lep)
                max_coeff = max(abs(a), abs(b), abs(c))
                abs_sum = abs(a) + abs(b) + abs(c)

                # Tie-break compatible with the paper's rigidity certificate:
                # primary: minimax on leptons, then sum on leptons, then coefficient complexity, then lexical.
                key = (maxe, sume, float(max_coeff), float(abs_sum), float(a), float(b), float(c))
                cand.append((key, maxe))
                e_list.append(maxe)

    best_key, best_e, second_key, second_e = _best_two_by_key(cand)
    _maxe, _sume, _mc, _as, a, b, c = best_key
    best_params_tex = f"$({int(a)},{int(b)},{int(c)})$"
    return (
        MetricRow(
            name=r"mass depth (leptons)",
            family_tex=r"$\widehat r=a\,\Delta V+b\,\Delta g+c\,\Delta|w|_1,\ |a|,|b|,|c|\le 20$",
            domain_size=len(e_list),
            best_params_tex=best_params_tex,
            best_e=best_e,
            second_e=second_e,
            count_le_001=sum(1 for e in e_list if e <= 0.01),
            count_le_005=sum(1 for e in e_list if e <= 0.05),
        ),
        e_list,
    )


def write_outputs(rows: List[MetricRow], quantiles: List[Tuple[str, List[float]]]) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Table rows for closure metrics.
    lines: List[str] = []
    for r in rows:
        gap = r.second_e - r.best_e
        lines.append(
            f"{r.name} & {r.family_tex} & {r.domain_size} & {r.best_params_tex} & {r.best_e:.6g} & {r.second_e:.6g} & {gap:.3g} & {r.count_le_001} & {r.count_le_005} \\\\"
        )
    lines.append("\\bottomrule")
    (out_dir / "audit_closure_metrics_rows.tex").write_text("\n".join(lines), encoding="utf-8")

    # Quantile rows for large-domain closures.
    q_lines: List[str] = []
    for name, e_list in quantiles:
        s = sorted(e_list)
        q_lines.append(
            f"{name} & {len(s)} & {quantile(s, 0.0):.6g} & {quantile(s, 0.5):.6g} & {quantile(s, 0.9):.6g} & {quantile(s, 0.99):.6g} & {quantile(s, 1.0):.6g} \\\\"
        )
    q_lines.append("\\bottomrule")
    (out_dir / "audit_closure_quantiles_rows.tex").write_text("\n".join(q_lines), encoding="utf-8")


def main() -> None:
    rows: List[MetricRow] = []
    rows.append(audit_alpha_em())
    rows.append(audit_alpha_Z())
    rows.append(audit_sin2_thetaW())
    rows.append(audit_jarlskog())

    ckm_row, ckm_e = audit_ckm_magnitudes_B20()
    rows.append(ckm_row)

    pmns_row, pmns_e = audit_pmns_sines_B20()
    rows.append(pmns_row)
    rows.append(audit_pmns_delta_Q12())

    md_row, md_e = audit_mass_depth_B20()
    rows.append(md_row)

    write_outputs(
        rows=rows,
        quantiles=[
            (r"CKM magnitudes ($B=20$)", ckm_e),
            (r"PMNS sines ($B=20$)", pmns_e),
            (r"mass depth ($B=20$)", md_e),
        ],
    )
    print("Wrote sections/generated/audit_closure_metrics_rows.tex and audit_closure_quantiles_rows.tex")


if __name__ == "__main__":
    main()



