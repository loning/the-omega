#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zeckendorf representation and truncated fold f_m."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


def fib_zeckendorf_upto(max_k: int) -> List[int]:
    """Return [F1, ..., F_max_k] with F1=1, F2=2, F_{k+2}=F_{k+1}+F_k."""
    if max_k <= 0:
        return []
    if max_k == 1:
        return [1]
    F = [1, 2]
    while len(F) < max_k:
        F.append(F[-1] + F[-2])
    return F


def zeckendorf_digits_low_to_high(N: int, max_k: int) -> List[int]:
    """Return digits c1..c_max_k (low-to-high) of Zeckendorf representation of N."""
    if N < 0:
        raise ValueError("N must be nonnegative")
    if max_k <= 0:
        return []

    # Ensure we have enough Fibonacci numbers to cover N.
    F = fib_zeckendorf_upto(max_k)
    while F[-1] <= N:
        F.append(F[-1] + F[-2])

    c = [0] * len(F)
    k = len(F) - 1
    n = N
    while n > 0 and k >= 0:
        if F[k] <= n:
            c[k] = 1
            n -= F[k]
            k -= 2  # skip adjacent
        else:
            k -= 1

    # Convert to c1..c_max_k, padding/truncating as needed.
    out = c[:max_k]
    if len(out) < max_k:
        out.extend([0] * (max_k - len(out)))
    return out


def no_adjacent_ones_mask_ok(x: int) -> bool:
    return (x & (x << 1)) == 0


def all_no_adjacent_words(m: int) -> List[int]:
    """All length-m binary words (as int with bit i = digit_{i+1}) with no adjacent ones."""
    if m < 0:
        raise ValueError("m must be nonnegative")
    out: List[int] = []
    for x in range(1 << m):
        if no_adjacent_ones_mask_ok(x):
            out.append(x)
    return out


def fold_f_m(N: int, m: int) -> int:
    """Fold f_m on micro integer N: return macro word as int bits c1..c_m (low-to-high)."""
    digits = zeckendorf_digits_low_to_high(N, max_k=m)
    w = 0
    for i, b in enumerate(digits):
        if b:
            w |= 1 << i
    return w


def word_bits_low_to_high_str(w: int, m: int) -> str:
    return "".join("1" if ((w >> i) & 1) else "0" for i in range(m))


def word_bits_high_to_low_str(w: int, m: int) -> str:
    return "".join("1" if ((w >> i) & 1) else "0" for i in range(m - 1, -1, -1))


def bin_m_high_to_low_str(N: int, m: int) -> str:
    return format(N, f"0{m}b")


@dataclass(frozen=True)
class FoldResult:
    m: int
    n_micro: int
    macro_words: List[int]
    macro_index: dict  # word -> idx in macro_words


def build_fold_domain(m: int) -> FoldResult:
    macro_words = all_no_adjacent_words(m)
    macro_words.sort()
    macro_index = {w: i for i, w in enumerate(macro_words)}
    return FoldResult(m=m, n_micro=1 << m, macro_words=macro_words, macro_index=macro_index)

