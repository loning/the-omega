#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the reproducible experiment pipeline for this paper."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from common_paths import paper_root, scripts_dir


@dataclass(frozen=True)
class Step:
    name: str
    script: str
    args: Sequence[str]
    expected_outputs: Sequence[str]


def _nonempty(p: Path) -> bool:
    return p.is_file() and p.stat().st_size > 0


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _cache_path() -> Path:
    return paper_root() / "artifacts" / "export" / "run_all_cache.json"


def _load_cache() -> Dict[str, object]:
    p = _cache_path()
    if not p.is_file():
        return {"version": 1, "steps": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        # If cache is corrupted, ignore it (deterministic pipeline still works).
        return {"version": 1, "steps": {}}


def _write_cache(cache: Dict[str, object]) -> None:
    p = _cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _step_signature(script_path: Path, args: Sequence[str]) -> Dict[str, object]:
    return {
        "script": script_path.name,
        "script_sha256": _sha256_file(script_path),
        "args": list(args),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }


def _outputs_ok(step: Step) -> Tuple[bool, List[str]]:
    missing: List[str] = []
    for rel in step.expected_outputs:
        p = paper_root() / rel
        if not _nonempty(p):
            missing.append(rel)
    return (len(missing) == 0), missing


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
            name="sync_kernel_real_input_40_arity_3d",
            script="exp_sync_kernel_real_input_40_arity_3d.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_real_input_40_arity_3d.json",
                "sections/generated/tab_real_input_40_arity_dirichlet_mertens_222.tex",
                "sections/generated/tab_real_input_40_arity_dirichlet_mertens_322.tex",
                "sections/generated/tab_real_input_40_arity_dirichlet_mertens_333.tex",
                "sections/generated/tab_real_input_40_arity_dirichlet_mertens_555.tex",
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
                "--k-max",
                "200",
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
            name="sync_kernel_graph_viz",
            script="exp_sync_kernel_graph_viz.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_10_state_graph.png",
                "artifacts/export/sync_kernel_real_input_40_matrix.png",
                "sections/generated/fig_sync_kernel_10_state_graph.tex",
                "sections/generated/fig_sync_kernel_real_input_40_matrix.tex",
            ],
        ),
        Step(
            name="parallel_addition_kernels_bfs",
            script="exp_parallel_addition_kernels_bfs.py",
            args=[
                "--primitive-n",
                "20",
                "--u-grid",
                "0,0.05,0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95,1",
            ],
            expected_outputs=[
                "artifacts/export/parallel_addition_kernels_bfs.json",
                "sections/generated/tab_parallel_addition_kernels_bfs.tex",
                "sections/generated/tab_parallel_addition_kernels_fingerprint.tex",
                "sections/generated/tab_parallel_addition_kernels_fingerprint_main.tex",
            ],
        ),
        Step(
            name="parallel_addition_kernels_fingerprint_figs",
            script="exp_parallel_addition_kernels_fingerprint_figs.py",
            args=[],
            expected_outputs=[
                "artifacts/export/parallel_addition_kernels_Bn0.png",
                "artifacts/export/parallel_addition_kernels_lambda_u.png",
                "sections/generated/fig_parallel_addition_kernels_Bn0.tex",
                "sections/generated/fig_parallel_addition_kernels_lambda_u.tex",
            ],
        ),
        Step(
            name="parallel_addition_kernels_weighted_primitive",
            script="exp_parallel_addition_kernels_weighted_primitive.py",
            args=[],
            expected_outputs=[
                "artifacts/export/parallel_addition_kernels_weighted_primitive.json",
                "sections/generated/tab_parallel_addition_kernels_weighted_primitive.tex",
            ],
        ),
        Step(
            name="parallel_addition_kernels_zeta_series",
            script="exp_parallel_addition_kernels_zeta_series.py",
            args=[],
            expected_outputs=[
                "artifacts/export/parallel_addition_kernels_zeta_series.json",
                "sections/generated/tab_parallel_addition_kernels_zeta_series.tex",
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
    parser = argparse.ArgumentParser(description="Run reproducible experiment pipeline (with step cache).")
    parser.add_argument("--force", action="store_true", help="Force rerun all steps (ignore cache).")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache (always run).")
    args = parser.parse_args()

    steps = build_steps()
    if not steps:
        print("[run_all] No steps configured yet.", flush=True)
        return

    cache = _load_cache()
    steps_cache: Dict[str, object] = dict(cache.get("steps", {}))  # type: ignore[assignment]

    for st in steps:
        script_path = scripts_dir() / st.script
        if not script_path.is_file():
            raise SystemExit(f"Missing script: {script_path}")

        sig = _step_signature(script_path, st.args)
        ok, missing = _outputs_ok(st)
        cached = steps_cache.get(st.name)
        if ok and (not args.force) and (not args.no_cache) and cached == sig:
            print(f"[run_all] SKIP {st.name} (cache hit)", flush=True)
            continue

        # Cache warm-up: if outputs already exist but cache has no entry,
        # we adopt the current signature without rerunning (auditable, avoids slow cold-start).
        if ok and (not args.force) and (not args.no_cache) and cached is None:
            steps_cache[st.name] = sig
            cache["steps"] = steps_cache
            _write_cache(cache)
            print(f"[run_all] SKIP {st.name} (cache warm-up: outputs already present)", flush=True)
            continue

        if ok and (not args.force) and (not args.no_cache) and cached != sig:
            # Outputs exist but signature changed; rerun for auditability.
            print(f"[run_all] RERUN {st.name} (signature changed)", flush=True)
        elif not ok:
            print(f"[run_all] RERUN {st.name} (missing outputs: {', '.join(missing)})", flush=True)

        cmd = [sys.executable, str(script_path), *list(st.args)]
        print(f"[run_all] RUN {st.name}: {' '.join(cmd)}", flush=True)
        subprocess.check_call(cmd, cwd=str(paper_root()))

        for rel in st.expected_outputs:
            p = paper_root() / rel
            if not _nonempty(p):
                raise SystemExit(f"[run_all] expected output missing/empty: {p}")
        print(f"[run_all] OK {st.name}", flush=True)

        # Update cache after a successful step.
        steps_cache[st.name] = sig
        cache["steps"] = steps_cache
        _write_cache(cache)

    print("[run_all] ALL DONE", flush=True)


if __name__ == "__main__":
    main()

