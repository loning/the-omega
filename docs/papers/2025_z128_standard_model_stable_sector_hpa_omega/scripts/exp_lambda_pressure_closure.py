# -*- coding: utf-8 -*-
"""
Lambda pressure closure (audit generator).

This script implements Appendix 58's finite-family pressure-based closure for the
vacuum normalization:

  Omega_{Lambda,0} ∈ { log_2(phi), 1 - log_2(phi) }

Selection is performed by a deterministic absolute log-mismatch minimizer against a
declared matching-layer target Omega_{Lambda,0}^{ref} (Planck-2018).

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

from common_paths import generated_dir, paper_root
from common_tex import write_lines


PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
LOG2_PHI: float = math.log(PHI) / math.log(2.0)

# Exact SI speed of light.
C_M_S: float = 299_792_458.0

# 1 Mpc in meters (exact via IAU parsec definition; fixed literal for determinism).
MPC_M: float = 3.085_677_581_491_367_3e22

# Bounded sensitivity diagnostics (matching-layer only).
# SH0ES (Riess et al. 2019): H0 = 74.03 ± 1.42 km/s/Mpc.
SH0ES19_H0_KM_S_MPC: float = 74.03
SH0ES19_H0_SIGMA_KM_S_MPC: float = 1.42


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
    h0: float
    h0_sigma: float
    omega_lambda0: float
    omega_lambda0_sigma: float
    omega_m0: Optional[float]
    omega_m0_sigma: Optional[float]


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

    h0_pair = _maybe_read_value_sigma(targets, "H0")
    if h0_pair is None:
        raise KeyError("Missing targets.H0.")
    omega_pair = _maybe_read_value_sigma(targets, "OmegaLambda0")
    if omega_pair is None:
        raise KeyError("Missing targets.OmegaLambda0.")
    h0, h0_sigma = h0_pair
    omega, omega_sigma = omega_pair

    if h0 <= 0.0:
        raise ValueError("H0 must be positive.")
    if h0_sigma < 0.0:
        raise ValueError("H0 sigma must be >= 0.")
    if not (0.0 < omega < 1.0):
        raise ValueError("OmegaLambda0 must be in (0,1).")
    if omega_sigma < 0.0:
        raise ValueError("OmegaLambda0 sigma must be >= 0.")

    omega_m_pair = _maybe_read_value_sigma(targets, "OmegaM0")
    omega_m0: Optional[float] = None
    omega_m0_sigma: Optional[float] = None
    if omega_m_pair is not None:
        omega_m0, omega_m0_sigma = omega_m_pair
        if not (0.0 < float(omega_m0) < 1.0):
            raise ValueError("OmegaM0 must be in (0,1).")

    return Targets(
        h0=h0,
        h0_sigma=h0_sigma,
        omega_lambda0=omega,
        omega_lambda0_sigma=omega_sigma,
        omega_m0=omega_m0,
        omega_m0_sigma=omega_m0_sigma,
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
    # Finite candidate family (explicit): dyadic-weighted pressure shares and their complements.
    # Keep this list short and auditable.
    ks = [0, 1, 2]
    cands = _iter_candidates(omega_ref, ks)
    best = min(cands, key=lambda c: c.key())
    return best


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

    # Baseline selection under the declared Planck-2018 Omega_{Lambda,0} target.
    best = _select_candidate(t.omega_lambda0)
    omega_hat = float(best.omega)
    log_mismatch = float(best.log_mismatch)

    # Baseline Lambda values (Planck-2018 H0).
    lambda_hat = _lambda_from_h0_omega(t.h0, omega_hat)
    lambda_ref = _lambda_from_h0_omega(t.h0, t.omega_lambda0)

    # Uncertainty propagation (matching-layer): treat the candidate value as exact,
    # and propagate H0 and (for Lambda_ref) Omega_ref.
    sigma_lambda_hat = _sigma_lambda_from_h0_omega(
        lambda_val=lambda_hat,
        h0=t.h0,
        h0_sigma=t.h0_sigma,
        omega=omega_hat,
        omega_sigma=0.0,
    )
    sigma_lambda_ref = _sigma_lambda_from_h0_omega(
        lambda_val=lambda_ref,
        h0=t.h0,
        h0_sigma=t.h0_sigma,
        omega=t.omega_lambda0,
        omega_sigma=t.omega_lambda0_sigma,
    )

    # Selection stability check under ±1σ on Omega_ref.
    omega_lo = max(1e-12, float(t.omega_lambda0) - float(t.omega_lambda0_sigma))
    omega_hi = min(1.0 - 1e-12, float(t.omega_lambda0) + float(t.omega_lambda0_sigma))
    best_lo = _select_candidate(omega_lo)
    best_hi = _select_candidate(omega_hi)
    selection_stable = (best_lo.name == best.name) and (best_hi.name == best.name)

    # Complementary matter fraction implied by the chosen Omega_{Lambda,0}.
    omega_m_hat = 1.0 - omega_hat
    omega_m_ref = float(t.omega_m0) if t.omega_m0 is not None else 1.0 - float(t.omega_lambda0)
    omega_m_log_mismatch = math.log(omega_m_hat / omega_m_ref) if (omega_m_hat > 0.0 and omega_m_ref > 0.0) else float("nan")

    # Late-time H0 sensitivity diagnostics (does not affect Omega selection).
    h0licow = _read_h0licow_h0()
    lambda_hat_h0licow: Optional[float] = None
    sigma_lambda_hat_h0licow: Optional[float] = None
    if h0licow is not None:
        h0_td, h0_td_sigma = h0licow
        lambda_hat_h0licow = _lambda_from_h0_omega(h0_td, omega_hat)
        sigma_lambda_hat_h0licow = _sigma_lambda_from_h0_omega(
            lambda_val=lambda_hat_h0licow,
            h0=h0_td,
            h0_sigma=h0_td_sigma,
            omega=omega_hat,
            omega_sigma=0.0,
        )

    lambda_hat_sh0es = _lambda_from_h0_omega(SH0ES19_H0_KM_S_MPC, omega_hat)
    sigma_lambda_hat_sh0es = _sigma_lambda_from_h0_omega(
        lambda_val=lambda_hat_sh0es,
        h0=SH0ES19_H0_KM_S_MPC,
        h0_sigma=SH0ES19_H0_SIGMA_KM_S_MPC,
        omega=omega_hat,
        omega_sigma=0.0,
    )

    # Very small numbers: report in m^{-2}.
    # For convenience we also report the implied rho_Lambda in SI units:
    #   rho_Lambda = (Lambda c^2) / (8πG)
    # but we do not compute it here to avoid introducing a specific G literal.

    # Candidate snapshot (explicit, finite).
    # Keep only the k=0 values in the displayed equation line for readability.
    s0 = float(_dyadic_weighted_gm_share(0))
    g0 = 1.0 - s0
    eq_line = (
        f"s_0=\\log_2\\varphi\\approx {_fmt_float(s0, 6)},\\quad "
        f"1-s_0\\approx {_fmt_float(g0, 6)}."
    )

    summary = (
        "Pressure family (finite): "
        + "$k\\in\\{0,1,2\\}$, "
        + "$w_k:=2^{-k}$, "
        + "$\\lambda_k:=\\frac{1+\\sqrt{1+4w_k}}{2}$, "
        + "$s_k:=\\log_2\\lambda_k$, "
        + "$\\Omega_{\\Lambda,0}\\in\\{s_k,1-s_k\\}$; "
        + "Planck-2018 targets: "
        + f"$\\Omega_{{\\Lambda,0}}^{{\\mathrm{{ref}}}}={_fmt_float(t.omega_lambda0, 4)}"
        + f"\\pm{_fmt_float(t.omega_lambda0_sigma, 4)}$, "
        + f"$H_0^{{\\mathrm{{ref}}}}={_fmt_float(t.h0, 2)}\\pm{_fmt_float(t.h0_sigma, 2)}\\,"
        + "\\mathrm{km\\,s^{-1}\\,Mpc^{-1}}$. "
        + f"Selection: $\\widehat\\Omega_{{\\Lambda,0}}={_fmt_float(omega_hat, 6)}$ "
        + f"(\\texttt{{{best.name}}}; stability under $\\pm1\\sigma$ on $\\Omega_{{\\Lambda,0}}^{{\\mathrm{{ref}}}}$: "
        + ("yes" if selection_stable else "no")
        + "). "
        + f"$\\log(\\widehat\\Omega_{{\\Lambda,0}}/\\Omega_{{\\Lambda,0}}^{{\\mathrm{{ref}}}})"
        + f"={_fmt_sci_tex(log_mismatch, 6)}$. "
        + f"Matter complement: $\\widehat\\Omega_{{m,0}}:=1-\\widehat\\Omega_{{\\Lambda,0}}={_fmt_float(omega_m_hat, 6)}$, "
        + f"$\\Omega_{{m,0}}^{{\\mathrm{{ref}}}}={_fmt_float(omega_m_ref, 4)}$, "
        + f"$\\log(\\widehat\\Omega_{{m,0}}/\\Omega_{{m,0}}^{{\\mathrm{{ref}}}})={_fmt_sci_tex(omega_m_log_mismatch, 6)}$. "
        + f"$\\widehat\\Lambda={_fmt_sci_tex(lambda_hat, 6)}\\pm{_fmt_sci_tex(sigma_lambda_hat, 6)}\\,\\mathrm{{m^{{-2}}}}$, "
        + f"$\\Lambda^{{\\mathrm{{ref}}}}={_fmt_sci_tex(lambda_ref, 6)}\\pm{_fmt_sci_tex(sigma_lambda_ref, 6)}\\,\\mathrm{{m^{{-2}}}}$. "
        + "H0 sensitivity (holding $\\widehat\\Omega_{\\Lambda,0}$ fixed): "
        + (
            f"$H_0^{{\\mathrm{{TD}}}}$ gives $\\widehat\\Lambda={_fmt_sci_tex(float(lambda_hat_h0licow), 6)}"
            f"\\pm{_fmt_sci_tex(float(sigma_lambda_hat_h0licow), 6)}\\,\\mathrm{{m^{{-2}}}}$; "
            if (lambda_hat_h0licow is not None and sigma_lambda_hat_h0licow is not None)
            else "(TD unavailable); "
        )
        + f"SH0ES19 gives $\\widehat\\Lambda={_fmt_sci_tex(lambda_hat_sh0es, 6)}"
        + f"\\pm{_fmt_sci_tex(sigma_lambda_hat_sh0es, 6)}\\,\\mathrm{{m^{{-2}}}}$."
    )

    out_dir = generated_dir()
    write_lines(out_dir / "lambda_pressure_closure_equations.tex", [eq_line])
    write_lines(out_dir / "lambda_pressure_closure_summary.tex", [summary])


if __name__ == "__main__":
    main()

