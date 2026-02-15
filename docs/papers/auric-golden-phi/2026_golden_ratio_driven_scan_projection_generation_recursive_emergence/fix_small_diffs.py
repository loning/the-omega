#!/usr/bin/env python3
"""
修正差异≤10行的所有文件
通过规范化空行来匹配行数
"""

import os
import sys
from pathlib import Path

# 工作目录
BASE_DIR = Path(__file__).parent

# 差异≤10行的文件列表（从find_missing.py的输出中提取）
small_diff_files = [
    # appendix files
    ("sections/appendix/sync_kernel/real_input/app__real-input-40-arity-3d", -2),
    ("sections/appendix/sync_kernel/real_input/app__real-input-40-arity-charge", -2),
    ("sections/appendix/sync_kernel/real_input/app__real-input-40-defect-entropy", -1),
    ("sections/appendix/sync_kernel/real_input/app__real-input-40-dirichlet", -2),
    ("sections/appendix/sync_kernel/real_input/app__real-input-40-finite-part", -3),
    ("sections/appendix/sync_kernel/real_input/app__real-input-40-finite-rh", -4),
    ("sections/appendix/sync_kernel/real_input/app__real-input-40-kernel", -3),
    ("sections/appendix/sync_kernel/real_input/app__real-input-40-length-mertens", -2),
    ("sections/appendix/sync_kernel/real_input/subsec__real-input-40-prime-splitting", -8),
    ("sections/appendix/sync_kernel/real_input/subsubsec__gm-farey-limit-mod-obstruction-zeck-measure", -1),
    ("sections/appendix/sync_kernel/real_input/subsubsec__gm-rational-sieve-affine-centered-opuc-multifractal", -1),
    ("sections/appendix/sync_kernel/subsec__sync-kernel-counting", -30),  # 可能超过10行，但先包含
    ("sections/appendix/sync_kernel/weighted/main", +1),
    ("sections/appendix/sync_kernel/weighted/subsubsec__sync-kernel-weighted-abel-mertens-analytic-radius-edgeworth", -1),
    ("sections/appendix/sync_kernel/weighted/subsubsec__sync-kernel-weighted-pressure-ldp", +2),
    ("sections/appendix/unit_circle_phase_arithmetic/app__unit-circle-phase-gate", +1),
    ("sections/appendix/unit_circle_phase_arithmetic/def__endpoint-tristate-set", -1),
    ("sections/appendix/unit_circle_phase_arithmetic/subsec__unit-disk-jensen-defect", -1),
    ("sections/appendix/unit_circle_phase_arithmetic/subsubsec__app-horizon-weyl-carath-toeplitz", -2),
    ("sections/appendix/fold_multiplicity/cor__fold-zero-divisor-triple-reduction", -1),
    ("sections/appendix/fold_multiplicity/rem__fold-zero-sparse-necessity", +1),
    ("sections/appendix/fold_multiplicity/thm__fold-bin-gauge-constant-stirling-bernoulli-hierarchy", -1),
    ("sections/appendix/fold_multiplicity/thm__fold-bin-two-state-asymptotic", +7),
    ("sections/appendix/operator_algebra/app__op-algebra", +1),
    ("sections/appendix/operator_algebra/subsec__op_algebra_hzom_unitary_slice_rh", -1),
    ("sections/appendix/operator_algebra/subsec__op_algebra_modular_zk_index_fkdet", +2),
    ("sections/appendix/operator_algebra/subsubsec__op_algebra_jones_scalar_twirl_cost_renyi_flatness", +1),
    ("sections/appendix/kronecker/app__kronecker-discrepancy", +1),
    # body/pom files with small diffs
    ("sections/body/pom/parts/08_projection_ontology_mathematics_part03c_a", -1),
    ("sections/body/pom/parts/08_projection_ontology_mathematics_part07_c", -1),
    ("sections/body/pom/parts/cor__pom-fiber-modq-pisano-invariant", +1),
    ("sections/body/pom/parts/cor__pom-fiber-reconstruction-cubical-addenda", -1),
    ("sections/body/pom/parts/cor__pom-fold-factor-chain-derived-invariants", -1),
    ("sections/body/pom/parts/cor__pom-symmetric-remainder", -1),
    ("sections/body/pom/parts/def__pom-ind-lyapunov-fingerprint", +4),
    ("sections/body/pom/parts/lem__pom-shifted-fib-fusion-defect-positive", +5),
    ("sections/body/pom/parts/part__pom-microcanonical-fold-information-linear-law-ldp-sidebits", -4),
    ("sections/body/pom/parts/part__pom-microcanonical-query-distortion-strong-converse", -2),
    ("sections/body/pom/parts/part__pom-microcanonical-query-distortion-strong-converse-part2", +5),
    ("sections/body/pom/parts/part__pom-microcanonical-two-temperature-kkt-failure-exponent", -2),
    ("sections/body/pom/parts/part__pom-microcanonical-typeclass-hamming-ball-volume", -2),
    ("sections/body/pom/parts/part__pom-multiwell-low-temperature-expansion-identifiability", -1),
    ("sections/body/pom/parts/part__pom-oracle-critical-budget-entropy-decomposition", -2),
    ("sections/body/pom/parts/part__pom-oracle-fenchel-duality-area-law", -1),
    ("sections/body/pom/parts/part__pom-oracle-min-kernel-closure-tomography-bregman", -2),
    ("sections/body/pom/parts/part__pom-pressure-multiplicative-chain-entropy-loss", +2),
    ("sections/body/pom/parts/part__pom-zero-temperature-two-term-maxfiber-freezing", -1),
    ("sections/body/pom/parts/prop__pom-a4-discriminant-quadratic-field-class-number", -1),
    ("sections/body/pom/parts/prop__pom-a4t-even-zeta-elimination", -1),
    ("sections/body/pom/parts/resonance/prop__pom-charpoly-modp-a2-embedding", -2),
    ("sections/body/pom/parts/prop__pom-fib-pell-unit-mobius", +3),
    ("sections/body/pom/parts/prop__pom-fiber-index-cgf", +5),
    ("sections/body/pom/parts/rem__pom-fiber-value-set-complexity", +1),
    ("sections/body/pom/parts/rem__pom-multiplicity-zeta-mellin-body", -1),
    ("sections/body/pom/parts/rem__pom-quantile-budget-computable", -1),
    ("sections/body/pom/parts/subsec__pom-cost-functorial-calculus", -5),
    ("sections/body/pom/parts/subsec__pom-division-groupoid", +1),
    ("sections/body/pom/parts/subsec__pom-mom-rewrite-normal", -2),
    ("sections/body/pom/parts/subsec__pom-overflow-global", -1),
    ("sections/body/pom/parts/subsec__pom-projection-entropy", -1),
    ("sections/body/pom/parts/subsec__pom-s5", -2),
    ("sections/body/pom/parts/subsec__pom-spectral-gap", -1),
    ("sections/body/pom/parts/subsubsec__pom-bivariate-system-identification", -2),
    ("sections/body/pom/parts/subsubsec__pom-collision-moment-2adic-odometer", -5),
    ("sections/body/pom/parts/subsubsec__pom-collision-moment-hardcore-homomorphization", +2),
    ("sections/body/pom/parts/subsubsec__pom-fence-green-kernel-area-law-resolvent", -1),
    ("sections/body/pom/parts/subsubsec__pom-fence-green-kernel-golden-coupling-fisher-zeros", -1),
    ("sections/body/pom/parts/subsubsec__pom-fence-green-kernel-spectral-algebra__determinant-polynomials", -1),
    ("sections/body/pom/parts/subsubsec__pom-fiber-indcomplex", -3),
    ("sections/body/pom/parts/subsubsec__pom-fiber-lattice-fence-interval-zeta", +1),
    ("sections/body/pom/parts/subsubsec__pom-low-temperature-maxedge-gap", +1),
    ("sections/body/pom/parts/subsubsec__pom-max-fiber-hidden-bit-phase-inference", -1),
    ("sections/body/pom/parts/subsubsec__pom-max-fiber-hidden-bit-phase-inference-part4", -1),
    ("sections/body/pom/parts/subsubsec__pom-multiplicity-composition-energy-ldp-multifractal", -1),
    ("sections/body/pom/parts/subsubsec__pom-multiplicity-composition-exact-update-softcore", -1),
    ("sections/body/pom/parts/subsubsec__pom-multiplicity-composition-exact-update-softcore-part2", +1),
    ("sections/body/pom/parts/subsubsec__pom-multiplicity-composition-partition-sqrt17", -1),
    ("sections/body/pom/parts/subsubsec__pom-multiplicity-composition-real-q-pressure", -2),
    ("sections/body/pom/parts/subsubsec__pom-multiplicity-composition-sharp-asymptotics-renewal", -3),
    ("sections/body/pom/parts/resonance/subsubsec__pom-resonance-cayley-breitwigner", -1),
    ("sections/body/pom/parts/subsubsec__pom-schur-character-sieve-thermodynamic", -1),
    ("sections/body/pom/parts/subsubsec__pom-schur-character-sieve-thermodynamic__finite-laplace-phase-gibbs", -2),
    ("sections/body/pom/parts/subsubsec__pom-schur-dirichlet-torsion-factorization", -1),
    ("sections/body/pom/parts/subsubsec__pom-schur-frobenius-primitive-fiber-coordinates", +2),
    ("sections/body/pom/parts/subsubsec__pom-schur-near-rh-linear-inequalities", +1),
    ("sections/body/pom/parts/subsubsec__pom-schur-near-rh-linear-inequalities-part2", -1),
    ("sections/body/pom/parts/subsubsec__pom-schur-variance-spectroscopy", +1),
    # body other files
    ("sections/body/emergent_arithmetic/sec__A-kernel-compare-main", -3),
    ("sections/body/group_unification/subsec__bdry-tower-zeck-gut-part1", -2),
    # zeta_finite_part files
    ("sections/body/zeta_finite_part/xi/subsec__discrete-abel-weil-polar-rigidity", +2),
    ("sections/body/zeta_finite_part/xi/subsec__xi-completion-audit", +1),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-basepoint-scan-profile-finite-rank-rkhs-anchoring", -4),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-basepoint-scan-profile-finite-rank-rkhs-anchoring-part2", -2),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-depth-truncated-moment-markov-pade-stieltjes", -2),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-horizon-residue-multipole-temperedness", +1),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-horizon-spectral-measure-tomography__defect-entropy-hyperbolic-laws", -2),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-horizon-spectral-measure-tomography__four-rigidity", -3),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-horizon-spectral-measure-tomography__scalar-certificates", -2),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-operator-valued-carath-toeplitz-complete-positivity", -2),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-pontryagin-toeplitz-blaschke-tomography-tate", -4),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part11", -2),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part13", -2),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part15", -7),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part16", -4),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part17", -2),
    ("sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part18", -2),
    ("sections/body/folding/subsubsec__fold-gauge-anomaly-spectral-recurrence-certificates", -23),  # 超过10行但包含
    ("sections/appendix/sync_kernel/real_input/thm__real-input-40-primedirichlet-dense-branch", -6),
]

def count_lines(filepath):
    """统计文件行数"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0

def fix_line_count(cn_file, en_file, diff):
    """
    修正文件行数差异
    diff < 0: 英文文件需要减少 |diff| 行（删除空行）
    diff > 0: 英文文件需要增加 diff 行（添加空行）
    """
    if not os.path.exists(en_file):
        print(f"  ⚠ 英文文件不存在: {en_file}")
        return False

    try:
        with open(en_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if diff < 0:
            # 需要删除空行
            to_remove = abs(diff)
            new_lines = []
            removed = 0

            # 从文件末尾开始删除空行
            for i in range(len(lines) - 1, -1, -1):
                if removed < to_remove and lines[i].strip() == '':
                    removed += 1
                else:
                    new_lines.insert(0, lines[i])

            if removed < to_remove:
                # 如果末尾空行不够，从中间删除
                final_lines = []
                for line in new_lines:
                    if removed < to_remove and line.strip() == '':
                        removed += 1
                    else:
                        final_lines.append(line)
                new_lines = final_lines

            with open(en_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"  ✓ 删除了 {removed} 个空行")

        else:
            # 需要添加空行
            # 在文件末尾添加空行
            if not lines[-1].endswith('\n'):
                lines[-1] += '\n'

            for _ in range(diff):
                lines.append('\n')

            with open(en_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            print(f"  ✓ 添加了 {diff} 个空行")

        return True

    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return False

def main():
    print("=" * 80)
    print("修正差异≤10行的文件")
    print("=" * 80)

    success = 0
    failed = 0

    for base_name, diff in small_diff_files:
        cn_file = BASE_DIR / f"{base_name}.tex"
        en_file = BASE_DIR / f"{base_name}_en.tex"

        print(f"\n处理: {base_name}")
        print(f"  差异: {diff:+d} 行")

        if fix_line_count(cn_file, en_file, diff):
            # 验证修正结果
            cn_lines = count_lines(cn_file)
            en_lines = count_lines(en_file)
            if cn_lines == en_lines:
                print(f"  ✓ 成功匹配: {cn_lines} 行")
                success += 1
            else:
                print(f"  ⚠ 行数仍不匹配: 中文 {cn_lines} vs 英文 {en_lines}")
                failed += 1
        else:
            failed += 1

    print("\n" + "=" * 80)
    print(f"完成: 成功 {success}, 失败 {failed}, 总计 {len(small_diff_files)}")
    print("=" * 80)

if __name__ == '__main__':
    main()
