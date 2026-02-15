#!/usr/bin/env python3
"""
自动修复尾部空行差异
规范化：确保所有文件都以 \\endinput 结尾，后面跟一个空行
"""

import os
from pathlib import Path

def normalize_file_ending(filepath):
    """规范化文件结尾"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines:
            return False

        # 移除所有尾部空行
        while lines and lines[-1].strip() == '':
            lines.pop()

        # 如果最后一行不是 \endinput，添加它
        if lines and not lines[-1].strip().startswith('\\endinput'):
            lines.append('\\endinput\n')

        # 确保最后有且仅有一个空行
        if lines[-1].strip() == '\\endinput':
            lines[-1] = '\\endinput\n'
            lines.append('\n')
        elif lines[-1] != '\n':
            lines.append('\n')

        # 写回文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return True
    except Exception as e:
        print(f"错误处理 {filepath}: {e}")
        return False

def count_lines(filepath):
    """统计文件行数"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0

def find_all_xi_files():
    """查找所有Xi相关的tex文件对"""
    base_dir = Path('.')
    file_pairs = []

    for tex_file in base_dir.rglob('*.tex'):
        if tex_file.name.endswith('_en.tex'):
            continue

        file_str = str(tex_file)
        if '/xi/' not in file_str and 'xi-' not in tex_file.name:
            continue

        en_name = tex_file.stem + '_en.tex'
        en_file = tex_file.parent / en_name

        if en_file.exists():
            file_pairs.append((str(tex_file), str(en_file)))

    return file_pairs

def main():
    file_pairs = find_all_xi_files()

    print(f"找到 {len(file_pairs)} 对Xi相关文件")
    print(f"正在规范化文件结尾...\n")

    fixed_count = 0
    for zh_file, en_file in file_pairs:
        zh_before = count_lines(zh_file)
        en_before = count_lines(en_file)

        normalize_file_ending(zh_file)
        normalize_file_ending(en_file)

        zh_after = count_lines(zh_file)
        en_after = count_lines(en_file)

        if zh_before != zh_after or en_before != en_after:
            fixed_count += 1
            name = Path(zh_file).name
            print(f"{fixed_count}. {name}")
            print(f"   中文: {zh_before} → {zh_after} 行")
            print(f"   英文: {en_before} → {en_after} 行")

    print(f"\n完成！修改了 {fixed_count} 对文件")

if __name__ == '__main__':
    main()
