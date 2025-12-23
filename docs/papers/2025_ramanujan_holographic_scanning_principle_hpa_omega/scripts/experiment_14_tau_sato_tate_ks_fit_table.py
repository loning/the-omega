import math


def primes_upto(n: int) -> list[int]:
    sieve = [True] * (n + 1)
    if n >= 0:
        sieve[0] = False
    if n >= 1:
        sieve[1] = False
    for p in range(2, int(n**0.5) + 1):
        if sieve[p]:
            step = p
            start = p * p
            sieve[start : n + 1 : step] = [False] * (((n - start) // step) + 1)
    return [i for i, v in enumerate(sieve) if v]


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


def tau_up_to(n_max: int) -> list[int]:
    """
    Compute Ramanujan tau(n) for 0 <= n <= n_max using
      Delta = (E4^3 - E6^2)/1728,
    where
      E4 = 1 + 240 * sum_{n>=1} sigma_3(n) q^n,
      E6 = 1 - 504 * sum_{n>=1} sigma_5(n) q^n.
    """
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

    tau = [0] * (n_max + 1)
    tau[0] = 0
    for n in range(1, n_max + 1):
        num = e4_cu[n] - e6_sq[n]
        if num % 1728 != 0:
            raise ValueError(f"non-integral Delta coefficient at n={n}: {num}/1728")
        tau[n] = num // 1728
    return tau


def semicircle_cdf(x: float) -> float:
    # Sato–Tate semicircle on [-1,1]: density (2/pi)*sqrt(1-x^2).
    if x <= -1.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    return 0.5 + (math.asin(x) + x * math.sqrt(1.0 - x * x)) / math.pi


def ks_distance(values: list[float]) -> float:
    xs = sorted(values)
    n = len(xs)
    ks = 0.0
    for i, x in enumerate(xs, start=1):
        fn = i / n
        f = semicircle_cdf(x)
        d = abs(fn - f)
        if d > ks:
            ks = d
        # also check left-limit (i-1)/n
        fn_left = (i - 1) / n
        d2 = abs(fn_left - f)
        if d2 > ks:
            ks = d2
    return ks


def dkw_eps(alpha: float, n: int) -> float:
    # P(KS > eps) <= 2 exp(-2 n eps^2) => eps = sqrt(log(2/alpha)/(2n))
    return math.sqrt(math.log(2.0 / alpha) / (2.0 * n))


def main() -> None:
    p_max_list = [59, 199, 499, 999, 1999]
    n_max = max(p_max_list)

    tau = tau_up_to(n_max)

    print("pmax,pi(pmax),ks,dkw95")
    for pmax in p_max_list:
        ps = primes_upto(pmax)
        vals = [tau[p] / (2.0 * (p ** (11 / 2))) for p in ps]
        ks = ks_distance(vals)
        eps95 = dkw_eps(0.05, len(vals))
        print(f"{pmax},{len(ps)},{ks:.8e},{eps95:.8e}")


if __name__ == "__main__":
    main()


