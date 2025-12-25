#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experiment 2 (d=2,3): truncated geometric kernels g_M and zeta-values, with
auditable truncation bounds and explicit multi-dimensional discrepancy
certificates via an ETK bracket term for Kronecker sequences.

This script writes LaTeX table row files into:
  sections/generated/zeta2_rows.tex
  sections/generated/zeta3_rows.tex

No third-party dependencies.
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


PHI = (1.0 + 5.0**0.5) / 2.0
ALPHA_GOLDEN = 1.0 / PHI
ALPHA2 = math.sqrt(2.0) - 1.0
ALPHA3 = math.sqrt(3.0) - 1.0
U_ROUNDOFF = 2.0**-53  # IEEE-754 binary64 unit roundoff (roughly 1.11e-16)


def frac_part(x: float) -> float:
    return x - int(x)


def geom_trunc(p: float, m: int) -> float:
    """Truncated geometric sum_{n=0}^{m-1} p^n in closed form, stable near p=1."""
    if m <= 0:
        return 0.0
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return float(m)
    if abs(1.0 - p) < 1e-12:
        return float(m)
    return (1.0 - (p**m)) / (1.0 - p)


def dist_to_nearest_int_lower_bound(theta_hat: float, sum_abs: float, d: int) -> float:
    """
    A conservative lower bound on dist_Z(theta) for the exact dot product theta,
    given a computed IEEE-754 float theta_hat and sum_abs = sum_j |h_j| |alpha_j|.

    Error model (standard): a length-d dot product in binary64 has absolute error
      |theta_hat - theta| <= gamma_{2d} * sum_abs,
    with gamma_k = k*u/(1-k*u).  We subtract this bound to obtain a lower bound on dist_Z.
    See, e.g., Higham (2002), Accuracy and Stability of Numerical Algorithms.
    """
    if d <= 0:
        return 0.0
    if sum_abs <= 0.0:
        # theta is exactly 0 in this case.
        return 0.0
    k = float(2 * d)
    gamma_k = (k * U_ROUNDOFF) / (1.0 - k * U_ROUNDOFF)
    err = gamma_k * float(sum_abs)
    dist_hat = abs(theta_hat - round(theta_hat))
    dist_low = dist_hat - err
    return dist_low if dist_low > 0.0 else 0.0


def etk_constant(d: int) -> float:
    """Explicit admissible ETK dimension constant: C_d = (3/2)^d."""
    return (1.5) ** float(d)


def etk_kronecker_bracket_term(alpha: Sequence[float], n: int, h_max: int) -> float:
    """
    Compute an explicit ETK bracket term B_{N,H} for a Kronecker orbit prefix.

    Returns a number B_{N,H} such that:
      D_N^*(P_N) <= C_d * B_{N,H}
    where C_d depends only on dimension.
    """
    if n <= 0 or h_max <= 0:
        return 1.0
    d = len(alpha)

    def term_for_h(h: Sequence[int]) -> float:
        r = 1.0
        theta = 0.0
        sum_abs = 0.0
        for hj, aj in zip(h, alpha):
            if hj != 0:
                r *= float(abs(hj))
            aaj = abs(float(aj))
            sum_abs += float(abs(hj)) * aaj
            theta += float(hj) * float(aj)
        dist = dist_to_nearest_int_lower_bound(theta, sum_abs=sum_abs, d=d)
        if dist <= 0.0:
            return 1.0 / r
        t = 1.0 / (2.0 * float(n) * dist)
        if t > 1.0:
            t = 1.0
        return (1.0 / r) * t

    s = 0.0
    if d == 2:
        for h1 in range(-h_max, h_max + 1):
            for h2 in range(-h_max, h_max + 1):
                if h1 == 0 and h2 == 0:
                    continue
                s += term_for_h((h1, h2))
    elif d == 3:
        for h1 in range(-h_max, h_max + 1):
            for h2 in range(-h_max, h_max + 1):
                for h3 in range(-h_max, h_max + 1):
                    if h1 == 0 and h2 == 0 and h3 == 0:
                        continue
                    s += term_for_h((h1, h2, h3))
    else:
        raise ValueError("Only d=2 or d=3 supported in etk_kronecker_bracket_term.")

    return 1.0 / float(h_max) + s


def choose_best_h(alpha: Sequence[float], n: int, candidates: Iterable[int]) -> Tuple[int, float]:
    """Choose H from a candidate list by minimizing the ETK bracket term B_{N,H}."""
    best_h = None
    best_b = None
    for h in candidates:
        if h <= 0:
            continue
        b = etk_kronecker_bracket_term(alpha, n, h)
        if best_b is None or b < best_b:
            best_b = b
            best_h = h
    assert best_h is not None and best_b is not None
    return best_h, best_b


def birkhoff_geom_2d(alpha: Sequence[float], n: int, m: int, x0: Sequence[float]) -> float:
    """2D Kronecker scan with g_M(x,y)=sum_{k=0}^{m-1}(xy)^k."""
    x = frac_part(x0[0])
    y = frac_part(x0[1])
    a0, a1 = float(alpha[0]), float(alpha[1])
    s = 0.0
    for _ in range(n):
        s += geom_trunc(x * y, m)
        x += a0
        x -= int(x)
        y += a1
        y -= int(y)
    return s / float(n)


def birkhoff_geom_3d(alpha: Sequence[float], n: int, m: int, x0: Sequence[float]) -> float:
    """3D Kronecker scan with g_M(x,y,z)=sum_{k=0}^{m-1}(xyz)^k."""
    x = frac_part(x0[0])
    y = frac_part(x0[1])
    z = frac_part(x0[2])
    a0, a1, a2 = float(alpha[0]), float(alpha[1]), float(alpha[2])
    s = 0.0
    for _ in range(n):
        s += geom_trunc(x * y * z, m)
        x += a0
        x -= int(x)
        y += a1
        y -= int(y)
        z += a2
        z -= int(z)
    return s / float(n)


def ensemble_mean_geom(alpha: Sequence[float], n: int, m: int, k: int, seed: int) -> float:
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
            raise ValueError("Only d=2 or d=3 supported.")
    return sum(vals) / float(k)


def harmonic(m: int, d: int) -> float:
    s = 0.0
    if d == 2:
        for n in range(1, m + 1):
            s += 1.0 / (n * n)
        return s
    if d == 3:
        for n in range(1, m + 1):
            s += 1.0 / (n * n * n)
        return s
    raise ValueError("Only d=2 or d=3 supported in harmonic.")


def fmt_sci_signed(x: float, sig: int = 3) -> str:
    if x == 0.0:
        return "$+0$"
    sign = "+" if x > 0 else "-"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = ax / (10.0**exp)
    mant = round(mant, max(sig - 1, 0))
    if mant >= 10.0:
        mant /= 10.0
        exp += 1
    mant_str = f"{mant:.{max(sig - 1, 0)}f}".rstrip("0").rstrip(".")
    return f"${sign}{mant_str}\\times 10^{{{exp}}}$"


def fmt_sci_unsigned(x: float, sig: int = 2) -> str:
    if x <= 0.0:
        return "$0$"
    exp = int(math.floor(math.log10(x)))
    mant = x / (10.0**exp)
    mant = round(mant, max(sig - 1, 0))
    if mant >= 10.0:
        mant /= 10.0
        exp += 1
    mant_str = f"{mant:.{max(sig - 1, 0)}f}".rstrip("0").rstrip(".")
    return f"${mant_str}\\times 10^{{{exp}}}$"


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

    # zeta(2) (exact)
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
        hm2 = harmonic(m, 2)
        delta_zeta = mean - zeta2
        sampling_err = mean - hm2
        trunc_bound = 1.0 / float(m)
        h_used, b_term = choose_best_h(
            alpha_2d, n, candidates=(10, 20, 30, 40, 50, 80, 100, 150, 200, 300, 500, 800)
        )
        hkvar = (2.0**2 - 1.0) * float(m - 1)
        sampling_bound = hkvar * (etk_constant(2) * b_term)
        ratio = abs(sampling_err) / sampling_bound if sampling_bound > 0.0 else 0.0
        zeta2_rows.append(
            f"({n:,},{m:,},{k}) & {h_used} & {mean:.12f} & {fmt_sci_signed(delta_zeta)} & {fmt_sci_signed(sampling_err)} & {fmt_sci_unsigned(trunc_bound)} & {fmt_sci_unsigned(b_term)} & {fmt_sci_unsigned(sampling_bound)} & {fmt_sci_unsigned(ratio)} \\\\"
        )
    write_rows(gen / "zeta2_rows.tex", zeta2_rows)

    # zeta(3): certified reference midpoint from series tail bound
    m_ref = 200_000
    h_ref = harmonic(m_ref, 3)
    rem_bound = 1.0 / (2.0 * float(m_ref) * float(m_ref))
    zeta3_ref = h_ref + 0.5 * rem_bound

    alpha_3d = (ALPHA_GOLDEN, ALPHA2, ALPHA3)
    zeta3_cases: List[Tuple[int, int, int]] = [
        (200_000, 2_000, 10),
        (1_000_000, 2_000, 10),
    ]
    zeta3_rows: List[str] = []
    for n, m, k in zeta3_cases:
        mean = ensemble_mean_geom(alpha_3d, n, m, k, seed=123)
        hm3 = harmonic(m, 3)
        delta_zeta = mean - zeta3_ref
        sampling_err = mean - hm3
        trunc_bound = 1.0 / (2.0 * float(m) * float(m))
        h_used, b_term = choose_best_h(alpha_3d, n, candidates=(10, 20, 30, 40, 50, 60, 80, 100))
        hkvar = (2.0**3 - 1.0) * float(m - 1)
        sampling_bound = hkvar * (etk_constant(3) * b_term)
        ratio = abs(sampling_err) / sampling_bound if sampling_bound > 0.0 else 0.0
        zeta3_rows.append(
            f"({n:,},{m:,},{k}) & {h_used} & {mean:.12f} & {fmt_sci_signed(delta_zeta)} & {fmt_sci_signed(sampling_err)} & {fmt_sci_unsigned(trunc_bound)} & {fmt_sci_unsigned(b_term)} & {fmt_sci_unsigned(sampling_bound)} & {fmt_sci_unsigned(ratio)} \\\\"
        )
    write_rows(gen / "zeta3_rows.tex", zeta3_rows)

    print(f"Wrote LaTeX rows into: {gen}")
    print("Files: zeta2_rows.tex, zeta3_rows.tex")
    print(f"zeta(3) reference midpoint: {zeta3_ref:.15f} (half-width <= {0.5*rem_bound:.3e})")


if __name__ == "__main__":
    main()


