#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scattering inverse-consistency audit: phase -> delay -> reconstructed phase.

We reuse vendored phase-shift point clouds under:
  data/k4_matching/scattering_phase_registry.json

Audit idea (bounded, deterministic):
  - Given samples (x_i, delta_i), estimate derivative d(delta)/dx via a bounded
    family of estimators (central-difference; windowed local-linear k=1..3),
    optionally after a bounded moving-average smoothing of delta.
  - Define tau_i := 2 d(delta)/dx (Wigner-Smith proxy convention in the paper).
  - Invert by integrating d(delta)/dx to reconstruct delta_hat on the same grid,
    anchoring delta_hat at the first interior point to remove the additive constant.
  - Report residual norms between delta_hat and delta on interior points.

Outputs (LaTeX fragments):
  - sections/generated/scattering_inverse_consistency_rows.tex
  - sections/generated/scattering_inverse_consistency_summary.tex

Design goals:
  - Deterministic output (no randomness).
  - Standard-library only.
  - English-only output.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from common_paths import generated_dir, paper_root
from common_tex import write_lines


@dataclass(frozen=True)
class PhasePoint:
    x: float
    delta: float


def _read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


def _moving_average(xs: List[float], w: int) -> List[float]:
    if w <= 1:
        return list(xs)
    n = len(xs)
    pad = w // 2
    # edge padding (deterministic)
    xpad = [xs[0]] * pad + list(xs) + [xs[-1]] * pad
    out: List[float] = []
    inv = 1.0 / float(w)
    for i in range(n):
        s = 0.0
        for j in range(w):
            s += float(xpad[i + j])
        out.append(float(s * inv))
    return out


def _central_diff_slopes(points: List[PhasePoint]) -> Tuple[List[float], List[float]]:
    """
    Return (xs_interior, ddelta_dx_interior) using central differences.
    """
    ps = sorted(points, key=lambda p: p.x)
    if len(ps) < 3:
        return ([], [])
    xs: List[float] = []
    slopes: List[float] = []
    for i in range(1, len(ps) - 1):
        x_lo, d_lo = float(ps[i - 1].x), float(ps[i - 1].delta)
        x_hi, d_hi = float(ps[i + 1].x), float(ps[i + 1].delta)
        if x_hi == x_lo:
            continue
        xs.append(float(ps[i].x))
        slopes.append(float((d_hi - d_lo) / (x_hi - x_lo)))
    return (xs, slopes)


def _local_linear_slope(ps: List[PhasePoint], i_center: int, k: int) -> Optional[float]:
    lo = i_center - int(k)
    hi = i_center + int(k)
    if lo < 0 or hi >= len(ps):
        return None
    xs = [float(ps[j].x) for j in range(lo, hi + 1)]
    ys = [float(ps[j].delta) for j in range(lo, hi + 1)]
    xbar = sum(xs) / float(len(xs))
    ybar = sum(ys) / float(len(ys))
    num = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
    den = sum((x - xbar) * (x - xbar) for x in xs)
    if den == 0.0:
        return None
    return float(num / den)


def _window_slopes(points: List[PhasePoint], k: int) -> Tuple[List[float], List[float]]:
    ps = sorted(points, key=lambda p: p.x)
    if len(ps) < 2 * int(k) + 1:
        return ([], [])
    xs: List[float] = []
    slopes: List[float] = []
    for i in range(int(k), len(ps) - int(k)):
        s = _local_linear_slope(ps, i_center=i, k=int(k))
        if s is None:
            continue
        xs.append(float(ps[i].x))
        slopes.append(float(s))
    return (xs, slopes)


def _reconstruct_delta(xs: List[float], slopes: List[float], delta_ref: float) -> List[float]:
    """
    Reconstruct delta_hat on xs by integrating slopes (ddelta/dx), anchoring at xs[0].
    Uses trapezoidal update on the slope field.
    """
    if not xs:
        return []
    if len(xs) != len(slopes):
        raise ValueError("xs and slopes must have the same length")
    dhat: List[float] = [float(delta_ref)]
    for i in range(1, len(xs)):
        dx = float(xs[i] - xs[i - 1])
        inc = 0.5 * float(slopes[i - 1] + slopes[i]) * dx
        dhat.append(float(dhat[-1] + inc))
    return dhat


def _residual_norms(delta_true: List[float], delta_hat: List[float]) -> Tuple[float, float]:
    if not delta_true or not delta_hat or len(delta_true) != len(delta_hat):
        return (float("nan"), float("nan"))
    abs_res = [abs(float(a - b)) for a, b in zip(delta_true, delta_hat)]
    mean_abs = sum(abs_res) / float(len(abs_res))
    max_abs = max(abs_res) if abs_res else float("nan")
    return (float(mean_abs), float(max_abs))


def main() -> None:
    reg = _read_json(paper_root() / "data" / "k4_matching" / "scattering_phase_registry.json")
    ds = list(reg.get("datasets", []))

    out = generated_dir()
    rows_path = out / "scattering_inverse_consistency_rows.tex"
    sum_path = out / "scattering_inverse_consistency_summary.tex"

    if not ds:
        write_lines(rows_path, ["% (no scattering phase datasets registered)"])
        write_lines(
            sum_path,
            [
                r"\paragraph{Audit summary (inverse consistency: phase$\to$delay$\to$phase).} \AuditTag "
                + r"No datasets registered in \texttt{data/k4\_matching/scattering\_phase\_registry.json}.",
            ],
        )
        return

    smooth_ws = [1, 3, 5]
    window_ks = [1, 2, 3]

    rows: List[str] = []

    best_overall = None  # (mean_abs, max_abs, dataset_id, method)
    for d in ds:
        did = str(d.get("id", "dataset")).strip()
        ab = dict(d.get("abscissa", {}) or {})
        x_symbol = str(ab.get("symbol", "x"))
        x_unit = str(ab.get("unit", "arb"))
        pts_raw = list(d.get("points", []))
        pts: List[PhasePoint] = [PhasePoint(x=float(p["E"]), delta=float(p["delta"])) for p in pts_raw]
        pts = sorted(pts, key=lambda p: p.x)
        if len(pts) < 5:
            continue

        x_all = [p.x for p in pts]
        d_all = [p.delta for p in pts]

        for w in smooth_ws:
            d_sm = _moving_average(d_all, w=int(w))
            pts_sm = [PhasePoint(x=float(x), delta=float(dd)) for x, dd in zip(x_all, d_sm)]

            # Central-difference estimator.
            xs_cd, slopes_cd = _central_diff_slopes(pts_sm)
            if xs_cd:
                # anchor delta at first interior point using the smoothed delta there
                i0 = x_all.index(xs_cd[0])
                dhat = _reconstruct_delta(xs_cd, slopes_cd, delta_ref=float(d_sm[i0]))
                dtrue = [float(d_sm[x_all.index(x)]) for x in xs_cd]
                mean_abs, max_abs = _residual_norms(dtrue, dhat)
                method = f"CD(w={w})"
                rows.append(
                    " & ".join(
                        [
                            did.replace("_", r"\_"),
                            x_symbol.replace("_", r"\_"),
                            x_unit.replace("_", r"\_"),
                            method.replace("_", r"\_"),
                            str(len(xs_cd)),
                            _fmt(mean_abs, 6),
                            _fmt(max_abs, 6),
                        ]
                    )
                    + r" \\"
                )
                key = (mean_abs, max_abs, did, method)
                if best_overall is None or key < best_overall:
                    best_overall = key

            # Windowed local-linear estimators.
            for k in window_ks:
                xs_w, slopes_w = _window_slopes(pts_sm, k=int(k))
                if not xs_w:
                    continue
                i0 = x_all.index(xs_w[0])
                dhat = _reconstruct_delta(xs_w, slopes_w, delta_ref=float(d_sm[i0]))
                dtrue = [float(d_sm[x_all.index(x)]) for x in xs_w]
                mean_abs, max_abs = _residual_norms(dtrue, dhat)
                method = f"LL(k={k},w={w})"
                rows.append(
                    " & ".join(
                        [
                            did.replace("_", r"\_"),
                            x_symbol.replace("_", r"\_"),
                            x_unit.replace("_", r"\_"),
                            method.replace("_", r"\_"),
                            str(len(xs_w)),
                            _fmt(mean_abs, 6),
                            _fmt(max_abs, 6),
                        ]
                    )
                    + r" \\"
                )
                key = (mean_abs, max_abs, did, method)
                if best_overall is None or key < best_overall:
                    best_overall = key

    write_lines(rows_path, rows if rows else ["% (no rows; datasets too small)"])

    if best_overall is None:
        write_lines(
            sum_path,
            [
                r"\paragraph{Audit summary (inverse consistency: phase$\to$delay$\to$phase).} \AuditTag "
                + r"No usable datasets/rows.",
            ],
        )
        return

    best_mean, best_max, best_did, best_method = best_overall
    write_lines(
        sum_path,
        [
            r"\paragraph{Audit summary (inverse consistency: phase$\to$delay$\to$phase).} \AuditTag "
            + r"We reconstruct $\delta$ by integrating a bounded-family derivative estimator and compare it to the (smoothed) input phase samples on the interior grid. "
            + f"Best (lexicographic) row: dataset {best_did.replace('_', r'\_')}, method {best_method.replace('_', r'\_')}, "
            + rf"mean abs residual {_fmt(best_mean,6)}, max abs residual {_fmt(best_max,6)}.",
        ],
    )

    print("Wrote sections/generated/scattering_inverse_consistency_rows.tex")
    print("Wrote sections/generated/scattering_inverse_consistency_summary.tex")


if __name__ == "__main__":
    main()

