#!/usr/bin/env python3
"""分析所有finite-part系列文件的行号差异"""

import os
import subprocess
from pathlib import Path

def count_lines(filepath):
    """统计文件行数"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0

def find_finite_part_files():
    """查找所有finite_part相关文件"""
    base_dir = Path.cwd()
    files_info = []

    # 查找zeta_finite_part目录下的所有文件
    patterns = [
        'sections/body/zeta_finite_part/**/*.tex',
        'sections/body/zeta_finite_part/**/*_en.tex',
    ]

    processed = set()

    for pattern in patterns:
        for zh_file in base_dir.glob(pattern):
            if '_en.tex' in str(zh_file):
                continue

            zh_path = str(zh_file)
            en_path = zh_path.replace('.tex', '_en.tex')

            if zh_path in processed:
                continue
            processed.add(zh_path)

            if os.path.exists(en_path):
                zh_lines = count_lines(zh_path)
                en_lines = count_lines(en_path)
                diff = en_lines - zh_lines

                if diff != 0:
                    rel_zh = os.path.relpath(zh_path, base_dir)
                    rel_en = os.path.relpath(en_path, base_dir)

                    files_info.append({
                        'name': Path(zh_path).stem,
                        'zh_path': rel_zh,
                        'en_path': rel_en,
                        'zh_lines': zh_lines,
                        'en_lines': en_lines,
                        'diff': diff,
                        'diff_pct': abs(diff) / zh_lines * 100 if zh_lines > 0 else 0
                    })

    return files_info

def categorize_files(files_info):
    """按差异大小分类文件"""
    categories = {
        'minor': [],      # <10行
        'medium': [],     # 10-30行
        'large': [],      # 30-70行
        'critical': []    # >70行
    }

    for info in files_info:
        abs_diff = abs(info['diff'])
        if abs_diff < 10:
            categories['minor'].append(info)
        elif abs_diff < 30:
            categories['medium'].append(info)
        elif abs_diff < 70:
            categories['large'].append(info)
        else:
            categories['critical'].append(info)

    return categories

def main():
    print("=" * 80)
    print("Finite-Part系列文件行号差异分析")
    print("=" * 80)
    print()

    files_info = find_finite_part_files()

    if not files_info:
        print("✓ 所有finite-part文件行号已对齐")
        return

    # 按差异绝对值排序
    files_info.sort(key=lambda x: abs(x['diff']))

    categories = categorize_files(files_info)

    print(f"总计发现 {len(files_info)} 个文件需要处理\n")

    # 按类别输出
    for cat_name, cat_label in [
        ('minor', '轻微差异 (<10行)'),
        ('medium', '中等差异 (10-30行)'),
        ('large', '较大差异 (30-70行)'),
        ('critical', '严重差异 (>70行)')
    ]:
        cat_files = categories[cat_name]
        if cat_files:
            print(f"\n{'='*80}")
            print(f"{cat_label} - {len(cat_files)} 个文件")
            print('='*80)

            for i, info in enumerate(cat_files, 1):
                print(f"\n{i}. {info['name']}")
                print(f"   中文: {info['zh_lines']} 行")
                print(f"   英文: {info['en_lines']} 行")
                print(f"   差异: {info['diff']:+d} 行 ({info['diff_pct']:.1f}%)")
                print(f"   路径: {info['zh_path']}")

    # 生成修复建议
    print("\n" + "="*80)
    print("修复建议")
    print("="*80)

    if categories['critical']:
        print(f"\n优先级1 (严重): {len(categories['critical'])} 个文件")
        print("   建议：完整内容审查，可能需要大段翻译或重构")
        for info in categories['critical'][:5]:
            print(f"   - {info['name']} (差异: {info['diff']:+d})")

    if categories['large']:
        print(f"\n优先级2 (较大): {len(categories['large'])} 个文件")
        print("   建议：内容完整性检查，补充缺失的定理/证明")
        for info in categories['large'][:5]:
            print(f"   - {info['name']} (差异: {info['diff']:+d})")

    if categories['medium']:
        print(f"\n优先级3 (中等): {len(categories['medium'])} 个文件")
        print("   建议：补充缺失的推论或证明步骤")
        for info in categories['medium'][:5]:
            print(f"   - {info['name']} (差异: {info['diff']:+d})")

    if categories['minor']:
        print(f"\n优先级4 (轻微): {len(categories['minor'])} 个文件")
        print("   建议：格式调整和空行规范化")
        for info in categories['minor'][:5]:
            print(f"   - {info['name']} (差异: {info['diff']:+d})")

    # 保存详细报告
    report_file = 'finite_part_alignment_report.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("Finite-Part系列文件行号差异详细报告\n")
        f.write("="*80 + "\n\n")

        for info in files_info:
            f.write(f"文件: {info['name']}\n")
            f.write(f"  中文路径: {info['zh_path']}\n")
            f.write(f"  英文路径: {info['en_path']}\n")
            f.write(f"  中文行数: {info['zh_lines']}\n")
            f.write(f"  英文行数: {info['en_lines']}\n")
            f.write(f"  差异: {info['diff']:+d} 行 ({info['diff_pct']:.1f}%)\n")
            f.write("\n")

    print(f"\n详细报告已保存至: {report_file}")

if __name__ == '__main__':
    main()
