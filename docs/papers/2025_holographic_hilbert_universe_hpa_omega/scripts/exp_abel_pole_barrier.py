# -*- coding: utf-8 -*-
"""
Toy Abel pole-barrier / threshold experiment.

We consider the mode:
  u_t = exp((beta - 1/2) t) * cos(gamma t),
and its Abel-weighted partial sum:
  S(r;T) = sum_{t=0}^{T-1} r^t u_t.

When beta > 1/2, the effective growth factor is r * exp(beta - 1/2).
The threshold radius is:
  r_c = exp(-(beta - 1/2)).

This script evaluates |S(r;T_max)| across r values around r_c and writes
sections/generated/abel_barrier_rows.tex for the paper table.
"""

from __future__ import annotations

import math
from pathlib import Path


def abel_mode_partial_sum(r: float, beta: float, gamma: float, T_max: int) -> float:
    lam = beta - 0.5
    s = 0.0
    for t in range(T_max):
        s += (r**t) * math.exp(lam * t) * math.cos(gamma * t)
    return s


def critical_radius(beta: float) -> float:
    return math.exp(-(beta - 0.5))


def write_rows(rows: list[tuple[float, float, float]]) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "abel_barrier_rows.tex"

    lines = []
    for beta, r, val in rows:
        lines.append(f"{beta:.3f} & {r:.4f} & {val:.6e} \\\\")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    gamma = 1.0
    T_max = 5000

    betas = [0.5, 0.6]
    rows: list[tuple[float, float, float]] = []

    for beta in betas:
        rc = critical_radius(beta)
        print(f"beta={beta:.3f}  critical radius r_c={rc:.6f}")

        # Choose r values around the threshold.
        r_values = [0.80, 0.88, 0.90, 0.905, 0.92, 0.95, 0.98]
        for r in r_values:
            s = abel_mode_partial_sum(r, beta=beta, gamma=gamma, T_max=T_max)
            mag = abs(s)
            rows.append((beta, r, mag))
            print(f"  r={r:.4f}  |S|={mag:.6e}")

    write_rows(rows)
    print("Wrote sections/generated/abel_barrier_rows.tex")


if __name__ == "__main__":
    main()


