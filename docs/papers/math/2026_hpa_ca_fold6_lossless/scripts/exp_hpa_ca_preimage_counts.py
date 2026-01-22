#!/usr/bin/env python3
"""Compute symbolic 1-step preimage counts on sampled visible slices (cached).

Artifacts:
  artifacts/hpa_ca_preimage_counts/<run_id>/counts.csv
  artifacts/hpa_ca_preimage_counts/<run_id>/manifest.json

Generated LaTeX:
  sections/generated/hpa_ca_preimage_counts_rows.tex
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List

import numpy as np

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir
from common_tex_pylatex import write_tabular_fragment
from hpa_ca_lossless import evolve
from hpa_ca_preimage_count import build_succ_table, count_preimages_k_ring, f_pair, stable_words_x6, words_from_state_bits
from pylatex import Command


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
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--seeds", type=str, default="1,2,3,4,5")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.L % 6 != 0:
        raise SystemExit("L must be a multiple of 6")
    if args.t < 1:
        raise SystemExit("t must be >= 1")
    if args.k < 1:
        raise SystemExit("k must be >= 1")

    seeds = parse_int_list(args.seeds)
    if not seeds:
        raise SystemExit("No seeds provided")

    script_path = Path(__file__).resolve()
    params = {
        "L": int(args.L),
        "T": int(args.T),
        "p": float(args.p),
        "t": int(args.t),
        "k": int(args.k),
        "seeds": seeds,
    }

    required = ["counts.csv"]
    run = prepare_run(
        "hpa_ca_preimage_counts",
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
        out_csv = run.run_dir / "counts.csv"
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["seed", "L", "T", "p", "t", "stable_offset", "k", "preimage_count"])
            for sd in seeds:
                res = evolve(L=args.L, T=args.T, seed=sd, p=args.p)
                state = res.states[args.t]
                out_words = words_from_state_bits(state, offset=stable_offset)
                if not all(ww in idx for ww in out_words):
                    count = 0
                else:
                    out_seq = [idx[ww] for ww in out_words]
                    count = count_preimages_k_ring(out_seq, succ, k=args.k)
                w.writerow([sd, args.L, args.T, args.p, args.t, stable_offset, args.k, count])

        manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
        manifest = add_output_hashes(manifest, run.run_dir, rel_paths=required)
        write_manifest(run.run_dir, manifest)

    # Emit LaTeX table fragment from CSV
    rows: List[List[str]] = []
    with open(run.run_dir / "counts.csv", "r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        for line in r:
            rows.append(line)

    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)
    write_tabular_fragment(
        gen / "hpa_ca_preimage_counts_rows.tex",
        column_spec="rllllrr",
        header=[r"\textbf{seed}", r"$L$", r"$T$", r"$p$", r"$t$", r"\textbf{offset}", r"\textbf{count}"],
        rows=[[line[0], line[1], line[2], line[3], line[4], line[5], line[7]] for line in rows],
        booktabs=True,
    )


if __name__ == "__main__":
    main()

