#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experiment 1 (1D): Kronecker scan realizations of log(2) and pi, with auditable
Koksma certificates based on exact 1D star discrepancy.

This script writes LaTeX table row files into:
  sections/generated/log2_rows.tex
  sections/generated/pi_rows.tex

No third-party dependencies.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, List, Sequence, Tuple


def frac_part(x: float) -> float:
    return x - int(x)


def kronecker_scan_avg_1d_with_points(
    f: Callable[[float], float], n: int, alpha: float, x0: float = 0.123456789
) -> Tuple[float, List[float]]:
    x = frac_part(x0)
    s = 0.0
    pts: List[float] = []
    for _ in range(n):
        pts.append(x)
        s += f(x)
        x += alpha
        x -= int(x)
    return s / float(n), pts


def star_discrepancy_1d(points: Sequence[float]) -> float:
    """
    Exact 1D star discrepancy:
      D_N^* = sup_{u in [0,1]} | (1/N) #{x_i < u} - u |
    computed from sorted points.
    """
    n = len(points)
    if n <= 0:
        return 0.0
    xs = sorted(points)
    inv_n = 1.0 / float(n)
    d_plus = 0.0
    d_minus = 0.0
    for i, x in enumerate(xs):
        a = (float(i + 1) * inv_n) - x
        b = x - (float(i) * inv_n)
        if a > d_plus:
            d_plus = a
        if b > d_minus:
            d_minus = b
    return max(d_plus, d_minus)


def fmt_sci_signed(x: float, sig: int = 3) -> str:
    """LaTeX scientific notation with explicit sign: $+a\\times 10^{b}$."""
    if x == 0.0:
        return "$+0$"
    sign = "+" if x > 0 else "-"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = ax / (10.0 ** exp)
    mant = round(mant, max(sig - 1, 0))
    if mant >= 10.0:
        mant /= 10.0
        exp += 1
    mant_str = f"{mant:.{max(sig - 1, 0)}f}".rstrip("0").rstrip(".")
    return f"${sign}{mant_str}\\times 10^{{{exp}}}$"


def fmt_sci_unsigned(x: float, sig: int = 2) -> str:
    """LaTeX scientific notation without sign, for positive bounds."""
    if x <= 0.0:
        return "$0$"
    exp = int(math.floor(math.log10(x)))
    mant = x / (10.0 ** exp)
    mant = round(mant, max(sig - 1, 0))
    if mant >= 10.0:
        mant /= 10.0
        exp += 1
    mant_str = f"{mant:.{max(sig - 1, 0)}f}".rstrip("0").rstrip(".")
    return f"${mant_str}\\times 10^{{{exp}}}$"


def loglog_slope(ns: Sequence[int], errs: Sequence[float]) -> float:
    """Least-squares slope of log(|err|) vs log(N)."""
    xs: List[float] = []
    ys: List[float] = []
    for n, e in zip(ns, errs):
        ae = abs(e)
        if n <= 0 or ae <= 0.0:
            continue
        xs.append(math.log(float(n)))
        ys.append(math.log(ae))
    if len(xs) < 2:
        return float("nan")
    mx = sum(xs) / float(len(xs))
    my = sum(ys) / float(len(ys))
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    return num / den if den > 0.0 else float("nan")


def write_rows(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = list(lines)
    if out:
        last = out[-1].rstrip()
        if last.endswith("\\\\"):
            last = last[:-2].rstrip()
        out[-1] = last
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    gen = root / "sections" / "generated"

    phi = (1.0 + math.sqrt(5.0)) / 2.0
    alpha = phi - 1.0  # golden branch slope

    # Kernels and exact values
    f_log2 = lambda x: 1.0 / (1.0 + x)  # Integral_0^1 dx/(1+x) = log 2
    f_pi = lambda x: 4.0 / (1.0 + x * x)  # Integral_0^1 4/(1+x^2) dx = pi

    log2_target = math.log(2.0)
    pi_target = math.pi

    # Total variations on [0,1]
    var_log2 = 0.5
    var_pi = 2.0

    ns = (10_000, 50_000, 200_000)

    log2_rows: List[str] = []
    log2_ns: List[int] = []
    log2_errs: List[float] = []
    for n in ns:
        est, pts = kronecker_scan_avg_1d_with_points(f_log2, n, alpha)
        dstar = star_discrepancy_1d(pts)
        err = est - log2_target
        bound = var_log2 * dstar
        ratio = abs(err) / bound if bound > 0.0 else 0.0
        log2_ns.append(n)
        log2_errs.append(err)
        log2_rows.append(
            f"{n:,} & {est:.12f} & {fmt_sci_signed(err)} & {fmt_sci_unsigned(dstar)} & {fmt_sci_unsigned(bound)} & {fmt_sci_unsigned(ratio)} \\\\"
        )
    write_rows(gen / "log2_rows.tex", log2_rows)
    write_rows(gen / "log2_fit.tex", [f"{loglog_slope(log2_ns, log2_errs):.3f}"])

    pi_rows: List[str] = []
    pi_ns: List[int] = []
    pi_errs: List[float] = []
    for n in ns:
        est, pts = kronecker_scan_avg_1d_with_points(f_pi, n, alpha)
        dstar = star_discrepancy_1d(pts)
        err = est - pi_target
        bound = var_pi * dstar
        ratio = abs(err) / bound if bound > 0.0 else 0.0
        pi_ns.append(n)
        pi_errs.append(err)
        pi_rows.append(
            f"{n:,} & {est:.12f} & {fmt_sci_signed(err)} & {fmt_sci_unsigned(dstar)} & {fmt_sci_unsigned(bound)} & {fmt_sci_unsigned(ratio)} \\\\"
        )
    write_rows(gen / "pi_rows.tex", pi_rows)
    write_rows(gen / "pi_fit.tex", [f"{loglog_slope(pi_ns, pi_errs):.3f}"])

    print(f"Wrote LaTeX rows into: {gen}")
    print("Files: log2_rows.tex, log2_fit.tex, pi_rows.tex, pi_fit.tex")


if __name__ == "__main__":
    main()


