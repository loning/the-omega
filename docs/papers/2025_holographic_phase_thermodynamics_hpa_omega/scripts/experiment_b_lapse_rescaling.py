"""
Experiment B: computational lapse rescaling of entropy flow.

Pure-Python (no third-party dependencies) reference implementation.

We treat the per-scan-step mismatch density sigma as a toy proxy given by
star discrepancy D_N^* for a large window N. The externally observed entropy
production rate is then:

  dS/dt = k_B * sigma * lapse.

This script demonstrates linear scaling in the lapse factor.
"""

from __future__ import annotations

import math


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


def main() -> None:
    kB = 1.0
    alpha_golden = (math.sqrt(5.0) - 1.0) / 2.0
    N = 100_000
    x0 = 0.123456789

    D = star_discrepancy(rotation_points(alpha_golden, N, x0=x0))
    sigma = D  # per-scan-step mismatch proxy

    print("Using sigma := D_N^* for the golden branch as a toy proxy.")
    print(f"N={N}, D_N^*={D:.8e}")

    lapses = [1.0, 0.5, 0.2, 0.1, 0.02]
    print("\nToy rescaling: dS/dt = k_B * sigma * lapse")
    baseline = kB * sigma * lapses[0]
    for L in lapses:
        rate = kB * sigma * L
        ratio = rate / baseline if baseline != 0.0 else float("nan")
        print(f"lapse={L:>6.2f}  dS/dt={rate:.8e}  ratio={ratio:.4f}")


if __name__ == "__main__":
    main()


