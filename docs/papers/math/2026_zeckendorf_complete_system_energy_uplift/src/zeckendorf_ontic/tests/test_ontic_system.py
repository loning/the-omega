#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest
from collections import Counter

from zeckendorf_ontic.ontic_system import OnticZeckendorfSystem


def _all_no_adjacent_words(L: int) -> list[int]:
    out: list[int] = []
    for x in range(1 << int(L)):
        if (x & (x << 1)) == 0:
            out.append(int(x))
    return out


class TestOnticZeckendorfSystem(unittest.TestCase):
    def test_tail_len_m6_is_3(self) -> None:
        ontic_system = OnticZeckendorfSystem(window_length=6)
        self.assertEqual(ontic_system.tail_length(), 3)

    def test_enc_rec_bijection_small_ms(self) -> None:
        for window_length in range(1, 11):
            ontic_system = OnticZeckendorfSystem(window_length=window_length)
            micro_domain_size = 1 << window_length
            seen_pairs: dict[tuple[int, int], int] = {}
            for micro_integer in range(micro_domain_size):
                pair = ontic_system.enc(micro_integer)
                self.assertTrue(ontic_system.ok(pair.macro_word, pair.tail_word))
                key = (pair.macro_word, pair.tail_word)
                if key in seen_pairs:
                    self.assertEqual(seen_pairs[key], micro_integer, msg=f"enc collision window_length={window_length} pair={key}")
                seen_pairs[key] = micro_integer
            for (macro_word, tail_word), N in seen_pairs.items():
                reconstructed = ontic_system.rec(macro_word, tail_word)
                self.assertIsNotNone(reconstructed)
                self.assertEqual(int(reconstructed), int(N))

    def test_m6_fiber_histogram_matches_paper(self) -> None:
        ontic_system = OnticZeckendorfSystem(window_length=6)
        ys = _all_no_adjacent_words(6)
        self.assertEqual(len(ys), 21)
        hist = Counter(ontic_system.fiber_size(macro_word) for macro_word in ys)
        self.assertEqual(dict(hist), {2: 8, 3: 4, 4: 9})

    def test_tail_inverse_candidates_soundness_m6(self) -> None:
        ontic_system = OnticZeckendorfSystem(window_length=6)
        tail_length = ontic_system.tail_length()
        self.assertEqual(tail_length, 3)
        for tail_word in range(1 << tail_length):
            candidates = ontic_system.tail_inverse_candidates(tail_word)
            if tail_word >= (1 << (tail_length - 1)):
                # By definition Tail(previous_tail_word)=previous_tail_word>>1, the top bit of tail_word must be 0
                # for a length-tail_length preimage to exist.
                self.assertEqual(candidates, [])
                continue
            for previous_tail_word in candidates:
                self.assertEqual(ontic_system.tail_shift(previous_tail_word), tail_word)
                # tail legality (no adjacent ones)
                self.assertEqual((previous_tail_word & (previous_tail_word << 1)), 0)

    def test_candidates_definition_and_ordering(self) -> None:
        ontic_system = OnticZeckendorfSystem(window_length=6)
        macro_word = 0  # macro_word = 0^window_length is used heavily in the paper
        tail_word = 0
        candidates = ontic_system.candidates(macro_word, tail_word)
        # must be subset of tail inverse cands
        inverse_candidates = set(ontic_system.tail_inverse_candidates(tail_word))
        self.assertTrue(set(candidates).issubset(inverse_candidates))
        # must all be feasible and ordered by increasing reconstructed N
        reconstructed_micro_integers: list[int] = []
        for candidate_tail_word in candidates:
            self.assertTrue(ontic_system.ok(macro_word, candidate_tail_word))
            reconstructed = ontic_system.rec(macro_word, candidate_tail_word)
            self.assertIsNotNone(reconstructed)
            reconstructed_micro_integers.append(int(reconstructed))
        self.assertEqual(reconstructed_micro_integers, sorted(reconstructed_micro_integers))

    def test_ok_rejects_out_of_range(self) -> None:
        ontic_system = OnticZeckendorfSystem(window_length=6)
        self.assertFalse(ontic_system.ok(-1, 0))
        self.assertFalse(ontic_system.ok(1 << 6, 0))
        # tail out of range should be rejected (not raise)
        self.assertFalse(ontic_system.ok(0, 1 << ontic_system.tail_length()))


if __name__ == "__main__":
    unittest.main()

