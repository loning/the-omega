import math


def ramanujan_tau_up_to(n_max: int) -> list[int]:
    """
    Compute tau(n) for 0 <= n <= n_max from
      Delta(q) = q * prod_{n>=1} (1 - q^n)^24 = sum_{n>=1} tau(n) q^n,
    truncated to q^{n_max}.
    """
    a = [1] + [0] * n_max  # coefficients for prod_{n>=1} (1 - q^n)^24

    for n in range(1, n_max + 1):
        # (1 - q^n)^24 = sum_{k=0}^{24} (-1)^k * C(24,k) * q^{n k}
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


def main() -> None:
    n_max = 60
    tau = ramanujan_tau_up_to(n_max)
    ps = primes_upto(n_max)

    print("p,tau(p),abs(tau(p))/(2*p^(11/2))")
    max_ratio = 0.0
    max_p = None
    for p in ps:
        tp = tau[p]
        ratio = abs(tp) / (2.0 * (p ** (11 / 2)))
        if ratio > max_ratio:
            max_ratio = ratio
            max_p = p
        print(f"{p},{tp},{ratio:.6f}")

    print(f"max_ratio={max_ratio:.6f} at p={max_p}")


if __name__ == "__main__":
    main()


