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


def catalan(n: int) -> int:
    return math.comb(2 * n, n) // (n + 1)


def sato_tate_even_moment(k: int) -> float:
    if k % 2 != 0:
        raise ValueError("moment order must be even")
    n = k // 2
    return catalan(n) / (4.0**n)


def moments(values: list[float], orders: list[int]) -> dict[int, float]:
    m = len(values)
    return {k: sum(v**k for v in values) / m for k in orders}


def main() -> None:
    # Representative cutoffs for primes.
    p_max_list = [59, 199, 499, 999, 1999]
    n_max = max(p_max_list)

    tau = tau_up_to(n_max)

    theo = {k: sato_tate_even_moment(k) for k in (2, 4, 6, 8)}

    print("pmax,pi(pmax),mean,m2,m4,m6,m8,err2,err4,err6,err8")
    for pmax in p_max_list:
        ps = primes_upto(pmax)
        vals = [tau[p] / (2.0 * (p ** (11 / 2))) for p in ps]

        mu = sum(vals) / len(vals)
        ms = moments(vals, [2, 4, 6, 8])
        err = {k: ms[k] - theo[k] for k in theo}

        print(
            f"{pmax},{len(ps)},{mu:.6e},"
            f"{ms[2]:.6e},{ms[4]:.6e},{ms[6]:.6e},{ms[8]:.6e},"
            f"{err[2]:.6e},{err[4]:.6e},{err[6]:.6e},{err[8]:.6e}"
        )


if __name__ == "__main__":
    main()


