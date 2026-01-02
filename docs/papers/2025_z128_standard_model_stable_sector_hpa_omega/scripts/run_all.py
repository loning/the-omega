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
from subprocess import CalledProcessError
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from common_paths import generated_dir, paper_root, scripts_dir
from common_progress import heartbeat_wait
from common_tex import nonempty_file


@dataclass(frozen=True)
class Step:
    name: str
    script: str
    expected_outputs: Sequence[str]


def _run_script(script_path: Path, step_name: str) -> None:
    cmd = [sys.executable, str(script_path)]
    proc = subprocess.Popen(cmd, cwd=str(paper_root()))
    rc = heartbeat_wait(proc, label=step_name, interval_s=60.0, poll_s=1.0)
    if rc != 0:
        raise CalledProcessError(rc, cmd)


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
            name="Xm weight sweep",
            script="exp_xm_weight_sweep.py",
            expected_outputs=[
                "sections/generated/xm_weight_sweep_rows.tex",
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
            name="Ghost sector violation diagnostics",
            script="exp_ghost_sector_violation_stats.py",
            expected_outputs=[
                "sections/generated/ghost_sector_violation_rows.tex",
            ],
        ),
        Step(
            name="Ghost sector repair-cost diagnostics",
            script="exp_ghost_sector_repair_cost_stats.py",
            expected_outputs=[
                "sections/generated/ghost_sector_repair_cost_rows.tex",
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
            name="Resolution calibration sweep",
            script="exp_resolution_calibration_sweep.py",
            expected_outputs=[
                "sections/generated/resolution_calibration_sweep_rows.tex",
            ],
        ),
        Step(
            name="Resolution calibration multianchor sweep",
            script="exp_resolution_calibration_multianchor.py",
            expected_outputs=[
                "sections/generated/resolution_calibration_multianchor_rows.tex",
            ],
        ),
        Step(
            name="Edge mismatch decomposition (finite connection)",
            script="exp_edge_mismatch_decomposition.py",
            expected_outputs=[
                "sections/generated/edge_mismatch_deg_pair_rows.tex",
                "sections/generated/edge_mismatch_cost_quantiles_rows.tex",
            ],
        ),
        Step(
            name="Plaquette holonomy (finite connection)",
            script="exp_holonomy_loops.py",
            expected_outputs=[
                "sections/generated/holonomy_cycle_type_rows.tex",
            ],
        ),
        Step(
            name="Holonomy SU(3) representation (finite diagnostic)",
            script="exp_holonomy_su3_representation.py",
            expected_outputs=[
                "sections/generated/holonomy_su3_rotation_rows.tex",
            ],
        ),
        Step(
            name="Holonomy phase lift (CP-odd invariant, finite diagnostic)",
            script="exp_holonomy_phase_lift_cp_invariant.py",
            expected_outputs=[
                "sections/generated/holonomy_phase_lift_j_rows.tex",
            ],
        ),
        Step(
            name="Holonomy phase denominator sweep (finite diagnostic)",
            script="exp_holonomy_phase_lift_family_sweep.py",
            expected_outputs=[
                "sections/generated/holonomy_phase_lift_family_rows.tex",
            ],
        ),
        Step(
            name="Holonomy phase-lift angles (finite diagnostic)",
            script="exp_holonomy_phase_lift_angles.py",
            expected_outputs=[
                "sections/generated/holonomy_phase_lift_angles_rows.tex",
            ],
        ),
        Step(
            name="Holonomy balanced-chain sweep (finite diagnostic)",
            script="exp_holonomy_balanced_chain_sweep.py",
            expected_outputs=[
                "sections/generated/holonomy_balanced_chain_rows.tex",
            ],
        ),
        Step(
            name="Holonomy balanced-chain permutation fits (PMNS/CKM, finite diagnostic)",
            script="exp_holonomy_balanced_chain_perm_fit.py",
            expected_outputs=[
                "sections/generated/holonomy_balanced_chain_fit_pmns_rows.tex",
                "sections/generated/holonomy_balanced_chain_fit_ckm_rows.tex",
            ],
        ),
        Step(
            name="Holonomy loop-scale sweep (finite diagnostic)",
            script="exp_holonomy_loop_scale_sweep.py",
            expected_outputs=[
                "sections/generated/holonomy_loop_scale_cycle_rows.tex",
                "sections/generated/holonomy_loop_scale_fit_pmns_rows.tex",
                "sections/generated/holonomy_loop_scale_fit_ckm_rows.tex",
            ],
        ),
        Step(
            name="Holonomy loop-scale SU(3) angles (finite diagnostic)",
            script="exp_holonomy_loop_scale_su3_angle_sweep.py",
            expected_outputs=[
                "sections/generated/holonomy_loop_scale_su3_angle_rows.tex",
            ],
        ),
        Step(
            name="Holonomy Wilson loop sweep (finite diagnostic)",
            script="exp_holonomy_wilson_loop_sweep.py",
            expected_outputs=[
                "sections/generated/holonomy_wilson_loop_rows.tex",
            ],
        ),
        Step(
            name="Holonomy single-loop best fits (finite diagnostic)",
            script="exp_holonomy_single_loop_bestfit.py",
            expected_outputs=[
                "sections/generated/holonomy_single_loop_bestfit_rows.tex",
            ],
        ),
        Step(
            name="Holonomy two-loop chain best fits (finite diagnostic)",
            script="exp_holonomy_two_loop_chain_bestfit.py",
            expected_outputs=[
                "sections/generated/holonomy_two_loop_chain_bestfit_rows.tex",
            ],
        ),
        Step(
            name="Holonomy two-loop chain best fits (mixed cycles, finite diagnostic)",
            script="exp_holonomy_two_loop_chain_mixed_cycles_bestfit.py",
            expected_outputs=[
                "sections/generated/holonomy_two_loop_chain_mixed_cycles_bestfit_rows.tex",
            ],
        ),
        Step(
            name="Holonomy phase-lift angles denom sweep (finite diagnostic)",
            script="exp_holonomy_phase_lift_angles_denom_sweep.py",
            expected_outputs=[
                "sections/generated/holonomy_phase_lift_angles_denom_sweep_rows.tex",
            ],
        ),
        Step(
            name="Holonomy PMNS denom fit (finite diagnostic)",
            script="exp_holonomy_phase_lift_pmns_denom_fit.py",
            expected_outputs=[
                "sections/generated/holonomy_phase_lift_pmns_denom_fit_rows.tex",
            ],
        ),
        Step(
            name="Holonomy permutation fits (PMNS/CKM, finite diagnostic)",
            script="exp_holonomy_phase_lift_perm_fit.py",
            expected_outputs=[
                "sections/generated/holonomy_perm_fit_pmns_rows.tex",
                "sections/generated/holonomy_perm_fit_ckm_rows.tex",
            ],
        ),
        Step(
            name="Holonomy phase-map family sweep (finite diagnostic)",
            script="exp_holonomy_phase_lift_map_family_sweep.py",
            expected_outputs=[
                "sections/generated/holonomy_map_family_pmns_rows.tex",
                "sections/generated/holonomy_map_family_ckm_rows.tex",
            ],
        ),
        Step(
            name="Holonomy soft-transport beta sweep (robustness diagnostic)",
            script="exp_holonomy_soft_transport_beta_sweep.py",
            expected_outputs=[
                "sections/generated/holonomy_soft_transport_pmns_rows.tex",
                "sections/generated/holonomy_soft_transport_ckm_rows.tex",
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
            name="Label lift refinement indices",
            script="exp_labeling_lift_refinement_indices.py",
            expected_outputs=[
                "sections/generated/label_lift_suffix_catalog_rows.tex",
                "sections/generated/label_lift_boundary_rho_rows.tex",
            ],
        ),
        Step(
            name="Audit label-lift refinement index",
            script="exp_audit_label_lift_refinement.py",
            expected_outputs=[
                "sections/generated/audit_label_lift_refinement_rows.tex",
            ],
        ),
        Step(
            name="Label lift high-m invariants",
            script="exp_labeling_lift_highm_invariants.py",
            expected_outputs=[
                "sections/generated/label_lift_highm_invariants_rows.tex",
            ],
        ),
        Step(
            name="Inverse hypercharge fit (inverse diagnostic)",
            script="exp_inverse_hypercharge_fit.py",
            expected_outputs=[
                "sections/generated/inverse_hypercharge_fit_rows.tex",
            ],
        ),
        Step(
            name="Inverse hypercharge sign fit (inverse diagnostic)",
            script="exp_inverse_hypercharge_sign_fit.py",
            expected_outputs=[
                "sections/generated/inverse_hypercharge_sign_fit_rows.tex",
            ],
        ),
        Step(
            name="Inverse hypercharge full fit (inverse diagnostic)",
            script="exp_inverse_hypercharge_full_fit.py",
            expected_outputs=[
                "sections/generated/inverse_hypercharge_full_fit_rows.tex",
            ],
        ),
        Step(
            name="Inverse rep-dimension fit (inverse diagnostic)",
            script="exp_inverse_rep_dim_fit.py",
            expected_outputs=[
                "sections/generated/inverse_rep_dim_fit_rows.tex",
            ],
        ),
        Step(
            name="Inverse generation fit (inverse diagnostic)",
            script="exp_inverse_generation_fit.py",
            expected_outputs=[
                "sections/generated/inverse_generation_fit_rows.tex",
            ],
        ),
        Step(
            name="Inverse (high-m) hypercharge-squared fit (inverse diagnostic)",
            script="exp_inverse_highm_hypercharge_fit.py",
            expected_outputs=[
                "sections/generated/inverse_highm_hypercharge_fit_rows.tex",
            ],
        ),
        Step(
            name="Inverse (high-m) hypercharge sign fit (inverse diagnostic)",
            script="exp_inverse_highm_hypercharge_sign_fit.py",
            expected_outputs=[
                "sections/generated/inverse_highm_hypercharge_sign_fit_rows.tex",
            ],
        ),
        Step(
            name="Inverse (high-m) full hypercharge numerator fit (inverse diagnostic)",
            script="exp_inverse_highm_hypercharge_full_fit.py",
            expected_outputs=[
                "sections/generated/inverse_highm_hypercharge_full_fit_rows.tex",
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
            name="Audit resolution calibration robustness",
            script="exp_audit_resolution_calibration_robustness.py",
            expected_outputs=[
                "sections/generated/audit_resolution_calibration_robustness_rows.tex",
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
        _run_script(script_path, step_name=step.name)
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


