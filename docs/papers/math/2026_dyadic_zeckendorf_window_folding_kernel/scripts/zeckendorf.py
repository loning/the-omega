#!/usr/bin/env python3
"""Zeckendorf/Fibonacci-base utilities used by experiments.

We use the convention:
  F_1=F_2=1, F_{n+2}=F_{n+1}+F_n.
Zeckendorf digits (c_k) satisfy:
  N = sum_{k>=1} c_k F_{k+1},  c_k in {0,1},  c_k c_{k+1}=0.
"""

from __future__ import annotations

from typing import List, Tuple


def fibs_up_to_index(n: int) -> List[int]:
    """Return list fib with 0..n indices; fib[i] = F_i for i>=1; fib[0]=0."""
    if n < 2:
        n = 2
    fib = [0] * (n + 1)
    fib[1] = 1
    fib[2] = 1
    for i in range(3, n + 1):
        fib[i] = fib[i - 1] + fib[i - 2]
    return fib


def zeckendorf_digits(N: int, fib: List[int]) -> Tuple[int, List[int]]:
    """Return (K, c) where c[k] is digit for weight F_{k+1}, 1<=k<=K, and K is max k used.

    The list c has length K+1 (index 0 unused).
    """
    if N < 0:
        raise ValueError("N must be non-negative")
    if N == 0:
        return 1, [0, 0]

    # Find largest i such that F_i <= N.
    i = len(fib) - 1
    while i >= 1 and fib[i] > N:
        i -= 1
    if i < 2:
        i = 2

    # Digits are for F_{k+1}. If we pick F_i, that corresponds to k=i-1.
    K = max(1, i - 1)
    c = [0] * (K + 1)
    rem = N
    prev_one = 0  # prev_one means c[k+1] was 1.
    for k in range(K, 0, -1):
        w = fib[k + 1]
        if prev_one == 0 and w <= rem:
            c[k] = 1
            rem -= w
            prev_one = 1
        else:
            c[k] = 0
            prev_one = 0
    if rem != 0:
        raise RuntimeError("greedy Zeckendorf failed to represent N")
    return K, c


def fold_prefix(c: List[int], m: int) -> Tuple[int, ...]:
    """Return (c_1,...,c_m), padding with zeros if needed."""
    if m < 0:
        raise ValueError("m must be non-negative")
    out = []
    for k in range(1, m + 1):
        out.append(c[k] if k < len(c) else 0)
    return tuple(out)


def V_m(w: Tuple[int, ...], fib: List[int]) -> int:
    """Value coordinate V_m(w)=sum_{k=1..m} w_k F_{k+1}."""
    s = 0
    for k, bit in enumerate(w, start=1):
        if bit:
            s += fib[k + 1]
    return s


def sigma_window(c: List[int], m: int, L: int) -> Tuple[int, ...]:
    """Return sigma_m^(L) = (c_{m-L+1},...,c_m) for digits list c (1-indexed)."""
    if L <= 0:
        raise ValueError("L must be positive")
    out = []
    start = m - L + 1
    for k in range(start, m + 1):
        out.append(c[k] if (k >= 1 and k < len(c)) else 0)
    return tuple(out)


def count_leq_with_fixed_digit(bound_c: List[int], fixed_k: int, fixed_val: int = 1) -> int:
    """Count Zeckendorf digit strings <= bound (in Fibonacci order) with c_fixed_k = fixed_val."""
    if fixed_val not in (0, 1):
        raise ValueError("fixed_val must be 0 or 1")
    K = len(bound_c) - 1
    if fixed_k < 1:
        raise ValueError("fixed_k must be >=1")

    # If the bound has no such position, that digit is always 0 under <= bound.
    if fixed_k > K:
        if fixed_val == 1:
            return 0
        # Count all valid digit strings <= bound.
        states = {(0, 1): 1}
        for pos in range(K, 0, -1):
            b = bound_c[pos]
            new_states = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 0}
            for (prev, tight), cnt in states.items():
                if cnt == 0:
                    continue
                max_d = b if tight == 1 else 1
                for d in (0, 1):
                    if d > max_d:
                        continue
                    if prev == 1 and d == 1:
                        continue
                    ntight = 1 if (tight == 1 and d == b) else 0
                    new_states[(d, ntight)] += cnt
            states = new_states
        return int(sum(states.values()))

    # Iterative DP to avoid Python recursion depth limits (K can be ~3000 for m~2000).
    # State: (prev_digit, tight) -> count, where prev_digit is digit at pos+1.
    states = {(0, 1): 1}
    for pos in range(K, 0, -1):
        b = bound_c[pos]
        new_states = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 0}
        for (prev, tight), cnt in states.items():
            if cnt == 0:
                continue
            max_d = b if tight == 1 else 1

            if pos == fixed_k:
                ds = [fixed_val]
            else:
                ds = [0, 1]

            for d in ds:
                if d > max_d:
                    continue
                if prev == 1 and d == 1:
                    continue
                ntight = 1 if (tight == 1 and d == b) else 0
                new_states[(d, ntight)] += cnt
        states = new_states

    return int(sum(states.values()))

