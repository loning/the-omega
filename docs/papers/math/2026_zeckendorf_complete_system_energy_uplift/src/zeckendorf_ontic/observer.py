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
from typing import Dict, Iterable, Mapping, Optional, Set, Tuple

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
class _HistoryRecord:
    previous_state: State
    previous_head_position: int
    previous_symbol_under_head: Symbol
    previous_protocol_state: ProtocolState
    protocol_step_was_applied: bool


@dataclass(frozen=True)
class ObserverObservation:
    """Observer-facing projection Obs(C)."""

    control_state: State
    macro_word: int
    tail_word: int
    tape_view: str


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
        _branches: Optional[Iterable["ObserverMachine"]] = None,
    ) -> None:
        self._protocol = protocol
        self._transition_table: Dict[Tuple[State, Symbol], Transition] = dict(transition_table)
        self._halt_states: Set[State] = set(halt_states)
        self._blank_symbol: Symbol = str(blank_symbol)
        self._couple_protocol_each_step: bool = bool(couple_protocol_each_step)

        if _branches is not None:
            self._branches: list["ObserverMachine"] = list(_branches)
        else:
            self._branches = [
                ObserverMachine(
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
        all_branches: list["ObserverMachine"] = []
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

    def tail_words(self) -> list[int]:
        return [int(b.tail_word) for b in self._branches]

    def macro_words(self) -> list[int]:
        return [int(b.macro_word) for b in self._branches]

    def commit(self) -> None:
        """Deterministic COMMIT: drop infeasible branches, then truncate by cap."""

        if not self._branches:
            return
        proto = self._branches[0]._protocol
        cap = min(proto.beam_width_cap(b._protocol_state) for b in self._branches)
        feasible = [b for b in self._branches if proto.is_ok_clo(b._protocol_state)]
        feasible.sort(key=lambda b: proto.score_key(b._protocol_state))
        self._branches = feasible[: min(int(cap), len(feasible))]

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
        expanded: list["ObserverMachine"] = []
        for b in self._branches:
            # Try both binary branch choices; invalid choices return None.
            for choice in (0, 1):
                next_state = proto.unfold_step(b._protocol_state, branch_choice_bit=int(choice))
                if next_state is None:
                    continue
                expanded.append(b._clone_with_protocol_state(next_state))
        self._branches = expanded
        return int(len(self._branches))

    def protocol_expand_one_step_and_commit(self) -> int:
        """Expand by one protocol step and then apply deterministic commit."""

        self.protocol_expand_one_step()
        self.commit()
        return int(len(self._branches))

    # -------------------------
    # Primary-branch convenience API
    # -------------------------
    def _primary(self) -> "ObserverMachine":
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


class ObserverBranchSet:
    """A parallel branch set of observer configurations.

    This is the object that COMMIT operates on in the paper.
    """

    def __init__(self, branches: Iterable["ObserverMachine"]) -> None:
        self._branches = list(branches)

    def branches(self) -> list["ObserverMachine"]:
        return list(self._branches)

    def commit(self) -> "ObserverBranchSet":
        """Deterministic COMMIT based on protocol beam width and score_key."""

        if not self._branches:
            return ObserverBranchSet([])
        proto = self._branches[0]._protocol
        # Use the smallest beam width among branches as a conservative cap.
        cap = min(proto.beam_width_cap(b._protocol_state) for b in self._branches)
        # Drop infeasible branches first.
        feasible = [b for b in self._branches if proto.is_ok_clo(b._protocol_state)]
        feasible.sort(key=lambda b: proto.score_key(b._protocol_state))
        kept = feasible[: min(int(cap), len(feasible))]
        return ObserverBranchSet(kept)

    def obs(self, left: int = -16, right: int = 16) -> list[ObserverObservation]:
        """Observer projection Obs applied to each branch."""

        return [b.observe(left=left, right=right) for b in self._branches]


class ObserverMachine:
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

        self._control_state: State = str(start_state)
        self._head_position: int = 0
        self._tape: Dict[int, Symbol] = {}  # sparse; missing = blank
        self._history: list[_HistoryRecord] = []

        trace_bits_list = None if trace_seed_bits is None else list(trace_seed_bits)
        self._protocol_state: ProtocolState = self._protocol.create_state(
            macro_word=int(macro_word),
            tail_word=int(tail_word_start),
            resource_limit=int(resource_limit),
            trace_seed_bits=trace_bits_list,
        )

        if tape_input_bits is not None:
            self._write_input_bits(list(tape_input_bits))

    # -------------------------
    # Public ontic guard (CHECK_Clo)
    # -------------------------
    def check_ok_clo(self) -> bool:
        """CHECK_Clo: return True iff OK_Clo(macro_word, tail_word)=1."""

        return bool(self._protocol.is_ok_clo(self._protocol_state))

    # -------------------------
    # Public read-only accessors
    # -------------------------
    @property
    def control_state(self) -> State:
        return str(self._control_state)

    @property
    def head_position(self) -> int:
        return int(self._head_position)

    @property
    def macro_word(self) -> int:
        return int(self._protocol_state.macro_word)

    @property
    def tail_word(self) -> int:
        return int(self._protocol_state.tail_word)

    @property
    def trace_tape_length(self) -> int:
        return int(self._protocol_state.trace_tape_length)

    @property
    def energy_tape_length(self) -> int:
        raise AttributeError("energy_tape_length has been removed; use resource_limit instead")

    @property
    def resource_limit(self) -> int:
        return int(self._protocol_state.resource_limit)

    def is_halted(self) -> bool:
        return self._control_state in self._halt_states

    # -------------------------
    # Public tape view utilities
    # -------------------------
    def read_symbol(self, position: Optional[int] = None) -> Symbol:
        tape_position = self._head_position if position is None else int(position)
        return self._tape.get(tape_position, self._blank_symbol)

    def view_tape(self, left: int = -16, right: int = 16) -> str:
        """Return a bounded view around the head position (inclusive)."""

        l = int(left)
        r = int(right)
        if l > r:
            raise ValueError("left must be <= right")
        symbols = [self.read_symbol(self._head_position + offset) for offset in range(l, r + 1)]
        return "".join(symbols)

    def observe(self, left: int = -16, right: int = 16) -> ObserverObservation:
        """Obs(C) = (control_state, macro_word, tail_word, View(tape,head))."""

        return ObserverObservation(
            control_state=str(self._control_state),
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

        symbol_under_head = self.read_symbol()
        transition = self._transition_table.get((self._control_state, symbol_under_head))
        if transition is None:
            # Undefined transition => halting by convention.
            self._control_state = next(iter(self._halt_states)) if self._halt_states else "HALT"
            return False

        previous_state = self._control_state
        previous_head_position = self._head_position
        previous_symbol_under_head = symbol_under_head
        previous_protocol_state = self._protocol_state

        protocol_step_was_applied = False
        if self._couple_protocol_each_step:
            next_protocol_state = self._protocol.unfold_step(self._protocol_state, branch_choice_bit=0)
            if next_protocol_state is None:
                # Resource or feasibility prevents coupling; treat as no-step.
                return False
            self._protocol_state = next_protocol_state
            protocol_step_was_applied = True

        # Apply the external (TM-like) semantics.
        self._write_symbol_at_head(transition.write_symbol)
        self._head_position = int(self._head_position + int(transition.head_move))
        self._control_state = str(transition.next_state)

        self._history.append(
            _HistoryRecord(
                previous_state=str(previous_state),
                previous_head_position=int(previous_head_position),
                previous_symbol_under_head=str(previous_symbol_under_head),
                previous_protocol_state=previous_protocol_state,
                protocol_step_was_applied=bool(protocol_step_was_applied),
            )
        )
        return True

    # -------------------------
    # Public explicit protocol instructions (U_STEP / D_STEP)
    # -------------------------
    def protocol_unfold_step(self) -> bool:
        """U_STEP: apply one protocol unfold_step to (macro_word,tail_word,trace,energy)."""

        if not self.check_ok_clo():
            return False
        next_protocol_state = self._protocol.unfold_step(self._protocol_state, branch_choice_bit=0)
        if next_protocol_state is None:
            return False
        self._history.append(
            _HistoryRecord(
                previous_state=str(self._control_state),
                previous_head_position=int(self._head_position),
                previous_symbol_under_head=str(self.read_symbol()),
                previous_protocol_state=self._protocol_state,
                protocol_step_was_applied=True,
            )
        )
        self._protocol_state = next_protocol_state
        return True

    def protocol_fold_step(self) -> bool:
        """D_STEP: apply one protocol fold_step (rollback) to the protocol state."""

        reverted = self._protocol.fold_step(self._protocol_state)
        if reverted is None:
            return False
        self._protocol_state = reverted
        return True

    def undo_step(self) -> bool:
        """Undo one previously executed observer step. Returns True if undone."""

        if not self._history:
            return False

        record = self._history.pop()

        # Undo TM-like effects.
        self._control_state = str(record.previous_state)
        self._head_position = int(record.previous_head_position)
        self._write_symbol_at_head(record.previous_symbol_under_head)

        # Undo coupled protocol evolution (if used).
        if record.protocol_step_was_applied:
            reverted = self._protocol.fold_step(self._protocol_state)
            if reverted is None or reverted != record.previous_protocol_state:
                # Strong invariant: coupled step must be strictly invertible.
                raise RuntimeError("protocol fold_step failed to invert unfold_step")
            self._protocol_state = reverted
        else:
            self._protocol_state = record.previous_protocol_state

        return True

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
    def _clone_with_protocol_state(self, protocol_state: ProtocolState) -> "ObserverMachine":
        """Internal: clone this machine with a replaced protocol state.

        This is used to materialize parallel branches under different protocol
        unfold choices. The clone does not share mutable tape state.
        """

        clone = ObserverMachine(
            self._protocol,
            transition_table=self._transition_table,
            start_state=str(self._control_state),
            halt_states=set(self._halt_states),
            macro_word=int(self.macro_word),
            tail_word_start=int(self.tail_word),
            resource_limit=int(self.resource_limit),
            trace_seed_bits=None,
            tape_input_bits=None,
            blank_symbol=str(self._blank_symbol),
            couple_protocol_each_step=bool(self._couple_protocol_each_step),
        )
        clone._control_state = str(self._control_state)
        clone._head_position = int(self._head_position)
        clone._tape = dict(self._tape)
        clone._history = list(self._history)
        clone._protocol_state = protocol_state
        return clone

    def _write_symbol_at_head(self, symbol: Symbol) -> None:
        write_symbol = str(symbol)
        if write_symbol == self._blank_symbol:
            self._tape.pop(self._head_position, None)
        else:
            self._tape[self._head_position] = write_symbol

    def _write_input_bits(self, input_bits: list[int]) -> None:
        # Write input bits starting at position 0, using symbols "0" and "1".
        for index, bit in enumerate(input_bits):
            symbol = "1" if int(bit) & 1 else "0"
            if symbol != self._blank_symbol:
                self._tape[int(index)] = symbol
        self._head_position = 0

