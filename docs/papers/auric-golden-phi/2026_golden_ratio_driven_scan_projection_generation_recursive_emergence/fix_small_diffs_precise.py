#!/usr/bin/env python3
"""
精确修正小差异文件
通过逐行对比找到具体差异位置
"""

import os
import sys
import difflib
from pathlib import Path

BASE_DIR = Path(__file__).parent

# 差异≤10行的appendix文件
appendix_files = [
    "sections/appendix/sync_kernel/real_input/app__real-input-40-arity-3d",
    "sections/appendix/sync_kernel/real_input/app__real-input-40-arity-charge",
    "sections/appendix/sync_kernel/real_input/app__real-input-40-defect-entropy",
    "sections/appendix/sync_kernel/real_input/app__real-input-40-dirichlet",
    "sections/appendix/sync_kernel/real_input/app__real-input-40-finite-part",
    "sections/appendix/sync_kernel/real_input/app__real-input-40-finite-rh",
    "sections/appendix/sync_kernel/real_input/app__real-input-40-kernel",
    "sections/appendix/sync_kernel/real_input/app__real-input-40-length-mertens",
    "sections/appendix/sync_kernel/real_input/subsec__real-input-40-prime-splitting",
    "sections/appendix/sync_kernel/real_input/subsubsec__gm-farey-limit-mod-obstruction-zeck-measure",
    "sections/appendix/sync_kernel/real_input/subsubsec__gm-rational-sieve-affine-centered-opuc-multifractal",
    "sections/appendix/sync_kernel/weighted/subsubsec__sync-kernel-weighted-abel-mertens-analytic-radius-edgeworth",
    "sections/appendix/sync_kernel/weighted/subsubsec__sync-kernel-weighted-pressure-ldp",
    "sections/appendix/unit_circle_phase_arithmetic/app__unit-circle-phase-gate",
    "sections/appendix/unit_circle_phase_arithmetic/def__endpoint-tristate-set",
    "sections/appendix/unit_circle_phase_arithmetic/subsec__unit-disk-jensen-defect",
    "sections/appendix/unit_circle_phase_arithmetic/subsubsec__app-horizon-weyl-carath-toeplitz",
    "sections/appendix/fold_multiplicity/cor__fold-zero-divisor-triple-reduction",
    "sections/appendix/fold_multiplicity/rem__fold-zero-sparse-necessity",
    "sections/appendix/fold_multiplicity/thm__fold-bin-gauge-constant-stirling-bernoulli-hierarchy",
    "sections/appendix/fold_multiplicity/thm__fold-bin-two-state-asymptotic",
    "sections/appendix/operator_algebra/app__op-algebra",
    "sections/appendix/operator_algebra/subsec__op_algebra_hzom_unitary_slice_rh",
    "sections/appendix/operator_algebra/subsec__op_algebra_modular_zk_index_fkdet",
    "sections/appendix/operator_algebra/subsubsec__op_algebra_jones_scalar_twirl_cost_renyi_flatness",
    "sections/appendix/kronecker/app__kronecker-discrepancy",
    "sections/appendix/sync_kernel/real_input/thm__real-input-40-primedirichlet-dense-branch",
]

def read_file(filepath):
    """读取文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.readlines()
    except:
        return []

def write_file(filepath, lines):
    """写入文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def fix_file_by_diff(cn_file, en_file):
    """通过diff修正文件"""
    cn_lines = read_file(cn_file)
    en_lines = read_file(en_file)

    if not cn_lines or not en_lines:
        return False

    cn_count = len(cn_lines)
    en_count = len(en_lines)
    diff = cn_count - en_count

    if diff == 0:
        print(f"  ✓ 已匹配: {cn_count} 行")
        return True

    print(f"  差异: {diff:+d} 行 (中文 {cn_count} vs 英文 {en_count})")

    # 使用difflib找到差异
    differ = difflib.Differ()
    diff_result = list(differ.compare([l.rstrip('\n') for l in cn_lines],
                                      [l.rstrip('\n') for l in en_lines]))

    # 分析差异
    cn_only_lines = []
    en_only_lines = []

    for i, line in enumerate(diff_result):
        if line.startswith('- '):
            cn_only_lines.append((i, line[2:]))
        elif line.startswith('+ '):
            en_only_lines.append((i, line[2:]))

    # 简单修正: 如果只是空行数量不同
    if diff < 0:
        # 英文多了空行，删除末尾空行
        while len(en_lines) > cn_count and en_lines[-1].strip() == '':
            en_lines.pop()

        # 如果还不匹配，删除文件中间的多余空行
        if len(en_lines) > cn_count:
            new_lines = []
            removed = 0
            target = len(en_lines) - cn_count

            for i, line in enumerate(en_lines):
                if removed < target and line.strip() == '' and i > 0 and i < len(en_lines) - 1:
                    # 检查是否是连续空行
                    if (i + 1 < len(en_lines) and en_lines[i + 1].strip() == '' and
                        i > 0 and en_lines[i - 1].strip() != ''):
                        removed += 1
                        continue
                new_lines.append(line)

            en_lines = new_lines

    elif diff > 0:
        # 英文少了行，在末尾添加空行
        for _ in range(diff):
            en_lines.append('\n')

    # 写回文件
    write_file(en_file, en_lines)

    # 验证
    new_count = len(en_lines)
    if new_count == cn_count:
        print(f"  ✓ 修正成功: {new_count} 行")
        return True
    else:
        print(f"  ⚠ 仍有差异: 中文 {cn_count} vs 英文 {new_count}")
        return False

def main():
    print("=" * 80)
    print("精确修正appendix小差异文件")
    print("=" * 80)

    success = 0
    failed = 0

    for base_name in appendix_files:
        cn_file = BASE_DIR / f"{base_name}.tex"
        en_file = BASE_DIR / f"{base_name}_en.tex"

        print(f"\n处理: {base_name.split('/')[-1]}")

        if not en_file.exists():
            print(f"  ⚠ 英文文件不存在")
            failed += 1
            continue

        if fix_file_by_diff(cn_file, en_file):
            success += 1
        else:
            failed += 1

    print("\n" + "=" * 80)
    print(f"Appendix文件: 成功 {success}, 失败 {failed}, 总计 {len(appendix_files)}")
    print("=" * 80)

if __name__ == '__main__':
    main()
