# -*- coding: utf-8 -*-
"""
Neutrino mass-mechanism candidate registry: enumeration + CAP-style selection + audit scoreboard.

Reads:
  - data/neutrino_mass_mechanisms/registry.json
  - data/neutrino_external_audit/inputs.json (external bounds; Match/Audit only)
  - sections/generated/pmns_angles_rows.tex (closed PMNS moduli; used to compute |U_ei|^2)

Writes (LaTeX fragments):
  - sections/generated/neutrino_mechanism_candidates_rows.tex
  - sections/generated/neutrino_mechanism_scoreboard_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import exp_sm_labeling_solver as sml
from common_constants import LOG_PHI, M_E_GEV, PHI
from common_tex import write_lines


# Unit conversion.
M_E_EV = M_E_GEV * 1.0e9  # GeV -> eV
V_EW_GEV = 246.0  # Higgs VEV (matching-layer calibration; see Appendix 48)


def _log_phi(x: float) -> float:
    if x <= 0.0:
        return float("nan")
    return math.log(x) / LOG_PHI


def _phi_pow(r: int) -> float:
    return PHI ** float(r)

def _tex_escape_texttt(s: str) -> str:
    """
    Minimal escaping for content placed inside \\texttt{...}.
    """
    return s.replace("_", "\\_").replace("^", "\\string^")


def _fmt_ev(x: float, sig: int = 6) -> str:
    return f"{x:.{sig}g}"


def _round_int(x: float, mode: str) -> int:
    if mode == "floor":
        return int(math.floor(x))
    if mode == "ceil":
        return int(math.ceil(x))
    if mode == "nearest":
        lo = math.floor(x)
        hi = lo + 1
        if abs(x - float(lo)) < abs(float(hi) - x):
            return int(lo)
        if abs(x - float(lo)) > abs(float(hi) - x):
            return int(hi)
        # Tie: choose +infinity (deterministic).
        return int(hi)
    raise ValueError(f"Unknown rounding mode: {mode}")


def _parse_pmns_s12_s13_delta_pred(pmns_angles_rows: Path) -> tuple[float, float, float]:
    lines = pmns_angles_rows.read_text(encoding="utf-8").splitlines()
    s12 = None
    s13 = None
    delta_deg = None
    for line in lines:
        cols = [c.strip() for c in line.split("&")]
        if len(cols) < 2:
            continue
        key = cols[0]
        val = cols[1]
        try:
            x = float(val)
        except Exception:
            continue
        if "s_{12}" in key:
            s12 = x
        if "s_{13}" in key:
            s13 = x
        if "\\delta" in key:
            delta_deg = x
    if s12 is None or s13 is None or delta_deg is None:
        raise AssertionError("Failed to parse s12/s13/delta from pmns_angles_rows.tex")
    return float(s12), float(s13), float(delta_deg)


def _ue_row_moduli_sq() -> tuple[float, float, float]:
    """
    Return (|U_e1|^2, |U_e2|^2, |U_e3|^2) from the closed PMNS angles (PDG convention).
    Majorana phases do not enter these moduli.
    """
    root = Path(__file__).resolve().parent.parent
    pmns_angles = root / "sections" / "generated" / "pmns_angles_rows.tex"
    if not pmns_angles.is_file():
        raise FileNotFoundError("Missing sections/generated/pmns_angles_rows.tex; run the PMNS closure first.")
    s12, s13, _delta_deg = _parse_pmns_s12_s13_delta_pred(pmns_angles)
    c12 = math.sqrt(max(0.0, 1.0 - s12 * s12))
    c13 = math.sqrt(max(0.0, 1.0 - s13 * s13))
    ue1 = (c12 * c13) ** 2
    ue2 = (s12 * c13) ** 2
    ue3 = (s13) ** 2
    return float(ue1), float(ue2), float(ue3)


def _ue_row_complex() -> tuple[complex, complex, complex]:
    """
    Return (U_e1, U_e2, U_e3) in PDG convention from the closed PMNS angles.
    Only the e-row is needed for m_{ββ}.
    """
    root = Path(__file__).resolve().parent.parent
    pmns_angles = root / "sections" / "generated" / "pmns_angles_rows.tex"
    if not pmns_angles.is_file():
        raise FileNotFoundError("Missing sections/generated/pmns_angles_rows.tex; run the PMNS closure first.")
    s12, s13, delta_deg = _parse_pmns_s12_s13_delta_pred(pmns_angles)
    c12 = math.sqrt(max(0.0, 1.0 - s12 * s12))
    c13 = math.sqrt(max(0.0, 1.0 - s13 * s13))
    delta = math.radians(delta_deg)
    ue1 = complex(c12 * c13, 0.0)
    ue2 = complex(s12 * c13, 0.0)
    ue3 = complex(s13 * math.cos(-delta), s13 * math.sin(-delta))
    return ue1, ue2, ue3


def _m_bb_with_phases(
    m1: float,
    m2: float,
    m3: float,
    ue: tuple[complex, complex, complex],
    alpha21: float,
    alpha31: float,
) -> float:
    ue1, ue2, ue3 = ue
    a1 = (ue1 * ue1) * complex(m1, 0.0)
    a2 = (ue2 * ue2) * complex(m2, 0.0) * complex(math.cos(alpha21), math.sin(alpha21))
    a3 = (ue3 * ue3) * complex(m3, 0.0) * complex(math.cos(alpha31), math.sin(alpha31))
    return abs(a1 + a2 + a3)


def _m_beta(m1: float, m2: float, m3: float, ue2: tuple[float, float, float]) -> float:
    u1, u2, u3 = ue2
    x = u1 * (m1 * m1) + u2 * (m2 * m2) + u3 * (m3 * m3)
    return math.sqrt(max(0.0, x))


def _m_bb_bounds(m1: float, m2: float, m3: float, ue2: tuple[float, float, float]) -> tuple[float, float]:
    u1, u2, u3 = ue2
    a1 = u1 * m1
    a2 = u2 * m2
    a3 = u3 * m3
    mx = a1 + a2 + a3
    mn = max(0.0, a1 - a2 - a3, a2 - a1 - a3, a3 - a1 - a2)
    return float(mn), float(mx)


def _interval_status(min_val: float, max_val: float, upper_bound: float) -> str:
    if min_val > upper_bound:
        return "EXCLUDED"
    if max_val <= upper_bound:
        return "OK"
    return "PARTIAL"


def _fib(n: int) -> int:
    if n <= 0:
        return 0
    if n == 1 or n == 2:
        return 1
    a, b = 1, 1
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b


def _ext_count(base_word: str, m: int) -> int:
    if m < 6:
        raise ValueError("m must be >= 6")
    u6 = base_word[-1]
    if u6 == "0":
        return _fib(m - 4)
    return _fib(m - 5)


def _repair_cost(word: str) -> int:
    c = 0
    run = 0
    for ch in word:
        if ch == "1":
            run += 1
        else:
            if run >= 2:
                c += run // 2
            run = 0
    if run >= 2:
        c += run // 2
    return c


def _mean_repair_cost_ghost(m: int) -> float:
    if m <= 0:
        raise ValueError("m must be positive")
    total = 1 << m
    ghost = 0
    s = 0
    for x in range(total):
        w = format(x, f"0{m}b")
        c = _repair_cost(w)
        if c <= 0:
            continue
        ghost += 1
        s += c
    if ghost <= 0:
        return 0.0
    return float(s) / float(ghost)


def _r_hat_base_x6(word: str) -> int:
    """
    Fixed-anchor depth template r_hat at m=6 for a stable word, relative to e_R^(1).
    This is the same integer template used in the m=6 mass-spectrum closure.
    """
    # Electron reference: e_R^(1) is 010000 under the closed labeling table.
    w_e = "010000"
    V_e = sml.zeckendorf_value(w_e)
    g_e = sml.degeneracy_g(w_e)
    wt_e = w_e.count("1")

    V = sml.zeckendorf_value(word)
    g = sml.degeneracy_g(word)
    wt = word.count("1")

    return 2 * (V - V_e) + 5 * (g - g_e) + (wt - wt_e)


def _complete_spectrum(ordering: str, m0: float, dm21: float, dm31_no: float, dm31_io: float) -> tuple[float, float, float]:
    if m0 < 0.0:
        raise ValueError("m0 must be nonnegative.")
    if ordering == "NO":
        m1 = m0
        m2 = math.sqrt(m0 * m0 + dm21)
        m3 = math.sqrt(m0 * m0 + dm31_no)
        return float(m1), float(m2), float(m3)
    if ordering == "IO":
        m3 = m0
        m1 = math.sqrt(m0 * m0 + dm31_io)
        m2 = math.sqrt(m0 * m0 + dm31_io + dm21)
        return float(m1), float(m2), float(m3)
    raise ValueError("ordering must be NO or IO")


def _mu_threshold_from_m(m: int) -> float:
    """
    Resolution-threshold scale μ_th(m) from the closed staircase r_step=2π:
      r_th(m) = 2π (m-6),  μ_th(m) = m_e * φ^{r_th(m)}.
    """
    if m < 6:
        raise ValueError("m must be >= 6")
    r_th = 2.0 * math.pi * float(m - 6)
    return float(M_E_GEV) * float(PHI ** r_th)


def _nearest_threshold_m(mu: float, m_min: int = 6, m_max: int = 40) -> tuple[int, float, float]:
    """
    Return (m_star, μ_th(m_star), log mismatch) where m_star minimizes |log(mu/μ_th(m))|
    over the integer window range [m_min, m_max], tie-breaking by smaller m.
    """
    if mu <= 0.0:
        raise ValueError("mu must be positive")
    best_m = None
    best_mu = None
    best_err = None
    for m in range(int(m_min), int(m_max) + 1):
        mu_th = _mu_threshold_from_m(m)
        err = _log_mismatch(mu, mu_th)
        key = (err, m)
        if best_m is None or key < (best_err, best_m):
            best_m = m
            best_mu = mu_th
            best_err = err
    assert best_m is not None and best_mu is not None and best_err is not None
    return int(best_m), float(best_mu), float(best_err)


def _weinberg_scale_from_mnu(m_max_eV: float, c_max: float = 1.0) -> float:
    """
    Weinberg operator estimate under the bounded-coefficient convention:
      m_ν,max = (v^2 / (2 Λ)) * c_max  =>  Λ = (v^2 * c_max) / (2 m_ν,max).
    """
    if m_max_eV <= 0.0:
        raise ValueError("m_max_eV must be positive")
    if c_max <= 0.0:
        raise ValueError("c_max must be positive")
    m_max_GeV = float(m_max_eV) * 1.0e-9
    return (V_EW_GEV * V_EW_GEV * float(c_max)) / (2.0 * m_max_GeV)


def _seesaw_mr_from_mnu(m_max_eV: float, y_eff: float) -> float:
    """
    Type-I seesaw single-scale estimate:
      m_ν,max ≈ (v^2 / (2 M_R)) * y_eff^2  =>  M_R = (v^2 y_eff^2) / (2 m_ν,max).
    """
    if y_eff <= 0.0:
        raise ValueError("y_eff must be positive")
    return _weinberg_scale_from_mnu(m_max_eV=m_max_eV, c_max=float(y_eff) * float(y_eff))


@dataclass(frozen=True)
class Candidate:
    mech_id: str
    mech_type: str
    selection: str  # "cap" or "feasible"
    ordering: str
    params: Dict[str, Any]
    comp: int
    r0: int
    m_lightest: float  # eV
    m1: float
    m2: float
    m3: float
    sigma_mnu: float
    m_beta: float
    mbb_min: float
    mbb_max: float
    delta_neff: float
    status: Dict[str, str]


def _cap_key(c: Candidate) -> Tuple[int, str]:
    # Deterministic tie-break: compare by complexity, then by serialized params.
    return (c.comp, json.dumps(c.params, sort_keys=True))


def _global_key(c: Candidate) -> Tuple[int, str, str, str]:
    # Deterministic global ordering across mechanisms.
    return (
        c.comp,
        c.mech_id,
        c.ordering,
        json.dumps(c.params, sort_keys=True),
    )


def _all_bounds() -> Dict[str, float]:
    root = Path(__file__).resolve().parent.parent
    inp = root / "data" / "neutrino_external_audit" / "inputs.json"
    data = json.loads(inp.read_text(encoding="utf-8"))
    out: Dict[str, float] = {}
    for ch in data.get("channels", []):
        obs = str(ch.get("observable", ""))
        val = ch.get("value", None)
        if isinstance(val, (int, float)) and math.isfinite(float(val)):
            out[obs] = float(val)
    return out


def _passes_bounds(status: Dict[str, str]) -> bool:
    # Treat PARTIAL as admissible; EXCLUDED is failure.
    for k, v in status.items():
        if v == "EXCLUDED":
            return False
    return True


def _fmt_ratio(k: int, q: int) -> str:
    return f"{k}/{q}"


def _log_mismatch(x: float, y: float) -> float:
    if x <= 0.0 or y <= 0.0:
        return float("inf")
    return abs(math.log(x / y))


@dataclass(frozen=True)
class SplitCandidate:
    selection: str  # "cap" or "match"
    ordering: str  # "NO" or "IO"
    q: int
    k_a: int
    k_b: int
    dr_a: float
    dr_b: float
    dm21: float
    dm3_abs: float
    max_log_mismatch: float
    status: str


def _split_family_candidates(m0: float, dm21_ref: float, dm31_no_ref: float, dm31_io_ref: float, q_max: int = 12) -> List[SplitCandidate]:
    """
    Attempt to represent neutrino splittings in the r-coordinate by bounded rationals:
      dr = k/q, with 1 <= q <= q_max.

    For NO we use (dr21, dr31) with m1=m0.
    For IO we use (dr13, dr23) with m3=m0.

    Returns three candidates as a list:
      - protocol-only CAP-minimizer ("cap")
      - an internally-motivated invariant-derived candidate ("proto")
      - mismatch-minimizer against recorded splittings ("match")
    """
    if m0 <= 0.0:
        raise ValueError("m0 must be positive for splitting closure.")

    # Candidate pool (protocol side): bounded rationals.
    pool: List[Tuple[str, int, int, int]] = []
    for q in range(1, q_max + 1):
        k_max = 4 * q  # allow dr up to ~4 (covers observed dr31 ~2.6)
        for k_a in range(1, k_max + 1):
            for k_b in range(k_a + 1, k_max + 1):
                pool.append(("NO", q, k_a, k_b))
                pool.append(("IO", q, k_a, k_b))

    def complexity_key(t: Tuple[str, int, int, int]) -> Tuple[int, int, int, str]:
        ordering, q, k_a, k_b = t
        # CAP-style: minimize denominator, then numerator sizes; tie-break by ordering.
        return (q, k_a, k_b, ordering)

    cap_choice = min(pool, key=complexity_key)

    def build(ordering: str, q: int, k_a: int, k_b: int) -> SplitCandidate:
        dr_a = float(k_a) / float(q)
        dr_b = float(k_b) / float(q)

        if ordering == "NO":
            m1 = m0
            m2 = m0 * (PHI ** dr_a)
            m3 = m0 * (PHI ** dr_b)
            dm21 = float(m2 * m2 - m1 * m1)
            dm3_abs = float(abs(m3 * m3 - m1 * m1))
            dm3_ref = float(dm31_no_ref)
        else:
            m3 = m0
            m1 = m0 * (PHI ** dr_a)
            m2 = m0 * (PHI ** dr_b)
            dm21 = float(m2 * m2 - m1 * m1)
            dm3_abs = float(abs(m1 * m1 - m3 * m3))
            dm3_ref = float(dm31_io_ref)

        e21 = _log_mismatch(dm21, dm21_ref)
        e3 = _log_mismatch(dm3_abs, dm3_ref)
        e = max(e21, e3)

        # Relative tolerance in log space: 20% default.
        tol = math.log(1.2)
        status = "OK" if (e <= tol and math.isfinite(e)) else "EXCLUDED"

        return SplitCandidate(
            selection="cap",
            ordering=ordering,
            q=q,
            k_a=k_a,
            k_b=k_b,
            dr_a=dr_a,
            dr_b=dr_b,
            dm21=dm21,
            dm3_abs=dm3_abs,
            max_log_mismatch=e,
            status=status,
        )

    cap_best = build(*cap_choice)

    # Match-minimal (audit): minimize mismatch, then complexity.
    match_best = None
    match_key_best = None
    for ordering, q, k_a, k_b in pool:
        cand = build(ordering, q, k_a, k_b)
        key = (cand.max_log_mismatch, q, k_a, k_b, ordering)
        if match_best is None or key < match_key_best:
            match_best = cand
            match_key_best = key
    assert match_best is not None
    match_best = SplitCandidate(
        selection="match",
        ordering=match_best.ordering,
        q=match_best.q,
        k_a=match_best.k_a,
        k_b=match_best.k_b,
        dr_a=match_best.dr_a,
        dr_b=match_best.dr_b,
        dm21=match_best.dm21,
        dm3_abs=match_best.dm3_abs,
        max_log_mismatch=match_best.max_log_mismatch,
        status=match_best.status,
    )

    # Invariant-derived candidate (audit/interface): use anchor counts at m=6 (18⊕3 split).
    # This is a bridge rule that ties the offset denominator to (m+1) and the numerators
    # to the cyclic/boundary split sizes.
    m_anchor = 6
    q_proto = m_anchor + 1  # = 7
    k_cyc = 18
    k_bdry = 3
    proto = build("NO", q_proto, k_bdry - 1, k_cyc)
    proto = SplitCandidate(
        selection="proto",
        ordering=proto.ordering,
        q=proto.q,
        k_a=proto.k_a,
        k_b=proto.k_b,
        dr_a=proto.dr_a,
        dr_b=proto.dr_b,
        dm21=proto.dm21,
        dm3_abs=proto.dm3_abs,
        max_log_mismatch=proto.max_log_mismatch,
        status=proto.status,
    )

    return [cap_best, proto, match_best]


def _eval_status(
    sigma_mnu: float,
    m_beta: float,
    mbb_min: float,
    mbb_max: float,
    delta_neff: float,
    dm21_pred: float,
    dm31_pred_abs: float,
    bounds: Dict[str, float],
    dm21_ref: float,
    dm31_ref_abs: float,
) -> Dict[str, str]:
    st: Dict[str, str] = {}
    if "sigma_mnu" in bounds:
        st["sigma_mnu"] = "OK" if sigma_mnu <= bounds["sigma_mnu"] else "EXCLUDED"
    if "m_beta" in bounds:
        st["m_beta"] = "OK" if m_beta <= bounds["m_beta"] else "EXCLUDED"
    if "m_beta_beta" in bounds:
        st["m_beta_beta"] = _interval_status(mbb_min, mbb_max, upper_bound=bounds["m_beta_beta"])
    if "delta_N_eff" in bounds:
        st["delta_N_eff"] = "OK" if abs(delta_neff) <= bounds["delta_N_eff"] else "EXCLUDED"
    # Splittings (relative error; audit-only). If ref is 0, mark as pending.
    def rel_ok(pred: float, ref: float, tol: float = 0.2) -> str:
        if ref <= 0.0:
            return "PENDING"
        rel = abs(pred - ref) / ref
        return "OK" if rel <= tol else "EXCLUDED"

    st["dm2"] = rel_ok(dm21_pred, dm21_ref) if dm21_ref > 0.0 else "PENDING"
    st["dm3"] = rel_ok(dm31_pred_abs, dm31_ref_abs) if dm31_ref_abs > 0.0 else "PENDING"
    st["dm2_dm3"] = "OK" if (st["dm2"] != "EXCLUDED" and st["dm3"] != "EXCLUDED") else "EXCLUDED"
    return st


def _candidate_from_params(
    mech_id: str,
    mech_type: str,
    ordering: str,
    params: Dict[str, Any],
    dm21: float,
    dm31_no: float,
    dm31_io: float,
    bounds: Dict[str, float],
    ue2: tuple[float, float, float],
) -> Candidate:
    # Compute (r0, delta_neff, comp) by mechanism type.
    delta_neff = 0.0
    if mech_type == "ghost_repair_cost":
        m_dec = int(params["m_dec"])
        a = int(params["a"])
        rnd = str(params["round"])
        mean_c = _mean_repair_cost_ghost(m_dec)
        K = _round_int(float(a) * float(m_dec) * float(mean_c), rnd)
        r0 = -int(K)
        comp = int(a + m_dec + (0 if rnd == "nearest" else 1))
    elif mech_type == "xi_visibility":
        n_R = int(params["n_R"])
        p = int(params["p"])
        xi_depth = int(params["xi_depth"])
        rnd = str(params["round"])
        xi = PHI ** (-float(xi_depth))
        r0 = _round_int(float(p) * _log_phi(xi), rnd)
        delta_neff = float(n_R) * (xi**4)
        comp = int(n_R + p + xi_depth + (0 if rnd == "nearest" else 1))
    elif mech_type == "uplift_dilution":
        base_word = str(params["base_word"])
        m_high = int(params["m_high"])
        a = int(params["a"])
        rnd = str(params["round"])
        r_base = _r_hat_base_x6(base_word)
        ext = _ext_count(base_word, m=m_high)
        shift = _round_int(float(a) * _log_phi(float(ext)), rnd)
        r0 = int(r_base - shift)
        comp = int(a + m_high + (0 if rnd == "nearest" else 1))
    elif mech_type == "parity_overhead":
        m_odd = int(params["m_odd"])
        a = int(params["a"])
        n = (m_odd - 1) // 2
        r0 = -int(a * n)
        comp = int(a + m_odd)
    else:
        raise ValueError(f"Unknown mechanism type: {mech_type}")

    # Convert r0 to m_lightest (eV).
    m0 = float(M_E_EV) * float(_phi_pow(int(r0)))
    m1, m2, m3 = _complete_spectrum(ordering, m0=m0, dm21=dm21, dm31_no=dm31_no, dm31_io=dm31_io)
    sigma = float(m1 + m2 + m3)
    mb = _m_beta(m1, m2, m3, ue2=ue2)
    mbb_min, mbb_max = _m_bb_bounds(m1, m2, m3, ue2=ue2)

    dm21_pred = float(m2 * m2 - m1 * m1)
    dm31_abs = float(abs(m3 * m3 - m1 * m1))

    status = _eval_status(
        sigma_mnu=sigma,
        m_beta=mb,
        mbb_min=mbb_min,
        mbb_max=mbb_max,
        delta_neff=float(delta_neff),
        dm21_pred=dm21_pred,
        dm31_pred_abs=dm31_abs,
        bounds=bounds,
        dm21_ref=dm21,
        dm31_ref_abs=(dm31_no if ordering == "NO" else dm31_io),
    )

    return Candidate(
        mech_id=mech_id,
        mech_type=mech_type,
        selection="cap",
        ordering=ordering,
        params=dict(params),
        comp=comp,
        r0=int(r0),
        m_lightest=m0,
        m1=m1,
        m2=m2,
        m3=m3,
        sigma_mnu=sigma,
        m_beta=mb,
        mbb_min=mbb_min,
        mbb_max=mbb_max,
        delta_neff=float(delta_neff),
        status=status,
    )


def _grid_from_box(box: Dict[str, Any]) -> List[Dict[str, Any]]:
    keys = list(box.keys())
    vals = [box[k] for k in keys]
    # Validate all are lists.
    for v in vals:
        if not isinstance(v, list):
            raise ValueError("parameter_box entries must be lists")
    out: List[Dict[str, Any]] = []

    def rec(i: int, cur: Dict[str, Any]) -> None:
        if i >= len(keys):
            out.append(dict(cur))
            return
        k = keys[i]
        for v in box[k]:
            cur[k] = v
            rec(i + 1, cur)
        cur.pop(k, None)

    rec(0, {})
    return out


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    reg_path = root / "data" / "neutrino_mass_mechanisms" / "registry.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    if int(reg.get("schema_version", 0)) != 1:
        raise ValueError("Unsupported schema_version in registry.json")

    spl = reg.get("splittings_eV2", {})
    dm21 = float(spl.get("dm21", 0.0))
    dm31_no = float(spl.get("dm31_no", 0.0))
    dm31_io = float(spl.get("dm31_io", 0.0))
    if dm21 <= 0.0 or dm31_no <= 0.0 or dm31_io <= 0.0:
        raise AssertionError("Missing or invalid oscillation splitting constants in registry.json")

    bounds = _all_bounds()
    ue2 = _ue_row_moduli_sq()
    ue_complex = _ue_row_complex()

    cand_rows: List[str] = []
    score_rows: List[str] = []
    global_all: List[Candidate] = []

    for mech in reg.get("mechanisms", []):
        mech_id = str(mech.get("id", ""))
        mech_type = str(mech.get("type", ""))
        box = mech.get("parameter_box", {})
        if not mech_id or not mech_type or not isinstance(box, dict):
            continue
        grid = _grid_from_box(box)
        if not grid:
            continue

        # Build candidates for all points in the box.
        all_cands: List[Candidate] = []
        for p in grid:
            ordering = str(p.get("ordering", "NO"))
            params = dict(p)
            params.pop("ordering", None)
            all_cands.append(
                _candidate_from_params(
                    mech_id=mech_id,
                    mech_type=mech_type,
                    ordering=ordering,
                    params=params,
                    dm21=dm21,
                    dm31_no=dm31_no,
                    dm31_io=dm31_io,
                    bounds=bounds,
                    ue2=ue2,
                )
            )
        global_all.extend(all_cands)

        # CAP minimizer (raw).
        cap_best = min(all_cands, key=_cap_key)

        # Feasible minimizer under external bounds (audit-only filter).
        feasible = [c for c in all_cands if _passes_bounds(c.status)]
        feasible_best = min(feasible, key=_cap_key) if feasible else None

        def fmt_params(c: Candidate) -> str:
            parts = [f"{k}={c.params[k]}" for k in sorted(c.params.keys())]
            return "\\texttt{" + _tex_escape_texttt(",".join(parts)) + "}"

        def fmt_interval(c: Candidate) -> str:
            return f"$[{_fmt_ev(c.mbb_min)},{_fmt_ev(c.mbb_max)}]$"

        def emit_candidate(c: Candidate, sel: str) -> None:
            cand_rows.append(
                f"\\texttt{{{mech_id}}} & \\texttt{{{sel}}} & {c.ordering} & {fmt_params(c)} & "
                f"${_fmt_ev(c.m_lightest)}$ & ${_fmt_ev(c.sigma_mnu)}$ & ${_fmt_ev(c.m_beta)}$ & {fmt_interval(c)} \\\\"
            )
            score_rows.append(
                f"\\texttt{{{mech_id}}} & \\texttt{{{sel}}} & "
                f"\\texttt{{{c.status.get('sigma_mnu','-')}}} & \\texttt{{{c.status.get('m_beta','-')}}} & "
                f"\\texttt{{{c.status.get('m_beta_beta','-')}}} & \\texttt{{{c.status.get('delta_N_eff','-')}}} & "
                f"\\texttt{{{c.status.get('dm2_dm3','-')}}} \\\\"
            )

        emit_candidate(cap_best, sel="cap")
        if feasible_best is None:
            # Emit a placeholder row for the feasible slot.
            cand_rows.append(
                f"\\texttt{{{mech_id}}} & \\texttt{{feasible}} & $-$ & $-$ & $-$ & $-$ & $-$ & $-$ \\\\"
            )
            score_rows.append(
                f"\\texttt{{{mech_id}}} & \\texttt{{feasible}} & \\texttt{{-}} & \\texttt{{-}} & \\texttt{{-}} & \\texttt{{-}} & \\texttt{{-}} \\\\"
            )
        else:
            emit_candidate(feasible_best, sel="feasible")

    cand_rows.append("\\bottomrule")
    score_rows.append("\\bottomrule")

    # Global selection (audit): CAP minimizer and feasible minimizer across the entire registry.
    global_rows: List[str] = []
    global_summary: List[str] = []
    phase_rows: List[str] = []
    phase_summary: List[str] = []
    split_rows: List[str] = []
    split_summary: List[str] = []
    weinberg_rows: List[str] = []
    weinberg_summary: List[str] = []
    seesaw_rows: List[str] = []
    seesaw_summary: List[str] = []
    if global_all:
        g_cap = min(global_all, key=_global_key)
        g_feasible_list = [c for c in global_all if _passes_bounds(c.status)]
        g_feas = min(g_feasible_list, key=_global_key) if g_feasible_list else None
        # Protocol-only "proto" selector: target a fixed suppression exponent tied to the m=6 split sizes.
        X6 = sml.all_x6()
        bdry_cnt = sum(1 for w in X6 if sml.is_boundary_word(w))
        cyc_cnt = len(X6) - bdry_cnt
        k_target = 2 * cyc_cnt
        proto_pool = [c for c in global_all if c.r0 < 0]
        if proto_pool:
            g_proto = min(
                proto_pool,
                key=lambda c: (
                    abs(int(-c.r0) - int(k_target)),
                    c.comp,
                    c.mech_id,
                    (0 if c.ordering == "NO" else 1),
                    json.dumps(c.params, sort_keys=True),
                ),
            )
        else:
            g_proto = g_cap

        def fmt_params_full(c: Candidate) -> str:
            parts = [f"{k}={c.params[k]}" for k in sorted(c.params.keys())]
            return "\\texttt{" + _tex_escape_texttt(",".join(parts)) + "}"

        def fmt_interval_full(c: Candidate) -> str:
            return f"$[{_fmt_ev(c.mbb_min)},{_fmt_ev(c.mbb_max)}]$"

        global_rows.append(
            f"\\texttt{{cap}} & \\texttt{{{g_cap.mech_id}}} & {g_cap.ordering} & {fmt_params_full(g_cap)} & "
            f"${_fmt_ev(g_cap.m_lightest)}$ & ${_fmt_ev(g_cap.sigma_mnu)}$ & ${_fmt_ev(g_cap.m_beta)}$ & {fmt_interval_full(g_cap)} \\\\"
        )
        global_rows.append(
            f"\\texttt{{proto}} & \\texttt{{{g_proto.mech_id}}} & {g_proto.ordering} & {fmt_params_full(g_proto)} & "
            f"${_fmt_ev(g_proto.m_lightest)}$ & ${_fmt_ev(g_proto.sigma_mnu)}$ & ${_fmt_ev(g_proto.m_beta)}$ & {fmt_interval_full(g_proto)} \\\\"
        )

        # Weinberg operator scale (audit/interface): estimate Λ from the protocol-selected spectrum.
        base = g_proto
        m_max = float(max(base.m1, base.m2, base.m3))
        lam = _weinberg_scale_from_mnu(m_max_eV=m_max, c_max=1.0)
        r_lam = _log_phi(lam / M_E_GEV)
        m_star, mu_th, err = _nearest_threshold_m(lam, m_min=6, m_max=40)
        c_req = (2.0 * float(mu_th) * float(m_max) * 1.0e-9) / (V_EW_GEV * V_EW_GEV)
        weinberg_rows.append(
            rf"\texttt{{weinberg}} & {base.ordering} & ${_fmt_ev(m_max)}$ & ${lam:.6g}$ & {r_lam:.3f} & {m_star} & ${mu_th:.6g}$ & ${err:.3f}$ & ${c_req:.6g}$ \\"
        )
        weinberg_rows.append("\\bottomrule")
        weinberg_summary.append(
            rf"\textbf{{Weinberg scale (audit):}} using $m_{{\nu,\max}}={_fmt_ev(m_max)}\,\mathrm{{eV}}$ and $v=246\,\mathrm{{GeV}}$, "
            rf"the coefficient-normalized estimate gives $\Lambda_W={lam:.6g}\,\mathrm{{GeV}}$; "
            rf"the nearest staircase threshold is $m={m_star}$ with $\mu_\mathrm{{th}}={mu_th:.6g}\,\mathrm{{GeV}}$ (log mismatch {err:.3f})."
        )

        # Type-I seesaw scale (audit/interface): single-scale estimate with a bounded Yukawa-magnitude family.
        # Candidate family: y_eff in {1} ∪ {up-type and charged-lepton Yukawas from the closed depth template}.
        def word_for_field() -> Dict[Tuple[int, str], str]:
            X6_local = sml.all_x6()
            cyc = [w for w in X6_local if not sml.is_boundary_word(w)]
            cyc_sorted = sorted(cyc, key=lambda w: sml.stable_type_sort_key(w))
            fields = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
            if len(cyc_sorted) != len(fields):
                raise AssertionError("Labeling map size mismatch.")
            return {(f.generation, f.name): w for w, f in zip(cyc_sorted, fields)}

        wf = word_for_field()

        def yukawa_pred(gen: int, name: str) -> float:
            w = wf[(gen, name)]
            rh = _r_hat_base_x6(w)
            m_pred_GeV = float(M_E_GEV) * float(PHI**float(rh))
            return math.sqrt(2.0) * m_pred_GeV / float(V_EW_GEV)

        y_candidates: List[Tuple[str, float, Tuple[int, int, str]]] = []
        y_candidates.append(("1", 1.0, (0, 0, "1")))
        for g in (1, 2, 3):
            y_candidates.append((f"u_R^{g}", yukawa_pred(g, "u_R"), (1, g, "u_R")))
        for g in (1, 2, 3):
            y_candidates.append((f"e_R^{g}", yukawa_pred(g, "e_R"), (2, g, "e_R")))

        if not y_candidates:
            seesaw_rows.append(r"\texttt{cap} & $-$ & $-$ & $-$ & $-$ & $-$ & $-$ \\")
            seesaw_rows.append(r"\texttt{match} & $-$ & $-$ & $-$ & $-$ & $-$ & $-$ \\")
            seesaw_rows.append("\\bottomrule")
            seesaw_summary.append(r"\textbf{Seesaw scale (audit):} \textit{pending} (empty Yukawa candidate family).")
        else:
            # cap: minimize candidate complexity only (tie-break by declared order key_info)
            cap_label, cap_y, cap_keyinfo = min(y_candidates, key=lambda t: t[2])
            cap_mr = _seesaw_mr_from_mnu(m_max_eV=m_max, y_eff=cap_y)
            cap_mR_star, cap_muR_th, cap_errR = _nearest_threshold_m(cap_mr, m_min=6, m_max=40)

            # match: minimize mismatch to the staircase thresholds (tie-break by key_info)
            best_match = None
            best_match_key = None
            for label, y, key_info in y_candidates:
                mr = _seesaw_mr_from_mnu(m_max_eV=m_max, y_eff=y)
                mR_star, muR_th, errR = _nearest_threshold_m(mr, m_min=6, m_max=40)
                key = (errR, key_info)
                if best_match is None or key < best_match_key:
                    best_match = (label, y, mr, mR_star, muR_th, errR)
                    best_match_key = key
            assert best_match is not None
            match_label, match_y, match_mr, match_mR_star, match_muR_th, match_errR = best_match

            seesaw_rows.append(
                rf"\texttt{{cap}} & \texttt{{{_tex_escape_texttt(cap_label)}}} & ${cap_y:.6g}$ & ${cap_mr:.6g}$ & {cap_mR_star} & ${cap_muR_th:.6g}$ & ${cap_errR:.3f}$ \\"
            )
            seesaw_rows.append(
                rf"\texttt{{match}} & \texttt{{{_tex_escape_texttt(match_label)}}} & ${match_y:.6g}$ & ${match_mr:.6g}$ & {match_mR_star} & ${match_muR_th:.6g}$ & ${match_errR:.3f}$ \\"
            )
            seesaw_rows.append("\\bottomrule")
            seesaw_summary.append(
                rf"\textbf{{Seesaw scale (audit):}} with $m_{{\nu,\max}}={_fmt_ev(m_max)}\,\mathrm{{eV}}$, "
                rf"the protocol-only \texttt{{cap}} rule selects $y_{{\nu,\mathrm{{eff}}}}={cap_y:.6g}$ (\texttt{{{_tex_escape_texttt(cap_label)}}}) giving $M_R={cap_mr:.6g}\,\mathrm{{GeV}}$; "
                rf"the \texttt{{match}} rule minimizes threshold mismatch and selects $y_{{\nu,\mathrm{{eff}}}}={match_y:.6g}$ (\texttt{{{_tex_escape_texttt(match_label)}}}) giving $M_R={match_mr:.6g}\,\mathrm{{GeV}}$."
            )
        if g_feas is None:
            global_rows.append(r"\texttt{feasible} & $-$ & $-$ & $-$ & $-$ & $-$ & $-$ & $-$ \\")
            global_summary.append(
                r"\textbf{Global mechanism selection:} no feasible candidate in the declared registry under the recorded external bounds."
            )
        else:
            global_rows.append(
                f"\\texttt{{feasible}} & \\texttt{{{g_feas.mech_id}}} & {g_feas.ordering} & {fmt_params_full(g_feas)} & "
                f"${_fmt_ev(g_feas.m_lightest)}$ & ${_fmt_ev(g_feas.sigma_mnu)}$ & ${_fmt_ev(g_feas.m_beta)}$ & {fmt_interval_full(g_feas)} \\\\"
            )
            global_summary.append(
                rf"\textbf{{Global mechanism selection (audit):}} feasible CAP-minimizer is \texttt{{{g_feas.mech_id}}} "
                rf"({g_feas.ordering}) with $m_{{\mathrm{{lightest}}}}={_fmt_ev(g_feas.m_lightest)}\,\mathrm{{eV}}$."
            )

            # Splitting-closure attempt (audit): bounded rational offsets in r-coordinate.
            split_cands = _split_family_candidates(
                m0=float(g_feas.m_lightest),
                dm21_ref=float(dm21),
                dm31_no_ref=float(dm31_no),
                dm31_io_ref=float(dm31_io),
                q_max=12,
            )
            for sc in split_cands:
                label_a = r"$\Delta r_{21}$" if sc.ordering == "NO" else r"$\Delta r_{13}$"
                label_b = r"$\Delta r_{31}$" if sc.ordering == "NO" else r"$\Delta r_{23}$"
                split_rows.append(
                    rf"\texttt{{{sc.selection}}} & {sc.ordering} & {sc.q} & "
                    rf"{label_a}={_fmt_ratio(sc.k_a, sc.q)} & {label_b}={_fmt_ratio(sc.k_b, sc.q)} & "
                    rf"${_fmt_ev(sc.dm21)}$ & ${_fmt_ev(sc.dm3_abs)}$ & ${sc.max_log_mismatch:.3f}$ & \texttt{{{sc.status}}} \\"
                )
            if split_rows:
                split_rows.append("\\bottomrule")
            split_summary.append(
                r"\textbf{Splitting closure attempt (audit):} bounded rational r-offsets with $q\le 12$ are evaluated in three modes: "
                r"(\texttt{cap}) protocol-only CAP-minimizer by denominator/numerator complexity, "
                r"(\texttt{proto}) an invariant-derived candidate at the $m=6$ anchor (18$\oplus$3 split), "
                r"and (\texttt{match}) mismatch-minimizer to the recorded oscillation splittings."
            )

            # Majorana phase closure (audit): bounded rational multiples of π with feasibility under m_{ββ} bound.
            mbb_bound = bounds.get("m_beta_beta", None)
            if mbb_bound is None or not math.isfinite(float(mbb_bound)) or float(mbb_bound) <= 0.0:
                phase_rows.append(r"\texttt{majorana} & \texttt{cap} & $-$ & $-$ & $-$ \\")
                phase_summary.append(r"\textbf{Majorana phase closure:} \textit{pending} (missing m_{\beta\beta} bound input).")
            else:
                B = float(mbb_bound)
                denom_list = [1, 2, 4, 8]

                def phase_complexity(den: int, k: int) -> tuple[int, int, int]:
                    # Complexity: smaller denominator first; then smaller distance to 0 (mod 2π); tie by k.
                    kmod = k % (2 * den)
                    dist = min(kmod, 2 * den - kmod)
                    return den, dist, kmod

                best = None
                best_key = None
                for d21 in denom_list:
                    for k21 in range(0, 2 * d21):
                        a21 = float(k21) * math.pi / float(d21)
                        for d31 in denom_list:
                            for k31 in range(0, 2 * d31):
                                a31 = float(k31) * math.pi / float(d31)
                                mbb = _m_bb_with_phases(
                                    m1=g_feas.m1,
                                    m2=g_feas.m2,
                                    m3=g_feas.m3,
                                    ue=ue_complex,
                                    alpha21=a21,
                                    alpha31=a31,
                                )
                                if mbb > B:
                                    continue
                                key = (
                                    max(phase_complexity(d21, k21)[0], phase_complexity(d31, k31)[0]),
                                    phase_complexity(d21, k21),
                                    phase_complexity(d31, k31),
                                )
                                if best is None or key < best_key:
                                    best = (d21, k21, d31, k31, a21, a31, mbb)
                                    best_key = key

                if best is None:
                    phase_rows.append(
                        rf"\texttt{{majorana}} & \texttt{{cap}} & {g_feas.ordering} & \texttt{{{g_feas.mech_id}}} & \texttt{{EXCLUDED}} \\"
                    )
                    phase_summary.append(
                        rf"\textbf{{Majorana phase closure:}} no phase pair in the bounded family satisfies $m_{{\beta\beta}}\le {B}\,\mathrm{{eV}}$ for the selected spectrum."
                    )
                else:
                    d21, k21, d31, k31, a21, a31, mbb = best
                    phase_rows.append(
                        rf"\texttt{{majorana}} & \texttt{{cap}} & {g_feas.ordering} & \texttt{{{g_feas.mech_id}}} & "
                        rf"$\alpha_{{21}}={k21}\pi/{d21}$, $\alpha_{{31}}={k31}\pi/{d31}$, $m_{{\beta\beta}}={_fmt_ev(mbb)}\,\mathrm{{eV}}$ \\"
                    )
                    phase_summary.append(
                        rf"\textbf{{Majorana phase closure (audit):}} bounded family yields $\alpha_{{21}}={k21}\pi/{d21}$, "
                        rf"$\alpha_{{31}}={k31}\pi/{d31}$ with $m_{{\beta\beta}}={_fmt_ev(mbb)}\,\mathrm{{eV}}$."
                    )
        global_rows.append("\\bottomrule")
    else:
        global_rows = [r"\texttt{cap} & $-$ & $-$ & $-$ & $-$ & $-$ & $-$ & $-$ \\", r"\bottomrule"]
        global_summary = [r"\textbf{Global mechanism selection:} \textit{pending} (empty registry)."]
        phase_rows = [r"\texttt{majorana} & \texttt{cap} & $-$ & $-$ & $-$ \\"]
        phase_summary = [r"\textbf{Majorana phase closure:} \textit{pending} (empty registry)."]
        split_rows = [r"\texttt{cap} & $-$ & $-$ & $-$ & $-$ & $-$ & $-$ & $-$ & \texttt{PENDING} \\", r"\bottomrule"]
        split_summary = [r"\textbf{Splitting closure attempt:} \textit{pending} (empty registry)."]
        weinberg_rows = [r"\texttt{weinberg} & $-$ & $-$ & $-$ & $-$ & $-$ & $-$ & $-$ & $-$ \\", r"\bottomrule"]
        weinberg_summary = [r"\textbf{Weinberg scale (audit):} \textit{pending} (empty registry)."]
        seesaw_rows = [r"\texttt{seesaw} & $-$ & $-$ & $-$ & $-$ & $-$ & $-$ \\", r"\bottomrule"]
        seesaw_summary = [r"\textbf{Seesaw scale (audit):} \textit{pending} (empty registry)."]

    out_dir = root / "sections" / "generated"
    write_lines(out_dir / "neutrino_mechanism_candidates_rows.tex", cand_rows)
    write_lines(out_dir / "neutrino_mechanism_scoreboard_rows.tex", score_rows)
    write_lines(out_dir / "neutrino_mechanism_global_rows.tex", global_rows)
    write_lines(out_dir / "neutrino_mechanism_global_summary.tex", global_summary)
    if not phase_rows:
        phase_rows = [r"\texttt{majorana} & \texttt{cap} & $-$ & $-$ & $-$ \\"]
    write_lines(out_dir / "neutrino_majorana_phase_closure_rows.tex", phase_rows + ["\\bottomrule"])
    write_lines(out_dir / "neutrino_majorana_phase_closure_summary.tex", phase_summary)
    write_lines(out_dir / "neutrino_splitting_depth_closure_rows.tex", split_rows)
    write_lines(out_dir / "neutrino_splitting_depth_closure_summary.tex", split_summary)
    write_lines(out_dir / "neutrino_weinberg_scale_rows.tex", weinberg_rows)
    write_lines(out_dir / "neutrino_weinberg_scale_summary.tex", weinberg_summary)
    write_lines(out_dir / "neutrino_seesaw_scale_rows.tex", seesaw_rows)
    write_lines(out_dir / "neutrino_seesaw_scale_summary.tex", seesaw_summary)
    print("Wrote sections/generated/neutrino_mechanism_candidates_rows.tex")
    print("Wrote sections/generated/neutrino_mechanism_scoreboard_rows.tex")
    print("Wrote sections/generated/neutrino_mechanism_global_rows.tex")
    print("Wrote sections/generated/neutrino_mechanism_global_summary.tex")
    print("Wrote sections/generated/neutrino_majorana_phase_closure_rows.tex")
    print("Wrote sections/generated/neutrino_majorana_phase_closure_summary.tex")
    print("Wrote sections/generated/neutrino_splitting_depth_closure_rows.tex")
    print("Wrote sections/generated/neutrino_splitting_depth_closure_summary.tex")
    print("Wrote sections/generated/neutrino_weinberg_scale_rows.tex")
    print("Wrote sections/generated/neutrino_weinberg_scale_summary.tex")
    print("Wrote sections/generated/neutrino_seesaw_scale_rows.tex")
    print("Wrote sections/generated/neutrino_seesaw_scale_summary.tex")


if __name__ == "__main__":
    main()

