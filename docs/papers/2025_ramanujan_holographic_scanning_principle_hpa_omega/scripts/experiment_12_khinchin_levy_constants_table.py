import math
import random


KHINCHIN_CONST = 2.6854520010
LEVY_CONST = (math.pi**2) / (12.0 * math.log(2.0))


def sample_gauss_measure(rng: random.Random) -> float:
    # Gauss measure on (0,1): dmu(x) = (1/log 2) * dx/(1+x).
    # CDF is F(x)=log_2(1+x), so inverse is x=2^U - 1.
    u = rng.random()
    x = (2.0**u) - 1.0
    # x is in (0,1) except for the measure-zero endpoints.
    if x <= 0.0:
        x = 0.5
    if x >= 1.0:
        x = 0.5
    return x


def cf_digit_step(x: float) -> tuple[int, float]:
    a = int(1.0 / x)
    return a, (1.0 / x) - a


def estimate_constants_one(x0: float, n: int) -> tuple[float, float]:
    # Returns (levy_est, khinchin_est) from first n digits of x0.
    x = x0
    log_prod_a = 0.0

    q_nm2 = 0  # q_{-1}
    q_nm1 = 1  # q_0

    for _ in range(n):
        a, x = cf_digit_step(x)
        log_prod_a += math.log(a)
        q_n = a * q_nm1 + q_nm2
        q_nm2, q_nm1 = q_nm1, q_n

    levy_est = math.log(q_nm1) / n
    khinchin_est = math.exp(log_prod_a / n)
    return levy_est, khinchin_est


def mean_std(xs: list[float]) -> tuple[float, float]:
    m = sum(xs) / len(xs)
    v = sum((x - m) ** 2 for x in xs) / (len(xs) - 1) if len(xs) > 1 else 0.0
    return m, math.sqrt(v)


def main() -> None:
    rng = random.Random(0)
    sample_count = 50
    ns = [200, 500, 1000, 2000]

    print("n,samples,levy_mean,levy_std,levy_err,khinchin_mean,khinchin_std,khinchin_err")
    for n in ns:
        levy_vals: list[float] = []
        kh_vals: list[float] = []
        for _ in range(sample_count):
            x0 = sample_gauss_measure(rng)
            levy_est, kh_est = estimate_constants_one(x0, n)
            levy_vals.append(levy_est)
            kh_vals.append(kh_est)

        levy_mean, levy_std = mean_std(levy_vals)
        kh_mean, kh_std = mean_std(kh_vals)

        print(
            f"{n},{sample_count},"
            f"{levy_mean:.8f},{levy_std:.8f},{(levy_mean-LEVY_CONST):+.3e},"
            f"{kh_mean:.8f},{kh_std:.8f},{(kh_mean-KHINCHIN_CONST):+.3e}"
        )


if __name__ == "__main__":
    main()


