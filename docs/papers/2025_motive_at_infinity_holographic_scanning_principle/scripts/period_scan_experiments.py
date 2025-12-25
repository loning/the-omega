#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Reproducible scan-period experiments for:
  - log(2) via 1D Kronecker scan
  - pi via 1D Kronecker scan
  - zeta(2) via 2D scan with truncated geometric kernel
  - zeta(3) via 3D scan with truncated geometric kernel

This script writes LaTeX table row files into:
  sections/generated/

No third-party dependencies.
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Callable, List, Sequence, Tuple


PHI = (1.0 + 5.0 ** 0.5) / 2.0
ALPHA_GOLDEN = 1.0 / PHI
ALPHA2 = math.sqrt(2.0) - 1.0
ALPHA3 = math.sqrt(3.0) - 1.0


def frac_part(x: float) -> float:
    """Fractional part for nonnegative floats."""
    return x - int(x)


def geom_trunc(p: float, m: int) -> float:
    """Truncated geometric sum_{n=0}^{m-1} p^n in closed form, stable near p=1."""
    if m <= 0:
        return 0.0
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        # p is a product of points in [0,1); this branch is defensive.
        return float(m)
    if abs(1.0 - p) < 1e-12:
        return float(m)
    return (1.0 - (p ** m)) / (1.0 - p)


def birkhoff_1d(alpha: float, n: int, f: Callable[[float], float], x0: float = 0.123456789) -> float:
    """Birkhoff average on [0,1) under x <- x + alpha mod 1."""
    x = frac_part(x0)
    s = 0.0
    for _ in range(n):
        s += f(x)
        x += alpha
        x -= int(x)
    return s / float(n)


def birkhoff_geom_2d(alpha: Sequence[float], n: int, m: int, x0: Sequence[float]) -> float:
    """2D Kronecker scan with truncated geometric kernel g_m(x,y)=sum_{k=0}^{m-1}(xy)^k."""
    x = frac_part(x0[0])
    y = frac_part(x0[1])
    a0, a1 = float(alpha[0]), float(alpha[1])
    s = 0.0
    for _ in range(n):
        p = x * y
        s += geom_trunc(p, m)
        x += a0
        x -= int(x)
        y += a1
        y -= int(y)
    return s / float(n)


def birkhoff_geom_3d(alpha: Sequence[float], n: int, m: int, x0: Sequence[float]) -> float:
    """3D Kronecker scan with truncated geometric kernel g_m(x,y,z)=sum_{k=0}^{m-1}(xyz)^k."""
    x = frac_part(x0[0])
    y = frac_part(x0[1])
    z = frac_part(x0[2])
    a0, a1, a2 = float(alpha[0]), float(alpha[1]), float(alpha[2])
    s = 0.0
    for _ in range(n):
        p = x * y * z
        s += geom_trunc(p, m)
        x += a0
        x -= int(x)
        y += a1
        y -= int(y)
        z += a2
        z -= int(z)
    return s / float(n)


def ensemble_mean_geom(alpha: Sequence[float], n: int, m: int, k: int, seed: int) -> float:
    """Mean over k random initial conditions, deterministic via seed."""
    rng = random.Random(seed)
    d = len(alpha)
    vals: List[float] = []
    for _ in range(k):
        x0 = [rng.random() for _ in range(d)]
        if d == 2:
            vals.append(birkhoff_geom_2d(alpha, n, m, x0))
        elif d == 3:
            vals.append(birkhoff_geom_3d(alpha, n, m, x0))
        else:
            raise ValueError("Only d=2 or d=3 supported in ensemble_mean_geom.")
    return sum(vals) / float(k)


def harmonic_2(m: int) -> float:
    """H_m^{(2)} = sum_{n=1}^m 1/n^2."""
    s = 0.0
    for n in range(1, m + 1):
        s += 1.0 / (n * n)
    return s


def harmonic_3(m: int) -> float:
    """H_m^{(3)} = sum_{n=1}^m 1/n^3."""
    s = 0.0
    for n in range(1, m + 1):
        s += 1.0 / (n * n * n)
    return s


def fmt_sci_signed(x: float, sig: int = 3) -> str:
    """LaTeX scientific notation with explicit sign: $+a\\times 10^{b}$."""
    if x == 0.0:
        return "$+0$"
    sign = "+" if x > 0 else "-"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = ax / (10.0 ** exp)
    # Round mantissa to sig digits; renormalize if needed.
    mant = round(mant, max(sig - 1, 0))
    if mant >= 10.0:
        mant /= 10.0
        exp += 1
    # Format mantissa: keep up to sig significant digits without trailing zeros explosion.
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


def write_rows(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines).rstrip() + "\n"
    path.write_text(content, encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    gen = root / "sections" / "generated"

    # Experiment I: log2
    def f_log2(x: float) -> float:
        return 1.0 / (1.0 + x)

    log2_target = math.log(2.0)
    log2_rows: List[str] = []
    for n in (10_000, 50_000, 200_000):
        est = birkhoff_1d(ALPHA_GOLDEN, n, f_log2)
        err = est - log2_target
        log2_rows.append(f"{n:,} & {est:.12f} & {fmt_sci_signed(err)} \\\\")
    write_rows(gen / "log2_rows.tex", log2_rows)

    # Experiment II: pi
    def f_pi(x: float) -> float:
        return 4.0 / (1.0 + x * x)

    pi_target = math.pi
    pi_rows: List[str] = []
    for n in (10_000, 50_000, 200_000):
        est = birkhoff_1d(ALPHA_GOLDEN, n, f_pi)
        err = est - pi_target
        pi_rows.append(f"{n:,} & {est:.12f} & {fmt_sci_signed(err)} \\\\")
    write_rows(gen / "pi_rows.tex", pi_rows)

    # Experiment III: zeta(2) via truncation
    zeta2 = (math.pi * math.pi) / 6.0
    alpha_2d = (ALPHA_GOLDEN, ALPHA2)
    zeta2_cases: List[Tuple[int, int, int]] = [
        (200_000, 5_000, 10),
        (1_000_000, 5_000, 10),
        (2_000_000, 20_000, 20),
    ]
    zeta2_rows: List[str] = []
    for n, m, k in zeta2_cases:
        mean = ensemble_mean_geom(alpha_2d, n, m, k, seed=123)
        hm2 = harmonic_2(m)
        delta_zeta = mean - zeta2
        sampling_err = mean - hm2
        trunc_bound = 1.0 / float(m)
        zeta2_rows.append(
            f"({n:,},{m:,},{k}) & {mean:.12f} & {fmt_sci_signed(delta_zeta)} & {fmt_sci_signed(sampling_err)} & {fmt_sci_unsigned(trunc_bound)} \\\\"
        )
    write_rows(gen / "zeta2_rows.tex", zeta2_rows)

    # Experiment IV: zeta(3) via truncation
    alpha_3d = (ALPHA_GOLDEN, ALPHA2, ALPHA3)
    zeta3_cases: List[Tuple[int, int, int]] = [
        (200_000, 2_000, 10),
        (1_000_000, 2_000, 10),
    ]
    # Reference zeta(3) by a high-M harmonic sum with certified remainder bound:
    m_ref = 200_000
    h_ref = harmonic_3(m_ref)
    rem_bound = 1.0 / (2.0 * float(m_ref) * float(m_ref))
    # Use the midpoint of the certified interval [H_m, H_m + bound].
    zeta3_ref = h_ref + 0.5 * rem_bound

    zeta3_rows: List[str] = []
    for n, m, k in zeta3_cases:
        mean = ensemble_mean_geom(alpha_3d, n, m, k, seed=123)
        hm3 = harmonic_3(m)
        delta_zeta = mean - zeta3_ref
        sampling_err = mean - hm3
        trunc_bound = 1.0 / (2.0 * float(m) * float(m))
        zeta3_rows.append(
            f"({n:,},{m:,},{k}) & {mean:.12f} & {fmt_sci_signed(delta_zeta)} & {fmt_sci_signed(sampling_err)} & {fmt_sci_unsigned(trunc_bound)} \\\\"
        )
    write_rows(gen / "zeta3_rows.tex", zeta3_rows)

    print(f"Wrote LaTeX rows into: {gen}")
    print("Files: log2_rows.tex, pi_rows.tex, zeta2_rows.tex, zeta3_rows.tex")
    print(f"zeta(3) reference: zeta3_ref = {zeta3_ref:.15f} (certified half-width <= {0.5*rem_bound:.3e})")


if __name__ == "__main__":
    main()


