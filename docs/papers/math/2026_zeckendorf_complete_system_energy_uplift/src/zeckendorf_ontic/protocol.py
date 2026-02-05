#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Protocol/Ledger layer (Layer 1 semantics) built on top of the ontic system.

Goal: provide reversible atomic steps (unfold/fold) that satisfy:
  - Perfect inverse: D(U(sigma)) = sigma and U(D(sigma')) = sigma'
  - Auditable ledger deltas:
      trace_tape_length(next) = trace_tape_length(current) + 1
      resource_limit(next) = resource_limit(current)

Rationale: in the "endogenous W" interpretation, W gain is an observer-level effect tied to the
realized discovery/maintenance of multiple compatible candidates (bubble growth + commit).
Therefore protocol unfold/fold keep W unchanged; commit decides how W is updated/propagated.

This module intentionally avoids exposing unnecessary internal structures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from .ontic_system import OnticZeckendorfSystem

__all__ = ["ProtocolState", "ZeckendorfProtocol"]


@dataclass(frozen=True)
class _BitTape:
    """Internal stack-like tape of bits (append/pop at the end)."""

    _bits: Tuple[int, ...]

    @staticmethod
    def empty() -> "_BitTape":
        return _BitTape(_bits=())

    @staticmethod
    def from_bits(bits: List[int]) -> "_BitTape":
        return _BitTape(_bits=tuple(int(b) & 1 for b in bits))

    @property
    def length(self) -> int:
        return int(len(self._bits))

    def push(self, bit: int) -> "_BitTape":
        return _BitTape(_bits=self._bits + (int(bit) & 1,))

    def push_many(self, bits: List[int]) -> "_BitTape":
        out = self
        for bit in bits:
            out = out.push(int(bit))
        return out

    def pop(self) -> Tuple["_BitTape", int]:
        if not self._bits:
            raise ValueError("pop from empty tape")
        bit = int(self._bits[-1])
        return _BitTape(_bits=self._bits[:-1]), bit

    def pop_many(self, count: int) -> Tuple["_BitTape", List[int]]:
        k = int(count)
        if k < 0:
            raise ValueError("count must be nonnegative")
        if k == 0:
            return self, []
        if k > len(self._bits):
            raise ValueError("pop_many beyond tape length")
        suffix = list(self._bits[-k:])
        prefix = _BitTape(_bits=self._bits[:-k])
        return prefix, [int(b) for b in suffix]


@dataclass(frozen=True)
class ProtocolState:
    """Protocol state container (Layer 1).

    This is the runtime state updated by reversible atomic steps:
      - macro_word: observable window word (space-side register)
      - tail_word: uplift tail head (time-fiber register)
      - trace_tape: reversible log that makes branching invertible
      - energy_tape: resource / inverse-information tape
    """

    _macro_word: int
    _tail_word: int
    _trace_tape: _BitTape
    _resource_limit: int

    @property
    def macro_word(self) -> int:
        return int(self._macro_word)

    @property
    def tail_word(self) -> int:
        return int(self._tail_word)

    @property
    def trace_tape_length(self) -> int:
        return int(self._trace_tape.length)

    @property
    def energy_tape_length(self) -> int:
        # Backward-compatibility is intentionally NOT provided.
        raise AttributeError("energy_tape_length has been removed; use resource_limit instead")

    @property
    def resource_limit(self) -> int:
        """Observer-maintainable upper bound on concurrent branches (beam width cap)."""

        return int(self._resource_limit)


class _FiberCodebook:
    """Deterministic injection Code_y and its partial inverse.

    Implementation: enumerate all micro_integer < 2^window_length with fold(micro_integer)=macro_word,
    sort by micro_integer, assign indices 0..fiber_size-1 and encode as fixed code_bit_length
    little-endian bits.
    """

    def __init__(self, sys: OnticZeckendorfSystem) -> None:
        self._sys = sys
        self._cache: Dict[int, Tuple[int, Dict[int, int]]] = {}  # macro_word -> (code_bit_length, micro_integer->index)

    def code_bit_length(self, macro_word: int) -> int:
        self._ensure(int(macro_word))
        code_bit_length, _ = self._cache[int(macro_word)]
        return int(code_bit_length)

    def encode(self, macro_word: int, micro_integer: int) -> List[int]:
        macro = int(macro_word)
        N = int(micro_integer)
        self._ensure(macro)
        code_bit_length, micro_to_index = self._cache[macro]
        idx = micro_to_index[N]
        return [(idx >> j) & 1 for j in range(int(code_bit_length))]

    def decode(self, macro_word: int, bits: List[int]) -> Optional[int]:
        macro = int(macro_word)
        self._ensure(macro)
        code_bit_length, micro_to_index = self._cache[macro]
        if len(bits) != int(code_bit_length):
            return None
        idx = 0
        for j, b in enumerate(bits):
            idx |= (int(b) & 1) << int(j)
        # partial inverse: valid iff idx < s
        fiber_size = len(micro_to_index)
        if idx < 0 or idx >= fiber_size:
            return None
        # find micro_integer by index (reverse map)
        for micro_integer, i in micro_to_index.items():
            if int(i) == int(idx):
                return int(micro_integer)
        return None

    def _ensure(self, macro_word: int) -> None:
        macro = int(macro_word)
        if macro in self._cache:
            return
        # Enumerate preimage.
        micro_preimage: List[int] = []
        for micro_integer in range(1 << self._sys.window_length):
            if self._sys.fold(micro_integer) == macro:
                micro_preimage.append(int(micro_integer))
        micro_preimage.sort()
        fiber_size = len(micro_preimage)
        code_bit_length = 0
        while (1 << code_bit_length) < max(1, fiber_size):
            code_bit_length += 1
        micro_to_index = {int(micro_integer): int(i) for i, micro_integer in enumerate(micro_preimage)}
        self._cache[macro] = (int(code_bit_length), micro_to_index)


class ZeckendorfProtocol:
    """Layer-1 reversible protocol built over a fixed ontic system."""

    def __init__(self, sys: OnticZeckendorfSystem) -> None:
        self._sys = sys
        self._code = _FiberCodebook(sys)

    # =========================
    # Public constructors (Observer-facing)
    # =========================
    def create_state(
        self,
        macro_word: int,
        *,
        tail_word: int = 0,
        resource_limit: int,
        trace_seed_bits: Optional[List[int]] = None,
    ) -> ProtocolState:
        """Create an initial protocol state with explicit seeds.

        Observer is expected to use this instead of constructing ProtocolState directly.
        """

        trace_bits = [] if trace_seed_bits is None else list(trace_seed_bits)
        limit = int(resource_limit)
        if limit < 1:
            raise ValueError("resource_limit must be >= 1")
        return ProtocolState(
            _macro_word=int(macro_word),
            _tail_word=int(tail_word),
            _trace_tape=_BitTape.from_bits(trace_bits),
            _resource_limit=limit,
        )

    # =========================
    # Public query methods (Observer-facing)
    # =========================
    def code_bit_length(self, macro_word: int) -> int:
        return int(self._code.code_bit_length(int(macro_word)))

    def is_ok_clo(self, state: ProtocolState) -> bool:
        """Ontic feasibility guard OK_Clo(macro_word, tail_word)."""

        return bool(self._sys.ok(state.macro_word, state.tail_word))

    def beam_width_cap(self, state: ProtocolState) -> int:
        """Current cap on concurrently maintained branches (resource upper bound)."""

        return int(state.resource_limit)

    def score_key(self, state: ProtocolState) -> tuple:
        """Deterministic score key for commit/ordering (paper-style).

        Key structure:
          (reconstructed_micro_integer, trace_tape_length, trace_bits_tuple, tail_word)
        """

        reconstructed = self._sys.rec(state.macro_word, state.tail_word)
        if reconstructed is None:
            # Infeasible states should not be committed/kept.
            return (10**30, 10**30, (), 10**30)
        trace_bits_tuple = tuple(state._trace_tape._bits)  # internal; observer uses protocol API only
        return (int(reconstructed), int(state.trace_tape_length), trace_bits_tuple, int(state.tail_word))

    def unfold_step(self, s: ProtocolState, branch_choice_bit: int = 0) -> Optional[ProtocolState]:
        """Unfold one reversible step.

        - Use branch_choice_bit to select a feasible predecessor tail_word candidate.
        - Append that branch_choice_bit to trace_tape.
        - Update resource_limit only if a real branch is taken (see module docstring).
        """

        candidates = self._sys.candidates(s.macro_word, s.tail_word)
        choice = int(branch_choice_bit)
        if choice < 0:
            return None
        if choice >= len(candidates):
            return None
        next_tail_word = int(candidates[choice])
        micro_integer = self._sys.rec(s.macro_word, next_tail_word)
        if micro_integer is None:
            return None

        resource_limit_next = int(s.resource_limit)

        trace_next = s._trace_tape.push(int(choice))
        return ProtocolState(
            _macro_word=int(s.macro_word),
            _tail_word=int(next_tail_word),
            _trace_tape=trace_next,
            _resource_limit=int(resource_limit_next),
        )

    def fold_step(self, s: ProtocolState) -> Optional[ProtocolState]:
        """D: inverse of unfold_step (strict)."""

        if s._trace_tape.length < 1:
            return None
        trace_prefix, branch_bit = s._trace_tape.pop()
        prev_tail_word = self._sys.tail_shift(s.tail_word)

        resource_limit_prev = int(s.resource_limit)

        # Candidate consistency: tail_word_current must be the branch_bit-th candidate from (macro_word, tail_word_previous).
        candidates = self._sys.candidates(s.macro_word, int(prev_tail_word))
        if branch_bit >= len(candidates) or int(candidates[int(branch_bit)]) != int(s.tail_word):
            return None
        return ProtocolState(
            _macro_word=int(s.macro_word),
            _tail_word=int(prev_tail_word),
            _trace_tape=trace_prefix,
            _resource_limit=int(resource_limit_prev),
        )

    # -----------------------
    # Reachability utilities
    # -----------------------
    def feasible_tails(self, macro_word: int) -> Set[int]:
        """All tail_word values such that OK_Clo(macro_word, tail_word)=1.

        Parameter name `macro_word` represents the Fold window word (space-side observation).
        """

        macro_word = int(macro_word)
        L = self._sys.tail_length()
        out: Set[int] = set()
        for tail_word in range(1 << L) if L > 0 else range(1):
            if self._sys.ok(macro_word, int(tail_word)):
                out.add(int(tail_word))
        return out

    def reachable_tails(self, macro_word: int, depth_max: int, tail_word_start: int = 0) -> Set[int]:
        """Tails reachable from tail_word_start by iterated candidates(macro_word,·) up to depth_max.

        This treats the branch label b as an API choice (not a random process).
        """

        macro_word = int(macro_word)
        dmax = int(depth_max)
        tail_word_start = int(tail_word_start)
        frontier: Set[int] = {tail_word_start}
        reached: Set[int] = {tail_word_start} if self._sys.ok(macro_word, tail_word_start) else set()
        for _ in range(dmax):
            nxt: Set[int] = set()
            for tail_word in frontier:
                for previous_tail_word in self._sys.candidates(macro_word, int(tail_word)):
                    nxt.add(int(previous_tail_word))
            frontier = nxt
            for tail_word in frontier:
                if self._sys.ok(macro_word, int(tail_word)):
                    reached.add(int(tail_word))
        return reached

