# -*- coding: utf-8 -*-
"""
Boundary–Planck capacity calibration (audit generator).

This script generates finite-family calibration fragments for Appendix 09:
  - boundary black-hole information capacity (area law / Planck units) vs
  - protocol screen capacity I_prot(m,n) = m * 4^n.

Outputs (LaTeX fragments):
  - sections/generated/bh_planck_capacity_rows.tex
  - sections/generated/bh_planck_capacity_summary.tex
  - sections/generated/bh_capacity_calibrated_uplift_path_rows.tex
  - sections/generated/bh_planck_capacity_known_rows.tex
  - sections/generated/bh_planck_capacity_known_summary.tex

Design goals (repo conventions):
  - Deterministic output (no timestamps).
  - English-only script output.
  - Standard-library only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from common_paths import generated_dir
from common_tex import write_lines

# --- Physical constants (SI) ---
#
# Exact by SI definition:
C_M_S: float = 299_792_458.0
H_J_S: float = 6.626_070_15e-34
K_B_J_K: float = 1.380_649e-23

# CODATA value (treated as an external matching constant; explicit literal for determinism).
# CODATA: G = 6.67430(15)×10^{-11} m^3 kg^{-1} s^{-2}.
G_M3_KG_S2: float = 6.674_30e-11
G_SIGMA: float = 1.5e-15


def _hbar() -> float:
    return H_J_S / (2.0 * math.pi)


def _l_p_sq() -> float:
    # ℓ_P^2 = G ħ / c^3
    return G_M3_KG_S2 * _hbar() / (C_M_S**3)


def _m_p() -> float:
    # m_P = sqrt(ħ c / G)
    return math.sqrt(_hbar() * C_M_S / G_M3_KG_S2)


def _i_prot_bits(m: int, n: int) -> int:
    return int(m) * (4**int(n))


def _schwarzschild_area_m2(mass_kg: float) -> float:
    rs = 2.0 * G_M3_KG_S2 * float(mass_kg) / (C_M_S**2)
    return 4.0 * math.pi * (rs**2)


def _i_bh_bits_from_area(area_m2: float) -> float:
    # I = S/(k_B ln 2) = A/(4 ℓ_P^2 ln 2)
    return float(area_m2) / (4.0 * _l_p_sq() * math.log(2.0))


def _i_bh_bits_from_mass(mass_kg: float) -> float:
    return _i_bh_bits_from_area(_schwarzschild_area_m2(mass_kg))


def _delta_log_ratio(a: float, b: float) -> float:
    if a <= 0.0 or b <= 0.0:
        return float("inf")
    return abs(math.log(float(a) / float(b)))


def _fmt_int(x: int) -> str:
    return str(int(x))


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


@dataclass(frozen=True)
class CalibRow:
    alpha: int
    m: int
    n: int
    i_prot_bits: int
    i_bh_bits: float
    delta: float


@dataclass(frozen=True)
class KnownRow:
    name: str
    m_over_msun: float
    m_over_mp: float
    m: int
    n: int
    i_bh_bits: float
    delta: float


def _candidate_m() -> List[int]:
    return [6, 8, 10, 12, 14, 16]


def _candidate_n() -> List[int]:
    return [3, 4, 5, 6]


def _mass_family_alpha() -> List[int]:
    return [1, 2, 4, 8, 16, 32, 64]


def _candidate_n_known(max_n: int = 200) -> List[int]:
    # Finite but sufficiently wide to cover reference astrophysical black-hole masses.
    return list(range(0, int(max_n) + 1))


def _known_bh_family_m_over_msun() -> List[Tuple[str, float]]:
    """
    Reference masses (in solar-mass units), used only as matching-layer examples.
    Values are nominal/rounded and intentionally treated as external inputs.
    """
    return [
        ("Solar-mass BH (1 $M_\\odot$)", 1.0),
        ("Cygnus X-1 (21.2 $M_\\odot$)", 21.2),
        ("GW150914 remnant ($\\sim 62\\,M_\\odot$)", 62.0),
        ("Sgr A* ($4.297\\times 10^6\\,M_\\odot$)", 4.297e6),
        ("M87* ($6.5\\times 10^9\\,M_\\odot$)", 6.5e9),
    ]


def _m_sun_kg() -> float:
    # Nominal solar mass (IAU 2015), treated as an external matching constant.
    return 1.988_47e30


def _best_mn_for_mass(i_bh_bits: float, m_set: Sequence[int], n_set: Sequence[int]) -> Tuple[int, int, int, float]:
    """
    Return (m, n, I_prot, delta) for the lexicographic key:
      (delta, n, m).
    """
    if i_bh_bits <= 0.0 or not math.isfinite(i_bh_bits):
        raise ValueError("i_bh_bits must be positive and finite")
    log_i_bh = math.log(float(i_bh_bits))
    best: Tuple[float, int, int, int] | None = None  # (delta, n, m, I_prot)
    for m in m_set:
        for n in n_set:
            ip = _i_prot_bits(m, n)
            # Use log-space mismatch to avoid float overflow for large n.
            d = abs((math.log(float(m)) + float(n) * math.log(4.0)) - log_i_bh)
            key = (d, int(n), int(m), int(ip))
            if best is None or key < best:
                best = key
    assert best is not None
    d, n, m, ip = best
    return (m, n, ip, float(d))


def _select_alpha_ref(i_anchor_bits: int, alpha_set: Sequence[int], mp_kg: float) -> int:
    """
    Deterministic reference-mass choice for the uplift-path table:
    pick the smallest dyadic alpha with I_BH(alpha*m_P) >= I_anchor.
    Fallback: max alpha.
    """
    for a in sorted(set(int(x) for x in alpha_set)):
        if a <= 0:
            continue
        if _i_bh_bits_from_mass(a * mp_kg) >= float(i_anchor_bits):
            return int(a)
    return int(max(alpha_set))


def _best_n_for_fixed_m(i_bh_bits: float, m: int, n_set: Sequence[int]) -> Tuple[int, int, float]:
    """
    Return (n, I_prot, delta) for fixed m with lexicographic key:
      (delta, n).
    """
    if i_bh_bits <= 0.0 or not math.isfinite(i_bh_bits):
        raise ValueError("i_bh_bits must be positive and finite")
    log_i_bh = math.log(float(i_bh_bits))
    best: Tuple[float, int, int] | None = None  # (delta, n, I_prot)
    for n in n_set:
        ip = _i_prot_bits(m, n)
        d = abs((math.log(float(m)) + float(n) * math.log(4.0)) - log_i_bh)
        key = (d, int(n), int(ip))
        if best is None or key < best:
            best = key
    assert best is not None
    d, n, ip = best
    return (int(n), int(ip), float(d))


def _write_capacity_rows(rows: Sequence[CalibRow]) -> None:
    lines: List[str] = []
    for r in rows:
        lines.append(
            " & ".join(
                [
                    _fmt_int(r.alpha),
                    _fmt_int(r.m),
                    _fmt_int(r.n),
                    _fmt_int(r.i_prot_bits),
                    _fmt_float(r.i_bh_bits, digits=3),
                    _fmt_float(r.delta, digits=6),
                ]
            )
            + r" \\"
        )
    out = generated_dir() / "bh_planck_capacity_rows.tex"
    write_lines(out, lines if lines else ["% (no rows)"])


def _write_uplift_path_rows(
    m_set: Sequence[int],
    n_set: Sequence[int],
    i_bh_ref_bits: float,
    alpha_ref: int,
) -> None:
    lines: List[str] = []
    for m in m_set:
        n, ip, d = _best_n_for_fixed_m(i_bh_ref_bits, int(m), n_set)
        note = rf"$M/m_P={alpha_ref}$; $\Delta={_fmt_float(d, digits=3)}$"
        lines.append(
            " & ".join(
                [
                    _fmt_int(int(m)),
                    _fmt_int(int(n)),
                    _fmt_int(int(ip)),
                    note,
                ]
            )
            + r" \\"
        )
    out = generated_dir() / "bh_capacity_calibrated_uplift_path_rows.tex"
    write_lines(out, lines if lines else ["% (no rows)"])


def _write_summary(
    m_set: Sequence[int],
    n_set: Sequence[int],
    alpha_set: Sequence[int],
    mp_kg: float,
    lp2: float,
    i_anchor_bits: int,
    alpha_ref: int,
    i_bh_ref_bits: float,
) -> None:
    m_list = ", ".join(str(int(x)) for x in m_set)
    n_list = ", ".join(str(int(x)) for x in n_set)
    a_list = ", ".join(str(int(x)) for x in alpha_set)
    lines: List[str] = [
        r"\paragraph{Audit summary (capacity calibration).} \AuditTag "
        + rf"Candidate family: $m\in\{{{m_list}\}}$, $n\in\{{{n_list}\}}$; "
        + rf"mass test family: $M/m_P\in\{{{a_list}\}}$ (Schwarzschild area law).",
        r"\noindent\AuditTag "
        + rf"Computed constants (SI): $m_P={_fmt_sci_tex(mp_kg, digits=6)}\,\mathrm{{kg}}$, "
        + rf"$\ell_P^2={_fmt_sci_tex(lp2, digits=6)}\,\mathrm{{m}}^2$, "
        + rf"$G={_fmt_sci_tex(G_M3_KG_S2, digits=6)}\,\mathrm{{m^3\,kg^{-1}\,s^{-2}}}$.",
        r"\noindent\AuditTag "
        + rf"Anchor capacity: $I_{{\mathrm{{prot}}}}(6,3)={i_anchor_bits}$ bits. "
        + rf"Reference mass for the uplift-path table: $M/m_P={alpha_ref}$ "
        + rf"(smallest dyadic $\\alpha$ with $I_{{\\mathrm{{BH}}}}(\\alpha m_P)\\ge I_{{\\mathrm{{prot}}}}(6,3)$), "
        + rf"so $I_{{\\mathrm{{BH}}}}(M)={_fmt_float(i_bh_ref_bits, digits=3)}$ bits.",
    ]
    out = generated_dir() / "bh_planck_capacity_summary.tex"
    write_lines(out, lines if lines else ["% (empty)"])


def _write_known_rows(rows: Sequence[KnownRow]) -> None:
    lines: List[str] = []
    for r in rows:
        i_prot_tex = rf"${int(r.m)}\,4^{{{int(r.n)}}}$"
        m_over_mp_tex = rf"${_fmt_sci_tex(r.m_over_mp, digits=6)}$"
        i_bh_tex = rf"${_fmt_sci_tex(r.i_bh_bits, digits=6)}$"
        lines.append(
            " & ".join(
                [
                    r.name,
                    _fmt_float(r.m_over_msun, digits=6),
                    m_over_mp_tex,
                    _fmt_int(r.m),
                    _fmt_int(r.n),
                    i_prot_tex,
                    i_bh_tex,
                    _fmt_float(r.delta, digits=6),
                ]
            )
            + r" \\"
        )
    out = generated_dir() / "bh_planck_capacity_known_rows.tex"
    write_lines(out, lines if lines else ["% (no rows)"])


def _write_known_summary(
    m_set: Sequence[int],
    n_set_known: Sequence[int],
    names: Sequence[str],
) -> None:
    m_list = ", ".join(str(int(x)) for x in m_set)
    n_min = int(min(n_set_known)) if n_set_known else 0
    n_max = int(max(n_set_known)) if n_set_known else 0
    items = "; ".join(names) if names else "(none)"
    lines: List[str] = [
        r"\paragraph{Audit summary (reference black holes).} \AuditTag "
        + rf"Candidate family: $m\in\{{{m_list}\}}$, $n\in\{{{n_min},\dots,{n_max}\}}$ (bounded finite set).",
        r"\noindent\AuditTag " + rf"Reference objects: {items}.",
    ]
    out = generated_dir() / "bh_planck_capacity_known_summary.tex"
    write_lines(out, lines if lines else ["% (empty)"])


def main() -> None:
    m_set = _candidate_m()
    n_set = _candidate_n()
    alpha_set = _mass_family_alpha()

    mp_kg = _m_p()
    lp2 = _l_p_sq()

    # Main calibration rows: best (m,n) for each mass in the finite family.
    rows: List[CalibRow] = []
    for a in alpha_set:
        mass_kg = float(a) * mp_kg
        i_bh = _i_bh_bits_from_mass(mass_kg)
        m_star, n_star, ip_star, d_star = _best_mn_for_mass(i_bh, m_set, n_set)
        rows.append(
            CalibRow(
                alpha=int(a),
                m=int(m_star),
                n=int(n_star),
                i_prot_bits=int(ip_star),
                i_bh_bits=float(i_bh),
                delta=float(d_star),
            )
        )

    # Reference mass for the uplift-path table (deterministic).
    i_anchor_bits = _i_prot_bits(6, 3)
    alpha_ref = _select_alpha_ref(i_anchor_bits, alpha_set, mp_kg)
    i_bh_ref_bits = _i_bh_bits_from_mass(alpha_ref * mp_kg)

    _write_capacity_rows(rows)
    _write_uplift_path_rows(m_set, n_set, i_bh_ref_bits, alpha_ref)
    _write_summary(m_set, n_set, alpha_set, mp_kg, lp2, i_anchor_bits, alpha_ref, i_bh_ref_bits)

    # Reference black holes (known objects) under an extended but still finite n-family.
    n_set_known = _candidate_n_known(max_n=200)
    msun_kg = _m_sun_kg()
    known_rows: List[KnownRow] = []
    for name, m_over_msun in _known_bh_family_m_over_msun():
        mass_kg = float(m_over_msun) * msun_kg
        i_bh = _i_bh_bits_from_mass(mass_kg)
        m_star, n_star, _ip_star, d_star = _best_mn_for_mass(i_bh, m_set, n_set_known)
        known_rows.append(
            KnownRow(
                name=str(name),
                m_over_msun=float(m_over_msun),
                m_over_mp=float(mass_kg / mp_kg),
                m=int(m_star),
                n=int(n_star),
                i_bh_bits=float(i_bh),
                delta=float(d_star),
            )
        )
    _write_known_rows(known_rows)
    _write_known_summary(m_set, n_set_known, [r.name for r in known_rows])


if __name__ == "__main__":
    main()

