import cmath
import math


ZETA5 = 1.0369277551433699263


def sigma_k_table(n_terms: int, k: int) -> list[int]:
    """
    Compute sigma_k(n)=sum_{d|n} d^k for n=0..n_terms in O(n_terms log n_terms) time.
    """
    sig = [0] * (n_terms + 1)
    for d in range(1, n_terms + 1):
        dk = d**k
        for m in range(d, n_terms + 1, d):
            sig[m] += dk
    return sig


def e6_coeffs(n_terms: int) -> list[int]:
    """
    Return the truncation coefficients for E6(tau)=sum_{n=0..n_terms} a_n q^n with a_0=1.
    """
    sig5 = sigma_k_table(n_terms, 5)
    coeffs = [0] * (n_terms + 1)
    coeffs[0] = 1
    for n in range(1, n_terms + 1):
        coeffs[n] = -504 * sig5[n]
    return coeffs


def eisenstein_value_trunc(tau: complex, coeffs: list[int]) -> complex:
    """
    Evaluate sum_{n=0..N} coeffs[n] q^n where q=exp(2*pi*i*tau).
    """
    q = cmath.exp(2j * math.pi * tau)
    acc = complex(coeffs[0], 0.0)
    qn = q
    for n in range(1, len(coeffs)):
        acc += coeffs[n] * qn
        qn *= q
    return acc


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


def sum_tail_n5(r: float, n0: int) -> float:
    """
    Bound sum_{k>=n0} k^5 r^k in closed form.
    We expand (n0+m)^5 and sum m^j r^m for j=0..5.
    """
    if r <= 0.0:
        return 0.0
    if not (0.0 < r < 1.0):
        raise ValueError("r must be in (0,1)")
    a = float(n0)
    s0 = 1.0 / (1.0 - r)
    s1 = r / (1.0 - r) ** 2
    s2 = r * (1.0 + r) / (1.0 - r) ** 3
    s3 = r * (1.0 + 4.0 * r + r * r) / (1.0 - r) ** 4
    s4 = r * (1.0 + 11.0 * r + 11.0 * r * r + r**3) / (1.0 - r) ** 5
    s5 = r * (1.0 + 26.0 * r + 66.0 * r * r + 26.0 * r**3 + r**4) / (1.0 - r) ** 6
    expr = a**5 * s0 + 5.0 * a**4 * s1 + 10.0 * a**3 * s2 + 10.0 * a**2 * s3 + 5.0 * a * s4 + s5
    return (r**n0) * expr


def log10_sum_tail_n5(r: float, n0: int) -> float:
    """
    log10 of the same closed-form bound as sum_tail_n5, computed without forming r**n0
    (avoids floating underflow when n0 is large).
    """
    if not (0.0 < r < 1.0):
        raise ValueError("r must be in (0,1)")
    a = float(n0)
    s0 = 1.0 / (1.0 - r)
    s1 = r / (1.0 - r) ** 2
    s2 = r * (1.0 + r) / (1.0 - r) ** 3
    s3 = r * (1.0 + 4.0 * r + r * r) / (1.0 - r) ** 4
    s4 = r * (1.0 + 11.0 * r + 11.0 * r * r + r**3) / (1.0 - r) ** 5
    s5 = r * (1.0 + 26.0 * r + 66.0 * r * r + 26.0 * r**3 + r**4) / (1.0 - r) ** 6
    expr = a**5 * s0 + 5.0 * a**4 * s1 + 10.0 * a**3 * s2 + 10.0 * a**2 * s3 + 5.0 * a * s4 + s5
    return float(n0) * math.log10(r) + math.log10(expr)


def e6_trunc_tail_bound(y: float, n_terms: int) -> float:
    """
    |E6 - E6^{(n_terms)}| <= 504 * zeta(5) * sum_{k>=n_terms+1} k^5 r^k
    with r = exp(-2*pi*y).
    """
    r = math.exp(-2.0 * math.pi * y)
    return 504.0 * ZETA5 * sum_tail_n5(r, n_terms + 1)


def log10_e6_trunc_tail_bound(y: float, n_terms: int) -> float:
    """
    log10 of the same bound as e6_trunc_tail_bound, computed in log domain.
    """
    r = math.exp(-2.0 * math.pi * y)
    return math.log10(504.0 * ZETA5) + log10_sum_tail_n5(r, n_terms + 1)


def variation_bound_g_ny_e6(n_coeff: int, y: float) -> float:
    """
    Explicit (safe) bound for Var(g_{n,y}) where
      g_{n,y}(x) = E6(x+iy) * exp(-2*pi*i*n*x),
    using |sigma_5(k)| <= zeta(5) * k^5 and |k-n| <= k+n.

    Var(g) <= 2*pi*( n + 504*zeta(5) * ( sum k^6 r^k + n sum k^5 r^k ) ).
    """
    r = math.exp(-2.0 * math.pi * y)
    s5 = poly_sum_power(r, 5)
    s6 = poly_sum_power(r, 6)
    sum_abs_m_c_m = float(n_coeff) + 504.0 * ZETA5 * (s6 + float(n_coeff) * s5)
    return 2.0 * math.pi * sum_abs_m_c_m


def estimate_a_n_e6(alpha: float, x0: float, y: float, n_coeff: int, n_terms: int, n_samples: int) -> complex:
    pts = rotation_points(alpha, n_samples, x0=x0)
    acc = 0.0 + 0j
    coeffs = e6_coeffs(n_terms)
    for x in pts:
        tau = complex(x, y)
        fy = eisenstein_value_trunc(tau, coeffs)
        acc += fy * cmath.exp(-2j * math.pi * n_coeff * x)
    return math.exp(2.0 * math.pi * n_coeff * y) * (acc / n_samples)


def main() -> None:
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    alpha = 1.0 / phi
    x0 = 0.123456789

    y = 1.0
    n_coeff = 1
    n_terms = 600
    coeffs = e6_coeffs(n_terms)
    a_n_true = coeffs[n_coeff]

    var_bd = variation_bound_g_ny_e6(n_coeff=n_coeff, y=y)
    log10_trunc_bd = (2.0 * math.pi * n_coeff * y) / math.log(10.0) + log10_e6_trunc_tail_bound(y=y, n_terms=n_terms)

    print("E6 slice-sampling coefficient recovery (n=1)")
    print(f"alpha=1/phi={alpha:.16f}, x0={x0}, y={y}, n_terms={n_terms}")
    print(f"a_n true = {a_n_true}")
    print(f"Var(g_{n_coeff},y) bound = {var_bd:.6f}")
    print(f"log10 trunc bound (coefficient) = {log10_trunc_bd:.3f}")
    print("")
    print(" N, D*, |error|, sampling_bound, log10_trunc_bound, ratio")

    for n_samples in [100, 200, 500, 1_000, 2_000, 5_000, 10_000]:
        pts = rotation_points(alpha, n_samples, x0=x0)
        dstar = star_discrepancy(pts)

        a_hat = estimate_a_n_e6(
            alpha=alpha,
            x0=x0,
            y=y,
            n_coeff=n_coeff,
            n_terms=n_terms,
            n_samples=n_samples,
        )
        err = abs(a_hat - a_n_true)

        sampling_bd = math.exp(2.0 * math.pi * n_coeff * y) * var_bd * dstar
        trunc_bd = 0.0
        if log10_trunc_bd > -300.0:
            trunc_bd = 10.0 ** log10_trunc_bd
        total_bd = sampling_bd + trunc_bd
        ratio = err / total_bd if total_bd > 0 else float("nan")

        print(f"{n_samples:6d}, {dstar:.6e}, {err:.6e}, {sampling_bd:.6e}, {log10_trunc_bd:.3f}, {ratio:.6e}")


if __name__ == "__main__":
    main()


