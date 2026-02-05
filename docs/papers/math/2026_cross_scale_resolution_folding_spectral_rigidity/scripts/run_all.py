#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the reproducible pipeline for this paper (cached + deterministic).

Design:
  - scripts generate artifacts/ (content-addressed run dirs with manifest.json)
  - scripts generate sections/generated/*.tex fragments (to be \\input{}-ed)
"""

from __future__ import annotations

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
            name="fold6_tables",
            script="exp_fold6_tables.py",
            args=[],
            expected_generated=[
                "fold6_preimage_histogram_table.tex",
                "fold6_boundary_preimages_table.tex",
                "fold6_full_table_part1.tex",
                "fold6_full_table_part2.tex",
            ],
        ),
        Step(
            name="cover_graph",
            script="exp_cover_graph.py",
            args=[],
            expected_generated=["cover_graph_summary.tex"],
        ),
        Step(
            name="artifact_hash_registry",
            script="exp_artifact_hash_registry.py",
            args=[],
            expected_generated=["artifact_hash_registry.json", "artifact_hash_registry_summary.tex"],
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

