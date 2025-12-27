# -*- coding: utf-8 -*-
"""
Golden-branch Kronecker scan star discrepancy and an explicit logarithmic bound.

Computes the exact 1D star discrepancy D*_N for P_N = {x0 + t*alpha mod 1}_{t=0}^{N-1}
with alpha = 1/phi, and compares against:
  D*_N <= 2(2 + log_phi N)/N.

Writes a LaTeX row file into sections/generated/golden_discrepancy_rows.tex.
"""

from __future__ import annotations

import math
from pathlib import Path


def kronecker_points(alpha: float, N: int, x0: float) -> list[float]:
    return [((x0 + t * alpha) % 1.0) for t in range(N)]


def star_discrepancy_1d(points: list[float]) -> float:
    xs = sorted(points)
    N = len(xs)
    # For intervals [0,u): D* = max(max_i ((i+1)/N - x_i), max_i (x_i - i/N))
    d_plus = max((i + 1) / N - xs[i] for i in range(N))
    d_minus = max(xs[i] - i / N for i in range(N))
    return max(d_plus, d_minus)


def golden_bound(N: int) -> float:
    phi = (1.0 + 5.0**0.5) / 2.0
    return 2.0 * (2.0 + (math.log(N) / math.log(phi))) / N


def write_rows(rows: list[tuple[int, float, float, float]]) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "golden_discrepancy_rows.tex"

    lines = []
    for N, D, bound, ratio in rows:
        lines.append(f"{N} & {D:.6g} & {bound:.6g} & {ratio:.3f} \\\\")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    phi = (1.0 + 5.0**0.5) / 2.0
    alpha = 1.0 / phi
    x0 = 0.1

    Ns = [100, 300, 1000, 3000, 10000, 30000]
    rows: list[tuple[int, float, float, float]] = []

    for N in Ns:
        pts = kronecker_points(alpha, N, x0=x0)
        D = star_discrepancy_1d(pts)
        bound = golden_bound(N)
        ratio = D / bound if bound > 0 else float("nan")
        rows.append((N, D, bound, ratio))
        print(f"N={N:6d}  D*={D:.6g}  bound={bound:.6g}  ratio={ratio:.3f}")

    write_rows(rows)
    print("Wrote sections/generated/golden_discrepancy_rows.tex")


if __name__ == "__main__":
    main()


