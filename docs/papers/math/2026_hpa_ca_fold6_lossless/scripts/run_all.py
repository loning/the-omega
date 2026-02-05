#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the reproducible pipeline for this paper (cached + deterministic).

This mirrors the z128 paper style:
  - scripts generate artifacts/ (content-addressed run dirs with manifest.json)
  - scripts generate sections/generated/*.tex fragments (to be \\input{}-ed)
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from common_paths import paper_root, scripts_dir, generated_dir


@dataclass(frozen=True)
class Step:
    name: str
    script: str
    args: Sequence[str]
    expected_generated: Sequence[str]


def _nonempty(p: Path) -> bool:
    return p.is_file() and p.stat().st_size > 0


def build_steps() -> List[Step]:
    return [
        Step(
            name="artifact_hash_registry",
            script="exp_artifact_hash_registry.py",
            args=[],
            expected_generated=[
                "artifact_hash_registry.json",
                "artifact_hash_registry_summary.tex",
            ],
        ),
        Step(
            name="export_rules_and_tex",
            script="exp_fold6_rules_and_tex.py",
            args=[],
            expected_generated=[
                "fold6_interface_rule_5x5_table.tex",
                "fold6_preimage_counts_summary.tex",
            ],
        ),
        Step(
            name="exp_lossless_example_run",
            script="exp_hpa_ca_lossless_run.py",
            args=["--L", "300", "--T", "200", "--p", "0.5", "--seed", "1"],
            expected_generated=["hpa_ca_example_run_summary.tex"],
        ),
        Step(
            name="exp_boundary_cases",
            script="exp_hpa_ca_boundary_cases.py",
            args=["--L", "300", "--T", "200", "--seed", "1", "--p", "0.5", "--tail", "80", "--max_period", "40"],
            expected_generated=["hpa_ca_boundary_cases_rows.tex"],
        ),
        Step(
            name="exp_scan_fractal_psd",
            script="exp_hpa_ca_scan_fractal_psd.py",
            args=["--L", "300", "--T", "200", "--ps", "0.1,0.3,0.5,0.7,0.9", "--seeds", "1,2,3,4,5", "--burn_in", "0"],
            expected_generated=["hpa_ca_scan_fractal_psd_summary.tex"],
        ),
        Step(
            name="exp_preimage_counts",
            script="exp_hpa_ca_preimage_counts.py",
            args=["--L", "300", "--T", "200", "--p", "0.5", "--t", "200", "--k", "1", "--seeds", "1,2,3,4,5"],
            expected_generated=["hpa_ca_preimage_counts_rows.tex"],
        ),
        Step(
            name="exp_inverse_search_cost",
            script="exp_hpa_ca_inverse_search_cost.py",
            args=[
                "--L",
                "300",
                "--T",
                "200",
                "--p",
                "0.5",
                "--t",
                "200",
                "--seeds",
                "1,2,3,4,5",
                "--shuffle",
                "--shuffle_seed",
                "1",
                "--max_nodes",
                "200000",
            ],
            expected_generated=["hpa_ca_inverse_search_cost_rows.tex"],
        ),
    ]


def main() -> None:
    generated_dir().mkdir(parents=True, exist_ok=True)

    for st in build_steps():
        script_path = scripts_dir() / st.script
        if not script_path.is_file():
            raise SystemExit(f"Missing script: {script_path}")

        cmd = [sys.executable, str(script_path), *list(st.args)]
        print(f"[run_all] RUN {st.name}: {' '.join(cmd)}", flush=True)
        subprocess.check_call(cmd, cwd=str(paper_root()))

        for rel in st.expected_generated:
            p = generated_dir() / rel
            if not _nonempty(p):
                raise SystemExit(f"[run_all] expected generated file missing/empty: {p}")
        print(f"[run_all] OK {st.name}", flush=True)

    print("[run_all] ALL DONE", flush=True)


if __name__ == "__main__":
    main()

