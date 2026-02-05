#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

from zeckendorf_ontic.ontic_system import OnticZeckendorfSystem
from zeckendorf_ontic.observer import Observer, Transition
from zeckendorf_ontic.protocol import ZeckendorfProtocol


class TestObserver(unittest.TestCase):
    def _min_initial_resource_limit(
        self,
        protocol: ZeckendorfProtocol,
        *,
        transition_table: dict,
        start_state: str,
        halt_states: set[str],
        macro_word: int,
        tail_word_start: int = 0,
        tape_input_bits: list[int] | None = None,
        couple_protocol_each_step: bool = False,
        max_W: int = 512,
    ) -> int:
        """Find the smallest W0 that can encode the initial space state."""

        for W in range(1, int(max_W) + 1):
            try:
                Observer(
                    protocol,
                    transition_table=transition_table,
                    start_state=start_state,
                    halt_states=halt_states,
                    macro_word=int(macro_word),
                    tail_word_start=int(tail_word_start),
                    resource_limit=int(W),
                    tape_input_bits=tape_input_bits,
                    couple_protocol_each_step=bool(couple_protocol_each_step),
                )
                return int(W)
            except ValueError:
                continue
        raise RuntimeError("failed to find a feasible initial W0 within search bound")

    def _min_W0_for_one_step(
        self,
        protocol: ZeckendorfProtocol,
        *,
        transition_table: dict,
        start_state: str,
        halt_states: set[str],
        macro_word: int,
        tail_word_start: int = 0,
        tape_input_bits: list[int] | None = None,
        couple_protocol_each_step: bool = False,
        max_W: int = 512,
    ) -> int:
        """Find the smallest W0 that allows executing one observer step."""

        for W in range(1, int(max_W) + 1):
            try:
                o = Observer(
                    protocol,
                    transition_table=transition_table,
                    start_state=start_state,
                    halt_states=halt_states,
                    macro_word=int(macro_word),
                    tail_word_start=int(tail_word_start),
                    resource_limit=int(W),
                    tape_input_bits=tape_input_bits,
                    couple_protocol_each_step=bool(couple_protocol_each_step),
                )
            except ValueError:
                continue
            if o.step():
                return int(W)
        raise RuntimeError("failed to find a feasible W0 for one step within search bound")

    def test_bubble_frontier_grows_under_resource_cap_m6_y0(self) -> None:
        """A single observer maintains a growing parallel branch set under W."""

        ontic_system = OnticZeckendorfSystem(window_length=6)
        protocol = ZeckendorfProtocol(ontic_system)

        # No-op TM semantics; we only use protocol-driven branch expansion here.
        transition_table = {
            ("START", "_"): Transition(next_state="START", write_symbol="_", head_move=0),
        }

        W0 = self._min_initial_resource_limit(
            protocol,
            transition_table=transition_table,
            start_state="START",
            halt_states={"HALT"},
            macro_word=0,
            tail_word_start=0,
            tape_input_bits=None,
            couple_protocol_each_step=False,
        )

        observer = Observer(
            protocol,
            transition_table=transition_table,
            start_state="START",
            halt_states={"HALT"},
            macro_word=0,  # y=0^6 has maximal fiber size
            tail_word_start=0,
            resource_limit=W0,
            couple_protocol_each_step=False,
        )

        counts = [observer.branch_count()]
        caps = [observer.resource_limit]

        # Repeatedly expand+commit. For y=0^6 in m=6 we expect W to grow (k(y)=2 => factor 2).
        for _ in range(4):
            observer.protocol_expand_one_step_and_commit()
            counts.append(observer.branch_count())
            caps.append(observer.resource_limit)
            # Scheme B: total encoded space cost must respect the cap.
            self.assertLessEqual(observer.space_cost_y6(), observer.resource_limit)

        # Bubble should grow from the initial single branch.
        self.assertGreaterEqual(max(counts), 2)
        # Resource cap should grow monotonically (in this fixed-y experiment).
        self.assertTrue(all(caps[i] <= caps[i + 1] for i in range(len(caps) - 1)))

    def test_step_and_undo_restore_tape_and_state(self) -> None:
        ontic_system = OnticZeckendorfSystem(window_length=6)
        protocol = ZeckendorfProtocol(ontic_system)

        # One-step machine: overwrite current symbol and halt.
        transition_table = {
            ("START", "0"): Transition(next_state="HALT", write_symbol="1", head_move=0),
            ("START", "_"): Transition(next_state="HALT", write_symbol="1", head_move=0),
        }

        # Scheme B: pick the smallest W0 that can execute one TM step (history growth costs space).
        W0 = self._min_W0_for_one_step(
            protocol,
            transition_table=transition_table,
            start_state="START",
            halt_states={"HALT"},
            macro_word=0,
            tail_word_start=0,
            tape_input_bits=[0],
            couple_protocol_each_step=False,
        )

        observer = Observer(
            protocol,
            transition_table=transition_table,
            start_state="START",
            halt_states={"HALT"},
            macro_word=0,
            tail_word_start=0,
            resource_limit=W0,
            tape_input_bits=[0],
            couple_protocol_each_step=False,
        )

        before_view = observer.view_tape(-1, 1)
        before_state = observer.control_state
        before_head = observer.head_position
        before_tail_word = observer.tail_word
        before_trace_length = observer.trace_tape_length
        before_resource_limit = observer.resource_limit

        executed = observer.step()
        self.assertTrue(executed)
        self.assertTrue(observer.is_halted())
        self.assertNotEqual(observer.view_tape(-1, 1), before_view)

        undone = observer.undo_step()
        self.assertTrue(undone)
        self.assertEqual(observer.view_tape(-1, 1), before_view)
        self.assertEqual(observer.control_state, before_state)
        self.assertEqual(observer.head_position, before_head)
        self.assertEqual(observer.tail_word, before_tail_word)
        self.assertEqual(observer.trace_tape_length, before_trace_length)
        self.assertEqual(observer.resource_limit, before_resource_limit)

    def test_coupled_protocol_step_is_reversible(self) -> None:
        ontic_system = OnticZeckendorfSystem(window_length=6)
        protocol = ZeckendorfProtocol(ontic_system)

        transition_table = {
            ("START", "_"): Transition(next_state="START", write_symbol="_", head_move=0),
        }

        # Scheme B: coupling also grows trace/W and writes history; find minimal W0 for one step.
        W0 = self._min_W0_for_one_step(
            protocol,
            transition_table=transition_table,
            start_state="START",
            halt_states={"HALT"},
            macro_word=0,
            tail_word_start=0,
            tape_input_bits=None,
            couple_protocol_each_step=True,
        )

        observer = Observer(
            protocol,
            transition_table=transition_table,
            start_state="START",
            halt_states={"HALT"},
            macro_word=0,
            tail_word_start=0,
            resource_limit=W0,
            couple_protocol_each_step=True,
        )

        before_tail_word = observer.tail_word
        before_trace_length = observer.trace_tape_length
        before_resource_limit = observer.resource_limit

        executed = observer.step()
        self.assertTrue(executed)
        # Coupling should have applied one protocol unfold step (trace/resource change).
        # Note: tail_word may or may not change depending on the deterministic branch choice.
        self.assertEqual(observer.trace_tape_length, before_trace_length + 1)
        # Endogenous W gain happens only when taking a nontrivial branch; branch_choice_bit=0 is trivial here.
        self.assertEqual(observer.resource_limit, before_resource_limit)

        undone = observer.undo_step()
        self.assertTrue(undone)
        self.assertEqual(observer.tail_word, before_tail_word)
        self.assertEqual(observer.trace_tape_length, before_trace_length)
        self.assertEqual(observer.resource_limit, before_resource_limit)

    def test_commit_deterministically_truncates_by_beam_width(self) -> None:
        ontic_system = OnticZeckendorfSystem(window_length=6)
        protocol = ZeckendorfProtocol(ontic_system)

        transition_table = {
            ("START", "_"): Transition(next_state="START", write_symbol="_", head_move=0),
        }

        W0 = self._min_W0_for_one_step(
            protocol,
            transition_table=transition_table,
            start_state="START",
            halt_states={"HALT"},
            macro_word=0,
            tail_word_start=0,
            tape_input_bits=None,
            couple_protocol_each_step=True,
        )

        observers = []
        for resource_limit in (W0, 2 * W0, 4 * W0):
            o = Observer(
                protocol,
                transition_table=transition_table,
                start_state="START",
                halt_states={"HALT"},
                macro_word=0,
                tail_word_start=0,
                resource_limit=resource_limit,
                couple_protocol_each_step=True,
            )
            # Execute one step to advance protocol if possible.
            o.step()
            observers.append(o)

        observer = Observer.merge(observers)
        observer.commit()
        kept_tail_words = observer.tail_words()

        self.assertTrue(len(kept_tail_words) >= 1)
        observer2 = Observer.merge(observers)
        observer2.commit()
        self.assertEqual(observer2.tail_words(), kept_tail_words)


if __name__ == "__main__":
    unittest.main()

