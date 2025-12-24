"""
Experiment A: star discrepancy and accumulated mismatch for rotation sequences.

Pure-Python (no third-party dependencies) reference implementation.

We compare accumulated mismatch E_N = N * D_N^* for:
- an irrational slope (golden branch),
- another irrational slope (sqrt(2) - 1),
- a rational slope (1/2) as a simple phase-locking / periodic case.

The output illustrates compatibility with O(log N) for badly approximable
irrationals, and linear growth for rational slopes.
"""

from __future__ import annotations

import math


def rotation_points(alpha: float, N: int, x0: float = 0.0) -> list[float]:
    pts: list[float] = []
    x = float(x0)
    a = float(alpha)
    for n in range(1, N + 1):
        x = x0 + n * a
        pts.append(x - math.floor(x))
    return pts


def star_discrepancy(points: list[float]) -> float:
    """1D star discrepancy for points in [0, 1)."""
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


def accumulated_mismatch(alpha: float, N: int, x0: float = 0.0) -> float:
    pts = rotation_points(alpha, N, x0=x0)
    D = star_discrepancy(pts)
    return float(N) * D


def unique_points_count(alpha: float, N: int, x0: float = 0.0, tol: float = 1e-12) -> int:
    pts = rotation_points(alpha, N, x0=x0)
    quant = set()
    inv_tol = 1.0 / tol
    for p in pts:
        q = int(round(p * inv_tol))
        quant.add(q)
    return len(quant)

def linfit(xs: list[float], ys: list[float]):
    """Least squares fit y = a x + b and R^2."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    a = sxy / sxx if sxx != 0 else float("nan")
    b = my - a * mx
    sst = sum((y - my) ** 2 for y in ys)
    sse = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - sse / sst if sst != 0 else float("nan")
    return a, b, r2


def stats(vals: list[float]):
    n = len(vals)
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / n
    return min(vals), max(vals), mean, math.sqrt(var)


def main() -> None:
    alpha_golden = (math.sqrt(5.0) - 1.0) / 2.0
    alpha_sqrt2 = math.sqrt(2.0) - 1.0
    alpha_rational = 1.0 / 2.0

    Ns = [100, 300, 1_000, 3_000, 10_000, 30_000, 100_000]
    x0 = 0.123456789

    print("N, E_N(golden), E_N(sqrt2-1), E_N(rational=1/2)")
    Eg_list: list[float] = []
    Es_list: list[float] = []
    for N in Ns:
        Eg = accumulated_mismatch(alpha_golden, N, x0=x0)
        Es = accumulated_mismatch(alpha_sqrt2, N, x0=x0)
        Er = accumulated_mismatch(alpha_rational, N, x0=x0)
        Eg_list.append(Eg)
        Es_list.append(Es)
        print(f"{N:>8d}  {Eg:>12.6f}  {Es:>12.6f}  {Er:>14.6f}")

    print("\nCompatibility check: E_N/log N (smaller and slowly varying suggests O(log N))")
    print("N, Eg/logN, Es/logN, Er/logN")
    for N in Ns:
        logN = math.log(float(N))
        Eg = accumulated_mismatch(alpha_golden, N, x0=x0) / logN
        Es = accumulated_mismatch(alpha_sqrt2, N, x0=x0) / logN
        Er = accumulated_mismatch(alpha_rational, N, x0=x0) / logN
        print(f"{N:>8d}  {Eg:>12.6f}  {Es:>12.6f}  {Er:>14.6f}")

    print("\nPeriodicity sanity check (unique points count for N=2000):")
    Np = 2000
    ug = unique_points_count(alpha_golden, Np, x0=x0)
    us = unique_points_count(alpha_sqrt2, Np, x0=x0)
    ur = unique_points_count(alpha_rational, Np, x0=x0)
    print(f"golden:  {ug} unique points (should be large)")
    print(f"sqrt2-1: {us} unique points (should be large)")
    print(f"1/2:     {ur} unique points (should be 2)")

    # Explicit continued-fraction envelope bounds for two standard badly-approximable slopes.
    # Using the bound D_N^* <= (1 + sum_{i=1}^m a_i)/N for q_m <= N < q_{m+1},
    # where a_i are continued-fraction partial quotients and q_m are denominators.
    #
    # For golden: a_i=1, q_m=F_{m+1}, so E_N <= 1+m when F_{m+1}<=N<F_{m+2}.
    # For sqrt(2)-1: a_i=2, q_m follow Pell-type recurrence q_{m+1}=2q_m+q_{m-1}.
    def fib_index_for_N(N: int) -> int:
        # Return m such that F_{m+1} <= N < F_{m+2}, with F_1=1,F_2=1.
        f_prev, f = 1, 1  # F_1, F_2
        m = 1  # corresponds to F_{m+1}=F_2 initially
        while True:
            f_next = f_prev + f  # next Fibonacci
            if f_next > N:
                return m
            f_prev, f = f, f_next
            m += 1

    def pell_index_for_N(N: int) -> int:
        # Denominators for [0;2,2,2,...] satisfy q_0=1,q_1=2,q_{m+1}=2q_m+q_{m-1}.
        q_prev, q = 1, 2
        m = 1
        while True:
            q_next = 2 * q + q_prev
            if q_next > N:
                return m
            q_prev, q = q, q_next
            m += 1

    print("\nExplicit envelope upper bounds from continued fractions (via Kuipers--Niederreiter):")
    print("N, E_N(golden), bound_golden, E_N(sqrt2-1), bound_sqrt2-1")
    for N in Ns:
        Eg = accumulated_mismatch(alpha_golden, N, x0=x0)
        Es = accumulated_mismatch(alpha_sqrt2, N, x0=x0)

        m_g = fib_index_for_N(N)
        bound_g = 1.0 + float(m_g)  # 1 + sum a_i = 1 + m (all a_i=1)

        m_s = pell_index_for_N(N)
        bound_s = 1.0 + 2.0 * float(m_s)  # 1 + sum a_i = 1 + 2m (all a_i=2)

        print(f"{N:>8d}  {Eg:>12.6f}  {bound_g:>12.6f}  {Es:>12.6f}  {bound_s:>12.6f}")

    print("\nFit diagnostic for irrationals: E_N ~ A log N + B (finite range)")
    xs = [math.log(float(N)) for N in Ns]
    A_g, B_g, r2_g = linfit(xs, Eg_list)
    A_s, B_s, r2_s = linfit(xs, Es_list)
    print(f"golden:   A={A_g:.6f}, B={B_g:.6f}, R2={r2_g:.6f}")
    print(f"sqrt2-1:  A={A_s:.6f}, B={B_s:.6f}, R2={r2_s:.6f}")

    print("\nPhase-offset sensitivity at N=30000 over x0 in {0,1/16,...,15/16}:")
    N0 = 30000
    x0s = [i / 16.0 for i in range(16)]
    for name, alpha in [("golden", alpha_golden), ("sqrt2-1", alpha_sqrt2), ("1/2", alpha_rational)]:
        vals = [accumulated_mismatch(alpha, N0, x0=float(xx)) for xx in x0s]
        mn, mx, mean, sd = stats(vals)
        print(f"{name:>6s}: min={mn:.6f} max={mx:.6f} mean={mean:.6f} std={sd:.6f}")


if __name__ == "__main__":
    main()


