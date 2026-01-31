#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A simple, auditable Fold_m via Zeckendorf normalization.

This follows the paper's Section 04 narrative:
1) interpret a binary word as a truncated Fibonacci-base numeral
2) map to the underlying integer N
3) output the length-m prefix of the Zeckendorf representation of N
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


def fibonacci_weights(m: int) -> List[int]:
    """Return Fibonacci weights [F1,...,Fm] with F1=1, F2=2."""
    if m <= 0:
        return []
    if m == 1:
        return [1]
    w = [1, 2]
    while len(w) < m:
        w.append(w[-1] + w[-2])
    return w


def word_to_int(bits: List[int]) -> int:
    w = fibonacci_weights(len(bits))
    return int(sum(b * wi for b, wi in zip(bits, w)))


def zeckendorf_bits(N: int, m: int) -> List[int]:
    """Greedy Zeckendorf representation truncated/padded to length m."""
    if N < 0:
        raise ValueError("N must be nonnegative")
    w = fibonacci_weights(m)
    bits = [0] * m
    remaining = N
    # Greedy from largest weight down, skipping adjacent positions.
    i = m - 1
    while i >= 0 and remaining > 0:
        if w[i] <= remaining:
            bits[i] = 1
            remaining -= w[i]
            i -= 2  # skip adjacent position to enforce no '11'
        else:
            i -= 1
    return bits


def fold_m(raw_word: Iterable[int]) -> Tuple[int, ...]:
    bits = [1 if int(b) else 0 for b in raw_word]
    m = len(bits)
    N = word_to_int(bits)
    z = zeckendorf_bits(N, m)
    return tuple(z)


@dataclass(frozen=True)
class DegeneracyHistogram:
    m: int
    fiber_sizes: Dict[Tuple[int, ...], int]

    def histogram(self) -> Counter:
        return Counter(self.fiber_sizes.values())


def exact_degeneracy_histogram(m: int) -> DegeneracyHistogram:
    """Compute exact fiber sizes for all 2^m raw words (small m)."""
    if m < 1:
        raise ValueError("m must be >= 1")
    if m > 20:
        raise ValueError("m too large for exact enumeration (use m<=20)")
    fiber_sizes: Dict[Tuple[int, ...], int] = {}
    for x in range(2**m):
        raw = [(x >> i) & 1 for i in range(m)]
        y = fold_m(raw)
        fiber_sizes[y] = fiber_sizes.get(y, 0) + 1
    return DegeneracyHistogram(m=m, fiber_sizes=fiber_sizes)

