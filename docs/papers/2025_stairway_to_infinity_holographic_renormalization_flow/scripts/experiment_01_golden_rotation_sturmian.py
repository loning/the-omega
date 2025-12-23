import math


def rotation_word(alpha: float, n: int, x0: float = 0.0, a: float = 0.0, b: float | None = None) -> str:
    """
    Generate the binary mechanical word s_t = 1_W(x_t) from x_{t+1} = x_t + alpha (mod 1),
    where W = [a, b). By default, b = 1 - alpha (a common canonical choice).
    """
    if b is None:
        b = 1.0 - alpha
    w: list[str] = []
    x = x0 % 1.0
    for _ in range(n):
        w.append("1" if (a <= x < b) else "0")
        x = (x + alpha) % 1.0
    return "".join(w)


def fibonacci_word(n: int) -> str:
    """
    Prefix of the Fibonacci fixed point under the substitution 0 -> 01, 1 -> 0.
    """
    s = "0"
    while len(s) < n:
        s = "".join("01" if ch == "0" else "0" for ch in s)
    return s[:n]


def empirical_histogram(alpha: float, n: int, k: int, x0: float = 0.0) -> list[float]:
    """
    Histogram of the rotation orbit into k equal bins on [0,1).
    """
    counts = [0] * k
    x = x0 % 1.0
    for _ in range(n):
        idx = int(x * k)
        counts[idx] += 1
        x = (x + alpha) % 1.0
    return [c / n for c in counts]


def main() -> None:
    phi = (1.0 + 5.0 ** 0.5) / 2.0
    alpha = 1.0 / phi  # golden branch alpha = phi^{-1}

    n = 80
    w = rotation_word(alpha, n + 1, x0=0.0)
    fib = fibonacci_word(n)

    print("rotation (drop first) =", w[1 : 1 + n])
    print("fibonacci             =", fib)
    print("match?                =", w[1 : 1 + n] == fib)

    for k in (5, 10, 20):
        probs = empirical_histogram(alpha, 200_000, k)
        max_err = max(abs(p - 1.0 / k) for p in probs)
        print(f"k={k} max|p-1/k|={max_err:.6e}")


if __name__ == "__main__":
    main()


