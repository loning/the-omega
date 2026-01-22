#!/usr/bin/env python3
"""Reversible extension utilities for HPA-CA (m=6).

This file provides a clean, *mathematically explicit* interface for the statement:

    s_t  <->  (s_{t+1}, u_t)

where u_t is the uplift edge-label sequence produced at time t.

Important:
----------
The step map on the *visible slice alone* is many-to-one.
The reversible extension is obtained by carrying u_t as additional data.
To rewind multiple steps, you must keep the whole uplift log (u_0,...,u_{T-1}).

This script focuses on:
  - one-step forward: (state_in, offset) -> (state_out, uplift_codes_step)
  - one-step inverse: (state_out, uplift_codes_step, offset) -> state_in
  - multi-step run + exact rewind check (log-based, no heuristics)
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from hpa_ca_lossless import (
    CODE_TO_UPLIFT,
    UPLIFT_TO_CODE,
    fold6_kernel,
    invert_step,
)


@dataclass
class StepResult:
    state_out: np.ndarray  # (L,)
    uplift_codes_step: np.ndarray  # (nb,)


def forward_step_with_uplift(state_in: np.ndarray, offset: int) -> StepResult:
    """One forward step plus uplift codes (edge labels) for that step."""
    if offset not in (0, 3):
        raise ValueError("offset must be 0 or 3")

    L = int(state_in.shape[0])
    if L % 6 != 0:
        raise ValueError("L must be a multiple of 6")

    nb = L // 6
    state_out = state_in.copy()
    uplift_codes_step = np.zeros(nb, dtype=np.uint8)

    for b in range(nb):
        start = (offset + 6 * b) % L
        idx = [(start + i) % L for i in range(6)]
        block = state_in[idx]
        w, uplift = fold6_kernel(block)
        state_out[idx] = w
        uplift_codes_step[b] = UPLIFT_TO_CODE[uplift]

    return StepResult(state_out=state_out, uplift_codes_step=uplift_codes_step)


def inverse_step_with_uplift(state_out: np.ndarray, uplift_codes_step: np.ndarray, offset: int) -> np.ndarray:
    """One inverse step (exact), given the uplift codes for that step."""
    return invert_step(state_out, uplift_codes_step, offset)


def run_with_log(state0: np.ndarray, T: int) -> Tuple[np.ndarray, np.ndarray]:
    """Run T steps and record all uplift codes.

    Returns:
      states: (T+1, L)
      uplift_codes: (T, nb)
    """
    L = int(state0.shape[0])
    if L % 6 != 0:
        raise ValueError("L must be a multiple of 6")
    nb = L // 6

    states = np.zeros((T + 1, L), dtype=np.uint8)
    uplift_codes = np.zeros((T, nb), dtype=np.uint8)

    state = state0.copy()
    states[0] = state

    for t in range(T):
        offset = 0 if (t % 2 == 0) else 3
        res = forward_step_with_uplift(state, offset=offset)
        state = res.state_out
        states[t + 1] = state
        uplift_codes[t] = res.uplift_codes_step

    return states, uplift_codes


def rewind_with_log(stateT: np.ndarray, uplift_codes: np.ndarray) -> np.ndarray:
    """Rewind exactly using the recorded uplift log."""
    T = int(uplift_codes.shape[0])
    state = stateT.copy()
    for t in range(T - 1, -1, -1):
        offset = 0 if (t % 2 == 0) else 3
        state = inverse_step_with_uplift(state, uplift_codes[t], offset=offset)
    return state


def uplift_code_histogram(uplift_codes: np.ndarray) -> dict:
    """Return histogram of uplift values {0,21,34,55} from codes."""
    vals = [CODE_TO_UPLIFT[int(c)] for c in uplift_codes.reshape(-1).tolist()]
    hist = {0: 0, 21: 0, 34: 0, 55: 0}
    for v in vals:
        hist[int(v)] += 1
    return hist


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, default=300, help="lattice length (multiple of 6)")
    ap.add_argument("--T", type=int, default=50, help="time steps")
    ap.add_argument("--seed", type=int, default=1, help="RNG seed for the initial state")
    ap.add_argument("--p", type=float, default=0.5, help="initial Bernoulli(p) density")
    ap.add_argument("--check_one_step", action="store_true", help="check exact one-step invertibility")
    ap.add_argument("--check_rewind", action="store_true", help="check exact multi-step rewind (log-based)")
    args = ap.parse_args()

    if args.L % 6 != 0:
        raise SystemExit("L must be a multiple of 6")

    rng = np.random.default_rng(args.seed)
    state0 = (rng.random(args.L) < args.p).astype(np.uint8)

    if args.check_one_step:
        res0 = forward_step_with_uplift(state0, offset=0)
        back0 = inverse_step_with_uplift(res0.state_out, res0.uplift_codes_step, offset=0)
        ok0 = np.array_equal(back0, state0)

        res3 = forward_step_with_uplift(state0, offset=3)
        back3 = inverse_step_with_uplift(res3.state_out, res3.uplift_codes_step, offset=3)
        ok3 = np.array_equal(back3, state0)

        print(f"One-step invertibility (offset=0): {ok0}")
        print(f"One-step invertibility (offset=3): {ok3}")

    if args.check_rewind:
        states, uplift_codes = run_with_log(state0, T=args.T)
        state_back = rewind_with_log(states[-1], uplift_codes)
        ok = np.array_equal(state_back, state0)
        hist = uplift_code_histogram(uplift_codes)
        print(f"Rewind check (T={args.T}): {ok}")
        print(f"Uplift histogram (counts): {hist}")


if __name__ == "__main__":
    main()

