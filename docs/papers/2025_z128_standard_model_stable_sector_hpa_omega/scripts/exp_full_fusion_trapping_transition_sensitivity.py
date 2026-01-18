# -*- coding: utf-8 -*-
"""
Deterministic sensitivity sweep for the trapping-transition changepoint.

We rerun the metrics-only scan and two-segment changepoint fit across a small family of
budget settings (I_obs, c) while keeping the rest of the full-fusion contract fixed.

Outputs (LaTeX fragments):
  - sections/generated/full_fusion_trapping_transition_sensitivity_rows.tex
  - sections/generated/full_fusion_trapping_transition_sensitivity_summary.tex

Design:
  - deterministic, small finite family
  - uses only python stdlib for analysis; relies on the existing full-fusion script for data
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines


def _fmt(x: float, nd: int = 6) -> str:
    return f"{float(x):.{int(nd)}f}"


def _ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b


@dataclass(frozen=True)
class Pt:
    f: float
    y: float


def _fit_line(xs: List[float], ys: List[float]) -> Tuple[float, float, float]:
    n = len(xs)
    if n <= 1:
        a = ys[0] if ys else 0.0
        return float(a), 0.0, 0.0
    mx = sum(xs) / float(n)
    my = sum(ys) / float(n)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0.0:
        a = my
        b = 0.0
    else:
        sxy = sum((x - mx) * (y - my) for (x, y) in zip(xs, ys))
        b = sxy / sxx
        a = my - b * mx
    sse = sum((y - (a + b * x)) ** 2 for (x, y) in zip(xs, ys))
    return float(a), float(b), float(sse)


def _run_metrics_point(*, n: int, m_window: int, i_obs: int, c: int, steps: int) -> dict:
    env = dict(os.environ)
    env["FULL_FUSION_MODE"] = "metrics"
    env["FULL_FUSION_N"] = str(n)
    env["FULL_FUSION_M_WINDOW"] = str(m_window)
    env["FULL_FUSION_I_OBS"] = str(i_obs)
    env["FULL_FUSION_MARGIN_C"] = str(c)
    env["FULL_FUSION_STEPS"] = str(steps)
    env["FULL_FUSION_SAMPLE_EVERY"] = str(steps)
    paper_root = str(generated_dir().parent.parent)
    out = subprocess.check_output(
        ["python3", "scripts/exp_full_fusion_bh_wormhole_measurement.py"],
        cwd=paper_root,
        env=env,
        text=True,
    )
    return json.loads(out.strip())


def _scan_pts(*, n: int, i_obs: int, c: int) -> List[Pt]:
    # Same m-grid as the earlier scan (kept small and auditable).
    ms = [4, 6, 8, 10, 12, 16]
    steps = int(os.environ.get("FULL_FUSION_SENS_STEPS", "1200"))
    if steps <= 0:
        raise ValueError("FULL_FUSION_SENS_STEPS must be positive")
    pts: List[Pt] = []
    for m in ms:
        p = _run_metrics_point(n=n, m_window=m, i_obs=i_obs, c=c, steps=steps)
        f = float(p["horizon_frac_on"])
        dtau = float(p["delay_trap_on"]) - float(p["delay_free_on"])
        pts.append(Pt(f=f, y=dtau))
    pts.sort(key=lambda t: (t.f, t.y))
    return pts


def _changepoint(pts: List[Pt]) -> Tuple[float, float, float, float, float]:
    """
    Returns: (f_star, b1, b2, r2, sse)
    """
    xs = [p.f for p in pts]
    ys = [p.y for p in pts]
    if len(xs) < 6:
        raise ValueError("Need >=6 points for a stable 2-segment fit.")
    k = 3
    best = None
    for idx in range(k, len(xs) - k + 1):
        a1, b1, sse1 = _fit_line(xs[:idx], ys[:idx])
        a2, b2, sse2 = _fit_line(xs[idx:], ys[idx:])
        sse = sse1 + sse2
        cand = (sse, idx, b1, b2)
        if best is None or cand[0] < best[0] - 1e-15 or (abs(cand[0] - best[0]) <= 1e-15 and cand[1] < best[1]):
            best = cand
    assert best is not None
    sse, idx, b1, b2 = best
    f_star = 0.5 * (xs[idx - 1] + xs[idx])
    ybar = sum(ys) / float(len(ys))
    sst = sum((y - ybar) ** 2 for y in ys)
    r2 = 1.0 - (sse / sst) if sst > 0.0 else 0.0
    return float(f_star), float(b1), float(b2), float(r2), float(sse)


def main() -> None:
    n = 6
    i_obs_list = [64, 1024, 1_000_000]
    c_list = [8, 16, 32]

    rows: List[str] = []
    fstars: List[float] = []
    fstars_nondegenerate: List[float] = []

    total_cases = len(i_obs_list) * len(c_list)
    done_cases = 0
    t0 = time.time()
    last_print = 0.0
    for i_obs in i_obs_list:
        for c in c_list:
            done_cases += 1
            # Progress line (at least once per case, and at least once per minute).
            now = time.time()
            if done_cases == 1 or (now - last_print) >= 60.0:
                elapsed = now - t0
                print(
                    f"[sensitivity] case {done_cases}/{total_cases}: "
                    f"I_obs={i_obs}, c={c} (elapsed {elapsed:.1f}s)"
                )
                last_print = now

            pts = _scan_pts(n=n, i_obs=i_obs, c=c)
            fs = [p.f for p in pts]
            fmin_case = min(fs)
            fmax_case = max(fs)
            f_span = fmax_case - fmin_case
            degenerate = "yes" if f_span < 1e-9 else "no"
            f_star, b1, b2, r2, sse = _changepoint(pts)
            fstars.append(f_star)
            if degenerate == "no":
                fstars_nondegenerate.append(f_star)

            # Also record the deterministic saturation boundary for reference:
            # f_sat = min( ceil(c*I_obs/m_min), 4^n ) / 4^n at the smallest m in the scan grid (m=4).
            total = 4 ** n
            req = _ceil_div(c * i_obs, 4)
            f_sat = float(min(req, total)) / float(total)

            rows.append(
                " & ".join(
                    [
                        str(n),
                        str(i_obs),
                        str(c),
                        _fmt(f_sat, 6),
                        _fmt(fmin_case, 6),
                        _fmt(fmax_case, 6),
                        degenerate,
                        _fmt(f_star, 6),
                        _fmt(b2 - b1, 6),
                        _fmt(r2, 6),
                    ]
                )
                + r" \\"
            )

    rows.append(r"\bottomrule")
    write_lines(generated_dir() / "full_fusion_trapping_transition_sensitivity_rows.tex", rows)

    fmin = min(fstars) if fstars else float("nan")
    fmax = max(fstars) if fstars else float("nan")
    fmin_nd = min(fstars_nondegenerate) if fstars_nondegenerate else float("nan")
    fmax_nd = max(fstars_nondegenerate) if fstars_nondegenerate else float("nan")
    summary = (
        r"\paragraph{Audit summary (changepoint sensitivity sweep).} \AuditTag "
        r"We rerun the metrics-only trapping-transition scan over a small finite family of $(I_{\mathrm{obs}},c)$ "
        r"settings and recompute the two-segment least-squares changepoint estimate $f_{\mathrm{hor}}^\star$. "
        + rf"Across the full tested family (including occupancy-degenerate cases), $f_{{\mathrm{{hor}}}}^\star$ ranges from {_fmt(fmin,6)} to {_fmt(fmax,6)}. "
        + rf"Restricting to nondegenerate cases where the scan produces a nontrivial occupancy span, "
        + rf"$f_{{\mathrm{{hor}}}}^\star$ ranges from {_fmt(fmin_nd,6)} to {_fmt(fmax_nd,6)}. "
        r"Rows are generated deterministically by \texttt{scripts/exp\_full\_fusion\_trapping\_transition\_sensitivity.py}."
    )
    write_lines(generated_dir() / "full_fusion_trapping_transition_sensitivity_summary.tex", [summary])
    print("Wrote sections/generated/full_fusion_trapping_transition_sensitivity_rows.tex")
    print("Wrote sections/generated/full_fusion_trapping_transition_sensitivity_summary.tex")


if __name__ == "__main__":
    main()

