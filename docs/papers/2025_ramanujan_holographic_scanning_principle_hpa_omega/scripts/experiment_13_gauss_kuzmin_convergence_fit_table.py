import math
import random


def gauss_cdf(x: float) -> float:
    # F(x) = mu((0,x]) for the Gauss invariant measure.
    return math.log1p(x) / math.log(2.0)


def gauss_step(x: float, eps: float = 2.0**-52) -> float:
    # Gauss map G(x) = {1/x}. For rational points, floating arithmetic can land on 0;
    # we jitter by eps (measure-zero event in the continuum model).
    inv = 1.0 / x
    a = int(inv)
    y = inv - a
    if y == 0.0:
        y = eps
    return y


def ks_distance_to_gauss(xs: list[float]) -> float:
    # Kolmogorov–Smirnov distance between the empirical CDF of xs and the Gauss CDF.
    xs_sorted = sorted(xs)
    n = len(xs_sorted)
    ks = 0.0
    for i, x in enumerate(xs_sorted, start=1):
        emp = i / n
        th = gauss_cdf(x)
        d = abs(emp - th)
        if d > ks:
            ks = d
    return ks


def linreg(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    # returns (slope, intercept, r2)
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx if sxx != 0.0 else 0.0
    intercept = my - slope * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot != 0.0 else 1.0
    return slope, intercept, r2


def main() -> None:
    rng = random.Random(0)
    sample_count = 200_000
    max_iter = 10

    xs = [rng.random() for _ in range(sample_count)]
    for i, x in enumerate(xs):
        if x == 0.0:
            xs[i] = 2.0**-52

    ks_vals: list[float] = []
    for n in range(max_iter + 1):
        ks = ks_distance_to_gauss(xs)
        ks_vals.append(ks)
        xs = [gauss_step(x) for x in xs]

    # Fit log(ks_n) ~ a + n log(lambda) on an early window above sampling noise.
    # This is a toy fit (not intended to estimate the optimal Wirsing constant).
    fit_n_min = 0
    fit_n_max = 4
    fit_ns = list(range(fit_n_min, min(fit_n_max, max_iter) + 1))
    fit_logs = [math.log(ks_vals[n]) for n in fit_ns]
    slope, intercept, r2 = linreg([float(n) for n in fit_ns], fit_logs)
    lambda_fit = math.exp(slope)

    # DKW–Massart 95% benchmark for the KS statistic of an i.i.d. sample of size N.
    # eps_95 = sqrt(log(2/0.05)/(2N)).
    eps95 = math.sqrt(math.log(2.0 / 0.05) / (2.0 * sample_count))

    print("samples,max_iter,fit_n_min,fit_n_max,lambda_fit,r2,dkw95")
    print(
        f"{sample_count},{max_iter},{min(fit_ns)},{max(fit_ns)},{lambda_fit:.8f},{r2:.6f},{eps95:.8e}"
    )
    print("n,ks_distance,log_ks")
    for n, ks in enumerate(ks_vals):
        log_ks = math.log(ks) if ks > 0.0 else float("-inf")
        print(f"{n},{ks:.8e},{log_ks:.8f}")


if __name__ == "__main__":
    main()


