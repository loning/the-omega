# -*- coding: utf-8 -*-
"""
Counterfactual baseline audit for selected bounded-complexity closures.

Goal: provide "look-elsewhere" context by comparing the best achievable mismatch
under the paper's structured candidate families to alternative families of
similar discrete complexity but without the same structural ingredients.

We implement a small set of deterministic counterfactuals:
  - alpha_em^{-1}: replace (pi^3,pi^2,pi) basis by (e^3,e^2,e)
  - CKM magnitudes: replace phi^{-k/2} by base^{-k/2} with base in {e, 2}
  - PMNS sines: same replacement for the s13 family

Outputs (LaTeX fragment):
  - sections/generated/audit_counterfactual_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import exp_ckm_mixing_depth_rigidity as ckm
import exp_pmns_mixing_depth_rigidity as pmns
from common_constants import ALPHA_INV_CODATA_2022


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        raise ValueError("abs_log_ratio requires positive arguments.")
    return abs(math.log(pred / ref))


def best_alpha_combo(ref: float, base: float) -> Tuple[Tuple[int, int, int], float, int]:
    """
    Candidate family: a*base^3 + b*base^2 + c*base, with a,b,c>=0 and a+b+c<=10.
    Returns (a,b,c), best_e, domain_size.
    """
    best: Tuple[float, int, int, int, int] | None = None  # (e,sum,a,b,c)
    domain = 0
    for a in range(0, 11):
        for b in range(0, 11 - a):
            for c in range(0, 11 - a - b):
                if a == 0 and b == 0 and c == 0:
                    continue
                pred = float(a) * (base**3) + float(b) * (base**2) + float(c) * base
                e = abs_log_ratio(pred, ref)
                domain += 1
                cand = (e, a + b + c, a, b, c)
                if best is None or cand < best:
                    best = cand
    if best is None:
        raise AssertionError("No candidates for alpha combo.")
    e, _s, a, b, c = best
    return (a, b, c), e, domain


def best_ckm_family(vus_ref: float, vcb_ref: float, vub_ref: float, base: float) -> Tuple[Tuple[int, int, int], float, int]:
    # Domain matches the CKM closure at B=20.
    B = 20
    vmax = ckm.v_max_x6()
    m_max = min(B, vmax)
    k_max = 2 * B
    best: Tuple[float, float, int, int, int, int] | None = None  # (maxe,sume,comp,m,k23,k13)
    domain = 0
    for m in range(1, m_max + 1):
        vus = 1.0 / math.sqrt(float(m))
        for k23 in range(1, k_max + 1):
            vcb = base ** (-0.5 * float(k23))
            for k13 in range(1, k_max + 1):
                vub = base ** (-0.5 * float(k13))
                e12 = abs_log_ratio(vus, vus_ref)
                e23 = abs_log_ratio(vcb, vcb_ref)
                e13 = abs_log_ratio(vub, vub_ref)
                maxe = max(e12, e23, e13)
                sume = e12 + e23 + e13
                comp = m + k23 + k13
                cand = (maxe, sume, comp, m, k23, k13)
                domain += 1
                if best is None or cand < best:
                    best = cand
    if best is None:
        raise AssertionError("No candidates for CKM family.")
    maxe, _sume, _comp, m, k23, k13 = best
    return (m, k23, k13), maxe, domain


def best_pmns_family(s12_ref: float, s23_ref: float, s13_ref: float, base: float) -> Tuple[Tuple[int, int, int], float, int]:
    B = 20
    k_max = 2 * B
    best: Tuple[float, float, int, int, int, int] | None = None  # (maxe,sume,comp,m12,m23,k13)
    domain = 0
    for m12 in range(1, B + 1):
        s12 = 1.0 / math.sqrt(float(m12))
        for m23 in range(1, B + 1):
            s23 = 1.0 / math.sqrt(float(m23))
            for k13 in range(1, k_max + 1):
                s13 = base ** (-0.5 * float(k13))
                e12 = abs_log_ratio(s12, s12_ref)
                e23 = abs_log_ratio(s23, s23_ref)
                e13 = abs_log_ratio(s13, s13_ref)
                maxe = max(e12, e23, e13)
                sume = e12 + e23 + e13
                comp = m12 + m23 + k13
                cand = (maxe, sume, comp, m12, m23, k13)
                domain += 1
                if best is None or cand < best:
                    best = cand
    if best is None:
        raise AssertionError("No candidates for PMNS family.")
    maxe, _sume, _comp, m12, m23, k13 = best
    return (m12, m23, k13), maxe, domain


def main() -> None:
    rows: List[str] = []

    # alpha_em^{-1} basis comparison.
    abc_pi, e_pi, dom_pi = best_alpha_combo(ALPHA_INV_CODATA_2022, base=math.pi)
    abc_e, e_e, dom_e = best_alpha_combo(ALPHA_INV_CODATA_2022, base=math.e)
    rows.append(
        f"$\\alpha_{{\\mathrm{{em}}}}^{{-1}}$ & $a\\pi^3+b\\pi^2+c\\pi$ & {dom_pi} & $({abc_pi[0]},{abc_pi[1]},{abc_pi[2]})$ & {e_pi:.6g} \\\\"
    )
    rows.append(
        f"$\\alpha_{{\\mathrm{{em}}}}^{{-1}}$ & $a\\e^3+b\\e^2+c\\e$ & {dom_e} & $({abc_e[0]},{abc_e[1]},{abc_e[2]})$ & {e_e:.6g} \\\\"
    )

    # CKM magnitudes.
    vus_ref, vcb_ref, vub_ref = 0.2243, 0.0422, 0.00394
    PHI = (1.0 + math.sqrt(5.0)) / 2.0
    p_phi, e_phi, dom_phi = best_ckm_family(vus_ref, vcb_ref, vub_ref, base=PHI)
    p_e, e_ce, dom_ce = best_ckm_family(vus_ref, vcb_ref, vub_ref, base=math.e)
    p_2, e_c2, dom_c2 = best_ckm_family(vus_ref, vcb_ref, vub_ref, base=2.0)
    rows.append(
        f"CKM magnitudes & $\\varphi$-family & {dom_phi} & $({p_phi[0]},{p_phi[1]},{p_phi[2]})$ & {e_phi:.6g} \\\\"
    )
    rows.append(
        f"CKM magnitudes & $\\e$-family & {dom_ce} & $({p_e[0]},{p_e[1]},{p_e[2]})$ & {e_ce:.6g} \\\\"
    )
    rows.append(
        f"CKM magnitudes & $2$-family & {dom_c2} & $({p_2[0]},{p_2[1]},{p_2[2]})$ & {e_c2:.6g} \\\\"
    )

    # PMNS sines.
    sin2_t12, sin2_t23, sin2_t13 = 0.307, 0.545, 0.0218
    s12_ref, s23_ref, s13_ref = math.sqrt(sin2_t12), math.sqrt(sin2_t23), math.sqrt(sin2_t13)
    q_phi, e_p_phi, dom_p_phi = best_pmns_family(s12_ref, s23_ref, s13_ref, base=PHI)
    q_e, e_p_e, dom_p_e = best_pmns_family(s12_ref, s23_ref, s13_ref, base=math.e)
    q_2, e_p_2, dom_p_2 = best_pmns_family(s12_ref, s23_ref, s13_ref, base=2.0)
    rows.append(
        f"PMNS sines & $\\varphi$-family & {dom_p_phi} & $({q_phi[0]},{q_phi[1]},{q_phi[2]})$ & {e_p_phi:.6g} \\\\"
    )
    rows.append(
        f"PMNS sines & $\\e$-family & {dom_p_e} & $({q_e[0]},{q_e[1]},{q_e[2]})$ & {e_p_e:.6g} \\\\"
    )
    rows.append(
        f"PMNS sines & $2$-family & {dom_p_2} & $({q_2[0]},{q_2[1]},{q_2[2]})$ & {e_p_2:.6g} \\\\"
    )

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit_counterfactual_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/audit_counterfactual_rows.tex")


if __name__ == "__main__":
    main()


