#!/usr/bin/env python3
"""
One-click reproduction entry point for this paper.

Caching:
  - This runner skips expensive scripts if the LaTeX-consumed outputs already
    exist under sections/generated/.
  - Use --force to recompute everything.

Paper asset policy:
  - All paper-referenced stable images must live under sections/generated/assets/.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from common_paths import generated_assets_dir, generated_dir


def _run(script: str, args: list[str]) -> None:
    cmd = [sys.executable, str(Path(__file__).resolve().parent / script), *args]
    print(f"[run_all] running: {' '.join(cmd)}", flush=True)
    subprocess.check_call(cmd)


def _have_all(paths: list[Path]) -> bool:
    return all(p.is_file() for p in paths)


def _sync_legacy_exports(force: bool) -> None:
    """
    Migration helper:
      - old stable export dir: artifacts/export/
      - new stable export dir: sections/generated/assets/
    Copy *.png if missing (or force=True).
    """
    root = Path(__file__).resolve().parents[1]
    old = root / "artifacts" / "export"
    new = generated_assets_dir()
    new.mkdir(parents=True, exist_ok=True)
    if not old.is_dir():
        return
    # Only keep assets that the paper actually references.
    needed = {
        "emergence_space_holonomy_rate.png",
        "emergence_space_holonomy_compare.png",
    }
    for src in old.glob("*.png"):
        if src.name not in needed:
            continue
        dst = new / src.name
        if (not dst.is_file()) or force:
            shutil.copyfile(src, dst)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="Recompute everything (ignore caches).")
    args = ap.parse_args()

    force = bool(args.force)

    # Ensure LaTeX-referenced assets live under sections/generated/assets/.
    _sync_legacy_exports(force=force)

    # Fixed reproduction configuration (paper defaults)
    seed = 0
    m_max = 24
    fiber_m = 16
    loop_m = 12
    loop_l = 6

    dyn_m = 10
    dyn_steps = 80
    dyn_threshold = 0.50
    dyn_beta = 6.0
    dyn_coupling = 1.0
    dyn_noise = 0.02
    dyn_defect_rate = 0.006
    dyn_r_diffusion = 0.25

    want_counts = [generated_dir() / "counts_check.tex"]
    if force or (not _have_all(want_counts)):
        _run("exp_counts_check.py", ["--m-max", str(m_max), *([] if not force else ["--force"])])
    else:
        print("[run_all] cached: exp_counts_check.py", flush=True)

    want_fiber = [generated_dir() / "fiber_entropy_summary.tex"]
    if force or (not _have_all(want_fiber)):
        _run("exp_fiber_spectrum.py", ["--m", str(fiber_m), *([] if not force else ["--force"])])
    else:
        print("[run_all] cached: exp_fiber_spectrum.py", flush=True)

    want_holo = [generated_dir() / "holonomy_interface_vs_bulk.tex"]
    if force or (not _have_all(want_holo)):
        _run(
            "exp_holonomy_spectrum.py",
            ["--m", str(loop_m), "--ell", str(loop_l), "--seed", str(seed), *([] if not force else ["--force"])],
        )
    else:
        print("[run_all] cached: exp_holonomy_spectrum.py", flush=True)

    want_space = [
        generated_dir() / "emergence_space_holonomy_summary.tex",
        generated_assets_dir() / "emergence_space_holonomy_rate.png",
    ]
    if force or (not _have_all(want_space)):
        _run(
            "exp_emergence_space_holonomy.py",
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
                *([] if not force else ["--force"]),
            ],
        )
    else:
        print("[run_all] cached: exp_emergence_space_holonomy.py", flush=True)

    want_space_induced = [
        generated_dir() / "emergence_space_holonomy_induced_summary.tex",
        generated_assets_dir() / "emergence_space_holonomy_compare.png",
    ]
    if force or (not _have_all(want_space_induced)):
        _run(
            "exp_emergence_space_holonomy_induced.py",
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
                *([] if not force else ["--force"]),
            ],
        )
    else:
        print("[run_all] cached: exp_emergence_space_holonomy_induced.py", flush=True)

    _sync_legacy_exports(force=False)

    print("[run_all] all experiments completed.", flush=True)


if __name__ == "__main__":
    main()

