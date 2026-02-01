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
            name="rotation_fold_vs_parry",
            script="exp_rotation_fold_vs_parry.py",
            args=[],
            expected_outputs=[
                "artifacts/export/rotation_fold_vs_parry.csv",
            ],
        ),
        Step(
            name="iid_sources_fold_vs_parry",
            script="exp_iid_sources_fold_vs_parry.py",
            args=[],
            expected_outputs=[
                "artifacts/export/iid_sources_fold_vs_parry.csv",
            ],
        ),
        Step(
            name="phi_m_sofic_entropy",
            script="exp_phi_m_sofic_entropy.py",
            args=[],
            expected_outputs=[
                "artifacts/export/phi_m_sofic_entropy.csv",
            ],
        ),
        Step(
            name="sync_kernel_primitive_spectrum",
            script="exp_sync_kernel_primitive_spectrum.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_primitive_spectrum.json",
            ],
        ),
        Step(
            name="sync_kernel_weighted_pressure",
            script="exp_sync_kernel_weighted_pressure.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_weighted_pressure.json",
            ],
        ),
        Step(
            name="sync_kernel_weighted_pressure_2d",
            script="exp_sync_kernel_weighted_pressure_2d.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_weighted_pressure_2d.json",
            ],
        ),
        Step(
            name="sync_kernel_weighted_pressure_3d",
            script="exp_sync_kernel_weighted_pressure_3d.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_weighted_pressure_3d.json",
            ],
        ),
        Step(
            name="sync_kernel_real_input_40",
            script="exp_sync_kernel_real_input_40.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_real_input_40.json",
            ],
        ),
        Step(
            name="sync_kernel_real_input_40_zeta_u",
            script="exp_sync_kernel_real_input_40_zeta_u.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_real_input_40_zeta_u.json",
            ],
        ),
        Step(
            name="sync_kernel_real_input_40_arity",
            script="exp_sync_kernel_real_input_40_arity.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_real_input_40_arity.json",
            ],
        ),
        Step(
            name="sync_kernel_real_input_40_arity_2d",
            script="exp_sync_kernel_real_input_40_arity_2d.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_real_input_40_arity_2d.json",
            ],
        ),
        Step(
            name="sync_kernel_real_input_40_logM_theta",
            script="exp_sync_kernel_real_input_40_logM_theta.py",
            args=[
                "--theta-e-steps",
                "25",
                "--theta-2-steps",
                "25",
                "--m-max",
                "30",
                "--c-eps",
                "1e-7",
            ],
            expected_outputs=[
                "artifacts/export/sync_kernel_real_input_40_logM_theta.json",
                "artifacts/export/sync_kernel_real_input_40_logM_theta.png",
                "sections/generated/fig_real_input_40_logM_theta.tex",
            ],
        ),
        Step(
            name="sync_kernel_A_compare",
            script="exp_sync_kernel_A_compare.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_A_compare.json",
                "sections/generated/tab_sync_kernel_A_compare.tex",
            ],
        ),
        Step(
            name="generated_tex_fragments",
            script="exp_generated_tex.py",
            args=[],
            expected_outputs=[
                "artifacts/export/rotation_tv_vs_m.png",
                "artifacts/export/rotation_kl_vs_m.png",
                "artifacts/export/rotation_tv_vs_n.png",
                "artifacts/export/rotation_kl_vs_n.png",
                "artifacts/export/iid_tv_vs_n.png",
                "artifacts/export/arity_class_density_by_m.png",
                "artifacts/export/arity_class_logM_by_m.png",
                "sections/generated/fig_rotation_tv_vs_m.tex",
                "sections/generated/fig_rotation_kl_vs_m.tex",
                "sections/generated/fig_rotation_tv_vs_n.tex",
                "sections/generated/fig_rotation_kl_vs_n.tex",
                "sections/generated/fig_iid_tv_vs_n.tex",
                "sections/generated/fig_arity_class_density.tex",
                "sections/generated/fig_arity_class_logM.tex",
                "sections/generated/tab_rotation_fold_vs_parry_summary.tex",
                "sections/generated/tab_iid_sources_fold_vs_parry_ci.tex",
                "sections/generated/tab_phi_m_sofic_entropy.tex",
            ],
        ),
    ]


def main() -> None:
    steps = build_steps()
    if not steps:
        print("[run_all] No steps configured yet.", flush=True)
        return

    for st in steps:
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

