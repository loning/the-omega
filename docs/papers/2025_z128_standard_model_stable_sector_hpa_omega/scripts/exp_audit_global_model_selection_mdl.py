# -*- coding: utf-8 -*-
"""
Global model-selection (look-elsewhere) audit across *families* using an MDL/prefix-code prior.

This script closes the cross-family OP4 gap in an explicit, deterministic way:
  - declare a finite family registry (mainline closures + existing audited baselines),
  - assign each family a prefix-code length L_fam using Elias gamma code on a deterministic index,
  - compute within-family success frequencies N_{<=eps}/|Theta| at eps in {0.01, 0.05},
  - aggregate across families by an MDL-weighted mixture bound, per closure.

Outputs (LaTeX fragments):
  - sections/generated/audit_global_mdl_family_rows.tex
  - sections/generated/audit_global_mdl_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import exp_fold6_stats as fold
import exp_holonomy_loops as holo
import exp_holonomy_loop_scale_sweep as ls
import exp_holonomy_phase_lift_angles as ang
import exp_holonomy_phase_lift_cp_invariant as ph
from common_constants import (
    ALPHA_INV_CODATA_2022,
    CKM_VCB_REF,
    CKM_VUB_REF,
    CKM_VUS_REF,
    PHI,
    PMNS_SIN2_T12_REF,
    PMNS_SIN2_T13_REF,
    PMNS_SIN2_T23_REF,
)
from common_progress import ProgressEvery
from common_tex import read_lines, write_lines


EPS_LIST = [0.01, 0.05]


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0 or (not math.isfinite(pred)) or (not math.isfinite(ref)):
        return float("inf")
    return abs(math.log(pred / ref))


def elias_gamma_length(n: int) -> int:
    if n <= 0:
        raise ValueError("Elias gamma code requires n>=1.")
    return 2 * int(math.floor(math.log2(float(n)))) + 1


def mdl_weight(L: int) -> float:
    return 2.0 ** (-float(L))


@dataclass(frozen=True)
class FamilyRow:
    closure_key: str
    closure_tex: str
    family_key: str
    family_tex: str
    domain_size: int
    n_le_001: int
    n_le_005: int
    fam_index: int  # 1-based within the closure

    @property
    def L_fam(self) -> int:
        return elias_gamma_length(self.fam_index)

    @property
    def w_fam(self) -> float:
        return mdl_weight(self.L_fam)


def _parse_audit_closure_metrics(gen_dir: Path) -> Dict[str, Tuple[int, int, int]]:
    """
    Parse sections/generated/audit_closure_metrics_rows.tex.
    Returns mapping: closure_tex -> (domain_size, N_le_001, N_le_005).
    """
    p = gen_dir / "audit_closure_metrics_rows.tex"
    if not p.is_file():
        raise FileNotFoundError(f"Missing generated file: {p}")
    out: Dict[str, Tuple[int, int, int]] = {}
    for line in read_lines(p):
        s = line.strip()
        if not s or s.startswith("\\bottomrule"):
            continue
        if "&" not in s:
            continue
        # Strip a trailing LaTeX row terminator robustly.
        s = s.rstrip("\\").strip()
        cols = [c.strip() for c in s.split("&")]
        if len(cols) < 9:
            continue
        closure_tex = cols[0]
        domain_size = int(cols[2].rstrip("\\").strip())
        n001 = int(cols[-2].rstrip("\\").strip())
        n005 = int(cols[-1].rstrip("\\").strip())
        out[closure_tex] = (domain_size, n001, n005)
    return out


def _parse_audit_pi_poly_null(gen_dir: Path) -> Tuple[int, int, int]:
    """
    Parse sections/generated/audit_pi_poly_null_rows.tex (single-row table).
    Returns (domain_size, N_le_001, N_le_005).
    """
    p = gen_dir / "audit_pi_poly_null_rows.tex"
    if not p.is_file():
        raise FileNotFoundError(f"Missing generated file: {p}")
    for line in read_lines(p):
        s = line.strip()
        if not s or s.startswith("\\bottomrule"):
            continue
        if "&" not in s:
            continue
        # Some generated rows use raw strings and may end with more than two backslashes.
        # Strip a trailing LaTeX row terminator robustly.
        s = s.rstrip("\\").strip()
        cols = [c.strip() for c in s.split("&")]
        # Columns: closure, family_tex, domain, minimizer, best_e, ties, n001, n005
        if len(cols) < 8:
            raise ValueError(f"Unexpected format in {p}: {line!r}")
        domain_size = int(cols[2].rstrip("\\").strip())
        n001 = int(cols[6].rstrip("\\").strip())
        n005 = int(cols[7].rstrip("\\").strip())
        return domain_size, n001, n005
    raise AssertionError(f"No data rows found in {p}")


def _alpha_simplex_counts(base: float) -> Tuple[int, int, int]:
    """
    Candidate family: a*base^3 + b*base^2 + c*base with a,b,c>=0 and a+b+c<=10, excluding (0,0,0).
    Returns (domain_size, N_le_001, N_le_005) for target alpha^{-1}.
    """
    x_ref = float(ALPHA_INV_CODATA_2022)
    domain = 0
    n001 = 0
    n005 = 0
    for a in range(0, 11):
        for b in range(0, 11 - a):
            for c in range(0, 11 - a - b):
                if a == 0 and b == 0 and c == 0:
                    continue
                domain += 1
                pred = float(a) * (base**3) + float(b) * (base**2) + float(c) * base
                e = abs_log_ratio(pred, x_ref)
                if e <= 0.01:
                    n001 += 1
                if e <= 0.05:
                    n005 += 1
    return domain, n001, n005


def _ckm_magnitudes_counts(base: float) -> Tuple[int, int, int]:
    """
    Candidate family: |Vus|=1/sqrt(d), |Vcb|=base^{-k23/2}, |Vub|=base^{-k13/2}
    with d in [1,20], k23,k13 in [1,40]. Objective E_inf is minimax abs log mismatch.
    Returns (domain_size, N_le_001, N_le_005).
    """
    domain = 0
    n001 = 0
    n005 = 0
    for d in range(1, 21):
        vus = 1.0 / math.sqrt(float(d))
        e12 = abs_log_ratio(vus, CKM_VUS_REF)
        for k23 in range(1, 41):
            vcb = base ** (-0.5 * float(k23))
            e23 = abs_log_ratio(vcb, CKM_VCB_REF)
            for k13 in range(1, 41):
                domain += 1
                vub = base ** (-0.5 * float(k13))
                e13 = abs_log_ratio(vub, CKM_VUB_REF)
                Einf = max(e12, e23, e13)
                if Einf <= 0.01:
                    n001 += 1
                if Einf <= 0.05:
                    n005 += 1
    return domain, n001, n005


def _pmns_simple_counts(base: float) -> Tuple[int, int, int]:
    """
    Counterfactual PMNS family used in audit baselines:
      s12=1/sqrt(m12), s23=1/sqrt(m23), s13=base^{-k13/2}
    with m12,m23 in [1,20], k13 in [1,40]. Objective E_inf is minimax abs log mismatch.
    Returns (domain_size, N_le_001, N_le_005).
    """
    s12_ref = math.sqrt(float(PMNS_SIN2_T12_REF))
    s23_ref = math.sqrt(float(PMNS_SIN2_T23_REF))
    s13_ref = math.sqrt(float(PMNS_SIN2_T13_REF))
    domain = 0
    n001 = 0
    n005 = 0
    for m12 in range(1, 21):
        s12 = 1.0 / math.sqrt(float(m12))
        e12 = abs_log_ratio(s12, s12_ref)
        for m23 in range(1, 21):
            s23 = 1.0 / math.sqrt(float(m23))
            e23 = abs_log_ratio(s23, s23_ref)
            for k13 in range(1, 41):
                domain += 1
                s13 = base ** (-0.5 * float(k13))
                e13 = abs_log_ratio(s13, s13_ref)
                Einf = max(e12, e23, e13)
                if Einf <= 0.01:
                    n001 += 1
                if Einf <= 0.05:
                    n005 += 1
    return domain, n001, n005


def _grid_labels_row_major(n_bits: int = 3) -> Dict[Tuple[int, int], str]:
    L = 1 << n_bits
    out: Dict[Tuple[int, int], str] = {}
    for y in range(L):
        for x in range(L):
            k = x + L * y
            out[(x, y)] = fold.fold6(k)
    return out


def _mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else float("nan")


def _holonomy_perm_fit_pmns_counts(labels: Dict[Tuple[int, int], str], denoms: List[int]) -> Tuple[int, int, int]:
    """
    Count candidates in the holonomy PMNS perm-fit domain:
      candidates are (denom, rperm, cperm) with denom=2^p, p=6..18 and (r,c) in S3×S3.
    For each candidate, compute mean angles over 3/4-cycle unit plaquettes and the minimax mismatch Einf.
    Returns (domain_size, N_le_001, N_le_005).
    """
    pmns_ref = (math.sqrt(float(PMNS_SIN2_T12_REF)), math.sqrt(float(PMNS_SIN2_T23_REF)), math.sqrt(float(PMNS_SIN2_T13_REF)))
    perms = list(itertools.permutations((0, 1, 2), 3))
    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)
    B = ph.basis_B()

    domain = 0
    n001 = 0
    n005 = 0

    prog = ProgressEvery(label="global_mdl holonomy_perm_fit_pmns", total=len(denoms) * 36, interval_s=60.0)
    prog.start()

    for denom in denoms:
        # Collect effective unitaries on 3/4-cycle unit plaquettes.
        Qs: List[List[List[complex]]] = []
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

        for r in perms:
            for c in perms:
                domain += 1
                prog.maybe(domain)
                s12s: List[float] = []
                s23s: List[float] = []
                s13s: List[float] = []
                for Q in Qs:
                    Qp = [[Q[r[i]][c[j]] for j in range(3)] for i in range(3)]
                    s12, s23, s13, _delta_deg, _J = ang.extract_angles(Qp)
                    if math.isnan(s12) or math.isnan(s23) or math.isnan(s13):
                        continue
                    s12s.append(float(s12))
                    s23s.append(float(s23))
                    s13s.append(float(s13))
                if not s12s:
                    continue
                s12m = _mean(s12s)
                s23m = _mean(s23s)
                s13m = _mean(s13s)
                e12 = abs_log_ratio(s12m, pmns_ref[0])
                e23 = abs_log_ratio(s23m, pmns_ref[1])
                e13 = abs_log_ratio(s13m, pmns_ref[2])
                Einf = max(e12, e23, e13)
                if Einf <= 0.01:
                    n001 += 1
                if Einf <= 0.05:
                    n005 += 1

    prog.done(extra=f"domain={domain}")
    return domain, n001, n005


def _holonomy_single_loop_counts(
    labels: Dict[Tuple[int, int], str],
    denoms: List[int],
    map_names: List[str],
) -> Tuple[int, int, int, int, int]:
    """
    Count candidates in the holonomy single-loop scan domain used by the counterfactual audit:
      candidates are (map_name, denom, k, x, y, rperm, cperm) with k<=7 and (r,c) in S3×S3.
    We compute minimax mismatch Einf to PMNS and to CKM references and count those <= thresholds.

    Returns:
      (domain_size, n001_pmns, n005_pmns, n001_ckm, n005_ckm)
    """
    pmns_ref = (math.sqrt(float(PMNS_SIN2_T12_REF)), math.sqrt(float(PMNS_SIN2_T23_REF)), math.sqrt(float(PMNS_SIN2_T13_REF)))
    ckm_ref = (float(CKM_VUS_REF), float(CKM_VCB_REF), float(CKM_VUB_REF))
    perms = list(itertools.permutations((0, 1, 2), 3))

    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)
    B = ph.basis_B()

    # Domain size: map family × denom × all square loops (k<=7) × S3×S3.
    loop_positions: List[Tuple[int, int, int]] = []
    for k in range(1, 8):
        max_xy = 8 - k - 1
        for x in range(max_xy + 1):
            for y in range(max_xy + 1):
                loop_positions.append((k, x, y))
    domain_total = len(map_names) * len(denoms) * len(loop_positions) * (len(perms) ** 2)

    n001_pmns = 0
    n005_pmns = 0
    n001_ckm = 0
    n005_ckm = 0

    prog = ProgressEvery(label="global_mdl holonomy_single_loop", total=domain_total, interval_s=60.0)
    prog.start()
    seen = 0

    for map_name in map_names:
        for denom in denoms:
            for k, x0, y0 in loop_positions:
                # Build 4x4 holonomy once for this (map, denom, loop).
                H = [[1.0 + 0j if i == j else 0j for j in range(4)] for i in range(4)]
                for a, b in ls.loop_edges_square(x0, y0, k=k):
                    U_ab = ph.edge_unitary_with_denom(a, b, labels, pre, edge_p, denom=denom, map_name=map_name, bits=6)
                    H = ph.matmul(U_ab, H)
                M3 = ph.project_3x3(H, B=B)
                Q = ph.gram_schmidt_unitary(M3)
                if Q is None:
                    # Still count the full S3×S3 slab as domain, but with zero successes.
                    seen += len(perms) ** 2
                    prog.maybe(seen)
                    continue

                for r in perms:
                    for c in perms:
                        seen += 1
                        prog.maybe(seen)
                        Qp = [[Q[r[i]][c[j]] for j in range(3)] for i in range(3)]
                        s12, s23, s13, _delta_deg, _J = ang.extract_angles(Qp)
                        if math.isnan(s12) or math.isnan(s23) or math.isnan(s13):
                            continue
                        s12f = float(s12)
                        s23f = float(s23)
                        s13f = float(s13)

                        # PMNS mismatch.
                        e12 = abs_log_ratio(s12f, pmns_ref[0])
                        e23 = abs_log_ratio(s23f, pmns_ref[1])
                        e13 = abs_log_ratio(s13f, pmns_ref[2])
                        Einf = max(e12, e23, e13)
                        if Einf <= 0.01:
                            n001_pmns += 1
                        if Einf <= 0.05:
                            n005_pmns += 1

                        # CKM mismatch.
                        e12 = abs_log_ratio(s12f, ckm_ref[0])
                        e23 = abs_log_ratio(s23f, ckm_ref[1])
                        e13 = abs_log_ratio(s13f, ckm_ref[2])
                        Einf = max(e12, e23, e13)
                        if Einf <= 0.01:
                            n001_ckm += 1
                        if Einf <= 0.05:
                            n005_ckm += 1

    prog.done(extra=f"domain={domain_total}")
    return domain_total, n001_pmns, n005_pmns, n001_ckm, n005_ckm


def _build_registry(gen_dir: Path) -> List[FamilyRow]:
    """
    Build the family registry with domain sizes and within-family counts.
    Mainline families are read from existing generated audit tables; baseline families are computed here.
    """
    main = _parse_audit_closure_metrics(gen_dir)
    pi_poly_domain, pi_poly_n001, pi_poly_n005 = _parse_audit_pi_poly_null(gen_dir)

    # Convenience: pull mainline entries by the exact closure label string used in the table.
    def need(closure_tex: str) -> Tuple[int, int, int]:
        if closure_tex not in main:
            raise KeyError(f"Missing closure row in audit_closure_metrics_rows.tex: {closure_tex}")
        return main[closure_tex]

    rows: List[FamilyRow] = []

    # ---------- alpha_em^{-1} ----------
    cl_key = "alpha_em_inv"
    cl_tex = r"$\alpha_{\mathrm{em}}^{-1}$"
    # Family indices are deterministic within each closure.
    dom, n001, n005 = need(cl_tex)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="pi_simplex",
            family_tex=r"$a\pi^3{+}b\pi^2{+}c\pi$",
            domain_size=dom,
            n_le_001=n001,
            n_le_005=n005,
            fam_index=1,
        )
    )
    dom_e, n001_e, n005_e = _alpha_simplex_counts(base=math.e)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="e_simplex",
            family_tex=r"$a\e^3{+}b\e^2{+}c\e$",
            domain_size=dom_e,
            n_le_001=n001_e,
            n_le_005=n005_e,
            fam_index=2,
        )
    )
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="pi_poly_null",
            family_tex=r"$\sum_{j=0}^3 a_j\pi^j$",
            domain_size=pi_poly_domain,
            n_le_001=pi_poly_n001,
            n_le_005=pi_poly_n005,
            fam_index=3,
        )
    )

    # ---------- alpha^{-1}(mu_Z) ----------
    cl_key = "alphaZ_inv"
    cl_tex = r"$\alpha^{-1}(\mu_Z)$"
    dom, n001, n005 = need(cl_tex)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="n_pi2",
            family_tex=r"$n\pi^2$",
            domain_size=dom,
            n_le_001=n001,
            n_le_005=n005,
            fam_index=1,
        )
    )

    # ---------- sin^2 thetaW ----------
    cl_key = "sin2_thetaW"
    cl_tex = r"$\sin^2\theta_W(\mu_Z)$"
    dom, n001, n005 = need(cl_tex)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="pq_rational",
            family_tex=r"$p/q$",
            domain_size=dom,
            n_le_001=n001,
            n_le_005=n005,
            fam_index=1,
        )
    )

    # ---------- J (CKM) ----------
    cl_key = "J_CKM"
    cl_tex = r"$J$ (CKM)"
    dom, n001, n005 = need(cl_tex)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="inv_a_pi_n",
            family_tex=r"$1/(a\pi^n)$",
            domain_size=dom,
            n_le_001=n001,
            n_le_005=n005,
            fam_index=1,
        )
    )

    # ---------- CKM magnitudes ----------
    cl_key = "ckm_magnitudes"
    cl_tex = "CKM magnitudes"
    dom, n001, n005 = need(cl_tex)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="phi_family",
            family_tex=r"$\varphi^{-k/2}$",
            domain_size=dom,
            n_le_001=n001,
            n_le_005=n005,
            fam_index=1,
        )
    )
    dom_e, n001_e, n005_e = _ckm_magnitudes_counts(base=math.e)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="e_family",
            family_tex=r"$\e^{-k/2}$",
            domain_size=dom_e,
            n_le_001=n001_e,
            n_le_005=n005_e,
            fam_index=2,
        )
    )
    dom_2, n001_2, n005_2 = _ckm_magnitudes_counts(base=2.0)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="two_family",
            family_tex=r"$2^{-k/2}$",
            domain_size=dom_2,
            n_le_001=n001_2,
            n_le_005=n005_2,
            fam_index=3,
        )
    )

    # ---------- PMNS sines ----------
    cl_key = "pmns_sines"
    cl_tex = "PMNS sines"
    dom, n001, n005 = need(cl_tex)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="phi_family",
            family_tex=r"$\varphi^{-k/2}$",
            domain_size=dom,
            n_le_001=n001,
            n_le_005=n005,
            fam_index=1,
        )
    )
    dom_e, n001_e, n005_e = _pmns_simple_counts(base=math.e)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="e_family",
            family_tex=r"$\e^{-k/2}$ (cf.)",
            domain_size=dom_e,
            n_le_001=n001_e,
            n_le_005=n005_e,
            fam_index=2,
        )
    )
    dom_2, n001_2, n005_2 = _pmns_simple_counts(base=2.0)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="two_family",
            family_tex=r"$2^{-k/2}$ (cf.)",
            domain_size=dom_2,
            n_le_001=n001_2,
            n_le_005=n005_2,
            fam_index=3,
        )
    )

    # ---------- PMNS delta ----------
    cl_key = "pmns_delta"
    cl_tex = r"PMNS $\delta$"
    dom, n001, n005 = need(cl_tex)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="kpi_over_q",
            family_tex=r"$k\pi/q$",
            domain_size=dom,
            n_le_001=n001,
            n_le_005=n005,
            fam_index=1,
        )
    )

    # ---------- mass depth ----------
    cl_key = "mass_depth"
    cl_tex = r"mass depth (leptons)"
    dom, n001, n005 = need(cl_tex)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="integer_abc",
            family_tex=r"$(a,b,c)$",
            domain_size=dom,
            n_le_001=n001,
            n_le_005=n005,
            fam_index=1,
        )
    )

    # ---------- Holonomy PMNS permutation fit (Hilbert vs row-major) ----------
    denoms = [1 << p for p in range(6, 19)]
    cl_key = "holo_permfit_pmns"
    cl_tex = r"Holonomy PMNS perm-fit"
    dom_h, n001_h, n005_h = _holonomy_perm_fit_pmns_counts(holo.grid_labels(n_bits=3), denoms)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="hilbert",
            family_tex=r"Hilbert",
            domain_size=dom_h,
            n_le_001=n001_h,
            n_le_005=n005_h,
            fam_index=1,
        )
    )
    dom_r, n001_r, n005_r = _holonomy_perm_fit_pmns_counts(_grid_labels_row_major(n_bits=3), denoms)
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="row_major",
            family_tex=r"row-major",
            domain_size=dom_r,
            n_le_001=n001_r,
            n_le_005=n005_r,
            fam_index=2,
        )
    )

    # ---------- Holonomy single-loop best-fit (Hilbert vs row-major; PMNS and CKM counted separately) ----------
    map_names = ["id", "gray", "bitrev", "not"]
    domain_single, n001_pmns_h, n005_pmns_h, n001_ckm_h, n005_ckm_h = _holonomy_single_loop_counts(
        holo.grid_labels(n_bits=3), denoms, map_names
    )
    domain_single_r, n001_pmns_r, n005_pmns_r, n001_ckm_r, n005_ckm_r = _holonomy_single_loop_counts(
        _grid_labels_row_major(n_bits=3), denoms, map_names
    )

    cl_key = "holo_single_pmns"
    cl_tex = r"Holonomy single-loop (PMNS)"
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="hilbert",
            family_tex=r"Hilbert",
            domain_size=domain_single,
            n_le_001=n001_pmns_h,
            n_le_005=n005_pmns_h,
            fam_index=1,
        )
    )
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="row_major",
            family_tex=r"row-major",
            domain_size=domain_single_r,
            n_le_001=n001_pmns_r,
            n_le_005=n005_pmns_r,
            fam_index=2,
        )
    )

    cl_key = "holo_single_ckm"
    cl_tex = r"Holonomy single-loop (CKM)"
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="hilbert",
            family_tex=r"Hilbert",
            domain_size=domain_single,
            n_le_001=n001_ckm_h,
            n_le_005=n005_ckm_h,
            fam_index=1,
        )
    )
    rows.append(
        FamilyRow(
            closure_key=cl_key,
            closure_tex=cl_tex,
            family_key="row_major",
            family_tex=r"row-major",
            domain_size=domain_single_r,
            n_le_001=n001_ckm_r,
            n_le_005=n005_ckm_r,
            fam_index=2,
        )
    )

    return rows


def _group_by_closure(rows: Iterable[FamilyRow]) -> Dict[str, List[FamilyRow]]:
    out: Dict[str, List[FamilyRow]] = {}
    for r in rows:
        out.setdefault(r.closure_key, []).append(r)
    # Sort by fam_index for determinism.
    for k in out:
        out[k] = sorted(out[k], key=lambda x: x.fam_index)
    return out


def _p_hat(row: FamilyRow, eps: float) -> float:
    if eps == 0.01:
        return float(row.n_le_001) / float(row.domain_size)
    if eps == 0.05:
        return float(row.n_le_005) / float(row.domain_size)
    raise ValueError("Unsupported eps.")


def _global_mixture_prob(rows: List[FamilyRow], eps: float) -> float:
    ws = [r.w_fam for r in rows]
    Z = sum(ws)
    if Z <= 0.0:
        return 0.0
    return sum((w / Z) * _p_hat(r, eps) for r, w in zip(rows, ws))


def write_outputs(rows: List[FamilyRow]) -> None:
    root = Path(__file__).resolve().parent.parent
    gen_dir = root / "sections" / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)

    # ----- family registry rows -----
    lines: List[str] = []
    # Sort by closure, then fam_index, to keep the table stable.
    rows_sorted = sorted(rows, key=lambda r: (r.closure_tex, r.fam_index, r.family_tex))
    for r in rows_sorted:
        lines.append(
            f"{r.closure_tex} & {r.family_tex} & {r.domain_size} & {r.n_le_001} & {r.n_le_005} & {r.L_fam} & $2^{{-{r.L_fam}}}$ \\\\"
        )
    lines.append("\\bottomrule")
    write_lines(gen_dir / "audit_global_mdl_family_rows.tex", lines)

    # ----- per-closure mixture summary -----
    grouped = _group_by_closure(rows)
    sum_lines: List[str] = []
    sum_lines.append(r"\begin{tabular}{lrr}")
    sum_lines.append(r"\toprule")
    sum_lines.append(r"closure & $p_{\mathrm{global}}(0.01)$ & $p_{\mathrm{global}}(0.05)$ \\")
    sum_lines.append(r"\midrule")
    total_001 = 0.0
    total_005 = 0.0
    # Stable ordering by closure_tex.
    closure_items = sorted(((rs[0].closure_tex, rs) for rs in grouped.values()), key=lambda x: x[0])
    for closure_tex, rs in closure_items:
        p001 = _global_mixture_prob(rs, 0.01)
        p005 = _global_mixture_prob(rs, 0.05)
        total_001 += p001
        total_005 += p005
        sum_lines.append(f"{closure_tex} & {p001:.6g} & {p005:.6g} \\\\")
    sum_lines.append(r"\midrule")
    sum_lines.append(rf"union bound (sum) & {total_001:.6g} & {total_005:.6g} \\")
    sum_lines.append(r"\bottomrule")
    sum_lines.append(r"\end{tabular}")
    write_lines(gen_dir / "audit_global_mdl_summary.tex", sum_lines)

    print("Wrote sections/generated/audit_global_mdl_family_rows.tex")
    print("Wrote sections/generated/audit_global_mdl_summary.tex")


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    gen_dir = root / "sections" / "generated"
    rows = _build_registry(gen_dir=gen_dir)
    write_outputs(rows)


if __name__ == "__main__":
    main()


