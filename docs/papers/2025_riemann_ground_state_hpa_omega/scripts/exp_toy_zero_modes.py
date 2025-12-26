#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experiment B: toy "zero-mode" signal, discrete energy growth, and Abel thresholds.

We build a signal from the imaginary parts of the first K nontrivial zeta zeros on
the critical line (hard-coded constants), then introduce an artificial real-part
shift delta>0 on a single mode and observe:
  (i) rapid energy growth in T, and
  (ii) an Abel threshold near r0 = exp(-delta).

This script writes LaTeX table row files into:
  sections/generated/toy_energy_rows.tex
  sections/generated/toy_abel_rows.tex

No third-party dependencies.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Sequence, Tuple


# Imaginary parts gamma_k of the first 20 nontrivial zeros 1/2 + i*gamma_k.
# Values are standard numerical constants; high precision is not required here.
GAMMAS_20: List[float] = [
    14.134725141734693,
    21.022039638771555,
    25.010857580145689,
    30.424876125859513,
    32.935061587739190,
    37.586178158825671,
    40.918719012147495,
    43.327073280914999,
    48.005150881167160,
    49.773832477672302,
    52.970321477714461,
    56.446247697063395,
    59.347044002602353,
    60.831778524609810,
    65.112544048081607,
    67.079810529494174,
    69.546401711173979,
    72.067157674481908,
    75.704690699083933,
    77.144840068874805,
]


def signal(t: int, gammas: Sequence[float], delta: float = 0.0, idx: int = 0) -> float:
    """
    e_delta(t) = exp(delta*t)*cos(gamma_idx * t) + sum_{k != idx} cos(gamma_k * t).
    """
    s = 0.0
    for j, g in enumerate(gammas):
        amp = math.exp(delta * float(t)) if (delta != 0.0 and j == idx) else 1.0
        s += amp * math.cos(g * float(t))
    return s


def energy_discrete(T: int, gammas: Sequence[float], delta: float = 0.0) -> Tuple[float, float]:
    """
    Discrete energy proxy: E(T) = sum_{t=0}^{T-1} |e_delta(t)|^2.
    Returns (energy, max_abs).
    """
    e2 = 0.0
    m = 0.0
    for t in range(T):
        v = signal(t, gammas, delta=delta)
        av = abs(v)
        if av > m:
            m = av
        e2 += v * v
    return e2, m


def abel_partial_sum(Tmax: int, r: float, gammas: Sequence[float], delta: float = 0.0) -> float:
    """
    Finite-horizon Abel sum S_delta(r;Tmax) = sum_{t=0}^{Tmax-1} r^t e_delta(t).
    """
    s = 0.0
    wt = 1.0
    for t in range(Tmax):
        s += wt * signal(t, gammas, delta=delta)
        wt *= r
    return s


def fmt_sci_unsigned(x: float, sig: int = 4) -> str:
    """LaTeX scientific notation without sign, for nonnegative quantities."""
    x = float(x)
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


def fmt_decimal(x: float, digits: int = 2) -> str:
    return f"${x:.{digits}f}$"


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

    gammas = GAMMAS_20
    Ts = [50, 100, 150]
    deltas = [0.00, 0.05, 0.10]

    energy_rows: List[str] = []
    for T in Ts:
        for delta in deltas:
            E, M = energy_discrete(T, gammas, delta=delta)
            energy_rows.append(
                f"{T:d} & {fmt_decimal(delta, digits=2)} & {fmt_sci_unsigned(E)} & {fmt_sci_unsigned(M)} \\\\"
            )
    write_rows(gen / "toy_energy_rows.tex", energy_rows)

    delta = 0.10
    Tmax = 2000
    rs = [0.80, 0.90, 0.92, 0.94, 0.96]

    abel_rows: List[str] = []
    for r in rs:
        S = abel_partial_sum(Tmax, r, gammas, delta=delta)
        abel_rows.append(
            f"{fmt_decimal(delta, digits=2)} & {fmt_decimal(r, digits=2)} & {fmt_sci_unsigned(abs(S), sig=5)} \\\\"
        )
    write_rows(gen / "toy_abel_rows.tex", abel_rows)

    print(f"Wrote LaTeX rows into: {gen}")
    print("Files: toy_energy_rows.tex, toy_abel_rows.tex")


if __name__ == "__main__":
    main()


