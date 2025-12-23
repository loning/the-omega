import cmath
import math


ZETA3 = 1.2020569031595942854
ZETA5 = 1.0369277551433699263


def sigma_k(n: int, k: int) -> int:
    s = 0
    r = int(n**0.5)
    for d in range(1, r + 1):
        if n % d == 0:
            s += d**k
            e = n // d
            if e != d:
                s += e**k
    return s


def e4_e6_trunc(tau: complex, n_terms: int) -> tuple[complex, complex]:
    """
    E4(tau) = 1 + 240 * sum_{n>=1} sigma_3(n) q^n
    E6(tau) = 1 - 504 * sum_{n>=1} sigma_5(n) q^n
    """
    q = cmath.exp(2j * math.pi * tau)
    e4 = 1.0 + 0j
    e6 = 1.0 + 0j
    qn = q
    for n in range(1, n_terms + 1):
        e4 += 240 * sigma_k(n, 3) * qn
        e6 += -504 * sigma_k(n, 5) * qn
        qn *= q
    return e4, e6


def sum_m0(r: float) -> float:
    return 1.0 / (1.0 - r)


def sum_m1(r: float) -> float:
    return r / (1.0 - r) ** 2


def sum_m2(r: float) -> float:
    return r * (1.0 + r) / (1.0 - r) ** 3


def sum_m3(r: float) -> float:
    return r * (1.0 + 4.0 * r + r * r) / (1.0 - r) ** 4


def sum_m4(r: float) -> float:
    return r * (1.0 + 11.0 * r + 11.0 * r * r + r**3) / (1.0 - r) ** 5


def sum_m5(r: float) -> float:
    return r * (1.0 + 26.0 * r + 66.0 * r * r + 26.0 * r**3 + r**4) / (1.0 - r) ** 6


def tail_n3(r: float, n0: int) -> float:
    """
    sum_{n>=n0} n^3 r^n = r^{n0} * sum_{m>=0} (n0+m)^3 r^m
    """
    a = float(n0)
    return (r**n0) * (a**3 * sum_m0(r) + 3.0 * a**2 * sum_m1(r) + 3.0 * a * sum_m2(r) + sum_m3(r))


def tail_n5(r: float, n0: int) -> float:
    """
    sum_{n>=n0} n^5 r^n = r^{n0} * sum_{m>=0} (n0+m)^5 r^m
    """
    a = float(n0)
    return (r**n0) * (
        a**5 * sum_m0(r)
        + 5.0 * a**4 * sum_m1(r)
        + 10.0 * a**3 * sum_m2(r)
        + 10.0 * a**2 * sum_m3(r)
        + 5.0 * a * sum_m4(r)
        + sum_m5(r)
    )


def e4_tail_bound(y: float, n_terms: int) -> float:
    r = math.exp(-2.0 * math.pi * y)
    # sigma_3(n) <= zeta(3) n^3
    return 240.0 * ZETA3 * tail_n3(r, n_terms + 1)


def e6_tail_bound(y: float, n_terms: int) -> float:
    r = math.exp(-2.0 * math.pi * y)
    # sigma_5(n) <= zeta(5) n^5
    return 504.0 * ZETA5 * tail_n5(r, n_terms + 1)


def j_from_e4_e6(e4: complex, e6: complex) -> complex:
    num = e4**3
    den = (e4**3 - e6**2)
    return 1728.0 * num / den


def j_trunc_and_bound(tau: complex, n_terms: int) -> tuple[complex, float]:
    """
    Returns (j_trunc, certified_bound) where certified_bound is an upper bound on
    |j_true(tau) - j_trunc(tau)| induced by truncating E4,E6 at n_terms.

    We use:
      E4 = E4h + d4,  |d4| <= b4
      E6 = E6h + d6,  |d6| <= b6
    Propagate to A=E4^3, B=E6^2, D=A-B, j=1728 A/D with explicit algebraic bounds.
    """
    y = float(tau.imag)
    if y <= 0.0:
        raise ValueError("tau must be in the upper half-plane (Im(tau)>0)")

    e4h, e6h = e4_e6_trunc(tau, n_terms)
    b4 = e4_tail_bound(y, n_terms)
    b6 = e6_tail_bound(y, n_terms)

    # Bounds for A=E4^3
    # |A - Ah| = |(e4h+d4)^3 - e4h^3| <= 3|e4h|^2 b4 + 3|e4h| b4^2 + b4^3
    abs_e4h = abs(e4h)
    abs_e6h = abs(e6h)
    bA = 3.0 * (abs_e4h**2) * b4 + 3.0 * abs_e4h * (b4**2) + (b4**3)

    # Bounds for B=E6^2
    # |B - Bh| <= 2|e6h| b6 + b6^2
    bB = 2.0 * abs_e6h * b6 + (b6**2)

    Ah = e4h**3
    Bh = e6h**2
    Dh = Ah - Bh

    # Bound D error
    bD = bA + bB

    # Lower bound on |D| using triangle inequality: |D| >= |Dh| - bD
    abs_Dh = abs(Dh)
    abs_D_lower = abs_Dh - bD
    if abs_D_lower <= 0.0:
        # Not safe to certify; return a huge bound.
        return j_from_e4_e6(e4h, e6h), float("inf")

    # Bound |A| upper: |A| <= |Ah| + bA
    abs_A_upper = abs(Ah) + bA

    # Bound |j_true - j_hat|:
    # j = 1728 A/D, jh = 1728 Ah/Dh
    # Add/subtract: |A/D - Ah/Dh| <= |A-Ah|/|D| + |Ah||D-Dh|/(|D||Dh|)
    # Use |D|>=abs_D_lower, |Dh|=abs_Dh
    term1 = bA / abs_D_lower
    term2 = abs(Ah) * bD / (abs_D_lower * abs_Dh) if abs_Dh > 0 else float("inf")
    bound = 1728.0 * (term1 + term2)

    jh = 1728.0 * Ah / Dh
    return jh, bound


def main() -> None:
    # Choose a point where truncation error bounds remain numerically visible
    # (avoids floating underflow in very deep cusp regimes).
    tau = 0.3 + 0.2j
    tau_s = -1.0 / tau

    n_terms_list = [20, 30, 40]

    print("tau, tau_s")
    print(f"{tau}, {tau_s}")
    print("N,diff,bound_sum,ratio,bound_tau,bound_tau_s")

    for n_terms in n_terms_list:
        j1, b1 = j_trunc_and_bound(tau, n_terms)
        j2, b2 = j_trunc_and_bound(tau_s, n_terms)
        diff = abs(j1 - j2)

        # Since j(tau)=j(-1/tau) exactly, we can certify:
        # |j1 - j2| <= |j1 - j_true| + |j2 - j_true| <= b1 + b2
        cert = b1 + b2
        ratio = diff / cert if cert > 0 else float("nan")

        print(f"{n_terms},{diff:.12e},{cert:.12e},{ratio:.12e},{b1:.12e},{b2:.12e}")


if __name__ == "__main__":
    main()


