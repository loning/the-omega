#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修正附录文件的中英文行号不匹配问题
"""

import os
import re
import sys

def count_lines(filepath):
    """统计文件行数"""
    if not os.path.exists(filepath):
        return 0
    with open(filepath, 'r', encoding='utf-8') as f:
        return len(f.readlines())

def get_file_pairs():
    """获取所有需要处理的中英文文件对"""
    appendix_dir = "sections/appendix"
    pairs = []

    for root, dirs, files in os.walk(appendix_dir):
        for file in files:
            if file.endswith('.tex') and not file.endswith('_en.tex'):
                cn_path = os.path.join(root, file)
                en_path = os.path.join(root, file.replace('.tex', '_en.tex'))

                if os.path.exists(en_path):
                    cn_lines = count_lines(cn_path)
                    en_lines = count_lines(en_path)
                    diff = cn_lines - en_lines

                    if diff != 0:
                        pairs.append({
                            'cn_path': cn_path,
                            'en_path': en_path,
                            'cn_lines': cn_lines,
                            'en_lines': en_lines,
                            'diff': diff,
                            'diff_pct': abs(diff) / cn_lines * 100 if cn_lines > 0 else 0
                        })

    # 按差异绝对值排序
    pairs.sort(key=lambda x: abs(x['diff']), reverse=True)
    return pairs

def normalize_blank_lines(content):
    """标准化空行，移除多余的连续空行"""
    # 将多个连续空行替换为单个空行
    content = re.sub(r'\n\n\n+', '\n\n', content)
    # 确保文件结尾只有一个换行符
    content = content.rstrip() + '\n'
    return content

def align_structure(cn_content, en_content):
    """对齐中英文文件的结构"""
    cn_lines = cn_content.split('\n')
    en_lines = en_content.split('\n')

    # 找出结构性差异
    # 1. 检查是否有多余的空行
    cn_normalized = normalize_blank_lines(cn_content)
    en_normalized = normalize_blank_lines(en_content)

    return cn_normalized, en_normalized

def fix_file_pair(pair):
    """修正单个文件对"""
    cn_path = pair['cn_path']
    en_path = pair['en_path']

    print(f"\n处理文件: {os.path.basename(cn_path)}")
    print(f"  中文: {cn_path} ({pair['cn_lines']} 行)")
    print(f"  英文: {en_path} ({pair['en_lines']} 行)")
    print(f"  差异: {pair['diff']:+d} 行 ({pair['diff_pct']:.1f}%)")

    # 读取文件内容
    with open(cn_path, 'r', encoding='utf-8') as f:
        cn_content = f.read()

    with open(en_path, 'r', encoding='utf-8') as f:
        en_content = f.read()

    # 对齐结构
    cn_new, en_new = align_structure(cn_content, en_content)

    # 检查是否有改进
    cn_new_lines = len(cn_new.split('\n'))
    en_new_lines = len(en_new.split('\n'))
    new_diff = cn_new_lines - en_new_lines

    if new_diff == 0:
        print(f"  ✓ 修正成功: {cn_new_lines} 行")
        # 写回文件
        with open(cn_path, 'w', encoding='utf-8') as f:
            f.write(cn_new)
        with open(en_path, 'w', encoding='utf-8') as f:
            f.write(en_new)
        return True
    elif abs(new_diff) < abs(pair['diff']):
        print(f"  ~ 部分改进: {pair['diff']:+d} → {new_diff:+d} 行")
        # 写回文件
        with open(cn_path, 'w', encoding='utf-8') as f:
            f.write(cn_new)
        with open(en_path, 'w', encoding='utf-8') as f:
            f.write(en_new)
        return False
    else:
        print(f"  ✗ 需要手动处理")
        return False

def main():
    """主函数"""
    print("=" * 80)
    print("批量修正附录文件中英文行号不匹配问题")
    print("=" * 80)

    pairs = get_file_pairs()

    print(f"\n找到 {len(pairs)} 个需要修正的文件对")

    # 统计
    fixed = 0
    improved = 0
    failed = 0

    for i, pair in enumerate(pairs, 1):
        print(f"\n[{i}/{len(pairs)}]", end='')
        result = fix_file_pair(pair)
        if result:
            fixed += 1
        else:
            new_cn = count_lines(pair['cn_path'])
            new_en = count_lines(pair['en_path'])
            if abs(new_cn - new_en) < abs(pair['diff']):
                improved += 1
            else:
                failed += 1

    # 总结
    print("\n" + "=" * 80)
    print("修正完成")
    print("=" * 80)
    print(f"完全修正: {fixed} 个")
    print(f"部分改进: {improved} 个")
    print(f"需要手动: {failed} 个")
    print(f"总计: {len(pairs)} 个")

    if failed > 0:
        print("\n需要手动处理的文件请查看上述输出。")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
