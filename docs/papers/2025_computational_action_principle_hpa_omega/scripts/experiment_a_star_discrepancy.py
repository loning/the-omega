import math

import numpy as np


def star_discrepancy_1d(x: np.ndarray) -> float:
    """Compute 1D star discrepancy for points x in [0,1)."""
    x = np.sort(np.asarray(x, dtype=float))
    N = len(x)
    i = np.arange(1, N + 1, dtype=float)
    d1 = np.max(i / N - x)
    d2 = np.max(x - (i - 1) / N)
    return float(max(d1, d2))


def orbit_points(alpha: float, N: int, x0: float = 0.0) -> np.ndarray:
    n = np.arange(N, dtype=float)
    return (x0 + n * alpha) % 1.0


def EN(alpha: float, N: int, x0: float = 0.12345) -> float:
    x = orbit_points(alpha, N, x0=x0)
    D = star_discrepancy_1d(x)
    return float(N * D)


def stats(vals: np.ndarray):
    vals = np.asarray(vals, dtype=float)
    return float(vals.min()), float(vals.max()), float(vals.mean()), float(vals.std())


def continued_fraction(alpha: float, max_terms: int = 64):
    """
    Return partial quotients [a1, a2, ...] for alpha in (0,1) with
    alpha = [0; a1, a2, ...] using floating-point iteration.
    """
    x = float(alpha)
    a = []
    for _ in range(max_terms):
        if x <= 0:
            break
        inv = 1.0 / x
        ai = int(math.floor(inv))
        a.append(ai)
        x = inv - ai
        if abs(x) < 1e-15:
            break
    return a


def dk_upper_bound(alpha: float, N: int, max_terms: int = 64):
    """
    Denjoy--Koksma/Ostrowski proxy upper bound used in Theorem 03:
      E_N = N D_N^* <= 2 * sum_{j=1}^{m+1} a_j,
    where q_m <= N < q_{m+1} and alpha = [0; a1, a2, ...].
    Returns (U_N, m, C_m) with U_N = 2*C_m and C_m = sum_{j=1}^{m+1} a_j.
    """
    a = continued_fraction(alpha, max_terms=max_terms)
    if not a:
        return float("nan"), -1, float("nan")

    # q_{-1} = 0, q_0 = 1
    q_prev = 0
    q_curr = 1
    m = -1
    for j, aj in enumerate(a, start=1):
        q_next = aj * q_curr + q_prev
        if q_curr <= N < q_next:
            m = j - 1  # current q_curr is q_m
            break
        q_prev, q_curr = q_curr, q_next

    if m < 0:
        # Fallback: N is beyond computed range; treat last available as m.
        m = len(a) - 1

    C_m = float(sum(a[: m + 1]))  # sum_{j=1}^{m+1} a_j
    U_N = 2.0 * C_m
    return U_N, m, C_m


def linfit(xs: np.ndarray, ys: np.ndarray):
    """Least squares fit y = a x + b with R^2."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    mx = float(xs.mean())
    my = float(ys.mean())
    sxx = float(((xs - mx) ** 2).sum())
    sxy = float(((xs - mx) * (ys - my)).sum())
    a = sxy / sxx if sxx != 0 else float("nan")
    b = my - a * mx
    sst = float(((ys - my) ** 2).sum())
    sse = float(((ys - (a * xs + b)) ** 2).sum())
    r2 = 1.0 - sse / sst if sst != 0 else float("nan")
    return a, b, r2


if __name__ == "__main__":
    alphas = {
        "golden_phi^-1": (math.sqrt(5) - 1) / 2,
        "sqrt2_minus_1": math.sqrt(2) - 1,
        "e_minus_2": math.e - 2,
        "pi_minus_3": math.pi - 3,
    }

    Ns = [200, 500, 1000, 2000, 5000, 10000, 20000]

    header = ["N"] + list(alphas.keys())
    print("\t".join(header))
    series = {name: [] for name in alphas}
    for N in Ns:
        row = [str(N)]
        for name, a in alphas.items():
            v = EN(a, N)
            series[name].append(v)
            row.append(f"{v:.6f}")
        print("\t".join(row))

    print("\nFit: E_N ~ A log N + B (least squares on the sampled Ns)")
    xs = np.log(np.asarray(Ns, dtype=float))
    for name, ys_list in series.items():
        ys = np.asarray(ys_list, dtype=float)
        A, B, r2 = linfit(xs, ys)
        print(f"{name}: A={A:.6f}, B={B:.6f}, R2={r2:.6f}")

    # x0 sensitivity (anchored-interval discrepancy depends on phase shift x0).
    N0 = 20000
    x0s = np.arange(16, dtype=float) / 16.0
    print(f"\nPhase-offset sensitivity at N={N0} over x0 in {{0,1/16,...,15/16}}")
    for name, a in alphas.items():
        vals = np.array([EN(a, N0, x0=float(x0)) for x0 in x0s], dtype=float)
        mn, mx, mean, sd = stats(vals)
        print(f"{name}: min={mn:.6f}, max={mx:.6f}, mean={mean:.6f}, std={sd:.6f}")

    # Theorem proxy upper bound (uniform in x0).
    print("\nTheorem proxy upper bound U_N = 2*sum_{j<=m+1} a_j (float CF)")
    for N in Ns:
        print(f"N={N}")
        for name, a in alphas.items():
            U_N, m, C_m = dk_upper_bound(a, N)
            e = EN(a, N)
            ratio = e / U_N if U_N > 0 else float("nan")
            print(f"  {name}: E_N={e:.6f}, U_N={U_N:.6f}, ratio={ratio:.6f}, m={m}, C_m={C_m:.0f}")


