"""
Experiment D: 1/f spectrum from Fibonacci/geometric relaxation ladders.

Pure-Python (no third-party dependencies) reference implementation.

We construct a ladder spectrum
  S(f) = sum_k w * tau_k / (1 + (2*pi*f*tau_k)^2)
with:
  (A) geometric times tau_k = tau0 * r^k
  (B) Fibonacci times  tau_k = tau0 * F_{k+1}

and fit log S vs log f over a mid-band to estimate the slope and R^2.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
import sys


@dataclass(frozen=True)
class Fit:
    slope: float
    intercept: float
    r2: float


def linfit(xs: list[float], ys: list[float]) -> Fit:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx != 0.0 else float("nan")
    intercept = my - slope * mx
    sst = sum((y - my) ** 2 for y in ys)
    sse = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - sse / sst if sst != 0.0 else float("nan")
    return Fit(slope=slope, intercept=intercept, r2=r2)


def fib_times(K: int, tau0: float = 1.0) -> list[float]:
    # Use F_{k+1} with F_0=0,F_1=1.
    f0, f1 = 0, 1
    out: list[float] = []
    for _ in range(K + 1):
        f0, f1 = f1, f0 + f1  # now f0 = F_{k+1}
        out.append(tau0 * float(f0))
    return out


def geometric_times(K: int, r: float, tau0: float = 1.0) -> list[float]:
    return [tau0 * (r ** k) for k in range(K + 1)]


def ladder_spectrum(freqs: list[float], taus: list[float], w: float = 1.0) -> list[float]:
    out: list[float] = []
    for f in freqs:
        omega = 2.0 * math.pi * f
        s = 0.0
        for tau in taus:
            x = omega * tau
            s += w * tau / (1.0 + x * x)
        out.append(s)
    return out


def logspace(f_min: float, f_max: float, n: int) -> list[float]:
    if f_min <= 0.0 or f_max <= 0.0 or f_max <= f_min:
        raise ValueError("Need 0 < f_min < f_max.")
    a = math.log10(f_min)
    b = math.log10(f_max)
    step = (b - a) / (n - 1)
    return [10.0 ** (a + i * step) for i in range(n)]


def fit_band(freqs: list[float], S: list[float], f_lo: float, f_hi: float) -> Fit:
    xs: list[float] = []
    ys: list[float] = []
    for f, s in zip(freqs, S):
        if f_lo <= f <= f_hi and s > 0.0:
            xs.append(math.log(f))
            ys.append(math.log(s))
    if len(xs) < 5:
        raise ValueError("Not enough points in fit band.")
    return linfit(xs, ys)


def main() -> None:
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    tau0 = 1.0
    K = 24  # gives tau_max ~ phi^K or F_{K+1} ~ phi^{K+1}/sqrt(5)
    w = 1.0

    taus_geo = geometric_times(K, r=phi, tau0=tau0)
    taus_fib = fib_times(K, tau0=tau0)

    f_min = 1e-4
    f_max = 1e2
    freqs = logspace(f_min, f_max, 500)

    S_geo = ladder_spectrum(freqs, taus_geo, w=w)
    S_fib = ladder_spectrum(freqs, taus_fib, w=w)

    # Choose a mid-band that satisfies the asymptotic conditions in Proposition app:fibonacci_1f.
    # We enforce omega*tau_min << 1 and omega*tau_max >> 1 with conservative margins.
    tau_min_geo, tau_max_geo = min(taus_geo), max(taus_geo)
    tau_min_fib, tau_max_fib = min(taus_fib), max(taus_fib)
    tau_min = min(tau_min_geo, tau_min_fib)
    tau_max = max(tau_max_geo, tau_max_fib)

    f_lo = 10.0 / (2.0 * math.pi * tau_max)   # omega*tau_max >= 10
    f_hi = 0.1 / (2.0 * math.pi * tau_min)    # omega*tau_min <= 0.1
    fit_geo = fit_band(freqs, S_geo, f_lo=f_lo, f_hi=f_hi)
    fit_fib = fit_band(freqs, S_fib, f_lo=f_lo, f_hi=f_hi)

    print("1/f ladder spectrum fit (log-log): log S = slope * log f + intercept")
    print(f"Fit band: f in [{f_lo}, {f_hi}]")
    print(f"Geometric r=phi: slope={fit_geo.slope:.4f}, R^2={fit_geo.r2:.6f}")
    print(f"Fibonacci:       slope={fit_fib.slope:.4f}, R^2={fit_fib.r2:.6f}")

    # Theoretical slope is -1, and the prefactor for the continuous-log approximation is ~ w/(4 ln r).
    pref = w / (4.0 * math.log(phi))
    print(f"Theory (continuous log-uniform, r=phi): slope=-1, prefactor~={pref:.6f} (units of S*f)")

    if "--latex" in sys.argv[1:]:
        print("% LaTeX table rows: model & K & fit-band & slope & R^2")
        band = f"[{f_lo:.3e},{f_hi:.3e}]"
        print(f"Geometric ($r=\\varphi$) & {K} & {band} & {fit_geo.slope:.6f} & {fit_geo.r2:.6f} \\\\")
        print(f"Fibonacci ($\\tau_k\\propto F_k$) & {K} & {band} & {fit_fib.slope:.6f} & {fit_fib.r2:.6f} \\\\")


if __name__ == "__main__":
    main()


