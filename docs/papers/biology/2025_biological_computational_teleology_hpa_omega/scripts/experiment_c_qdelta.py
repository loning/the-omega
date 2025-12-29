"""
Experiment C: computing the resonance susceptibility / anti-locking index Q_delta(alpha).

Definition:
  Q_delta(alpha) = min{ q in N : exists p in Z s.t. |alpha - p/q| < delta }.

We implement a constructive search by scanning q and checking the nearest p.
This is a toy utility for Section 7 and Appendix (golden-branch control-law hypothesis).
"""

from __future__ import annotations

import math


def q_delta(alpha: float, delta: float, q_max: int = 200_000) -> int | None:
    """Return Q_delta(alpha) up to q_max, or None if not found within the search."""
    a = float(alpha)
    d = float(delta)
    for q in range(1, q_max + 1):
        aq = a * q
        p0 = int(round(aq))
        # Check nearest integers (robust to rounding edge cases).
        for p in (p0 - 1, p0, p0 + 1):
            if abs(a - (p / q)) < d:
                return q
    return None


def main() -> None:
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    alpha_golden = 1.0 / phi
    alpha_rational = 3.0 / 5.0

    deltas = [1e-1, 5e-2, 2e-2, 1e-2, 5e-3, 2e-3, 1e-3]

    print("delta, Q_delta(golden), Q_delta(3/5)")
    for delta in deltas:
        qg = q_delta(alpha_golden, delta=delta, q_max=200_000)
        qr = q_delta(alpha_rational, delta=delta, q_max=200_000)
        print(f"{delta:>8.1e}  {str(qg):>14s}  {str(qr):>10s}")

    print("\nHurwitz lower bound scale for golden branch: ceil((1/(sqrt(5)*delta))^(1/2))")
    for delta in deltas:
        bound = math.ceil(math.sqrt(1.0 / (math.sqrt(5.0) * delta)))
        print(f"{delta:>8.1e}  {bound:>6d}")


if __name__ == "__main__":
    main()


