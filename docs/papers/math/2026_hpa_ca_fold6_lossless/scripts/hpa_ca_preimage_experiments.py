#!/usr/bin/env python3
"""Compute symbolic preimage counts on HPA-CA generated samples.

This script is meant to support the "observer-time = inverse search cost" line:
before implementing any backtracking search, we can compute exact *counts* of
symbolic preimages (k-step) on the ring for small k.
"""

from __future__ import annotations

import argparse
import csv
import os
from typing import List

import numpy as np

from hpa_ca_lossless import evolve
from hpa_ca_preimage_count import (
    build_succ_table,
    count_preimages_k_ring,
    f_pair,
    stable_words_x6,
    words_from_state_bits,
)


def parse_int_list(s: str) -> List[int]:
    if not s.strip():
        return []
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, default=300)
    ap.add_argument("--T", type=int, default=200)
    ap.add_argument("--p", type=float, default=0.5)
    ap.add_argument("--seeds", type=str, default="1,2,3,4,5", help="comma-separated seeds")
    ap.add_argument("--k", type=int, default=1, help="k-step symbolic preimage count")
    ap.add_argument("--t", type=int, default=-1, help="time index to analyze (default: last)")
    ap.add_argument("--out_csv", type=str, default="out_preimage_counts.csv")
    args = ap.parse_args()

    if args.L % 6 != 0:
        raise SystemExit("L must be a multiple of 6")
    if args.k < 1:
        raise SystemExit("k must be >= 1")

    seeds = parse_int_list(args.seeds)
    if not seeds:
        raise SystemExit("No seeds provided")

    words = stable_words_x6()
    idx = {w: i for i, w in enumerate(words)}
    out_f, _upl = f_pair(words)
    succ = build_succ_table(out_f)

    t_analyze = args.t if args.t >= 0 else args.T
    if t_analyze < 1:
        raise SystemExit("t must be >= 1 (need a produced block-admissible slice)")

    # In our convention: step 0 uses offset=0, step 1 uses offset=3, ...
    stable_offset = 0 if ((t_analyze - 1) % 2 == 0) else 3

    os.makedirs(os.path.dirname(args.out_csv) or ".", exist_ok=True)
    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["seed", "L", "T", "p", "t", "stable_offset", "k", "preimage_count"])

        for seed in seeds:
            res = evolve(L=args.L, T=args.T, seed=seed, p=args.p)
            state = res.states[t_analyze]
            out_words = words_from_state_bits(state, offset=stable_offset)
            if not all(ww in idx for ww in out_words):
                # This should not happen for the produced stable offset, but keep it explicit.
                count = 0
            else:
                out_seq = [idx[ww] for ww in out_words]
                count = count_preimages_k_ring(out_seq, succ, k=args.k)
            w.writerow([seed, args.L, args.T, args.p, t_analyze, stable_offset, args.k, count])

    print(f"Wrote CSV: {args.out_csv}")


if __name__ == "__main__":
    main()

