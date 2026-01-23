#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

from zeckendorf_ontic.ontic_system import OnticZeckendorfSystem
from zeckendorf_ontic.observer import Observer, Transition
from zeckendorf_ontic.protocol import ZeckendorfProtocol


class TestObserver(unittest.TestCase):
    def test_bubble_frontier_grows_under_resource_cap_m6_y0(self) -> None:
        """A single observer maintains a growing parallel branch set under W."""

        ontic_system = OnticZeckendorfSystem(window_length=6)
        protocol = ZeckendorfProtocol(ontic_system)

        # No-op TM semantics; we only use protocol-driven branch expansion here.
        transition_table = {
            ("START", "_"): Transition(next_state="START", write_symbol="_", head_move=0),
        }

        observer = Observer(
            protocol,
            transition_table=transition_table,
            start_state="START",
            halt_states={"HALT"},
            macro_word=0,  # y=0^6 has maximal fiber size
            tail_word_start=0,
            resource_limit=1,  # W0 = 1
            couple_protocol_each_step=False,
        )

        counts = [observer.branch_count()]
        caps = [observer.resource_limit]

        # Repeatedly expand+commit. For y=0^6 in m=6 we expect W to grow (k(y)=2 => factor 2).
        for _ in range(4):
            observer.protocol_expand_one_step_and_commit()
            counts.append(observer.branch_count())
            caps.append(observer.resource_limit)
            # The bubble (branch set) must respect the cap.
            self.assertLessEqual(observer.branch_count(), observer.resource_limit)

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

        observer = Observer(
            protocol,
            transition_table=transition_table,
            start_state="START",
            halt_states={"HALT"},
            macro_word=0,
            tail_word_start=0,
            resource_limit=1,
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

        observer = Observer(
            protocol,
            transition_table=transition_table,
            start_state="START",
            halt_states={"HALT"},
            macro_word=0,
            tail_word_start=0,
            resource_limit=1,
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
        self.assertNotEqual(observer.resource_limit, before_resource_limit)

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

        observers = []
        for resource_limit in (1, 2, 4):
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

