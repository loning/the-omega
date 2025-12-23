from __future__ import annotations

import math


def ramanujan_tau_up_to(n_max: int) -> list[int]:
    """
    Compute tau(n) for 0 <= n <= n_max from
      Delta(q) = q * prod_{n>=1} (1 - q^n)^24 = sum_{n>=1} tau(n) q^n,
    truncated to q^{n_max}.
    """
    a = [1] + [0] * n_max  # coefficients for prod_{n>=1} (1 - q^n)^24

    for n in range(1, n_max + 1):
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


def check_multiplicativity(tau: list[int], m_max: int, n_max: int) -> bool:
    for m in range(1, m_max + 1):
        for n in range(1, n_max + 1):
            mn = m * n
            if mn >= len(tau):
                continue
            if math.gcd(m, n) == 1:
                if tau[mn] != tau[m] * tau[n]:
                    return False
    return True


def check_prime_power_recursion(tau: list[int], p: int, r_max: int) -> list[tuple[int, int, int, int, bool]]:
    """
    For Delta of weight 12: tau(p^{r+1}) = tau(p) tau(p^r) - p^{11} tau(p^{r-1}).
    """
    out: list[tuple[int, int, int, int, bool]] = []
    for r in range(1, r_max + 1):
        n1 = p ** (r + 1)
        if n1 >= len(tau):
            break
        lhs = tau[n1]
        rhs = tau[p] * tau[p**r] - (p**11) * tau[p ** (r - 1)]
        out.append((p, r, lhs, rhs, lhs == rhs))
    return out


def main() -> None:
    n_max = 60
    tau = ramanujan_tau_up_to(n_max)

    print("tau(1..10) =", [tau[i] for i in range(1, 11)])
    print("multiplicative on coprime pairs (<=30)?", check_multiplicativity(tau, 30, 30))

    for p in (2, 3, 5):
        for (p, r, lhs, rhs, ok) in check_prime_power_recursion(tau, p, 6):
            print(f"p={p} r={r} lhs={lhs} rhs={rhs} ok={ok}")


if __name__ == "__main__":
    main()


