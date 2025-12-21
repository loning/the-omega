"""
Experiment C: least-squares fits for mismatch-growth templates.

Pure-Python (no third-party dependencies) reference implementation.

We fit:
  (i) irrationals:  E_N = a * log N + b
 (ii) rationals:   E_N = c * N + d

The script prints fitted coefficients and R^2, and can emit a LaTeX table.

Usage:
  python3 scripts/experiment_c_fit_tables.py
  python3 scripts/experiment_c_fit_tables.py --latex
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass


def rotation_points(alpha: float, N: int, x0: float = 0.0) -> list[float]:
    pts: list[float] = []
    a = float(alpha)
    for n in range(1, N + 1):
        x = x0 + n * a
        pts.append(x - math.floor(x))
    return pts


def star_discrepancy(points: list[float]) -> float:
    x = sorted(points)
    N = len(x)
    invN = 1.0 / float(N)

    d1 = 0.0
    d2 = 0.0
    for idx, xi in enumerate(x, start=1):
        i_over_N = idx * invN
        im1_over_N = (idx - 1) * invN
        d1 = max(d1, abs(i_over_N - xi))
        d2 = max(d2, abs(xi - im1_over_N))
    return max(d1, d2)


def accumulated_mismatch(alpha: float, N: int, x0: float = 0.0) -> float:
    pts = rotation_points(alpha, N, x0=x0)
    D = star_discrepancy(pts)
    return float(N) * D


@dataclass(frozen=True)
class Fit:
    a: float
    b: float
    r2: float


def linear_regression(x: list[float], y: list[float]) -> Fit:
    n = len(x)
    if n != len(y) or n < 2:
        raise ValueError("Need at least two data points with matched lengths.")

    sx = sum(x)
    sy = sum(y)
    sxx = sum(v * v for v in x)
    sxy = sum(xi * yi for xi, yi in zip(x, y))

    denom = n * sxx - sx * sx
    if denom == 0.0:
        raise ValueError("Degenerate x values (cannot fit).")

    a = (n * sxy - sx * sy) / denom
    b = (sy - a * sx) / n

    y_mean = sy / n
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    ss_res = sum((yi - (a * xi + b)) ** 2 for xi, yi in zip(x, y))
    r2 = 1.0 - (ss_res / ss_tot if ss_tot != 0.0 else 0.0)

    return Fit(a=a, b=b, r2=r2)


def as_latex_row(label: str, model: str, fit: Fit) -> str:
    return (
        f"{label} & {model} & {fit.a:.6f} & {fit.b:.6f} & {fit.r2:.6f} \\\\"
    )


def running_max(values: list[float]) -> list[float]:
    out: list[float] = []
    m = -float("inf")
    for v in values:
        if v > m:
            m = v
        out.append(m)
    return out


def main() -> None:
    alpha_golden = (math.sqrt(5.0) - 1.0) / 2.0
    alpha_sqrt2 = math.sqrt(2.0) - 1.0
    alpha_rational = 1.0 / 2.0

    Ns = [100, 300, 1_000, 3_000, 10_000, 30_000, 100_000]
    x0 = 0.123456789

    def series(alpha: float) -> list[float]:
        return [accumulated_mismatch(alpha, N, x0=x0) for N in Ns]

    Eg = series(alpha_golden)
    Es = series(alpha_sqrt2)
    Er = series(alpha_rational)

    x_log = [math.log(float(N)) for N in Ns]
    x_lin = [float(N) for N in Ns]

    Eg_env = running_max(Eg)
    Es_env = running_max(Es)

    fit_g = linear_regression(x_log, Eg_env)
    fit_s = linear_regression(x_log, Es_env)
    fit_r = linear_regression(x_lin, Er)

    print("Fit templates:")
    print("  irrationals: E_N = a * log N + b")
    print("  rationals:   E_N = c * N + d\n")

    print(f"Initial phase x0 = {x0}")
    print(f"N samples = {Ns}\n")

    print("Golden branch (envelope fit):")
    print(f"  a={fit_g.a:.6f}, b={fit_g.b:.6f}, R^2={fit_g.r2:.6f}")
    print("sqrt(2)-1 (envelope fit):")
    print(f"  a={fit_s.a:.6f}, b={fit_s.b:.6f}, R^2={fit_s.r2:.6f}")
    print("Rational 1/2:")
    print(f"  c={fit_r.a:.6f}, d={fit_r.b:.6f}, R^2={fit_r.r2:.6f}\n")

    want_latex = "--latex" in sys.argv[1:]
    if want_latex:
        print("% LaTeX table rows (a,b,R^2):")
        print(as_latex_row(r"$\\alpha=\\varphi^{-1}$", r"$E_N^{\\uparrow}=a\\log N+b$", fit_g))
        print(as_latex_row(r"$\\alpha=\\sqrt{2}-1$", r"$E_N^{\\uparrow}=a\\log N+b$", fit_s))
        print(as_latex_row(r"$\\alpha=1/2$", r"$E_N=cN+d$", fit_r))


if __name__ == "__main__":
    main()


