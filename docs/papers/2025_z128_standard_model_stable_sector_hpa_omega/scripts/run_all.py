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
import ast
import hashlib
import subprocess
import sys
from subprocess import CalledProcessError
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from common_cache import cache_disabled, cache_path, load_pickle, save_pickle_atomic
from common_paths import generated_dir, paper_root, scripts_dir
from common_progress import heartbeat_wait
from common_tex import nonempty_file


@dataclass(frozen=True)
class Step:
    name: str
    script: str
    expected_outputs: Sequence[str]


RUN_ALL_CACHE_VERSION = 1


def _run_all_cache_file() -> Path:
    return cache_path("run_all_steps.pkl")


def _load_run_all_cache() -> dict[str, str]:
    """
    Mapping: step.script -> dependency fingerprint (sha256 hex).
    """
    p = _run_all_cache_file()
    if not p.is_file():
        return {}
    try:
        obj = load_pickle(p)
        if not isinstance(obj, dict):
            return {}
        if int(obj.get("version", -1)) != RUN_ALL_CACHE_VERSION:
            return {}
        steps = obj.get("steps", {})
        if not isinstance(steps, dict):
            return {}
        out: dict[str, str] = {}
        for k, v in steps.items():
            if isinstance(k, str) and isinstance(v, str):
                out[k] = v
        return out
    except Exception:
        return {}


def _save_run_all_cache(cache: dict[str, str]) -> None:
    if cache_disabled():
        return
    try:
        save_pickle_atomic(
            _run_all_cache_file(),
            {"version": RUN_ALL_CACHE_VERSION, "steps": dict(cache)},
        )
    except Exception:
        # Best-effort; never fail the pipeline because of caching.
        pass


def _local_module_map() -> dict[str, Path]:
    # Editing this orchestrator should not force a full recompute of fragments.
    return {p.stem: p for p in scripts_dir().glob("*.py") if p.name != "run_all.py"}


def _direct_local_imports(py_path: Path, module_map: dict[str, Path]) -> set[Path]:
    """
    Return local (same-directory) Python dependencies imported by this file.
    If parsing fails for any reason, fall back to a conservative dependency set.
    """
    try:
        src = py_path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(py_path))
    except Exception:
        # Conservative fallback: assume it depends on all local modules *except itself*.
        # This avoids self-dependency cycles in the dependency-closure recursion.
        return {p for p in module_map.values() if p != py_path}

    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    mods.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                mods.add(node.module.split(".")[0])
    return {module_map[m] for m in mods if m in module_map}


def _script_deps_closure(
    root: Path, module_map: dict[str, Path], memo: dict[Path, set[Path]]
) -> set[Path]:
    """
    Compute the transitive closure of local Python dependencies for a script.
    """
    if root in memo:
        return memo[root]
    # Provisional memo entry to break cycles (including self-dependency via fallback).
    memo[root] = {root}
    deps: set[Path] = {root}
    for dep in _direct_local_imports(root, module_map):
        if dep == root:
            continue
        deps |= _script_deps_closure(dep, module_map, memo)
    memo[root] = deps
    return deps


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
        msg = "Missing/empty generated outputs:\n" + "\n".join(
            f"  - {m}" for m in missing
        )
        raise RuntimeError(msg)


def _have_outputs(rel_paths: Iterable[str]) -> bool:
    for rel in rel_paths:
        p = paper_root() / rel
        if not nonempty_file(p):
            return False
    return True


def _deps_fingerprint(deps: Iterable[Path]) -> str:
    """
    Stable fingerprint for a set of local dependency files (content-based).
    """
    h = hashlib.sha256()
    root = scripts_dir()
    for p in sorted(set(deps), key=lambda x: str(x)):
        try:
            rel = str(p.resolve().relative_to(root.resolve()))
        except Exception:
            rel = str(p.resolve())
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def _max_mtime(paths: Iterable[Path]) -> float:
    mt = 0.0
    for p in paths:
        try:
            mt = max(mt, p.stat().st_mtime)
        except FileNotFoundError:
            continue
    return mt


def _scripts_deps_mtime() -> float:
    # Conservative invalidation: any change to any generator/helper in this directory
    # makes all steps "not up-to-date".
    #
    # IMPORTANT: exclude this orchestrator itself; editing `run_all.py` should not
    # force a full recompute of generated fragments.
    py = [p for p in scripts_dir().glob("*.py") if p.name != "run_all.py"]
    return _max_mtime(py)


def _outputs_up_to_date(rel_paths: Iterable[str], deps_mtime: float) -> bool:
    for rel in rel_paths:
        p = paper_root() / rel
        if not nonempty_file(p):
            return False
        if p.stat().st_mtime < deps_mtime:
            return False
    return True


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
            name="Fold-family sensitivity (counterfactual audit)",
            script="exp_fold_family_sensitivity.py",
            expected_outputs=[
                "sections/generated/fold_family_sensitivity_rows.tex",
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
            name="Kernel summary (m-sweep)",
            script="exp_fractal_kernel_summary.py",
            expected_outputs=[
                "sections/generated/fractal_kernel_sweep_rows.tex",
            ],
        ),
        Step(
            name="Kernel mu/r bridge (demo)",
            script="exp_kernel_mu_r_bridge_demo.py",
            expected_outputs=[
                "sections/generated/kernel_mu_r_bridge_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG flow (balanced chain)",
            script="exp_kernel_rg_flow_balanced_chain.py",
            expected_outputs=[
                "sections/generated/kernel_rg_flow_balanced_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG operator sanity (16x16 matrix audit)",
            script="exp_kernel_rg_operator_matrix_audit.py",
            expected_outputs=[
                "sections/generated/kernel_rg_operator_sanity_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG operator predict-vs-recompute (backreaction audit)",
            script="exp_kernel_rg_operator_predict_vs_recompute.py",
            expected_outputs=[
                "sections/generated/kernel_rg_operator_backreaction_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG operator error-budget decomposition (certificate)",
            script="exp_kernel_rg_operator_error_bound_certificate.py",
            expected_outputs=[
                "sections/generated/kernel_rg_operator_error_budget_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG operator spectral-gap diagnostic",
            script="exp_kernel_rg_operator_spectral_gap.py",
            expected_outputs=[
                "sections/generated/kernel_rg_operator_spectral_gap_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG operator 2-point library (covariance audit)",
            script="exp_kernel_rg_operator_covariance_audit.py",
            expected_outputs=[
                "sections/generated/kernel_rg_operator_covariance_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG operator D4 layout sensitivity (conjugacy audit)",
            script="exp_kernel_rg_operator_layout_sensitivity.py",
            expected_outputs=[
                "sections/generated/kernel_rg_operator_layout_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG resolvent-trace audit (one-point / two-point)",
            script="exp_kernel_rg_resolvent_trace_audit.py",
            expected_outputs=[
                "sections/generated/kernel_rg_resolvent_trace_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG weighted operator pole-barrier summary",
            script="exp_kernel_rg_weighted_operator_pole_barrier.py",
            expected_outputs=[
                "sections/generated/kernel_rg_weighted_pole_barrier_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG weighted operator Doob normalization (Markov audit)",
            script="exp_kernel_rg_weighted_doob_normalization.py",
            expected_outputs=[
                "sections/generated/kernel_rg_weighted_doob_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG weighted operator pressure proxy (log spectral radius)",
            script="exp_kernel_rg_weighted_pressure_summary.py",
            expected_outputs=[
                "sections/generated/kernel_rg_weighted_pressure_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG covariant transport lift (S4 anchor certificate)",
            script="exp_kernel_rg_covariant_transport_anchor.py",
            expected_outputs=[
                "sections/generated/kernel_rg_covariant_transport_anchor_rows.tex",
                "sections/generated/kernel_rg_covariant_transport_reduction_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG covariant operator spectral gap (anchor)",
            script="exp_kernel_rg_operator_covariant_spectral_gap.py",
            expected_outputs=[
                "sections/generated/kernel_rg_operator_covariant_spectral_gap_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG covariant operator reduction / decomposition (anchor)",
            script="exp_kernel_rg_operator_covariant_reduction_audit.py",
            expected_outputs=[
                "sections/generated/kernel_rg_operator_covariant_reduction_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG covariant operator gauge covariance (anchor)",
            script="exp_kernel_rg_operator_covariant_gauge_audit.py",
            expected_outputs=[
                "sections/generated/kernel_rg_operator_covariant_gauge_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG covariant internal-mode resolvent trace (anchor)",
            script="exp_kernel_rg_operator_covariant_internal_resolvent_trace_audit.py",
            expected_outputs=[
                "sections/generated/kernel_rg_operator_covariant_internal_resolvent_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG covariant internal-mode gauge covariance (anchor)",
            script="exp_kernel_rg_operator_covariant_internal_gauge_audit.py",
            expected_outputs=[
                "sections/generated/kernel_rg_operator_covariant_internal_gauge_rows.tex",
            ],
        ),
        Step(
            name="Kernel RG covariant internal closure triplet (anchor)",
            script="exp_kernel_rg_operator_covariant_internal_closure_triplet_audit.py",
            expected_outputs=[
                "sections/generated/kernel_rg_operator_covariant_internal_closure_triplet_rows.tex",
            ],
        ),
        Step(
            name="Ext boundary operator check (uplift refinement audit)",
            script="exp_ext_boundary_operator_check.py",
            expected_outputs=[
                "sections/generated/ext_boundary_operator_check_rows.tex",
            ],
        ),
        Step(
            name="Folding entropy decomposition (numeric certificate)",
            script="exp_folding_entropy_decomposition.py",
            expected_outputs=[
                "sections/generated/folding_entropy_decomposition_rows.tex",
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
            name="Addressing-basis selection audit (Hilbert vs row-major)",
            script="exp_addressing_selection.py",
            expected_outputs=[
                "sections/generated/addressing_selection_rows.tex",
            ],
        ),
        Step(
            name="Gauge-factor complexity sensitivity (audit)",
            script="exp_gauge_complexity_sensitivity.py",
            expected_outputs=[
                "sections/generated/gauge_complexity_sensitivity_rows.tex",
            ],
        ),
        Step(
            name="Gauge3 holonomy candidate closure (audit)",
            script="exp_gauge3_holonomy_candidate_closure.py",
            expected_outputs=[
                "sections/generated/gauge3_holonomy_candidate_closure_rows.tex",
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
            name="Coarse-grained scalar parity check",
            script="exp_scalar_coarse_grain.py",
            expected_outputs=[
                "sections/generated/scalar_coarse_grain_rows.tex",
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
            name="Cosmology energy-budget fit",
            script="exp_cosmology_energy_budget_fit.py",
            expected_outputs=[
                "sections/generated/cosmology_energy_budget_fit_equation.tex",
                "sections/generated/cosmology_energy_budget_fit_summary.tex",
                "sections/generated/cosmology_energy_budget_fit_stability.tex",
                "figures/cosmology_energy_budget_fit.png",
            ],
        ),
        Step(
            name="Lambda pressure closure (e-channel; audit)",
            script="exp_lambda_pressure_closure.py",
            expected_outputs=[
                "sections/generated/lambda_pressure_closure_equations.tex",
                "sections/generated/lambda_pressure_closure_summary.tex",
            ],
        ),
        Step(
            name="Weighted pressure sweep toy (e-channel; audit)",
            script="exp_weighted_pressure_sweep.py",
            expected_outputs=[
                "sections/generated/weighted_pressure_sweep_rows.tex",
            ],
        ),
        Step(
            name="Pole-barrier mode toy (audit)",
            script="exp_pole_barrier_mode_toy.py",
            expected_outputs=[
                "sections/generated/pole_barrier_mode_toy_rows.tex",
            ],
        ),
        Step(
            name="Hilbert-knot triptych (Figure 1)",
            script="fig_hilbert_knot_triptych.py",
            expected_outputs=[
                "figures/hilbert_knot_triptych.png",
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
            name="Holonomy transport-rule sensitivity (audit)",
            script="exp_holonomy_transport_rule_sensitivity.py",
            expected_outputs=[
                "sections/generated/holonomy_transport_rule_sensitivity_rows.tex",
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
                "sections/generated/holonomy_balanced_chain_wilson_rows.tex",
            ],
        ),
        Step(
            name="Curvature-bridge sanity checks (weak-field Laplacian + Wilson scaling)",
            script="exp_curvature_bridge_audit.py",
            expected_outputs=[
                "sections/generated/curvature_bridge_weak_field_rows.tex",
                "sections/generated/curvature_bridge_weak_field_summary.tex",
                "sections/generated/curvature_bridge_wilson_rows.tex",
                "sections/generated/curvature_bridge_wilson_summary.tex",
            ],
        ),
        Step(
            name="Curvature bridge end-to-end (protocolized input -> chi -> curvature proxy)",
            script="exp_curvature_bridge_end_to_end.py",
            expected_outputs=[
                "sections/generated/curvature_e2e_rows.tex",
                "sections/generated/curvature_e2e_summary.tex",
                "sections/generated/curvature_e2e_gamma_rows.tex",
                "sections/generated/curvature_e2e_gamma_summary.tex",
                "sections/generated/curvature_e2e_gamma_stability_rows.tex",
                "sections/generated/curvature_e2e_gamma_stability_summary.tex",
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
            name="QCD confinement proxy (Wilson-loop area/perimeter; audit)",
            script="exp_qcd_confinement_proxy_audit.py",
            expected_outputs=[
                "sections/generated/qcd_confinement_proxy_rows.tex",
                "sections/generated/qcd_confinement_proxy_summary.tex",
                "sections/generated/qcd_confinement_proxy_robustness_rows.tex",
                "sections/generated/qcd_confinement_proxy_sigma_rows.tex",
                "sections/generated/qcd_confinement_proxy_sigma_summary.tex",
            ],
        ),
        Step(
            name="QCD confinement proxy Padé pole-barrier audit (analytic continuation; audit)",
            script="exp_qcd_confinement_pade_pole_barrier_audit.py",
            expected_outputs=[
                "sections/generated/qcd_confinement_pade_pole_rows.tex",
                "sections/generated/qcd_confinement_pade_pole_summary.tex",
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
            name="Leakage kernel demo (audit illustration)",
            script="exp_leakage_kernel_demo.py",
            expected_outputs=[
                "sections/generated/leakage_kernel_demo_rows.tex",
            ],
        ),
        Step(
            name="Leakage kernel m=6 trap/exit audit table",
            script="exp_leakage_kernel_m6_trap_exit.py",
            expected_outputs=[
                "sections/generated/leakage_kernel_m6_trap_exit_rows.tex",
                "sections/generated/leakage_kernel_m6_trap_exit_summary.tex",
            ],
        ),
        Step(
            name="Protocol horizon illustration (tick-trap)",
            script="exp_protocol_horizon_tick_trap_examples.py",
            expected_outputs=[
                "sections/generated/protocol_horizon_examples_rows.tex",
                "sections/generated/protocol_horizon_examples_summary.tex",
            ],
        ),
        Step(
            name="Wormhole-like pointer jump audit (protocol-only)",
            script="exp_wormhole_pointer_jump_audit.py",
            expected_outputs=[
                "sections/generated/wormhole_pointer_jump_rows.tex",
                "sections/generated/wormhole_pointer_jump_summary.tex",
            ],
        ),
        Step(
            name="Budget-triggered chi-horizon occupancy (capacity-only table)",
            script="exp_chi_horizon_budget_occupancy.py",
            expected_outputs=[
                "sections/generated/chi_horizon_budget_occupancy_rows.tex",
                "sections/generated/chi_horizon_budget_occupancy_summary.tex",
            ],
        ),
        Step(
            name="Resolution uplift CAP choice under constraints (capacity-driven staging)",
            script="exp_resolution_uplift_cap_choice.py",
            expected_outputs=[
                "sections/generated/resolution_uplift_cap_choice_rows.tex",
                "sections/generated/resolution_uplift_cap_choice_summary.tex",
            ],
        ),
        Step(
            name="K4 delay dictionary audit (gravitational time-delay channels)",
            script="exp_k4_delay_dictionary_audit.py",
            expected_outputs=[
                "sections/generated/k4_delay_audit_rows.tex",
                "sections/generated/k4_delay_audit_summary.tex",
            ],
        ),
        Step(
            name="K4 scattering phase -> delay audit (benchmark interface)",
            script="exp_k4_scattering_phase_delay_audit.py",
            expected_outputs=[
                "sections/generated/k4_scattering_phase_delay_rows.tex",
                "sections/generated/k4_scattering_phase_delay_window_rows.tex",
                "sections/generated/k4_scattering_phase_delay_coord_rows.tex",
                "sections/generated/k4_scattering_phase_delay_summary.tex",
            ],
        ),
        Step(
            name="K4 WS-linewidth calibration audit (interface)",
            script="exp_k4_ws_linewidth_audit.py",
            expected_outputs=[
                "sections/generated/k4_ws_linewidth_rows.tex",
                "sections/generated/k4_ws_linewidth_coord_rows.tex",
                "sections/generated/k4_ws_linewidth_summary.tex",
            ],
        ),
        Step(
            name="K4 leakage audit vs PDG mini-set",
            script="exp_k4_pdg_leakage_audit.py",
            expected_outputs=[
                "sections/generated/k4_pdg_leakage_rows.tex",
                "sections/generated/k4_pdg_leakage_summary.tex",
            ],
        ),
        Step(
            name="K4 alpha link audit (m=6 exit weights)",
            script="exp_k4_alpha_link_audit.py",
            expected_outputs=[
                "sections/generated/k4_alpha_link_rows.tex",
                "sections/generated/k4_alpha_link_summary.tex",
            ],
        ),
        Step(
            name="Low-leakage phase signatures (audit illustration)",
            script="exp_low_leakage_phase_signatures.py",
            expected_outputs=[
                "sections/generated/low_leakage_phase_rows.tex",
                "sections/generated/low_leakage_phase_summary.tex",
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
            name="Mass flow under uplift (CAP vs free-energy)",
            script="exp_mass_flow_uplift.py",
            expected_outputs=[
                "sections/generated/mass_flow_uplift_rows.tex",
                "sections/generated/mass_flow_uplift_summary.tex",
            ],
        ),
        Step(
            name="BH/Planck capacity calibration (boundary vs protocol capacity)",
            script="exp_bh_planck_capacity_calibration.py",
            expected_outputs=[
                "sections/generated/bh_planck_capacity_rows.tex",
                "sections/generated/bh_planck_capacity_summary.tex",
                "sections/generated/bh_capacity_calibrated_uplift_path_rows.tex",
                "sections/generated/bh_planck_capacity_known_rows.tex",
                "sections/generated/bh_planck_capacity_known_summary.tex",
            ],
        ),
        Step(
            name="Neutrino external audit ledger (Match/Audit only)",
            script="exp_neutrino_external_audit.py",
            expected_outputs=[
                "sections/generated/neutrino_external_audit_rows.tex",
                "sections/generated/neutrino_external_audit_summary.tex",
                "sections/generated/neutrino_external_audit_internal_rows.tex",
            ],
        ),
        Step(
            name="Neutrino mass mechanisms (candidate registry; audit)",
            script="exp_neutrino_mass_mechanisms.py",
            expected_outputs=[
                "sections/generated/neutrino_mechanism_candidates_rows.tex",
                "sections/generated/neutrino_mechanism_scoreboard_rows.tex",
                "sections/generated/neutrino_mechanism_global_rows.tex",
                "sections/generated/neutrino_mechanism_global_summary.tex",
                "sections/generated/neutrino_majorana_phase_closure_rows.tex",
                "sections/generated/neutrino_majorana_phase_closure_summary.tex",
                "sections/generated/neutrino_splitting_depth_closure_rows.tex",
                "sections/generated/neutrino_splitting_depth_closure_summary.tex",
                "sections/generated/neutrino_weinberg_scale_rows.tex",
                "sections/generated/neutrino_weinberg_scale_summary.tex",
                "sections/generated/neutrino_seesaw_scale_rows.tex",
                "sections/generated/neutrino_seesaw_scale_summary.tex",
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
            name="Inverse diagnostic summary (main-text)",
            script="exp_inverse_diag_summary.py",
            expected_outputs=[
                "sections/generated/inverse_diag_summary_rows.tex",
            ],
        ),
        Step(
            name="Labeling order-key sensitivity (audit)",
            script="exp_labeling_order_sensitivity.py",
            expected_outputs=[
                "sections/generated/labeling_order_sensitivity_rows.tex",
            ],
        ),
        Step(
            name="Mass spectrum",
            script="exp_mass_spectrum.py",
            expected_outputs=[
                "sections/generated/mass_spectrum_anchor_rows.tex",
                "sections/generated/mass_spectrum_quark_rows.tex",
                "sections/generated/mass_spectrum_neutrino_rows.tex",
                "sections/generated/mass_spectrum_anchor_summary.tex",
            ],
        ),
        Step(
            name="Higgs--Z depth offset rigidity (scalar-sector diagnostic)",
            script="exp_higgs_z_offset_rigidity.py",
            expected_outputs=[
                "sections/generated/higgs_z_offset_sweep_rows.tex",
            ],
        ),
        Step(
            name="Mass matching layer",
            script="exp_mass_matching_layer.py",
            expected_outputs=[
                "sections/generated/mass_matching_layer_rows.tex",
                "sections/generated/mass_matching_layer_summary_rows.tex",
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
            name="Mass depth leave-one-out (robustness)",
            script="exp_mass_depth_leave_one_out.py",
            expected_outputs=[
                "sections/generated/mass_depth_leave_one_out_rows.tex",
                "sections/generated/mass_depth_leave_one_out_summary_rows.tex",
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
                "sections/generated/pmns_delta_sweep_rows.tex",
                "sections/generated/pmns_angles_rows.tex",
                "sections/generated/pmns_matrix_rows.tex",
                "sections/generated/pmns_unitarity_rows.tex",
            ],
        ),
        Step(
            name="PMNS NO/IO stability diagnostic",
            script="exp_pmns_no_io_stability.py",
            expected_outputs=[
                "sections/generated/pmns_no_io_stability_rows.tex",
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
            name="Audit pi-polynomial null baseline",
            script="exp_audit_pi_polynomial_null.py",
            expected_outputs=[
                "sections/generated/audit_pi_poly_null_rows.tex",
            ],
        ),
        Step(
            name="Audit global model selection (MDL, cross-family)",
            script="exp_audit_global_model_selection_mdl.py",
            expected_outputs=[
                "sections/generated/audit_global_mdl_family_rows.tex",
                "sections/generated/audit_global_mdl_summary.tex",
            ],
        ),
        Step(
            name="Rigidity alpha coefficient simplex",
            script="exp_alpha_coeff_rigidity.py",
            expected_outputs=[
                "sections/generated/alpha_coeff_rigidity_rows.tex",
            ],
        ),
        Step(
            name="Aggregation and multiplicity baselines (audit)",
            script="exp_aggregation_baselines.py",
            expected_outputs=[
                "sections/generated/alpha_aggregation_baselines_rows.tex",
                "sections/generated/j_multiplicity_baselines_rows.tex",
            ],
        ),
        Step(
            name="Rigidity electroweak Z-scale",
            script="exp_ew_rigidity.py",
            expected_outputs=[
                "sections/generated/ew_alpha_pi2_rigidity_rows.tex",
                "sections/generated/ew_sin2_rational_rigidity_rows.tex",
            ],
        ),
        Step(
            name="Coupling unification audit in r (bounded family; match/audit)",
            script="exp_coupling_unification_audit_in_r.py",
            expected_outputs=[
                "sections/generated/coupling_unification_audit_rows.tex",
                "sections/generated/coupling_unification_audit_summary.tex",
                "sections/generated/coupling_unification_threshold_registry_rows.tex",
                "sections/generated/coupling_unification_threshold_audit_rows.tex",
                "sections/generated/coupling_unification_threshold_audit_summary.tex",
            ],
        ),
        Step(
            name="Force->phase->delay toy audit (numerical stability; audit)",
            script="exp_force_phase_delay_audit_toy.py",
            expected_outputs=[
                "sections/generated/force_phase_delay_audit_toy_rows.tex",
                "sections/generated/force_phase_delay_audit_toy_summary.tex",
            ],
        ),
        Step(
            name="Coupling unification audit (two-loop + threshold uncertainty; audit)",
            script="exp_coupling_unification_audit_2loop_thresholds.py",
            expected_outputs=[
                "sections/generated/coupling_unification_2loop_threshold_audit_rows.tex",
                "sections/generated/coupling_unification_2loop_threshold_audit_summary.tex",
            ],
        ),
        Step(
            name="Coupling unification audit (two-loop missing-sector perturbations; audit)",
            script="exp_coupling_unification_2loop_yukawa_scalar_perturbation_audit.py",
            expected_outputs=[
                "sections/generated/coupling_unification_2loop_yukawa_scalar_audit_rows.tex",
                "sections/generated/coupling_unification_2loop_yukawa_scalar_audit_summary.tex",
            ],
        ),
        Step(
            name="Coupling unification threshold correlation modes (audit)",
            script="exp_coupling_unification_threshold_correlation_modes.py",
            expected_outputs=[
                "sections/generated/coupling_unification_threshold_corr_modes_rows.tex",
                "sections/generated/coupling_unification_threshold_corr_modes_summary.tex",
            ],
        ),
        Step(
            name="Scattering inverse consistency audit (phase->delay->phase; audit)",
            script="exp_scattering_inverse_consistency_audit.py",
            expected_outputs=[
                "sections/generated/scattering_inverse_consistency_rows.tex",
                "sections/generated/scattering_inverse_consistency_summary.tex",
            ],
        ),
        Step(
            name="Scattering inverse consistency coord-gate (audit)",
            script="exp_scattering_inverse_consistency_coord_audit.py",
            expected_outputs=[
                "sections/generated/scattering_inverse_coord_rows.tex",
                "sections/generated/scattering_inverse_coord_summary.tex",
            ],
        ),
        Step(
            name="Scattering delay-linewidth triangle audit (audit)",
            script="exp_scattering_delay_linewidth_triangle_audit.py",
            expected_outputs=[
                "sections/generated/scattering_delay_linewidth_triangle_rows.tex",
                "sections/generated/scattering_delay_linewidth_triangle_summary.tex",
            ],
        ),
        Step(
            name="QCD proxy<->pole-barrier consistency loop (audit)",
            script="exp_qcd_proxy_polebarrier_mutual_exclusion.py",
            expected_outputs=[
                "sections/generated/qcd_proxy_polebarrier_failure_rows.tex",
                "sections/generated/qcd_proxy_polebarrier_failure_summary.tex",
            ],
        ),
        Step(
            name="Scheme reparam invariance demo (audit)",
            script="exp_scheme_reparam_invariance_audit.py",
            expected_outputs=[
                "sections/generated/scheme_invariance_demo_rows.tex",
                "sections/generated/scheme_invariance_demo_summary.tex",
            ],
        ),
        Step(
            name="Rigidity Jarlskog pi-ansatz",
            script="exp_jarlskog_pi_rigidity.py",
            expected_outputs=[
                "sections/generated/jarlskog_pi_rigidity_rows.tex",
            ],
        ),
        Step(
            name="Quantitative summary table",
            script="exp_quant_summary.py",
            expected_outputs=[
                "sections/generated/quant_summary_rows.tex",
            ],
        ),
        Step(
            name="Sigma mismatch summary table",
            script="exp_sigma_summary.py",
            expected_outputs=[
                "sections/generated/sigma_summary_rows.tex",
            ],
        ),
        Step(
            name="Gamma cross-observation consistency (audit)",
            script="exp_gamma_cross_observation.py",
            expected_outputs=[
                "sections/generated/gamma_crossobs_proxy_rows.tex",
                "sections/generated/gamma_crossobs_proxy_diagnostics.tex",
                "sections/generated/gamma_crossobs_proxy_stability_rows.tex",
                "figures/gamma_crossobs_proxy.png",
                "sections/generated/gamma_crossobs_direct_rows.tex",
                "sections/generated/gamma_crossobs_direct_diagnostics.tex",
                "sections/generated/gamma_crossobs_direct_stability_rows.tex",
                "figures/gamma_crossobs_direct.png",
            ],
        ),
        Step(
            name="Audit summary",
            script="exp_audit_summary.py",
            expected_outputs=[
                "sections/generated/audit_summary_rows.tex",
            ],
        ),
        Step(
            name="Yukawa/beta-function closure (OP5)",
            script="exp_yukawa_beta_closure.py",
            expected_outputs=[
                "sections/generated/yukawa_eigenvalue_rows.tex",
                "sections/generated/beta_representation_rows.tex",
                "sections/generated/beta_summary.tex",
                "sections/generated/yukawa_beta_closure_summary_rows.tex",
            ],
        ),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run all reproducible generators for this paper."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recomputation (ignore cached/up-to-date outputs) and run all steps.",
    )
    parser.add_argument(
        "--skip-up-to-date",
        dest="skip_up_to_date",
        action="store_true",
        help=(
            "Skip steps whose expected outputs exist, are non-empty, and are newer than the step's "
            "local Python dependencies. Useful for iterative LaTeX work."
        ),
    )
    parser.add_argument(
        "--no-skip-up-to-date",
        dest="skip_up_to_date",
        action="store_false",
        help="Disable skipping and run all steps (unless --stop-after stops early).",
    )
    parser.add_argument(
        "--stop-after",
        default="",
        help="Optional step name prefix to stop after (for debugging).",
    )
    parser.set_defaults(skip_up_to_date=True)
    args = parser.parse_args(list(argv) if argv is not None else None)

    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)

    steps = build_steps()
    all_expected: List[str] = []
    use_skip = (
        bool(args.skip_up_to_date) and (not bool(args.force)) and (not cache_disabled())
    )
    module_map: dict[str, Path] = _local_module_map() if use_skip else {}
    deps_memo: dict[Path, set[Path]] = {}
    cache: dict[str, str] = _load_run_all_cache() if use_skip else {}
    cache_dirty = False

    for step in steps:
        script_path = scripts_dir() / step.script
        if not script_path.is_file():
            raise FileNotFoundError(f"Missing script: {script_path}")
        if use_skip:
            deps = _script_deps_closure(script_path, module_map, deps_memo)
            fp = _deps_fingerprint(deps)
            have = _have_outputs(step.expected_outputs)
            cached_fp = cache.get(step.script)
            if have and cached_fp == fp:
                print(f"[run_all] SKIP (up-to-date) {step.name}")
                _check_outputs(step.expected_outputs)
            elif have and cached_fp is None:
                # First run (or cache cleared):
                # If outputs are older than the script/dependency mtimes, they may be stale
                # relative to local edits. In that case, recompute once; otherwise adopt the
                # existing outputs as the cache baseline (useful for fresh clones with
                # committed generated fragments).
                deps_mtime = _max_mtime(deps)
                if _outputs_up_to_date(step.expected_outputs, deps_mtime):
                    print(f"[run_all] SKIP (cached) {step.name}")
                    _check_outputs(step.expected_outputs)
                else:
                    print(
                        f"[run_all] {step.name} -> {step.script} (cache missing; outputs stale)"
                    )
                    _run_script(script_path, step_name=step.name)
                    _check_outputs(step.expected_outputs)
                cache[step.script] = fp
                cache_dirty = True
            else:
                print(f"[run_all] {step.name} -> {step.script}")
                _run_script(script_path, step_name=step.name)
                _check_outputs(step.expected_outputs)
                cache[step.script] = fp
                cache_dirty = True
        else:
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
    if (paper_root() / "sections/generated/audit_summary_rows.tex") in [
        paper_root() / p for p in all_expected
    ]:
        _check_outputs(["sections/generated/audit_summary_rows.tex"])

    if cache_dirty:
        _save_run_all_cache(cache)

    print("[run_all] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
