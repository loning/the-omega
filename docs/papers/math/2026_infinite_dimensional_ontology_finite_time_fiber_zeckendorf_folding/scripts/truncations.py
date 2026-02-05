#!/usr/bin/env python3
"""
Truncation (compression) families for this paper.

We expose a minimal, auditable interface:
  - micro domain S_m is represented by integers 0..n_micro-1
  - space projection returns an X_m word packed into an int (bit i = digit_{i+1}, low-to-high)
  - time residual returns an integer label (auditable time information)

Supported truncations (selected by the user):
  - "zeck_window": micro is b in {0,1}^m (packed as int), space is Zeckendorf window (z2..z_{m+1}),
                  time residual is the single overflow bit u=z_{m+2} (0/1)
  - "dirac_dyadic": micro is N in [0, 2^m-1], space is Zeckendorf prefix (c1..c_m),
                    time residual is tail sum T = N - V_m(space)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Iterator, Tuple

from common_zeckendorf import (
    fib_value_from_window_bits,
    fib_zeckendorf_upto,
    zeckendorf_digits_low_to_high,
)


@dataclass(frozen=True)
class Truncation:
    name: str
    description: str
    micro_size: Callable[[int], int]
    iter_micro: Callable[[int], Iterable[int]]
    space_word: Callable[[int, int], int]  # (micro, m) -> x (packed int)
    time_residual: Callable[[int, int, int], int]  # (micro, m, x) -> u (int label)


def _iter_range(n: int) -> Iterator[int]:
    for i in range(int(n)):
        yield i


def trunc_zeck_window() -> Truncation:
    def micro_size(m: int) -> int:
        return 1 << int(m)

    def iter_micro(m: int) -> Iterable[int]:
        return _iter_range(1 << int(m))

    def space_word(b: int, m: int) -> int:
        # Compute Zeckendorf digits up to (m+1) to also allow reading overflow.
        N = fib_value_from_window_bits(int(b), m=int(m))
        digits = zeckendorf_digits_low_to_high(N, max_k=int(m) + 1)
        w = 0
        for i in range(int(m)):
            if digits[i]:
                w |= 1 << i
        return int(w)

    def time_residual(b: int, m: int, x: int) -> int:
        # Single overflow bit u = z_{m+2}, which corresponds to digit index m (0-based) in our convention.
        N = fib_value_from_window_bits(int(b), m=int(m))
        digits = zeckendorf_digits_low_to_high(N, max_k=int(m) + 1)
        return int(digits[int(m)])

    return Truncation(
        name="zeck_window",
        description="Window Zeckendorf: micro b in {0,1}^m; space is (z2..z_{m+1}); time is overflow bit z_{m+2}.",
        micro_size=micro_size,
        iter_micro=iter_micro,
        space_word=space_word,
        time_residual=time_residual,
    )


def trunc_dirac_dyadic() -> Truncation:
    def micro_size(m: int) -> int:
        return 1 << int(m)

    def iter_micro(m: int) -> Iterable[int]:
        return _iter_range(1 << int(m))

    def space_word(N: int, m: int) -> int:
        # Zeckendorf digits of N are canonical by definition; take prefix c1..c_m.
        digits = zeckendorf_digits_low_to_high(int(N), max_k=int(m))
        w = 0
        for i in range(int(m)):
            if digits[i]:
                w |= 1 << i
        return int(w)

    def time_residual(N: int, m: int, x: int) -> int:
        # Tail sum T = N - V_m(x), where V_m uses weights [1,2,3,5,...].
        weights = fib_zeckendorf_upto(int(m))
        vm = 0
        for i, wt in enumerate(weights):
            if (int(x) >> i) & 1:
                vm += int(wt)
        return int(N) - int(vm)

    return Truncation(
        name="dirac_dyadic",
        description="Dirac/dyadic: micro N in [0,2^m-1]; space is Zeckendorf prefix (c1..c_m); time is tail sum T.",
        micro_size=micro_size,
        iter_micro=iter_micro,
        space_word=space_word,
        time_residual=time_residual,
    )


_REGISTRY: Dict[str, Callable[[], Truncation]] = {
    "zeck_window": trunc_zeck_window,
    "dirac_dyadic": trunc_dirac_dyadic,
}


def get_truncation(name: str) -> Truncation:
    key = str(name).strip()
    if key not in _REGISTRY:
        raise ValueError(f"unknown truncation: {name!r}; available: {sorted(_REGISTRY.keys())}")
    return _REGISTRY[key]()


def available_truncations() -> Tuple[str, ...]:
    return tuple(sorted(_REGISTRY.keys()))

