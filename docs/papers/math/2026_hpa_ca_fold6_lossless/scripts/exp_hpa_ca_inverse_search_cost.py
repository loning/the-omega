#!/usr/bin/env python3
"""Measure inverse search cost on sampled visible slices (cached).

We implement a lightweight DFS that reconstructs *one* 1-step preimage on the
symbol lattice y_i = f(x_i, x_{i+1}) with ring closure. The node expansion count
is the operational "observer-time" proxy.

Artifacts:
  artifacts/hpa_ca_inverse_search_cost/<run_id>/costs.csv
  artifacts/hpa_ca_inverse_search_cost/<run_id>/manifest.json

Generated LaTeX:
  sections/generated/hpa_ca_inverse_search_cost_rows.tex
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir
from common_tex_pylatex import write_tabular_fragment
from hpa_ca_lossless import evolve
from hpa_ca_preimage_count import build_succ_table, count_preimages_k1_ring, f_pair, stable_words_x6, words_from_state_bits


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
) -> SearchStats:
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
            return SearchStats(found=True, nodes_visited=nodes, backtracks=backtracks, x0_trials=x0_trials)
        x[0] = -1

    return SearchStats(found=False, nodes_visited=nodes, backtracks=backtracks, x0_trials=x0_trials)


def parse_int_list(s: str) -> List[int]:
    if not s.strip():
        return []
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, default=300)
    ap.add_argument("--T", type=int, default=200)
    ap.add_argument("--p", type=float, default=0.5)
    ap.add_argument("--t", type=int, default=200)
    ap.add_argument("--seeds", type=str, default="1,2,3,4,5")
    ap.add_argument("--max_nodes", type=int, default=0, help="0 means unlimited")
    ap.add_argument("--shuffle", action="store_true")
    ap.add_argument("--shuffle_seed", type=int, default=1)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.L % 6 != 0:
        raise SystemExit("L must be a multiple of 6")
    if args.t < 1:
        raise SystemExit("t must be >= 1")

    seeds = parse_int_list(args.seeds)
    if not seeds:
        raise SystemExit("No seeds provided")

    max_nodes = None if args.max_nodes <= 0 else int(args.max_nodes)
    rng = np.random.default_rng(args.shuffle_seed) if args.shuffle else None

    script_path = Path(__file__).resolve()
    params = {
        "L": int(args.L),
        "T": int(args.T),
        "p": float(args.p),
        "t": int(args.t),
        "seeds": seeds,
        "max_nodes": int(args.max_nodes),
        "shuffle": bool(args.shuffle),
        "shuffle_seed": int(args.shuffle_seed),
    }

    required = ["costs.csv"]
    run = prepare_run(
        "hpa_ca_inverse_search_cost",
        params=params,
        script_path=script_path,
        required_files=required,
        force=bool(args.force),
    )

    words = stable_words_x6()
    idx = {w: i for i, w in enumerate(words)}
    out_f, _upl = f_pair(words)
    succ = build_succ_table(out_f)
    stable_offset = 0 if ((args.t - 1) % 2 == 0) else 3

    if not run.cached:
        out_csv = run.run_dir / "costs.csv"
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "seed",
                    "L",
                    "T",
                    "p",
                    "t",
                    "stable_offset",
                    "exact_preimage_count_k1",
                    "found",
                    "nodes_visited",
                    "backtracks",
                    "x0_trials",
                ]
            )
            for sd in seeds:
                print(f"[inv_search] seed={sd} start", flush=True)
                res = evolve(L=args.L, T=args.T, seed=sd, p=args.p)
                state = res.states[args.t]
                out_words = words_from_state_bits(state, offset=stable_offset)
                if not all(ww in idx for ww in out_words):
                    exact = 0
                    stats = SearchStats(found=False, nodes_visited=0, backtracks=0, x0_trials=0)
                else:
                    out_seq = [idx[ww] for ww in out_words]
                    exact = count_preimages_k1_ring(out_seq, succ)
                    stats = dfs_find_one_preimage(out_seq, succ, rng=rng, max_nodes=max_nodes)
                w.writerow(
                    [
                        sd,
                        args.L,
                        args.T,
                        args.p,
                        args.t,
                        stable_offset,
                        exact,
                        int(stats.found),
                        stats.nodes_visited,
                        stats.backtracks,
                        stats.x0_trials,
                    ]
                )
                print(
                    f"[inv_search] seed={sd} done found={int(stats.found)} nodes={stats.nodes_visited} backtracks={stats.backtracks} x0_trials={stats.x0_trials}",
                    flush=True,
                )

        manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
        manifest = add_output_hashes(manifest, run.run_dir, rel_paths=required)
        write_manifest(run.run_dir, manifest)

    # Emit LaTeX fragment from CSV
    rows: List[List[str]] = []
    with open(run.run_dir / "costs.csv", "r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        _header = next(r)
        for line in r:
            rows.append(line)

    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)
    write_tabular_fragment(
        gen / "hpa_ca_inverse_search_cost_rows.tex",
        column_spec="rllllrrrrr",
        header=[
            r"\textbf{seed}",
            r"$L$",
            r"$T$",
            r"$p$",
            r"$t$",
            r"\textbf{exact\_k1}",
            r"\textbf{found}",
            r"\textbf{nodes}",
            r"\textbf{backtracks}",
            r"\textbf{x0\_trials}",
        ],
        rows=[[ln[0], ln[1], ln[2], ln[3], ln[4], ln[6], ln[7], ln[8], ln[9], ln[10]] for ln in rows],
        booktabs=True,
    )


if __name__ == "__main__":
    main()

