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
    mismatches: List[float] = []
    coord_i = 0

    for d in ds:
        ds_id = str(d.get("id", "dataset"))
        ab = _abscissa_from_dataset(d)
        pts_raw = list(d.get("points", []))
        pts: List[PhasePoint] = [PhasePoint(E=float(p["E"]), delta=float(p["delta"])) for p in pts_raw]

        for r in list(d.get("resonances", [])):
            E0 = float(r["E0"])
            gamma = float(r["gamma"])
            unit = str(r.get("gamma_unit", ab.unit))
            if gamma <= 0:
                continue
            # Proxy convention: tau_proxy(E0) ~ 4/gamma when gamma is expressed in the same abscissa units.
            if unit != ab.unit:
                continue
            tau_pred = float(4.0 / gamma)
            # Report a small, bounded window family (k=1..3) to make discretization sensitivity explicit.
            for k in (1, 2, 3):
                slope = _local_linear_slope(pts, E0=E0, k=int(k), coord=None)
                if slope is None:
                    continue
                tau_from_phase = float(2.0 * slope)
                sgn = "+" if tau_from_phase >= 0.0 else "-"
                # Compare magnitudes but keep sign as a separate audit output.
                e = _safe_log_mismatch(abs(tau_from_phase), abs(tau_pred))
                mismatches.append(e)
                n_cmp += 1
                rows.append(
                    " & ".join(
                        [
                            ds_id.replace("_", r"\_"),
                            ab.symbol.replace("_", r"\_"),
                            ab.unit.replace("_", r"\_"),
                            _fmt(E0, 6),
                            _fmt(gamma, 6),
                            str(int(k)),
                            _fmt(tau_from_phase, 6),
                            _fmt(tau_pred, 6),
                            sgn,
                            _fmt(e, 6),
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
                        gamma_y = float(gamma * jac)
                        tau_gamma_y = float(4.0 / gamma_y) if (gamma_y > 0.0) else float("nan")
                        sgn_y = "+" if tau_phase_y >= 0.0 else "-"
                        e_y = _safe_log_mismatch(abs(tau_phase_y), abs(tau_gamma_y))
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
                                    _fmt(tau_gamma_y, 6),
                                    sgn_y,
                                    _fmt(e_y, 6),
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

    mismatches.sort()
    med = mismatches[len(mismatches) // 2]
    mx = mismatches[-1]
    mn = mismatches[0]
    write_lines(
        sum_path,
        [
            r"\paragraph{Audit summary (WS proxy vs linewidth proxy).} \AuditTag "
            + rf"Comparisons: {n_cmp}. "
            + r"We estimate a phase-derived delay proxy by $\tau_{\mathrm{phase}}\approx 2\,\mathrm{d}\delta/\mathrm{d}x$ "
            + r"and compare it to the single-resonance linewidth proxy $\tau_{\gamma}\approx 4/\gamma$ in the same abscissa units. "
            + r"We report (i) the sign of $\tau_{\mathrm{phase}}$ and (ii) an absolute log mismatch on magnitudes "
            + r"$e=\lvert\log(\lvert\tau_{\mathrm{phase}}\rvert/\lvert\tau_{\gamma}\rvert)\rvert$.",
            r"\noindent\AuditTag "
            + rf"Mismatch summary over the bounded window family: min/median/max $e=({_fmt(mn,6)},{_fmt(med,6)},{_fmt(mx,6)})$.",
        ],
    )


if __name__ == "__main__":
    main()

