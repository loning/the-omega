import math


def sigma_k_sieve(n_max: int, k: int) -> list[int]:
    sig = [0] * (n_max + 1)
    for d in range(1, n_max + 1):
        dk = d**k
        for m in range(d, n_max + 1, d):
            sig[m] += dk
    return sig


def convolve_trunc(a: list[int], b: list[int], n_max: int) -> list[int]:
    res = [0] * (n_max + 1)
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        j_max = min(n_max - i, len(b) - 1)
        for j in range(j_max + 1):
            bj = b[j]
            if bj:
                res[i + j] += ai * bj
    return res


def series_divide_unit(a: list[int], b: list[int], n_max: int) -> list[int]:
    """
    Compute c = a / b as power series up to q^n_max, assuming b[0] == 1 and all are integers.
    """
    if b[0] != 1:
        raise ValueError("denominator must have constant term 1")
    c = [0] * (n_max + 1)
    c[0] = a[0]
    for n in range(1, n_max + 1):
        s = a[n]
        for k in range(1, n + 1):
            s -= b[k] * c[n - k]
        c[n] = s
    return c


def main() -> None:
    # We will compute series up to q^n_max, and then print a few leading coefficients.
    n_max = 10

    s3 = sigma_k_sieve(n_max, 3)
    s5 = sigma_k_sieve(n_max, 5)

    e4 = [0] * (n_max + 1)
    e6 = [0] * (n_max + 1)
    e4[0] = 1
    e6[0] = 1
    for n in range(1, n_max + 1):
        e4[n] = 240 * s3[n]
        e6[n] = -504 * s5[n]

    e4_sq = convolve_trunc(e4, e4, n_max)
    e4_cu = convolve_trunc(e4_sq, e4, n_max)
    e6_sq = convolve_trunc(e6, e6, n_max)

    # Delta = (E4^3 - E6^2)/1728
    delta = [0] * (n_max + 1)
    ok = True
    for n in range(0, n_max + 1):
        num = e4_cu[n] - e6_sq[n]
        if num % 1728 != 0:
            ok = False
        delta[n] = num // 1728

    # j = E4^3 / Delta = q^{-1} * E4^3 / (Delta/q)
    if delta[0] != 0 or delta[1] != 1:
        raise ValueError("unexpected Delta leading terms; expected Delta = q + ...")
    delta1 = [0] * (n_max + 1)
    # delta(q) = q * delta1(q), so delta1[n] = delta[n+1]
    for n in range(0, n_max):
        delta1[n] = delta[n + 1]
    delta1[n_max] = 0

    d = series_divide_unit(e4_cu, delta1, n_max)  # d(q) = E4^3 / delta1
    # Then j(q) = q^{-1} d(q) = q^{-1} + d[1] + d[2] q + ...

    known_j = {
        -1: 1,
        0: 744,
        1: 196884,
        2: 21493760,
        3: 864299970,
        4: 20245856256,
        5: 333202640600,
    }

    print("check,e4^3_minus_e6^2_divisible_by_1728,", ok)
    print("check,Delta_q_coeff_1,", delta[1])
    print("n,E4_n,E6_n,Delta_n")
    for n in range(0, 6):
        print(f"{n},{e4[n]},{e6[n]},{delta[n]}")

    print("j_power,computed,known,match")
    # print j terms from q^{-1} through q^5
    for p in range(-1, 6):
        if p == -1:
            comp = d[0]
        else:
            comp = d[p + 1]
        kn = known_j[p]
        print(f"{p},{comp},{kn},{comp==kn}")


if __name__ == "__main__":
    main()


