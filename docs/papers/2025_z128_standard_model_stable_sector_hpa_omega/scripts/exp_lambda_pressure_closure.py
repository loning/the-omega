# -*- coding: utf-8 -*-
"""
Lambda pressure closure (audit generator).

This script implements Appendix 58's finite-family pressure-based closure for the
vacuum normalization:

  Omega_{Lambda,0} ∈ { s_k, 1 - s_k } with k in a bounded dyadic index set.

Selection is performed by a deterministic complexity-first tie-break within the declared
finite family. External targets (Planck-2018) are used only for mismatch reporting.

Outputs (LaTeX fragments):
  - sections/generated/lambda_pressure_closure_equations.tex
  - sections/generated/lambda_pressure_closure_summary.tex

Design goals (repo conventions):
  - Deterministic output (no timestamps).
  - English-only script output.
  - Standard-library only.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import exp_cosmology_energy_budget_fit as cosmo_fit
from common_paths import generated_dir, paper_root
from common_tex import write_lines


PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
LOG2_PHI: float = math.log(PHI) / math.log(2.0)

# Z128 baseline: at the anchor window m=6 one uses p=m+1=7 (i.e., Z_{2^p}=Z_128).
# See subsec:z128_label in the paper.
Z128_P: int = 7

# Dyadic pressure-family index set K = {0,1,...,K_MAX} (finite, auditable).
K_MAX: int = 8
K_DEFAULT: List[int] = list(range(0, K_MAX + 1))

# Exact SI speed of light.
C_M_S: float = 299_792_458.0

# 1 Mpc in meters (exact via IAU parsec definition; fixed literal for determinism).
MPC_M: float = 3.085_677_581_491_367_3e22

def _read_h0_candidates() -> List[Tuple[str, float, float]]:
    """
    Load a finite audit family of H0 candidates (km/s/Mpc).
    Each entry is (id, value, sigma_sym).
    """
    p = paper_root() / "data" / "cosmology_lambda" / "h0_candidates.json"
    if not p.is_file():
        return []
    obj = _read_json(p)
    cands = obj.get("candidates", None)
    if not isinstance(cands, list):
        raise TypeError("Expected h0_candidates.json:candidates to be a list.")
    out: List[Tuple[str, float, float]] = []
    for c in cands:
        if not isinstance(c, dict):
            continue
        cid = c.get("id", None)
        h0 = c.get("H0_km_s_Mpc", None)
        if not isinstance(cid, str) or not isinstance(h0, dict):
            continue
        v = _require_float(h0, "value")
        s = _require_float(h0, "sigma")
        if v <= 0.0 or s < 0.0 or (not math.isfinite(v)) or (not math.isfinite(s)):
            continue
        out.append((cid, float(v), float(s)))
    return out


def _select_h0_by_precision(cands: List[Tuple[str, float, float]]) -> Tuple[str, float, float]:
    """
    Deterministic audit closure for H0 from a finite candidate family:
    select the candidate with minimal fractional uncertainty sigma/H0.
    Tie-break: smaller sigma, then smaller H0, then lexicographic id.
    """
    if not cands:
        raise ValueError("Empty H0 candidate family.")

    def _key(x: Tuple[str, float, float]) -> Tuple[float, float, float, str]:
        cid, h0, sig = x
        frac = (sig / h0) if h0 > 0.0 else float("inf")
        return (frac, sig, h0, cid)

    return min(cands, key=_key)


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_float(obj: Dict[str, Any], key: str) -> float:
    v = obj.get(key, None)
    if not isinstance(v, (int, float)):
        raise TypeError(f"Expected '{key}' to be a number, got {type(v).__name__}.")
    return float(v)


def _fmt_sci_tex(x: float, digits: int = 6) -> str:
    """
    Stable LaTeX-friendly scientific notation: a×10^{b}.
    """
    if not math.isfinite(x):
        return "nan"
    if x == 0.0:
        return "0"
    s = f"{x:.{max(1, int(digits))}e}"
    mant, exp = s.split("e")
    e = int(exp)
    if e == 0:
        return mant
    return f"{mant}\\times 10^{{{e}}}"


def _fmt_float(x: float, digits: int) -> str:
    return f"{x:.{int(digits)}f}"


def _h0_km_s_mpc_to_sinv(h0_km_s_mpc: float) -> float:
    return float(h0_km_s_mpc) * 1000.0 / MPC_M


def _lambda_from_h0_omega(h0_km_s_mpc: float, omega_lambda0: float) -> float:
    h0_sinv = _h0_km_s_mpc_to_sinv(h0_km_s_mpc)
    return 3.0 * (h0_sinv * h0_sinv) * float(omega_lambda0) / (C_M_S * C_M_S)


@dataclass(frozen=True)
class Targets:
    h0: Optional[float]
    h0_sigma: Optional[float]
    omega_lambda0: Optional[float]
    omega_lambda0_sigma: Optional[float]
    omega_m0: Optional[float]
    omega_m0_sigma: Optional[float]
    omega_b0: Optional[float]
    omega_b0_sigma: Optional[float]


def _maybe_read_value_sigma(targets: Dict[str, Any], key: str) -> Optional[Tuple[float, float]]:
    obj = targets.get(key, None)
    if obj is None:
        return None
    if not isinstance(obj, dict):
        raise TypeError(f"Expected targets.{key} to be an object.")
    v = _require_float(obj, "value")
    s = _require_float(obj, "sigma")
    if not math.isfinite(v) or not math.isfinite(s):
        raise ValueError(f"Non-finite targets.{key} value/sigma.")
    if s < 0.0:
        raise ValueError(f"targets.{key}.sigma must be >= 0.")
    return (v, s)


def _load_targets() -> Targets:
    p = paper_root() / "data" / "cosmology_lambda" / "planck2018_targets.json"
    obj = _read_json(p)
    targets = obj.get("targets", None)
    if not isinstance(targets, dict):
        raise TypeError("Expected top-level key 'targets' to be an object.")

    h0: Optional[float] = None
    h0_sigma: Optional[float] = None
    omega: Optional[float] = None
    omega_sigma: Optional[float] = None

    h0_pair = _maybe_read_value_sigma(targets, "H0")
    if h0_pair is not None:
        h0, h0_sigma = h0_pair
        if h0 <= 0.0:
            raise ValueError("H0 must be positive.")
        if h0_sigma < 0.0:
            raise ValueError("H0 sigma must be >= 0.")

    omega_pair = _maybe_read_value_sigma(targets, "OmegaLambda0")
    if omega_pair is not None:
        omega, omega_sigma = omega_pair
        if not (0.0 < float(omega) < 1.0):
            raise ValueError("OmegaLambda0 must be in (0,1).")
        if float(omega_sigma) < 0.0:
            raise ValueError("OmegaLambda0 sigma must be >= 0.")

    omega_m_pair = _maybe_read_value_sigma(targets, "OmegaM0")
    omega_m0: Optional[float] = None
    omega_m0_sigma: Optional[float] = None
    if omega_m_pair is not None:
        omega_m0, omega_m0_sigma = omega_m_pair
        if not (0.0 < float(omega_m0) < 1.0):
            raise ValueError("OmegaM0 must be in (0,1).")

    omega_b_pair = _maybe_read_value_sigma(targets, "OmegaB0")
    omega_b0: Optional[float] = None
    omega_b0_sigma: Optional[float] = None
    if omega_b_pair is not None:
        omega_b0, omega_b0_sigma = omega_b_pair
        if not (0.0 < float(omega_b0) < 1.0):
            raise ValueError("OmegaB0 must be in (0,1).")

    return Targets(
        h0=h0,
        h0_sigma=h0_sigma,
        omega_lambda0=omega,
        omega_lambda0_sigma=omega_sigma,
        omega_m0=omega_m0,
        omega_m0_sigma=omega_m0_sigma,
        omega_b0=omega_b0,
        omega_b0_sigma=omega_b0_sigma,
    )


@dataclass(frozen=True)
class Candidate:
    name: str
    omega: float
    log_mismatch: float
    k: int
    variant: str  # "share" or "complement"

    def key(self) -> Tuple[float, int, int]:
        # Deterministic tie-break: smaller |log mismatch|, then smaller k, then share before complement.
        return (abs(self.log_mismatch), int(self.k), 0 if self.variant == "share" else 1)


def _dyadic_weighted_gm_share(k: int) -> float:
    """
    Dyadic-weighted golden-mean transfer matrix:
      A_k = [[1, 2^{-k}],
             [1,      0]]
    Spectral radius: lambda_k = (1 + sqrt(1 + 4*2^{-k})) / 2.
    Candidate share: s_k = log_2(lambda_k).
    """
    if k < 0:
        raise ValueError("k must be >= 0.")
    w = 2.0 ** (-float(k))
    lam = 0.5 * (1.0 + math.sqrt(1.0 + 4.0 * w))
    return math.log(lam) / math.log(2.0)


def _iter_candidates(omega_ref: float, ks: Iterable[int]) -> List[Candidate]:
    out: List[Candidate] = []
    for k in ks:
        s_k = float(_dyadic_weighted_gm_share(int(k)))
        out.append(
            Candidate(
                name=f"k{int(k)}-share",
                omega=s_k,
                log_mismatch=math.log(s_k / omega_ref),
                k=int(k),
                variant="share",
            )
        )
        out.append(
            Candidate(
                name=f"k{int(k)}-comp",
                omega=float(1.0 - s_k),
                log_mismatch=math.log((1.0 - s_k) / omega_ref),
                k=int(k),
                variant="complement",
            )
        )
    return out


def _select_candidate(omega_ref: float) -> Candidate:
    """
    Return the deterministic best candidate under absolute log-mismatch, with a fixed tie-break.
    """
    if not (0.0 < float(omega_ref) < 1.0):
        raise ValueError("omega_ref must be in (0,1).")
    cands = _iter_candidates(omega_ref, K_DEFAULT)
    best = min(cands, key=lambda c: c.key())
    return best


def _select_by_complexity(ks: Iterable[int]) -> Tuple[str, float, int]:
    """
    Deterministic finite-family selection rule:
      k_* := min K,  Omega_hat := s_{k_*} (share is preferred over complement).
    Returns (name, omega_hat, k_star).
    """
    ks_list = sorted(set(int(k) for k in ks))
    if not ks_list:
        raise ValueError("Empty candidate index set.")
    k_star = int(ks_list[0])
    omega_hat = float(_dyadic_weighted_gm_share(k_star))
    return (f"k{k_star}-share", omega_hat, k_star)


def _abs_log_ratio(a: float, b: float) -> float:
    if a <= 0.0 or b <= 0.0:
        return float("inf")
    return abs(math.log(a / b))


def _tex_escape(s: str) -> str:
    # Minimal TeX escaping for audit ids in \texttt{...}.
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("#", "\\#")
        .replace("&", "\\&")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )


def _sigma_lambda_from_h0_omega(
    lambda_val: float,
    h0: float,
    h0_sigma: float,
    omega: float,
    omega_sigma: float,
) -> float:
    """
    First-order propagation (independent uncertainties):
      Lambda ∝ H0^2 * Omega
      => (σ/L)^2 = (2σ_H0/H0)^2 + (σ_Omega/Omega)^2
    """
    if lambda_val <= 0.0:
        return 0.0
    if h0 <= 0.0 or omega <= 0.0:
        return 0.0
    r_h0 = 2.0 * float(h0_sigma) / float(h0) if float(h0_sigma) > 0.0 else 0.0
    r_om = float(omega_sigma) / float(omega) if float(omega_sigma) > 0.0 else 0.0
    return float(lambda_val) * math.sqrt(r_h0 * r_h0 + r_om * r_om)


def _read_h0licow_h0() -> Optional[Tuple[float, float]]:
    """
    Read a compact late-time H0 proxy from the existing vendored time-delay JSON used by the gamma audit.
    Returns (H0, sigma_sym) in km/s/Mpc, or None if not available.
    """
    p = paper_root() / "data" / "gamma_crossobs" / "strong_lensing" / "h0_time_delay.json"
    if not p.is_file():
        return None
    obj = _read_json(p)
    meas = obj.get("measurements", None)
    if not isinstance(meas, list) or not meas:
        return None
    m0 = meas[0]
    if not isinstance(m0, dict):
        return None
    v = m0.get("value", None)
    sp = m0.get("sigma_plus", None)
    sm = m0.get("sigma_minus", None)
    if not isinstance(v, (int, float)) or not isinstance(sp, (int, float)) or not isinstance(sm, (int, float)):
        return None
    sigma = 0.5 * (float(sp) + float(sm))
    return (float(v), float(sigma))


def main() -> None:
    t = _load_targets()

    # Finite candidate family for Omega_{Lambda,0} (explicit).
    ks = list(K_DEFAULT)

    # Finite-family closure output (complexity-first; independent of matching targets).
    sel_name, omega_hat, k_star = _select_by_complexity(ks)

    omega_ref = float(t.omega_lambda0) if t.omega_lambda0 is not None else None
    omega_ref_sigma = float(t.omega_lambda0_sigma) if t.omega_lambda0_sigma is not None else None
    log_mismatch = (
        math.log(omega_hat / omega_ref) if (omega_ref is not None and omega_ref > 0.0) else float("nan")
    )

    # Matching-layer diagnostic: mismatch-minimizer and its ±1σ stability (if a reference is provided).
    best_mm: Optional[Candidate] = _select_candidate(omega_ref) if omega_ref is not None else None
    mismatch_minimizer_agrees = (best_mm is not None) and (best_mm.name == sel_name)
    mismatch_minimizer_stable = False
    if best_mm is not None and omega_ref_sigma is not None:
        omega_lo = max(1e-12, float(omega_ref) - float(omega_ref_sigma))
        omega_hi = min(1.0 - 1e-12, float(omega_ref) + float(omega_ref_sigma))
        best_mm_lo = _select_candidate(omega_lo)
        best_mm_hi = _select_candidate(omega_hi)
        mismatch_minimizer_stable = (best_mm_lo.name == best_mm.name) and (best_mm_hi.name == best_mm.name)

    # Matching-layer diagnostic: MDL-penalized mismatch minimizer over the same finite family.
    best_mm_mdl: Optional[Candidate] = None
    mismatch_mdl_agrees = False
    if omega_ref is not None:
        cands_mdl = _iter_candidates(float(omega_ref), ks)

        def _mdl_key(c: Candidate) -> Tuple[float, int, int]:
            # Simple MDL proxy: data cost = |log mismatch|, model cost = k·ln 2 (dyadic-weight index).
            score = abs(float(c.log_mismatch)) + (math.log(2.0) * float(c.k))
            return (float(score), int(c.k), 0 if c.variant == "share" else 1)

        best_mm_mdl = min(cands_mdl, key=_mdl_key)
        mismatch_mdl_agrees = best_mm_mdl.name == sel_name

    # Complementary matter fraction implied by the chosen Omega_{Lambda,0}.
    omega_m_hat = 1.0 - omega_hat
    omega_m_ref: Optional[float] = None
    if t.omega_m0 is not None:
        omega_m_ref = float(t.omega_m0)
    elif omega_ref is not None:
        omega_m_ref = 1.0 - float(omega_ref)
    omega_m_log_mismatch = (
        math.log(omega_m_hat / omega_m_ref)
        if (omega_m_ref is not None and omega_m_hat > 0.0 and omega_m_ref > 0.0)
        else float("nan")
    )

    # Baryon/matter split diagnostic (Appendix 32): fix a Z128-tied resolution point m_b^* and treat Planck as audit only.
    m_b_star = 2 * int(Z128_P) + 1
    _b_num, _b_den, omega_b_hat = cosmo_fit.f_stab(int(m_b_star))
    omega_b_ref = float(t.omega_b0) if t.omega_b0 is not None else None
    omega_b_ref_sigma = float(t.omega_b0_sigma) if t.omega_b0_sigma is not None else None

    omega_dm_hat = max(0.0, omega_m_hat - omega_b_hat)
    dm_over_b_hat = omega_dm_hat / omega_b_hat if omega_b_hat > 0.0 else float("nan")

    dm_over_b_ref = float("nan")
    dm_over_b_log_mismatch = float("nan")
    if omega_m_ref is not None and omega_b_ref is not None and omega_b_ref > 0.0:
        omega_dm_ref = max(0.0, float(omega_m_ref) - float(omega_b_ref))
        if omega_dm_ref > 0.0:
            dm_over_b_ref = omega_dm_ref / float(omega_b_ref)
            if dm_over_b_hat > 0.0:
                dm_over_b_log_mismatch = math.log(dm_over_b_hat / dm_over_b_ref)

    # Matching-layer diagnostic: baryon mismatch-minimizer for m_* and its stability (if Omega_b^ref is provided).
    best_m_baryon: Optional[cosmo_fit.FitResult] = None
    m_baryon_mm_agrees = False
    m_baryon_mm_stable = False
    ms_allowed_sorted: List[int] = []
    ms_allowed_tex = ""
    dm_over_b_log_mismatch_min: float = float("nan")
    dm_over_b_log_mismatch_max: float = float("nan")
    if omega_b_ref is not None:
        best_m_baryon = cosmo_fit.best_fit_m(omega_vis0=float(omega_b_ref), m_min=6, m_max=40)
        m_baryon_mm_agrees = int(best_m_baryon.m_star) == int(m_b_star)
        ms_allowed = cosmo_fit.stability_ms(
            omega_vis0=float(omega_b_ref),
            omega_vis0_sigma=float(omega_b_ref_sigma) if omega_b_ref_sigma is not None else 0.0,
            m_min=6,
            m_max=40,
        )
        ms_allowed_sorted = sorted(set(int(m) for m in ms_allowed))
        ms_allowed_tex = ",".join(str(m) for m in ms_allowed_sorted)
        m_baryon_mm_stable = (len(ms_allowed_sorted) == 1) and (ms_allowed_sorted[0] == int(best_m_baryon.m_star))

        if ms_allowed_sorted and (dm_over_b_ref > 0.0 and math.isfinite(dm_over_b_ref)):
            vals: List[float] = []
            for m in ms_allowed_sorted:
                _n, _d, fstab_m = cosmo_fit.f_stab(int(m))
                omega_b_hat_m = float(fstab_m)
                if omega_b_hat_m <= 0.0:
                    continue
                omega_dm_hat_m = max(0.0, omega_m_hat - omega_b_hat_m)
                dm_over_b_hat_m = omega_dm_hat_m / omega_b_hat_m if omega_b_hat_m > 0.0 else float("nan")
                if dm_over_b_hat_m > 0.0:
                    vals.append(math.log(dm_over_b_hat_m / float(dm_over_b_ref)))
            if vals:
                dm_over_b_log_mismatch_min = float(min(vals))
                dm_over_b_log_mismatch_max = float(max(vals))

    # Matching-layer diagnostic: multi-target mismatch-minimizer (Omega_Lambda0, Omega_m0, DM/baryon ratio).
    best_mm_multi: Optional[Candidate] = None
    mismatch_minimizer_multi_agrees = False
    best_mm_multi_mdl: Optional[Candidate] = None
    mismatch_mdl_multi_agrees = False
    if omega_ref is not None and omega_m_ref is not None and (dm_over_b_ref > 0.0 and math.isfinite(dm_over_b_ref)):
        cands_mm = _iter_candidates(float(omega_ref), ks)

        def _multi_key(c: Candidate) -> Tuple[float, float, float, int, int]:
            omega_c = float(c.omega)
            m1 = abs(float(c.log_mismatch))
            m2 = _abs_log_ratio(1.0 - omega_c, float(omega_m_ref))
            dm_over_b_hat_c = (
                (max(0.0, (1.0 - omega_c) - omega_b_hat) / omega_b_hat) if omega_b_hat > 0.0 else float("inf")
            )
            m3 = _abs_log_ratio(dm_over_b_hat_c, float(dm_over_b_ref))
            return (m1, m2, m3, int(c.k), 0 if c.variant == "share" else 1)

        best_mm_multi = min(cands_mm, key=_multi_key)
        mismatch_minimizer_multi_agrees = best_mm_multi.name == sel_name

        def _multi_mdl_key(c: Candidate) -> Tuple[float, int, int]:
            omega_c = float(c.omega)
            m1 = abs(float(c.log_mismatch))
            m2 = _abs_log_ratio(1.0 - omega_c, float(omega_m_ref))
            dm_over_b_hat_c = (
                (max(0.0, (1.0 - omega_c) - omega_b_hat) / omega_b_hat) if omega_b_hat > 0.0 else float("inf")
            )
            m3 = _abs_log_ratio(dm_over_b_hat_c, float(dm_over_b_ref))
            score = float(m1 + m2 + m3) + (math.log(2.0) * float(c.k))
            return (score, int(c.k), 0 if c.variant == "share" else 1)

        best_mm_multi_mdl = min(cands_mm, key=_multi_mdl_key)
        mismatch_mdl_multi_agrees = best_mm_multi_mdl.name == sel_name

    # H0 finite-family audit closure (used for Lambda calibration).
    h0_family = _read_h0_candidates()
    # Backfill from the existing vendored time-delay proxy if not present.
    td = _read_h0licow_h0()
    if td is not None and not any("h0licow" in cid.lower() for cid, _, _ in h0_family):
        h0_family.append(("h0licow-xiii", float(td[0]), float(td[1])))
    # Backfill the Planck H0 target if available.
    if t.h0 is not None and t.h0_sigma is not None and not any("planck" in cid.lower() for cid, _, _ in h0_family):
        h0_family.append(("planck2018", float(t.h0), float(t.h0_sigma)))
    if not h0_family:
        raise RuntimeError("Empty H0 candidate family (no candidates and no fallback targets).")

    h0_hat_id, h0_hat, h0_hat_sigma = _select_h0_by_precision(h0_family)

    lambda_hat = _lambda_from_h0_omega(h0_hat, omega_hat)
    sigma_lambda_hat = _sigma_lambda_from_h0_omega(
        lambda_val=lambda_hat,
        h0=h0_hat,
        h0_sigma=h0_hat_sigma,
        omega=omega_hat,
        omega_sigma=0.0,
    )

    lambda_ref: Optional[float] = None
    sigma_lambda_ref: Optional[float] = None
    if omega_ref is not None and t.h0 is not None and t.h0_sigma is not None and omega_ref_sigma is not None:
        lambda_ref = _lambda_from_h0_omega(float(t.h0), float(omega_ref))
        sigma_lambda_ref = _sigma_lambda_from_h0_omega(
            lambda_val=float(lambda_ref),
            h0=float(t.h0),
            h0_sigma=float(t.h0_sigma),
            omega=float(omega_ref),
            omega_sigma=float(omega_ref_sigma),
        )

    # H0-family sensitivity diagnostics (holding Omega_hat fixed).
    h0_sensitivity_parts: List[str] = []
    for cid, h0_v, h0_s in sorted(h0_family, key=lambda x: x[0]):
        lam_v = _lambda_from_h0_omega(h0_v, omega_hat)
        lam_s = _sigma_lambda_from_h0_omega(lambda_val=lam_v, h0=h0_v, h0_sigma=h0_s, omega=omega_hat, omega_sigma=0.0)
        h0_sensitivity_parts.append(
            f"\\texttt{{{_tex_escape(cid)}}}: "
            f"$\\widehat\\Lambda={_fmt_sci_tex(lam_v, 6)}\\pm{_fmt_sci_tex(lam_s, 6)}\\,\\mathrm{{m^{{-2}}}}$"
        )
    h0_sensitivity_tex = "; ".join(h0_sensitivity_parts)

    # Candidate snapshot (explicit, finite).
    # Keep only the k=0 values in the displayed equation line for readability.
    s0 = float(_dyadic_weighted_gm_share(0))
    g0 = 1.0 - s0
    eq_line = f"s_0=\\log_2\\varphi\\approx {_fmt_float(s0, 6)},\\quad 1-s_0\\approx {_fmt_float(g0, 6)}."

    # Single-line audit summary fragment (TeX).
    parts: List[str] = []
    parts.append(
        "Pressure family (finite): "
        + "$k\\in\\{0,1,\\dots,8\\}$, "
        + "$w_k:=2^{-k}$, "
        + "$\\lambda_k:=\\frac{1+\\sqrt{1+4w_k}}{2}$, "
        + "$s_k:=\\log_2\\lambda_k$, "
        + "$\\Omega_{\\Lambda,0}\\in\\{s_k,1-s_k\\}$;"
    )

    if omega_ref is not None and omega_ref_sigma is not None:
        parts.append(
            "Planck-2018 targets: "
            + f"$\\Omega_{{\\Lambda,0}}^{{\\mathrm{{ref}}}}={_fmt_float(float(omega_ref), 4)}"
            + f"\\pm{_fmt_float(float(omega_ref_sigma), 4)}$,"
        )
    if t.h0 is not None and t.h0_sigma is not None:
        parts.append(
            f"$H_0^{{\\mathrm{{ref}}}}={_fmt_float(float(t.h0), 2)}\\pm{_fmt_float(float(t.h0_sigma), 2)}\\,"
            + "\\mathrm{km\\,s^{-1}\\,Mpc^{-1}}$."
        )

    parts.append(
        f"Selection: $\\widehat\\Omega_{{\\Lambda,0}}={_fmt_float(omega_hat, 6)}$ "
        + f"(\\texttt{{{_tex_escape(sel_name)}}}; mismatch-minimizer: "
        + (f"\\texttt{{{_tex_escape(best_mm.name)}}}" if best_mm is not None else "n/a")
        + ", agrees: "
        + ("yes" if mismatch_minimizer_agrees else "no")
        + "; MDL-minimizer: "
        + (f"\\texttt{{{_tex_escape(best_mm_mdl.name)}}}" if best_mm_mdl is not None else "n/a")
        + ", agrees: "
        + ("yes" if mismatch_mdl_agrees else "no")
        + "; multi-target minimizer: "
        + (f"\\texttt{{{_tex_escape(best_mm_multi.name)}}}" if best_mm_multi is not None else "n/a")
        + ", agrees: "
        + ("yes" if mismatch_minimizer_multi_agrees else "no")
        + "; multi-target MDL: "
        + (f"\\texttt{{{_tex_escape(best_mm_multi_mdl.name)}}}" if best_mm_multi_mdl is not None else "n/a")
        + ", agrees: "
        + ("yes" if mismatch_mdl_multi_agrees else "no")
        + ", stable under $\\pm1\\sigma$: "
        + ("yes" if mismatch_minimizer_stable else "no")
        + ")."
    )

    if omega_ref is not None:
        parts.append(
            f"$\\log(\\widehat\\Omega_{{\\Lambda,0}}/\\Omega_{{\\Lambda,0}}^{{\\mathrm{{ref}}}})={_fmt_sci_tex(log_mismatch, 6)}$."
        )

    parts.append(f"Matter complement: $\\widehat\\Omega_{{m,0}}:=1-\\widehat\\Omega_{{\\Lambda,0}}={_fmt_float(omega_m_hat, 6)}$.")
    if omega_m_ref is not None:
        parts.append(
            f"$\\Omega_{{m,0}}^{{\\mathrm{{ref}}}}={_fmt_float(float(omega_m_ref), 4)}$, "
            + f"$\\log(\\widehat\\Omega_{{m,0}}/\\Omega_{{m,0}}^{{\\mathrm{{ref}}}})={_fmt_sci_tex(omega_m_log_mismatch, 6)}$."
        )

    parts.append(
        f"DM split (Z128-fixed $m_b^\\ast=2p+1={m_b_star}$ with $p={Z128_P}$): "
        + f"$\\widehat\\Omega_{{b,0}}=f_\\mathrm{{stab}}(m_b^\\ast)={_fmt_float(omega_b_hat, 6)}$, "
        + f"$\\widehat\\Omega_{{\\mathrm{{DM}},0}}:=\\widehat\\Omega_{{m,0}}-\\widehat\\Omega_{{b,0}}={_fmt_float(omega_dm_hat, 6)}$, "
        + f"$(\\Omega_\\mathrm{{DM}}/\\Omega_b)^{{\\mathrm{{hat}}}}={_fmt_float(dm_over_b_hat, 6)}$."
    )
    if dm_over_b_ref > 0.0 and math.isfinite(dm_over_b_ref):
        parts.append(
            f"$(\\Omega_\\mathrm{{DM}}/\\Omega_b)^{{\\mathrm{{ref}}}}={_fmt_float(float(dm_over_b_ref), 6)}$, "
            + f"$\\log\\bigl((\\Omega_\\mathrm{{DM}}/\\Omega_b)^{{\\mathrm{{hat}}}}/(\\Omega_\\mathrm{{DM}}/\\Omega_b)^{{\\mathrm{{ref}}}}\\bigr)"
            + f"={_fmt_sci_tex(dm_over_b_log_mismatch, 6)}$."
        )
    if best_m_baryon is not None:
        parts.append(
            f"Baryon mismatch-minimizer: $m_\\ast^{{\\mathrm{{mm}}}}={best_m_baryon.m_star}$ "
            + f"(agrees with $m_b^\\ast$: {'yes' if m_baryon_mm_agrees else 'no'}); "
            + f"stable under $\\pm1\\sigma$: {'yes' if m_baryon_mm_stable else 'no'}; "
            + f"allowed $m\\in\\{{{ms_allowed_tex}\\}}$."
        )
    if math.isfinite(dm_over_b_log_mismatch_min) and math.isfinite(dm_over_b_log_mismatch_max):
        parts.append(
            f"$\\log$-mismatch range for $(\\Omega_\\mathrm{{DM}}/\\Omega_b)$: "
            + f"$[{_fmt_sci_tex(dm_over_b_log_mismatch_min, 6)}, {_fmt_sci_tex(dm_over_b_log_mismatch_max, 6)}]$."
        )

    parts.append(
        f"$\\widehat H_0={_fmt_float(h0_hat, 2)}\\pm{_fmt_float(h0_hat_sigma, 2)}\\,\\mathrm{{km\\,s^{{-1}}\\,Mpc^{{-1}}}}$ "
        + f"(\\texttt{{{_tex_escape(h0_hat_id)}}})."
    )
    parts.append(
        f"$\\widehat\\Lambda={_fmt_sci_tex(lambda_hat, 6)}\\pm{_fmt_sci_tex(sigma_lambda_hat, 6)}\\,\\mathrm{{m^{{-2}}}}$"
        + (
            f", $\\Lambda^{{\\mathrm{{ref}}}}={_fmt_sci_tex(float(lambda_ref), 6)}\\pm{_fmt_sci_tex(float(sigma_lambda_ref), 6)}\\,\\mathrm{{m^{{-2}}}}$"
            if (lambda_ref is not None and sigma_lambda_ref is not None)
            else ""
        )
        + "."
    )
    parts.append("H0-family sensitivity (holding $\\widehat\\Omega_{\\Lambda,0}$ fixed): " + h0_sensitivity_tex + ".")

    summary = " ".join(parts)

    out_dir = generated_dir()
    write_lines(out_dir / "lambda_pressure_closure_equations.tex", [eq_line])
    write_lines(out_dir / "lambda_pressure_closure_summary.tex", [summary])
    print(
        "[protocol_state] Lambda pressure closure is a finite-family audit closure: "
        "Omega_Lambda,0 in {s_k,1-s_k} with k in {0..8} and a finite H0 candidate family; "
        "no readout kernel K is used beyond explicitly declared matching-layer targets."
    )


if __name__ == "__main__":
    main()

