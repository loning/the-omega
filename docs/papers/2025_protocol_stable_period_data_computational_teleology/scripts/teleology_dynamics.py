#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experiment 4: inertial gradient flow with damping (teleological dynamics).

We simulate:
  mu * ddot(theta) + gamma * dot(theta) = - grad U(theta)
with a toy multi-well potential U(theta) = (theta^2 - 1)^2.

This script writes a LaTeX row file into:
  sections/generated/teleology_energy_rows.tex

No third-party dependencies.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple


def U(theta: float) -> float:
    return (theta * theta - 1.0) ** 2


def grad_U(theta: float) -> float:
    return 4.0 * theta * (theta * theta - 1.0)


def simulate(
    mu: float = 1.0,
    gamma: float = 0.6,
    dt: float = 1e-3,
    steps: int = 200000,
    theta0: float = 2.0,
    v0: float = 0.0,
    sample_every: int = 20000,
) -> List[Tuple[int, float, float, float, float]]:
    theta = theta0
    v = v0
    samples: List[Tuple[int, float, float, float, float]] = []
    for k in range(steps + 1):
        if k % sample_every == 0:
            e = 0.5 * mu * (v * v) + U(theta)
            samples.append((k, theta, v, U(theta), e))
        if k == steps:
            break
        # semi-implicit Euler
        a = -(gamma * v + grad_U(theta)) / mu
        v = v + dt * a
        theta = theta + dt * v
    return samples


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
    samples = simulate(mu=1.0, gamma=0.6, dt=1e-3, steps=200000, theta0=2.0, v0=0.0)

    latex_lines: List[str] = []
    for k, theta, v, u, e in samples:
        latex_lines.append(f"{k:,} & {theta:+.6f} & {v:+.6f} & {u:.6e} & {e:.6e} \\\\")

    root = Path(__file__).resolve().parent.parent
    gen = root / "sections" / "generated"
    write_rows(gen / "teleology_energy_rows.tex", latex_lines)

    print("Teleological dynamics toy run:")
    for k, theta, v, u, e in samples:
        print(f"k={k:6d} theta={theta:+.6f} v={v:+.6f} U={u:.6e} E={e:.6e}")
    print(f"\nWrote LaTeX rows into: {gen}")
    print("File: teleology_energy_rows.tex")


if __name__ == "__main__":
    main()


