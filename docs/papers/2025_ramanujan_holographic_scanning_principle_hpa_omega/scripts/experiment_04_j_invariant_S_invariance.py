import cmath
import math


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
    # E4(tau) = 1 + 240 * sum_{n>=1} sigma_3(n) q^n
    a = [0] * (n_max + 1)
    a[0] = 1
    for n in range(1, n_max + 1):
        a[n] = 240 * sigma_k(n, 3)
    return a


def e6_coeffs(n_max: int) -> list[int]:
    # E6(tau) = 1 - 504 * sum_{n>=1} sigma_5(n) q^n
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


def j_invariant(tau: complex, n_terms: int = 80) -> complex:
    q = cmath.exp(2j * math.pi * tau)
    e4 = qseries_eval(e4_coeffs(n_terms), q)
    e6 = qseries_eval(e6_coeffs(n_terms), q)
    return 1728.0 * (e4**3) / (e4**3 - e6**2)


def main() -> None:
    tau = 0.3 + 0.9j
    j1 = j_invariant(tau, 80)
    j2 = j_invariant(-1.0 / tau, 80)

    print("tau       =", tau)
    print("j(tau)    =", j1)
    print("j(-1/tau) =", j2)
    print("|diff|    =", abs(j1 - j2))


if __name__ == "__main__":
    main()


