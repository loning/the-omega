import cmath
import math


ZETA3 = 1.2020569031595942854
ZETA5 = 1.0369277551433699263


def sigma_k(n: int, k: int) -> int:
    s = 0
    r = int(math.isqrt(n))
    for d in range(1, r + 1):
        if n % d == 0:
            s += d**k
            e = n // d
            if e != d:
                s += e**k
    return s


def e4_coeffs(n_max: int) -> list[int]:
    a = [0] * (n_max + 1)
    a[0] = 1
    for n in range(1, n_max + 1):
        a[n] = 240 * sigma_k(n, 3)
    return a


def e6_coeffs(n_max: int) -> list[int]:
    a = [0] * (n_max + 1)
    a[0] = 1
    for n in range(1, n_max + 1):
        a[n] = -504 * sigma_k(n, 5)
    return a


def qseries_eval(coeffs: list[int], q: complex) -> complex:
    s: complex = 0.0 + 0.0j
    qp: complex = 1.0 + 0.0j
    for c in coeffs:
        s += c * qp
        qp *= q
    return s


def j_invariant(tau: complex, n_terms: int) -> complex:
    q = cmath.exp(2j * math.pi * tau)
    e4 = qseries_eval(e4_coeffs(n_terms), q)
    e6 = qseries_eval(e6_coeffs(n_terms), q)
    return 1728.0 * (e4**3) / (e4**3 - e6**2)


def tail_sum_power(r: float, k: int, n0: int) -> float:
    # sum_{n>n0} n^k r^n
    s = 0.0
    n = n0 + 1
    for _ in range(500_000):
        term = (n**k) * (r**n)
        s += term
        if term < 1e-20:
            break
        n += 1
    return s


def j_truncation_bound(tau: complex, n_terms: int) -> float:
    """
    Certified truncation-only bound for |j(tau) - j^(N)(tau)| using:
    - tail bounds on E4,E6 via sigma_k(n) <= zeta(k) n^k,
    - denominator separation using computed D^(N)=E4^(N)^3 - E6^(N)^2.
    """
    q = cmath.exp(2j * math.pi * tau)
    r = abs(q)

    e4n = qseries_eval(e4_coeffs(n_terms), q)
    e6n = qseries_eval(e6_coeffs(n_terms), q)

    eps4 = 240.0 * ZETA3 * tail_sum_power(r, 3, n_terms)
    eps6 = 504.0 * ZETA5 * tail_sum_power(r, 5, n_terms)

    m4 = abs(e4n) + eps4
    m6 = abs(e6n) + eps6

    dn = e4n**3 - e6n**2
    delta_d = 3.0 * (m4**2) * eps4 + 2.0 * m6 * eps6
    d_min = abs(dn) - delta_d

    if d_min <= 0:
        return float("inf")

    delta_e4cube = 3.0 * (m4**2) * eps4
    inv_diff = delta_d / (d_min * abs(dn))

    return 1728.0 * (delta_e4cube / d_min + abs(e4n**3) * inv_diff)


def main() -> None:
    tau = 0.3 + 0.2j
    print("tau =", tau)
    print("N,diff_abs,trunc_bound_abs")

    for n_terms in (10, 20, 30, 40, 60):
        j1 = j_invariant(tau, n_terms)
        j2 = j_invariant(-1.0 / tau, n_terms)
        diff = abs(j1 - j2)

        b1 = j_truncation_bound(tau, n_terms)
        b2 = j_truncation_bound(-1.0 / tau, n_terms)
        bound = b1 + b2

        print(f\"{n_terms},{diff:.16e},{bound:.16e}\")


if __name__ == \"__main__\":
    main()


