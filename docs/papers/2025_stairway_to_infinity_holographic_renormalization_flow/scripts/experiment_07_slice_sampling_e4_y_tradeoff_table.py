import cmath
import math


ZETA3 = 1.2020569031595942854


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


def e4_coeffs(n_terms: int) -> list[int]:
    """
    Return the truncation coefficients for E4(tau)=sum_{n=0..n_terms} a_n q^n with a_0=1.
    """
    sig3 = sigma_k_table(n_terms, 3)
    coeffs = [0] * (n_terms + 1)
    coeffs[0] = 1
    for n in range(1, n_terms + 1):
        coeffs[n] = 240 * sig3[n]
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


def poly_sum_n3(r: float) -> float:
    # sum_{k>=1} k^3 r^k = r(1+4r+r^2)/(1-r)^4
    if r <= 0.0:
        return 0.0
    den = (1.0 - r) ** 4
    return (r * (1.0 + 4.0 * r + r * r)) / den


def poly_sum_n4(r: float) -> float:
    # sum_{k>=1} k^4 r^k = r(1+11r+11r^2+r^3)/(1-r)^5
    if r <= 0.0:
        return 0.0
    den = (1.0 - r) ** 5
    return (r * (1.0 + 11.0 * r + 11.0 * r * r + r**3)) / den


def sum_tail_n3(r: float, n0: int) -> float:
    """
    Bound sum_{k>=n0} k^3 r^k in closed form.
    We expand (n0+m)^3 and sum m^j r^m for j=0..3.
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
    return (r**n0) * (a**3 * s0 + 3.0 * a**2 * s1 + 3.0 * a * s2 + s3)


def log10_sum_tail_n3(r: float, n0: int) -> float:
    """
    log10 of the same closed-form bound as sum_tail_n3, computed without forming r**n0
    (avoids floating underflow when n0 is large).
    """
    if not (0.0 < r < 1.0):
        raise ValueError("r must be in (0,1)")
    a = float(n0)
    s0 = 1.0 / (1.0 - r)
    s1 = r / (1.0 - r) ** 2
    s2 = r * (1.0 + r) / (1.0 - r) ** 3
    s3 = r * (1.0 + 4.0 * r + r * r) / (1.0 - r) ** 4
    expr = a**3 * s0 + 3.0 * a**2 * s1 + 3.0 * a * s2 + s3
    return float(n0) * math.log10(r) + math.log10(expr)


def e4_trunc_tail_bound(y: float, n_terms: int) -> float:
    """
    |E4 - E4^{(n_terms)}| <= 240 * zeta(3) * sum_{k>=n_terms+1} k^3 r^k
    with r = exp(-2*pi*y).
    """
    r = math.exp(-2.0 * math.pi * y)
    return 240.0 * ZETA3 * sum_tail_n3(r, n_terms + 1)


def log10_e4_trunc_tail_bound(y: float, n_terms: int) -> float:
    """
    log10 of the bound in e4_trunc_tail_bound, computed in log domain.
    """
    r = math.exp(-2.0 * math.pi * y)
    return math.log10(240.0 * ZETA3) + log10_sum_tail_n3(r, n_terms + 1)


def variation_bound_g_ny_e4(n_coeff: int, y: float) -> float:
    """
    Explicit (safe) bound for Var(g_{n,y}) where
      g_{n,y}(x) = E4(x+iy) * exp(-2*pi*i*n*x).
    Uses sigma_3(k) <= zeta(3)*k^3 and the closed forms of sum k^3 r^k, sum k^4 r^k.
    """
    r = math.exp(-2.0 * math.pi * y)
    s3 = poly_sum_n3(r)
    s4 = poly_sum_n4(r)
    sum_abs_m_c_m = float(n_coeff) + 240.0 * ZETA3 * (s4 + float(n_coeff) * s3)
    return 2.0 * math.pi * sum_abs_m_c_m


def estimate_a_n_e4_from_samples(alpha: float, x0: float, y: float, n_coeff: int, coeffs: list[int], xs: list[float]) -> complex:
    acc = 0.0 + 0j
    for x in xs:
        tau = complex(x, y)
        fy = eisenstein_value_trunc(tau, coeffs)
        acc += fy * cmath.exp(-2j * math.pi * n_coeff * x)
    return math.exp(2.0 * math.pi * n_coeff * y) * (acc / len(xs))


def main() -> None:
    # Golden branch
    phi = (1.0 + 5.0**0.5) / 2.0
    alpha = 1.0 / phi
    x0 = 0.123456789

    n_coeff = 1

    # Fix sample size and truncation depth
    n_samples = 5000
    n_terms = 800
    coeffs = e4_coeffs(n_terms)
    a_n_true = coeffs[n_coeff]

    xs = rotation_points(alpha, n_samples, x0=x0)
    dstar = star_discrepancy(xs)

    ys = [0.4, 0.6, 0.8, 1.0, 1.2]

    print("E4 slice-sampling y-tradeoff (n=1)")
    print(f"alpha=1/phi={alpha:.16f}, x0={x0}, N={n_samples}, D*={dstar:.6e}, n_terms={n_terms}")
    print(f"a_n true = {a_n_true}")
    print("")
    print(" y, |q|, |error|, sampling_bound, log10_trunc_bound, ratio")

    for y in ys:
        r = math.exp(-2.0 * math.pi * y)
        a_hat = estimate_a_n_e4_from_samples(alpha, x0, y, n_coeff, coeffs, xs)
        err = abs(a_hat - a_n_true)

        var_bd = variation_bound_g_ny_e4(n_coeff=n_coeff, y=y)
        sampling_bd = math.exp(2.0 * math.pi * n_coeff * y) * var_bd * dstar

        log10_trunc_bd = (2.0 * math.pi * n_coeff * y) / math.log(10.0) + log10_e4_trunc_tail_bound(y=y, n_terms=n_terms)
        # materialize trunc bound only if it is representable in float
        trunc_bd = 0.0
        if log10_trunc_bd > -300.0:
            trunc_bd = 10.0 ** log10_trunc_bd
        total_bd = sampling_bd + trunc_bd

        ratio = err / total_bd if total_bd > 0 else float("nan")

        print(f"{y:4.1f}, {r:.3e}, {err:.6e}, {sampling_bd:.6e}, {log10_trunc_bd:.3f}, {ratio:.6e}")


if __name__ == "__main__":
    main()


