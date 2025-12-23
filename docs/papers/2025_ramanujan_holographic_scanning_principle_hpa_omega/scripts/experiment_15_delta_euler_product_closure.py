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
    with truncated q-expansions at depth n_max.
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


def dirichlet_partial_sum(tau: list[int], n_max: int, s: float) -> float:
    return sum(tau[n] / (n**s) for n in range(1, n_max + 1))


def euler_partial_product(tau: list[int], p_max: int, s: float) -> float:
    ps = primes_upto(p_max)
    prod = 1.0
    for p in ps:
        a_p = tau[p]
        prod *= 1.0 / (1.0 - a_p * (p**(-s)) + (p ** (11 - 2 * s)))
    return prod


def main() -> None:
    # Choose s > 13/2 so that L(Delta,s) converges absolutely.
    s = 10.0
    cutoffs = [50, 100, 200, 500, 1000, 2000]
    n_max = max(cutoffs)

    tau = tau_up_to(n_max)

    print("s,N,pi(N),dirichlet_sum,euler_product,abs_diff,rel_diff")
    for n in cutoffs:
        S = dirichlet_partial_sum(tau, n, s)
        P = euler_partial_product(tau, n, s)
        abs_diff = abs(P - S)
        rel_diff = abs_diff / abs(S) if S != 0.0 else float("inf")
        pi_n = len(primes_upto(n))
        print(f"{s:.1f},{n},{pi_n},{S:.15f},{P:.15f},{abs_diff:.3e},{rel_diff:.3e}")


if __name__ == "__main__":
    main()


