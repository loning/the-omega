import math


def rotation_points(alpha: float, n: int, x0: float = 0.0) -> list[float]:
    pts: list[float] = []
    x = x0 % 1.0
    for _ in range(n):
        pts.append(x)
        x = (x + alpha) % 1.0
    return pts


def star_discrepancy(points: list[float]) -> float:
    """
    Compute the one-dimensional star discrepancy D*_N for a point set in [0,1).
    """
    n = len(points)
    xs = sorted(points)
    d_plus = max(((i + 1) / n - xs[i]) for i in range(n))
    d_minus = max((xs[i] - i / n) for i in range(n))
    return max(d_plus, d_minus)


def main() -> None:
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    alpha = 1.0 / phi

    for n in [10, 20, 50, 100, 1_000, 10_000, 50_000]:
        d = star_discrepancy(rotation_points(alpha, n))
        print(f"n={n:6d} D*={d:.6e} nD*={n*d:.6f} log n={math.log(n):.6f}")


if __name__ == "__main__":
    main()


