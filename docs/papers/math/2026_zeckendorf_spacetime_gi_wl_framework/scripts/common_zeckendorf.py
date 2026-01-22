#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zeckendorf representation utilities for this paper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


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
            k -= 2
        else:
            k -= 1

    out = c[:max_k]
    if len(out) < max_k:
        out.extend([0] * (max_k - len(out)))
    return out


def fold_f_m(N: int, m: int) -> int:
    """Fold f_m on micro integer N: macro word as int bits c1..c_m (low-to-high)."""
    digits = zeckendorf_digits_low_to_high(N, max_k=m)
    w = 0
    for i, b in enumerate(digits):
        if b:
            w |= 1 << i
    return w


def no_adjacent_ones_mask_ok(x: int) -> bool:
    return (x & (x << 1)) == 0


def all_no_adjacent_words(m: int) -> List[int]:
    """All length-m binary words as ints with no adjacent ones (low-to-high bits)."""
    if m < 0:
        raise ValueError("m must be nonnegative")
    out: List[int] = []
    for x in range(1 << m):
        if no_adjacent_ones_mask_ok(x):
            out.append(x)
    return out


def K_of_m(m: int) -> int:
    """Smallest K such that F_K > 2^m - 1 (Zeckendorf Fibonacci version)."""
    if m < 0:
        raise ValueError("m must be nonnegative")
    target = (1 << m) - 1
    if target <= 0:
        return 1
    F = [1, 2]  # F1, F2
    k = 2
    while F[-1] <= target:
        F.append(F[-1] + F[-2])
        k += 1
    return k


def tail_length(m: int) -> int:
    return max(0, K_of_m(m) - m)


def tail_word_of_N(N: int, m: int) -> int:
    """Return tail bits (c_{m+1}..c_{K(m)}) packed into int low-to-high."""
    K = K_of_m(m)
    if K <= m:
        return 0
    digits = zeckendorf_digits_low_to_high(N, max_k=K)
    out = 0
    for j in range(m, K):
        if digits[j]:
            out |= 1 << (j - m)
    return out


def tail_shift_word(t: int) -> int:
    """Shift tail word left by one 'time step': drop lowest bit, shift down."""
    return t >> 1


@dataclass(frozen=True)
class FoldDomain:
    m: int
    n_micro: int
    macro_words: List[int]
    macro_index: Dict[int, int]
    tail_len: int
    tail_words: List[int]
    tail_index: Dict[int, int]


def build_fold_domain(m: int) -> FoldDomain:
    macro_words = all_no_adjacent_words(m)
    macro_words.sort()
    macro_index = {w: i for i, w in enumerate(macro_words)}

    L = tail_length(m)
    tail_words = all_no_adjacent_words(L)
    tail_words.sort()
    tail_index = {w: i for i, w in enumerate(tail_words)}

    return FoldDomain(
        m=m,
        n_micro=1 << m,
        macro_words=macro_words,
        macro_index=macro_index,
        tail_len=L,
        tail_words=tail_words,
        tail_index=tail_index,
    )

