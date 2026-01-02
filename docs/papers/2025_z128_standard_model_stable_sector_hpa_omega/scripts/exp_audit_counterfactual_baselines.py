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
import itertools
from pathlib import Path
from typing import List, Tuple

import exp_ckm_mixing_depth_rigidity as ckm
import exp_pmns_mixing_depth_rigidity as pmns
import exp_fold6_stats as fold
import exp_holonomy_loops as holo
import exp_holonomy_loop_scale_sweep as ls
import exp_holonomy_phase_lift_angles as ang
import exp_holonomy_phase_lift_cp_invariant as ph
from common_constants import ALPHA_INV_CODATA_2022


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0 or (not math.isfinite(pred)) or (not math.isfinite(ref)):
        return float("inf")
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


def grid_labels_row_major(n_bits: int = 3) -> dict[tuple[int, int], str]:
    L = 1 << n_bits
    out: dict[tuple[int, int], str] = {}
    for y in range(L):
        for x in range(L):
            k = x + L * y
            out[(x, y)] = fold.fold6(k)
    return out


def _mean(xs: list[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else float("nan")


def _best_holonomy_perm_fit_pmns(labels: dict[tuple[int, int], str], denoms: list[int]) -> Tuple[tuple[int, tuple[int, int, int], tuple[int, int, int]], float, int]:
    """
    Return (minimizer=(denom, rperm, cperm), best_Einf, domain_size).
    Domain counts each (denom, rperm, cperm) evaluation.
    """
    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)
    B = ph.basis_B()

    pmns_ref = (math.sqrt(0.307), math.sqrt(0.545), math.sqrt(0.0218))
    perms = list(itertools.permutations((0, 1, 2), 3))

    best = None  # (Einf,E1,denom,r,c)
    domain = 0

    for denom in denoms:
        # Collect effective 3x3 unitaries on 3/4-cycle unit plaquettes.
        Qs: list[list[list[complex]]] = []
        for x in range(7):
            for y in range(7):
                a = (x, y)
                b = (x + 1, y)
                c = (x + 1, y + 1)
                d = (x, y + 1)
                p_ab = edge_p[(a, b)]
                p_bc = edge_p[(b, c)]
                p_cd = edge_p[(c, d)]
                p_da = edge_p[(d, a)]
                hol_p = holo.compose(p_da, holo.compose(p_cd, holo.compose(p_bc, p_ab)))
                ct = holo.cycle_type(hol_p)
                if ct not in ("3", "4"):
                    continue
                U_ab = ph.edge_unitary_with_denom(a, b, labels, pre, edge_p, denom=denom, map_name="id", bits=6)
                U_bc = ph.edge_unitary_with_denom(b, c, labels, pre, edge_p, denom=denom, map_name="id", bits=6)
                U_cd = ph.edge_unitary_with_denom(c, d, labels, pre, edge_p, denom=denom, map_name="id", bits=6)
                U_da = ph.edge_unitary_with_denom(d, a, labels, pre, edge_p, denom=denom, map_name="id", bits=6)
                H = ph.matmul(U_da, ph.matmul(U_cd, ph.matmul(U_bc, U_ab)))
                M3 = ph.project_3x3(H, B=B)
                Q = ph.gram_schmidt_unitary(M3)
                if Q is None:
                    continue
                Qs.append(Q)

        # Evaluate all global permutations.
        for r in perms:
            for c in perms:
                domain += 1
                s12s: list[float] = []
                s23s: list[float] = []
                s13s: list[float] = []
                for Q in Qs:
                    Qp = [[Q[r[i]][c[j]] for j in range(3)] for i in range(3)]
                    s12, s23, s13, _delta_deg, _J = ang.extract_angles(Qp)
                    if math.isnan(s12) or math.isnan(s23) or math.isnan(s13):
                        continue
                    s12s.append(s12)
                    s23s.append(s23)
                    s13s.append(s13)
                if not s12s:
                    continue
                s12 = _mean(s12s)
                s23 = _mean(s23s)
                s13 = _mean(s13s)
                e12 = abs_log_ratio(s12, pmns_ref[0])
                e23 = abs_log_ratio(s23, pmns_ref[1])
                e13 = abs_log_ratio(s13, pmns_ref[2])
                Einf = max(e12, e23, e13)
                E1 = e12 + e23 + e13
                cand = (Einf, E1, denom, r, c)
                if best is None or cand < best:
                    best = cand

    if best is None:
        raise AssertionError("No holonomy perm-fit candidates enumerated.")
    Einf, _E1, denom, r, c = best
    return (denom, r, c), Einf, domain


def _best_single_loop_two_targets(
    labels: dict[tuple[int, int], str],
    pmns_ref: Tuple[float, float, float],
    ckm_ref: Tuple[float, float, float],
) -> Tuple[
    Tuple[float, Tuple[str, int, int, int, int, str, Tuple[int, int, int], Tuple[int, int, int]]],
    Tuple[float, Tuple[str, int, int, int, int, str, Tuple[int, int, int], Tuple[int, int, int]]],
]:
    """
    Scan single k×k square loops (k<=7) with map family and denom=2^p (p=6..18),
    plus global S3×S3 relabeling, and return best Einf and its minimizer for PMNS/CKM.

    Minimizer tuple:
      (map_name, denom, k, x, y, cycle_type, rperm, cperm)
    """
    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)
    B = ph.basis_B()

    map_names = ["id", "gray", "bitrev", "not"]
    denoms = [1 << p for p in range(6, 19)]
    perms = list(itertools.permutations((0, 1, 2), 3))

    best_pmns = None  # (Einf,E1,minimizer)
    best_ckm = None

    def update(best, Einf: float, E1: float, minimizer):
        cand = (Einf, E1, minimizer)
        return cand if best is None or cand < best else best

    for map_name in map_names:
        for denom in denoms:
            for k in range(1, 8):
                max_xy = 8 - k - 1
                for x in range(max_xy + 1):
                    for y in range(max_xy + 1):
                        hol_p = (0, 1, 2, 3)
                        H = [[1.0 + 0j if i == j else 0j for j in range(4)] for i in range(4)]
                        for a, b in ls.loop_edges_square(x, y, k=k):
                            p_ab = edge_p[(a, b)]
                            hol_p = holo.compose(p_ab, hol_p)
                            U_ab = ph.edge_unitary_with_denom(
                                a, b, labels, pre, edge_p, denom=denom, map_name=map_name, bits=6
                            )
                            H = ph.matmul(U_ab, H)
                        ct = holo.cycle_type(hol_p)

                        M3 = ph.project_3x3(H, B=B)
                        Q = ph.gram_schmidt_unitary(M3)
                        if Q is None:
                            continue

                        for r in perms:
                            for c in perms:
                                Qp = [[Q[r[i]][c[j]] for j in range(3)] for i in range(3)]
                                s12, s23, s13, _delta_deg, _J = ang.extract_angles(Qp)
                                # PMNS objective
                                e12 = abs_log_ratio(s12, pmns_ref[0])
                                e23 = abs_log_ratio(s23, pmns_ref[1])
                                e13 = abs_log_ratio(s13, pmns_ref[2])
                                Einf = max(e12, e23, e13)
                                E1 = e12 + e23 + e13
                                best_pmns = update(best_pmns, Einf, E1, (map_name, denom, k, x, y, ct, r, c))
                                # CKM objective
                                e12 = abs_log_ratio(s12, ckm_ref[0])
                                e23 = abs_log_ratio(s23, ckm_ref[1])
                                e13 = abs_log_ratio(s13, ckm_ref[2])
                                Einf = max(e12, e23, e13)
                                E1 = e12 + e23 + e13
                                best_ckm = update(best_ckm, Einf, E1, (map_name, denom, k, x, y, ct, r, c))

    if best_pmns is None or best_ckm is None:
        raise AssertionError("No candidates for single-loop scan.")
    Einf_p, _E1_p, min_p = best_pmns
    Einf_c, _E1_c, min_c = best_ckm
    return (Einf_p, min_p), (Einf_c, min_c)


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

    # Holonomy PMNS permutation-fit counterfactual: Hilbert vs row-major addressing.
    denoms = [1 << p for p in range(6, 19)]  # 64..262144
    m_h, e_h, dom_h = _best_holonomy_perm_fit_pmns(holo.grid_labels(n_bits=3), denoms)
    rows.append(
        f"Holonomy PMNS perm-fit & Hilbert addressing & {dom_h} & $({m_h[0]},{m_h[1]},{m_h[2]})$ & {e_h:.6g} \\\\"
    )
    m_r, e_r, dom_r = _best_holonomy_perm_fit_pmns(grid_labels_row_major(n_bits=3), denoms)
    rows.append(
        f"Holonomy PMNS perm-fit & row-major addressing & {dom_r} & $({m_r[0]},{m_r[1]},{m_r[2]})$ & {e_r:.6g} \\\\"
    )

    # Holonomy single-loop best-fit counterfactual: Hilbert vs row-major addressing.
    pmns_ref = (math.sqrt(0.307), math.sqrt(0.545), math.sqrt(0.0218))
    ckm_ref = (0.2243, 0.0422, 0.00394)
    domain_single = 4 * len(denoms) * 140 * 36  # map family × denom × loops × S3×S3

    def fmt_perm3(p: Tuple[int, int, int]) -> str:
        return f"({p[0]},{p[1]},{p[2]})"

    def fmt_minimizer(m) -> str:
        map_name, denom, k, x, y, ct, r, c = m
        return f"\\texttt{{({map_name},{denom},{k},({x},{y}),{ct},{fmt_perm3(r)},{fmt_perm3(c)})}}"

    (e_pmns_h, m_pmns_h), (e_ckm_h, m_ckm_h) = _best_single_loop_two_targets(holo.grid_labels(n_bits=3), pmns_ref, ckm_ref)
    rows.append(f"Holonomy single-loop PMNS & Hilbert addressing & {domain_single} & {fmt_minimizer(m_pmns_h)} & {e_pmns_h:.6g} \\\\")
    rows.append(f"Holonomy single-loop CKM & Hilbert addressing & {domain_single} & {fmt_minimizer(m_ckm_h)} & {e_ckm_h:.6g} \\\\")

    (e_pmns_r, m_pmns_r), (e_ckm_r, m_ckm_r) = _best_single_loop_two_targets(grid_labels_row_major(n_bits=3), pmns_ref, ckm_ref)
    rows.append(f"Holonomy single-loop PMNS & row-major addressing & {domain_single} & {fmt_minimizer(m_pmns_r)} & {e_pmns_r:.6g} \\\\")
    rows.append(f"Holonomy single-loop CKM & row-major addressing & {domain_single} & {fmt_minimizer(m_ckm_r)} & {e_ckm_r:.6g} \\\\")

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit_counterfactual_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/audit_counterfactual_rows.tex")


if __name__ == "__main__":
    main()


