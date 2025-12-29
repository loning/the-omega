"""
Experiment A: star discrepancy and accumulated mismatch for rotation sequences.

Pure-Python (no third-party dependencies) reference implementation.

We compare accumulated mismatch E_N = N * D_N^* for:
- an irrational slope (golden branch),
- another irrational slope (sqrt(2) - 1),
- a rational slope (1/2) as a simple phase-locking / periodic case.
"""

from __future__ import annotations

import math


def kronecker_points(alpha: float, n: int, x0: float) -> list[float]:
    """Return points x_k = (x0 + k*alpha) mod 1 for k=1..n."""
    pts: list[float] = []
    a = float(alpha)
    for k in range(1, n + 1):
        x = x0 + k * a
        pts.append(x - math.floor(x))
    return pts


def star_discrepancy_1d(points: list[float]) -> float:
    """
    1D star discrepancy:
      D*_N = sup_{a in [0,1]} | (1/N)*#{x_i < a} - a |.

    For sorted points y_i, an exact formula is:
      max_i (i/N - y_i) and max_i (y_i - (i-1)/N).
    """
    y = sorted(points)
    n = len(y)
    if n == 0:
        return 0.0
    inv = 1.0 / float(n)
    d1 = 0.0
    d2 = 0.0
    for i, yi in enumerate(y, start=1):
        d1 = max(d1, i * inv - yi)
        d2 = max(d2, yi - (i - 1) * inv)
    return max(d1, d2)


def accumulated_mismatch(alpha: float, n: int, x0: float) -> float:
    pts = kronecker_points(alpha, n=n, x0=x0)
    d = star_discrepancy_1d(pts)
    return float(n) * d


def main() -> None:
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    alpha_golden = 1.0 / phi
    alpha_sqrt2 = math.sqrt(2.0) - 1.0
    alpha_rational = 1.0 / 2.0

    x0 = 0.123456789
    ns = [100, 300, 1_000, 3_000, 10_000, 30_000]

    print("N, E_N(golden), E_N(sqrt2-1), E_N(1/2)")
    for n in ns:
        eg = accumulated_mismatch(alpha_golden, n=n, x0=x0)
        es = accumulated_mismatch(alpha_sqrt2, n=n, x0=x0)
        er = accumulated_mismatch(alpha_rational, n=n, x0=x0)
        print(f"{n:>8d}  {eg:>12.6f}  {es:>12.6f}  {er:>12.6f}")

    print("\nCompatibility check: E_N/log N (slow variation suggests O(log N))")
    print("N, Eg/logN, Es/logN, Er/logN")
    for n in ns:
        logn = math.log(float(n))
        eg = accumulated_mismatch(alpha_golden, n=n, x0=x0) / logn
        es = accumulated_mismatch(alpha_sqrt2, n=n, x0=x0) / logn
        er = accumulated_mismatch(alpha_rational, n=n, x0=x0) / logn
        print(f"{n:>8d}  {eg:>12.6f}  {es:>12.6f}  {er:>12.6f}")


if __name__ == "__main__":
    main()


