#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

from zeckendorf_ontic.ontic_system import OnticZeckendorfSystem
from zeckendorf_ontic.observer import ObserverBranchSet, ObserverMachine, Transition
from zeckendorf_ontic.protocol import ZeckendorfProtocol


class TestObserverMachine(unittest.TestCase):
    def test_step_and_undo_restore_tape_and_state(self) -> None:
        ontic_system = OnticZeckendorfSystem(window_length=6)
        protocol = ZeckendorfProtocol(ontic_system)

        # One-step machine: overwrite current symbol and halt.
        transition_table = {
            ("START", "0"): Transition(next_state="HALT", write_symbol="1", head_move=0),
            ("START", "_"): Transition(next_state="HALT", write_symbol="1", head_move=0),
        }

        machine = ObserverMachine(
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

        before_view = machine.view_tape(-1, 1)
        before_state = machine.control_state
        before_head = machine.head_position
        before_tail_word = machine.tail_word
        before_trace_length = machine.trace_tape_length
        before_resource_limit = machine.resource_limit

        executed = machine.step()
        self.assertTrue(executed)
        self.assertTrue(machine.is_halted())
        self.assertNotEqual(machine.view_tape(-1, 1), before_view)

        undone = machine.undo_step()
        self.assertTrue(undone)
        self.assertEqual(machine.view_tape(-1, 1), before_view)
        self.assertEqual(machine.control_state, before_state)
        self.assertEqual(machine.head_position, before_head)
        self.assertEqual(machine.tail_word, before_tail_word)
        self.assertEqual(machine.trace_tape_length, before_trace_length)
        self.assertEqual(machine.resource_limit, before_resource_limit)

    def test_coupled_protocol_step_is_reversible(self) -> None:
        ontic_system = OnticZeckendorfSystem(window_length=6)
        protocol = ZeckendorfProtocol(ontic_system)

        transition_table = {
            ("START", "_"): Transition(next_state="START", write_symbol="_", head_move=0),
        }

        machine = ObserverMachine(
            protocol,
            transition_table=transition_table,
            start_state="START",
            halt_states={"HALT"},
            macro_word=0,
            tail_word_start=0,
            resource_limit=1,
            couple_protocol_each_step=True,
        )

        before_tail_word = machine.tail_word
        before_trace_length = machine.trace_tape_length
        before_resource_limit = machine.resource_limit

        executed = machine.step()
        self.assertTrue(executed)
        # Coupling should have applied one protocol unfold step (trace/resource change).
        # Note: tail_word may or may not change depending on the deterministic branch choice.
        self.assertEqual(machine.trace_tape_length, before_trace_length + 1)
        self.assertNotEqual(machine.resource_limit, before_resource_limit)

        undone = machine.undo_step()
        self.assertTrue(undone)
        self.assertEqual(machine.tail_word, before_tail_word)
        self.assertEqual(machine.trace_tape_length, before_trace_length)
        self.assertEqual(machine.resource_limit, before_resource_limit)

    def test_commit_deterministically_truncates_by_beam_width(self) -> None:
        ontic_system = OnticZeckendorfSystem(window_length=6)
        protocol = ZeckendorfProtocol(ontic_system)

        transition_table = {
            ("START", "_"): Transition(next_state="START", write_symbol="_", head_move=0),
        }

        # Make three machines with different tails by coupling protocol step once with different energy seeds.
        machines = []
        for resource_limit in (1, 2, 4):
            m = ObserverMachine(
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
            m.step()
            machines.append(m)

        branch_set = ObserverBranchSet(machines)
        committed = branch_set.commit()
        kept = committed.branches()

        # Beam width is 2^{|energy_tape|}, so cap>=1; and commit must be deterministic.
        self.assertTrue(len(kept) >= 1)
        committed2 = branch_set.commit()
        self.assertEqual([b.tail_word for b in committed2.branches()], [b.tail_word for b in kept])


if __name__ == "__main__":
    unittest.main()

