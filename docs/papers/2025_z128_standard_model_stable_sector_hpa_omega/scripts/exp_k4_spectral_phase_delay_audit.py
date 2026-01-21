# -*- coding: utf-8 -*-
"""
K4 spectral phase -> delay audit (data-facing, deterministic).

This audit mirrors the K4 scattering phase->delay interface, but uses a spectral
response phase phi(omega)=arg S(omega) with omega in rad/s.

Convention:
  - Here tau_i := d(phi)/d(omega) (no factor 2), because phi is the full response
    phase of S(omega). (For scattering phase shifts, S=exp(2 i delta) motivates
    the 2*d(delta)/dE proxy.)

Inputs:
  - data/k4_matching/spectral_phase_registry.json

Outputs (LaTeX fragments):
  - sections/generated/k4_spectral_phase_delay_rows.tex
  - sections/generated/k4_spectral_phase_delay_window_rows.tex
  - sections/generated/k4_spectral_phase_delay_summary.tex

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.
  - If no datasets are present, still succeed and emit a minimal note.
"""

from __future__ import annotations

import cmath
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from common_paths import generated_dir, paper_root
from common_tex import write_lines


def _read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(float(x)):
        return "nan"
    ax = abs(float(x))
    # Use a deterministic compact format: fixed for moderate values, scientific for tiny/huge.
    if ax == 0.0:
        return "0"
    if ax < 1.0e-4 or ax >= 1.0e4:
        exp = int(math.floor(math.log10(ax)))
        mant = float(x) / (10.0**exp)
        return f"{mant:.6g}\\times 10^{{{exp}}}"
    return f"{float(x):.{int(digits)}f}"


@dataclass(frozen=True)
class PhasePoint:
    omega: float
    phi: float


@dataclass(frozen=True)
class Abscissa:
    symbol: str
    unit: str


def _abscissa_from_dataset(d: Dict[str, Any]) -> Abscissa:
    a = dict(d.get("abscissa", {}) or {})
    symbol = str(a.get("symbol", "omega"))
    unit = str(a.get("unit", "rad/s"))
    return Abscissa(symbol=symbol, unit=unit)


def _unwrap(phases: List[float]) -> List[float]:
    """Deterministic 1D unwrap to enforce continuity (2*pi jumps)."""
    if not phases:
        return []
    out = [float(phases[0])]
    two_pi = 2.0 * math.pi
    for p in phases[1:]:
        v = float(p)
        prev = out[-1]
        # bring v close to prev by adding/subtracting 2pi
        while (v - prev) > math.pi:
            v -= two_pi
        while (v - prev) < -math.pi:
            v += two_pi
        out.append(v)
    return out


def _materialize_points(d: Dict[str, Any]) -> List[PhasePoint]:
    # If explicit point cloud exists, use it.
    pts_raw = list(d.get("points", []))
    if pts_raw:
        pts = [PhasePoint(omega=float(p["omega"]), phi=float(p["phi"])) for p in pts_raw]
        pts_sorted = sorted(pts, key=lambda p: p.omega)
        ph_unwrapped = _unwrap([p.phi for p in pts_sorted])
        return [PhasePoint(omega=p.omega, phi=ph) for p, ph in zip(pts_sorted, ph_unwrapped)]

    # Otherwise materialize from a deterministic toy model family.
    model = dict(d.get("model", {}) or {})
    fam = str(model.get("family", ""))
    if fam != "one_channel_unitary_resonance":
        return []
    omega0 = float(model.get("omega0", 0.0))
    gamma = float(model.get("gamma", 1.0))
    mults = list(d.get("offset_multipliers", []))
    if not mults:
        mults = [-5.0, -4.0, -3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0]

    omegas = [omega0 + float(m) * gamma for m in mults]
    omegas_sorted = sorted(omegas)

    phases: List[float] = []
    for w in omegas_sorted:
        # One-channel unitary resonance:
        #   S(omega) = (omega-omega0 - i gamma/2) / (omega-omega0 + i gamma/2)
        z = complex(float(w) - omega0, 0.0)
        num = z - 1j * (gamma / 2.0)
        den = z + 1j * (gamma / 2.0)
        S = num / den
        phases.append(float(cmath.phase(S)))
    phases_u = _unwrap(phases)
    return [PhasePoint(omega=float(w), phi=float(ph)) for w, ph in zip(omegas_sorted, phases_u)]


def _local_linear_slope(
    points: List[PhasePoint],
    omega0: float,
    k: int,
    coord: Optional[Callable[[PhasePoint], float]] = None,
) -> Optional[float]:
    if coord is None:
        coord = lambda p: p.omega  # noqa: E731
    if len(points) < 2 * k + 1:
        return None
    ps = sorted(points, key=lambda p: p.omega)
    j = min(range(len(ps)), key=lambda i: abs(ps[i].omega - omega0))
    lo = j - int(k)
    hi = j + int(k)
    if lo < 0 or hi >= len(ps):
        return None
    xs = [float(coord(ps[i])) for i in range(lo, hi + 1)]
    ys = [ps[i].phi for i in range(lo, hi + 1)]
    xbar = sum(xs) / float(len(xs))
    ybar = sum(ys) / float(len(ys))
    num = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
    den = sum((x - xbar) * (x - xbar) for x in xs)
    if den == 0.0:
        return None
    return float(num / den)


def _tau_series(points: List[PhasePoint], coord: Optional[Callable[[PhasePoint], float]] = None) -> List[float]:
    """tau_i := d(phi)/d(omega) via central differences on interior points."""
    if coord is None:
        coord = lambda p: p.omega  # noqa: E731
    if len(points) < 3:
        return []
    ps = sorted(points, key=lambda p: p.omega)
    taus: List[float] = []
    for i in range(1, len(ps) - 1):
        x_lo, p_lo = float(coord(ps[i - 1])), ps[i - 1].phi
        x_hi, p_hi = float(coord(ps[i + 1])), ps[i + 1].phi
        if x_hi == x_lo:
            continue
        taus.append(float((p_hi - p_lo) / (x_hi - x_lo)))
    return taus


def _tau_series_window(points: List[PhasePoint], k: int, coord: Optional[Callable[[PhasePoint], float]] = None) -> List[float]:
    """tau_i := d(phi)/d(omega) by local linear slope on window radius k."""
    if coord is None:
        coord = lambda p: p.omega  # noqa: E731
    if len(points) < 2 * k + 1:
        return []
    ps = sorted(points, key=lambda p: p.omega)
    taus: List[float] = []
    for i in range(k, len(ps) - k):
        slope = _local_linear_slope(ps, omega0=float(ps[i].omega), k=int(k), coord=coord)
        if slope is None:
            continue
        taus.append(float(slope))
    return taus


def _median(xs: List[float]) -> float:
    ys = sorted(float(x) for x in xs)
    if not ys:
        return float("nan")
    n = len(ys)
    if n % 2 == 1:
        return float(ys[n // 2])
    return float(0.5 * (ys[n // 2 - 1] + ys[n // 2]))


def main() -> None:
    reg = _read_json(paper_root() / "data" / "k4_matching" / "spectral_phase_registry.json")
    ds = list(reg.get("datasets", []))

    out = generated_dir()
    rows_path = out / "k4_spectral_phase_delay_rows.tex"
    win_rows_path = out / "k4_spectral_phase_delay_window_rows.tex"
    sum_path = out / "k4_spectral_phase_delay_summary.tex"

    if not ds:
        write_lines(rows_path, ["% (no spectral phase datasets registered)"])
        write_lines(win_rows_path, ["% (no window-family rows)"])
        write_lines(
            sum_path,
            [
                r"\paragraph{Audit summary (K4 spectral phase $\to$ delay).} \AuditTag "
                + r"No datasets registered in \texttt{data/k4\_matching/spectral\_phase\_registry.json}. "
                + r"This audit is currently a dormant interface; vendored phase samples can activate it.",
            ],
        )
        return

    rows: List[str] = []
    win_rows: List[str] = []
    for i, d in enumerate(ds, start=1):
        label = str(d.get("id", f"dataset_{i}"))
        ab = _abscissa_from_dataset(d)
        pts = _materialize_points(d)
        taus = _tau_series(pts, coord=None)
        tau_med = _median(taus)
        tau_min = float(min(taus)) if taus else float("nan")
        tau_max = float(max(taus)) if taus else float("nan")
        frac_neg = (sum(1 for x in taus if x < 0.0) / float(len(taus))) if taus else float("nan")

        rows.append(
            " & ".join(
                [
                    str(i),
                    label.replace("_", r"\_"),
                    ab.symbol.replace("_", r"\_"),
                    ab.unit.replace("_", r"\_"),
                    str(len(pts)),
                    str(len(taus)),
                    _fmt(float(tau_med), 6),
                    _fmt(float(tau_min), 6),
                    _fmt(float(tau_max), 6),
                    _fmt(float(frac_neg), 6),
                ]
            )
            + r" \\"
        )

        for k in (1, 2, 3):
            taus_k = _tau_series_window(pts, k=int(k), coord=None)
            tau_med_k = _median(taus_k)
            tau_min_k = float(min(taus_k)) if taus_k else float("nan")
            tau_max_k = float(max(taus_k)) if taus_k else float("nan")
            frac_neg_k = (sum(1 for x in taus_k if x < 0.0) / float(len(taus_k))) if taus_k else float("nan")
            win_rows.append(
                " & ".join(
                    [
                        str(i),
                        label.replace("_", r"\_"),
                        ab.symbol.replace("_", r"\_"),
                        ab.unit.replace("_", r"\_"),
                        str(int(k)),
                        str(len(taus_k)),
                        _fmt(float(tau_med_k), 6),
                        _fmt(float(tau_min_k), 6),
                        _fmt(float(tau_max_k), 6),
                        _fmt(float(frac_neg_k), 6),
                    ]
                )
                + r" \\"
            )

    write_lines(rows_path, rows if rows else ["% (no rows)"])
    write_lines(win_rows_path, win_rows if win_rows else ["% (no window rows)"])

    write_lines(
        sum_path,
        [
            r"\paragraph{Audit summary (K4 spectral phase $\to$ delay).} \AuditTag "
            + rf"Dataset count: {len(ds)}. "
            + r"For each dataset we compute a signed proxy series "
            + r"$\tau_i:=\mathrm{d}\phi/\mathrm{d}\omega$ (units: seconds) on interior points (central differences) "
            + r"and report median/min/max and the negative fraction. "
            + r"Sign convention note: in signal-processing language the (positive) group delay is often defined as "
            + r"$\tau_g:=-\mathrm{d}\phi/\mathrm{d}\omega$ for a transfer-function phase $\phi(\omega)$; "
            + r"thus negative $\tau$ corresponds to positive group delay under that convention. "
            + r"We additionally report a bounded window family ($k=1,2,3$) using local linear fits "
            + r"to make discretization sensitivity explicit. "
            + r"Datasets are read from \texttt{data/k4\_matching/spectral\_phase\_registry.json}.",
        ],
    )


if __name__ == "__main__":
    main()

