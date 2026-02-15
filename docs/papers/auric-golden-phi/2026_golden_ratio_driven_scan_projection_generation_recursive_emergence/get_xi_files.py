#!/usr/bin/env python3
"""获取所有Xi协议相关的行号不匹配文件"""

import os
import re
from pathlib import Path

def count_lines(filepath):
    """统计文件行数"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0

def find_file_pairs():
    """查找所有中英文文件对"""
    base_dir = Path('.')
    chinese_files = {}

    # 查找所有.tex文件（非_en结尾）
    for tex_file in base_dir.rglob('*.tex'):
        if tex_file.name.endswith('_en.tex'):
            continue

        # 检查是否在xi目录或文件名包含xi-
        file_str = str(tex_file)
        if '/xi/' not in file_str and 'xi-' not in tex_file.name:
            continue

        # 查找对应的英文文件
        en_name = tex_file.stem + '_en.tex'
        en_file = tex_file.parent / en_name

        if en_file.exists():
            chinese_files[str(tex_file)] = str(en_file)

    return chinese_files

def main():
    pairs = find_file_pairs()
    mismatches = []

    for zh_file, en_file in pairs.items():
        zh_lines = count_lines(zh_file)
        en_lines = count_lines(en_file)

        if zh_lines != en_lines:
            diff = en_lines - zh_lines
            percent = abs(diff) / zh_lines * 100 if zh_lines > 0 else 0

            mismatches.append({
                'name': Path(zh_file).stem,
                'zh_file': zh_file,
                'en_file': en_file,
                'zh_lines': zh_lines,
                'en_lines': en_lines,
                'diff': diff,
                'percent': percent
            })

    # 按差异程度排序
    mismatches.sort(key=lambda x: abs(x['diff']), reverse=True)

    print(f"找到 {len(mismatches)} 个Xi相关的行号不匹配文件：\n")

    for item in mismatches:
        print(f"文件: {item['name']}")
        print(f"  中文: {item['zh_file']} ({item['zh_lines']} 行)")
        print(f"  英文: {item['en_file']} ({item['en_lines']} 行)")
        print(f"  差异: {item['diff']:+d} 行 ({item['percent']:.1f}%)")
        print()

if __name__ == '__main__':
    main()
