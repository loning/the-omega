import math
import random


def gauss_step(x: float) -> float:
    # Gauss map G(x) = {1/x} for x in (0,1)
    a = int(1.0 / x)
    y = (1.0 / x) - a
    # avoid exact 0 in floating arithmetic
    if y == 0.0:
        y = 0.5
    return y


def roof(x: float) -> float:
    # r(x) = -2 log x
    return -2.0 * math.log(x)


def orbit_means(x0: float, burn: int, ns: list[int]) -> dict[int, float]:
    x = x0
    for _ in range(burn):
        x = gauss_step(x)
    s = 0.0
    out: dict[int, float] = {}
    targets = set(ns)
    max_n = max(ns)
    for i in range(1, max_n + 1):
        x = gauss_step(x)
        s += roof(x)
        if i in targets:
            out[i] = s / i
    return out


def mean_std(vals: list[float]) -> tuple[float, float]:
    n = len(vals)
    if n <= 0:
        raise ValueError("empty vals")
    m = sum(vals) / n
    if n == 1:
        return m, 0.0
    v = sum((x - m) * (x - m) for x in vals) / (n - 1)
    return m, math.sqrt(v)


def main() -> None:
    # Theoretical mean under Gauss invariant measure:
    # E[r] = pi^2 / (6 log 2).
    mu = (math.pi * math.pi) / (6.0 * math.log(2.0))

    rng = random.Random(0)
    burn = 2000
    n_orbits = 20
    x0s = [rng.random() for _ in range(n_orbits)]

    ns = [10_000, 50_000, 100_000, 300_000, 1_000_000]

    orbits: list[dict[int, float]] = [orbit_means(x0=x0, burn=burn, ns=ns) for x0 in x0s]

    print("N, mean_over_orbits, std_over_orbits, theo_mean, abs_error, rel_error, max_abs_error")
    for n in ns:
        vals = [orb[n] for orb in orbits]
        m, s = mean_std(vals)
        abs_err = abs(m - mu)
        rel_err = abs_err / mu
        max_abs_err = max(abs(v - mu) for v in vals)
        print(f"{n},{m:.12e},{s:.12e},{mu:.12e},{abs_err:.12e},{rel_err:.12e},{max_abs_err:.12e}")


if __name__ == "__main__":
    main()


