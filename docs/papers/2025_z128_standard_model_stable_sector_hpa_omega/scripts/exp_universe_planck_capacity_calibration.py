# -*- coding: utf-8 -*-
"""
Universe horizon capacity calibration (audit generator).

Goal:
  Provide an auditable mapping from a "cosmological maximum information" target
  (treated as a boundary area-law capacity in bits) to protocol resolution (m,n)
  using the same finite-family CAP discipline as Appendix 09.

We include two standard horizon conventions as a finite target family:
  (U1) Hubble radius horizon: R_H = c / H0
  (U2) de Sitter (Lambda) horizon in flat LCDM proxy: R_dS = c / (H0 * sqrt(Omega_Lambda))

Capacity target in bits:
  I_univ(A) = A / (4 * l_P^2 * ln 2)

Protocol screen capacity in bits (paper convention):
  I_prot(m,n) = m * 4^n

Outputs (LaTeX fragments):
  - sections/generated/universe_planck_capacity_rows.tex
  - sections/generated/universe_planck_capacity_summary.tex

Design goals (repo conventions):
  - Deterministic output (no timestamps).
  - English-only script output.
  - Standard-library only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from common_paths import generated_dir
from common_tex import write_lines

# --- Physical constants (SI) ---
# Exact by SI definition:
C_M_S: float = 299_792_458.0
H_J_S: float = 6.626_070_15e-34

# CODATA value (treated as an external matching constant; explicit literal for determinism).
G_M3_KG_S2: float = 6.674_30e-11

# Unit helpers:
MPC_M: float = 3.085_677_581_491_367_3e22  # 1 Mpc in meters (exact in this script; matching constant)


def _hbar() -> float:
    return H_J_S / (2.0 * math.pi)


def _l_p_sq() -> float:
    # ℓ_P^2 = G ħ / c^3
    return G_M3_KG_S2 * _hbar() / (C_M_S**3)


def _i_bh_bits_from_area(area_m2: float) -> float:
    # I = S/(k_B ln 2) = A/(4 ℓ_P^2 ln 2)
    return float(area_m2) / (4.0 * _l_p_sq() * math.log(2.0))


def _fmt_float(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


def _fmt_sci_tex(x: float, digits: int = 6) -> str:
    """
    Stable LaTeX-friendly scientific notation: a\\times 10^{b}.
    """
    if not math.isfinite(x):
        return "nan"
    if x == 0.0:
        return "0"
    s = f"{float(x):.{max(1, int(digits))}e}"
    mant, exp = s.split("e")
    e = int(exp)
    if e == 0:
        return mant
    return f"{mant}\\times 10^{{{e}}}"


def _i_prot_log(m: int, n: int) -> float:
    # log(I_prot) = log(m) + n*log(4)
    return math.log(float(m)) + float(n) * math.log(4.0)


def _best_mn_for_target(i_target_bits: float, m_set: Sequence[int], n_set: Sequence[int]) -> Tuple[int, int, float]:
    """
    Return (m*, n*, delta) for lexicographic key (delta, n, m).
    delta is log-mismatch: |log(I_prot/I_target)|.
    """
    if i_target_bits <= 0.0 or not math.isfinite(i_target_bits):
        raise ValueError("i_target_bits must be positive and finite")
    log_i = math.log(float(i_target_bits))
    best: Tuple[float, int, int] | None = None
    for m in m_set:
        for n in n_set:
            d = abs(_i_prot_log(int(m), int(n)) - log_i)
            key = (float(d), int(n), int(m))
            if best is None or key < best:
                best = key
    assert best is not None
    d, n, m = best
    return int(m), int(n), float(d)


def _candidate_m() -> List[int]:
    # Match Appendix 09 main calibration family.
    return [6, 8, 10, 12, 14, 16]


def _candidate_n(max_n: int = 260) -> List[int]:
    # Wide enough to cover cosmological targets at ~1e122 bits (n≈201–202 for m=16).
    return list(range(0, int(max_n) + 1))


@dataclass(frozen=True)
class UnivTarget:
    name: str
    h0_km_s_mpc: float
    omega_lambda: float
    horizon: str  # "Hubble" or "dS"


def _h0_s_inv(h0_km_s_mpc: float) -> float:
    # H0 [s^-1] = (H0 [km/s/Mpc] * 1000) / Mpc_m
    return float(h0_km_s_mpc) * 1000.0 / MPC_M


def _radius_horizon_m(t: UnivTarget) -> float:
    h0 = _h0_s_inv(t.h0_km_s_mpc)
    if t.horizon == "Hubble":
        return C_M_S / h0
    if t.horizon == "dS":
        # Flat LCDM proxy: Λ = 3 Ω_Λ H0^2 / c^2 -> R_dS = sqrt(3/Λ) = c/(H0*sqrt(Ω_Λ))
        if t.omega_lambda <= 0.0:
            raise ValueError("omega_lambda must be positive for dS proxy")
        return C_M_S / (h0 * math.sqrt(float(t.omega_lambda)))
    raise ValueError("Unknown horizon type")


def _area_from_radius_m2(r_m: float) -> float:
    return 4.0 * math.pi * (float(r_m) ** 2)


def main() -> None:
    # Matching-layer reference values (explicit literals for determinism).
    # These are used only as a compact numerical example set, not as theorem-level premises.
    targets: List[UnivTarget] = [
        UnivTarget(
            name="Universe horizon (Planck18 proxy)",
            h0_km_s_mpc=67.4,
            omega_lambda=0.6847,
            horizon="Hubble",
        ),
        UnivTarget(
            name="Universe horizon (Planck18 proxy)",
            h0_km_s_mpc=67.4,
            omega_lambda=0.6847,
            horizon="dS",
        ),
    ]

    m_set = _candidate_m()
    n_set = _candidate_n(max_n=260)

    lines: List[str] = []
    for t in targets:
        r = _radius_horizon_m(t)
        a = _area_from_radius_m2(r)
        i_bits = _i_bh_bits_from_area(a)
        m_star, n_star, d = _best_mn_for_target(i_bits, m_set=m_set, n_set=n_set)

        # Report I_prot in a compact exact form and a float approximation.
        # I_prot = m * 4^n is an integer but can be huge; float approximation is safe here (~1e122).
        i_prot_log = _i_prot_log(m_star, n_star)
        i_prot_bits_approx = math.exp(i_prot_log)
        i_prot_tex = rf"${m_star}\,4^{{{n_star}}}$"

        lines.append(
            " & ".join(
                [
                    t.name,
                    t.horizon,
                    _fmt_float(t.h0_km_s_mpc, digits=3),
                    _fmt_float(t.omega_lambda, digits=4),
                    str(m_star),
                    str(n_star),
                    i_prot_tex,
                    rf"${_fmt_sci_tex(i_prot_bits_approx, digits=6)}$",
                    rf"${_fmt_sci_tex(i_bits, digits=6)}$",
                    _fmt_float(d, digits=6),
                ]
            )
            + r" \\"
        )

    out_rows = generated_dir() / "universe_planck_capacity_rows.tex"
    write_lines(out_rows, lines if lines else ["% (no rows)"])

    # Summary (AuditTag style, deterministic).
    summary = [
        r"\paragraph{Audit summary (Universe horizons).} \AuditTag "
        + r"Target family: Hubble horizon $R_H=c/H_0$ and de Sitter proxy $R_{\mathrm{dS}}=c/(H_0\sqrt{\Omega_\Lambda})$ (flat-$\Lambda$CDM proxy).",
        r"\noindent\AuditTag "
        + r"Numerical reference: $H_0=67.4\,\mathrm{km\,s^{-1}\,Mpc^{-1}}$ and $\Omega_\Lambda=0.6847$ (Planck18 proxy; matching-scope only).",
        r"\noindent\AuditTag "
        + r"Candidate family: $m\in\{6,8,10,12,14,16\}$, $n\in\{0,\dots,260\}$; CAP key $(\Delta,n,m)$ with $\Delta=|\log(I_{\mathrm{prot}}/I_{\mathrm{BH}})|$.",
    ]
    out_sum = generated_dir() / "universe_planck_capacity_summary.tex"
    write_lines(out_sum, summary)


if __name__ == "__main__":
    main()

