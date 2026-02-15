#!/usr/bin/env python3
"""筛选finite-part相关且差异在10-100行之间的文件"""

import os
from pathlib import Path

# 工作目录
base_dir = Path("/Users/cookie/gemini/the-omega/docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence")

# 从find_missing.py的输出中筛选
files_with_diff = [
    ("09_zeta_finite_04_03_subsec_arity-dirichlet-mertens-tensor_b",
     "sections/body/zeta_finite_part/parts/09_zeta_finite_04_03_subsec_arity-dirichlet-mertens-tensor_b.tex",
     "sections/body/zeta_finite_part/parts/09_zeta_finite_04_03_subsec_arity-dirichlet-mertens-tensor_b_en.tex",
     689, 703, 14),
    ("app__delta-only",
     "sections/appendix/sync_kernel/weighted/app__delta-only.tex",
     "sections/appendix/sync_kernel/weighted/app__delta-only_en.tex",
     194, 148, -46),
    ("app__real-input-40-zeta-u",
     "sections/appendix/sync_kernel/real_input/app__real-input-40-zeta-u.tex",
     "sections/appendix/sync_kernel/real_input/app__real-input-40-zeta-u_en.tex",
     585, 559, -26),
    ("app__sync-kernel-A-compare",
     "sections/appendix/sync_kernel/app__sync-kernel-A-compare.tex",
     "sections/appendix/sync_kernel/app__sync-kernel-A-compare_en.tex",
     457, 442, -15),
    ("app__vector-potential",
     "sections/appendix/sync_kernel/app__vector-potential.tex",
     "sections/appendix/sync_kernel/app__vector-potential_en.tex",
     476, 415, -61),
    ("cor__sync-kernel-weighted-phase-amplitude",
     "sections/appendix/sync_kernel/weighted/cor__sync-kernel-weighted-phase-amplitude.tex",
     "sections/appendix/sync_kernel/weighted/cor__sync-kernel-weighted-phase-amplitude_en.tex",
     279, 254, -25),
    ("rem__arity-335-rational-tail",
     "sections/body/zeta_finite_part/finite_part/rem__arity-335-rational-tail.tex",
     "sections/body/zeta_finite_part/finite_part/rem__arity-335-rational-tail_en.tex",
     689, 703, 14),
    ("rem__pom-charpoly-mod3-selection",
     "sections/body/pom/parts/resonance/rem__pom-charpoly-mod3-selection.tex",
     "sections/body/pom/parts/resonance/rem__pom-charpoly-mod3-selection_en.tex",
     157, 103, -54),
    ("rem__pom-collision-kernel-rh-phase",
     "sections/body/pom/parts/rem__pom-collision-kernel-rh-phase.tex",
     "sections/body/pom/parts/rem__pom-collision-kernel-rh-phase_en.tex",
     570, 495, -75),
    ("rem__pom-renyi-gap-to-hinfty",
     "sections/body/pom/parts/rem__pom-renyi-gap-to-hinfty.tex",
     "sections/body/pom/parts/rem__pom-renyi-gap-to-hinfty_en.tex",
     334, 289, -45),
    ("sec__experiments",
     "sections/body/experiments/sec__experiments.tex",
     "sections/body/experiments/sec__experiments_en.tex",
     582, 550, -32),
    ("prop__pom-resonance-two-cycle-ratio",
     "sections/body/pom/parts/resonance/prop__pom-resonance-two-cycle-ratio.tex",
     "sections/body/pom/parts/resonance/prop__pom-resonance-two-cycle-ratio_en.tex",
     145, 113, -32),
    ("subsec__group-unification-audit-pointers",
     "sections/body/group_unification/subsec__group-unification-audit-pointers.tex",
     "sections/body/group_unification/subsec__group-unification-audit-pointers_en.tex",
     575, 530, -45),
    ("subsec__folding-map",
     "sections/body/folding/subsec__folding-map.tex",
     "sections/body/folding/subsec__folding-map_en.tex",
     112, 135, 23),
    ("subsec__pom-pw-tannaka-krein-reconstruction",
     "sections/body/pom/parts/subsec__pom-pw-tannaka-krein-reconstruction.tex",
     "sections/body/pom/parts/subsec__pom-pw-tannaka-krein-reconstruction_en.tex",
     88, 72, -16),
    ("subsec__real-input-40-prime-splitting",
     "sections/appendix/sync_kernel/real_input/subsec__real-input-40-prime-splitting.tex",
     "sections/appendix/sync_kernel/real_input/subsec__real-input-40-prime-splitting_en.tex",
     260, 252, -8),
    ("subsec__sync-kernel-counting",
     "sections/appendix/sync_kernel/subsec__sync-kernel-counting.tex",
     "sections/appendix/sync_kernel/subsec__sync-kernel-counting_en.tex",
     319, 289, -30),
    ("subsec__unit-circle-phase-lift",
     "sections/appendix/unit_circle_phase_arithmetic/subsec__unit-circle-phase-lift.tex",
     "sections/appendix/unit_circle_phase_arithmetic/subsec__unit-circle-phase-lift_en.tex",
     128, 100, -28),
    ("subsec__unit-disk-witt-chebyshev",
     "sections/appendix/unit_circle_phase_arithmetic/subsec__unit-disk-witt-chebyshev.tex",
     "sections/appendix/unit_circle_phase_arithmetic/subsec__unit-disk-witt-chebyshev_en.tex",
     281, 242, -39),
    ("subsec__xi-from-self-dual",
     "sections/body/zeta_finite_part/xi/subsec__xi-from-self-dual.tex",
     "sections/body/zeta_finite_part/xi/subsec__xi-from-self-dual_en.tex",
     516, 489, -27),
    ("subsec__xi-near1-diffusive",
     "sections/body/zeta_finite_part/xi/subsec__xi-near1-diffusive.tex",
     "sections/body/zeta_finite_part/xi/subsec__xi-near1-diffusive_en.tex",
     174, 119, -55),
    ("subsec__xi-radial-counterexample-collapse",
     "sections/body/zeta_finite_part/xi/subsec__xi-radial-counterexample-collapse.tex",
     "sections/body/zeta_finite_part/xi/subsec__xi-radial-counterexample-collapse_en.tex",
     288, 272, -16),
    ("subsubsec__fold-gauge-anomaly-spectral-recurrence-certificates",
     "sections/body/folding/subsubsec__fold-gauge-anomaly-spectral-recurrence-certificates.tex",
     "sections/body/folding/subsubsec__fold-gauge-anomaly-spectral-recurrence-certificates_en.tex",
     258, 235, -23),
    ("subsubsec__pom-collision-kernel-family",
     "sections/body/pom/parts/subsubsec__pom-collision-kernel-family.tex",
     "sections/body/pom/parts/subsubsec__pom-collision-kernel-family_en.tex",
     536, 460, -76),
    ("subsubsec__pom-fence-green-kernel-spectral-algebra",
     "sections/body/pom/parts/subsubsec__pom-fence-green-kernel-spectral-algebra.tex",
     "sections/body/pom/parts/subsubsec__pom-fence-green-kernel-spectral-algebra_en.tex",
     486, 403, -83),
    ("subsubsec__pom-fence-green-kernel-spectral-algebra__boundary-spectral-measure",
     "sections/body/pom/parts/subsubsec__pom-fence-green-kernel-spectral-algebra__boundary-spectral-measure.tex",
     "sections/body/pom/parts/subsubsec__pom-fence-green-kernel-spectral-algebra__boundary-spectral-measure_en.tex",
     191, 111, -80),
    ("subsubsec__pom-fiber-cubical-hyperplane-symmetry-limit",
     "sections/body/pom/parts/subsubsec__pom-fiber-cubical-hyperplane-symmetry-limit.tex",
     "sections/body/pom/parts/subsubsec__pom-fiber-cubical-hyperplane-symmetry-limit_en.tex",
     379, 292, -87),
    ("subsubsec__pom-hoelder-mixed-kl-bridge",
     "sections/body/pom/parts/subsubsec__pom-hoelder-mixed-kl-bridge.tex",
     "sections/body/pom/parts/subsubsec__pom-hoelder-mixed-kl-bridge_en.tex",
     220, 171, -49),
    ("subsubsec__window6-edge-flux-arithmetic",
     "sections/body/group_unification/subsubsec__window6-edge-flux-arithmetic.tex",
     "sections/body/group_unification/subsubsec__window6-edge-flux-arithmetic_en.tex",
     218, 172, -46),
    ("subsubsec__ramanujan-phase-lift-symmetry",
     "sections/body/zeta_finite_part/xi/subsubsec__ramanujan-phase-lift-symmetry.tex",
     "sections/body/zeta_finite_part/xi/subsubsec__ramanujan-phase-lift-symmetry_en.tex",
     594, 557, -37),
    ("subsubsec__xi-endpoint-tomography-radial-profile",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-endpoint-tomography-radial-profile.tex",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-endpoint-tomography-radial-profile_en.tex",
     193, 155, -38),
    ("subsubsec__xi-fixed-slice-audit-chain",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-fixed-slice-audit-chain.tex",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-fixed-slice-audit-chain_en.tex",
     127, 109, -18),
    ("subsubsec__xi-quadratic-pencil-leakage-spectrum",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-quadratic-pencil-leakage-spectrum.tex",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-quadratic-pencil-leakage-spectrum_en.tex",
     422, 400, -22),
    ("subsubsec__xi-ramanujan-horizon-ledger-framework",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-ramanujan-horizon-ledger-framework.tex",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-ramanujan-horizon-ledger-framework_en.tex",
     261, 192, -69),
    ("subsubsec__xi-read-reflector-completeness",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-read-reflector-completeness.tex",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-read-reflector-completeness_en.tex",
     585, 569, -16),
    ("subsubsec__xi-time-protocol-conclusions",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions.tex",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions_en.tex",
     531, 513, -18),
    ("subsubsec__xi-time-protocol-conclusions-part2",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part2.tex",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part2_en.tex",
     418, 366, -52),
    ("subsubsec__xi-time-protocol-conclusions-part5",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part5.tex",
     "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part5_en.tex",
     226, 206, -20),
    ("thm__pom-third-max-fiber-even-closed-form",
     "sections/body/pom/parts/thm__pom-third-max-fiber-even-closed-form.tex",
     "sections/body/pom/parts/thm__pom-third-max-fiber-even-closed-form_en.tex",
     573, 545, -28),
]

# 筛选finite-part相关的文件
finite_part_keywords = [
    "finite", "zeta", "arity", "xi", "real-input",
    "sync-kernel", "weighted", "mertens", "dirichlet"
]

def is_finite_part_related(name, path_cn, path_en):
    """检查文件是否与finite-part相关"""
    combined = (name + path_cn + path_en).lower()
    return any(keyword in combined for keyword in finite_part_keywords)

# 筛选并打印
print("=" * 100)
print("finite-part相关且差异在10-100行之间的文件")
print("=" * 100)
print()

count = 0
for name, path_cn, path_en, lines_cn, lines_en, diff in files_with_diff:
    abs_diff = abs(diff)
    if 10 <= abs_diff <= 100 and is_finite_part_related(name, path_cn, path_en):
        count += 1
        print(f"{count}. 文件: {name}")
        print(f"   中文: {path_cn} ({lines_cn} 行)")
        print(f"   英文: {path_en} ({lines_en} 行)")
        print(f"   差异: {diff:+d} 行 (绝对值: {abs_diff})")
        print()

print(f"共找到 {count} 个需要处理的文件")
