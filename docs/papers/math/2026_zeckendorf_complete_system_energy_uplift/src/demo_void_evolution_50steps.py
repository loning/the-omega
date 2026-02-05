#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print a 50-step "watch the program run" log from the void.

This demo is intentionally minimal and paper-aligned:
  - Fix m=6 and choose y_con = 0^6 (macro_word = 0).
  - Start from the smallest W0 that can encode the initial space state.
  - Repeatedly:
      (1) expand bubble by one protocol unfold step (try b=0,1 for each branch),
      (2) commit under the single cap W (scheme B: storage + branch keeping),
      (3) read y_obs via the default observer readout.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from zeckendorf_ontic.ontic_system import OnticZeckendorfSystem
from zeckendorf_ontic.observer import Observer, Transition
from zeckendorf_ontic.protocol import ZeckendorfProtocol


def _bits_msb(x: int, width: int) -> str:
    return format(int(x), "0{}b".format(int(width)))


@dataclass(frozen=True)
class BranchRow:
    micro_integer: int
    tail_word: int
    trace_len: int
    space_cost: int


def _min_W0_for_init(observer_factory, max_W: int = 4096) -> int:
    for W in range(1, int(max_W) + 1):
        try:
            observer_factory(int(W))
            return int(W)
        except ValueError:
            continue
    raise RuntimeError("failed to find a feasible initial W0 within search bound")


def _min_W0_for_n_steps(build, *, steps: int, max_W: int = 20000) -> int:
    """Find minimal W0 such that the demo can run `steps` iterations."""

    for W in range(1, int(max_W) + 1):
        try:
            o = build(int(W))
        except ValueError:
            continue
        ok = True
        for _ in range(int(steps)):
            o.protocol_expand_one_step_and_commit()
            if not o.branch_count():
                ok = False
                break
            if o.space_cost_y6() > o.resource_limit:
                ok = False
                break
        if ok:
            return int(W)
    raise RuntimeError("failed to find a feasible W0 for the requested step count")


def main() -> None:
    window_length = 6
    macro_word = 0  # y_con = 0^6

    ontic = OnticZeckendorfSystem(window_length=window_length)
    proto = ZeckendorfProtocol(ontic)

    transition_table: Dict[Tuple[str, str], Transition] = {
        ("START", "_"): Transition(next_state="START", write_symbol="_", head_move=0),
        ("START", "0"): Transition(next_state="START", write_symbol="0", head_move=0),
        ("START", "1"): Transition(next_state="START", write_symbol="1", head_move=0),
    }

    def build(W0: int) -> Observer:
        return Observer(
            proto,
            transition_table=transition_table,
            start_state="START",
            halt_states={"HALT"},
            macro_word=macro_word,
            tail_word_start=0,
            resource_limit=int(W0),
            tape_input_bits=None,
            couple_protocol_each_step=False,
        )

    # For a readable 50-step log, pick the smallest W0 that can actually run 50 rounds
    # under the "W grows only when new micro candidates are discovered" rule.
    W0 = _min_W0_for_n_steps(build, steps=50)
    observer = build(W0)

    tail_len = ontic.tail_length()
    y_con_bits = _bits_msb(macro_word, window_length)

    print("=== Void evolution demo (m=6) ===")
    print(f"y_con = {y_con_bits} (macro_word={macro_word})")
    print(f"tail_length = {tail_len}")
    print(f"minimal W0 to run 50 rounds (under endogenous W-gain) = {W0}")
    print("")
    print(
        "step | W | space_cost | branches | y_obs | primary_t | |tr| | top_branches(micro,t,|tr|,cost)"
    )
    print("-" * 110)

    for step in range(0, 50):
        # Expand + commit (protocol-driven bubble growth under single cap W).
        observer.protocol_expand_one_step_and_commit()

        W = int(observer.resource_limit) if observer.branch_count() else 0
        total_cost = int(observer.space_cost_y6()) if observer.branch_count() else 0
        y_obs = int(observer.observed_macro_word(observation_setting=step)) if observer.branch_count() else -1

        # Collect via the same ordering used by commit (score_key).
        branches: List[BranchRow] = []
        proto_local = proto
        ordered = sorted(
            [b for b in observer._branches if proto_local.is_ok_clo(b.protocol_state())],
            key=lambda b: proto_local.score_key(b.protocol_state()),
        )
        for b in ordered[:3]:
            micro_integer = int(proto_local.score_key(b.protocol_state())[0])
            branches.append(
                BranchRow(
                    micro_integer=micro_integer,
                    tail_word=int(b.tail_word),
                    trace_len=int(b.trace_tape_length),
                    space_cost=int(b.space_cost_y6()),
                )
            )

        primary_t = int(observer.tail_word) if observer.branch_count() else 0
        primary_tr = int(observer.trace_tape_length) if observer.branch_count() else 0
        top = ", ".join(
            f"({r.micro_integer},{_bits_msb(r.tail_word, tail_len)},{r.trace_len},{r.space_cost})" for r in branches
        )
        print(
            f"{step:>4} | {W:>4} | {total_cost:>10} | {observer.branch_count():>8} | "
            f"{_bits_msb(y_obs, window_length) if y_obs >= 0 else '------'} | "
            f"{_bits_msb(primary_t, tail_len)} | {primary_tr:>3} | {top}"
        )


if __name__ == "__main__":
    main()

