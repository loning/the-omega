import math


def fibonacci_up_to_index(n_max: int) -> list[int]:
    if n_max < 1:
        return []
    if n_max == 1:
        return [1]
    f = [1, 1]
    while len(f) < n_max:
        f.append(f[-1] + f[-2])
    return f


def rotation_points(alpha: float, n: int, x0: float = 0.0) -> list[float]:
    pts: list[float] = []
    x = x0 % 1.0
    for _ in range(n):
        pts.append(x)
        x = (x + alpha) % 1.0
    return pts


def star_discrepancy(points: list[float]) -> float:
    n = len(points)
    xs = sorted(points)
    d_plus = max(((i + 1) / n - xs[i]) for i in range(n))
    d_minus = max((xs[i] - i / n) for i in range(n))
    return max(d_plus, d_minus)


def main() -> None:
    phi = (1.0 + 5.0**0.5) / 2.0
    alpha = 1.0 / phi
    c_limit = 1.0 + 1.0 / math.sqrt(5.0)

    fib = fibonacci_up_to_index(16)

    print("n,F_n,D*,F_n D*,F_n D*-(1+1/sqrt(5))")
    for n in range(3, 17):
        fn = fib[n - 1]
        d = star_discrepancy(rotation_points(alpha, fn))
        nd = fn * d
        err = nd - c_limit
        print(f"{n},{fn},{d:.12f},{nd:.12f},{err:.12e}")


if __name__ == "__main__":
    main()


