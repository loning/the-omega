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
            name="zeckendorf_scan",
            script="exp_compare_foldings_scan.py",
            args=[],
            expected_outputs=[
                "artifacts/export/zeckendorf_scan_m3_to_m18.csv",
            ],
        ),
        Step(
            name="m6_models_compare",
            script="exp_m6_models_compare.py",
            args=[],
            expected_outputs=[
                "artifacts/export/m6_models_compare.csv",
                "sections/generated/tab_m6_models_compare.tex",
            ],
        ),
        Step(
            name="dim_scan_bitsplit_open",
            script="exp_dim_scan_bitsplit.py",
            args=[],
            expected_outputs=[
                "artifacts/export/dim_scan_bitsplit_open_m6_m9_m12_m15.csv",
                "artifacts/export/resolve_time_vs_dimension_m6_m9_m12_m15.png",
                "artifacts/export/unresolved_vs_dimension_m6_m9_m12_m15.png",
            ],
        ),
        Step(
            name="generated_tex_fragments",
            script="exp_generated_tex.py",
            args=[],
            expected_outputs=[
                "artifacts/export/resolve_time_vs_m.png",
                "artifacts/export/unresolved_vs_m.png",
                "artifacts/export/resolve_time_vs_dimension_m6_m9_m12_m15.png",
                "artifacts/export/unresolved_vs_dimension_m6_m9_m12_m15.png",
                "sections/generated/fig_resolve_time_vs_m.tex",
                "sections/generated/fig_unresolved_vs_m.tex",
                "sections/generated/tab_zeckendorf_scan_m.tex",
                "sections/generated/fig_resolve_time_vs_dimension.tex",
                "sections/generated/fig_unresolved_vs_dimension.tex",
            ],
        ),
    ]


def main() -> None:
    steps = build_steps()
    if not steps:
        print('[run_all] No steps configured yet.', flush=True)
        return

    for st in steps:
        script_path = scripts_dir() / st.script
        if not script_path.is_file():
            raise SystemExit(f'Missing script: {script_path}')

        cmd = [sys.executable, str(script_path), *list(st.args)]
        print(f"[run_all] RUN {st.name}: {' '.join(cmd)}", flush=True)
        subprocess.check_call(cmd, cwd=str(paper_root()))

        for rel in st.expected_outputs:
            p = paper_root() / rel
            if not _nonempty(p):
                raise SystemExit(f'[run_all] expected output missing/empty: {p}')
        print(f'[run_all] OK {st.name}', flush=True)

    print('[run_all] ALL DONE', flush=True)


if __name__ == '__main__':
    main()

