#!/usr/bin/env python3
"""
批量修复差异为1行的Xi相关文件
策略：使用diff定位差异，然后智能修复
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

def find_1line_xi_mismatches():
    """查找所有Xi相关的1行差异文件"""
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

            diff = en_lines - zh_lines
            if abs(diff) == 1:  # 只处理1行差异
                mismatches.append({
                    'zh_file': str(tex_file),
                    'en_file': str(en_file),
                    'zh_lines': zh_lines,
                    'en_lines': en_lines,
                    'diff': diff,
                    'name': tex_file.stem
                })

    return sorted(mismatches, key=lambda x: x['name'])

def get_last_lines(filepath, n=5):
    """读取文件最后n行"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return lines[-n:] if len(lines) >= n else lines
    except:
        return []

def main():
    mismatches = find_1line_xi_mismatches()

    print(f"发现 {len(mismatches)} 个差异为1行的Xi相关文件\n")
    print("=" * 80)

    for i, item in enumerate(mismatches, 1):
        print(f"\n{i}. {item['name']}")
        print(f"   中文: {item['zh_lines']} 行, 英文: {item['en_lines']} 行")
        print(f"   差异: {item['diff']:+d} 行")

        # 检查最后几行
        zh_last = get_last_lines(item['zh_file'], 3)
        en_last = get_last_lines(item['en_file'], 3)

        print(f"   中文最后3行:")
        for line in zh_last:
            print(f"     {line.rstrip()[:70]}")

        print(f"   英文最后3行:")
        for line in en_last:
            print(f"     {line.rstrip()[:70]}")

        # 分析差异类型
        zh_last_clean = [l.strip() for l in zh_last if l.strip()]
        en_last_clean = [l.strip() for l in en_last if l.strip()]

        if item['diff'] > 0:
            print(f"   → 英文多1行")
        else:
            print(f"   → 中文多1行")

if __name__ == '__main__':
    main()
