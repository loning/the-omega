#!/usr/bin/env python3
"""
One-click reproduction entry point for this paper.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _run(script: str, args: list[str]) -> None:
    cmd = [sys.executable, str(Path(__file__).resolve().parent / script), *args]
    print(f"[run_all] running: {' '.join(cmd)}", flush=True)
    subprocess.check_call(cmd)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="Recompute even if cached artifacts exist.")
    ap.add_argument("--m-max", type=int, default=24, help="Max m for counting checks.")
    ap.add_argument("--fiber-m", type=int, default=16, help="m for fiber spectrum experiment (2^m micro states).")
    ap.add_argument("--loop-m", type=int, default=12, help="m for holonomy loop experiment.")
    ap.add_argument("--loop-l", type=int, default=6, help="Loop length bound.")
    ap.add_argument("--dyn-m", type=int, default=10, help="m for local dynamics experiment.")
    ap.add_argument("--dyn-steps", type=int, default=60, help="Time steps for local dynamics experiment.")
    ap.add_argument("--dyn-threshold", type=float, default=0.50)
    ap.add_argument("--dyn-beta", type=float, default=6.0)
    ap.add_argument("--dyn-coupling", type=float, default=1.0)
    ap.add_argument("--dyn-noise", type=float, default=0.02)
    ap.add_argument("--dyn-defect-rate", type=float, default=0.006)
    ap.add_argument("--dyn-r-diffusion", type=float, default=0.25)
    ap.add_argument("--scan", action="store_true", help="Run emergence parameter scan and export phase plots.")
    ap.add_argument("--extended", action="store_true", help="Run object + space-holonomy emergence experiments.")
    ap.add_argument("--extended2", action="store_true", help="Run periodicity + induced-connection holonomy experiments.")
    ap.add_argument("--seed", type=int, default=0, help="Random seed.")
    args = ap.parse_args()

    force_args = ["--force"] if args.force else []

    _run("exp_counts_check.py", [*force_args, "--m-max", str(args.m_max)])
    _run("exp_fiber_spectrum.py", [*force_args, "--m", str(args.fiber_m)])
    _run(
        "exp_holonomy_spectrum.py",
        [*force_args, "--m", str(args.loop_m), "--ell", str(args.loop_l), "--seed", str(args.seed)],
    )
    _run(
        "exp_emergence_local_dynamics.py",
        [
            *force_args,
            "--m",
            str(args.dyn_m),
            "--steps",
            str(args.dyn_steps),
            "--threshold",
            str(args.dyn_threshold),
            "--beta",
            str(args.dyn_beta),
            "--coupling",
            str(args.dyn_coupling),
            "--noise",
            str(args.dyn_noise),
            "--defect-rate",
            str(args.dyn_defect_rate),
            "--r-diffusion",
            str(args.dyn_r_diffusion),
            "--seed",
            str(args.seed),
        ],
    )

    if args.scan:
        _run(
            "exp_emergence_scan.py",
            [
                *force_args,
                "--m",
                str(args.dyn_m),
                "--seed0",
                str(args.seed),
            ],
        )

    if args.extended:
        _run(
            "exp_emergence_objects.py",
            [
                *force_args,
                "--m",
                str(args.dyn_m),
                "--steps",
                str(max(args.dyn_steps, 80)),
                "--threshold",
                str(args.dyn_threshold),
                "--beta",
                str(args.dyn_beta),
                "--coupling",
                str(args.dyn_coupling),
                "--noise",
                str(args.dyn_noise),
                "--defect-rate",
                str(args.dyn_defect_rate),
                "--r-diffusion",
                str(args.dyn_r_diffusion),
                "--seed",
                str(args.seed),
            ],
        )
        _run(
            "exp_emergence_space_holonomy.py",
            [
                *force_args,
                "--m",
                str(args.dyn_m),
                "--steps",
                str(max(args.dyn_steps, 80)),
                "--threshold",
                str(args.dyn_threshold),
                "--beta",
                str(args.dyn_beta),
                "--coupling",
                str(args.dyn_coupling),
                "--noise",
                str(args.dyn_noise),
                "--defect-rate",
                str(args.dyn_defect_rate),
                "--r-diffusion",
                str(args.dyn_r_diffusion),
                "--seed",
                str(args.seed),
            ],
        )

    if args.extended2:
        _run(
            "exp_emergence_objects_periodicity.py",
            [
                *force_args,
                "--m",
                str(args.dyn_m),
                "--steps",
                str(max(args.dyn_steps, 180)),
                "--threshold",
                str(args.dyn_threshold),
                "--beta",
                str(args.dyn_beta),
                "--coupling",
                str(args.dyn_coupling),
                "--noise",
                str(args.dyn_noise),
                "--defect-rate",
                str(args.dyn_defect_rate),
                "--r-diffusion",
                str(args.dyn_r_diffusion),
                "--seed",
                str(args.seed),
            ],
        )
        _run(
            "exp_emergence_space_holonomy_induced.py",
            [
                *force_args,
                "--m",
                str(args.dyn_m),
                "--steps",
                str(max(args.dyn_steps, 80)),
                "--threshold",
                str(args.dyn_threshold),
                "--beta",
                str(args.dyn_beta),
                "--coupling",
                str(args.dyn_coupling),
                "--noise",
                str(args.dyn_noise),
                "--defect-rate",
                str(args.dyn_defect_rate),
                "--r-diffusion",
                str(args.dyn_r_diffusion),
                "--seed",
                str(args.seed),
            ],
        )

    print("[run_all] all experiments completed.", flush=True)


if __name__ == "__main__":
    main()

