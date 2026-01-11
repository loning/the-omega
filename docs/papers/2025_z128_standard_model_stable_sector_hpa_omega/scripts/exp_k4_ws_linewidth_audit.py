# -*- coding: utf-8 -*-
"""
K4 scattering: Wigner-Smith proxy vs linewidth proxy calibration audit.

Goal:
  Provide a minimal *externally falsifiable* interface check:
    - compute a delay proxy from phase-shift points (finite differences)
    - compare against a linewidth proxy tau ~ 4/gamma (single-resonance benchmark)

This audit is intentionally simple and can be activated by a single measured resonance.

Outputs (LaTeX fragments):
  - sections/generated/k4_ws_linewidth_rows.tex
  - sections/generated/k4_ws_linewidth_summary.tex

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from common_paths import generated_dir, paper_root
from common_tex import write_lines


def _read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


@dataclass(frozen=True)
class PhasePoint:
    E: float
    delta: float


@dataclass(frozen=True)
class Abscissa:
    symbol: str
    unit: str


def _abscissa_from_dataset(d: Dict[str, Any]) -> Abscissa:
    a = dict(d.get("abscissa", {}) or {})
    symbol = str(a.get("symbol", "E"))
    unit = str(a.get("unit", "arb"))
    return Abscissa(symbol=symbol, unit=unit)


def _local_linear_slope(
    points: List[PhasePoint],
    E0: float,
    k: int,
    coord: Optional[Callable[[PhasePoint], float]] = None,
) -> Optional[float]:
    """
    Deterministic local linear fit slope for d(delta)/dx near E0, where x is an
    abscissa coordinate.
    - Find the closest sample index to E0.
    - Fit a line delta = a + b x on the symmetric window of radius k samples.
    Returns b.
    """
    if coord is None:
        coord = lambda p: p.E  # noqa: E731
    if len(points) < 2 * k + 1:
        return None
    ps = sorted(points, key=lambda p: p.E)
    j = min(range(len(ps)), key=lambda i: abs(ps[i].E - E0))
    lo = j - int(k)
    hi = j + int(k)
    if lo < 0 or hi >= len(ps):
        return None
    xs = [float(coord(ps[i])) for i in range(lo, hi + 1)]
    ys = [ps[i].delta for i in range(lo, hi + 1)]
    xbar = sum(xs) / float(len(xs))
    ybar = sum(ys) / float(len(ys))
    num = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
    den = sum((x - xbar) * (x - xbar) for x in xs)
    if den == 0.0:
        return None
    return float(num / den)


def _safe_log_mismatch(a: float, b: float) -> float:
    if not (a > 0 and b > 0):
        return float("inf")
    return float(abs(math.log(a / b)))


def _interval_from_resonance(r: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """
    Return (gamma_low, gamma_high) if present; otherwise (None, None).
    """
    gl = r.get("gamma_low", None)
    gh = r.get("gamma_high", None)
    try:
        glf = float(gl) if gl is not None else None
    except Exception:
        glf = None
    try:
        ghf = float(gh) if gh is not None else None
    except Exception:
        ghf = None
    if glf is None or ghf is None:
        return (None, None)
    if not (math.isfinite(glf) and math.isfinite(ghf)):
        return (None, None)
    if glf <= 0.0 or ghf <= 0.0:
        return (None, None)
    if glf > ghf:
        glf, ghf = ghf, glf
    return (glf, ghf)


def _tau_gamma_interval(gamma_low: float, gamma_high: float) -> Tuple[float, float]:
    """
    tau_gamma = 4/gamma. For gamma in [low, high], tau in [4/high, 4/low].
    Returns (tau_min, tau_max).
    """
    tau_min = float(4.0 / float(gamma_high))
    tau_max = float(4.0 / float(gamma_low))
    return (tau_min, tau_max)


def _mismatch_interval(tau_phase_abs: float, tau_min: float, tau_max: float) -> Tuple[float, float]:
    """
    e(tau) = |log(tau_phase_abs / tau)| for tau in [tau_min, tau_max], tau>0.
    Return (e_min, e_max).
    """
    if not (tau_phase_abs > 0 and tau_min > 0 and tau_max > 0):
        return (float("inf"), float("inf"))
    if tau_min > tau_max:
        tau_min, tau_max = tau_max, tau_min
    e_a = _safe_log_mismatch(tau_phase_abs, tau_min)
    e_b = _safe_log_mismatch(tau_phase_abs, tau_max)
    # If tau_phase lies inside the interval, the minimum mismatch can be 0 (achieved at tau=tau_phase).
    if tau_min <= tau_phase_abs <= tau_max:
        e_min = 0.0
    else:
        e_min = float(min(e_a, e_b))
    e_max = float(max(e_a, e_b))
    return (e_min, e_max)


def main() -> None:
    reg = _read_json(paper_root() / "data" / "k4_matching" / "scattering_phase_registry.json")
    ds = list(reg.get("datasets", []))

    out = generated_dir()
    rows_path = out / "k4_ws_linewidth_rows.tex"
    coord_rows_path = out / "k4_ws_linewidth_coord_rows.tex"
    sum_path = out / "k4_ws_linewidth_summary.tex"

    rows: List[str] = []
    coord_rows: List[str] = []
    n_cmp = 0
    mismatches_min: List[float] = []
    mismatches_max: List[float] = []
    coord_i = 0

    for d in ds:
        ds_id = str(d.get("id", "dataset"))
        ab = _abscissa_from_dataset(d)
        pts_raw = list(d.get("points", []))
        pts: List[PhasePoint] = [PhasePoint(E=float(p["E"]), delta=float(p["delta"])) for p in pts_raw]

        for r in list(d.get("resonances", [])):
            E0 = float(r["E0"])
            unit = str(r.get("gamma_unit", ab.unit))
            # Proxy convention: tau_proxy(E0) ~ 4/gamma when gamma is expressed in the same abscissa units.
            if unit != ab.unit:
                continue

            gl, gh = _interval_from_resonance(r)
            if gl is not None and gh is not None:
                gamma_low = float(gl)
                gamma_high = float(gh)
            else:
                gamma = float(r["gamma"])
                if gamma <= 0:
                    continue
                gamma_low = float(gamma)
                gamma_high = float(gamma)

            tau_min, tau_max = _tau_gamma_interval(gamma_low, gamma_high)
            # Report a small, bounded window family (k=1..3) to make discretization sensitivity explicit.
            for k in (1, 2, 3):
                slope = _local_linear_slope(pts, E0=E0, k=int(k), coord=None)
                if slope is None:
                    continue
                tau_from_phase = float(2.0 * slope)
                sgn = "+" if tau_from_phase >= 0.0 else "-"

                # Compare magnitudes but keep sign as a separate audit output.
                e_min, e_max = _mismatch_interval(abs(tau_from_phase), tau_min=tau_min, tau_max=tau_max)
                mismatches_min.append(e_min)
                mismatches_max.append(e_max)
                n_cmp += 1
                rows.append(
                    " & ".join(
                        [
                            ds_id.replace("_", r"\_"),
                            ab.symbol.replace("_", r"\_"),
                            ab.unit.replace("_", r"\_"),
                            _fmt(E0, 6),
                            _fmt(gamma_low, 6),
                            _fmt(gamma_high, 6),
                            str(int(k)),
                            _fmt(tau_from_phase, 6),
                            _fmt(tau_min, 6),
                            _fmt(tau_max, 6),
                            sgn,
                            _fmt(e_min, 6),
                            _fmt(e_max, 6),
                        ]
                    )
                    + r" \\"
                )

                # Optional coordinate-transform report: only meaningful when x is NN-OnLine T_lab (MeV).
                if ds_id.startswith("nn_online_np_") and ab.symbol == "T_lab" and ab.unit == "MeV":
                    m_p = 938.2720813
                    m_n = 939.5654133

                    # y = E_cm,kin (MeV), with analytic dy/dT for each hypothesis.
                    def dy_dx_nr(T: float) -> float:
                        return float(m_p / (m_p + m_n))

                    def dy_dx_rel(T: float) -> float:
                        s = (m_p * m_p) + (m_n * m_n) + (2.0 * m_p * (m_n + T))
                        return float(m_p / math.sqrt(s))

                    for j, (tid, ysym, yunit, dy_dx_fn) in enumerate(
                        [
                            ("Tlab_to_Ecmkin_NR", r"$E_{\mathrm{cm,kin}}^{(\mathrm{NR})}$", "MeV", dy_dx_nr),
                            ("Tlab_to_Ecmkin_REL", r"$E_{\mathrm{cm,kin}}^{(\mathrm{REL})}$", "MeV", dy_dx_rel),
                        ],
                        start=1,
                    ):
                        jac = float(dy_dx_fn(float(E0)))
                        if jac == 0.0 or not math.isfinite(jac):
                            continue
                        tau_phase_y = float(tau_from_phase / jac)
                        gamma_low_y = float(gamma_low * jac)
                        gamma_high_y = float(gamma_high * jac)
                        if gamma_low_y <= 0.0 or gamma_high_y <= 0.0:
                            continue
                        tau_y_min, tau_y_max = _tau_gamma_interval(gamma_low_y, gamma_high_y)
                        sgn_y = "+" if tau_phase_y >= 0.0 else "-"
                        e_y_min, e_y_max = _mismatch_interval(abs(tau_phase_y), tau_min=tau_y_min, tau_max=tau_y_max)
                        coord_i += 1
                        coord_rows.append(
                            " & ".join(
                                [
                                    str(coord_i),
                                    ds_id.replace("_", r"\_"),
                                    tid.replace("_", r"\_"),
                                    ysym,
                                    yunit.replace("_", r"\_"),
                                    str(int(k)),
                                    _fmt(tau_phase_y, 6),
                                    _fmt(tau_y_min, 6),
                                    _fmt(tau_y_max, 6),
                                    sgn_y,
                                    _fmt(e_y_min, 6),
                                    _fmt(e_y_max, 6),
                                ]
                            )
                            + r" \\"
                        )

    write_lines(rows_path, rows if rows else ["% (no resonance comparisons available)"])
    write_lines(coord_rows_path, coord_rows if coord_rows else ["% (no coordinate-transform resonance comparisons available)"])

    if n_cmp <= 0:
        write_lines(
            sum_path,
            [
                r"\paragraph{Audit summary (WS proxy vs linewidth proxy).} \AuditTag "
                + r"No usable resonance metadata found in \texttt{data/k4\_matching/scattering\_phase\_registry.json}. "
                + r"Provide a resonance entry with \texttt{E0,gamma} and \texttt{gamma\_unit} matching the dataset abscissa unit to activate this audit.",
            ],
        )
        return

    mismatches_min.sort()
    mismatches_max.sort()
    med_min = mismatches_min[len(mismatches_min) // 2]
    mx_min = mismatches_min[-1]
    mn_min = mismatches_min[0]
    med_max = mismatches_max[len(mismatches_max) // 2]
    mx_max = mismatches_max[-1]
    mn_max = mismatches_max[0]
    write_lines(
        sum_path,
        [
            r"\paragraph{Audit summary (WS proxy vs linewidth proxy).} \AuditTag "
            + rf"Comparisons: {n_cmp}. "
            + r"We estimate a phase-derived delay proxy by $\tau_{\mathrm{phase}}\approx 2\,\mathrm{d}\delta/\mathrm{d}x$ "
            + r"and compare it to the single-resonance linewidth proxy $\tau_{\gamma}\approx 4/\gamma$ (or an interval if $\gamma$ is specified as a range) in the same abscissa units. "
            + r"We report (i) the sign of $\tau_{\mathrm{phase}}$ and (ii) an absolute log mismatch envelope on magnitudes "
            + r"$e=\lvert\log(\lvert\tau_{\mathrm{phase}}\rvert/\lvert\tau_{\gamma}\rvert)\rvert$ over the allowed $\tau_{\gamma}$ interval.",
            r"\noindent\AuditTag "
            + rf"Mismatch envelope summary over the bounded window family: "
            + rf"$e_{{\min}}=({_fmt(mn_min,6)},{_fmt(med_min,6)},{_fmt(mx_min,6)})$, "
            + rf"$e_{{\max}}=({_fmt(mn_max,6)},{_fmt(med_max,6)},{_fmt(mx_max,6)})$ (min/median/max).",
        ],
    )


if __name__ == "__main__":
    main()

