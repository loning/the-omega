import math


def gauss_step(x: float) -> tuple[int, float]:
    # One step of the Gauss map: x in (0,1) -> (a, new_x), where a is a CF digit.
    a = int(1.0 / x)
    return a, (1.0 / x) - a


def gauss_digit_prob(k: int) -> float:
    # P(a1=k) under Gauss measure: log_2(1 + 1/(k(k+2))).
    return math.log(1.0 + 1.0 / (k * (k + 2.0)), 2.0)


def run_fit(x0: float, burn_in: int, n: int, k_max: int) -> tuple[float, float, float]:
    # Returns (l1_error, linf_error, tail_error) for digits 1..k_max and tail > k_max.
    counts = [0] * (k_max + 2)  # 1..k_max in-place, index k_max+1 used for tail

    x = x0
    for _ in range(burn_in):
        _, x = gauss_step(x)

    for _ in range(n):
        a, x = gauss_step(x)
        if 1 <= a <= k_max:
            counts[a] += 1
        else:
            counts[k_max + 1] += 1

    # empirical
    phat = [0.0] * (k_max + 2)
    for k in range(1, k_max + 2):
        phat[k] = counts[k] / n

    # theoretical
    p = [0.0] * (k_max + 2)
    for k in range(1, k_max + 1):
        p[k] = gauss_digit_prob(k)
    p[k_max + 1] = 1.0 - sum(p[1 : k_max + 1])

    l1 = sum(abs(phat[k] - p[k]) for k in range(1, k_max + 2))
    linf = max(abs(phat[k] - p[k]) for k in range(1, k_max + 2))
    tail_err = abs(phat[k_max + 1] - p[k_max + 1])
    return l1, linf, tail_err


def main() -> None:
    # Deterministic seed: sqrt(2)-1 has an eventually periodic CF digits (all 2),
    # which is NOT typical for Gauss measure. So we use an irrational with nontrivial digits:
    # sqrt(3)-1 is also quadratic; instead, use pi fractional part to avoid periodic CF.
    x0 = math.modf(math.pi)[0]
    if x0 <= 0.0:
        x0 = math.sqrt(2.0) - 1.0

    burn_in = 2000
    k_max = 10
    ns = [10_000, 100_000, 1_000_000]

    print("N,kmax,L1_error,Linf_error,tail_error")
    for n in ns:
        l1, linf, tail = run_fit(x0, burn_in, n, k_max)
        print(f"{n},{k_max},{l1:.6e},{linf:.6e},{tail:.6e}")


if __name__ == "__main__":
    main()


