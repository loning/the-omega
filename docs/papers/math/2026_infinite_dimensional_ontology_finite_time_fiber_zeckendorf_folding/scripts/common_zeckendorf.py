#!/usr/bin/env python3
"""
Zeckendorf (Fibonacci) representation helpers used by this paper.

Convention:
  Zeckendorf Fibonacci weights are [1, 2, 3, 5, 8, ...], i.e. standard Fibonacci F2, F3, ...
Digits are returned low-to-high (least significant weight first).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Tuple


def fib_zeckendorf_upto(max_k: int) -> List[int]:
    """
    Return [Z1, ..., Z_max_k] where Z1=1, Z2=2, Z_{k+2}=Z_{k+1}+Z_k.
    """
    if max_k <= 0:
        return []
    if max_k == 1:
        return [1]
    F = [1, 2]
    while len(F) < max_k:
        F.append(F[-1] + F[-2])
    return F


def zeckendorf_digits_low_to_high(N: int, max_k: int) -> List[int]:
    """
    Return digits c1..c_max_k (low-to-high) of Zeckendorf representation of integer N >= 0.
    """
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
            k -= 2  # skip adjacent
        else:
            k -= 1

    out = c[:max_k]
    if len(out) < max_k:
        out.extend([0] * (max_k - len(out)))
    return out


def no_adjacent_ones_mask_ok(x: int) -> bool:
    return (x & (x << 1)) == 0


def word_bit(x: int, i: int) -> int:
    return (x >> i) & 1


def word_bits_low_to_high_str(w: int, m: int) -> str:
    return "".join("1" if ((w >> i) & 1) else "0" for i in range(m))


def word_bits_high_to_low_str(w: int, m: int) -> str:
    return "".join("1" if ((w >> i) & 1) else "0" for i in range(m - 1, -1, -1))


def iter_no_adjacent_words(m: int) -> Iterator[int]:
    """
    Generate all length-m binary words with no adjacent ones.
    Words are packed into int with bit i = digit_{i+1} (low-to-high).
    """
    if m < 0:
        raise ValueError("m must be nonnegative")

    def rec(pos: int, prev1: int, acc: int) -> Iterator[int]:
        if pos == m:
            yield acc
            return
        # place 0
        yield from rec(pos + 1, 0, acc)
        # place 1 only if previous is 0
        if prev1 == 0:
            yield from rec(pos + 1, 1, acc | (1 << pos))

    yield from rec(0, 0, 0)


def iter_cycle_no_adjacent_words(m: int) -> Iterator[int]:
    """
    Generate all length-m cycle-legal words (no adjacent ones, including wrap-around).
    """
    if m < 0:
        raise ValueError("m must be nonnegative")
    if m == 0:
        yield 0
        return
    if m == 1:
        yield 0
        yield 1
        return

    def rec(pos: int, first1: int, prev1: int, acc: int) -> Iterator[int]:
        if pos == m:
            if first1 == 1 and prev1 == 1:
                return
            yield acc
            return
        # place 0
        yield from rec(pos + 1, first1, 0, acc)
        # place 1 only if previous is 0
        if prev1 == 0:
            if pos == 0:
                yield from rec(pos + 1, 1, 1, acc | (1 << pos))
            else:
                yield from rec(pos + 1, first1, 1, acc | (1 << pos))

    yield from rec(0, 0, 0, 0)


def fib_value_from_window_bits(b: int, m: int) -> int:
    """
    Compute N(b)=sum_{i=1..m} b_i * F_{i+1}, where weights are [1,2,3,5,...].
    Here b packs b_i as bit (i-1) (low-to-high).
    """
    if m < 0:
        raise ValueError("m must be nonnegative")
    weights = fib_zeckendorf_upto(m)
    total = 0
    for i in range(m):
        if (b >> i) & 1:
            total += weights[i]
    return total


def fold_window_bits_to_macro_word(b: int, m: int) -> int:
    """
    Paper's Fold_m: interpret b as Fibonacci-weighted digits, convert to Zeckendorf canonical digits,
    then truncate to first m digits (low-to-high).
    """
    N = fib_value_from_window_bits(b, m=m)
    digits = zeckendorf_digits_low_to_high(N, max_k=m)
    w = 0
    for i, bit in enumerate(digits):
        if bit:
            w |= 1 << i
    return w


@dataclass(frozen=True)
class FoldDomain:
    m: int
    macro_words: List[int]
    macro_index: Dict[int, int]


def build_fold_domain(m: int) -> FoldDomain:
    macro_words = list(iter_no_adjacent_words(m))
    macro_words.sort()
    macro_index = {w: i for i, w in enumerate(macro_words)}
    return FoldDomain(m=m, macro_words=macro_words, macro_index=macro_index)


def mean(xs: Iterable[float]) -> float:
    xs = list(xs)
    return sum(xs) / float(len(xs)) if xs else 0.0

