#!/usr/bin/env python3
"""Run a canonical lossless HPA-CA experiment (cached) and emit a LaTeX summary.

Artifacts:
  artifacts/hpa_ca_lossless_run/<run_id>/
    - data.npz
    - spacetime.png
    - uplift.png
    - density.png
    - psd.png
    - boxcount.png
    - manifest.json

Generated LaTeX (PyLaTeX):
  sections/generated/hpa_ca_example_run_summary.tex
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import matplotlib

matplotlib.use("Agg")  # must be set before importing pyplot in the core script

import numpy as np

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir
from common_tex_pylatex import write_tabular_fragment

from hpa_ca_lossless import (
    UPLIFT_VALUES,
    evolve,
    save_boxcount_png,
    save_density_png,
    save_psd_png,
    save_spacetime_png,
    save_uplift_png,
)
from pylatex import Command


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, default=300)
    ap.add_argument("--T", type=int, default=200)
    ap.add_argument("--p", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.L % 6 != 0:
        raise SystemExit("L must be a multiple of 6")

    script_path = Path(__file__).resolve()
    params = {"L": int(args.L), "T": int(args.T), "p": float(args.p), "seed": int(args.seed)}

    required = ["data.npz", "spacetime.png", "uplift.png", "density.png", "psd.png", "boxcount.png"]
    run = prepare_run(
        "hpa_ca_lossless_run",
        params=params,
        script_path=script_path,
        required_files=required,
        force=bool(args.force),
    )

    if not run.cached:
        res = evolve(L=args.L, T=args.T, seed=args.seed, p=args.p)

        np.savez_compressed(
            run.run_dir / "data.npz",
            states=res.states,
            uplift_codes=res.uplift,
            density=res.density,
            uplift_values=np.array(UPLIFT_VALUES, dtype=np.int32),
        )

        save_spacetime_png(res.states, str(run.run_dir / "spacetime.png"))
        save_uplift_png(res.uplift, str(run.run_dir / "uplift.png"))
        save_density_png(res.density, str(run.run_dir / "density.png"))
        save_psd_png(res.density, str(run.run_dir / "psd.png"))
        D = save_boxcount_png(res.states, str(run.run_dir / "boxcount.png"))

        manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
        manifest["metrics"] = {"final_density": float(res.density[-1]), "boxcount_D": float(D)}
        manifest = add_output_hashes(manifest, run.run_dir, rel_paths=required)
        write_manifest(run.run_dir, manifest)

    # Build LaTeX summary (load metrics from manifest).
    man = (run.run_dir / "manifest.json").read_text(encoding="utf-8")
    # Small parse without importing json to avoid accidental formatting; numpy is already present anyway.
    import json as _json

    mj = _json.loads(man)
    final_density = mj.get("metrics", {}).get("final_density", "")
    boxD = mj.get("metrics", {}).get("boxcount_D", "")
    art_path = f"artifacts/{run.experiment}/{run.run_id}/".replace("_", r"\_")

    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)
    write_tabular_fragment(
        gen / "hpa_ca_example_run_summary.tex",
        column_spec="ll",
        header=[r"\textbf{key}", r"\textbf{value}"],
        rows=[
            [r"run\_id", Command("texttt", run.run_id)],
            [r"L", str(args.L)],
            [r"T", str(args.T)],
            [r"p", str(args.p)],
            [r"seed", str(args.seed)],
            [r"final\_density", str(final_density)],
            [r"boxcount\_D", str(boxD)],
            [r"artifacts", Command("texttt", art_path)],
        ],
        booktabs=True,
    )


if __name__ == "__main__":
    main()

