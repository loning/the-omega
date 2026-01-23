#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

from zeckendorf_ontic.ontic_system import OnticZeckendorfSystem


class TestProtocolLedgerConservation(unittest.TestCase):
    def test_unfold_then_fold_is_identity_m6_y0(self) -> None:
        from zeckendorf_ontic.protocol import ZeckendorfProtocol

        ontic_system = OnticZeckendorfSystem(window_length=6)
        protocol = ZeckendorfProtocol(ontic_system)
        macro_word = 0  # fixed observation macro_word = 0^window_length

        # Start from void tail_word=0 with a one-bit seed energy_tape.
        s0 = protocol.create_state(macro_word, tail_word=0, resource_limit=1)
        s1 = protocol.unfold_step(s0, branch_choice_bit=0)
        self.assertIsNotNone(s1)
        s2 = protocol.fold_step(s1)
        self.assertIsNotNone(s2)
        self.assertEqual(s2, s0)

    def test_fold_then_unfold_is_identity_for_reachable_state(self) -> None:
        from zeckendorf_ontic.protocol import ZeckendorfProtocol

        ontic_system = OnticZeckendorfSystem(window_length=6)
        protocol = ZeckendorfProtocol(ontic_system)
        macro_word = 0

        # Build a reachable state by 2 unfolds with explicit branch_choice bits.
        s = protocol.create_state(macro_word, tail_word=0, resource_limit=1)
        s = protocol.unfold_step(s, branch_choice_bit=0)
        self.assertIsNotNone(s)
        s = protocol.unfold_step(s, branch_choice_bit=0)
        self.assertIsNotNone(s)

        back = protocol.fold_step(s)
        self.assertIsNotNone(back)
        fwd = protocol.unfold_step(back, branch_choice_bit=0)
        self.assertIsNotNone(fwd)
        self.assertEqual(fwd, s)

    def test_ledger_deltas(self) -> None:
        from zeckendorf_ontic.protocol import ZeckendorfProtocol

        ontic_system = OnticZeckendorfSystem(window_length=6)
        protocol = ZeckendorfProtocol(ontic_system)
        macro_word = 0

        s0 = protocol.create_state(macro_word, tail_word=0, resource_limit=1)
        resource_limit0 = s0.resource_limit
        trace_length0 = s0.trace_tape_length

        s1 = protocol.unfold_step(s0, branch_choice_bit=0)
        self.assertIsNotNone(s1)
        # trace grows by 1
        self.assertEqual(s1.trace_tape_length, trace_length0 + 1)
        # resource_limit multiplies by 2^(code_bit_length-1)
        code_bit_length = protocol.code_bit_length(macro_word)
        factor = 1 << (int(code_bit_length) - 1)
        self.assertEqual(s1.resource_limit, resource_limit0 * factor)

        s2 = protocol.fold_step(s1)
        self.assertIsNotNone(s2)
        self.assertEqual(s2, s0)

    def test_reach_all_feasible_tails_m6_y0(self) -> None:
        from zeckendorf_ontic.protocol import ZeckendorfProtocol

        ontic_system = OnticZeckendorfSystem(window_length=6)
        protocol = ZeckendorfProtocol(ontic_system)
        macro_word = 0
        tail_length = ontic_system.tail_length()
        reachable = protocol.reachable_tails(macro_word=macro_word, depth_max=tail_length)
        feasible = protocol.feasible_tails(macro_word=macro_word)
        self.assertEqual(reachable, feasible)


if __name__ == "__main__":
    unittest.main()

