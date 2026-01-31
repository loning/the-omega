#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the minimal reproducible numerical demonstrations for this paper."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from common_paths import artifacts_dir, generated_dir, paper_root, scripts_dir


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
            name="demo_1d_zero_entropy_time",
            script="demo_1d_zero_entropy_time.py",
            args=["--out", "artifacts", "--fig-out", "sections/generated", "--seed", "0"],
            expected_outputs=[
                "sections/generated/demo_1d_tau_log_growth.png",
                "sections/generated/demo_1d_entropy_rate_proxy.png",
                "artifacts/demo_1d_entropy_estimates.json",
            ],
        ),
        Step(
            name="demo_2d_cnp_fibonacci_fingerprints",
            script="demo_2d_cnp_fibonacci_fingerprints.py",
            args=["--out", "artifacts", "--fig-out", "sections/generated", "--seed", "0"],
            expected_outputs=[
                "sections/generated/demo_2d_diffraction.png",
                "sections/generated/demo_2d_visibility_curve.png",
                "sections/generated/demo_2d_degeneracy_hist.png",
                "artifacts/demo_2d_fingerprints.json",
            ],
        ),
        Step(
            name="demo_6d_icosa_fingerprints",
            script="demo_6d_icosa_fingerprints.py",
            args=["--out", "artifacts", "--fig-out", "sections/generated", "--seed", "0"],
            expected_outputs=[
                "sections/generated/demo_6d_diffraction_slice.png",
                "sections/generated/demo_6d_visibility_curve.png",
                "sections/generated/demo_6d_entropy_rate_proxy.png",
                "artifacts/demo_6d_fingerprints.json",
            ],
        ),
    ]


def main() -> None:
    steps = build_steps()
    if not steps:
        print("[run_all] No steps configured yet.", flush=True)
        return

    root = paper_root()
    out_dir = artifacts_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_dir().mkdir(parents=True, exist_ok=True)

    runlog = out_dir / "run.log"
    params_path = out_dir / "params.json"
    params_path.write_text(
        json.dumps(
            {
                "timestamp_unix": time.time(),
                "steps": [
                    {"name": s.name, "script": s.script, "args": list(s.args)}
                    for s in steps
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with runlog.open("w", encoding="utf-8") as f:
        f.write("[run_all] START\n")
        f.write(f"[run_all] paper_root={root}\n")
        f.write(f"[run_all] python={sys.executable}\n")

        for st in steps:
            script_path = scripts_dir() / st.script
            if not script_path.is_file():
                raise SystemExit(f"Missing script: {script_path}")

            cmd = [sys.executable, str(script_path), *list(st.args)]
            print(f"[run_all] RUN {st.name}: {' '.join(cmd)}", flush=True)
            f.write(f"[run_all] RUN {st.name}: {' '.join(cmd)}\n")
            f.flush()

            subprocess.check_call(cmd, cwd=str(root))

            for rel in st.expected_outputs:
                p = root / rel
                if not _nonempty(p):
                    raise SystemExit(f"[run_all] expected output missing/empty: {p}")

            print(f"[run_all] OK {st.name}", flush=True)
            f.write(f"[run_all] OK {st.name}\n")
            f.flush()

        f.write("[run_all] ALL DONE\n")
        f.flush()

    print("[run_all] ALL DONE", flush=True)


if __name__ == "__main__":
    main()

