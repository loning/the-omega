#!/usr/bin/env python3
"""批量对齐finite-part系列文件的辅助脚本"""

import os
import sys
from pathlib import Path

# 待处理文件列表（按差异从大到小排序）
PRIORITY_FILES = [
    # 优先级1：严重差异 (>70行)
    {
        'name': 'subsec__xi-pw-type-safety-null',
        'zh_lines': 598,
        'en_lines': 175,
        'diff': -423,
        'path': 'sections/body/zeta_finite_part/xi',
        'priority': 1,
        'status': 'pending'
    },
    {
        'name': 'subsubsec__selfdual-blaschke-defect-fixed-slice',
        'zh_lines': 410,
        'en_lines': 51,
        'diff': -359,
        'path': 'sections/body/zeta_finite_part/xi',
        'priority': 1,
        'status': 'pending'
    },
    {
        'name': 'subsec__reduced-determinant-residue',
        'zh_lines': 359,
        'en_lines': 87,
        'diff': -272,
        'path': 'sections/body/zeta_finite_part/finite_part',
        'priority': 1,
        'status': 'pending'
    },
    {
        'name': 'subsubsec__xi-time-protocol-conclusions-part7',
        'zh_lines': 487,
        'en_lines': 254,
        'diff': -233,
        'path': 'sections/body/zeta_finite_part/xi',
        'priority': 1,
        'status': 'pending'
    },
    {
        'name': 'subsec__real-input-40-geodesic-prime-shadow',
        'zh_lines': 394,
        'en_lines': 192,
        'diff': -202,
        'path': 'sections/body/zeta_finite_part/finite_part',
        'priority': 1,
        'status': 'pending'
    },
    {
        'name': 'subsubsec__xi-time-protocol-conclusions-part6',
        'zh_lines': 357,
        'en_lines': 214,
        'diff': -143,
        'path': 'sections/body/zeta_finite_part/xi',
        'priority': 1,
        'status': 'pending'
    },

    # 优先级2：较大差异 (30-70行)
    {
        'name': 'subsubsec__xi-ramanujan-horizon-ledger-framework',
        'zh_lines': 261,
        'en_lines': 192,
        'diff': -69,
        'path': 'sections/body/zeta_finite_part/xi',
        'priority': 2,
        'status': 'pending'
    },
    {
        'name': 'subsec__xi-near1-diffusive',
        'zh_lines': 174,
        'en_lines': 119,
        'diff': -55,
        'path': 'sections/body/zeta_finite_part/xi',
        'priority': 2,
        'status': 'pending'
    },
    {
        'name': 'subsubsec__xi-time-protocol-conclusions-part2',
        'zh_lines': 418,
        'en_lines': 366,
        'diff': -52,
        'path': 'sections/body/zeta_finite_part/xi',
        'priority': 2,
        'status': 'pending'
    },
    {
        'name': 'subsubsec__xi-endpoint-tomography-radial-profile',
        'zh_lines': 193,
        'en_lines': 155,
        'diff': -38,
        'path': 'sections/body/zeta_finite_part/xi',
        'priority': 2,
        'status': 'pending'
    },
    {
        'name': 'subsubsec__ramanujan-phase-lift-symmetry',
        'zh_lines': 594,
        'en_lines': 557,
        'diff': -37,
        'path': 'sections/body/zeta_finite_part/xi',
        'priority': 2,
        'status': 'pending'
    },
]

def count_lines(filepath):
    """统计文件行数"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0

def check_file_status(base_dir, file_info):
    """检查文件当前状态"""
    zh_file = os.path.join(base_dir, file_info['path'], f"{file_info['name']}.tex")
    en_file = os.path.join(base_dir, file_info['path'], f"{file_info['name']}_en.tex")

    if not os.path.exists(zh_file) or not os.path.exists(en_file):
        return None, None, 'missing'

    zh_lines = count_lines(zh_file)
    en_lines = count_lines(en_file)

    if zh_lines == en_lines:
        return zh_lines, en_lines, 'aligned'
    else:
        return zh_lines, en_lines, 'misaligned'

def generate_alignment_report(base_dir):
    """生成对齐报告"""
    print("=" * 80)
    print("Finite-Part文件对齐状态报告")
    print("=" * 80)
    print()

    aligned = []
    misaligned = []
    missing = []

    for file_info in PRIORITY_FILES:
        zh_lines, en_lines, status = check_file_status(base_dir, file_info)

        if status == 'aligned':
            aligned.append({**file_info, 'current_zh': zh_lines, 'current_en': en_lines})
        elif status == 'misaligned':
            misaligned.append({**file_info, 'current_zh': zh_lines, 'current_en': en_lines})
        else:
            missing.append(file_info)

    if aligned:
        print(f"\n✅ 已对齐文件 ({len(aligned)}个):")
        for f in aligned:
            print(f"   - {f['name']} ({f['current_zh']}行)")

    if misaligned:
        print(f"\n❌ 仍需对齐文件 ({len(misaligned)}个):")
        for f in misaligned:
            diff = f['current_en'] - f['current_zh']
            print(f"   - {f['name']}")
            print(f"     中文: {f['current_zh']}行 | 英文: {f['current_en']}行 | 差异: {diff:+d}行")
            print(f"     优先级: {f['priority']} | 路径: {f['path']}")

    if missing:
        print(f"\n⚠️  文件缺失 ({len(missing)}个):")
        for f in missing:
            print(f"   - {f['name']}")

    print()
    print("=" * 80)
    print(f"总计: {len(PRIORITY_FILES)}个文件")
    print(f"已对齐: {len(aligned)}个 ({len(aligned)/len(PRIORITY_FILES)*100:.1f}%)")
    print(f"待处理: {len(misaligned)}个 ({len(misaligned)/len(PRIORITY_FILES)*100:.1f}%)")
    print("=" * 80)

    return aligned, misaligned, missing

def generate_todo_list(misaligned):
    """生成待办清单"""
    print("\n处理建议:")
    print("-" * 80)

    # 按优先级分组
    priority1 = [f for f in misaligned if f['priority'] == 1]
    priority2 = [f for f in misaligned if f['priority'] == 2]

    if priority1:
        print(f"\n优先级1 (严重差异, {len(priority1)}个文件):")
        for i, f in enumerate(priority1, 1):
            diff = abs(f['current_en'] - f['current_zh'])
            print(f"{i}. {f['name']}")
            print(f"   需补充: 约{diff}行内容")
            print(f"   建议: 完整内容审查，大段翻译补充")

    if priority2:
        print(f"\n优先级2 (较大差异, {len(priority2)}个文件):")
        for i, f in enumerate(priority2, 1):
            diff = abs(f['current_en'] - f['current_zh'])
            print(f"{i}. {f['name']}")
            print(f"   需补充: 约{diff}行内容")
            print(f"   建议: 内容完整性检查，补充缺失定理/证明")

def main():
    base_dir = Path.cwd()

    # 生成报告
    aligned, misaligned, missing = generate_alignment_report(base_dir)

    # 生成待办清单
    if misaligned:
        generate_todo_list(misaligned)
    else:
        print("\n🎉 所有文件已完全对齐！")

if __name__ == '__main__':
    main()
