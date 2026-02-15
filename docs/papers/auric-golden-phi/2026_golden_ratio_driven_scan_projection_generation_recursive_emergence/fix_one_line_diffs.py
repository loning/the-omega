#!/usr/bin/env python3
"""
自动修正1行差异的文件
通过对比找到多余或缺失的空行
"""

import os
import difflib
from pathlib import Path

BASE_DIR = Path(__file__).parent

# 所有1行差异的文件
one_line_diffs = [
    # 英文多1行 (需要删除)
    "sections/appendix/fold_multiplicity/rem__fold-zero-sparse-necessity",
    "sections/appendix/operator_algebra/app__op-algebra",
    "sections/appendix/operator_algebra/subsubsec__op_algebra_jones_scalar_twirl_cost_renyi_flatness",
    "sections/appendix/kronecker/app__kronecker-discrepancy",
    "sections/body/pom/parts/cor__pom-fiber-modq-pisano-invariant",
    "sections/body/pom/parts/rem__pom-fiber-value-set-complexity",
    "sections/body/pom/parts/subsec__pom-division-groupoid",
    "sections/body/pom/parts/subsubsec__pom-fiber-lattice-fence-interval-zeta",
    "sections/body/pom/parts/subsubsec__pom-low-temperature-maxedge-gap",
    "sections/body/pom/parts/subsubsec__pom-multiplicity-composition-exact-update-softcore-part2",
    "sections/body/pom/parts/subsubsec__pom-schur-frobenius-primitive-fiber-coordinates",
    "sections/body/pom/parts/subsubsec__pom-schur-near-rh-linear-inequalities",
    "sections/body/pom/parts/subsubsec__pom-schur-variance-spectroscopy",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-basepoint-scan-profile-finite-rank-rkhs-anchoring-part2",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-depth-truncated-moment-markov-pade-stieltjes",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-operator-valued-carath-toeplitz-complete-positivity",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part11",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part13",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part17",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-time-protocol-conclusions-part18",
    "sections/body/zeta_finite_part/xi/subsubsec__xi-horizon-spectral-measure-tomography__four-rigidity",
]

def fix_one_line_diff(base_path):
    """修正1行差异的文件"""
    cn_file = BASE_DIR / f"{base_path}.tex"
    en_file = BASE_DIR / f"{base_path}_en.tex"

    if not cn_file.exists() or not en_file.exists():
        return False, "文件不存在"

    with open(cn_file, 'r', encoding='utf-8') as f:
        cn_lines = f.readlines()
    with open(en_file, 'r', encoding='utf-8') as f:
        en_lines = f.readlines()

    cn_count = len(cn_lines)
    en_count = len(en_lines)

    if cn_count == en_count:
        return True, f"已匹配 {cn_count} 行"

    diff = en_count - cn_count

    if diff == 1:
        # 英文多1行，找到并删除多余的空行
        # 使用difflib查找差异
        differ = difflib.Differ()
        diff_lines = list(differ.compare(
            [l.rstrip('\n') for l in cn_lines],
            [l.rstrip('\n') for l in en_lines]
        ))

        # 找到第一个多余的空行
        cn_idx = 0
        en_idx = 0
        for d_line in diff_lines:
            if d_line.startswith('  '):  # 相同
                cn_idx += 1
                en_idx += 1
            elif d_line.startswith('- '):  # 中文有，英文无
                cn_idx += 1
            elif d_line.startswith('+ '):  # 英文有，中文无
                # 这是多余的行
                if d_line[2:].strip() == '':
                    # 找到多余空行，删除它
                    del en_lines[en_idx]
                    break
                en_idx += 1

        # 如果没有找到中间的空行，删除末尾空行
        if len(en_lines) > cn_count:
            while len(en_lines) > cn_count and en_lines[-1].strip() == '':
                en_lines.pop()

        with open(en_file, 'w', encoding='utf-8') as f:
            f.writelines(en_lines)

        return len(en_lines) == cn_count, f"修正成功 {cn_count} 行" if len(en_lines) == cn_count else f"仍有差异"

    elif diff == -1:
        # 中文多1行，在英文文件适当位置添加空行
        en_lines.append('\n')
        with open(en_file, 'w', encoding='utf-8') as f:
            f.writelines(en_lines)
        return True, f"修正成功 {cn_count} 行"

    else:
        return False, f"差异{diff}行，不是1行"

def main():
    print("=" * 80)
    print("修正1行差异文件")
    print("=" * 80)

    success = 0
    failed = 0

    for base_path in one_line_diffs:
        fname = base_path.split('/')[-1]
        ok, msg = fix_one_line_diff(base_path)

        if ok:
            print(f"✓ {fname}: {msg}")
            success += 1
        else:
            print(f"✗ {fname}: {msg}")
            failed += 1

    print("\n" + "=" * 80)
    print(f"完成: 成功 {success}, 失败 {failed}, 总计 {len(one_line_diffs)}")
    print("=" * 80)

if __name__ == '__main__':
    main()
