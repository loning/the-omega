from __future__ import annotations

import math
from functools import lru_cache
from typing import Iterable, Optional


def golden_ratio() -> float:
    return (1.0 + 5.0**0.5) / 2.0


def golden_alpha() -> float:
    return 1.0 / golden_ratio()


def rotation_orbit(alpha: float, n: int, x0: float = 0.0) -> "list[float]":
    import numpy as np

    t = np.arange(n, dtype=float)
    xs = (x0 + alpha * t) % 1.0
    return xs.tolist()


def star_discrepancy_1d(points: Iterable[float]) -> float:
    xs = sorted(points)
    n = len(xs)
    if n == 0:
        return 0.0
    d_plus = max(((i + 1) / n - xs[i]) for i in range(n))
    d_minus = max((xs[i] - i / n) for i in range(n))
    return max(d_plus, d_minus)


def fibonacci_word(n: int) -> str:
    # Prefix of the Fibonacci fixed point under the substitution 0 -> 01, 1 -> 0.
    s = "0"
    while len(s) < n:
        s = "".join("01" if ch == "0" else "0" for ch in s)
    return s[:n]


def rotation_word(alpha: float, n: int, x0: float = 0.0, a: float = 0.0, b: Optional[float] = None) -> str:
    # Binary mechanical word s_t = 1_{[a,b)}(x_t) from x_{t+1} = x_t + alpha (mod 1).
    if b is None:
        b = 1.0 - alpha
    out: list[str] = []
    x = x0 % 1.0
    for _ in range(n):
        out.append("1" if (a <= x < b) else "0")
        x = (x + alpha) % 1.0
    return "".join(out)


def primes_upto(n: int) -> list[int]:
    if n < 2:
        return []
    sieve = [True] * (n + 1)
    sieve[0] = False
    sieve[1] = False
    for p in range(2, int(n**0.5) + 1):
        if sieve[p]:
            step = p
            start = p * p
            sieve[start : n + 1 : step] = [False] * (((n - start) // step) + 1)
    return [i for i, v in enumerate(sieve) if v]


def sigma_k_sieve(n_max: int, k: int) -> list[int]:
    sig = [0] * (n_max + 1)
    for d in range(1, n_max + 1):
        dk = d**k
        for m in range(d, n_max + 1, d):
            sig[m] += dk
    return sig


def convolve_trunc(a: list[int], b: list[int], n_max: int) -> list[int]:
    res = [0] * (n_max + 1)
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        j_max = min(n_max - i, len(b) - 1)
        for j in range(j_max + 1):
            bj = b[j]
            if bj:
                res[i + j] += ai * bj
    return res


@lru_cache(maxsize=8)
def tau_up_to(n_max: int) -> tuple[int, ...]:
    # Compute Ramanujan tau(n) for 0 <= n <= n_max using Delta = (E4^3 - E6^2)/1728.
    s3 = sigma_k_sieve(n_max, 3)
    s5 = sigma_k_sieve(n_max, 5)

    e4 = [0] * (n_max + 1)
    e6 = [0] * (n_max + 1)
    e4[0] = 1
    e6[0] = 1
    for n in range(1, n_max + 1):
        e4[n] = 240 * s3[n]
        e6[n] = -504 * s5[n]

    e4_sq = convolve_trunc(e4, e4, n_max)
    e4_cu = convolve_trunc(e4_sq, e4, n_max)
    e6_sq = convolve_trunc(e6, e6, n_max)

    tau = [0] * (n_max + 1)
    tau[0] = 0
    for n in range(1, n_max + 1):
        num = e4_cu[n] - e6_sq[n]
        if num % 1728 != 0:
            raise ValueError(f"non-integral Delta coefficient at n={n}: {num}/1728")
        tau[n] = num // 1728

    return tuple(tau)


def gauss_step(x: float) -> float:
    inv = 1.0 / x
    a = int(inv)
    y = inv - a
    if y == 0.0:
        y = 0.5
    return y


def gauss_digit_prob(k: int) -> float:
    return math.log(1.0 + 1.0 / (k * (k + 2.0)), 2.0)


def roof(x: float) -> float:
    return -2.0 * math.log(x)


def poly_sum_n3(r: float) -> float:
    # sum_{k>=1} k^3 r^k = r(1+4r+r^2)/(1-r)^4
    if r <= 0.0:
        return 0.0
    den = (1.0 - r) ** 4
    return (r * (1.0 + 4.0 * r + r * r)) / den


def poly_sum_n4(r: float) -> float:
    # sum_{k>=1} k^4 r^k = r(1+11r+11r^2+r^3)/(1-r)^5
    if r <= 0.0:
        return 0.0
    den = (1.0 - r) ** 5
    return (r * (1.0 + 11.0 * r + 11.0 * r * r + r**3)) / den


