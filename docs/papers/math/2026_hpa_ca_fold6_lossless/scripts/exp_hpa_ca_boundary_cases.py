#!/usr/bin/env python3
"""Run boundary/extreme initial conditions (cached) and emit a LaTeX table.

Artifacts:
  artifacts/hpa_ca_boundary_cases/<run_id>/
    - cases.csv
    - manifest.json

Generated LaTeX:
  sections/generated/hpa_ca_boundary_cases_rows.tex
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir
from common_tex_pylatex import write_tabular_fragment
from hpa_ca_lossless import detect_tail_period, evolve_from_state, invert_step


@dataclass(frozen=True)
class CaseSpec:
    name: str
    kind: str
    params: Dict[str, int]


def make_initial_state(kind: str, L: int, seed: int, p: float, params: Dict[str, int]) -> np.ndarray:
    if kind == "all_zeros":
        return np.zeros(L, dtype=np.uint8)
    if kind == "all_ones":
        return np.ones(L, dtype=np.uint8)
    if kind == "single_one":
        state = np.zeros(L, dtype=np.uint8)
        pos = int(params.get("pos", 0)) % L
        state[pos] = 1
        return state
    if kind == "single_zero":
        state = np.ones(L, dtype=np.uint8)
        pos = int(params.get("pos", 0)) % L
        state[pos] = 0
        return state
    if kind == "alternating01":
        return (np.arange(L, dtype=np.int64) % 2).astype(np.uint8)
    if kind == "alternating10":
        return (1 - (np.arange(L, dtype=np.int64) % 2)).astype(np.uint8)
    if kind == "repeat_word6":
        word = str(params.get("word", "100001"))
        if len(word) != 6 or any(ch not in "01" for ch in word):
            raise ValueError("repeat_word6 requires params['word'] as a 6-bit string")
        bits = np.array([0 if ch == "0" else 1 for ch in word], dtype=np.uint8)
        return np.tile(bits, L // 6)
    if kind == "bernoulli":
        rng = np.random.default_rng(seed)
        return (rng.random(L) < p).astype(np.uint8)
    raise ValueError(f"Unknown kind: {kind}")


def check_invertibility(states: np.ndarray, uplift_codes: np.ndarray) -> bool:
    T = int(uplift_codes.shape[0])
    state = states[-1].copy()
    for t in range(T - 1, -1, -1):
        offset = 0 if (t % 2 == 0) else 3
        state = invert_step(state, uplift_codes[t], offset=offset)
        if not np.array_equal(state, states[t]):
            return False
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, default=300)
    ap.add_argument("--T", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1, help="used only for stochastic cases (bernoulli)")
    ap.add_argument("--p", type=float, default=0.5, help="used only for stochastic cases (bernoulli)")
    ap.add_argument("--tail", type=int, default=120, help="tail window for period detection")
    ap.add_argument("--max_period", type=int, default=60, help="max period to test")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.L % 6 != 0:
        raise SystemExit("L must be a multiple of 6")
    if args.T < 2:
        raise SystemExit("T must be >= 2")

    cases: List[CaseSpec] = [
        CaseSpec(name="all_zeros", kind="all_zeros", params={}),
        CaseSpec(name="all_ones", kind="all_ones", params={}),
        CaseSpec(name="single_one", kind="single_one", params={"pos": 0}),
        CaseSpec(name="single_zero", kind="single_zero", params={"pos": 0}),
        CaseSpec(name="alternating01", kind="alternating01", params={}),
        CaseSpec(name="repeat_100001", kind="repeat_word6", params={"word": "100001"}),
        CaseSpec(name="bernoulli_p", kind="bernoulli", params={}),
    ]

    script_path = Path(__file__).resolve()
    params = {
        "L": int(args.L),
        "T": int(args.T),
        "seed": int(args.seed),
        "p": float(args.p),
        "tail": int(args.tail),
        "max_period": int(args.max_period),
        "cases": [(c.name, c.kind, dict(c.params)) for c in cases],
    }

    required = ["cases.csv"]
    run = prepare_run(
        "hpa_ca_boundary_cases",
        params=params,
        script_path=script_path,
        required_files=required,
        force=bool(args.force),
    )

    if not run.cached:
        out_csv = run.run_dir / "cases.csv"
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "case",
                    "kind",
                    "L",
                    "T",
                    "seed",
                    "p",
                    "invert_ok",
                    "tail_period",
                    "final_density",
                ]
            )
            for i, c in enumerate(cases):
                if (i % 1) == 0:
                    print(f"[boundary] {i+1}/{len(cases)} {c.name} start", flush=True)
                init = make_initial_state(c.kind, L=args.L, seed=args.seed, p=args.p, params=c.params)
                res = evolve_from_state(init, T=args.T)
                invert_ok = check_invertibility(res.states, res.uplift)
                period = detect_tail_period(res.states, tail=int(args.tail), max_period=int(args.max_period))
                w.writerow(
                    [
                        c.name,
                        c.kind,
                        args.L,
                        args.T,
                        args.seed,
                        args.p,
                        int(invert_ok),
                        int(period),
                        f"{float(res.density[-1]):.6f}",
                    ]
                )
                print(
                    f"[boundary] {c.name} done invert_ok={int(invert_ok)} tail_period={int(period)} final_density={float(res.density[-1]):.6f}",
                    flush=True,
                )

        manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
        manifest = add_output_hashes(manifest, run.run_dir, rel_paths=required)
        write_manifest(run.run_dir, manifest)

    # Emit LaTeX table from CSV
    rows: List[List[str]] = []
    with open(run.run_dir / "cases.csv", "r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        _header = next(r)
        for line in r:
            rows.append(line)

    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)
    write_tabular_fragment(
        gen / "hpa_ca_boundary_cases_rows.tex",
        column_spec="lllrrrllr",
        header=[
            r"\textbf{case}",
            r"\textbf{kind}",
            r"\textbf{L}",
            r"\textbf{T}",
            r"\textbf{seed}",
            r"\textbf{p}",
            r"\textbf{invert}",
            r"\textbf{tail\_period}",
            r"\textbf{final\_rho}",
        ],
        rows=[
            [
                ln[0].replace("_", r"\_"),
                ln[1].replace("_", r"\_"),
                ln[2],
                ln[3],
                ln[4],
                ln[5],
                ln[6],
                ln[7],
                ln[8],
            ]
            for ln in rows
        ],
        booktabs=True,
    )


if __name__ == "__main__":
    main()

