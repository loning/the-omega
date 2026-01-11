# -*- coding: utf-8 -*-
"""
K4 scattering phase-shift -> Wigner-Smith delay audit (data-facing, deterministic).

This is a *skeleton* audit that becomes active once datasets are vendored into
data/k4_matching/scattering_phase_registry.json.

We avoid any network access and require explicit literals for reproducibility.

Outputs (LaTeX fragments):
  - sections/generated/k4_scattering_phase_delay_rows.tex
  - sections/generated/k4_scattering_phase_delay_summary.tex

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.
  - If no datasets are present, still succeed and emit a minimal note.
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
    - Find the closest sample index to E0 (using the raw E field for indexing).
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


def _tau_series_window(points: List[PhasePoint], k: int, coord: Optional[Callable[[PhasePoint], float]] = None) -> List[float]:
    """
    Compute tau_i := 2 * d(delta)/dx at interior points by local linear fits
    over a bounded window radius k.
    """
    if coord is None:
        coord = lambda p: p.E  # noqa: E731
    if len(points) < 2 * k + 1:
        return []
    ps = sorted(points, key=lambda p: p.E)
    taus: List[float] = []
    for i in range(k, len(ps) - k):
        slope = _local_linear_slope(ps, E0=float(ps[i].E), k=int(k), coord=coord)
        if slope is None:
            continue
        taus.append(float(2.0 * slope))
    return taus


def _window_centers(points: List[PhasePoint], k: int) -> List[PhasePoint]:
    """
    Return the list of center points used by the window-family estimator for a given k.
    """
    if len(points) < 2 * k + 1:
        return []
    ps = sorted(points, key=lambda p: p.E)
    return [ps[i] for i in range(int(k), len(ps) - int(k))]


def _tau_series(points: List[PhasePoint], coord: Optional[callable] = None) -> List[float]:
    """
    Compute a simple signed proxy series:
      tau_i := 2 * d(delta)/dx at interior points via central differences,
      where x is a dataset-dependent abscissa coordinate.

    Notes:
      - We keep the sign. Signed Wigner time delay can be negative depending on
        conventions and physics (e.g., repulsive phases); the audit reports sign
        distribution and does not clip.
      - Abscissa x is treated as the provided coordinate (matching layer fixes
        physical unit conventions and coordinate meaning).
    """
    if coord is None:
        coord = lambda p: p.E  # noqa: E731
    if len(points) < 3:
        return []
    ps = sorted(points, key=lambda p: p.E)
    taus: List[float] = []
    for i in range(1, len(ps) - 1):
        x_lo, d_lo = float(coord(ps[i - 1])), ps[i - 1].delta
        x_hi, d_hi = float(coord(ps[i + 1])), ps[i + 1].delta
        if x_hi == x_lo:
            continue
        slope = (d_hi - d_lo) / (x_hi - x_lo)
        taus.append(float(2.0 * slope))
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
    reg = _read_json(paper_root() / "data" / "k4_matching" / "scattering_phase_registry.json")
    ds = list(reg.get("datasets", []))

    out = generated_dir()
    rows_path = out / "k4_scattering_phase_delay_rows.tex"
    coord_rows_path = out / "k4_scattering_phase_delay_coord_rows.tex"
    win_rows_path = out / "k4_scattering_phase_delay_window_rows.tex"
    sum_path = out / "k4_scattering_phase_delay_summary.tex"

    if not ds:
        write_lines(rows_path, ["% (no scattering phase datasets registered)"])
        write_lines(coord_rows_path, ["% (no coordinate-transform rows)"])
        write_lines(win_rows_path, ["% (no window-family rows)"])
        write_lines(
            sum_path,
            [
                r"\paragraph{Audit summary (K4 scattering phase $\to$ delay).} \AuditTag "
                + r"No datasets registered in \texttt{data/k4\_matching/scattering\_phase\_registry.json}. "
                + r"This audit is currently a dormant interface; vendored phase-shift points can activate it.",
            ],
        )
        return

    rows: List[str] = []
    coord_rows: List[str] = []
    win_rows: List[str] = []
    for i, d in enumerate(ds, start=1):
        label = str(d.get("id", f"dataset_{i}"))
        ab = _abscissa_from_dataset(d)
        pts_raw = list(d.get("points", []))
        pts: List[PhasePoint] = []
        for p in pts_raw:
            pts.append(PhasePoint(E=float(p["E"]), delta=float(p["delta"])))
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

        # Window-family sensitivity report (k=1..3), local linear fits.
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

        # Optional coordinate transform family (reported, not selected).
        if label.startswith("nn_online_np_") and ab.symbol == "T_lab" and ab.unit == "MeV":
            # Two explicit hypotheses for mapping T_lab -> E_cm,kin (MeV):
            #   - NR: E_cm,kin = T_lab * m_target / (m_proj + m_target)
            #   - REL: E_cm,kin = sqrt(s) - (m_proj + m_target), with s = m_t^2 + m_p^2 + 2 m_t (m_p + T_lab)
            # We fix (proj=n, target=p at rest) for the vendored NN-OnLine np tables.
            m_p = 938.2720813
            m_n = 939.5654133

            def _Ecm_nr(p: PhasePoint) -> float:
                return float(p.E) * (m_p / (m_p + m_n))

            def _Ecm_rel(p: PhasePoint) -> float:
                T = float(p.E)
                s = (m_p * m_p) + (m_n * m_n) + (2.0 * m_p * (m_n + T))
                return float(math.sqrt(s) - (m_p + m_n))

            def _jac_nr(p: PhasePoint) -> float:
                return float(m_p / (m_p + m_n))

            def _jac_rel(p: PhasePoint) -> float:
                # y(T)=sqrt(s(T))-(m_p+m_n), with s(T)=m_p^2+m_n^2+2 m_p (m_n+T)
                # dy/dT = (1/(2 sqrt(s))) * 2 m_p = m_p / sqrt(s)
                T = float(p.E)
                s = (m_p * m_p) + (m_n * m_n) + (2.0 * m_p * (m_n + T))
                return float(m_p / math.sqrt(s))

            for j, (tid, ysym, yunit, fn, jac_fn) in enumerate(
                [
                    ("Tlab_to_Ecmkin_NR", r"$E_{\mathrm{cm,kin}}^{(\mathrm{NR})}$", "MeV", _Ecm_nr, _jac_nr),
                    ("Tlab_to_Ecmkin_REL", r"$E_{\mathrm{cm,kin}}^{(\mathrm{REL})}$", "MeV", _Ecm_rel, _jac_rel),
                ],
                start=1,
            ):
                for k in (1, 2, 3):
                    taus_y = _tau_series_window(pts, k=int(k), coord=fn)
                    centers = _window_centers(pts, k=int(k))
                    jacs = [float(jac_fn(p)) for p in centers] if centers else []
                    jac_min = float(min(jacs)) if jacs else float("nan")
                    jac_max = float(max(jacs)) if jacs else float("nan")
                    tau_med_y = _median(taus_y)
                    tau_min_y = float(min(taus_y)) if taus_y else float("nan")
                    tau_max_y = float(max(taus_y)) if taus_y else float("nan")
                    frac_neg_y = (sum(1 for x in taus_y if x < 0.0) / float(len(taus_y))) if taus_y else float("nan")
                    coord_rows.append(
                        " & ".join(
                            [
                                f"{i}.{j}",
                                label.replace("_", r"\_"),
                                tid.replace("_", r"\_"),
                                ysym,
                                yunit.replace("_", r"\_"),
                                str(int(k)),
                                str(len(taus_y)),
                                _fmt(float(jac_min), 6),
                                _fmt(float(jac_max), 6),
                                _fmt(float(tau_med_y), 6),
                                _fmt(float(tau_min_y), 6),
                                _fmt(float(tau_max_y), 6),
                                _fmt(float(frac_neg_y), 6),
                            ]
                        )
                        + r" \\"
                    )

    write_lines(rows_path, rows if rows else ["% (no rows)"])
    write_lines(coord_rows_path, coord_rows if coord_rows else ["% (no coordinate-transform rows)"])
    write_lines(win_rows_path, win_rows if win_rows else ["% (no window-family rows)"])
    write_lines(
        sum_path,
        [
            r"\paragraph{Audit summary (K4 scattering phase $\to$ delay).} \AuditTag "
            + rf"Dataset count: {len(ds)}. "
            + r"For each dataset we compute a signed central-difference proxy series "
            + r"$\tau_i:=2\,\mathrm{d}\delta/\mathrm{d}x$ on interior points (where $x$ is the dataset abscissa) and report summary statistics "
            + r"(median/min/max and the negative fraction). "
            + r"We additionally report a bounded window family ($k=1,2,3$) using local linear fits to make discretization sensitivity explicit. "
            + r"For NN-OnLine np tables with $x=T_{\mathrm{lab}}$, we also report two transparent coordinate-transform hypotheses "
            + r"($T_{\mathrm{lab}}\to E_{\mathrm{cm,kin}}^{(\mathrm{NR})}$ and $T_{\mathrm{lab}}\to E_{\mathrm{cm,kin}}^{(\mathrm{REL})}$) over the same bounded window family, without selecting one. "
            + r"When the coordinate change is monotone ($\mathrm{d}y/\mathrm{d}x>0$), the sign of $\mathrm{d}\delta/\mathrm{d}y$ must match the sign of $\mathrm{d}\delta/\mathrm{d}x$; the reported Jacobian ranges make this condition explicit. "
            + r"Unit conventions are deferred to the matching layer under explicit $P_{\mathrm{phys}}$ if needed.",
        ],
    )


if __name__ == "__main__":
    main()

