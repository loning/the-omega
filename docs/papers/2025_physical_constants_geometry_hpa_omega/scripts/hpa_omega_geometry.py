#!/usr/bin/env python3
"""
Unified computation script for the HPA–Omega constant-geometry paper.

This script reproduces (and can re-tune) the paper's numeric claims that are
based on finite low-complexity rigidity checks and on the Fibonacci resolution map.

No third-party dependencies. All outputs are English-only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations_with_replacement
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


PI = math.pi
PHI = (1.0 + math.sqrt(5.0)) / 2.0


DEFAULT_CONFIG: Dict[str, Any] = {
    # Reference values (data-facing targets).
    "codata_alpha_inv": 137.035999177,  # CODATA 2022 (central), as used in the paper
    "pdg_alpha_inv_mZ": 127.955,  # PDG effective alpha^{-1} near Z pole (benchmark)
    "pdg_sin2_thetaW_mZ": 0.23122,  # PDG sin^2 theta_W at mu_Z (benchmark, scheme-dependent)
    "pdg_alpha_s_mZ": 0.1180,  # PDG world average
    "pdg_alpha_s_mZ_unc": 0.0009,  # representative uncertainty used in the paper
    "pdg_jarlskog": 3.00e-5,  # PDG J central value
    "pdg_jarlskog_unc": 0.15e-5,  # PDG J uncertainty (symmetric proxy)
    "codata_mu_mp_me": 1836.15267343,  # CODATA 2022 m_p/m_e (central), as used in the paper
    "codata_alphaG_p": 5.90615e-39,  # CODATA-derived alpha_G(p) used in the paper
    # PDG/CODATA masses/scales (GeV) for resolution-map tables.
    "m_e_GeV": 5.1099895e-4,
    "m_mu_GeV": 1.0565838e-1,
    "m_tau_GeV": 1.77686,
    "m_p_GeV": 0.9382721,
    "m_W_GeV": 80.377,
    "m_Z_GeV": 91.1876,
    "m_c_GeV": 1.27,
    "m_b_GeV": 4.18,
    "m_t_GeV": 172.76,
    "lambda_msbar_5_GeV": 0.209,  # representative Lambda_MSbar^(5) value
    # Resolution-map configuration.
    "resolution_mu0_GeV": None,  # default: m_e
    # Rigidity search bounds.
    "alpha_integer_max_coeff": 12,
    "IG_integer_max_coeff": 10,
    "mu_integer_max_coeff": 12,
    "mu_integer_max_sum": 10,
    "jarlskog_a_max": 50,
    "jarlskog_n_max": 20,
    "weinberg_max_denominator": 50,
}


def _deep_update(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)  # type: ignore[index]
        else:
            dst[k] = v
    return dst


def load_config(path: Optional[str]) -> Dict[str, Any]:
    cfg: Dict[str, Any] = json.loads(json.dumps(DEFAULT_CONFIG))
    if path is None:
        return cfg
    with open(path, "r", encoding="utf-8") as f:
        user_cfg = json.load(f)
    if not isinstance(user_cfg, dict):
        raise ValueError("Config JSON must be an object.")
    return _deep_update(cfg, user_cfg)


def round_nearest_int(x: float) -> int:
    # Avoid bankers rounding; we need deterministic nearest-integer behavior.
    if x >= 0.0:
        return int(math.floor(x + 0.5))
    return -int(math.floor(-x + 0.5))


def frac_to_nearest_int(x: float) -> float:
    k = round_nearest_int(x)
    return x - float(k)


def fmt_float(x: float, digits: int = 10) -> str:
    return f"{x:.{digits}f}"


def fmt_sci(x: float, digits: int = 3) -> str:
    if x == 0.0:
        return "0"
    return f"{x:.{digits}e}"


def latex_sci(x: float, mantissa_decimals: int = 2, sign: bool = True) -> str:
    """Format a float as LaTeX scientific notation: [+/-]m\\times 10^{e}."""
    if x == 0.0:
        return "0"
    s = "-" if x < 0.0 else ("+" if sign else "")
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = ax / (10.0**exp)

    mant_r = round(mant, mantissa_decimals)
    if mant_r >= 10.0:
        mant_r /= 10.0
        exp += 1
    mant_s = f"{mant_r:.{mantissa_decimals}f}"
    return f"{s}{mant_s}\\times 10^{{{exp}}}"


def latex_sci_sig(x: float, sig: int = 8, sign: bool = False) -> str:
    """Format a float as LaTeX scientific notation with given significant digits in mantissa."""
    if x == 0.0:
        return "0"
    s = "-" if x < 0.0 else ("+" if sign else "")
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = ax / (10.0**exp)

    mant_s = f"{mant:.{sig}g}"
    try:
        mant_f = float(mant_s)
    except ValueError:
        mant_f = mant
    if mant_f >= 10.0:
        mant_f /= 10.0
        exp += 1
        mant_s = f"{mant_f:.{sig}g}"
    return f"{s}{mant_s}\\times 10^{{{exp}}}"


def latex_number_GeV(mu: float, sci_lt: float = 0.3, sci_ge: float = 100.0, sig: int = 8) -> str:
    """Format a positive GeV-scale number as LaTeX, using sci notation only when needed."""
    if mu == 0.0:
        return "0"
    if mu < sci_lt or mu >= sci_ge:
        return latex_sci_sig(mu, sig=sig, sign=False)
    return f"{mu:.10g}"


def fmt_signed_fixed(x: float, decimals: int = 3) -> str:
    """Fixed-point format with sign, but suppress +0.000 at small magnitude."""
    if abs(x) < 0.5 * (10.0 ** (-decimals)):
        return f"{0.0:.{decimals}f}"
    return f"{x:+.{decimals}f}"


def header(title: str) -> None:
    line = "=" * len(title)
    print(f"\n{title}\n{line}")


def subheader(title: str) -> None:
    print(f"\n{title}\n" + "-" * len(title))


@dataclass(frozen=True)
class SearchHit:
    value: float
    abs_error: float
    rel_error: float
    payload: Tuple[Any, ...]


def best_two_hits(hits: Iterable[SearchHit]) -> Tuple[SearchHit, Optional[SearchHit]]:
    best: Optional[SearchHit] = None
    second: Optional[SearchHit] = None
    for h in hits:
        if best is None or h.abs_error < best.abs_error:
            second = best
            best = h
        elif second is None or h.abs_error < second.abs_error:
            second = h
    if best is None:
        raise ValueError("No candidates.")
    return best, second


def top_k_hits(hits: Iterable[SearchHit], k: int) -> List[SearchHit]:
    return sorted(hits, key=lambda h: (h.abs_error, h.payload))[:k]


def alpha_three_channel() -> Tuple[float, float, float, float]:
    # Canonical volumes (unit-radius).
    vol_u1 = 2.0 * PI
    vol_su2 = 2.0 * PI * PI
    vol_so3 = PI * PI
    vol_rp1 = PI

    v_bulk = vol_u1 * vol_su2  # U(1) x SU(2)
    v_boundary = vol_so3
    v_line = vol_rp1
    alpha_inv = v_bulk + v_boundary + v_line
    return alpha_inv, v_bulk, v_boundary, v_line


def search_alpha_integer_rigidity(target: float, max_coeff: int) -> Tuple[SearchHit, Optional[SearchHit]]:
    def candidates() -> Iterable[SearchHit]:
        for a in range(0, max_coeff + 1):
            for b in range(0, max_coeff + 1):
                for c in range(0, max_coeff + 1):
                    if a == 0 and b == 0 and c == 0:
                        continue
                    val = a * (PI**3) + b * (PI**2) + c * PI
                    err = val - target
                    yield SearchHit(value=val, abs_error=abs(err), rel_error=err / target, payload=(a, b, c))

    return best_two_hits(candidates())


def resolution_r(mu: float, mu0: float) -> float:
    return math.log(mu / mu0) / math.log(PHI)


def resolution_mu0_infer(mu: float, r_star: int) -> float:
    return mu / (PHI**r_star)


def resolution_significance_uniform_null(deltas: Sequence[float]) -> float:
    # deltas are x - round(x) in [-1/2, 1/2], assume i.i.d. uniform under null.
    delta0 = max(abs(d) for d in deltas)
    n = len(deltas)
    return (2.0 * delta0) ** n


def qcd_lambda_msbar_two_loop(mu: float, alpha_s: float, nf: int) -> float:
    # Lambda_MSbar = mu * exp(-2π/(b0 α_s)) * (b0 α_s/(4π))^(-b1/(2 b0^2))
    b0 = 11.0 - (2.0 / 3.0) * nf
    b1 = 102.0 - (38.0 / 3.0) * nf
    pref = mu * math.exp(-(2.0 * PI) / (b0 * alpha_s))
    pow_term = (b0 * alpha_s / (4.0 * PI)) ** (-(b1 / (2.0 * b0 * b0)))
    return pref * pow_term


def electroweak_predictions() -> Tuple[float, float]:
    alpha_inv = 13.0 * PI * PI
    sin2 = 3.0 / 13.0
    return alpha_inv, sin2


def search_best_rational(x: float, q_max: int, reduced_only: bool = True) -> Tuple[Fraction, float]:
    best: Optional[Fraction] = None
    best_err: Optional[float] = None
    for q in range(1, q_max + 1):
        for p in range(0, q + 1):
            if reduced_only and math.gcd(p, q) != 1:
                continue
            f = Fraction(p, q)
            err = abs(float(f) - x)
            if best is None or err < best_err:  # type: ignore[operator]
                best = f
                best_err = err
            elif err == best_err and best is not None:
                # Tie-break: smaller denominator, then smaller numerator.
                if f.denominator < best.denominator or (
                    f.denominator == best.denominator and f.numerator < best.numerator
                ):
                    best = f
                    best_err = err
    if best is None or best_err is None:
        raise ValueError("No rationals searched.")
    return best, best_err


def mu_geo() -> float:
    return 6.0 * (PI**5)


def search_mu_integer_rigidity(target: float, max_coeff: int, max_sum: int) -> Tuple[SearchHit, Optional[SearchHit]]:
    # mu(a,b,c,d,e)=a*pi^5+b*pi^4+c*pi^3+d*pi^2+e*pi with 0<=coeff<=max_coeff and sum<=max_sum.
    pi_pows = [PI**5, PI**4, PI**3, PI**2, PI]

    def candidates() -> Iterable[SearchHit]:
        for a in range(0, max_coeff + 1):
            for b in range(0, max_coeff + 1):
                s2 = a + b
                if s2 > max_sum:
                    continue
                for c in range(0, max_coeff + 1):
                    s3 = s2 + c
                    if s3 > max_sum:
                        continue
                    for d in range(0, max_coeff + 1):
                        s4 = s3 + d
                        if s4 > max_sum:
                            continue
                        for e in range(0, max_coeff + 1):
                            s5 = s4 + e
                            if s5 > max_sum:
                                continue
                            if a == 0 and b == 0 and c == 0 and d == 0 and e == 0:
                                continue
                            val = a * pi_pows[0] + b * pi_pows[1] + c * pi_pows[2] + d * pi_pows[3] + e * pi_pows[4]
                            err = val - target
                            yield SearchHit(
                                value=val,
                                abs_error=abs(err),
                                rel_error=err / target,
                                payload=(a, b, c, d, e),
                            )

    return best_two_hits(candidates())


def phase_space_volumes() -> Dict[str, float]:
    return {
        "U(1)": 2.0 * PI,
        "SU(2)": 2.0 * PI * PI,
        "SO(3)": PI * PI,
        "RP^1": PI,
    }


def enumerate_mu_phase_factorizations(mu_exp: float) -> List[Tuple[Tuple[str, str, str], float, float, float]]:
    vols = phase_space_volumes()
    keys = sorted(vols.keys())
    results: List[Tuple[Tuple[str, str, str], float, float, float]] = []
    for combo in combinations_with_replacement(keys, 3):
        v = vols[combo[0]] * vols[combo[1]] * vols[combo[2]]
        mu_val = 3.0 * v
        err = mu_val - mu_exp
        results.append((combo, mu_val, err, err / mu_exp))
    results.sort(key=lambda t: abs(t[2]))
    return results


def jarlskog_search(j_target: float, a_max: int, n_max: int) -> Tuple[SearchHit, Optional[SearchHit]]:
    def candidates() -> Iterable[SearchHit]:
        for a in range(1, a_max + 1):
            for n in range(1, n_max + 1):
                val = 1.0 / (a * (PI**n))
                err = val - j_target
                yield SearchHit(value=val, abs_error=abs(err), rel_error=err / j_target, payload=(a, n))

    return best_two_hits(candidates())


def alphaG_from_codate(alphaG: float) -> float:
    return math.log(1.0 / alphaG)


def IG_geo() -> float:
    return 2.0 * (PI**3) + 2.0 * (PI**2) + 2.0 * PI


def IG_integer_search(target: float, max_coeff: int) -> Tuple[SearchHit, Optional[SearchHit]]:
    def candidates() -> Iterable[SearchHit]:
        for a in range(0, max_coeff + 1):
            for b in range(0, max_coeff + 1):
                for c in range(0, max_coeff + 1):
                    if a == 0 and b == 0 and c == 0:
                        continue
                    val = a * (PI**3) + b * (PI**2) + c * PI
                    err = val - target
                    yield SearchHit(value=val, abs_error=abs(err), rel_error=err / target, payload=(a, b, c))

    return best_two_hits(candidates())


def run_alpha(cfg: Dict[str, Any]) -> None:
    header("Alpha_em: three-channel value and integer rigidity")
    alpha_inv_geo, v_bulk, v_boundary, v_line = alpha_three_channel()
    alpha_inv_codata = float(cfg["codata_alpha_inv"])

    print(f"pi = {fmt_float(PI, 15)}")
    print(f"phi = {fmt_float(PHI, 15)}")
    print(f"alpha_geo^{-1} = 4*pi^3 + pi^2 + pi = {fmt_float(alpha_inv_geo, 10)}")
    print(f"  bulk     = 4*pi^3 = {fmt_float(v_bulk, 10)}")
    print(f"  boundary = pi^2   = {fmt_float(v_boundary, 10)}")
    print(f"  line     = pi     = {fmt_float(v_line, 10)}")
    print(f"alpha_CODATA^{-1} (config) = {fmt_float(alpha_inv_codata, 9)}")
    delta = alpha_inv_geo - alpha_inv_codata
    print(f"Delta = alpha_geo^{-1} - alpha_CODATA^{-1} = {fmt_sci(delta, 3)} (rel {fmt_sci(delta/alpha_inv_codata, 3)})")

    max_coeff = int(cfg["alpha_integer_max_coeff"])
    best, second = search_alpha_integer_rigidity(alpha_inv_codata, max_coeff=max_coeff)
    a, b, c = best.payload
    print(f"Best (a,b,c) in a*pi^3 + b*pi^2 + c*pi with 0..{max_coeff}: ({a},{b},{c})")
    print(f"  value = {fmt_float(best.value, 10)}")
    print(f"  rel_error = {fmt_sci(best.rel_error, 3)}")
    if second is not None:
        a2, b2, c2 = second.payload
        print(f"Second best: ({a2},{b2},{c2}) rel_error = {fmt_sci(second.rel_error, 3)}")

    subheader("Aggregation-rule isolation (diagnostic)")
    l2 = math.sqrt(v_bulk * v_bulk + v_boundary * v_boundary + v_line * v_line)
    linf = max(v_bulk, v_boundary, v_line)
    par = 1.0 / (1.0 / v_bulk + 1.0 / v_boundary + 1.0 / v_line)
    print(f"l1 (serial sum) = {fmt_float(alpha_inv_geo, 10)}  (rel {fmt_sci((alpha_inv_geo - alpha_inv_codata) / alpha_inv_codata, 3)})")
    print(f"l2 (euclidean)  = {fmt_float(l2, 10)}  (rel {fmt_sci((l2 - alpha_inv_codata) / alpha_inv_codata, 3)})")
    print(f"linf (max)      = {fmt_float(linf, 10)}  (rel {fmt_sci((linf - alpha_inv_codata) / alpha_inv_codata, 3)})")
    print(f"parallel        = {fmt_float(par, 10)}  (rel {fmt_sci((par - alpha_inv_codata) / alpha_inv_codata, 3)})")


def run_resolution(cfg: Dict[str, Any]) -> None:
    header("Resolution map: calibration, inverse check, and null significance")
    me = float(cfg["m_e_GeV"])
    mu0 = cfg["resolution_mu0_GeV"]
    mu0 = float(me if mu0 is None else mu0)
    print(f"mu0 = {fmt_sci(mu0, 7)} GeV")
    print(f"phi = {fmt_float(PHI, 15)}")

    scales = [
        ("m_e", me),
        ("m_mu", float(cfg["m_mu_GeV"])),
        ("m_tau", float(cfg["m_tau_GeV"])),
        ("m_p", float(cfg["m_p_GeV"])),
        ("m_W", float(cfg["m_W_GeV"])),
        ("m_Z", float(cfg["m_Z_GeV"])),
    ]

    subheader("Table: r(mu) and deviation to nearest integer")
    rows: List[Tuple[str, float, float, float]] = []
    for name, mu in scales:
        r = resolution_r(mu, mu0)
        d = frac_to_nearest_int(r)
        rows.append((name, mu, r, d))
    for name, mu, r, d in rows:
        print(f"{name:5s}  mu={mu: .10g}  r={r: .6f}  r-round(r)={d:+.6f}")

    subheader("Inverse check: infer mu0 from near-integer depth")
    inverse_scales = [("m_mu", float(cfg["m_mu_GeV"])), ("m_tau", float(cfg["m_tau_GeV"])), ("m_W", float(cfg["m_W_GeV"])), ("m_Z", float(cfg["m_Z_GeV"]))]
    inferred: List[Tuple[str, int, float, float, float]] = []
    for name, mu in inverse_scales:
        r = resolution_r(mu, mu0)
        r_star = round_nearest_int(r)
        mu0_i = resolution_mu0_infer(mu, r_star)
        ratio = mu0_i / me
        inferred.append((name, r_star, mu0_i, ratio, ratio - 1.0))
    for name, r_star, mu0_i, ratio, dr in inferred:
        print(f"{name:5s}  r*={r_star:2d}  mu0(mu)={mu0_i:.7e}  mu0/m_e={ratio:.6f}  (mu0/m_e-1)={dr:+.3e}")

    subheader("Near-integer depth probability under a uniform null (illustrative)")
    deltas = [frac_to_nearest_int(resolution_r(mu, mu0)) for _, mu in inverse_scales]
    delta0 = max(abs(d) for d in deltas)
    p = resolution_significance_uniform_null(deltas)
    print(f"N={len(deltas)}  delta0=max|r-round(r)|={delta0:.3f}  P(max<=delta0)=(2*delta0)^N={p:.3e}")

    subheader("Extended table (scheme-dependent matching inputs)")
    extra = [
        ("Lambda_MSbar_5", float(cfg["lambda_msbar_5_GeV"])),
        ("m_c", float(cfg["m_c_GeV"])),
        ("m_b", float(cfg["m_b_GeV"])),
        ("m_t", float(cfg["m_t_GeV"])),
    ]
    for name, mu in extra:
        r = resolution_r(mu, mu0)
        d = frac_to_nearest_int(r)
        print(f"{name:12s}  mu={mu: .10g}  r={r: .6f}  r-round(r)={d:+.6f}")


def run_running_couplings(cfg: Dict[str, Any]) -> None:
    header("Running couplings: QED benchmark slope and QCD Lambda_MSbar")
    alpha_inv_0 = float(cfg["codata_alpha_inv"])
    alpha_inv_mZ = float(cfg["pdg_alpha_inv_mZ"])
    mZ = float(cfg["m_Z_GeV"])
    me = float(cfg["m_e_GeV"])
    delta_alpha = alpha_inv_0 - alpha_inv_mZ
    log_ratio = math.log(mZ / me)
    b_eff = (2.0 * PI * delta_alpha) / log_ratio
    # One-loop QED coefficient b = (2/3) * sum_f N_c Q_f^2.
    # At mu = mZ, the active charged fermions are e,mu,tau,u,d,s,c,b (top is above threshold).
    b_sm = 40.0 / 9.0

    print(f"log(mZ/me) = {fmt_float(log_ratio, 12)}")
    print(f"Delta alpha^{-1} = alpha^{-1}(0) - alpha^{-1}(mZ) = {fmt_float(delta_alpha, 6)}")
    print(f"b_eff = 2*pi*Delta/log(mZ/me) = {fmt_float(b_eff, 6)}")
    print(f"b_SM(mZ) = 40/9 = {fmt_float(b_sm, 6)}")
    print(f"b_eff/b_SM = {fmt_float(b_eff/b_sm, 6)}")

    subheader("QCD Lambda_MSbar^(5) from two-loop formula (PDG benchmark)")
    alpha_s = float(cfg["pdg_alpha_s_mZ"])
    nf = 5
    lam = qcd_lambda_msbar_two_loop(mu=mZ, alpha_s=alpha_s, nf=nf)
    print(f"alpha_s(mZ) = {alpha_s:.4f}  nf={nf}")
    print(f"Lambda_MSbar^(5) = {lam:.6f} GeV")

    alpha_s_unc = float(cfg["pdg_alpha_s_mZ_unc"])
    lam_lo = qcd_lambda_msbar_two_loop(mu=mZ, alpha_s=alpha_s - alpha_s_unc, nf=nf)
    lam_hi = qcd_lambda_msbar_two_loop(mu=mZ, alpha_s=alpha_s + alpha_s_unc, nf=nf)
    print(f"alpha_s uncertainty +/- {alpha_s_unc:.4f} -> Lambda range [{lam_lo:.6f}, {lam_hi:.6f}] GeV")


def run_electroweak(cfg: Dict[str, Any]) -> None:
    header("Electroweak matching: volume quantization and rational rigidity")
    alpha_inv_geo, sin2_geo = electroweak_predictions()
    alpha_inv_pdg = float(cfg["pdg_alpha_inv_mZ"])
    sin2_pdg = float(cfg["pdg_sin2_thetaW_mZ"])

    print(f"alpha^{-1}(mu_Z) geo = 13*pi^2 = {fmt_float(alpha_inv_geo, 10)}")
    print(f"alpha^{-1}(mu_Z) PDG (config) = {fmt_float(alpha_inv_pdg, 6)}")
    d_alpha = alpha_inv_geo - alpha_inv_pdg
    print(f"Delta alpha^{-1} = {fmt_float(d_alpha, 6)}  (rel {fmt_sci(d_alpha/alpha_inv_pdg, 3)})")

    print(f"sin^2 theta_W geo = 3/13 = {fmt_float(sin2_geo, 10)}")
    print(f"sin^2 theta_W PDG (config) = {fmt_float(sin2_pdg, 6)}")
    d_sin = sin2_geo - sin2_pdg
    print(f"Delta sin^2 = {fmt_sci(d_sin, 3)}  (rel {fmt_sci(d_sin/sin2_pdg, 3)})")

    subheader("Integer n rigidity for alpha^{-1}(mu_Z) ≈ n*pi^2")
    best_n = None
    best_err = None
    for n in range(1, 51):
        val = n * PI * PI
        err = abs(val - alpha_inv_pdg)
        if best_err is None or err < best_err:
            best_err = err
            best_n = n
    assert best_n is not None and best_err is not None
    print(f"Best n in [1,50] is n={best_n} with |n*pi^2 - alpha_inv| = {fmt_float(best_err, 6)}")

    subheader("Rational rigidity for sin^2 theta_W: best reduced p/q with q <= Qmax")
    q_max = int(cfg["weinberg_max_denominator"])
    best_frac, best_abs = search_best_rational(sin2_pdg, q_max=q_max, reduced_only=True)
    rel = (float(best_frac) - sin2_pdg) / sin2_pdg
    print(f"Best reduced p/q (q<= {q_max}): {best_frac.numerator}/{best_frac.denominator} = {float(best_frac):.12f}")
    print(f"|p/q - x| = {best_abs:.12g}  (rel {fmt_sci(rel, 3)})")


def run_mu(cfg: Dict[str, Any]) -> None:
    header("Mass ratio mu = m_p/m_e: phase volumes and integer rigidity")
    mu_exp = float(cfg["codata_mu_mp_me"])
    mu_val = mu_geo()
    d = mu_val - mu_exp
    print(f"mu_geo = 6*pi^5 = {fmt_float(mu_val, 10)}")
    print(f"mu_exp (config) = {fmt_float(mu_exp, 8)}")
    print(f"Delta mu = mu_geo - mu_exp = {fmt_sci(d, 3)} (rel {fmt_sci(d/mu_exp, 3)})")

    subheader("Primitive phase-space factorization enumeration (3 factors, per-color sector)")
    ranked = enumerate_mu_phase_factorizations(mu_exp=mu_exp)
    for i, (combo, mu_candidate, err, rel) in enumerate(ranked[:10], start=1):
        name = " x ".join(combo)
        print(f"{i:2d}. {name:24s}  mu= {mu_candidate: .10f}  rel={rel:+.3e}")

    subheader("Integer rigidity: mu(a,b,c,d,e) = a*pi^5 + b*pi^4 + c*pi^3 + d*pi^2 + e*pi")
    max_coeff = int(cfg["mu_integer_max_coeff"])
    max_sum = int(cfg["mu_integer_max_sum"])
    best, second = search_mu_integer_rigidity(mu_exp, max_coeff=max_coeff, max_sum=max_sum)
    a, b, c, d_, e = best.payload
    print(f"Best (a,b,c,d,e) with coeff<= {max_coeff} and sum<= {max_sum}: ({a},{b},{c},{d_},{e})")
    print(f"  value = {fmt_float(best.value, 10)}")
    print(f"  rel_error = {fmt_sci(best.rel_error, 3)}")
    if second is not None:
        a2, b2, c2, d2, e2 = second.payload
        print(f"Second best: ({a2},{b2},{c2},{d2},{e2}) rel_error = {fmt_sci(second.rel_error, 3)}")


def run_jarlskog(cfg: Dict[str, Any]) -> None:
    header("CKM CP violation: Jarlskog rigidity in 1/(a*pi^n)")
    j = float(cfg["pdg_jarlskog"])
    j_unc = float(cfg["pdg_jarlskog_unc"])
    a_max = int(cfg["jarlskog_a_max"])
    n_max = int(cfg["jarlskog_n_max"])

    print(f"J_PDG (config) = {fmt_sci(j, 6)}  +/- {fmt_sci(j_unc, 2)}")
    best, second = jarlskog_search(j_target=j, a_max=a_max, n_max=n_max)
    a, n = best.payload
    print(f"Best (a,n) in [1..{a_max}]x[1..{n_max}] for 1/(a*pi^n): ({a},{n})")
    print(f"  J_geo = {fmt_sci(best.value, 12)}")
    print(f"  rel_error = {fmt_sci(best.rel_error, 3)}")
    if second is not None:
        a2, n2 = second.payload
        print(f"Second best: ({a2},{n2}) rel_error = {fmt_sci(second.rel_error, 3)}")

    subheader("Minimax check over the PDG interval (optional diagnostic)")
    j_min = j - j_unc
    j_max = j + j_unc
    best_worst: Optional[Tuple[float, int, int, float]] = None
    for aa in range(1, a_max + 1):
        for nn in range(1, n_max + 1):
            val = 1.0 / (aa * (PI**nn))
            worst = max(abs(val - j_min) / j_min, abs(val - j_max) / j_max)
            if best_worst is None or worst < best_worst[0]:
                best_worst = (worst, aa, nn, val)
    assert best_worst is not None
    w, aa, nn, val = best_worst
    print(f"Minimax (a,n) over [J-unc, J+unc]: ({aa},{nn}) with worst-case rel = {fmt_sci(w, 3)}")


def run_gravity(cfg: Dict[str, Any]) -> None:
    header("Gravity: proton Newton coupling and integer rigidity for I_G(p)")
    alphaG_p = float(cfg["codata_alphaG_p"])
    IG_p = alphaG_from_codate(alphaG_p)
    IG_p_geo = IG_geo()
    d_IG = IG_p_geo - IG_p

    print(f"alpha_G(p) (config) = {fmt_sci(alphaG_p, 6)}")
    print(f"I_G(p) CODATA = log(alpha_G^{-1}) = {fmt_float(IG_p, 12)}")
    print(f"I_G(p) geo = 2*pi^3 + 2*pi^2 + 2*pi = {fmt_float(IG_p_geo, 12)}")
    print(f"Delta I_G = I_G_geo - I_G_CODATA = {fmt_sci(d_IG, 3)} (rel {fmt_sci(d_IG/IG_p, 3)})")
    print(f"alpha_G_geo(p) = exp(-I_G_geo) = {fmt_sci(math.exp(-IG_p_geo), 6)}")

    subheader("Integer rigidity for I_G in a*pi^3 + b*pi^2 + c*pi")
    max_coeff = int(cfg["IG_integer_max_coeff"])
    best, second = IG_integer_search(target=IG_p, max_coeff=max_coeff)
    a, b, c = best.payload
    print(f"Best (a,b,c) in 0..{max_coeff}: ({a},{b},{c})")
    print(f"  value = {fmt_float(best.value, 12)}")
    print(f"  rel_error = {fmt_sci(best.rel_error, 3)}")
    if second is not None:
        a2, b2, c2 = second.payload
        print(f"Second best: ({a2},{b2},{c2}) rel_error = {fmt_sci(second.rel_error, 3)}")

    subheader("Aggregation-rule isolation (diagnostic)")
    v_bulk = 2.0 * (PI**3)
    v_boundary = 2.0 * (PI**2)
    v_line = 2.0 * PI
    l1 = v_bulk + v_boundary + v_line
    l2 = math.sqrt(v_bulk * v_bulk + v_boundary * v_boundary + v_line * v_line)
    linf = max(v_bulk, v_boundary, v_line)
    par = 1.0 / (1.0 / v_bulk + 1.0 / v_boundary + 1.0 / v_line)
    print(f"l1 (serial sum) = {fmt_float(l1, 12)}  (rel {fmt_sci((l1 - IG_p) / IG_p, 3)})")
    print(f"l2 (euclidean)  = {fmt_float(l2, 12)}  (rel {fmt_sci((l2 - IG_p) / IG_p, 3)})")
    print(f"linf (max)      = {fmt_float(linf, 12)}  (rel {fmt_sci((linf - IG_p) / IG_p, 3)})")
    print(f"parallel        = {fmt_float(par, 12)}  (rel {fmt_sci((par - IG_p) / IG_p, 3)})")


def run_all(cfg: Dict[str, Any]) -> None:
    run_alpha(cfg)
    run_running_couplings(cfg)
    run_electroweak(cfg)
    run_mu(cfg)
    run_jarlskog(cfg)
    run_gravity(cfg)
    run_resolution(cfg)


def emit_tex_tables(cfg: Dict[str, Any], out_dir: Optional[str]) -> None:
    base = (
        Path(out_dir).expanduser().resolve()
        if out_dir is not None
        else (Path(__file__).resolve().parents[1] / "sections" / "generated")
    )
    base.mkdir(parents=True, exist_ok=True)

    def join_rows(rows: List[str]) -> str:
        if not rows:
            return ""
        out: List[str] = []
        for i, r in enumerate(rows):
            out.append(r + (" \\\\" if i < len(rows) - 1 else ""))
        return "\n".join(out)

    # ---- Table: alpha integer search (top 3) ----
    alpha_target = float(cfg["codata_alpha_inv"])
    max_coeff = int(cfg["alpha_integer_max_coeff"])

    def alpha_hits() -> Iterable[SearchHit]:
        for a in range(0, max_coeff + 1):
            for b in range(0, max_coeff + 1):
                for c in range(0, max_coeff + 1):
                    if a == 0 and b == 0 and c == 0:
                        continue
                    val = a * (PI**3) + b * (PI**2) + c * PI
                    err = val - alpha_target
                    yield SearchHit(value=val, abs_error=abs(err), rel_error=err / alpha_target, payload=(a, b, c))

    alpha_top = top_k_hits(alpha_hits(), 3)
    alpha_rows: List[str] = []
    for h in alpha_top:
        a, b, c = h.payload
        s = int(a) + int(b) + int(c)
        val_s = fmt_float(h.value, 10)
        delta = h.value - alpha_target
        alpha_rows.append(
            f"$({a},{b},{c})$ & {s} & {val_s} & ${latex_sci(delta, 2, True)}$ & ${latex_sci(delta/alpha_target, 2, True)}$"
        )
    (base / "alpha_integer_search_rows.tex").write_text(join_rows(alpha_rows), encoding="utf-8")

    # ---- Table: mu integer search (top 3) ----
    mu_target = float(cfg["codata_mu_mp_me"])
    mu_max_coeff = int(cfg["mu_integer_max_coeff"])
    mu_max_sum = int(cfg["mu_integer_max_sum"])
    pi5, pi4, pi3, pi2, pi1 = PI**5, PI**4, PI**3, PI**2, PI

    def mu_hits() -> Iterable[SearchHit]:
        for a in range(0, mu_max_coeff + 1):
            for b in range(0, mu_max_coeff + 1):
                s2 = a + b
                if s2 > mu_max_sum:
                    continue
                for c in range(0, mu_max_coeff + 1):
                    s3 = s2 + c
                    if s3 > mu_max_sum:
                        continue
                    for d in range(0, mu_max_coeff + 1):
                        s4 = s3 + d
                        if s4 > mu_max_sum:
                            continue
                        for e in range(0, mu_max_coeff + 1):
                            s5 = s4 + e
                            if s5 > mu_max_sum:
                                continue
                            if s5 == 0:
                                continue
                            val = a * pi5 + b * pi4 + c * pi3 + d * pi2 + e * pi1
                            err = val - mu_target
                            yield SearchHit(value=val, abs_error=abs(err), rel_error=err / mu_target, payload=(a, b, c, d, e))

    mu_top = top_k_hits(mu_hits(), 3)
    mu_rows: List[str] = []
    for h in mu_top:
        a, b, c, d_, e = h.payload
        s = int(a) + int(b) + int(c) + int(d_) + int(e)
        val_s = f"{h.value:.10f}"
        delta = h.value - mu_target
        mu_rows.append(
            f"$({a},{b},{c},{d_},{e})$ & {s} & {val_s} & ${latex_sci(delta, 2, True)}$ & ${latex_sci(delta/mu_target, 2, True)}$"
        )
    (base / "mu_integer_search_rows.tex").write_text(join_rows(mu_rows), encoding="utf-8")

    # ---- Table: mu primitive phase-space factorizations (selected) ----
    # Canonical primitive volumes:
    #   Vol(U(1)) = 2*pi, Vol(SU(2)) = 2*pi^2, Vol(SO(3)) = pi^2, Vol(RP^1) = pi.
    # The table records 3 * product of three primitive factors per color sector.
    mu_fact_rows: List[str] = []
    mu_fact_cases = [
        ("$SO(3)\\times SO(3)\\times U(1)$", 6, 5),
        ("$SO(3)\\times SU(2)\\times \\mathbb{R}P^1$", 6, 5),
        ("$SU(2)\\times U(1)\\times U(1)$", 24, 4),
        ("$SU(2)\\times U(1)\\times \\mathbb{R}P^1$", 12, 4),
    ]
    for name, coeff, k in mu_fact_cases:
        val = float(coeff) * (PI**int(k))
        delta = val - mu_target
        expr = f"{coeff}\\pi^{k}={val:.10f}"
        mu_fact_rows.append(
            f"{name} & ${expr}$ & ${latex_sci(delta, 2, True)}$ & ${latex_sci(delta/mu_target, 2, True)}$"
        )
    (base / "mu_phase_factorizations_rows.tex").write_text(join_rows(mu_fact_rows), encoding="utf-8")

    # ---- Table: Jarlskog integer search (top 3) ----
    j_target = float(cfg["pdg_jarlskog"])
    a_max = int(cfg["jarlskog_a_max"])
    n_max = int(cfg["jarlskog_n_max"])

    def j_hits() -> Iterable[SearchHit]:
        for a in range(1, a_max + 1):
            for n in range(1, n_max + 1):
                val = 1.0 / (a * (PI**n))
                err = val - j_target
                yield SearchHit(value=val, abs_error=abs(err), rel_error=err / j_target, payload=(a, n))

    j_top = top_k_hits(j_hits(), 3)
    j_rows: List[str] = []
    for h in j_top:
        a, n = h.payload
        delta = h.value - j_target
        j_val = latex_sci(h.value, mantissa_decimals=9, sign=False)
        j_rows.append(
            f"{a} & {n} & ${j_val}$ & ${latex_sci(delta, 2, True)}$ & ${latex_sci(delta/j_target, 2, True)}$"
        )
    (base / "jarlskog_integer_search_rows.tex").write_text(join_rows(j_rows), encoding="utf-8")

    # ---- Table: I_G integer search (top 3) ----
    alphaG_p = float(cfg["codata_alphaG_p"])
    IG_target = alphaG_from_codate(alphaG_p)
    IG_max_coeff = int(cfg["IG_integer_max_coeff"])

    def IG_hits() -> Iterable[SearchHit]:
        for a in range(0, IG_max_coeff + 1):
            for b in range(0, IG_max_coeff + 1):
                for c in range(0, IG_max_coeff + 1):
                    if a == 0 and b == 0 and c == 0:
                        continue
                    val = a * (PI**3) + b * (PI**2) + c * PI
                    err = val - IG_target
                    yield SearchHit(value=val, abs_error=abs(err), rel_error=err / IG_target, payload=(a, b, c))

    IG_top = top_k_hits(IG_hits(), 3)
    IG_rows: List[str] = []
    for h in IG_top:
        a, b, c = h.payload
        s = int(a) + int(b) + int(c)
        val_s = fmt_float(h.value, 9)
        delta = h.value - IG_target
        IG_rows.append(
            f"$({a},{b},{c})$ & {s} & {val_s} & ${latex_sci(delta, 2, True)}$ & ${latex_sci(delta/IG_target, 2, True)}$"
        )
    (base / "alpha_G_integer_search_rows.tex").write_text(join_rows(IG_rows), encoding="utf-8")

    # ---- Tables: resolution-map calibration rows ----
    me = float(cfg["m_e_GeV"])
    mu0_cfg = cfg["resolution_mu0_GeV"]
    mu0 = float(me if mu0_cfg is None else mu0_cfg)

    calib_scales = [
        ("$m_e$", float(cfg["m_e_GeV"])),
        ("$m_\\mu$", float(cfg["m_mu_GeV"])),
        ("$m_\\tau$", float(cfg["m_tau_GeV"])),
        ("$m_p$", float(cfg["m_p_GeV"])),
        ("$m_W$", float(cfg["m_W_GeV"])),
        ("$m_Z$", float(cfg["m_Z_GeV"])),
    ]
    calib_rows: List[str] = []
    for name, mu in calib_scales:
        r = resolution_r(mu, mu0)
        d = frac_to_nearest_int(r)
        mu_s = latex_number_GeV(mu, sci_lt=0.3, sci_ge=100.0, sig=8)
        calib_rows.append(f"{name} & ${mu_s}$ & ${r:.3f}$ & ${fmt_signed_fixed(d, 3)}$")
    (base / "resolution_map_calibration_rows.tex").write_text(join_rows(calib_rows), encoding="utf-8")

    inv_scales = [
        ("$m_\\mu$", float(cfg["m_mu_GeV"])),
        ("$m_\\tau$", float(cfg["m_tau_GeV"])),
        ("$m_W$", float(cfg["m_W_GeV"])),
        ("$m_Z$", float(cfg["m_Z_GeV"])),
    ]
    mu0_rows: List[str] = []
    for name, mu in inv_scales:
        r = resolution_r(mu, mu0)
        r_star = round_nearest_int(r)
        mu0_i = resolution_mu0_infer(mu, r_star)
        ratio = mu0_i / me
        mu0_s = latex_sci_sig(mu0_i, sig=5, sign=False)
        mu0_rows.append(f"{name} & {r_star} & ${mu0_s}$ & ${ratio:.4f}$ & ${latex_sci(ratio-1.0, 2, True)}$")
    (base / "resolution_map_mu0_cluster_rows.tex").write_text(join_rows(mu0_rows), encoding="utf-8")

    extra_scales = [
        ("$\\Lambda_{\\overline{\\mathrm{MS}}}^{(5)}$", float(cfg["lambda_msbar_5_GeV"])),
        ("$m_c$", float(cfg["m_c_GeV"])),
        ("$m_b$", float(cfg["m_b_GeV"])),
        ("$m_t$", float(cfg["m_t_GeV"])),
    ]
    extra_rows: List[str] = []
    for name, mu in extra_scales:
        r = resolution_r(mu, mu0)
        d = frac_to_nearest_int(r)
        mu_s = latex_number_GeV(mu, sci_lt=0.3, sci_ge=100.0, sig=5)
        extra_rows.append(f"{name} & ${mu_s}$ & ${r:.3f}$ & ${fmt_signed_fixed(d, 3)}$")
    (base / "resolution_map_calibration_extended_rows.tex").write_text(join_rows(extra_rows), encoding="utf-8")



def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hpa_omega_geometry.py",
        description="Unified computations and rigidity searches for the HPA–Omega constant-geometry paper.",
    )
    p.add_argument("--config", default=None, help="Path to a JSON config overriding defaults.")
    p.add_argument("--dump-default-config", action="store_true", help="Print default config as JSON and exit.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("all", help="Run all computations.")
    sub.add_parser("alpha", help="Alpha_em three-channel value and rigidity.")
    sub.add_parser("running", help="Running-coupling benchmarks (QED/QCD).")
    sub.add_parser("ew", help="Electroweak matching and rational rigidity.")
    sub.add_parser("mu", help="Proton-electron mass ratio computations.")
    sub.add_parser("j", help="Jarlskog invariant rigidity.")
    sub.add_parser("gravity", help="Proton Newton coupling computations.")
    sub.add_parser("resolution", help="Resolution-map calibration and significance.")
    p_emit = sub.add_parser("emit-tex", help="Emit LaTeX table-row fragments used by the paper.")
    p_emit.add_argument(
        "--out-dir",
        default=None,
        help="Output directory for LaTeX fragments (default: sections/generated in the paper root).",
    )
    return p


def main(argv: Sequence[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.dump_default_config:
        print(json.dumps(DEFAULT_CONFIG, indent=2, sort_keys=True))
        return 0

    cfg = load_config(args.config)

    cmd = args.cmd
    if cmd == "all":
        run_all(cfg)
    elif cmd == "alpha":
        run_alpha(cfg)
    elif cmd == "running":
        run_running_couplings(cfg)
    elif cmd == "ew":
        run_electroweak(cfg)
    elif cmd == "mu":
        run_mu(cfg)
    elif cmd == "j":
        run_jarlskog(cfg)
    elif cmd == "gravity":
        run_gravity(cfg)
    elif cmd == "resolution":
        run_resolution(cfg)
    elif cmd == "emit-tex":
        emit_tex_tables(cfg, out_dir=getattr(args, "out_dir", None))
    else:
        raise ValueError(f"Unknown command: {cmd}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

