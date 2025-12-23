import cmath
import math


def ramanujan_tau_up_to(n_max: int) -> list[int]:
    """
    Compute tau(n) for 0 <= n <= n_max from
      Delta(q) = q * prod_{n>=1} (1 - q^n)^24 = sum_{n>=1} tau(n) q^n,
    truncated to q^{n_max}.

    This is exact integer arithmetic.
    """
    a = [1] + [0] * n_max  # coefficients for prod_{n>=1} (1 - q^n)^24

    for n in range(1, n_max + 1):
        factor = [0] * (n_max + 1)
        for k in range(0, 25):
            power = n * k
            if power > n_max:
                break
            factor[power] += ((-1) ** k) * math.comb(24, k)

        new = [0] * (n_max + 1)
        for i, ai in enumerate(a):
            if ai == 0:
                continue
            for j, fj in enumerate(factor):
                if fj == 0:
                    continue
                if i + j > n_max:
                    break
                new[i + j] += ai * fj
        a = new

    # Multiply by q: shift coefficients right by 1
    delta = [0] * (n_max + 1)
    for k in range(n_max):
        delta[k + 1] = a[k]
    return delta


def rotation_points(alpha: float, n: int, x0: float = 0.0) -> list[float]:
    pts: list[float] = []
    x = x0 % 1.0
    for _ in range(n):
        pts.append(x)
        x = (x + alpha) % 1.0
    return pts


def star_discrepancy(points: list[float]) -> float:
    n = len(points)
    xs = sorted(points)
    d_plus = max(((i + 1) / n - xs[i]) for i in range(n))
    d_minus = max((xs[i] - i / n) for i in range(n))
    return max(d_plus, d_minus)


def delta_value_trunc(tau: complex, tau_coeffs: list[int]) -> complex:
    """
    Delta^{(N)}(tau) = sum_{n=1..N} tau(n) q^n with q=exp(2*pi*i*tau).
    tau_coeffs is a list with tau_coeffs[n]=tau(n) for n=0..N.
    """
    q = cmath.exp(2j * math.pi * tau)
    acc = 0.0 + 0j
    qn = q
    for n in range(1, len(tau_coeffs)):
        acc += tau_coeffs[n] * qn
        qn *= q
    return acc


def poly_sum_power(r: float, p: int) -> float:
    """
    Compute S_p(r)=sum_{k>=1} k^p r^k as r * P_p(r)/(1-r)^{p+1}
    where P_p is the Eulerian polynomial.
    """
    if r <= 0.0:
        return 0.0
    if not (0.0 < r < 1.0):
        raise ValueError("r must be in (0,1)")
    coeffs = eulerian_numbers(p)
    poly = 0.0
    rp = 1.0
    for c in coeffs:
        poly += float(c) * rp
        rp *= r
    return (r * poly) / ((1.0 - r) ** (p + 1))


def eulerian_numbers(p: int) -> list[int]:
    """
    Return Eulerian numbers A(p,m) for m=0..p-1 as a list of length p.
    """
    if p <= 0:
        raise ValueError("p must be >= 1")
    arr = [1]
    for n in range(2, p + 1):
        prev = arr
        cur = [0] * n
        for m in range(n):
            t1 = (m + 1) * (prev[m] if m < len(prev) else 0)
            t2 = (n - m) * (prev[m - 1] if m - 1 >= 0 else 0)
            cur[m] = t1 + t2
        arr = cur
    if len(arr) != p:
        raise RuntimeError("unexpected Eulerian length")
    return arr


def sum_tail_power_bound(r: float, n0: int, p: int) -> float:
    """
    Bound sum_{k>=n0} k^p r^k in closed form:
      sum_{k>=n0} k^p r^k = r^{n0} * sum_{m>=0} (n0+m)^p r^m
    and we bound by expanding (n0+m)^p and using exact generating functions
    for sum_{m>=0} m^j r^m.
    """
    if r <= 0.0:
        return 0.0
    if not (0.0 < r < 1.0):
        raise ValueError("r must be in (0,1)")
    a = float(n0)
    s0 = 1.0 / (1.0 - r)
    expr = (a**p) * s0
    for j in range(1, p + 1):
        sj = poly_sum_power(r, j)
        expr += math.comb(p, j) * (a ** (p - j)) * sj
    return (r**n0) * expr


def log10_sum_tail_power_bound(r: float, n0: int, p: int) -> float:
    """
    log10 of sum_tail_power_bound, computed without forming r**n0 (avoids underflow).
    """
    if not (0.0 < r < 1.0):
        raise ValueError("r must be in (0,1)")
    a = float(n0)
    s0 = 1.0 / (1.0 - r)
    expr = (a**p) * s0
    for j in range(1, p + 1):
        sj = poly_sum_power(r, j)
        expr += math.comb(p, j) * (a ** (p - j)) * sj
    return float(n0) * math.log10(r) + math.log10(expr)


def deligne_majorant_tau(n: int) -> float:
    """
    A simple explicit majorant derived from Deligne + trivial divisor bound:
      |tau(n)| <= d(n) * n^{11/2} <= 2*sqrt(n)*n^{11/2} = 2 n^6.
    """
    return 2.0 * (float(n) ** 6)


def delta_tail_sup_bound(y: float, n_terms: int) -> float:
    """
    A certified sup-norm bound for the tail on the horizontal slice:
      |Delta - Delta^{(n_terms)}| <= sum_{k>=n_terms+1} |tau(k)| r^k
      <= sum_{k>=n_terms+1} 2 k^6 r^k.
    """
    r = math.exp(-2.0 * math.pi * y)
    return 2.0 * sum_tail_power_bound(r, n_terms + 1, 6)


def log10_delta_tail_sup_bound(y: float, n_terms: int) -> float:
    r = math.exp(-2.0 * math.pi * y)
    return math.log10(2.0) + log10_sum_tail_power_bound(r, n_terms + 1, 6)


def variation_bound_g_ny_delta(n_coeff: int, y: float, tau_coeffs: list[int]) -> float:
    """
    Certified bound for Var(g_{n,y}) where
      g_{n,y}(x) = Delta(x+iy) * exp(-2*pi*i*n*x).

    We use Var(g) <= 2*pi * sum_{k>=1} |k-n| |tau(k)| r^k,
    split into a partial sum using exact tau(k) for k<=N and a tail bound using
    |tau(k)| <= 2 k^6 and |k-n| <= k+n.
    """
    r = math.exp(-2.0 * math.pi * y)
    n_terms = len(tau_coeffs) - 1
    partial = 0.0
    for k in range(1, n_terms + 1):
        partial += abs(k - n_coeff) * abs(tau_coeffs[k]) * (r**k)

    # tail: k >= n_terms+1
    # <= sum 2 (k+n) k^6 r^k = 2( sum k^7 r^k + n sum k^6 r^k ) over k>=n_terms+1
    tail_k6 = sum_tail_power_bound(r, n_terms + 1, 6)
    tail_k7 = sum_tail_power_bound(r, n_terms + 1, 7)
    tail = 2.0 * (tail_k7 + float(n_coeff) * tail_k6)

    return 2.0 * math.pi * (partial + tail)


def estimate_tau_n_from_samples(alpha: float, x0: float, y: float, n_coeff: int, tau_coeffs: list[int], xs: list[float]) -> complex:
    acc = 0.0 + 0j
    for x in xs:
        tau = complex(x, y)
        fy = delta_value_trunc(tau, tau_coeffs)
        acc += fy * cmath.exp(-2j * math.pi * n_coeff * x)
    return math.exp(2.0 * math.pi * n_coeff * y) * (acc / len(xs))


def main() -> None:
    # Golden branch scan
    phi = (1.0 + 5.0**0.5) / 2.0
    alpha = 1.0 / phi
    x0 = 0.123456789

    # Choose a moderate height to avoid ill-conditioning for n>1.
    y = 0.4
    r = math.exp(-2.0 * math.pi * y)

    # Sampling parameters
    n_samples = 5000
    xs = rotation_points(alpha, n_samples, x0=x0)
    dstar = star_discrepancy(xs)

    # Delta truncation depth (exact integer coefficients)
    n_terms = 200
    tau_coeffs = ramanujan_tau_up_to(n_terms)

    print("Delta / Ramanujan tau slice-sampling recovery (golden scan)")
    print(f"alpha=1/phi={alpha:.16f}, x0={x0}, y={y}, |q|={r:.6e}")
    print(f"N={n_samples}, D*={dstar:.6e}, n_terms={n_terms}")
    print("")

    ns = [1, 2, 4]
    print("n, tau(n), |error|, sampling_bound, log10_trunc_bound, ratio")
    for n in ns:
        tau_true = tau_coeffs[n]
        tau_hat = estimate_tau_n_from_samples(alpha, x0, y, n, tau_coeffs, xs)
        err = abs(tau_hat - tau_true)

        var_bd = variation_bound_g_ny_delta(n_coeff=n, y=y, tau_coeffs=tau_coeffs)
        sampling_bd = math.exp(2.0 * math.pi * n * y) * var_bd * dstar

        log10_trunc_bd = (2.0 * math.pi * n * y) / math.log(10.0) + log10_delta_tail_sup_bound(y=y, n_terms=n_terms)
        trunc_bd = 0.0
        if log10_trunc_bd > -300.0:
            trunc_bd = 10.0 ** log10_trunc_bd

        total_bd = sampling_bd + trunc_bd
        ratio = err / total_bd if total_bd > 0 else float("nan")

        print(f"{n:2d}, {tau_true:12d}, {err:.6e}, {sampling_bd:.6e}, {log10_trunc_bd:.3f}, {ratio:.6e}")

    print("")
    # Certified Hecke check at p=2: tau(4) = tau(2)^2 - 2^11 tau(1)
    p = 2
    tau1_true = tau_coeffs[1]
    tau2_true = tau_coeffs[2]
    tau4_true = tau_coeffs[4]

    tau1_hat = estimate_tau_n_from_samples(alpha, x0, y, 1, tau_coeffs, xs)
    tau2_hat = estimate_tau_n_from_samples(alpha, x0, y, 2, tau_coeffs, xs)
    tau4_hat = estimate_tau_n_from_samples(alpha, x0, y, 4, tau_coeffs, xs)

    # Individual certified bounds (same as above)
    def total_bound(n: int) -> float:
        var_bd = variation_bound_g_ny_delta(n_coeff=n, y=y, tau_coeffs=tau_coeffs)
        sampling_bd = math.exp(2.0 * math.pi * n * y) * var_bd * dstar
        log10_trunc_bd = (2.0 * math.pi * n * y) / math.log(10.0) + log10_delta_tail_sup_bound(y=y, n_terms=n_terms)
        trunc_bd = 0.0
        if log10_trunc_bd > -300.0:
            trunc_bd = 10.0 ** log10_trunc_bd
        return sampling_bd + trunc_bd

    e1 = total_bound(1)
    e2 = total_bound(2)
    e4 = total_bound(4)

    lhs = abs(tau4_hat - (tau2_hat * tau2_hat - (p**11) * tau1_hat))
    rhs = e4 + e2 * (abs(tau2_hat) + abs(tau2_true)) + (p**11) * e1
    ratio = lhs / rhs if rhs > 0 else float("nan")

    print("Hecke p=2 certified closure (using recovered coefficients)")
    print(f"lhs=|tau_hat(4) - (tau_hat(2)^2 - 2^11 tau_hat(1))| = {lhs:.6e}")
    print(f"rhs=budget = {rhs:.6e}")
    print(f"ratio = {ratio:.6e}")


if __name__ == "__main__":
    main()


