#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the reproducible experiment pipeline for this paper."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from common_paths import paper_root, scripts_dir


@dataclass(frozen=True)
class Step:
    name: str
    script: str
    args: Sequence[str]
    expected_outputs: Sequence[str]


def _nonempty(p: Path) -> bool:
    return p.is_file() and p.stat().st_size > 0


def build_steps() -> List[Step]:
    return [
        Step(
            name="hypercube_residual_scan",
            script="exp_hypercube_residual_scan.py",
            args=[],
            expected_outputs=[
                "artifacts/export/hypercube_residual_scan_m3_to_m18.csv",
                "artifacts/export/hypercube_residual_ambiguity_m3_to_m18.png",
            ],
        ),
        Step(
            name="hypercube_ambiguous_pairs",
            script="exp_hypercube_ambiguous_pairs.py",
            args=["--ms", "6,9"],
            expected_outputs=[
                "artifacts/export/m6_hypercube_ambiguous_pairs.txt",
                "artifacts/export/m9_hypercube_ambiguous_pairs.txt",
            ],
        ),
        Step(
            name="dim_scan_bitsplit_open",
            script="exp_dim_scan.py",
            args=["--ms", "6,9,12,15"],
            expected_outputs=[
                "artifacts/export/dim_scan_m6_m9_m12_m15.csv",
                "artifacts/export/resolve_time_vs_dimension_m6_m9_m12_m15.png",
                "artifacts/export/unresolved_vs_dimension_m6_m9_m12_m15.png",
            ],
        ),
        Step(
            name="m6_models_compare",
            script="exp_m6_models_compare.py",
            args=[],
            expected_outputs=[
                "artifacts/export/m6_wl1_hilbert_vs_bitsplit_vs_hypercube.csv",
                "artifacts/export/m6_2d_hilbert_grid.png",
                "artifacts/export/m6_3d_hilbert_layers.png",
            ],
        ),
        Step(
            name="m6_fold6_hilbert_table",
            script="exp_m6_fold6_hilbert_table.py",
            args=[],
            expected_outputs=["artifacts/export/m6_fold6_hilbert2d3d_table.csv"],
        ),
        Step(
            name="generated_tex_fragments",
            script="exp_generated_tex.py",
            args=[],
            expected_outputs=[
                "sections/generated/fig_hypercube_residual_ambiguity.tex",
                "sections/generated/fig_resolve_time_vs_dimension.tex",
                "sections/generated/fig_unresolved_vs_dimension.tex",
                "sections/generated/fig_m6_hilbert_2d_grid.tex",
                "sections/generated/fig_m6_hilbert_3d_layers.tex",
                "sections/generated/tab_m6_models_compare.tex",
                "sections/generated/tab_hypercube_residual_unresolved_only.tex",
                "sections/generated/tab_dim_scan_m6_m9.tex",
            ],
        ),
    ]


def main() -> None:
    for st in build_steps():
        script_path = scripts_dir() / st.script
        if not script_path.is_file():
            raise SystemExit(f"Missing script: {script_path}")

        cmd = [sys.executable, str(script_path), *list(st.args)]
        print(f"[run_all] RUN {st.name}: {' '.join(cmd)}", flush=True)
        subprocess.check_call(cmd, cwd=str(paper_root()))

        for rel in st.expected_outputs:
            p = paper_root() / rel
            if not _nonempty(p):
                raise SystemExit(f"[run_all] expected output missing/empty: {p}")
        print(f"[run_all] OK {st.name}", flush=True)

    print("[run_all] ALL DONE", flush=True)


if __name__ == "__main__":
    main()

