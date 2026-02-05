#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zeckendorf folding (64->21) + explicit uplift tail rules (2025 resolution folding convention).

Conventions match `docs/papers/2025_resolution_folding_phi_pi_e_hpa_omega`:
- Fibonacci numbers: F1=1, F2=1, F_{n+2}=F_{n+1}+F_n.
- Zeckendorf digits c_k use weights F_{k+1} for digit index k>=1.
- Macro window of length m: (c_1,...,c_m) (low-to-high).
- Tail/uplift: (c_{m+1},...,c_{K(m)}) where K(m) satisfies
    F_{K(m)+1} <= 2^m - 1 < F_{K(m)+2}.

We pack a bitstring (b1,...,bL) (low-to-high) as an int with bit0=b1.
Tail shift (forward time): drop lowest tail bit, shift down (t >> 1).
Inverse tail step (unfolding): t_prev in {(t<<1), (t<<1)|1} with admissibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


def fib_upto(n: int) -> List[int]:
    """Return [F1..Fn] with F1=F2=1."""
    if n <= 0:
        return []
    if n == 1:
        return [1]
    F = [1, 1]
    while len(F) < n:
        F.append(F[-1] + F[-2])
    return F


def zeckendorf_digits_low_to_high(N: int, max_k: int) -> List[int]:
    """Return digits c1..c_max_k (low-to-high) for Zeckendorf expansion of N."""
    if N < 0:
        raise ValueError("N must be nonnegative")
    if max_k <= 0:
        return []

    # Build weights up to (k+1) index.
    # Weight for digit c_k is F_{k+1}.
    F = fib_upto(max_k + 2)  # ensure at least F_{max_k+1}
    # Extend if needed to cover N (for greedy).
    while F[-1] <= N:
        F.append(F[-1] + F[-2])

    # Greedy from highest weight to lowest.
    c = [0] * (len(F) - 1)  # indices 1..len(F)-1 (we ignore c_0)
    k = len(c) - 1  # corresponds to digit index k, weight F_{k+1}=F[k]
    n = N
    while n > 0 and k >= 1:
        if F[k] <= n:
            c[k] = 1
            n -= F[k]
            k -= 2
        else:
            k -= 1

    out = c[1 : max_k + 1]
    if len(out) < max_k:
        out.extend([0] * (max_k - len(out)))
    return out


def no_adjacent_ones_mask_ok(x: int) -> bool:
    return (x & (x << 1)) == 0


def all_no_adjacent_words(L: int) -> List[int]:
    """All length-L binary words as ints with no adjacent ones (low-to-high bits)."""
    if L < 0:
        raise ValueError("L must be nonnegative")
    out: List[int] = []
    for x in range(1 << L):
        if no_adjacent_ones_mask_ok(x):
            out.append(x)
    return out


def fold_f_m(N: int, m: int) -> int:
    """Fold_m: macro word as int bits c1..c_m (low-to-high)."""
    digits = zeckendorf_digits_low_to_high(N, max_k=m)
    w = 0
    for i, b in enumerate(digits):
        if b:
            w |= 1 << i
    return w


def K_of_m(m: int) -> int:
    """Return K(m) with F_{K+1} <= 2^m-1 < F_{K+2} (2025 convention)."""
    if m < 0:
        raise ValueError("m must be nonnegative")
    target = (1 << m) - 1
    # Find smallest n such that F_n > target, then K+2 = n.
    F = [0, 1, 1]  # dummy 0 so F[1]=1,F[2]=1
    while F[-1] <= target:
        F.append(F[-1] + F[-2])
    n = len(F) - 1  # F_n > target
    return max(1, n - 2)


def tail_length(m: int) -> int:
    return max(0, K_of_m(m) - m)


def tail_word_of_N(N: int, m: int) -> Tuple[int, int]:
    """Return (tail_word, L) where tail_word packs c_{m+1}..c_{K(m)} into low-to-high bits."""
    K = K_of_m(m)
    L = max(0, K - m)
    if L == 0:
        return 0, 0
    digits = zeckendorf_digits_low_to_high(N, max_k=K)
    out = 0
    for j in range(m, K):
        if digits[j]:
            out |= 1 << (j - m)
    return out, L


def tail_shift_word(t: int) -> int:
    """Forward time: drop lowest tail bit."""
    return t >> 1


def tail_inverse_step_candidates(t: int, L: int) -> List[int]:
    """Upward search: all admissible t_prev such that tail_shift_word(t_prev)==t."""
    if L <= 0:
        return [0]
    mask = (1 << L) - 1
    base = (t << 1) & mask
    cands = [base, (base | 1)]
    out: List[int] = []
    for x in cands:
        if no_adjacent_ones_mask_ok(x):
            out.append(x)
    return out


def micro_N_from_macro_and_tail(macro_w: int, tail: int, m: int) -> int:
    """Compute N = sum_{k=1..m} c_k F_{k+1} + sum_{k=m+1..K} c_k F_{k+1}.

    Here macro_w encodes c1..cm in low-to-high bits, tail encodes c_{m+1}..c_K similarly.
    """
    K = K_of_m(m)
    F = fib_upto(K + 2)  # need up to F_{K+1}
    N = 0
    for i in range(m):
        if (macro_w >> i) & 1:
            N += F[i + 1]  # weight F_{(i+1)+1} = F_{i+2} but F is 1-indexed in list; F[1]=1
    for j in range(m, K):
        if (tail >> (j - m)) & 1:
            N += F[j + 1]
    return N


@dataclass(frozen=True)
class FoldDomain:
    m: int
    n_micro: int
    K: int
    L: int
    macro_words: List[int]
    macro_index: Dict[int, int]
    tail_words: List[int]
    tail_index: Dict[int, int]


def build_fold_domain(m: int) -> FoldDomain:
    K = K_of_m(m)
    L = tail_length(m)
    macro_words = all_no_adjacent_words(m)
    macro_words.sort()
    macro_index = {w: i for i, w in enumerate(macro_words)}
    tail_words = all_no_adjacent_words(L)
    tail_words.sort()
    tail_index = {t: i for i, t in enumerate(tail_words)}
    return FoldDomain(
        m=m,
        n_micro=1 << m,
        K=K,
        L=L,
        macro_words=macro_words,
        macro_index=macro_index,
        tail_words=tail_words,
        tail_index=tail_index,
    )

