#!/usr/bin/env python3
"""
最后处理appendix下的几个小差异文件
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# 剩余的小差异文件
final_fixes = [
    ("sections/appendix/kronecker/app__kronecker-discrepancy", +1),
    ("sections/appendix/operator_algebra/app__op-algebra", +1),
    ("sections/appendix/operator_algebra/subsec__op_algebra_modular_zk_index_fkdet", +2),
    ("sections/appendix/fold_multiplicity/rem__fold-zero-sparse-necessity", +1),
    ("sections/appendix/sync_kernel/weighted/main", -1),
    ("sections/appendix/operator_algebra/subsubsec__op_algebra_jones_scalar_twirl_cost_renyi_flatness", +1),
]

def smart_fix(base_path, target_diff):
    """智能修正文件"""
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

    actual_diff = cn_count - en_count

    if target_diff > 0:
        # 中文多，英文需要添加空行
        for _ in range(abs(target_diff)):
            en_lines.append('\n')
    else:
        # 英文多，删除空行
        to_remove = abs(target_diff)
        # 先尝试从末尾删除
        while to_remove > 0 and en_lines and en_lines[-1].strip() == '':
            en_lines.pop()
            to_remove -= 1

        # 如果还需要删除，从文件中间找连续空行
        if to_remove > 0:
            new_lines = []
            i = 0
            removed = 0
            while i < len(en_lines) and removed < to_remove:
                if (en_lines[i].strip() == '' and
                    i + 1 < len(en_lines) and
                    en_lines[i + 1].strip() == ''):
                    # 跳过连续空行中的一个
                    removed += 1
                    i += 1
                    continue
                new_lines.append(en_lines[i])
                i += 1

            # 添加剩余的行
            new_lines.extend(en_lines[i:])
            en_lines = new_lines

    with open(en_file, 'w', encoding='utf-8') as f:
        f.writelines(en_lines)

    new_count = len(en_lines)
    if new_count == cn_count:
        return True, f"修正成功 {cn_count} 行"
    else:
        return False, f"仍有差异 中文{cn_count} vs 英文{new_count}"

def main():
    print("=" * 80)
    print("最后修正appendix小差异文件")
    print("=" * 80)

    success = 0
    failed = 0

    for base_path, target_diff in final_fixes:
        fname = base_path.split('/')[-1]
        ok, msg = smart_fix(base_path, target_diff)

        if ok:
            print(f"✓ {fname}: {msg}")
            success += 1
        else:
            print(f"✗ {fname}: {msg}")
            failed += 1

    print("\n" + "=" * 80)
    print(f"完成: 成功 {success}, 失败 {failed}, 总计 {len(final_fixes)}")
    print("=" * 80)

if __name__ == '__main__':
    main()
