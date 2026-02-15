#!/usr/bin/env python3
from pathlib import Path

def count_lines(filepath):
    """Count lines in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return -1

sections_dir = Path('sections')
cn_files = {}
en_files = {}

# Collect Chinese and English files
for tex_file in sections_dir.rglob('*.tex'):
    if 'generated' in tex_file.parts:
        continue
    if tex_file.name.endswith('_en.tex'):
        en_files[tex_file.stem[:-3]] = tex_file
    else:
        cn_files[tex_file.stem] = tex_file

# Find mismatched line counts
print("=" * 100)
print("行号不匹配的文件（中文行数 ≠ 英文行数）")
print("=" * 100)

mismatched = []
missing_en = []

for stem, cn_path in sorted(cn_files.items()):
    if stem not in en_files:
        missing_en.append((stem, cn_path))
        continue

    en_path = en_files[stem]
    cn_lines = count_lines(cn_path)
    en_lines = count_lines(en_path)

    if cn_lines != en_lines:
        diff = en_lines - cn_lines
        diff_pct = abs(diff) / cn_lines * 100 if cn_lines > 0 else 0
        mismatched.append((stem, cn_path, en_path, cn_lines, en_lines, diff, diff_pct))

# Output mismatched files
if mismatched:
    print(f"\n找到 {len(mismatched)} 个行号不匹配的文件：\n")
    for stem, cn_path, en_path, cn_lines, en_lines, diff, diff_pct in mismatched:
        print(f"文件: {stem}")
        print(f"  中文: {cn_path}")
        print(f"    {cn_lines} 行")
        print(f"  英文: {en_path}")
        print(f"    {en_lines} 行")
        print(f"  差异: {diff:+d} 行 ({diff_pct:.1f}%)")
        print()
else:
    print("\n✓ 所有文件行号完全匹配！")

# Output missing English files
if missing_en:
    print("=" * 100)
    print(f"缺失英文版的文件（{len(missing_en)} 个）")
    print("=" * 100)
    for stem, cn_path in missing_en:
        cn_lines = count_lines(cn_path)
        print(f"{cn_path}")
        print(f"  中文: {cn_lines} 行")
        print()

# Summary
print("=" * 100)
print("统计汇总")
print("=" * 100)
print(f"总文件数: {len(cn_files)}")
print(f"完全匹配: {len(cn_files) - len(mismatched) - len(missing_en)}")
print(f"行号不匹配: {len(mismatched)}")
print(f"缺失英文版: {len(missing_en)}")
print("=" * 100)
