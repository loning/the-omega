#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Observer layer built on top of the protocol layer.

Design intent (paper-aligned):
  - Ontic layer (Layer 0) defines static feasibility and tail dynamics.
  - Protocol layer (Layer 1) defines reversible atomic steps and ledger tapes.
  - Observer layer uses protocol as a substrate to run an external "machine"
    semantics (e.g., a Turing-machine-like runner), and may optionally couple
    each machine step with a protocol unfold/fold step to make "time-fiber"
    evolution and ledgers part of the executed history.

This module intentionally exposes a small public API. Internal tape and history
representation are private.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Set, Tuple, List, Iterator, NamedTuple

from .protocol import ProtocolState, ZeckendorfProtocol

__all__ = ["Observer", "Transition", "ObserverObservation"]


Symbol = str
State = str
Move = int  # -1, 0, +1


@dataclass(frozen=True)
class Transition:
    """One deterministic transition of the observer machine."""

    next_state: State
    write_symbol: Symbol
    head_move: Move  # -1,0,+1


@dataclass(frozen=True)
class _DecodedHistoryRecord:
    previous_state_index: int
    previous_head_position: int
    previous_symbol_under_head: Symbol
    previous_tail_word: int
    previous_trace_bits: Tuple[int, ...]
    previous_resource_limit: int
    previous_tape: "_TwoStackTape"
    protocol_step_was_applied: bool


class _DecodedBranch(NamedTuple):
    macro_word: int
    tail_word: int
    trace_bits: Tuple[int, ...]
    resource_limit: int
    control_state_index: int
    head_position: int
    tape: "_TwoStackTape"
    history: Tuple[_DecodedHistoryRecord, ...]


@dataclass(frozen=True)
class ObserverObservation:
    """Observer-facing projection Obs(C)."""

    control_state: State
    macro_word: int
    tail_word: int
    tape_view: str
    # Bubble-level observed space state is not per-branch; kept optional.
    observed_macro_word: Optional[int] = None


class Observer:
    """A single observer that maintains a parallel branch set.

    Public intent:
      - External callers interact with ONE observer object.
      - The observer internally maintains a set of parallel branches (machines).
      - COMMIT is an operation on the internal branch set.

    The first branch is treated as the "primary" branch for convenience accessors.
    """

    def __init__(
        self,
        protocol: ZeckendorfProtocol,
        *,
        transition_table: Mapping[Tuple[State, Symbol], Transition],
        start_state: State,
        halt_states: Set[State],
        macro_word: int,
        tail_word_start: int = 0,
        resource_limit: int = 1,
        trace_seed_bits: Optional[Iterable[int]] = None,
        tape_input_bits: Optional[Iterable[int]] = None,
        blank_symbol: Symbol = "_",
        couple_protocol_each_step: bool = False,
        _branches: Optional[Iterable["_ObserverMachine"]] = None,
    ) -> None:
        self._protocol = protocol
        self._transition_table: Dict[Tuple[State, Symbol], Transition] = dict(transition_table)
        self._halt_states: Set[State] = set(halt_states)
        self._blank_symbol: Symbol = str(blank_symbol)
        self._couple_protocol_each_step: bool = bool(couple_protocol_each_step)

        if _branches is not None:
            self._branches: list["_ObserverMachine"] = list(_branches)
        else:
            self._branches = [
                _ObserverMachine(
                    protocol,
                    transition_table=self._transition_table,
                    start_state=str(start_state),
                    halt_states=set(self._halt_states),
                    macro_word=int(macro_word),
                    tail_word_start=int(tail_word_start),
                    resource_limit=int(resource_limit),
                    trace_seed_bits=trace_seed_bits,
                    tape_input_bits=tape_input_bits,
                    blank_symbol=str(self._blank_symbol),
                    couple_protocol_each_step=bool(self._couple_protocol_each_step),
                )
            ]

    @staticmethod
    def merge(observers: Iterable["Observer"]) -> "Observer":
        """Merge branch sets from multiple observers into one observer."""

        observers_list = list(observers)
        if not observers_list:
            raise ValueError("observers must be non-empty")
        first = observers_list[0]
        all_branches: list["_ObserverMachine"] = []
        for obs in observers_list:
            all_branches.extend(obs._branches)
        return Observer(
            first._protocol,
            transition_table=first._transition_table,
            start_state=first._branches[0].control_state if first._branches else "START",
            halt_states=set(first._halt_states),
            macro_word=int(first.macro_word),
            tail_word_start=int(first.tail_word),
            resource_limit=int(first.resource_limit),
            blank_symbol=str(first._blank_symbol),
            couple_protocol_each_step=bool(first._couple_protocol_each_step),
            _branches=all_branches,
        )

    # -------------------------
    # Branch-set public API
    # -------------------------
    def branch_count(self) -> int:
        return int(len(self._branches))

    def obs(self, left: int = -16, right: int = 16) -> list[ObserverObservation]:
        return [b.observe(left=left, right=right) for b in self._branches]

    def space_blocks_y6(self) -> list[list[int]]:
        """Encode all branches' full states as Y6-block strings.

        This returns one Y6^* encoding per branch, including protocol registers and undo history.
        """

        return [b.space_blocks_y6() for b in self._branches]

    def space_cost_y6(self) -> int:
        """Total Y6-space cost across all kept branches (scheme B)."""

        return int(sum(int(b.space_cost_y6()) for b in self._branches))

    def observed_macro_word(self, observation_setting: int = 0) -> int:
        """Default y_obs readout (paper-closed default).

        Implements the paper's default:
          - Sort bubble by Score_{y_con} (protocol.score_key)
          - Apply cyclic shift by s on the ordered list
          - Select the shifted first branch b*
          - Reconstruct N* (micro integer) for that branch
          - Return Unrank_{Y6}((N* + s) mod 21)
        """

        if not self._branches:
            raise RuntimeError("no branches available")
        proto = self._branches[0]._protocol
        sys = proto._sys  # internal access; observer layer is coupled to this protocol instance
        if int(sys.window_length) != 6:
            raise NotImplementedError("observed_macro_word default is defined for m=6 only")

        ordered = sorted(
            [b for b in self._branches if proto.is_ok_clo(b.protocol_state())],
            key=lambda b: proto.score_key(b.protocol_state()),
        )
        if not ordered:
            raise RuntimeError("no feasible branches available")
        B = len(ordered)
        s = int(observation_setting)
        b_star = ordered[int(s % B)]
        micro_integer = proto.score_key(b_star.protocol_state())[0]
        if int(micro_integer) >= 10**20:
            raise RuntimeError("failed to reconstruct micro integer for observed branch")
        return int(sys.unrank_y6((int(micro_integer) + int(s)) % 21))

    def tail_words(self) -> list[int]:
        return [int(b.tail_word) for b in self._branches]

    def macro_words(self) -> list[int]:
        return [int(b.macro_word) for b in self._branches]

    def commit(self) -> None:
        """Deterministic COMMIT under a single resource cap W.

        Scheme B semantics:
          - W is a single upper bound that constrains both:
            (i) how many branches can be kept, and
            (ii) how much encoded space-state storage can be kept.

        We implement this by keeping a deterministic prefix until the summed Y6-space
        cost would exceed W.
        """

        if not self._branches:
            return
        proto = self._branches[0]._protocol
        # Scheme B + endogenous W: treat W as a single shared cap for the observer.
        # If any branch has discovered a larger W, it should raise the global cap.
        cap_W = max(int(proto.beam_width_cap(b.protocol_state())) for b in self._branches)
        feasible = [b for b in self._branches if proto.is_ok_clo(b.protocol_state())]
        feasible.sort(key=lambda b: proto.score_key(b.protocol_state()))

        kept: list["_ObserverMachine"] = []
        used = 0
        for b in feasible:
            cost = int(b.space_cost_y6())
            if cost < 0:
                continue
            if used + cost > int(cap_W):
                break
            kept.append(b)
            used += cost
        # Propagate the (shared) cap_W into all kept branches.
        propagated: list["_ObserverMachine"] = []
        for b in kept:
            d = b._decode()
            d2 = d._replace(resource_limit=int(cap_W))
            if not b._write_space(d2):
                # If we cannot write under cap_W (should not happen since cap_W is a max),
                # drop the branch.
                continue
            propagated.append(b)
        self._branches = propagated

    def protocol_expand_one_step(self) -> int:
        """Expand the branch set by one protocol unfold step.

        For each current branch, try all available binary branch choices (0/1) for
        the protocol unfold step, cloning the branch when the step is defined.
        This grows the observer's parallel branch set (the "bubble frontier").

        Returns the new branch count (before any commit).
        """

        if not self._branches:
            return 0
        proto = self._branches[0]._protocol
        expanded: list["_ObserverMachine"] = []
        for b in self._branches:
            # Try both binary branch choices; invalid choices return None.
            for choice in (0, 1):
                next_state = proto.unfold_step(b.protocol_state(), branch_choice_bit=int(choice))
                if next_state is None:
                    continue
                expanded.append(b._clone_with_protocol_state(next_state))
        self._branches = expanded
        return int(len(self._branches))

    def protocol_expand_one_step_and_commit(self) -> int:
        """Expand by one protocol step and then apply deterministic commit."""

        if not self._branches:
            return 0
        proto = self._branches[0]._protocol

        # Endogenous W gain: only when the bubble actually discovers new micro explanations.
        before_micro = {
            int(proto.score_key(b.protocol_state())[0])
            for b in self._branches
            if proto.is_ok_clo(b.protocol_state())
        }

        self.protocol_expand_one_step()

        after_micro = {
            int(proto.score_key(b.protocol_state())[0])
            for b in self._branches
            if proto.is_ok_clo(b.protocol_state())
        }

        if len(after_micro) > len(before_micro):
            current_W = max(int(proto.beam_width_cap(b.protocol_state())) for b in self._branches)
            new_W = int(current_W) * 2
            for b in self._branches:
                d = b._decode()
                b._write_space(d._replace(resource_limit=int(new_W)))

        self.commit()
        return int(len(self._branches))

    # -------------------------
    # Primary-branch convenience API
    # -------------------------
    def _primary(self) -> "_ObserverMachine":
        if not self._branches:
            raise RuntimeError("no branches available")
        return self._branches[0]

    @property
    def control_state(self) -> State:
        return self._primary().control_state

    @property
    def head_position(self) -> int:
        return self._primary().head_position

    @property
    def macro_word(self) -> int:
        return self._primary().macro_word

    @property
    def tail_word(self) -> int:
        return self._primary().tail_word

    @property
    def trace_tape_length(self) -> int:
        return self._primary().trace_tape_length

    @property
    def resource_limit(self) -> int:
        return self._primary().resource_limit

    def is_halted(self) -> bool:
        return self._primary().is_halted()

    def view_tape(self, left: int = -16, right: int = 16) -> str:
        return self._primary().view_tape(left=left, right=right)

    def step(self) -> bool:
        """Step all branches once. Returns True iff at least one branch stepped."""

        any_executed = False
        for b in self._branches:
            any_executed = bool(b.step()) or any_executed
        return bool(any_executed)

    def undo_step(self) -> bool:
        """Undo one step on all branches. Returns True iff at least one branch undone."""

        any_undone = False
        for b in self._branches:
            any_undone = bool(b.undo_step()) or any_undone
        return bool(any_undone)


class _TwoStackTape:
    """A finite-support bidirectional tape represented as (L, head, R).

    Conventions:
      - left_stack: symbols left of head, nearest at the end ([-1] is offset -1)
      - right_stack: symbols right of head, nearest at the end ([-1] is offset +1)
    """

    def __init__(self, blank: Symbol) -> None:
        self._blank = str(blank)
        self._left: list[Symbol] = []
        self._head: Symbol = self._blank
        self._right: list[Symbol] = []

    def head_symbol(self) -> Symbol:
        return str(self._head)

    def set_head_symbol(self, symbol: Symbol) -> None:
        self._head = str(symbol)

    def move(self, delta: int) -> None:
        d = int(delta)
        if d == 0:
            return
        if d == 1:
            self._left.append(self._head)
            self._head = self._right.pop() if self._right else self._blank
            return
        if d == -1:
            self._right.append(self._head)
            self._head = self._left.pop() if self._left else self._blank
            return
        raise ValueError("head_move must be -1, 0, or +1")

    def symbol_at_offset(self, offset: int) -> Symbol:
        k = int(offset)
        if k == 0:
            return str(self._head)
        if k < 0:
            idx = -k
            return str(self._left[-idx]) if idx <= len(self._left) else self._blank
        idx = k
        return str(self._right[-idx]) if idx <= len(self._right) else self._blank

    def load_input_bits(self, bits: list[int], blank: Symbol) -> None:
        self._blank = str(blank)
        self._left = []
        if not bits:
            self._head = self._blank
            self._right = []
            return
        symbols = ["1" if (int(b) & 1) else "0" for b in bits]
        self._head = symbols[0]
        # Right side nearest is +1, which should be last element.
        self._right = list(reversed(symbols[1:]))

    def clone(self) -> "_TwoStackTape":
        out = _TwoStackTape(self._blank)
        out._left = list(self._left)
        out._head = str(self._head)
        out._right = list(self._right)
        return out

    def to_space_blocks_y6(self, beta0: int, beta1: int, beta_blank: int, beta_hash: int) -> list[int]:
        """Encode (L,head,R) into a Y6-block string SP_tape (paper realizability)."""

        def sym_to_block(sym: Symbol) -> int:
            s = str(sym)
            if s == "0":
                return int(beta0)
            if s == "1":
                return int(beta1)
            if s == self._blank:
                return int(beta_blank)
            # Fallback: treat unknown as blank (keeps encoding total).
            return int(beta_blank)

        left_blocks = [sym_to_block(s) for s in reversed(self._left)]
        head_block = sym_to_block(self._head)
        right_blocks = [sym_to_block(s) for s in reversed(self._right)]
        return [*left_blocks, int(beta_hash), int(head_block), int(beta_hash), *right_blocks]

    @staticmethod
    def from_space_blocks_y6(
        blocks: List[int],
        *,
        beta0: int,
        beta1: int,
        beta_blank: int,
        beta_hash: int,
        blank_symbol: Symbol,
    ) -> "_TwoStackTape":
        """Decode a tape from blocks of the form left + # + head + # + right."""

        if int(beta_hash) not in blocks:
            raise ValueError("invalid tape blocks: missing separators")
        first = blocks.index(int(beta_hash))
        if first + 2 > len(blocks):
            raise ValueError("invalid tape blocks")
        second = blocks.index(int(beta_hash), first + 1)
        if second != first + 2:
            # We require exactly one head-block between the two hashes.
            raise ValueError("invalid tape blocks: expected one head block")

        left_blocks = blocks[:first]
        head_block = int(blocks[first + 1])
        right_blocks = blocks[second + 1 :]

        def block_to_symbol(b: int) -> Symbol:
            if int(b) == int(beta0):
                return "0"
            if int(b) == int(beta1):
                return "1"
            if int(b) == int(beta_blank):
                return str(blank_symbol)
            # Unknown block: treat as blank (total decoding).
            return str(blank_symbol)

        tape = _TwoStackTape(blank=str(blank_symbol))
        # left_blocks were encoded far->near to make _left[-1] be near.
        tape._left = [block_to_symbol(b) for b in left_blocks]
        tape._head = block_to_symbol(head_block)
        tape._right = [block_to_symbol(b) for b in right_blocks]
        return tape


def _encode_int_to_y6_blocks(n: int, *, beta0: int, beta1: int, beta_hash: int) -> list[int]:
    """Encode a nonnegative integer as little-endian bits terminated by beta_hash."""

    x = int(n)
    if x < 0:
        raise ValueError("integer must be nonnegative")
    out: list[int] = []
    while x > 0:
        out.append(int(beta1) if (x & 1) else int(beta0))
        x >>= 1
    out.append(int(beta_hash))
    return out


def _decode_int_from_y6_blocks(
    blocks: List[int], start: int, *, beta0: int, beta1: int, beta_hash: int
) -> Tuple[int, int]:
    """Decode a little-endian integer terminated by beta_hash. Returns (value, next_index)."""

    idx = int(start)
    value = 0
    shift = 0
    while idx < len(blocks):
        b = int(blocks[idx])
        idx += 1
        if b == int(beta_hash):
            return int(value), int(idx)
        if b == int(beta1):
            value |= 1 << shift
        elif b == int(beta0):
            pass
        else:
            raise ValueError("invalid integer encoding block")
        shift += 1
    raise ValueError("unterminated integer encoding")


def _decode_bits_from_y6_blocks(
    blocks: List[int], start: int, *, beta0: int, beta1: int, beta_hash: int
) -> Tuple[Tuple[int, ...], int]:
    """Decode bits terminated by beta_hash. Returns (bits_tuple, next_index)."""

    idx = int(start)
    out: list[int] = []
    while idx < len(blocks):
        b = int(blocks[idx])
        idx += 1
        if b == int(beta_hash):
            return tuple(int(x) for x in out), int(idx)
        if b == int(beta1):
            out.append(1)
        elif b == int(beta0):
            out.append(0)
        else:
            raise ValueError("invalid bit encoding block")
    raise ValueError("unterminated bit encoding")


def _encode_bits_to_y6_blocks(bits: Iterable[int], *, beta0: int, beta1: int, beta_hash: int) -> list[int]:
    out: list[int] = [int(beta1) if (int(b) & 1) else int(beta0) for b in bits]
    out.append(int(beta_hash))
    return out


def _encode_symbol_to_y6_block(symbol: Symbol, *, beta0: int, beta1: int, beta_blank: int) -> int:
    s = str(symbol)
    if s == "0":
        return int(beta0)
    if s == "1":
        return int(beta1)
    return int(beta_blank)


def _encode_int_to_y6_blocks(n: int, *, beta0: int, beta1: int, beta_hash: int) -> list[int]:
    """Encode a nonnegative integer as little-endian bits terminated by beta_hash."""

    x = int(n)
    if x < 0:
        raise ValueError("integer must be nonnegative")
    out: list[int] = []
    while x > 0:
        out.append(int(beta1) if (x & 1) else int(beta0))
        x >>= 1
    out.append(int(beta_hash))
    return out


def _encode_bits_to_y6_blocks(bits: Iterable[int], *, beta0: int, beta1: int, beta_hash: int) -> list[int]:
    """Encode a finite bitstring terminated by beta_hash."""

    out: list[int] = [int(beta1) if (int(b) & 1) else int(beta0) for b in bits]
    out.append(int(beta_hash))
    return out


def _encode_symbol_to_y6_block(symbol: Symbol, *, beta0: int, beta1: int, beta_blank: int) -> int:
    s = str(symbol)
    if s == "0":
        return int(beta0)
    if s == "1":
        return int(beta1)
    return int(beta_blank)


class _ObserverMachine:
    """Turing-machine-like observer runner.

    Public responsibilities:
      - Maintain a finite control state and a read/write head over an unbounded tape.
      - Provide deterministic step and reversible undo_step.
      - Provide accessors for a bounded "view" of the tape (observer readout).
      - Optionally couple each observer step with a protocol unfold/fold step.

    The observer machine does NOT access ontic internals directly; it only uses
    the public protocol API and stores the protocol state as an opaque value.
    """

    def __init__(
        self,
        protocol: ZeckendorfProtocol,
        *,
        transition_table: Mapping[Tuple[State, Symbol], Transition],
        start_state: State,
        halt_states: Set[State],
        macro_word: int,
        tail_word_start: int = 0,
        resource_limit: int = 1,
        trace_seed_bits: Optional[Iterable[int]] = None,
        tape_input_bits: Optional[Iterable[int]] = None,
        blank_symbol: Symbol = "_",
        couple_protocol_each_step: bool = False,
    ) -> None:
        self._protocol = protocol
        self._transition_table: Dict[Tuple[State, Symbol], Transition] = dict(transition_table)
        self._halt_states: Set[State] = set(halt_states)
        self._blank_symbol: Symbol = str(blank_symbol)
        self._couple_protocol_each_step: bool = bool(couple_protocol_each_step)

        state_names: Set[str] = set()
        state_names.add(str(start_state))
        state_names |= {str(s) for (s, _) in self._transition_table.keys()}
        state_names |= {str(tr.next_state) for tr in self._transition_table.values()}
        state_names |= {str(s) for s in self._halt_states}
        self._state_universe: List[str] = sorted(state_names)
        self._state_to_index: Dict[str, int] = {s: i for i, s in enumerate(self._state_universe)}
        self._index_to_state: Dict[int, str] = {i: s for i, s in enumerate(self._state_universe)}

        # Unique register: the entire machine state is stored as a Y6-block string (space state).
        sys = self._protocol._sys
        if int(sys.window_length) != 6:
            raise NotImplementedError("Observer machine space-state encoding is defined for m=6 only")
        beta0, beta1, beta_blank, beta_hash = sys.y6_default_blocks()
        mw = int(macro_word)
        if not sys.is_macro_word_in_language(mw):
            raise ValueError("macro_word must be in Y6")

        tail0 = int(tail_word_start)
        trace0 = tuple(int(b) & 1 for b in ([] if trace_seed_bits is None else list(trace_seed_bits)))
        W0 = int(resource_limit)
        if W0 < 1:
            raise ValueError("resource_limit must be >= 1")

        tape = _TwoStackTape(blank=str(self._blank_symbol))
        if tape_input_bits is not None:
            tape.load_input_bits(list(tape_input_bits), blank=str(self._blank_symbol))

        control_idx = int(self._state_to_index.get(str(start_state), 0))
        decoded0 = _DecodedBranch(
            macro_word=mw,
            tail_word=tail0,
            trace_bits=trace0,
            resource_limit=W0,
            control_state_index=control_idx,
            head_position=0,
            tape=tape,
            history=(),
        )
        self._space_blocks: list[int] = self._encode_branch_state(decoded0, beta0, beta1, beta_blank, beta_hash)
        if len(self._space_blocks) > W0:
            raise ValueError("resource_limit too small to encode initial space state")

    # -------------------------
    # Public ontic guard (CHECK_Clo)
    # -------------------------
    def check_ok_clo(self) -> bool:
        """CHECK_Clo: return True iff OK_Clo(macro_word, tail_word)=1."""
        return bool(self._protocol.is_ok_clo(self.protocol_state()))

    # -------------------------
    # Public read-only accessors
    # -------------------------
    @property
    def control_state(self) -> State:
        d = self._decode()
        return str(self._index_to_state.get(int(d.control_state_index), "START"))

    @property
    def head_position(self) -> int:
        return int(self._decode().head_position)

    @property
    def macro_word(self) -> int:
        return int(self._decode().macro_word)

    @property
    def tail_word(self) -> int:
        return int(self._decode().tail_word)

    @property
    def trace_tape_length(self) -> int:
        return int(len(self._decode().trace_bits))

    @property
    def energy_tape_length(self) -> int:
        raise AttributeError("energy_tape_length has been removed; use resource_limit instead")

    @property
    def resource_limit(self) -> int:
        return int(self._decode().resource_limit)

    def is_halted(self) -> bool:
        return str(self.control_state) in self._halt_states

    # -------------------------
    # Public tape view utilities
    # -------------------------
    def read_symbol(self, position: Optional[int] = None) -> Symbol:
        offset = 0 if position is None else int(position)
        return self._decode().tape.symbol_at_offset(offset)

    def view_tape(self, left: int = -16, right: int = 16) -> str:
        """Return a bounded view around the head position (inclusive)."""

        l = int(left)
        r = int(right)
        if l > r:
            raise ValueError("left must be <= right")
        symbols = [self.read_symbol(offset) for offset in range(l, r + 1)]
        return "".join(symbols)

    def observe(self, left: int = -16, right: int = 16) -> ObserverObservation:
        """Obs(C) = (control_state, macro_word, tail_word, View(tape,head))."""

        return ObserverObservation(
            control_state=str(self.control_state),
            macro_word=int(self.macro_word),
            tail_word=int(self.tail_word),
            tape_view=self.view_tape(left=left, right=right),
        )

    # -------------------------
    # Public stepping API
    # -------------------------
    def step(self) -> bool:
        """Execute one observer step. Returns True if a step was executed."""

        if self.is_halted():
            return False

        # Enforce ontic feasibility guard if protocol coupling is enabled.
        if not self.check_ok_clo():
            return False

        decoded_before = self._decode()
        state_name = str(self._index_to_state.get(int(decoded_before.control_state_index), "START"))
        symbol_under_head = decoded_before.tape.symbol_at_offset(0)
        transition = self._transition_table.get((state_name, symbol_under_head))
        if transition is None:
            # Undefined transition => halting by convention.
            halt_name = next(iter(self._halt_states)) if self._halt_states else "HALT"
            decoded_after = decoded_before._replace(control_state_index=int(self._state_to_index.get(halt_name, 0)))
            self._write_space(decoded_after)
            return False

        # Optional coupled protocol step (updates tail/trace/W).
        protocol_step_was_applied = False
        tail_word_next = int(decoded_before.tail_word)
        trace_bits_next = tuple(decoded_before.trace_bits)
        W_next = int(decoded_before.resource_limit)
        if self._couple_protocol_each_step:
            ps = self.protocol_state()
            ps_next = self._protocol.unfold_step(ps, branch_choice_bit=0)
            if ps_next is None:
                return False
            tail_word_next = int(ps_next.tail_word)
            trace_bits_next = tuple(int(b) & 1 for b in ps_next._trace_tape._bits)
            W_next = int(ps_next.resource_limit)
            protocol_step_was_applied = True

        # Apply TM-like update to tape/head/control.
        tape_next = decoded_before.tape.clone()
        tape_next.set_head_symbol(str(transition.write_symbol))
        tape_next.move(int(transition.head_move))
        head_next = int(decoded_before.head_position + int(transition.head_move))
        next_state_idx = int(self._state_to_index.get(str(transition.next_state), 0))

        # Append reversible history record into the unique space state.
        history_new = list(decoded_before.history)
        history_new.append(
            _DecodedHistoryRecord(
                previous_state_index=int(decoded_before.control_state_index),
                previous_head_position=int(decoded_before.head_position),
                previous_symbol_under_head=str(symbol_under_head),
                previous_tail_word=int(decoded_before.tail_word),
                previous_trace_bits=tuple(decoded_before.trace_bits),
                previous_resource_limit=int(decoded_before.resource_limit),
                previous_tape=decoded_before.tape.clone(),
                protocol_step_was_applied=bool(protocol_step_was_applied),
            )
        )

        decoded_after = _DecodedBranch(
            macro_word=int(decoded_before.macro_word),
            tail_word=int(tail_word_next),
            trace_bits=tuple(trace_bits_next),
            resource_limit=int(W_next),
            control_state_index=int(next_state_idx),
            head_position=int(head_next),
            tape=tape_next,
            history=tuple(history_new),
        )
        return bool(self._write_space(decoded_after))

    # -------------------------
    # Public explicit protocol instructions (U_STEP / D_STEP)
    # -------------------------
    def protocol_unfold_step(self) -> bool:
        """U_STEP: apply one protocol unfold_step to (macro_word,tail_word,trace,energy)."""

        if not self.check_ok_clo():
            return False
        decoded_before = self._decode()
        ps = self.protocol_state()
        ps_next = self._protocol.unfold_step(ps, branch_choice_bit=0)
        if ps_next is None:
            return False

        history_new = list(decoded_before.history)
        history_new.append(
            _DecodedHistoryRecord(
                previous_state_index=int(decoded_before.control_state_index),
                previous_head_position=int(decoded_before.head_position),
                previous_symbol_under_head=str(decoded_before.tape.symbol_at_offset(0)),
                previous_tail_word=int(decoded_before.tail_word),
                previous_trace_bits=tuple(decoded_before.trace_bits),
                previous_resource_limit=int(decoded_before.resource_limit),
                previous_tape=decoded_before.tape.clone(),
                protocol_step_was_applied=True,
            )
        )
        decoded_after = _DecodedBranch(
            macro_word=int(decoded_before.macro_word),
            tail_word=int(ps_next.tail_word),
            trace_bits=tuple(int(b) & 1 for b in ps_next._trace_tape._bits),
            resource_limit=int(ps_next.resource_limit),
            control_state_index=int(decoded_before.control_state_index),
            head_position=int(decoded_before.head_position),
            tape=decoded_before.tape.clone(),
            history=tuple(history_new),
        )
        return bool(self._write_space(decoded_after))

    def protocol_fold_step(self) -> bool:
        """D_STEP: apply one protocol fold_step (rollback) to the protocol state."""
        decoded_before = self._decode()
        ps = self.protocol_state()
        reverted = self._protocol.fold_step(ps)
        if reverted is None:
            return False
        decoded_after = _DecodedBranch(
            macro_word=int(decoded_before.macro_word),
            tail_word=int(reverted.tail_word),
            trace_bits=tuple(int(b) & 1 for b in reverted._trace_tape._bits),
            resource_limit=int(reverted.resource_limit),
            control_state_index=int(decoded_before.control_state_index),
            head_position=int(decoded_before.head_position),
            tape=decoded_before.tape.clone(),
            history=tuple(decoded_before.history),
        )
        return bool(self._write_space(decoded_after))

    def undo_step(self) -> bool:
        """Undo one previously executed observer step. Returns True if undone."""

        decoded_before = self._decode()
        if not decoded_before.history:
            return False

        history = list(decoded_before.history)
        rec = history.pop()
        restored = _DecodedBranch(
            macro_word=int(decoded_before.macro_word),
            tail_word=int(rec.previous_tail_word),
            trace_bits=tuple(int(b) & 1 for b in rec.previous_trace_bits),
            resource_limit=int(rec.previous_resource_limit),
            control_state_index=int(rec.previous_state_index),
            head_position=int(rec.previous_head_position),
            tape=rec.previous_tape.clone(),
            history=tuple(history),
        )
        return bool(self._write_space(restored))

    def run(self, max_steps: int = 10_000) -> int:
        """Run until halt/undefined transition or max_steps. Returns executed step count."""

        steps_executed = 0
        limit = int(max_steps)
        while steps_executed < limit and self.step():
            steps_executed += 1
        return int(steps_executed)

    # -------------------------
    # Internal helpers
    # -------------------------
    def _clone_with_protocol_state(self, protocol_state: ProtocolState) -> "_ObserverMachine":
        """Internal: clone this machine with a replaced protocol state.

        This is used to materialize parallel branches under different protocol
        unfold choices. The clone does not share mutable tape state.
        """

        clone = _ObserverMachine(
            self._protocol,
            transition_table=self._transition_table,
            start_state=str(self.control_state),
            halt_states=set(self._halt_states),
            macro_word=int(self.macro_word),
            tail_word_start=int(self.tail_word),
            resource_limit=int(self.resource_limit),
            trace_seed_bits=None,
            tape_input_bits=None,
            blank_symbol=str(self._blank_symbol),
            couple_protocol_each_step=bool(self._couple_protocol_each_step),
        )
        # Replace protocol registers inside the single space register.
        d = self._decode()
        replaced = _DecodedBranch(
            macro_word=int(d.macro_word),
            tail_word=int(protocol_state.tail_word),
            trace_bits=tuple(int(b) & 1 for b in protocol_state._trace_tape._bits),
            resource_limit=int(protocol_state.resource_limit),
            control_state_index=int(d.control_state_index),
            head_position=int(d.head_position),
            tape=d.tape.clone(),
            history=tuple(d.history),
        )
        clone._space_blocks = self._encode_branch_state(
            replaced, *self._protocol._sys.y6_default_blocks()
        )
        return clone

    def _write_symbol_at_head(self, symbol: Symbol) -> None:
        # Internal legacy helper kept for API parity; all writes go through decoded tape now.
        raise RuntimeError("direct tape writes are not allowed; state is stored only as space blocks")

    def protocol_state(self) -> ProtocolState:
        """Reconstruct ProtocolState from the unique space-state register."""

        d = self._decode()
        return self._protocol.create_state(
            macro_word=int(d.macro_word),
            tail_word=int(d.tail_word),
            resource_limit=int(d.resource_limit),
            trace_seed_bits=list(int(b) & 1 for b in d.trace_bits),
        )

    def space_blocks_y6(self) -> list[int]:
        return [int(b) for b in self._space_blocks]

    def space_cost_y6(self) -> int:
        return int(len(self._space_blocks))

    def _decode(self) -> _DecodedBranch:
        sys = self._protocol._sys
        beta0, beta1, beta_blank, beta_hash = sys.y6_default_blocks()
        return self._decode_branch_state(
            list(self._space_blocks),
            beta0=beta0,
            beta1=beta1,
            beta_blank=beta_blank,
            beta_hash=beta_hash,
            blank_symbol=str(self._blank_symbol),
        )

    def _write_space(self, decoded: _DecodedBranch) -> bool:
        sys = self._protocol._sys
        beta0, beta1, beta_blank, beta_hash = sys.y6_default_blocks()
        blocks = self._encode_branch_state(decoded, beta0, beta1, beta_blank, beta_hash)
        if len(blocks) > int(decoded.resource_limit):
            return False
        self._space_blocks = blocks
        return True

    @staticmethod
    def _encode_branch_state(
        decoded: _DecodedBranch, beta0: int, beta1: int, beta_blank: int, beta_hash: int
    ) -> list[int]:
        blocks: list[int] = []
        blocks.append(int(decoded.macro_word))
        blocks.append(int(beta_hash))
        blocks.extend(_encode_int_to_y6_blocks(int(decoded.tail_word), beta0=beta0, beta1=beta1, beta_hash=beta_hash))
        blocks.extend(_encode_bits_to_y6_blocks(decoded.trace_bits, beta0=beta0, beta1=beta1, beta_hash=beta_hash))
        blocks.extend(
            _encode_int_to_y6_blocks(int(decoded.resource_limit), beta0=beta0, beta1=beta1, beta_hash=beta_hash)
        )
        blocks.extend(
            _encode_int_to_y6_blocks(
                int(decoded.control_state_index), beta0=beta0, beta1=beta1, beta_hash=beta_hash
            )
        )
        blocks.extend(_encode_int_to_y6_blocks(int(decoded.head_position), beta0=beta0, beta1=beta1, beta_hash=beta_hash))
        blocks.extend(decoded.tape.to_space_blocks_y6(beta0, beta1, beta_blank, beta_hash))
        blocks.append(int(beta_hash))

        blocks.extend(
            _encode_int_to_y6_blocks(int(len(decoded.history)), beta0=beta0, beta1=beta1, beta_hash=beta_hash)
        )
        for rec in decoded.history:
            blocks.extend(_encode_int_to_y6_blocks(int(rec.previous_state_index), beta0=beta0, beta1=beta1, beta_hash=beta_hash))
            blocks.extend(_encode_int_to_y6_blocks(int(rec.previous_head_position), beta0=beta0, beta1=beta1, beta_hash=beta_hash))
            blocks.append(_encode_symbol_to_y6_block(rec.previous_symbol_under_head, beta0=beta0, beta1=beta1, beta_blank=beta_blank))
            blocks.append(int(beta_hash))
            blocks.extend(_encode_int_to_y6_blocks(1 if rec.protocol_step_was_applied else 0, beta0=beta0, beta1=beta1, beta_hash=beta_hash))
            blocks.extend(_encode_int_to_y6_blocks(int(rec.previous_tail_word), beta0=beta0, beta1=beta1, beta_hash=beta_hash))
            blocks.extend(_encode_bits_to_y6_blocks(rec.previous_trace_bits, beta0=beta0, beta1=beta1, beta_hash=beta_hash))
            blocks.extend(_encode_int_to_y6_blocks(int(rec.previous_resource_limit), beta0=beta0, beta1=beta1, beta_hash=beta_hash))
            blocks.extend(rec.previous_tape.to_space_blocks_y6(beta0, beta1, beta_blank, beta_hash))
            blocks.append(int(beta_hash))
        blocks.append(int(beta_hash))
        blocks.append(int(beta_hash))
        return [int(b) for b in blocks]

    @staticmethod
    def _decode_branch_state(
        blocks: List[int],
        *,
        beta0: int,
        beta1: int,
        beta_blank: int,
        beta_hash: int,
        blank_symbol: Symbol,
    ) -> _DecodedBranch:
        if len(blocks) < 2:
            raise ValueError("space state too short")
        i = 0
        macro = int(blocks[i])
        i += 1
        if int(blocks[i]) != int(beta_hash):
            raise ValueError("invalid header delimiter")
        i += 1
        tail, i = _decode_int_from_y6_blocks(blocks, i, beta0=beta0, beta1=beta1, beta_hash=beta_hash)
        trace_bits, i = _decode_bits_from_y6_blocks(blocks, i, beta0=beta0, beta1=beta1, beta_hash=beta_hash)
        W, i = _decode_int_from_y6_blocks(blocks, i, beta0=beta0, beta1=beta1, beta_hash=beta_hash)
        control_idx, i = _decode_int_from_y6_blocks(blocks, i, beta0=beta0, beta1=beta1, beta_hash=beta_hash)
        head_pos, i = _decode_int_from_y6_blocks(blocks, i, beta0=beta0, beta1=beta1, beta_hash=beta_hash)

        # Tape: left + # + head + # + right + #delim
        tape_start = i
        first = blocks.index(int(beta_hash), tape_start)
        second = blocks.index(int(beta_hash), first + 1)
        if second != first + 2:
            raise ValueError("invalid tape encoding")
        third = blocks.index(int(beta_hash), second + 1)
        tape_blocks = blocks[tape_start:third]
        tape = _TwoStackTape.from_space_blocks_y6(
            list(tape_blocks),
            beta0=beta0,
            beta1=beta1,
            beta_blank=beta_blank,
            beta_hash=beta_hash,
            blank_symbol=str(blank_symbol),
        )
        i = third + 1

        hist_count, i = _decode_int_from_y6_blocks(blocks, i, beta0=beta0, beta1=beta1, beta_hash=beta_hash)
        history: list[_DecodedHistoryRecord] = []
        for _ in range(int(hist_count)):
            prev_state_idx, i = _decode_int_from_y6_blocks(blocks, i, beta0=beta0, beta1=beta1, beta_hash=beta_hash)
            prev_head, i = _decode_int_from_y6_blocks(blocks, i, beta0=beta0, beta1=beta1, beta_hash=beta_hash)
            sym_block = int(blocks[i])
            i += 1
            if int(blocks[i]) != int(beta_hash):
                raise ValueError("invalid symbol delimiter")
            i += 1
            prev_symbol = (
                "0"
                if sym_block == int(beta0)
                else "1"
                if sym_block == int(beta1)
                else str(blank_symbol)
                if sym_block == int(beta_blank)
                else str(blank_symbol)
            )
            applied, i = _decode_int_from_y6_blocks(blocks, i, beta0=beta0, beta1=beta1, beta_hash=beta_hash)
            prev_tail, i = _decode_int_from_y6_blocks(blocks, i, beta0=beta0, beta1=beta1, beta_hash=beta_hash)
            prev_trace, i = _decode_bits_from_y6_blocks(blocks, i, beta0=beta0, beta1=beta1, beta_hash=beta_hash)
            prev_W, i = _decode_int_from_y6_blocks(blocks, i, beta0=beta0, beta1=beta1, beta_hash=beta_hash)
            # prev tape
            tape_start = i
            first = blocks.index(int(beta_hash), tape_start)
            second = blocks.index(int(beta_hash), first + 1)
            if second != first + 2:
                raise ValueError("invalid prev tape encoding")
            third = blocks.index(int(beta_hash), second + 1)
            prev_tape_blocks = blocks[tape_start:third]
            prev_tape = _TwoStackTape.from_space_blocks_y6(
                list(prev_tape_blocks),
                beta0=beta0,
                beta1=beta1,
                beta_blank=beta_blank,
                beta_hash=beta_hash,
                blank_symbol=str(blank_symbol),
            )
            i = third + 1
            history.append(
                _DecodedHistoryRecord(
                    previous_state_index=int(prev_state_idx),
                    previous_head_position=int(prev_head),
                    previous_symbol_under_head=str(prev_symbol),
                    previous_tail_word=int(prev_tail),
                    previous_trace_bits=tuple(int(b) & 1 for b in prev_trace),
                    previous_resource_limit=int(prev_W),
                    previous_tape=prev_tape,
                    protocol_step_was_applied=bool(int(applied) != 0),
                )
            )
        return _DecodedBranch(
            macro_word=int(macro),
            tail_word=int(tail),
            trace_bits=tuple(int(b) & 1 for b in trace_bits),
            resource_limit=int(W),
            control_state_index=int(control_idx),
            head_position=int(head_pos),
            tape=tape,
            history=tuple(history),
        )

