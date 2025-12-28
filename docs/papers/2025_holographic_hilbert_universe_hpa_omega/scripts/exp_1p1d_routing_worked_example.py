# -*- coding: utf-8 -*-
"""
1+1D worked example: weighted scan-chain compilation and weak-field lapse matching.

We specify:
  - a 1D screen lattice Sigma_n = {0..L-1}, L = 2^n,
  - a weighted path hardware graph with edge weights w_{i+1/2} (tick costs),
  - a local clock task at site i that executes a fixed two-body primitive on
    edges (i-1,i) and (i,i+1) sequentially (shared vertex constraint).

Then the exact compilation depth for interior sites is:
  kappa(i) = w_{i-1/2} + w_{i+1/2}
and the induced lapse is:
  N(i) = kappa0 / kappa(i).

We choose the edge weights by midpoint sampling so that N(i) matches a standard
weak-field target along a radial line: the Schwarzschild lapse
  N_Schw(r) = sqrt(1 - 2M/r)  (units c=G=1),
and we report finite-size errors and a log-log scaling fit.

This script writes LaTeX table rows into:
  sections/generated/1p1d_error_rows.tex
  sections/generated/1p1d_scaling_fit_rows.tex
  sections/generated/1p1d_curve_rows.tex
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path


def schw_lapse(r: float, *, M: float) -> float:
    if r <= 2.0 * M:
        raise ValueError("Need r > 2M for a real Schwarzschild lapse.")
    return math.sqrt(1.0 - (2.0 * M) / r)


@dataclass(frozen=True)
class Metrics:
    n: int
    L: int
    h: float
    max_abs: float
    rms: float
    rel_rms: float


def _round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def build_profile(
    *,
    n: int,
    r_min: float,
    r_max: float,
    M: float,
    kappa0: int,
) -> tuple[list[float], list[float], list[int], list[int | None], list[float | None]]:
    """
    Returns:
      r_sites: r_i at sites
      N_target: N_Schw(r_i)
      w_edges: w_{i+1/2} for i=0..L-2 (edge weights, integers)
      kappa_sites: kappa(i) for i=0..L-1 (None at endpoints)
      N_meas: induced N(i)=kappa0/kappa(i) (None at endpoints)
    """
    L = 1 << n
    if L < 4:
        raise ValueError("Need L >= 4 to have interior sites.")
    if r_max <= r_min:
        raise ValueError("Need r_max > r_min.")

    h = (r_max - r_min) / float(L - 1)
    r_sites = [r_min + i * h for i in range(L)]
    N_target = [schw_lapse(r, M=M) for r in r_sites]

    # Midpoint construction of edge weights:
    #   w_{i+1/2} ~ (1/2) * kappa_target(r_{i+1/2}), rounded to integer ticks.
    w_edges: list[int] = []
    for i in range(L - 1):
        r_mid = r_sites[i] + 0.5 * h
        N_mid = schw_lapse(r_mid, M=M)
        kappa_mid = float(kappa0) / N_mid
        w_edges.append(_round_half_up(0.5 * kappa_mid))

    # Exact compilation depth for the 2-edge local task on interior sites.
    kappa_sites: list[int | None] = [None for _ in range(L)]
    N_meas: list[float | None] = [None for _ in range(L)]
    for i in range(1, L - 1):
        k = w_edges[i - 1] + w_edges[i]
        kappa_sites[i] = k
        N_meas[i] = float(kappa0) / float(k)

    return r_sites, N_target, w_edges, kappa_sites, N_meas


def metrics_for_n(
    *,
    n: int,
    r_min: float,
    r_max: float,
    M: float,
    kappa0: int,
) -> Metrics:
    r_sites, N_target, _w_edges, _kappa_sites, N_meas = build_profile(
        n=n, r_min=r_min, r_max=r_max, M=M, kappa0=kappa0
    )
    L = len(r_sites)
    h = (r_max - r_min) / float(L - 1)

    errs: list[float] = []
    rel_errs: list[float] = []
    for i in range(1, L - 1):
        if N_meas[i] is None:
            continue
        e = abs(N_meas[i] - N_target[i])
        errs.append(e)
        rel_errs.append(e / N_target[i])

    if not errs:
        raise ValueError("No interior errors computed.")

    max_abs = max(errs)
    rms = math.sqrt(sum(e * e for e in errs) / float(len(errs)))
    rel_rms = math.sqrt(sum(e * e for e in rel_errs) / float(len(rel_errs)))
    return Metrics(n=n, L=L, h=h, max_abs=max_abs, rms=rms, rel_rms=rel_rms)


def linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """
    Ordinary least squares fit for y = a + b x.
    Returns (b, a, R^2).
    """
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("Need at least 2 points for a fit.")
    n = float(len(xs))
    x_bar = sum(xs) / n
    y_bar = sum(ys) / n
    sxx = sum((x - x_bar) ** 2 for x in xs)
    if sxx == 0.0:
        raise ValueError("Degenerate x values.")
    sxy = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = y_bar - b * x_bar
    ss_tot = sum((y - y_bar) ** 2 for y in ys)
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - (ss_res / ss_tot if ss_tot != 0.0 else 0.0)
    return b, a, r2


def write_rows(lines: list[str], filename: str) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    # Weak-field target parameters (units c=G=1).
    M = 0.05
    r_min = 1.0
    r_max = 8.0

    # Tick calibration: larger kappa0 reduces integer-quantization effects.
    kappa0 = 1_000_000_000

    # Finite-size scan (orders).
    n_min = 6
    n_max = 11

    # Representative curve sample order.
    n_curve = 9
    curve_points = 12

    metrics: list[Metrics] = []
    for n in range(n_min, n_max + 1):
        m = metrics_for_n(n=n, r_min=r_min, r_max=r_max, M=M, kappa0=kappa0)
        metrics.append(m)
        print(
            f"n={m.n:2d}  L={m.L:4d}  h={m.h:.6g}  max|dN|={m.max_abs:.3e}  rms|dN|={m.rms:.3e}  rel_rms={m.rel_rms:.3e}"
        )

    # LaTeX rows: errors per n.
    error_rows: list[str] = []
    for m in metrics:
        error_rows.append(
            f"{m.n} & {m.L} & {m.h:.6g} & {m.max_abs:.3e} & {m.rms:.3e} & {m.rel_rms:.3e} \\\\"
        )
    write_rows(error_rows, "1p1d_error_rows.tex")

    # Scaling fit: log(rms) vs log(h) (expect slope ~ 2 from midpoint averaging).
    xs = [math.log(mm.h) for mm in metrics]
    ys = [math.log(mm.rms) for mm in metrics]
    slope, _a, r2 = linear_fit(xs, ys)
    fit_rows = [f"{n_min}--{n_max} & {slope:.4f} & {r2:.5f} \\\\"]
    write_rows(fit_rows, "1p1d_scaling_fit_rows.tex")
    print(f"fit: log(rms) ~ a + b log(h),  b={slope:.4f}, R^2={r2:.5f}")

    # Representative curve samples.
    r_sites, N_target, _w_edges, _kappa_sites, N_meas = build_profile(
        n=n_curve, r_min=r_min, r_max=r_max, M=M, kappa0=kappa0
    )
    L = len(r_sites)
    idxs = [
        int(round(1 + (L - 3) * k / float(curve_points - 1))) for k in range(curve_points)
    ]
    idxs = [min(max(i, 1), L - 2) for i in idxs]
    idxs = sorted(set(idxs))

    curve_rows: list[str] = []
    for i in idxs:
        Nm = float(N_meas[i]) if N_meas[i] is not None else float("nan")
        Nt = float(N_target[i])
        dn = Nm - Nt
        curve_rows.append(f"{r_sites[i]:.6g} & {Nt:.10f} & {Nm:.10f} & {dn:.3e} \\\\")
    write_rows(curve_rows, "1p1d_curve_rows.tex")

    print("Wrote sections/generated/1p1d_error_rows.tex")
    print("Wrote sections/generated/1p1d_scaling_fit_rows.tex")
    print("Wrote sections/generated/1p1d_curve_rows.tex")


if __name__ == "__main__":
    main()


