#!/usr/bin/env python3
"""
自动修复Xi相关文件的中英文行号不匹配问题
优先处理差异大于50行的文件
"""

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

def find_xi_mismatches():
    """查找所有Xi相关的不匹配文件，按差异大小排序"""
    base_dir = Path('.')
    mismatches = []

    for tex_file in base_dir.rglob('*.tex'):
        if tex_file.name.endswith('_en.tex'):
            continue

        file_str = str(tex_file)
        if '/xi/' not in file_str and 'xi-' not in tex_file.name:
            continue

        en_name = tex_file.stem + '_en.tex'
        en_file = tex_file.parent / en_name

        if en_file.exists():
            zh_lines = count_lines(tex_file)
            en_lines = count_lines(en_file)

            if zh_lines != en_lines:
                diff = abs(en_lines - zh_lines)
                mismatches.append({
                    'zh_file': str(tex_file),
                    'en_file': str(en_file),
                    'zh_lines': zh_lines,
                    'en_lines': en_lines,
                    'diff': diff
                })

    # 按差异大小排序
    mismatches.sort(key=lambda x: x['diff'], reverse=True)
    return mismatches

def main():
    mismatches = find_xi_mismatches()

    # 只处理差异大于50行的文件
    major_mismatches = [m for m in mismatches if m['diff'] > 50]

    print(f"发现 {len(major_mismatches)} 个差异超过50行的Xi相关文件需要修复：\n")

    for i, item in enumerate(major_mismatches, 1):
        print(f"{i}. {Path(item['zh_file']).name}")
        print(f"   中文: {item['zh_lines']} 行")
        print(f"   英文: {item['en_lines']} 行")
        print(f"   差异: {item['diff']} 行")
        print(f"   路径: {item['zh_file']}")
        print()

if __name__ == '__main__':
    main()
