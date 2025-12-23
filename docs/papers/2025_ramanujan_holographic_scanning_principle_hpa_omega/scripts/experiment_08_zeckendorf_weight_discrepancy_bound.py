import math


def fibonacci_basis_up_to(n: int) -> list[int]:
    """
    Fibonacci numbers for Zeckendorf representation using F_2=1, F_3=2, ...
    Returns an increasing list including the first term > n.
    """
    fib = [1, 2]
    while fib[-1] <= n:
        fib.append(fib[-1] + fib[-2])
    return fib


def zeckendorf_weight(n: int) -> int:
    """
    Zeckendorf weight (number of Fibonacci summands) via greedy decomposition.
    """
    if n <= 0:
        return 0
    fib = fibonacci_basis_up_to(n)
    w = 0
    i = len(fib) - 1
    remaining = n
    while remaining > 0 and i >= 0:
        while i >= 0 and fib[i] > remaining:
            i -= 1
        if i < 0:
            break
        remaining -= fib[i]
        w += 1
        i -= 2  # enforce non-adjacent Fibonacci summands
    return w


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
    alpha = 1.0 / phi  # golden branch

    # Representative N values (includes a Fibonacci N=1597 with w_Z=1).
    ns = [50, 100, 500, 1000, 1597, 2000, 4000, 8000, 12816]

    print("N,wZ,D,2wZ/N,ratio,D*N")
    for n in ns:
        w = zeckendorf_weight(n)
        d = star_discrepancy(rotation_points(alpha, n))
        bound = 2.0 * w / n
        ratio = d / bound if bound > 0 else float("inf")
        print(f"{n},{w},{d:.12f},{bound:.12f},{ratio:.6f},{n*d:.6f}")


if __name__ == "__main__":
    main()


