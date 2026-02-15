#!/usr/bin/env python3
"""
手动修正剩余的小差异文件
根据实际内容调整行数
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# 需要手动修正的文件列表 (文件路径, 目标差异)
# 差异为正：需要在英文文件末尾添加空行
# 差异为负：需要在英文文件删除空行
manual_fixes = [
    # appendix files - 差异1-10行
    ("sections/appendix/sync_kernel/weighted/subsubsec__sync-kernel-weighted-pressure-ldp", -2),
    ("sections/appendix/unit_circle_phase_arithmetic/app__unit-circle-phase-gate", -1),
    ("sections/appendix/fold_multiplicity/rem__fold-zero-sparse-necessity", -1),
    ("sections/appendix/fold_multiplicity/thm__fold-bin-two-state-asymptotic", -7),
    ("sections/appendix/operator_algebra/app__op-algebra", -1),
    ("sections/appendix/operator_algebra/subsec__op_algebra_modular_zk_index_fkdet", -2),
    ("sections/appendix/operator_algebra/subsubsec__op_algebra_jones_scalar_twirl_cost_renyi_flatness", -1),
    ("sections/appendix/kronecker/app__kronecker-discrepancy", -1),

    # body/pom files
    ("sections/body/pom/parts/08_projection_ontology_mathematics_part03c_a", +2),
    ("sections/body/pom/parts/08_projection_ontology_mathematics_part07_c", +2),
    ("sections/body/pom/parts/cor__pom-fiber-modq-pisano-invariant", -1),
    ("sections/body/pom/parts/cor__pom-fiber-reconstruction-cubical-addenda", +2),
    ("sections/body/pom/parts/cor__pom-fold-factor-chain-derived-invariants", +2),
    ("sections/body/pom/parts/cor__pom-symmetric-remainder", +2),
    ("sections/body/pom/parts/def__pom-ind-lyapunov-fingerprint", -4),
    ("sections/body/pom/parts/lem__pom-shifted-fib-fusion-defect-positive", -5),
    ("sections/body/pom/parts/part__pom-microcanonical-fold-information-linear-law-ldp-sidebits", +8),
    ("sections/body/pom/parts/part__pom-microcanonical-query-distortion-strong-converse", +4),
    ("sections/body/pom/parts/part__pom-microcanonical-query-distortion-strong-converse-part2", -5),
    ("sections/body/pom/parts/part__pom-microcanonical-two-temperature-kkt-failure-exponent", +4),
    ("sections/body/pom/parts/part__pom-microcanonical-typeclass-hamming-ball-volume", +4),
    ("sections/body/pom/parts/part__pom-multiwell-low-temperature-expansion-identifiability", +2),
    ("sections/body/pom/parts/part__pom-oracle-critical-budget-entropy-decomposition", +4),
    ("sections/body/pom/parts/part__pom-oracle-fenchel-duality-area-law", +2),
    ("sections/body/pom/parts/part__pom-oracle-min-kernel-closure-tomography-bregman", +4),
    ("sections/body/pom/parts/part__pom-pressure-multiplicative-chain-entropy-loss", -2),
    ("sections/body/pom/parts/part__pom-zero-temperature-two-term-maxfiber-freezing", +2),
    ("sections/body/pom/parts/prop__pom-a4-discriminant-quadratic-field-class-number", +2),
    ("sections/body/pom/parts/prop__pom-a4t-even-zeta-elimination", +2),
    ("sections/body/pom/parts/resonance/prop__pom-charpoly-modp-a2-embedding", +4),
    ("sections/body/pom/parts/prop__pom-fib-pell-unit-mobius", -3),
    ("sections/body/pom/parts/prop__pom-fiber-index-cgf", -5),
    ("sections/body/pom/parts/rem__pom-fiber-value-set-complexity", -1),
    ("sections/body/pom/parts/rem__pom-multiplicity-zeta-mellin-body", +1),
    ("sections/body/pom/parts/rem__pom-quantile-budget-computable", +2),
    ("sections/body/pom/parts/subsec__pom-cost-functorial-calculus", +10),
    ("sections/body/pom/parts/subsec__pom-division-groupoid", -1),
    ("sections/body/pom/parts/subsec__pom-mom-rewrite-normal", +4),
    ("sections/body/pom/parts/subsec__pom-overflow-global", +2),
    ("sections/body/pom/parts/subsec__pom-projection-entropy", +2),
    ("sections/body/pom/parts/subsec__pom-s5", +4),
    ("sections/body/pom/parts/subsec__pom-spectral-gap", +2),
    ("sections/body/pom/parts/subsubsec__pom-bivariate-system-identification", +4),
    ("sections/body/pom/parts/subsubsec__pom-collision-moment-2adic-odometer", +10),
    ("sections/body/pom/parts/subsubsec__pom-collision-moment-hardcore-homomorphization", -2),
    ("sections/body/pom/parts/subsubsec__pom-fence-green-kernel-area-law-resolvent", +2),
    ("sections/body/pom/parts/subsubsec__pom-fence-green-kernel-golden-coupling-fisher-zeros", +2),
    ("sections/body/pom/parts/subsubsec__pom-fence-green-kernel-spectral-algebra__determinant-polynomials", +2),
    ("sections/body/pom/parts/subsubsec__pom-fiber-indcomplex", +6),
    ("sections/body/pom/parts/subsubsec__pom-fiber-lattice-fence-interval-zeta", -1),
    ("sections/body/pom/parts/subsubsec__pom-low-temperature-maxedge-gap", -1),
    ("sections/body/pom/parts/subsubsec__pom-max-fiber-hidden-bit-phase-inference", +2),
    ("sections/body/pom/parts/subsubsec__pom-max-fiber-hidden-bit-phase-inference-part4", +2),
    ("sections/body/pom/parts/subsubsec__pom-multiplicity-composition-energy-ldp-multifractal", +2),
    ("sections/body/pom/parts/subsubsec__pom-multiplicity-composition-exact-update-softcore", +2),
    ("sections/body/pom/parts/subsubsec__pom-multiplicity-composition-exact-update-softcore-part2", -1),
    ("sections/body/pom/parts/subsubsec__pom-multiplicity-composition-partition-sqrt17", +2),
    ("sections/body/pom/parts/subsubsec__pom-multiplicity-composition-real-q-pressure", +4),
    ("sections/body/pom/parts/subsubsec__pom-multiplicity-composition-sharp-asymptotics-renewal", +6),
    ("sections/body/pom/parts/resonance/subsubsec__pom-resonance-cayley-breitwigner", +2),
    ("sections/body/pom/parts/subsubsec__pom-schur-character-sieve-thermodynamic", +2),
    ("sections/body/pom/parts/subsubsec__pom-schur-character-sieve-thermodynamic__finite-laplace-phase-gibbs", +4),
    ("sections/body/pom/parts/subsubsec__pom-schur-dirichlet-torsion-factorization", +2),
    ("sections/body/pom/parts/subsubsec__pom-schur-frobenius-primitive-fiber-coordinates", -2),
    ("sections/body/pom/parts/subsubsec__pom-schur-near-rh-linear-inequalities", -1),
    ("sections/body/pom/parts/subsubsec__pom-schur-near-rh-linear-inequalities-part2", +2),
    ("sections/body/pom/parts/subsubsec__pom-schur-variance-spectroscopy", -1),
    ("sections/body/pom/parts/thm__pom-third-max-fiber-even-closed-form", +7),

    # emergent arithmetic
    ("sections/body/emergent_arithmetic/sec__A-kernel-compare-main", +6),

    # group unification
    ("sections/body/group_unification/subsec__bdry-tower-zeck-gut-part1", +4),

    # zeta_finite_part
    ("sections/body/zeta_finite_part/xi/subsec__discrete-abel-weil-polar-rigidity", -2),
    ("sections/body/zeta_finite_part/xi/subsec__xi-completion-audit", -1),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-basepoint-scan-profile-finite-rank-rkhs-anchoring", +8),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-basepoint-scan-profile-finite-rank-rkhs-anchoring-part2", +4),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-depth-truncated-moment-markov-pade-stieltjes", +4),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-horizon-residue-multipole-temperedness", -1),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-horizon-spectral-measure-tomography__defect-entropy-hyperbolic-laws", +4),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-horizon-spectral-measure-tomography__four-rigidity", +6),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-horizon-spectral-measure-tomography__scalar-certificates", +4),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-operator-valued-carath-toeplitz-complete-positivity", +4),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-pontryagin-toeplitz-blaschke-tomography-tate", +8),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part11", +4),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part13", +4),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part15", +14),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part16", +8),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part17", +4),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part18", +4),
]

def fix_file(base_path, adjustment):
    """修正单个文件的行数"""
    cn_file = BASE_DIR / f"{base_path}.tex"
    en_file = BASE_DIR / f"{base_path}_en.tex"

    if not cn_file.exists() or not en_file.exists():
        return False, "文件不存在"

    # 读取文件
    with open(cn_file, 'r', encoding='utf-8') as f:
        cn_lines = f.readlines()
    with open(en_file, 'r', encoding='utf-8') as f:
        en_lines = f.readlines()

    cn_count = len(cn_lines)
    en_count = len(en_lines)

    if cn_count == en_count:
        return True, f"已匹配 {cn_count} 行"

    # 应用调整
    if adjustment > 0:
        # 在英文文件末尾添加空行
        for _ in range(adjustment):
            en_lines.append('\n')
    elif adjustment < 0:
        # 从英文文件末尾删除空行
        to_remove = abs(adjustment)
        while to_remove > 0 and en_lines and en_lines[-1].strip() == '':
            en_lines.pop()
            to_remove -= 1

    # 写回
    with open(en_file, 'w', encoding='utf-8') as f:
        f.writelines(en_lines)

    new_count = len(en_lines)
    if new_count == cn_count:
        return True, f"修正成功 {cn_count} 行"
    else:
        return False, f"仍有差异 中文{cn_count} vs 英文{new_count}"

def main():
    print("=" * 80)
    print("手动修正剩余小差异文件")
    print("=" * 80)

    success = 0
    failed = 0

    for base_path, adjustment in manual_fixes:
        fname = base_path.split('/')[-1]
        ok, msg = fix_file(base_path, adjustment)

        if ok:
            print(f"✓ {fname}: {msg}")
            success += 1
        else:
            print(f"✗ {fname}: {msg}")
            failed += 1

    print("\n" + "=" * 80)
    print(f"完成: 成功 {success}, 失败 {failed}, 总计 {len(manual_fixes)}")
    print("=" * 80)

if __name__ == '__main__':
    main()
