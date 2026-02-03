#!/usr/bin/env python3
"""
拆分大型LaTeX文件，按subsection边界分割
"""
import re
import os
from pathlib import Path

def find_subsection_boundaries(content_lines):
    """找到所有subsection的行号"""
    boundaries = []
    for i, line in enumerate(content_lines, 1):
        if re.match(r'^\\subsection', line):
            boundaries.append(i)
    return boundaries

def split_latex_file(input_file, output_dir=None, max_subsections_per_file=6):
    """
    拆分LaTeX文件
    
    Args:
        input_file: 输入文件路径
        output_dir: 输出目录（默认与输入文件同目录）
        max_subsections_per_file: 每个输出文件最多包含的subsection数量
    """
    input_path = Path(input_file)
    
    if output_dir is None:
        output_dir = input_path.parent
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 读取文件
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找到所有subsection边界
    boundaries = find_subsection_boundaries(lines)
    
    if not boundaries:
        print(f"未找到subsection，文件可能不需要拆分")
        return
    
    print(f"找到 {len(boundaries)} 个subsection，行号: {boundaries}")
    
    # 找到section声明行（通常是第一行）
    section_start = 0
    for i, line in enumerate(lines):
        if re.match(r'^\\section', line):
            section_start = i
            break
    
    # 文件结束行
    file_end = len(lines)
    
    # 确定拆分点
    # 每个文件包含section声明 + 若干个subsection
    num_files = (len(boundaries) + max_subsections_per_file - 1) // max_subsections_per_file
    
    base_name = input_path.stem
    extension = input_path.suffix
    
    for file_idx in range(num_files):
        start_idx = file_idx * max_subsections_per_file
        end_idx = min((file_idx + 1) * max_subsections_per_file, len(boundaries))
        
        if start_idx >= len(boundaries):
            break
        
        # 确定行号范围
        start_line = boundaries[start_idx] - 1  # 转换为0-based索引
        if end_idx < len(boundaries):
            end_line = boundaries[end_idx] - 1
        else:
            end_line = file_end
        
        # 构建输出文件名
        if num_files == 1:
            output_file = output_dir / f"{base_name}{extension}"
        else:
            output_file = output_dir / f"{base_name}_part{file_idx+1:02d}{extension}"
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            # 写入section声明（每个文件都包含，便于独立使用）
            f.write(lines[section_start])
            f.write('\n')
            
            # 写入subsection内容
            f.writelines(lines[start_line:end_line])
        
        print(f"创建文件: {output_file} (行 {start_line+1}-{end_line}, 包含subsection {start_idx+1}-{end_idx})")
    
    print(f"\n拆分完成！共生成 {num_files} 个文件")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python3 split_latex_section.py <input_file> [output_dir] [max_subsections]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    max_subsections = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    
    split_latex_file(input_file, output_dir, max_subsections)
