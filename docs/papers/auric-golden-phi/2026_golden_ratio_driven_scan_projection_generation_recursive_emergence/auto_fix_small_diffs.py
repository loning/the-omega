#!/usr/bin/env python3
"""
自动修复差异小于3行的Xi相关文件
使用diff工具定位具体差异位置
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

def get_diff_summary(zh_file, en_file):
    """获取diff摘要"""
    try:
        result = subprocess.run(
            ['diff', '-u', zh_file, en_file],
            capture_output=True,
            text=True
        )
        return result.stdout
    except:
        return None

def find_small_xi_mismatches():
    """查找所有Xi相关的小差异文件"""
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

            diff = abs(en_lines - zh_lines)
            if 0 < diff <= 2:  # 只处理1-2行差异
                mismatches.append({
                    'zh_file': str(tex_file),
                    'en_file': str(en_file),
                    'zh_lines': zh_lines,
                    'en_lines': en_lines,
                    'diff': diff
                })

    return mismatches

def main():
    mismatches = find_small_xi_mismatches()

    print(f"发现 {len(mismatches)} 个差异1-2行的Xi相关文件：\n")

    for i, item in enumerate(mismatches, 1):
        print(f"{i}. {Path(item['zh_file']).name}")
        print(f"   中文: {item['zh_lines']} 行")
        print(f"   英文: {item['en_lines']} 行")
        print(f"   差异: {item['diff']} 行")

        # 获取diff摘要
        diff_output = get_diff_summary(item['zh_file'], item['en_file'])
        if diff_output:
            lines = diff_output.split('\n')
            # 只显示前15行
            print("   Diff预览:")
            for line in lines[2:12]:  # 跳过diff头部
                if line.startswith('+') or line.startswith('-'):
                    print(f"     {line[:80]}")
        print()

if __name__ == '__main__':
    main()
