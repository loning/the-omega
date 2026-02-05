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
            name="rotation_microstate_kl_certificate",
            script="exp_rotation_microstate_kl_certificate.py",
            args=[],
            expected_outputs=[
                "artifacts/export/rotation_microstate_kl_certificate.csv",
                "sections/generated/tab_rotation_microstate_kl_certificate.tex",
                "sections/generated/tab_rotation_folded_kl_certificate.tex",
            ],
        ),
        Step(
            name="rotation_fold_vs_parry",
            script="exp_rotation_fold_vs_parry.py",
            args=[],
            expected_outputs=[
                "artifacts/export/rotation_fold_vs_parry.csv",
            ],
        ),
        Step(
            name="rotation_multiscale_residual_summary",
            script="exp_rotation_multiscale_residual_summary.py",
            args=[],
            expected_outputs=[
                "sections/generated/tab_rotation_multiscale_residual_summary.tex",
            ],
        ),
        Step(
            name="fold_gauge_anomaly",
            script="exp_fold_gauge_anomaly.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_gauge_anomaly_stats.json",
                "sections/generated/tab_fold_gauge_anomaly_stats.tex",
            ],
        ),
        Step(
            name="fold_truncation_curvature",
            script="exp_fold_truncation_curvature.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_truncation_curvature_stats.json",
                "sections/generated/tab_fold_truncation_curvature_stats.tex",
            ],
        ),
        Step(
            name="fold_gauge_anomaly_density_49",
            script="exp_fold_gauge_anomaly_density_49.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_gauge_anomaly_density_49_audit.json",
                "sections/generated/eq_fold_gauge_anomaly_density_49.tex",
            ],
        ),
        Step(
            name="fold_gauge_anomaly_density_transducer",
            script="exp_fold_gauge_anomaly_density_transducer.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_gauge_anomaly_density_transducer.json",
                "sections/generated/eq_fold_gauge_anomaly_density_transducer.tex",
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
            name="parry_endpoint_audit",
            script="exp_parry_endpoint_audit.py",
            args=[],
            expected_outputs=[
                "artifacts/export/parry_endpoint_audit.json",
                "sections/generated/tab_parry_endpoint_audit.tex",
            ],
        ),
        Step(
            name="boundary_tower_gut_signatures",
            script="exp_boundary_tower_gut_signatures.py",
            args=[],
            expected_outputs=[
                "artifacts/export/boundary_tower_gut_signatures.json",
                "sections/generated/eq_boundary_tower_sm12.tex",
                "sections/generated/tab_zeckendorf_gut_signatures.tex",
            ],
        ),
        Step(
            name="prime_shadow_window_mi",
            script="exp_prime_shadow_window_mi.py",
            args=[],
            expected_outputs=[
                "artifacts/export/prime_shadow_window_mi.json",
                "sections/generated/tab_prime_shadow_window_mi.tex",
            ],
        ),
        Step(
            name="fib_prime_resolution_windows",
            script="exp_fib_prime_resolution_windows.py",
            args=["--m-min", "6", "--m-max", "40"],
            expected_outputs=[
                "artifacts/export/fib_prime_resolution_windows.json",
                "sections/generated/tab_fib_prime_resolution_windows.tex",
            ],
        ),
        Step(
            name="sync_kernel_weighted_delta_completed",
            script="exp_sync_kernel_weighted_delta_completed.py",
            args=[],
            expected_outputs=[
                "sections/generated/eq_sync_kernel_weighted_delta_completed.tex",
            ],
        ),
        Step(
            name="collision_kernel_A2_primitive",
            script="exp_collision_kernel_A2_primitive.py",
            args=[],
            expected_outputs=[
                "artifacts/export/collision_kernel_A2_primitive.json",
                "sections/generated/tab_collision_kernel_A2_primitive.tex",
            ],
        ),
        Step(
            name="collision_kernel_A2_finite_part",
            script="exp_collision_kernel_A2_finite_part.py",
            args=[],
            expected_outputs=[
                "artifacts/export/collision_kernel_A2_finite_part.json",
                "sections/generated/tab_collision_kernel_A2_finite_part.tex",
            ],
        ),
        Step(
            name="collision_kernel_A3_primitive",
            script="exp_collision_kernel_A3_primitive.py",
            args=[],
            expected_outputs=[
                "artifacts/export/collision_kernel_A3_primitive.json",
                "sections/generated/tab_collision_kernel_A3_primitive.tex",
            ],
        ),
        Step(
            name="collision_kernel_A3_finite_part",
            script="exp_collision_kernel_A3_finite_part.py",
            args=[],
            expected_outputs=[
                "artifacts/export/collision_kernel_A3_finite_part.json",
                "sections/generated/tab_collision_kernel_A3_finite_part.tex",
            ],
        ),
        Step(
            name="fold_collision_renyi_spectrum",
            script="exp_fold_collision_renyi_spectrum.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_collision_renyi_spectrum.json",
                "sections/generated/tab_fold_collision_renyi_spectrum.tex",
            ],
        ),
        Step(
            name="fold_collision_renyi_spectrum_mod_dp_q20",
            script="exp_fold_collision_renyi_spectrum_mod_dp_q20.py",
            args=["--m-min", "8", "--m-max", "30", "--q-max", "20"],
            expected_outputs=[
                "artifacts/export/fold_collision_renyi_spectrum_mod_dp_q20.json",
                "sections/generated/tab_fold_collision_renyi_spectrum_mod_dp_q20.tex",
            ],
        ),
        Step(
            name="fold_collision_renyi_endpoint_convergence_q60",
            script="exp_fold_collision_renyi_endpoint_convergence_q60.py",
            args=["--m-min", "24", "--m-max", "30", "--q-list", "20,30,40,60"],
            expected_outputs=[
                "artifacts/export/fold_collision_renyi_endpoint_convergence_q60.json",
                "sections/generated/tab_fold_collision_renyi_endpoint_convergence_q60.tex",
            ],
        ),
        Step(
            name="fold_collision_pressure_multifractal_q60",
            script="exp_fold_collision_pressure_multifractal_q60.py",
            args=["--m-min", "24", "--m-max", "30", "--q-max", "60", "--use-exact-up-to", "17"],
            expected_outputs=[
                "artifacts/export/fold_collision_pressure_multifractal_q60.json",
                "artifacts/export/fold_collision_pressure_multifractal_q60_rq.png",
                "artifacts/export/fold_collision_pressure_multifractal_q60_pressure.png",
                "artifacts/export/fold_collision_pressure_multifractal_q60_falpha.png",
                "sections/generated/fig_fold_collision_pressure_multifractal_q60_rq.tex",
                "sections/generated/fig_fold_collision_pressure_multifractal_q60_pressure.tex",
                "sections/generated/fig_fold_collision_pressure_multifractal_q60_falpha.tex",
            ],
        ),
        Step(
            name="fold_max_fiber_achievers_phase",
            script="exp_fold_max_fiber_achievers_phase.py",
            args=["--m-min", "2", "--m-max", "32", "--show-words", "4"],
            expected_outputs=[
                "artifacts/export/fold_max_fiber_achievers_phase.json",
                "sections/generated/tab_fold_max_fiber_achievers_phase.tex",
            ],
        ),
        Step(
            name="fold_max_fiber_achievers_bsplit",
            script="exp_fold_max_fiber_achievers_bsplit.py",
            args=["--m-min", "2", "--m-max", "32", "--show-words", "4"],
            expected_outputs=[
                "artifacts/export/fold_max_fiber_achievers_bsplit.json",
                "sections/generated/tab_fold_max_fiber_achievers_bsplit.tex",
            ],
        ),
        Step(
            name="fold_collision_moment_recursions",
            script="exp_fold_collision_moment_recursions.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_collision_moment_recursions.json",
                "sections/generated/tab_fold_collision_moment_recursions.tex",
            ],
        ),
        Step(
            name="fold_collision_moment_recursions_moddp_9_17_precomputed",
            script="exp_fold_collision_moment_recursions_mod_dp.py",
            args=["--precomputed"],
            expected_outputs=[
                "artifacts/export/fold_collision_moment_recursions_moddp_9_17.json",
                "sections/generated/tab_fold_collision_moment_recursions_9_17.tex",
            ],
        ),
        Step(
            name="fold_collision_resonance_nullmodes_hankel_q9_17",
            script="exp_fold_collision_resonance_nullmodes_hankel.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_collision_resonance_nullmodes_hankel_q9_17.json",
                "sections/generated/tab_fold_collision_resonance_gap_delta_q_9_17.tex",
                "sections/generated/tab_fold_collision_resonance_nullmodes_q9_17.tex",
            ],
        ),
        Step(
            name="fold_collision_col_hankel_mod3_alignment_q9",
            script="exp_fold_collision_col_hankel_mod3_alignment.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_collision_col_hankel_mod3_alignment_q9.json",
                "artifacts/export/fold_collision_col_hankel_mod3_alignment_q9.png",
                "sections/generated/fig_fold_collision_col_hankel_mod3_alignment_q9.tex",
            ],
        ),
        Step(
            name="fold_collision_moment_spectrum_k2_8",
            script="exp_fold_collision_moment_spectrum_k2_8.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_collision_moment_spectrum_k2_8.json",
                "sections/generated/tab_fold_collision_moment_spectrum_k2_8.tex",
            ],
        ),
        Step(
            name="fold_collision_moment_spectrum_k9_17",
            script="exp_fold_collision_moment_spectrum_k9_17.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_collision_moment_spectrum_k9_17.json",
                "sections/generated/tab_fold_collision_moment_spectrum_k9_17.tex",
            ],
        ),
        Step(
            name="fold_collision_kernel_rh_scan_q2_17",
            script="exp_fold_collision_kernel_rh_scan_q2_17.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_collision_kernel_rh_scan_q2_17.json",
                "sections/generated/tab_fold_collision_kernel_rh_scan_q2_17.tex",
            ],
        ),
        Step(
            name="fold_collision_shadow_spectral_packet_q9_17",
            script="exp_fold_collision_shadow_spectral_packet_q9_17.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_collision_shadow_spectral_packet_q9_17.json",
                "sections/generated/tab_fold_collision_shadow_spectral_packet_q9_17.tex",
            ],
        ),
        Step(
            name="fold_fiber_log_moments_mu_sigma",
            script="exp_fold_fiber_log_moments_mu_sigma.py",
            args=["--m-min", "8", "--m-max", "30", "--m-step", "2"],
            expected_outputs=[
                "artifacts/export/fold_fiber_log_moments_mu_sigma.json",
                "sections/generated/tab_fold_fiber_log_moments_mu_sigma.tex",
            ],
        ),
        Step(
            name="fold_kappa_tv_budget",
            script="exp_fold_kappa_tv_budget.py",
            args=["--m-list", "8,10,12,14,16", "--tau", "0.02", "--delta", "1e-6"],
            expected_outputs=[
                "artifacts/export/fold_kappa_tv_budget.json",
                "sections/generated/tab_fold_kappa_tv_budget.tex",
            ],
        ),
        Step(
            name="pom_rewriting_engine_demo",
            script="exp_pom_rewriting_engine_demo.py",
            args=[],
            expected_outputs=[
                "artifacts/export/pom_rewriting_engine_demo.json",
                "sections/generated/tab_pom_rewriting_engine_demo.tex",
            ],
        ),
        Step(
            name="pom_projword_lift_proj_normalizer_demo",
            script="exp_pom_projword_lift_proj_normalizer_demo.py",
            args=[],
            expected_outputs=[
                "artifacts/export/pom_projword_lift_proj_normalizer_demo.json",
                "sections/generated/tab_pom_projword_lift_proj_normalizer_demo.tex",
            ],
        ),
        Step(
            name="pom_projword_mom_twist_normalizer_demo",
            script="exp_pom_projword_mom_twist_normalizer_demo.py",
            args=[],
            expected_outputs=[
                "artifacts/export/pom_projword_mom_twist_normalizer_demo.json",
                "sections/generated/tab_pom_projword_mom_twist_normalizer_demo.tex",
            ],
        ),
        Step(
            name="pom_projword_full_normalizer_demo",
            script="exp_pom_projword_full_normalizer_demo.py",
            args=[],
            expected_outputs=[
                "artifacts/export/pom_projword_full_normalizer_demo.json",
                "sections/generated/tab_pom_projword_full_normalizer_demo.tex",
            ],
        ),
        Step(
            name="pom_holonomy_cocycle_audit",
            script="exp_pom_holonomy_cocycle_audit.py",
            args=[],
            expected_outputs=[
                "artifacts/export/pom_holonomy_cocycle_audit.json",
            ],
        ),
        Step(
            name="fold_tail_budget_gamma_cert",
            script="exp_fold_tail_budget_gamma_cert.py",
            args=["--m", "24", "--eps-list", "1e-6,1e-9", "--q-max", "17"],
            expected_outputs=[
                "artifacts/export/fold_tail_budget_gamma_cert.json",
            ],
        ),
        Step(
            name="fold_collision_moment_hankel_rank",
            script="exp_fold_collision_moment_hankel_rank.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_collision_moment_hankel_rank.json",
                "sections/generated/tab_fold_collision_moment_hankel_rank.tex",
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
            name="sync_kernel_B_dirichlet_constants",
            script="exp_sync_kernel_B_dirichlet_constants.py",
            args=[],
            expected_outputs=[
                "sections/generated/tab_sync_kernel_B_dirichlet_constants.tex",
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
            name="sync_kernel_weighted_3d_exact_audits",
            script="exp_sync_kernel_weighted_3d_exact_audits.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_weighted_3d_exact_audits.json",
                "sections/generated/eq_sync_kernel_3d_critical_w_half_delta.tex",
                "sections/generated/eq_sync_kernel_3d_hessian_inverse_exact.tex",
                "sections/generated/eq_sync_kernel_3d_quadratic_orthobasis.tex",
            ],
        ),
        Step(
            name="sync_kernel_weighted_primitive_completed",
            script="exp_sync_kernel_weighted_primitive_completed.py",
            args=[],
            expected_outputs=[
                "sections/generated/tab_sync_kernel_weighted_primitive_completed.tex",
                "sections/generated/eq_sync_kernel_weighted_primitive_pn_first10.tex",
            ],
        ),
        Step(
            name="sync_kernel_weighted_completion_Q_sy",
            script="exp_sync_kernel_weighted_completion_Q_sy.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_weighted_completion_Q_sy.json",
                "sections/generated/eq_sync_kernel_weighted_completion_Q_sy.tex",
            ],
        ),
        Step(
            name="sync_kernel_weighted_delta_explicit",
            script="exp_sync_kernel_weighted_delta_explicit.py",
            args=[],
            expected_outputs=[
                "sections/generated/eq_sync_kernel_weighted_delta_explicit.tex",
            ],
        ),
        Step(
            name="sync_kernel_weighted_padic_unit_root",
            script="exp_sync_kernel_weighted_padic_unit_root.py",
            args=["--p", "5", "--N", "12", "--k-max", "6", "--u", "minus1"],
            expected_outputs=[
                "artifacts/export/sync_kernel_weighted_padic_unit_root.json",
                "sections/generated/tab_sync_kernel_weighted_padic_unit_root.tex",
            ],
        ),
        Step(
            name="sync_kernel_rate_curve_elimination",
            script="exp_sync_kernel_rate_curve_elimination.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_rate_curve_resultant.json",
                "sections/generated/tab_sync_kernel_rate_curve_resultant_degree.tex",
                "sections/generated/eq_sync_kernel_rate_curve_resultant_structure.tex",
            ],
        ),
        Step(
            name="sync_kernel_rate_curve_curvature_bounds",
            script="exp_sync_kernel_rate_curve_curvature_bounds.py",
            args=[],
            expected_outputs=[
                "sections/generated/tab_sync_kernel_rate_curve_curvature_bounds.tex",
            ],
        ),
        Step(
            name="sync_kernel_weighted_chebyshev_dwork_chain",
            script="exp_sync_kernel_weighted_chebyshev_dwork_chain.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_weighted_chebyshev_dwork_chain.json",
                "sections/generated/tab_sync_kernel_weighted_chebyshev_dwork_chain.tex",
            ],
        ),
        Step(
            name="sync_kernel_weighted_phase_amplitude",
            script="exp_sync_kernel_weighted_phase_amplitude_separation.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_weighted_phase_amplitude.json",
                "sections/generated/tab_sync_kernel_weighted_phase_amplitude.tex",
            ],
        ),
        Step(
            name="sync_kernel_time_correlation",
            script="exp_sync_kernel_time_correlation.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_time_correlation.json",
                "artifacts/export/sync_kernel_time_correlation.png",
                "sections/generated/fig_sync_kernel_time_correlation.tex",
            ],
        ),
        Step(
            name="sync_kernel_10_state_uniform_input_fingerprint",
            script="exp_sync_kernel_10_state_uniform_input_fingerprint.py",
            args=["--steps", "10000000", "--burn-in", "200000", "--seed", "7"],
            expected_outputs=[
                "artifacts/export/sync_kernel_10_state_uniform_input_fingerprint.json",
                "sections/generated/eq_sync_kernel_10_state_uniform_input_fingerprint.tex",
            ],
        ),
        Step(
            name="sync_kernel_cyclotomic_elimination",
            script="exp_sync_kernel_cyclotomic_elimination.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_cyclotomic_elimination.json",
                "sections/generated/tab_sync_kernel_cyclotomic_elimination_summary.tex",
                "sections/generated/tab_sync_kernel_cyclotomic_elimination_polys.tex",
            ],
        ),
        Step(
            name="sync_kernel_hatdelta_discriminant",
            script="exp_sync_kernel_hatdelta_discriminant.py",
            args=["--dps", "80"],
            expected_outputs=[
                "artifacts/export/sync_kernel_hatdelta_discriminant.json",
                "sections/generated/eq_sync_kernel_hatdelta_discriminant.tex",
                "sections/generated/tab_sync_kernel_hatdelta_branch_points.tex",
            ],
        ),
        Step(
            name="sync_kernel_output_potential_branch_radius_certificate",
            script="exp_sync_kernel_output_potential_branch_radius_certificate.py",
            args=["--dps", "80", "--nphi", "512", "--radial-steps", "120"],
            expected_outputs=[
                "artifacts/export/sync_kernel_output_potential_branch_radius_certificate.json",
                "sections/generated/eq_sync_kernel_output_potential_branch_radius_certificate.tex",
            ],
        ),
        Step(
            name="sync_kernel_phi_minus_cubic_series",
            script="exp_sync_kernel_phi_minus_cubic_series.py",
            args=[],
            expected_outputs=[
                "sections/generated/eq_sync_kernel_phi_minus_cubic_series.tex",
            ],
        ),
        Step(
            name="sync_kernel_xi_cubic_cos_polynomial",
            script="exp_sync_kernel_xi_cubic_cos_polynomial.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_xi_cubic_criterion.json",
                "sections/generated/eq_sync_kernel_xi_cubic_cos_polynomial.tex",
                "sections/generated/eq_sync_kernel_xi_off_critical_shift.tex",
                "sections/generated/tab_sync_kernel_xi_cubic_roots.tex",
            ],
        ),
        Step(
            name="sync_kernel_3d_conditional_covariance",
            script="exp_sync_kernel_3d_conditional_covariance.py",
            args=[],
            expected_outputs=[
                "sections/generated/eq_sync_kernel_3d_conditional_covariance.tex",
            ],
        ),
        Step(
            name="arity_335_cross_layer_diagnostics",
            script="exp_arity_335_cross_layer_diagnostics.py",
            args=[],
            expected_outputs=[
                "sections/generated/eq_arity_335_cross_layer_diagnostics.tex",
            ],
        ),
        Step(
            name="real_input_40_logM_artin_factorization",
            script="exp_real_input_40_logM_artin_factorization.py",
            args=[],
            expected_outputs=[
                "sections/generated/eq_real_input_40_logM_artin_factorization.tex",
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
            name="real_input_40_operator_algebra_invariants",
            script="exp_real_input_40_operator_algebra_invariants.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_operator_algebra_invariants.json",
                "sections/generated/tab_real_input_40_bf_ktheory.tex",
                "sections/generated/tab_real_input_40_parry_internal_distribution.tex",
                "sections/generated/tab_real_input_40_nilpotent_jordan.tex",
            ],
        ),
        Step(
            name="real_input_40_kernel_newman_threshold",
            script="exp_real_input_40_kernel_newman_threshold.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_kernel_newman_threshold.json",
                "sections/generated/tab_real_input_40_kernel_newman_threshold.tex",
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
            name="real_input_40_output_potential_zero_temp_ground_sft",
            script="exp_real_input_40_output_potential_zero_temp_ground_sft.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_output_potential_zero_temp_ground_sft.json",
                "sections/generated/eq_real_input_40_output_potential_zero_temp_ground_sft.tex",
            ],
        ),
        Step(
            name="real_input_40_rotation_polytope",
            script="exp_real_input_40_rotation_polytope.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_rotation_polytope_sample.json",
                "sections/generated/tab_real_input_40_rotation_polytope_sample.tex",
            ],
        ),
        Step(
            name="real_input_40_rotation_polytope_exact",
            script="exp_real_input_40_rotation_polytope_exact.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_rotation_polytope_exact.json",
                "sections/generated/eq_real_input_40_rotation_polytope_vertices.tex",
                "sections/generated/eq_real_input_40_rotation_polytope_facets.tex",
                "sections/generated/eq_real_input_40_rotation_polytope_zero_temp_support.tex",
                "sections/generated/tab_real_input_40_rotation_polytope_vertices.tex",
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
            name="sync_kernel_real_input_40_arity_charge_closed_form",
            script="exp_sync_kernel_real_input_40_arity_charge_closed_form.py",
            args=[],
            expected_outputs=[
                "artifacts/export/sync_kernel_real_input_40_arity_charge_closed_form.json",
                "sections/generated/eq_real_input_40_arity_charge_det_closed.tex",
                "sections/generated/eq_real_input_40_arity_charge_zero_charge_zeta.tex",
                "sections/generated/eq_real_input_40_arity_charge_cumulants_closed.tex",
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
                "sections/generated/tab_real_input_40_arity_dirichlet_mertens_335.tex",
                "sections/generated/tab_real_input_40_arity_dirichlet_mertens_555.tex",
            ],
        ),
        Step(
            name="real_input_40_mertens_tensor_bias_222",
            script="exp_real_input_40_mertens_tensor_bias_222.py",
            args=[],
            expected_outputs=[
                "sections/generated/eq_real_input_40_arity_dirichlet_mertens_222_bias.tex",
            ],
        ),
        Step(
            name="sync_kernel_real_input_40_arity_3d_335_N2",
            script="exp_sync_kernel_real_input_40_arity_3d.py",
            args=[
                "--third-axis",
                "N2",
                "--triple-values",
                "3x3x5",
                "--output",
                "artifacts/export/sync_kernel_real_input_40_arity_3d_N2_335.json",
            ],
            expected_outputs=[
                "artifacts/export/sync_kernel_real_input_40_arity_3d_N2_335.json",
                "sections/generated/tab_real_input_40_arity_dirichlet_mertens_335_N2.tex",
            ],
        ),
        Step(
            name="arity_335_character_energy",
            script="exp_arity_335_character_energy.py",
            args=[],
            expected_outputs=[
                "artifacts/export/arity_335_character_energy.json",
                "sections/generated/tab_arity_335_character_energy_head.tex",
            ],
        ),
        Step(
            name="real_input_40_dirichlet_mertens_functoriality",
            script="exp_real_input_40_dirichlet_mertens_functoriality.py",
            args=["--triple", "3x3x5"],
            expected_outputs=[
                "artifacts/export/real_input_40_dirichlet_mertens_functoriality.json",
                "sections/generated/tab_real_input_40_dirichlet_mertens_functoriality.tex",
            ],
        ),
        Step(
            name="real_input_40_dirichlet_mertens_tensor_anova",
            script="exp_real_input_40_dirichlet_mertens_tensor_anova.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_dirichlet_mertens_tensor_anova.json",
                "artifacts/export/real_input_40_dirichlet_mertens_tensor_anova_scatter.png",
                "sections/generated/tab_real_input_40_dirichlet_mertens_tensor_anova.tex",
                "sections/generated/fig_real_input_40_dirichlet_mertens_tensor_anova_scatter.tex",
            ],
        ),
        Step(
            name="group_unification_spectral_alignment_diagnostics",
            script="exp_group_unification_spectral_alignment_diagnostics.py",
            args=[],
            expected_outputs=[
                "artifacts/export/group_unification_spectral_alignment_diagnostics.json",
                "sections/generated/eq_group_unification_spectral_alignment_diagnostics.tex",
            ],
        ),
        Step(
            name="real_input_40_covariance_worst_character",
            script="exp_real_input_40_covariance_predict_worst_character.py",
            args=["--triple", "3x3x5", "--third-axis", "N2", "--h", "0.0002"],
            expected_outputs=[
                "artifacts/export/real_input_40_covariance_worst_character.json",
                "sections/generated/tab_real_input_40_covariance_worst_character.tex",
            ],
        ),
        Step(
            name="real_input_40_output_potential_dirichlet_twists",
            script="exp_real_input_40_output_potential_dirichlet_twists.py",
            args=["--m-list", "2,3,4,5,6,10,20", "--dps", "90"],
            expected_outputs=[
                "artifacts/export/real_input_40_output_potential_dirichlet_twists.json",
                "sections/generated/tab_real_input_40_output_potential_dirichlet_twists.tex",
            ],
        ),
        Step(
            name="real_input_40_output_potential_activated_branch_series",
            script="exp_real_input_40_output_potential_activated_branch_series.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_output_potential_activated_branch_series.json",
                "sections/generated/eq_real_input_40_output_potential_activated_branch_series.tex",
            ],
        ),
        Step(
            name="real_input_40_pure_collision_block_factorization",
            script="exp_real_input_40_pure_collision_block_factorization.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_pure_collision_block_factorization.json",
                "sections/generated/tab_real_input_40_pure_collision_block_factorization.tex",
            ],
        ),
        Step(
            name="arity_335_n2_master_curve",
            script="exp_arity_335_n2_master_curve.py",
            args=["--p-list", "7,11,13", "--k-max", "1", "--diff-h", "0.0002"],
            expected_outputs=[
                "artifacts/export/arity_335_n2_master_curve.json",
                "sections/generated/tab_real_input_40_arity_335_n2_master_curve.tex",
            ],
        ),
        Step(
            name="arity_pure_collision_cubic_asymp_coeffs",
            script="exp_arity_pure_collision_cubic_asymp_coeffs.py",
            args=[],
            expected_outputs=[
                "artifacts/export/arity_pure_collision_cubic_asymp_coeffs.json",
                "sections/generated/tab_arity_pure_collision_cubic_asymp_coeffs.tex",
            ],
        ),
        Step(
            name="arity_pure_collision_cubic_primes",
            script="exp_arity_pure_collision_cubic_primes.py",
            args=["--p-max", "101", "--dps", "80"],
            expected_outputs=[
                "artifacts/export/arity_pure_collision_cubic_primes.json",
                "sections/generated/tab_arity_pure_collision_cubic_primes.tex",
            ],
        ),
        Step(
            name="arity_pure_collision_cubic_rh_threshold_beta",
            script="exp_arity_pure_collision_cubic_rh_threshold_beta.py",
            args=["--dps", "80"],
            expected_outputs=[
                "artifacts/export/arity_pure_collision_cubic_rh_threshold_beta.json",
                "sections/generated/eq_arity_pure_collision_cubic_rh_threshold_uR.tex",
                "sections/generated/tab_arity_pure_collision_cubic_rh_threshold_beta.tex",
            ],
        ),
        Step(
            name="arity_335_N2_selection_law_primes",
            script="exp_arity_335_n2_selection_law_primes.py",
            args=[],
            expected_outputs=[
                "artifacts/export/arity_335_n2_selection_law_primes.json",
                "sections/generated/tab_real_input_40_arity_335_n2_selection_law_primes.tex",
            ],
        ),
        Step(
            name="arity_335_n2_limit_law",
            script="exp_arity_335_n2_limit_law_table.py",
            args=[],
            expected_outputs=[
                "artifacts/export/arity_335_n2_limit_law.json",
                "sections/generated/tab_real_input_40_arity_335_n2_limit_law.tex",
            ],
        ),
        Step(
            name="arity_335_kappa_poisson",
            script="exp_arity_335_kappa_poisson.py",
            args=[],
            expected_outputs=[
                "artifacts/export/arity_335_kappa_poisson.json",
                "sections/generated/eq_arity_335_kappa_poisson.tex",
            ],
        ),
        Step(
            name="arity_335_n2_poisson_richardson_validate",
            script="exp_arity_335_n2_poisson_richardson_validate.py",
            args=[],
            expected_outputs=[
                "artifacts/export/arity_335_n2_poisson_richardson_validate.json",
                "sections/generated/tab_real_input_40_arity_335_n2_poisson_richardson_validate.tex",
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
            name="sync_kernel_real_input_40_logM_chi",
            script="exp_sync_kernel_real_input_40_logM_chi.py",
            args=[
                "--t-steps",
                "161",
                "--k-max",
                "250",
            ],
            expected_outputs=[
                "artifacts/export/sync_kernel_real_input_40_logM_chi.json",
                "artifacts/export/sync_kernel_real_input_40_logM_chi.png",
                "sections/generated/fig_real_input_40_logM_chi.tex",
                "sections/generated/tab_real_input_40_logM_chi_local_derivatives.tex",
            ],
        ),
        Step(
            name="sync_kernel_real_input_40_logM_theta_taylor",
            script="exp_sync_kernel_real_input_40_logM_theta_taylor.py",
            args=[
                "--h",
                "0.0002",
                "--k-max",
                "200",
            ],
            expected_outputs=[
                "artifacts/export/sync_kernel_real_input_40_logM_theta_taylor.json",
                "sections/generated/tab_real_input_40_logM_theta_taylor.tex",
            ],
        ),
        Step(
            name="real_input_40_local_bigeometry_invariants",
            script="exp_real_input_40_local_bigeometry_invariants.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_local_bigeometry_invariants.json",
                "sections/generated/tab_real_input_40_local_bigeometry_invariants.tex",
            ],
        ),
        Step(
            name="real_input_40_time_correlation",
            script="exp_real_input_40_time_correlation.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_time_correlation.json",
                "artifacts/export/real_input_40_time_correlation.png",
                "sections/generated/fig_real_input_40_time_correlation.tex",
            ],
        ),
        Step(
            name="real_input_40_output_potential_cumulants_closed",
            script="exp_real_input_40_output_potential_cumulants_closed.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_output_potential_cumulants_closed.json",
                "sections/generated/tab_real_input_40_output_potential_cumulants_closed.tex",
            ],
        ),
        Step(
            name="real_input_40_output_potential_ldp_algebraic_param",
            script="exp_real_input_40_output_potential_ldp_algebraic_param.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_output_potential_ldp_algebraic_param.json",
                "sections/generated/eq_real_input_40_output_potential_ldp_algebraic_param.tex",
            ],
        ),
        Step(
            name="real_input_40_output_potential_spectral_collisions",
            script="exp_real_input_40_output_potential_spectral_collisions.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_output_potential_spectral_collisions.json",
                "sections/generated/eq_real_input_40_output_potential_spectral_collision_identities.tex",
                "sections/generated/tab_real_input_40_output_potential_spectral_collision_roots.tex",
            ],
        ),
        Step(
            name="real_input_40_event_time_dilation",
            script="exp_real_input_40_event_time_dilation.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_event_time_dilation.json",
                "sections/generated/tab_real_input_40_event_time_dilation.tex",
            ],
        ),
        Step(
            name="real_input_40_event_clock_vs_tau_mix",
            script="exp_real_input_40_event_clock_vs_tau_mix.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_event_clock_vs_tau_mix.json",
                "sections/generated/tab_real_input_40_event_clock_vs_tau_mix.tex",
            ],
        ),
        Step(
            name="real_input_40_event_clock_deviation_certificate",
            script="exp_real_input_40_event_clock_deviation_certificate.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_event_clock_deviation_certificate.json",
                "sections/generated/tab_real_input_40_event_clock_deviation_certificate.tex",
                "sections/generated/tab_real_input_40_hitting_time_deviation_certificate.tex",
            ],
        ),
        Step(
            name="real_input_40_hitting_time_exact_quantiles",
            script="exp_real_input_40_hitting_time_exact_quantiles.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_hitting_time_exact_quantiles.json",
                "sections/generated/tab_real_input_40_hitting_time_exact_quantiles.tex",
            ],
        ),
        Step(
            name="real_input_40_event_time_rescaling_error_budget",
            script="exp_real_input_40_event_time_rescaling_error_budget.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_event_time_rescaling_error_budget.json",
                "artifacts/export/real_input_40_event_time_envelope_vs_tau_mix.json",
                "artifacts/export/real_input_40_event_time_tau_eff_vs_tau_mix.json",
                "artifacts/export/real_input_40_event_time_rho_tau_expectation_vs_tau_mix.json",
                "artifacts/export/real_input_40_event_time_tauE_delta_vs_tau_mix.json",
                "sections/generated/tab_real_input_40_event_time_rescaling_error_budget.tex",
                "sections/generated/tab_real_input_40_event_time_envelope_vs_tau_mix.tex",
                "sections/generated/tab_real_input_40_event_time_tau_eff_vs_tau_mix.tex",
                "sections/generated/tab_real_input_40_event_time_rho_tau_expectation_vs_tau_mix.tex",
                "sections/generated/tab_real_input_40_event_time_tauE_delta_vs_tau_mix.tex",
            ],
        ),
        Step(
            name="real_input_40_time_correlation_fine",
            script="exp_real_input_40_time_correlation.py",
            args=[
                "--t-steps",
                "241",
                "--tag",
                "fine",
            ],
            expected_outputs=[
                "artifacts/export/real_input_40_time_correlation_fine.json",
                "artifacts/export/real_input_40_time_correlation_fine.png",
                "sections/generated/fig_real_input_40_time_correlation_fine.tex",
            ],
        ),
        Step(
            name="real_input_40_time_correlation_decay_certificate",
            script="exp_real_input_40_time_correlation_decay_certificate.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_time_correlation_decay_certificate.json",
                "sections/generated/tab_real_input_40_time_correlation_decay_certificate.tex",
                "sections/generated/tab_real_input_40_time_correlation_decay_certificate_tail.tex",
            ],
        ),
        Step(
            name="real_input_40_time_correlation_phase",
            script="exp_real_input_40_time_correlation_phase.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_time_correlation_phase.json",
                "artifacts/export/real_input_40_time_correlation_phase.png",
                "sections/generated/fig_real_input_40_time_correlation_phase.tex",
                "sections/generated/tab_real_input_40_time_correlation_phase.tex",
            ],
        ),
        Step(
            name="real_input_40_time_correlation_phase_windows",
            script="exp_real_input_40_time_correlation_phase_windows.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_time_correlation_phase_windows.json",
                "sections/generated/tab_real_input_40_time_correlation_phase_windows.tex",
            ],
        ),
        Step(
            name="real_input_40_tau_corr_vs_tau_mix",
            script="exp_real_input_40_tau_corr_vs_tau_mix.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_tau_corr_vs_tau_mix.csv",
                "sections/generated/tab_real_input_40_tau_corr_vs_tau_mix.tex",
                "artifacts/export/real_input_40_tau_corr_vs_tau_mix.png",
                "sections/generated/fig_real_input_40_tau_corr_vs_tau_mix.tex",
                "artifacts/export/real_input_40_tau_corr_monotonicity.json",
                "sections/generated/tab_real_input_40_tau_corr_monotonicity.tex",
                "artifacts/export/real_input_40_tau_corr_monotonicity_refinement.json",
                "sections/generated/tab_real_input_40_tau_corr_monotonicity_refinement.tex",
            ],
        ),
        Step(
            name="real_input_40_finite_part_split",
            script="exp_real_input_40_finite_part_split.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_finite_part_split.json",
                "sections/generated/tab_real_input_40_finite_part_split.tex",
            ],
        ),
        Step(
            name="real_input_40_vert_single_series",
            script="exp_real_input_40_vert_single_series.py",
            args=["--k-max", "800"],
            expected_outputs=[
                "artifacts/export/real_input_40_vert_single_series.json",
                "sections/generated/tab_real_input_40_vert_single_series.tex",
            ],
        ),
        Step(
            name="real_input_40_primitive_artin_split",
            script="exp_real_input_40_primitive_artin_split.py",
            args=[],
            expected_outputs=[
                "artifacts/export/real_input_40_primitive_artin_split.json",
                "sections/generated/tab_real_input_40_primitive_artin_split.tex",
            ],
        ),
        Step(
            name="real_input_40_abel_mertens_two_series_split",
            script="exp_real_input_40_abel_mertens_two_series_split.py",
            args=["--N", "160", "--dps", "80"],
            expected_outputs=[
                "artifacts/export/real_input_40_abel_mertens_two_series_split.json",
                "sections/generated/tab_real_input_40_abel_mertens_two_series_split.tex",
            ],
        ),
        Step(
            name="real_input_40_carry_constant_certified",
            script="exp_real_input_40_carry_constant_certified.py",
            args=["--N", "160", "--dps", "120"],
            expected_outputs=[
                "artifacts/export/real_input_40_carry_constant_certified.json",
                "sections/generated/eq_real_input_40_carry_constant_certified.tex",
            ],
        ),
        Step(
            name="real_input_40_collision_branch_radius",
            script="exp_real_input_40_collision_branch_radius.py",
            args=["--dps", "80"],
            expected_outputs=[
                "artifacts/export/real_input_40_collision_branch_radius.json",
                "sections/generated/eq_real_input_40_collision_branch_radius.tex",
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
            name="parallel_addition_kernels_endpoints_primitive",
            script="exp_parallel_addition_kernels_endpoints_primitive.py",
            args=["--nmax", "20"],
            expected_outputs=[
                "sections/generated/tab_parallel_addition_kernels_endpoint_primitive.tex",
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
            args=[
                "--nmax-9",
                "6",
                "--nmax-13",
                "4",
                "--nmax-21",
                "6",
                "--method-21",
                "enum",
            ],
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
            name="parallel_addition_kernels_trace_hutchinson",
            script="exp_parallel_addition_kernels_trace_hutchinson.py",
            args=[
                "--u-grid",
                "0.25,0.5,0.75",
                "--n-list",
                "3,5,7",
                "--nmax",
                "7",
                "--samples",
                "200",
                "--seed",
                "12345",
            ],
            expected_outputs=[
                "artifacts/export/parallel_addition_kernels_trace_hutchinson.json",
                "sections/generated/tab_parallel_addition_kernels_fingerprint_u_samples.tex",
            ],
        ),
        Step(
            name="parallel_addition_kernels_ihara",
            script="exp_parallel_addition_kernels_ihara.py",
            args=[],
            expected_outputs=[
                "artifacts/export/parallel_addition_kernels_ihara.json",
                "sections/generated/tab_parallel_addition_kernels_ihara_fingerprint.tex",
            ],
        ),
        Step(
            name="parallel_addition_kernels_backtracking_entropy_gap",
            script="exp_parallel_addition_kernels_backtracking_entropy_gap.py",
            args=["--n", "50"],
            expected_outputs=[
                "artifacts/export/parallel_addition_kernels_backtracking_entropy_gap.json",
                "sections/generated/tab_parallel_addition_kernels_backtracking_entropy_gap.tex",
            ],
        ),
        Step(
            name="parallel_addition_kernels_ihara_phase",
            script="exp_parallel_addition_kernels_ihara_phase.py",
            args=[],
            expected_outputs=[
                "artifacts/export/parallel_addition_kernels_ihara_phase.json",
                "artifacts/export/parallel_addition_kernels_ihara_phase.png",
                "sections/generated/tab_parallel_addition_kernels_ihara_rh_scan.tex",
                "sections/generated/fig_parallel_addition_kernels_ihara_phase.tex",
            ],
        ),
        Step(
            name="fold_conditional_expectation_pythagoras",
            script="exp_fold_conditional_expectation_pythagoras.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_conditional_expectation_pythagoras.json",
                "sections/generated/tab_fold_conditional_expectation_pythagoras.tex",
            ],
        ),
        Step(
            name="fold_multiplicity_histogram",
            script="exp_fold_multiplicity_histogram.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_multiplicity_histogram.json",
                "sections/generated/tab_fold_multiplicity_histogram.tex",
            ],
        ),
        Step(
            name="fold_conditional_expectation_singular_spectrum",
            script="exp_fold_conditional_expectation_singular_spectrum.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_conditional_expectation_singular_spectrum.json",
                "sections/generated/tab_fold_conditional_expectation_singular_spectrum.tex",
            ],
        ),
        Step(
            name="fold_markov_projection_tv_decomposition",
            script="exp_fold_markov_projection_tv_decomposition.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_markov_projection_tv_decomposition.json",
                "sections/generated/tab_fold_markov_projection_tv_decomposition.tex",
            ],
        ),
        Step(
            name="fold_conditional_variance_decomposition",
            script="exp_fold_conditional_variance_decomposition.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_conditional_variance_decomposition.json",
                "sections/generated/tab_fold_conditional_variance_decomposition.tex",
            ],
        ),
        Step(
            name="fold_pinsker_residual_bridge",
            script="exp_fold_pinsker_residual_bridge.py",
            args=[],
            expected_outputs=[
                "artifacts/export/fold_pinsker_residual_bridge.json",
                "sections/generated/tab_fold_pinsker_residual_bridge.tex",
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
    parser = argparse.ArgumentParser(
        description="Run reproducible experiment pipeline (with step cache)."
    )
    parser.add_argument(
        "--force", action="store_true", help="Force rerun all steps (ignore cache)."
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable cache (always run)."
    )
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
            print(
                f"[run_all] SKIP {st.name} (cache warm-up: outputs already present)",
                flush=True,
            )
            continue

        if ok and (not args.force) and (not args.no_cache) and cached != sig:
            # Outputs exist but signature changed; rerun for auditability.
            print(f"[run_all] RERUN {st.name} (signature changed)", flush=True)
        elif not ok:
            print(
                f"[run_all] RERUN {st.name} (missing outputs: {', '.join(missing)})",
                flush=True,
            )

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
