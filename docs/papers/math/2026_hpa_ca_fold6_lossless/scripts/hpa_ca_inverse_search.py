#!/usr/bin/env python3
"""Inverse reconstruction as constrained search (observer-time prototype).

We treat one-step inverse reconstruction on the symbol lattice:
  y_i = f(x_i, x_{i+1})   on a ring of length n
Given y (visible), find some x (a preimage) by DFS + local constraint propagation.

We report:
  - nodes_visited: number of partial assignments expanded
  - backtracks
  - found / not found

This is a concrete operationalization of:
  observer_time ~ inverse_consistency_search_cost
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from hpa_ca_lossless import evolve
from hpa_ca_preimage_count import (
    build_succ_table,
    count_preimages_k1_ring,
    f_pair,
    stable_words_x6,
    words_from_state_bits,
)


@dataclass
class SearchStats:
    found: bool
    nodes_visited: int
    backtracks: int
    x0_trials: int


def dfs_find_one_preimage(
    out_seq: Sequence[int],
    succ: List[List[List[int]]],
    rng: Optional[np.random.Generator] = None,
    max_nodes: Optional[int] = None,
) -> Tuple[Optional[List[int]], SearchStats]:
    n = len(out_seq)
    A = len(succ)

    nodes = 0
    backtracks = 0
    x = [-1] * n

    def order(lst: List[int]) -> List[int]:
        if rng is None or len(lst) <= 1:
            return lst
        arr = lst.copy()
        rng.shuffle(arr)
        return arr

    def rec(i: int, x0: int) -> bool:
        nonlocal nodes, backtracks
        if max_nodes is not None and nodes >= max_nodes:
            return False

        if i == n - 1:
            # closure constraint at last edge: y_{n-1} = f(x_{n-1}, x0)
            y_last = int(out_seq[-1])
            nodes += 1
            return x0 in succ[y_last][x[i]]

        y = int(out_seq[i])
        options = succ[y][x[i]]
        nodes += 1
        for x_next in order(options):
            x[i + 1] = int(x_next)
            if rec(i + 1, x0):
                return True
        backtracks += 1
        x[i + 1] = -1
        return False

    x0_trials = 0
    for x0 in range(A):
        x0_trials += 1
        x[0] = int(x0)
        if rec(0, x0):
            return x, SearchStats(found=True, nodes_visited=nodes, backtracks=backtracks, x0_trials=x0_trials)
        x[0] = -1

    return None, SearchStats(found=False, nodes_visited=nodes, backtracks=backtracks, x0_trials=x0_trials)


def parse_int_list(s: str) -> List[int]:
    if not s.strip():
        return []
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=str, default="", help="optional .npz produced by hpa_ca_lossless.py")
    ap.add_argument("--t", type=int, default=-1, help="time index to analyze (default: last)")
    ap.add_argument("--offset", type=int, default=-1, help="0 or 3; default: infer by t parity (HPA-CA)")
    ap.add_argument("--max_nodes", type=int, default=0, help="0 means unlimited")
    ap.add_argument("--shuffle", action="store_true", help="randomize branching order")
    ap.add_argument("--seed", type=int, default=1, help="RNG seed for shuffling")

    # optional sweep mode (generate states on the fly)
    ap.add_argument("--sweep", action="store_true", help="run multiple seeds and write a CSV")
    ap.add_argument("--L", type=int, default=300)
    ap.add_argument("--T", type=int, default=200)
    ap.add_argument("--p", type=float, default=0.5)
    ap.add_argument("--seeds", type=str, default="1,2,3,4,5", help="comma-separated seeds for sweep")
    ap.add_argument("--out_csv", type=str, default="out_inverse_search_cost.csv")

    args = ap.parse_args()

    words = stable_words_x6()
    idx = {w: i for i, w in enumerate(words)}
    out_f, _upl = f_pair(words)
    succ = build_succ_table(out_f)

    max_nodes = None if args.max_nodes <= 0 else int(args.max_nodes)
    rng = np.random.default_rng(args.seed) if args.shuffle else None

    def analyze_state(state: np.ndarray, t: int) -> Tuple[int, SearchStats, int]:
        # choose the stable offset used at step t-1, unless user forces it
        if args.offset in (0, 3):
            offset = int(args.offset)
        else:
            if t <= 0:
                raise ValueError("t must be >= 1")
            offset = 0 if ((t - 1) % 2 == 0) else 3

        out_words = words_from_state_bits(state, offset=offset)
        if not all(w in idx for w in out_words):
            # no valid symbolic slice
            return 0, SearchStats(found=False, nodes_visited=0, backtracks=0, x0_trials=0), offset

        out_seq = [idx[w] for w in out_words]
        exact = count_preimages_k1_ring(out_seq, succ)
        _x_pre, stats = dfs_find_one_preimage(out_seq, succ, rng=rng, max_nodes=max_nodes)
        return exact, stats, offset

    if args.sweep:
        if args.L % 6 != 0:
            raise SystemExit("L must be a multiple of 6")
        seeds = parse_int_list(args.seeds)
        if not seeds:
            raise SystemExit("No seeds provided")

        t = args.t if args.t >= 0 else args.T
        if t < 1:
            raise SystemExit("t must be >= 1")

        os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
        with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "seed",
                    "L",
                    "T",
                    "p",
                    "t",
                    "offset",
                    "exact_preimage_count_k1",
                    "found",
                    "nodes_visited",
                    "backtracks",
                    "x0_trials",
                ]
            )
            for sd in seeds:
                res = evolve(L=args.L, T=args.T, seed=sd, p=args.p)
                exact, stats, offset = analyze_state(res.states[t], t=t)
                w.writerow(
                    [
                        sd,
                        args.L,
                        args.T,
                        args.p,
                        t,
                        offset,
                        exact,
                        int(stats.found),
                        stats.nodes_visited,
                        stats.backtracks,
                        stats.x0_trials,
                    ]
                )
        print(f"Wrote CSV: {args.out_csv}")
        return

    if not args.data:
        raise SystemExit("Please provide --data path/to/data.npz or use --sweep.")

    data = np.load(args.data)
    states = data["states"]
    t = int(args.t) if args.t >= 0 else (states.shape[0] - 1)
    state = states[t].astype(np.uint8)

    exact, stats, offset = analyze_state(state, t=t)
    print(f"t={t}, offset={offset}, exact_preimage_count_k1={exact}")
    print(f"found={stats.found}, nodes_visited={stats.nodes_visited}, backtracks={stats.backtracks}, x0_trials={stats.x0_trials}")


if __name__ == "__main__":
    main()

