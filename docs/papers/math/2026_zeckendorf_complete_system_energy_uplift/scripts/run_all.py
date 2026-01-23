#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the reproducible pipeline for this paper (cached + deterministic)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from common_paths import generated_dir, paper_root, scripts_dir


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
            name="runlog_m6_y0",
            script="gen_runlog_m6_y0.py",
            args=[],
            expected_generated=[
                "tab_runlog_m6_y0.tex",
                "tab_runlog_m6_y0_fold.tex",
            ],
        ),
        Step(
            name="m6_fiber_potential_energy",
            script="exp_m6_fiber_potential_energy.py",
            args=[],
            expected_generated=[
                "tab_m6_fiber_potential_energy.tex",
                "fig_m6_fiber_potential_energy_hist.tex",
            ],
        ),
        Step(
            name="zeckendorf_energy_beam_uplift",
            script="exp_zeckendorf_energy_beam_uplift.py",
            args=[],
            expected_generated=[
                "tab_zeckendorf_energy_beam_uplift.tex",
                "fig_zeckendorf_energy_beam_uplift_curve.tex",
            ],
        ),
        Step(
            name="observer_bubble_graph_m6",
            script="fig_observer_bubble_graph_m6.py",
            args=[],
            expected_generated=[
                "fig_observer_bubble_graph_m6.tex",
            ],
        ),
        Step(
            name="m6_confluence_trace_needed",
            script="exp_m6_confluence_trace_needed.py",
            args=[],
            expected_generated=[
                "tab_m6_confluence_example.tex",
            ],
        ),
        Step(
            name="m6_trace_fixedpoint_demo",
            script="exp_m6_trace_fixedpoint_demo.py",
            args=[],
            expected_generated=[
                "tab_m6_trace_fixedpoint_demo.tex",
            ],
        ),
        Step(
            name="quine_emergence_vm",
            script="exp_quine_emergence_vm.py",
            args=[],
            expected_generated=[
                "fig_quine_emergence_state_timeseries.tex",
                "fig_quine_emergence_search_trace.tex",
                "fig_quine_emergence_ledger_deltas.tex",
                "tab_quine_emergence_summary.tex",
                "tab_quine_emergence_excerpt.tex",
            ],
        ),
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    generated_dir().mkdir(parents=True, exist_ok=True)

    for st in build_steps():
        script_path = scripts_dir() / st.script
        if not script_path.is_file():
            raise SystemExit(f"Missing script: {script_path}")

        extra = ["--force"] if bool(args.force) else []
        cmd = [sys.executable, str(script_path), *list(st.args), *extra]
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

