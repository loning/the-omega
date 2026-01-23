#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Layer-0 (ontic) system: Zeckendorf window folding + explicit uplift tail.

Paper semantics (Layer 0):
  - Fibonacci: F1=1, F2=1, F_{n+2}=F_{n+1}+F_n
  - Zeckendorf digits c_k use weights F_{k+1} for digit index k>=1
  - Fixed window length is called window_length (= m in the paper).
  - Fold_{window_length}(micro_integer) = (c1..c_m) window projection
    (packed int, low-to-high).
  - tau_{window_length}(micro_integer) = (c_{m+1}..c_{K(m)}) uplift tail word
    (packed int, low-to-high).
  - K(window_length) is the unique integer satisfying:
      F_{K+1} <= 2^m - 1 < F_{K+2}.
  - Tail(tail_word): tail shift operator (drop the lowest tail bit, i.e., >> 1).
  - Enc(micro_integer) = (macro_word, tail_word) = (Fold(micro_integer), tau(micro_integer)).
  - A_m = Im(Enc) is the feasible set of (macro_word, tail_word) pairs.
  - OK_Clo(macro_word, tail_word) is the feasibility guard for pairs.
  - C(macro_word, tail_word) is the feasible Tail^{-1} candidate set.

Representation:
  - macro_word is an int packing (c1..c_m), bit0=c1
  - tail_word is an int packing (c_{m+1}..c_K), bit0=c_{m+1}

This module is self-contained and does not depend on the paper's `scripts/`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

__all__ = ["EncPair", "OnticZeckendorfSystem"]

# =========================
# Module-private static helpers
# (kept outside classes; not part of public API)
# =========================


def _fib_table(n: int) -> List[int]:
    """Return Fibonacci table F[0..n] with F1=1,F2=1 (1-indexed convention)."""

    nn = int(n)
    if nn < 0:
        raise ValueError("n must be nonnegative")
    if nn == 0:
        return [0]
    if nn == 1:
        return [0, 1]
    F = [0] * (nn + 1)
    F[1] = 1
    F[2] = 1
    for k in range(3, nn + 1):
        F[k] = F[k - 1] + F[k - 2]
    return F


def _no_adjacent_ones_mask_ok(x: int) -> bool:
    xi = int(x)
    return (xi & (xi << 1)) == 0


def _zeckendorf_digits_low_to_high(N: int, max_k: int) -> List[int]:
    """Return digits [c1..c_max_k] for Zeckendorf expansion of N."""

    n = int(N)
    if n < 0:
        raise ValueError("N must be nonnegative")
    mk = int(max_k)
    if mk <= 0:
        return []

    # Need weights up to cover n: digit k uses weight F_{k+1}.
    # We build F up to some index >= mk+1 and extend until the max weight exceeds n.
    F = _fib_table(mk + 2)  # ensures F_{mk+2} exists
    while F[-1] <= n:
        # extend one more term
        F.append(F[-1] + F[-2])

    # Greedy from highest usable digit index downwards.
    # Weight for digit k is F[k+1] (note: F is 1-indexed).
    # The largest possible digit index is len(F)-2 (since weight uses F[k+1]).
    max_digit = len(F) - 2
    c = [0] * (max_digit + 1)  # indices 0..max_digit; we use 1..max_digit

    k = max_digit
    rem = n
    while rem > 0 and k >= 1:
        w = F[k + 1]
        if w <= rem:
            c[k] = 1
            rem -= w
            k -= 2  # enforce no adjacent ones
        else:
            k -= 1

    out = c[1 : mk + 1]
    if len(out) < mk:
        out.extend([0] * (mk - len(out)))
    return out


def _K_of_m(m: int) -> int:
    """Return K(m) with F_{K+1} <= 2^m-1 < F_{K+2}."""

    mm = int(m)
    if mm < 0:
        raise ValueError("m must be nonnegative")
    target = (1 << mm) - 1
    # Find smallest n such that F_n > target, then K+2 = n.
    F = [0, 1, 1]  # F[1]=1,F[2]=1
    while F[-1] <= target:
        F.append(F[-1] + F[-2])
    n = len(F) - 1  # index of last element
    return max(1, n - 2)


def _tail_length(m: int) -> int:
    return max(0, _K_of_m(m) - int(m))


def _pack_bits_low_to_high(bits: List[int]) -> int:
    x = 0
    for i, b in enumerate(bits):
        if int(b) & 1:
            x |= 1 << i
    return int(x)


@dataclass(frozen=True)
class EncPair:
    """(macro_word, tail_word) = (Fold_m(N), tau_m(N))."""

    macro_word: int
    tail_word: int


class OnticZeckendorfSystem:
    """Minimal Layer-0 API for the paper (no extra data exposure)."""

    def __init__(self, window_length: int) -> None:
        m = int(window_length)
        if m < 0:
            raise ValueError("window_length must be nonnegative")
        self._window_length = m
        self._micro_domain_size = 1 << self._window_length
        self._tail_cover_index = _K_of_m(self._window_length)  # K(m) in the paper
        self._tail_length = _tail_length(self._window_length)  # L(m) in the paper

        # Internal caches
        self._enc_cache: Dict[int, EncPair] = {}
        self._rec_cache: Dict[Tuple[int, int], int] = {}
        self._fiber_size_cache: Dict[int, int] = {}

    # ====================
    # Public instance methods (Layer-0 API)
    # ====================
    @property
    def window_length(self) -> int:
        """Window length m."""

        return int(self._window_length)

    def tail_length(self) -> int:
        """Tail length L(m) = max(0, K(m)-m)."""

        return int(self._tail_length)

    def fold(self, micro_integer: int) -> int:
        """Fold_m: window (macro) word as packed int."""

        N = self._assert_micro_integer_in_domain(micro_integer)
        digits = _zeckendorf_digits_low_to_high(N, max_k=self._window_length)
        return _pack_bits_low_to_high(digits)

    def tail(self, micro_integer: int) -> int:
        """tau_m: tail (uplift) word as packed int."""

        N = self._assert_micro_integer_in_domain(micro_integer)
        if self._tail_length == 0:
            return 0
        digits = _zeckendorf_digits_low_to_high(N, max_k=self._tail_cover_index)
        tail_digits = digits[self._window_length : self._tail_cover_index]  # c_{m+1}..c_K
        return _pack_bits_low_to_high(tail_digits)

    def enc(self, micro_integer: int) -> EncPair:
        """Enc_m(N) = (Fold_m(N), tau_m(N))."""

        N = self._assert_micro_integer_in_domain(micro_integer)
        if N in self._enc_cache:
            return self._enc_cache[N]
        pair = EncPair(macro_word=self.fold(N), tail_word=self.tail(N))
        self._enc_cache[N] = pair
        self._rec_cache[(pair.macro_word, pair.tail_word)] = N
        return pair

    def rec(self, macro_word: int, tail_word: int) -> Optional[int]:
        """Rec_m(macro_word, tail_word) -> micro N if feasible else None."""

        macro = int(macro_word)
        tail = int(tail_word)
        key = (macro, tail)
        if key in self._rec_cache:
            return int(self._rec_cache[key])

        if macro < 0 or macro >= (1 << self._window_length):
            return None
        if self._tail_length == 0:
            if tail != 0:
                return None
        else:
            if tail < 0 or tail >= (1 << self._tail_length):
                return None

        N = self._micro_integer_from_macro_and_tail(macro_word=macro, tail_word=tail)
        if N < 0 or N >= self._micro_domain_size:
            return None
        pair = self.enc(N)
        if pair.macro_word != macro or pair.tail_word != tail:
            return None
        self._rec_cache[key] = N
        return N

    def ok(self, macro_word: int, tail_word: int) -> bool:
        """OK_Clo(macro_word, tail_word) := 1_{(macro_word,tail_word) in A_m}."""

        return self.rec(macro_word, tail_word) is not None

    def tail_shift(self, tail_word: int) -> int:
        """Tail(tail_word): forward-time tail shift (drop lowest tail bit)."""

        tail = self._assert_tail_word_in_range(tail_word)
        if self._tail_length == 0:
            return 0
        return int(tail >> 1)

    def tail_inverse_candidates(self, tail_word: int) -> List[int]:
        """All admissible t_prev with Tail(t_prev) = tail_word (tail-only legality)."""

        tail = self._assert_tail_word_in_range(tail_word)
        if self._tail_length == 0:
            return [0]
        # Tail(previous_tail_word) = (previous_tail_word >> 1). Therefore a preimage exists iff the
        # top bit of tail_word is 0 (equivalently tail_word < 2^(tail_length-1)).
        if tail >= (1 << (self._tail_length - 1)):
            return []
        base = tail << 1
        cands = [base, base | 1]
        out: List[int] = []
        for x in cands:
            if _no_adjacent_ones_mask_ok(x):
                out.append(int(x))
        return out

    def candidates(self, macro_word: int, tail_word: int) -> List[int]:
        """Feasible tail preimages under Tail^{-1} and OK_Clo.

        Returns: { previous_tail_word : Tail(previous_tail_word)=tail_word AND OK_Clo(macro_word,previous_tail_word) }.
        """

        macro = int(macro_word)
        tail = self._assert_tail_word_in_range(tail_word)
        out: List[int] = []
        for tail_prev in self.tail_inverse_candidates(tail):
            if self.ok(macro, int(tail_prev)):
                out.append(int(tail_prev))
        # Deterministic order: smaller micro integer N first.
        out.sort(key=lambda tp: int(self._micro_integer_from_macro_and_tail(macro_word=macro, tail_word=int(tp))))
        return out

    def fiber_size(self, macro_word: int) -> int:
        """s_m(macro_word) = |{N<2^m : Fold_m(N)=macro_word}|."""

        macro = int(macro_word)
        if macro in self._fiber_size_cache:
            return int(self._fiber_size_cache[macro])
        s = 0
        for N in range(self._micro_domain_size):
            if self.fold(N) == macro:
                s += 1
        self._fiber_size_cache[macro] = int(s)
        return int(s)

    # ====================
    # Private instance methods (internal)
    # ====================
    def _assert_micro_integer_in_domain(self, micro_integer: int) -> int:
        N = int(micro_integer)
        if N < 0 or N >= self._micro_domain_size:
            raise ValueError("micro_integer out of dyadic domain for this window_length")
        return N

    def _assert_tail_word_in_range(self, tail_word: int) -> int:
        tail = int(tail_word)
        if self._tail_length == 0:
            if tail != 0:
                raise ValueError("tail_word out of range (tail_length=0 implies only tail_word=0)")
            return 0
        if tail < 0 or tail >= (1 << self._tail_length):
            raise ValueError("tail_word out of range for this window_length")
        return tail

    def _micro_integer_from_macro_and_tail(self, macro_word: int, tail_word: int) -> int:
        """Compute micro integer N from packed macro_word and packed tail_word using Fibonacci weights."""

        macro = int(macro_word)
        tail = int(tail_word)
        F = _fib_table(self._tail_cover_index + 2)
        micro_integer = 0
        # macro bits: c1..cm
        for i in range(self._window_length):
            if (macro >> i) & 1:
                digit_index = i + 1
                micro_integer += F[digit_index + 1]  # F_{digit_index+1}
        # tail bits: c_{m+1}..c_K
        for digit_index in range(self._window_length + 1, self._tail_cover_index + 1):
            bit_index = digit_index - (self._window_length + 1)  # bit0 = c_{m+1}
            if (tail >> bit_index) & 1:
                micro_integer += F[digit_index + 1]
        return int(micro_integer)

