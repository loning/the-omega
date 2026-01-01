# -*- coding: utf-8 -*-
"""
Run the full reproducible pipeline for this paper.

This script:
  - executes all exp_*.py generators in a deterministic order,
  - checks that expected LaTeX fragments were produced,
  - fails fast if any generator raises an assertion error.

Notes:
  - We intentionally run scripts by file path (not as modules) to preserve the
    paper's current import style (e.g., `import exp_fold6_stats as fold`).
  - The core combinatorics are standard-library only; some extended scripts may
    require optional scientific dependencies.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from common_paths import generated_dir, paper_root, scripts_dir
from common_tex import nonempty_file


@dataclass(frozen=True)
class Step:
    name: str
    script: str
    expected_outputs: Sequence[str]


def _run_script(script_path: Path) -> None:
    cmd = [sys.executable, str(script_path)]
    subprocess.run(cmd, cwd=str(paper_root()), check=True)


def _check_outputs(rel_paths: Iterable[str]) -> None:
    missing: List[str] = []
    for rel in rel_paths:
        p = paper_root() / rel
        if not nonempty_file(p):
            missing.append(rel)
    if missing:
        msg = "Missing/empty generated outputs:\n" + "\n".join(f"  - {m}" for m in missing)
        raise RuntimeError(msg)


def build_steps() -> List[Step]:
    # Keep this list explicit and auditable.
    return [
        Step(
            name="X6 enumeration",
            script="exp_x6_enumeration.py",
            expected_outputs=[
                "sections/generated/x6_weight_rows.tex",
                "sections/generated/x6_cyclic_boundary_rows.tex",
            ],
        ),
        Step(
            name="Xm sweep",
            script="exp_xm_enumeration.py",
            expected_outputs=[
                "sections/generated/xm_sweep_rows.tex",
            ],
        ),
        Step(
            name="Fold6 stats",
            script="exp_fold6_stats.py",
            expected_outputs=[
                "sections/generated/fold6_degeneracy_rows.tex",
                "sections/generated/fold6_full_table_rows.tex",
            ],
        ),
        Step(
            name="Foldm sweep",
            script="exp_foldm_stats.py",
            expected_outputs=[
                "sections/generated/foldm_sweep_rows.tex",
            ],
        ),
        Step(
            name="Hilbert chirality index (n=3)",
            script="exp_hilbert_chirality_index.py",
            expected_outputs=[
                "sections/generated/hilbert_chi_summary.tex",
            ],
        ),
        Step(
            name="Hilbert chirality sweep",
            script="exp_hilbert_chi_sweep.py",
            expected_outputs=[
                "sections/generated/hilbert_chi_sweep_rows.tex",
            ],
        ),
        Step(
            name="Resolution-threshold staircase",
            script="exp_resolution_thresholds.py",
            expected_outputs=[
                "sections/generated/resolution_thresholds_rows.tex",
            ],
        ),
        Step(
            name="Edge mismatch decomposition (toy connection)",
            script="exp_edge_mismatch_decomposition.py",
            expected_outputs=[
                "sections/generated/edge_mismatch_deg_pair_rows.tex",
                "sections/generated/edge_mismatch_cost_quantiles_rows.tex",
            ],
        ),
        Step(
            name="Plaquette holonomy (toy connection)",
            script="exp_holonomy_loops.py",
            expected_outputs=[
                "sections/generated/holonomy_cycle_type_rows.tex",
            ],
        ),
        Step(
            name="SM labeling solver",
            script="exp_sm_labeling_solver.py",
            expected_outputs=[
                "sections/generated/sm_labeling_rows.tex",
                "sections/generated/sm_labeling_invariants_rows.tex",
            ],
        ),
        Step(
            name="Label lift consistency",
            script="exp_labeling_lift_consistency.py",
            expected_outputs=[
                "sections/generated/label_lift_rows.tex",
            ],
        ),
        Step(
            name="Mass spectrum",
            script="exp_mass_spectrum.py",
            expected_outputs=[
                "sections/generated/mass_spectrum_anchor_rows.tex",
                "sections/generated/mass_spectrum_quark_rows.tex",
                "sections/generated/mass_spectrum_neutrino_rows.tex",
            ],
        ),
        Step(
            name="Mass matching layer",
            script="exp_mass_matching_layer.py",
            expected_outputs=[
                "sections/generated/mass_matching_layer_rows.tex",
            ],
        ),
        Step(
            name="Mass depth rigidity",
            script="exp_mass_depth_rigidity.py",
            expected_outputs=[
                "sections/generated/mass_depth_rigidity_rows.tex",
            ],
        ),
        Step(
            name="CKM mixing rigidity",
            script="exp_ckm_mixing_depth_rigidity.py",
            expected_outputs=[
                "sections/generated/ckm_mixing_rigidity_rows.tex",
                "sections/generated/ckm_mixing_rows.tex",
            ],
        ),
        Step(
            name="CKM matrix closure",
            script="exp_ckm_matrix_closure.py",
            expected_outputs=[
                "sections/generated/ckm_angles_rows.tex",
                "sections/generated/ckm_matrix_rows.tex",
                "sections/generated/ckm_unitarity_rows.tex",
            ],
        ),
        Step(
            name="PMNS mixing rigidity",
            script="exp_pmns_mixing_depth_rigidity.py",
            expected_outputs=[
                "sections/generated/pmns_mixing_rigidity_rows.tex",
                "sections/generated/pmns_mixing_rows.tex",
            ],
        ),
        Step(
            name="PMNS matrix closure",
            script="exp_pmns_matrix_closure.py",
            expected_outputs=[
                "sections/generated/pmns_angles_rows.tex",
                "sections/generated/pmns_matrix_rows.tex",
                "sections/generated/pmns_unitarity_rows.tex",
            ],
        ),
        Step(
            name="Neutrino mass interface",
            script="exp_neutrino_mass_interface.py",
            expected_outputs=[
                "sections/generated/neutrino_mass_interface_rows.tex",
            ],
        ),
        Step(
            name="Audit closure metrics",
            script="exp_audit_closure_metrics.py",
            expected_outputs=[
                "sections/generated/audit_closure_metrics_rows.tex",
                "sections/generated/audit_closure_quantiles_rows.tex",
            ],
        ),
        Step(
            name="Audit uncertainty robustness",
            script="exp_audit_uncertainty_robustness.py",
            expected_outputs=[
                "sections/generated/audit_uncertainty_robustness_rows.tex",
            ],
        ),
        Step(
            name="Audit counterfactual baselines",
            script="exp_audit_counterfactual_baselines.py",
            expected_outputs=[
                "sections/generated/audit_counterfactual_rows.tex",
            ],
        ),
        Step(
            name="Audit summary",
            script="exp_audit_summary.py",
            expected_outputs=[
                "sections/generated/audit_summary_rows.tex",
            ],
        ),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run all reproducible generators for this paper.")
    parser.add_argument(
        "--stop-after",
        default="",
        help="Optional step name prefix to stop after (for debugging).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)

    steps = build_steps()
    all_expected: List[str] = []

    for step in steps:
        script_path = scripts_dir() / step.script
        if not script_path.is_file():
            raise FileNotFoundError(f"Missing script: {script_path}")
        print(f"[run_all] {step.name} -> {step.script}")
        _run_script(script_path)
        _check_outputs(step.expected_outputs)
        all_expected.extend(list(step.expected_outputs))
        if args.stop_after and step.name.lower().startswith(args.stop_after.lower()):
            break

    # Final cross-check: ensure the generated directory exists and contains files.
    if not gen.is_dir():
        raise RuntimeError("Missing generated directory.")

    # Minimal sanity: ensure the audit summary exists if we ran it.
    if (paper_root() / "sections/generated/audit_summary_rows.tex") in [paper_root() / p for p in all_expected]:
        _check_outputs(["sections/generated/audit_summary_rows.tex"])

    print("[run_all] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


