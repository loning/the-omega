#!/usr/bin/env python3
"""
One-click reproduction entry point for this paper.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run(script: str, args: list[str]) -> None:
    cmd = [sys.executable, str(Path(__file__).resolve().parent / script), *args]
    print(f"[run_all] running: {' '.join(cmd)}", flush=True)
    subprocess.check_call(cmd)


def main() -> None:
    # This entry point intentionally accepts NO arguments: it is a single-paper,
    # single-button reproduction runner. If you want partial runs, execute the
    # corresponding scripts directly.
    if len(sys.argv) != 1:
        print("[run_all] This script accepts no arguments. Run: python3 scripts/run_all.py", file=sys.stderr, flush=True)
        raise SystemExit(2)

    # Fixed reproduction configuration (paper defaults)
    seed = 0
    m_max = 24
    fiber_m = 16
    loop_m = 12
    loop_l = 6

    dyn_m = 10
    dyn_steps = 60
    dyn_threshold = 0.50
    dyn_beta = 6.0
    dyn_coupling = 1.0
    dyn_noise = 0.02
    dyn_defect_rate = 0.006
    dyn_r_diffusion = 0.25

    transport_coupling = 2.0
    drive_gamma = "6.0"

    _run("exp_counts_check.py", ["--m-max", str(m_max)])
    _run("exp_fiber_spectrum.py", ["--m", str(fiber_m)])
    _run("exp_holonomy_spectrum.py", ["--m", str(loop_m), "--ell", str(loop_l), "--seed", str(seed)])

    _run(
        "exp_emergence_local_dynamics.py",
        [
            "--m",
            str(dyn_m),
            "--steps",
            str(dyn_steps),
            "--threshold",
            str(dyn_threshold),
            "--beta",
            str(dyn_beta),
            "--coupling",
            str(dyn_coupling),
            "--noise",
            str(dyn_noise),
            "--defect-rate",
            str(dyn_defect_rate),
            "--r-diffusion",
            str(dyn_r_diffusion),
            "--seed",
            str(seed),
        ],
    )

    _run("exp_emergence_scan.py", ["--m", str(dyn_m), "--seed0", str(seed)])

    _run(
        "exp_emergence_objects.py",
        [
            "--m",
            str(dyn_m),
            "--steps",
            str(max(dyn_steps, 80)),
            "--threshold",
            str(dyn_threshold),
            "--beta",
            str(dyn_beta),
            "--coupling",
            str(dyn_coupling),
            "--noise",
            str(dyn_noise),
            "--defect-rate",
            str(dyn_defect_rate),
            "--r-diffusion",
            str(dyn_r_diffusion),
            "--seed",
            str(seed),
        ],
    )
    _run(
        "exp_emergence_objects_periodicity.py",
        [
            "--m",
            str(dyn_m),
            "--steps",
            str(max(dyn_steps, 180)),
            "--threshold",
            str(dyn_threshold),
            "--beta",
            str(dyn_beta),
            "--coupling",
            str(dyn_coupling),
            "--noise",
            str(dyn_noise),
            "--defect-rate",
            str(dyn_defect_rate),
            "--r-diffusion",
            str(dyn_r_diffusion),
            "--seed",
            str(seed),
        ],
    )

    _run(
        "exp_emergence_space_holonomy.py",
        [
            "--m",
            str(dyn_m),
            "--steps",
            str(max(dyn_steps, 80)),
            "--threshold",
            str(dyn_threshold),
            "--beta",
            str(dyn_beta),
            "--coupling",
            str(dyn_coupling),
            "--noise",
            str(dyn_noise),
            "--defect-rate",
            str(dyn_defect_rate),
            "--r-diffusion",
            str(dyn_r_diffusion),
            "--seed",
            str(seed),
        ],
    )
    _run(
        "exp_emergence_space_holonomy_induced.py",
        [
            "--m",
            str(dyn_m),
            "--steps",
            str(max(dyn_steps, 80)),
            "--threshold",
            str(dyn_threshold),
            "--beta",
            str(dyn_beta),
            "--coupling",
            str(dyn_coupling),
            "--noise",
            str(dyn_noise),
            "--defect-rate",
            str(dyn_defect_rate),
            "--r-diffusion",
            str(dyn_r_diffusion),
            "--seed",
            str(seed),
        ],
    )

    _run(
        "exp_emergence_transport.py",
        [
            "--m",
            str(dyn_m),
            "--steps",
            "240",
            "--threshold",
            str(dyn_threshold),
            "--beta",
            str(dyn_beta),
            "--coupling",
            str(transport_coupling),
            "--noise",
            str(dyn_noise),
            "--defect-rate",
            str(dyn_defect_rate),
            "--r-diffusion",
            str(dyn_r_diffusion),
            "--advect-p",
            "0.0",
            "--drive-gamma",
            drive_gamma,
            "--seed",
            str(seed),
        ],
    )
    _run("exp_emergence_transport_scan.py", ["--m", str(dyn_m), "--drive-gamma", drive_gamma, "--seed0", str(seed)])
    _run(
        "exp_emergence_transport_walkers.py",
        [
            "--m",
            str(dyn_m),
            "--steps",
            "260",
            "--threshold",
            str(dyn_threshold),
            "--beta",
            str(dyn_beta),
            "--coupling",
            str(transport_coupling),
            "--noise",
            str(dyn_noise),
            "--defect-rate",
            str(dyn_defect_rate),
            "--r-diffusion",
            str(dyn_r_diffusion),
            "--advect-p",
            "0.0",
            "--drive-gamma",
            drive_gamma,
            "--seed",
            str(seed),
        ],
    )
    _run(
        "exp_emergence_transport_scattering.py",
        [
            "--m",
            str(dyn_m),
            "--steps",
            "260",
            "--threshold",
            str(dyn_threshold),
            "--beta",
            str(dyn_beta),
            "--coupling",
            str(transport_coupling),
            "--noise",
            str(dyn_noise),
            "--defect-rate",
            str(dyn_defect_rate),
            "--r-diffusion",
            str(dyn_r_diffusion),
            "--advect-p",
            "0.0",
            "--drive-gamma",
            drive_gamma,
            "--seed0",
            str(seed),
        ],
    )

    print("[run_all] all experiments completed.", flush=True)


if __name__ == "__main__":
    main()

