#!/usr/bin/env python3
"""
扫描文档问题：
1. 未收录的文件（在 docs/ 目录下但不在 SUMMARY.md 中，包括 .md 和 .tex 文件）
2. 链接缺失（SUMMARY.md 中链接的文件不存在）
3. 图片未引用或缺失（文档中引用的图片文件不存在，或者图片文件存在但未被引用）
4. LaTeX 文件引用缺失（.tex 文件中的 \input 和 \include 引用的文件不存在）
"""
import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import Set, Dict, List, Tuple


class DocScanner:
    def __init__(self, docs_dir: Path, summary_file: Path):
        self.docs_dir = docs_dir
        self.summary_file = summary_file
        self.base_dir = docs_dir.parent
        
    def extract_links_from_summary(self) -> Set[str]:
        """从 SUMMARY.md 中提取所有文件链接"""
        if not self.summary_file.exists():
            print(f"✗ SUMMARY.md 不存在: {self.summary_file}")
            return set()
        
        with open(self.summary_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取所有链接
        pattern = r'\]\(([^)]+)\)'
        links = re.findall(pattern, content)
        
        file_links = set()
        for link in links:
            # 跳过外部链接
            if link.startswith('http') or link.startswith('mailto:') or not link:
                continue
            
            # 分离文件路径和锚点
            if '#' in link:
                file_path_str = link.split('#')[0]
            else:
                file_path_str = link
            
            # 跳过空链接
            if not file_path_str or file_path_str == '()':
                continue
            
            # 规范化路径
            if file_path_str.startswith('./'):
                file_path_str = file_path_str[2:]
            elif file_path_str.startswith('../'):
                # 相对于 docs/ 目录
                file_path_str = file_path_str[3:]
            
            file_links.add(file_path_str)
        
        return file_links
    
    def find_all_markdown_files(self) -> Set[str]:
        """查找所有 Markdown 文件"""
        md_files = set()
        for md_file in self.docs_dir.rglob('*.md'):
            # 跳过 SUMMARY.md 本身
            if md_file.name == 'SUMMARY.md':
                continue
            # 转换为相对于 docs/ 的路径
            try:
                rel_path = md_file.relative_to(self.docs_dir)
                md_files.add(str(rel_path).replace('\\', '/'))
            except ValueError:
                # 如果文件不在 docs_dir 下，跳过
                pass
        return md_files
    
    def find_all_tex_files(self) -> Set[str]:
        """查找所有 LaTeX 文件"""
        tex_files = set()
        for tex_file in self.docs_dir.rglob('*.tex'):
            # 转换为相对于 docs/ 的路径
            try:
                rel_path = tex_file.relative_to(self.docs_dir)
                tex_files.add(str(rel_path).replace('\\', '/'))
            except ValueError:
                pass
        return tex_files
    
    def find_all_doc_files(self) -> Set[str]:
        """查找所有文档文件（.md 和 .tex）"""
        return self.find_all_markdown_files() | self.find_all_tex_files()
    
    def find_all_image_files(self) -> Set[str]:
        """查找所有图片文件"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
        image_files = set()
        assets_dir = self.docs_dir / 'assets'
        for img_file in self.docs_dir.rglob('*'):
            # 忽略 docs/assets 目录
            try:
                if assets_dir in img_file.parents or img_file.parent == assets_dir:
                    continue
            except (ValueError, AttributeError):
                pass
            if img_file.suffix.lower() in image_extensions:
                try:
                    rel_path = img_file.relative_to(self.docs_dir)
                    image_files.add(str(rel_path).replace('\\', '/'))
                except ValueError:
                    pass
        return image_files
    
    def extract_image_references(self) -> Dict[str, Set[str]]:
        """从所有文档文件（.md 和 .tex）中提取图片引用"""
        image_refs = defaultdict(set)  # file -> set of image paths
        
        # 处理 Markdown 文件
        for md_file in self.docs_dir.rglob('*.md'):
            if md_file.name == 'SUMMARY.md':
                continue
            self._extract_md_images(md_file, image_refs)
        
        # 处理 LaTeX 文件
        for tex_file in self.docs_dir.rglob('*.tex'):
            self._extract_tex_images(tex_file, image_refs)
        
        return image_refs
    
    def _extract_md_images(self, md_file: Path, image_refs: Dict[str, Set[str]]):
        """从 Markdown 文件中提取图片引用"""
        # 图片引用模式：![alt](path) 或 ![alt](path "title")
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            matches = re.findall(image_pattern, content)
            for alt_text, img_path in matches:
                img_rel_path = self._resolve_image_path(md_file, img_path)
                if img_rel_path:
                    rel_md_path = str(md_file.relative_to(self.docs_dir)).replace('\\', '/')
                    image_refs[rel_md_path].add(img_rel_path)
        except Exception as e:
            print(f"✗ 读取文件错误 {md_file}: {e}")
    
    def _extract_tex_images(self, tex_file: Path, image_refs: Dict[str, Set[str]]):
        """从 LaTeX 文件中提取图片引用"""
        # LaTeX 图片引用模式：\includegraphics[options]{path}
        # 支持多种格式：\includegraphics{path}, \includegraphics[width=...]{path}
        image_pattern = r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}'
        
        try:
            with open(tex_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            matches = re.findall(image_pattern, content)
            for img_path in matches:
                img_rel_path = self._resolve_image_path(tex_file, img_path)
                if img_rel_path:
                    rel_tex_path = str(tex_file.relative_to(self.docs_dir)).replace('\\', '/')
                    image_refs[rel_tex_path].add(img_rel_path)
        except Exception as e:
            print(f"✗ 读取文件错误 {tex_file}: {e}")
    
    def _find_book_root(self, doc_file: Path) -> Path:
        """找到文档文件所属的 book 根目录"""
        current = doc_file.parent
        # 向上查找，直到找到 book-* 目录或到达 docs/books 目录
        while current != self.docs_dir and current.parent != self.docs_dir:
            if current.name.startswith('book-'):
                return current
            current = current.parent
        # 如果没有找到 book-* 目录，返回 docs/books 目录
        return self.docs_dir / 'books'
    
    def _resolve_image_path(self, doc_file: Path, img_path: str) -> str:
        """解析图片路径（相对于文档文件）"""
        # 处理相对路径
        if img_path.startswith('http') or img_path.startswith('//'):
            return None  # 跳过外部链接
        
        # 解析图片路径
        img_path_clean = img_path.split('"')[0].strip()  # 移除可选的 title
        
        # 如果是相对路径，需要相对于当前文件解析
        if not img_path_clean.startswith('/'):
            # 确保 doc_file 是绝对路径
            if not doc_file.is_absolute():
                doc_file = (self.docs_dir / doc_file).resolve()
            doc_dir = doc_file.parent
            
            # 对于 .tex 文件，图片路径可能是相对于文件目录或 book 根目录的
            if doc_file.suffix == '.tex':
                # 先尝试相对于文件目录解析
                if img_path_clean.startswith('../') or img_path_clean.startswith('./'):
                    # 相对路径，相对于文件目录
                    img_abs_path = (doc_dir / img_path_clean).resolve()
                else:
                    # 绝对路径（相对于 book 根目录）
                    book_root = self._find_book_root(doc_file)
                    img_abs_path = book_root / img_path_clean
            else:
                # 对于 .md 文件，图片路径是相对于当前文件的，必须使用绝对路径解析
                # 处理 `books/assets/...` 这种格式（可能是错误的，尝试修复）
                if img_path_clean.startswith('books/assets/'):
                    # 这可能是错误的路径格式，尝试找到 book 根目录的 assets
                    book_root = self._find_book_root(doc_file)
                    img_abs_path = book_root / 'assets' / img_path_clean[12:]  # 移除 'books/assets/'，保留后面的路径
                elif img_path_clean.startswith('../'):
                    # 向上级目录 - 对于 .md 文件，必须严格按照相对路径解析
                    parts = img_path_clean.split('/')
                    up_levels = 0
                    for part in parts:
                        if part == '..':
                            up_levels += 1
                        else:
                            break
                    # 计算实际路径
                    # 手动向上遍历目录，避免 resolve() 的规范化问题
                    current_dir = doc_dir
                    for _ in range(up_levels):
                        if current_dir == self.docs_dir or current_dir.parent == current_dir:
                            break  # 不能超过 docs 目录或到达根目录
                        current_dir = current_dir.parent
                    # 使用 Path 对象拼接剩余路径部分
                    remaining_parts = parts[up_levels:]
                    if remaining_parts:
                        img_abs_path = current_dir
                        for part in remaining_parts:
                            img_abs_path = img_abs_path / part
                    else:
                        img_abs_path = current_dir
                else:
                    # 相对于当前文件目录
                    img_abs_path = doc_dir / img_path_clean
            
            # 转换为相对于 docs_dir 的路径
            try:
                # 确保使用绝对路径进行比较
                docs_dir_abs = self.docs_dir.resolve() if not self.docs_dir.is_absolute() else self.docs_dir
                img_abs_path_resolved = img_abs_path.resolve() if img_abs_path.exists() else img_abs_path
                img_rel_path = img_abs_path_resolved.relative_to(docs_dir_abs)
                img_rel_path = str(img_rel_path).replace('\\', '/')
                
                # 对于 .tex 文件，如果路径不存在，尝试使用 book 根目录作为备选
                if doc_file.suffix == '.tex' and not img_abs_path.exists():
                    # 尝试使用 book 根目录
                    book_root = self._find_book_root(doc_file)
                    # 解析剩余路径部分
                    if img_path_clean.startswith('../'):
                        # 从相对路径中提取剩余部分
                        path_parts = img_path_clean.split('/')
                        up_count = sum(1 for p in path_parts if p == '..')
                        remaining_parts = path_parts[up_count:]
                    elif img_path_clean.startswith('./'):
                        remaining_parts = img_path_clean[2:].split('/')
                    else:
                        remaining_parts = img_path_clean.split('/')
                    
                    if remaining_parts:
                        alt_img_abs_path = book_root
                        for part in remaining_parts:
                            if part:  # 跳过空字符串
                                alt_img_abs_path = alt_img_abs_path / part
                        if alt_img_abs_path.exists():
                            try:
                                alt_img_rel_path = alt_img_abs_path.relative_to(self.docs_dir)
                                return str(alt_img_rel_path).replace('\\', '/')
                            except ValueError:
                                pass
                
                # 对于 .md 文件，必须使用绝对路径，不使用备选路径
                # 直接返回解析的路径（无论是否存在，让调用者检查）
                return img_rel_path
            except ValueError:
                # 如果路径不在 docs_dir 下，跳过
                return None
        else:
            # 绝对路径（相对于 docs/）
            return img_path_clean.lstrip('/')
    
    def extract_tex_file_references(self) -> Dict[str, Set[str]]:
        """从所有 LaTeX 文件中提取文件引用（\input 和 \include）"""
        file_refs = defaultdict(set)  # file -> set of referenced file paths
        
        # LaTeX 文件引用模式：\input{path} 或 \include{path}
        # 注意：\include 会自动添加 .tex 扩展名，但 \input 不会
        input_pattern = r'\\input\{([^}]+)\}'
        include_pattern = r'\\include\{([^}]+)\}'
        
        for tex_file in self.docs_dir.rglob('*.tex'):
            try:
                with open(tex_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取 \input 引用
                input_matches = re.findall(input_pattern, content)
                for ref_path in input_matches:
                    resolved_path = self._resolve_tex_file_path(tex_file, ref_path, add_ext=False)
                    if resolved_path:
                        rel_tex_path = str(tex_file.relative_to(self.docs_dir)).replace('\\', '/')
                        file_refs[rel_tex_path].add(resolved_path)
                
                # 提取 \include 引用
                include_matches = re.findall(include_pattern, content)
                for ref_path in include_matches:
                    resolved_path = self._resolve_tex_file_path(tex_file, ref_path, add_ext=True)
                    if resolved_path:
                        rel_tex_path = str(tex_file.relative_to(self.docs_dir)).replace('\\', '/')
                        file_refs[rel_tex_path].add(resolved_path)
            except Exception as e:
                print(f"✗ 读取文件错误 {tex_file}: {e}")
        
        return file_refs
    
    def check_md_tex_image_consistency(self, image_refs: Dict[str, Set[str]]) -> List[Tuple[str, str, Set[str], Set[str]]]:
        """检查对应的 .md 和 .tex 文件的图片引用是否一致"""
        mismatches = []
        
        # 构建文件映射：基础名称 -> (md_file, tex_file)
        md_files_by_base = {}  # base_name -> md_file_path
        tex_files_by_base = {}  # base_name -> tex_file_path
        
        for file_path, images in image_refs.items():
            if file_path.endswith('.md'):
                # 获取基础名称（去掉扩展名和可能的 _en 后缀）
                base_name = file_path[:-3]  # 去掉 .md
                # 处理 _en.md 的情况
                if base_name.endswith('_en'):
                    base_name = base_name[:-3]
                md_files_by_base[base_name] = file_path
            elif file_path.endswith('.tex'):
                base_name = file_path[:-4]  # 去掉 .tex
                if base_name.endswith('_en'):
                    base_name = base_name[:-3]
                tex_files_by_base[base_name] = file_path
        
        # 找到所有对应的文件对
        common_bases = set(md_files_by_base.keys()) & set(tex_files_by_base.keys())
        
        for base_name in common_bases:
            md_file = md_files_by_base[base_name]
            tex_file = tex_files_by_base[base_name]
            
            md_images = image_refs.get(md_file, set())
            tex_images = image_refs.get(tex_file, set())
            
            # 标准化图片路径（移除路径差异，只比较文件名）
            md_image_names = {Path(img).name for img in md_images}
            tex_image_names = {Path(img).name for img in tex_images}
            
            # 如果图片引用不一致（包括一个文件有图片而另一个没有的情况）
            if md_image_names != tex_image_names:
                mismatches.append((md_file, tex_file, md_image_names, tex_image_names))
        
        # 也检查只有 .md 或只有 .tex 文件有图片引用，但对应的文件存在的情况
        # 找到所有文档文件
        all_md_files = self.find_all_markdown_files()
        all_tex_files = self.find_all_tex_files()
        
        # 检查只有 MD 有图片引用，但对应的 TEX 文件存在
        for md_file in all_md_files:
            base_name = md_file[:-3]
            if base_name.endswith('_en'):
                base_name = base_name[:-3]
            
            # 查找对应的 .tex 文件
            for tex_file in all_tex_files:
                tex_base = tex_file[:-4]
                if tex_base.endswith('_en'):
                    tex_base = tex_base[:-3]
                
                if base_name == tex_base:
                    md_images = image_refs.get(md_file, set())
                    tex_images = image_refs.get(tex_file, set())
                    
                    # 如果 MD 有图片但 TEX 没有，或反之
                    if md_images and not tex_images:
                        md_image_names = {Path(img).name for img in md_images}
                        mismatches.append((md_file, tex_file, md_image_names, set()))
                    elif tex_images and not md_images:
                        tex_image_names = {Path(img).name for img in tex_images}
                        mismatches.append((md_file, tex_file, set(), tex_image_names))
                    break
        
        return mismatches
    
    def _resolve_tex_file_path(self, tex_file: Path, ref_path: str, add_ext: bool = False) -> str:
        """解析 LaTeX 文件引用路径"""
        # \include 会自动添加 .tex 扩展名
        # \input 可能已经有扩展名，也可能没有
        if add_ext:
            # \include: 如果没有扩展名，添加 .tex
            if not ref_path.endswith('.tex'):
                ref_path = ref_path + '.tex'
        else:
            # \input: 如果没有扩展名，尝试添加
            if not ref_path.endswith('.tex'):
                ref_path = ref_path + '.tex'
        
        # 解析相对路径
        doc_dir = tex_file.parent
        
        if ref_path.startswith('../'):
            parts = ref_path.split('/')
            up_levels = 0
            for part in parts:
                if part == '..':
                    up_levels += 1
                else:
                    break
            current_dir = doc_dir
            for _ in range(up_levels):
                if current_dir == self.docs_dir:
                    break
                current_dir = current_dir.parent
            # 使用 Path 对象拼接剩余路径部分
            remaining_parts = parts[up_levels:]
            if remaining_parts:
                ref_abs_path = current_dir
                for part in remaining_parts:
                    ref_abs_path = ref_abs_path / part
            else:
                ref_abs_path = current_dir
        else:
            ref_abs_path = doc_dir / ref_path
        
        # 转换为相对于 docs_dir 的路径
        try:
            ref_rel_path = ref_abs_path.relative_to(self.docs_dir)
            return str(ref_rel_path).replace('\\', '/')
        except ValueError:
            return None
    
    def check_missing_links(self, summary_links: Set[str]) -> List[str]:
        """检查 SUMMARY.md 中链接的文件是否存在"""
        missing = []
        for link in summary_links:
            file_path = self.docs_dir / link
            if not file_path.exists():
                missing.append(link)
        return missing
    
    def check_unlisted_files(self, summary_links: Set[str], all_md_files: Set[str]) -> List[str]:
        """检查未收录的文件"""
        unlisted = []
        for md_file in all_md_files:
            if md_file not in summary_links:
                unlisted.append(md_file)
        return sorted(unlisted)
    
    def check_missing_images(self, image_refs: Dict[str, Set[str]]) -> List[Tuple[str, str]]:
        """检查引用的图片文件是否存在"""
        missing = []
        for md_file, img_paths in image_refs.items():
            for img_path in img_paths:
                # 检查相对于 docs/ 的路径
                img_file = self.docs_dir / img_path
                if not img_file.exists():
                    missing.append((md_file, img_path))
        return missing
    
    def check_unreferenced_images(self, image_refs: Dict[str, Set[str]], all_images: Set[str]) -> List[str]:
        """检查未被引用的图片文件"""
        referenced_images = set()
        for img_paths in image_refs.values():
            referenced_images.update(img_paths)

        unreferenced = []
        for img_file in all_images:
            # 忽略 docs/assets 目录下的图片
            if img_file.startswith('assets/'):
                continue
            if img_file not in referenced_images:
                # 排除 architecture.png 和 architecture-thumb.png（封面图片不需要引用）
                if not (img_file.endswith('architecture.png') or img_file.endswith('architecture-thumb.png')):
                    unreferenced.append(img_file)
        return sorted(unreferenced)
    
    def scan(self, output_file: Path = None, verbose: bool = False):
        """执行完整扫描
        
        Args:
            output_file: 输出文件路径（可选）
            verbose: 是否输出详细信息（显示所有结果，不限制数量）
        """
        output_lines = []
        
        def print_and_save(*args, **kwargs):
            line = ' '.join(str(arg) for arg in args)
            print(*args, **kwargs)
            if output_file:
                output_lines.append(line)
        
        print_and_save("=" * 80)
        print_and_save("文档问题扫描")
        print_and_save("=" * 80)
        print_and_save()
        
        # 1. 提取 SUMMARY.md 中的链接
        print_and_save("1. 提取 SUMMARY.md 中的链接...")
        summary_links = self.extract_links_from_summary()
        print_and_save(f"   ✓ 找到 {len(summary_links)} 个链接")
        print_and_save()
        
        # 2. 查找所有文档文件
        print_and_save("2. 查找所有文档文件...")
        all_md_files = self.find_all_markdown_files()
        all_tex_files = self.find_all_tex_files()
        all_doc_files = self.find_all_doc_files()
        print_and_save(f"   ✓ 找到 {len(all_md_files)} 个 Markdown 文件")
        print_and_save(f"   ✓ 找到 {len(all_tex_files)} 个 LaTeX 文件")
        print_and_save(f"   ✓ 总计 {len(all_doc_files)} 个文档文件")
        print_and_save()
        
        # 3. 检查链接缺失
        print_and_save("3. 检查链接缺失...")
        missing_links = self.check_missing_links(summary_links)
        if missing_links:
            print_and_save(f"   ✗ 发现 {len(missing_links)} 个缺失的链接:")
            display_count = len(missing_links) if verbose else min(20, len(missing_links))
            for link in missing_links[:display_count]:
                print_and_save(f"      - {link}")
            if not verbose and len(missing_links) > 20:
                print_and_save(f"      ... 还有 {len(missing_links) - 20} 个")
        else:
            print_and_save("   ✓ 所有链接都有效")
        print_and_save()
        
        # 4. 检查未收录的文件（只检查 .md 文件，因为 SUMMARY.md 只收录 .md 文件）
        print_and_save("4. 检查未收录的文件（仅 .md 文件）...")
        unlisted_files = self.check_unlisted_files(summary_links, all_md_files)
        if unlisted_files:
            print_and_save(f"   ⚠️  发现 {len(unlisted_files)} 个未收录的文件:")
            display_count = len(unlisted_files) if verbose else min(30, len(unlisted_files))
            for file in unlisted_files[:display_count]:
                print_and_save(f"      - {file}")
            if not verbose and len(unlisted_files) > 30:
                print_and_save(f"      ... 还有 {len(unlisted_files) - 30} 个")
        else:
            print_and_save("   ✓ 所有文件都已收录")
        print_and_save()
        
        # 5. 查找所有图片文件
        print_and_save("5. 查找所有图片文件...")
        all_images = self.find_all_image_files()
        print_and_save(f"   ✓ 找到 {len(all_images)} 个图片文件")
        print_and_save()
        
        # 6. 提取图片引用
        print_and_save("6. 提取图片引用...")
        image_refs = self.extract_image_references()
        total_refs = sum(len(refs) for refs in image_refs.values())
        print_and_save(f"   ✓ 找到 {total_refs} 个图片引用（在 {len(image_refs)} 个文件中）")
        print_and_save()
        
        # 7. 检查缺失的图片
        print_and_save("7. 检查缺失的图片...")
        missing_images = self.check_missing_images(image_refs)
        if missing_images:
            print_and_save(f"   ✗ 发现 {len(missing_images)} 个缺失的图片:")
            display_count = len(missing_images) if verbose else min(20, len(missing_images))
            for md_file, img_path in missing_images[:display_count]:
                print_and_save(f"      - {md_file}: {img_path}")
            if not verbose and len(missing_images) > 20:
                print_and_save(f"      ... 还有 {len(missing_images) - 20} 个")
        else:
            print_and_save("   ✓ 所有引用的图片都存在")
        print_and_save()
        
        # 8. 检查未引用的图片
        print_and_save("8. 检查未引用的图片...")
        unreferenced_images = self.check_unreferenced_images(image_refs, all_images)
        if unreferenced_images:
            print_and_save(f"   ⚠️  发现 {len(unreferenced_images)} 个未引用的图片:")
            display_count = len(unreferenced_images) if verbose else min(30, len(unreferenced_images))
            for img_file in unreferenced_images[:display_count]:
                print_and_save(f"      - {img_file}")
            if not verbose and len(unreferenced_images) > 30:
                print_and_save(f"      ... 还有 {len(unreferenced_images) - 30} 个")
        else:
            print_and_save("   ✓ 所有图片都被引用")
        print_and_save()
        
        # 9. 提取 LaTeX 文件引用
        print_and_save("9. 提取 LaTeX 文件引用（\\input 和 \\include）...")
        tex_file_refs = self.extract_tex_file_references()
        total_tex_refs = sum(len(refs) for refs in tex_file_refs.values())
        print_and_save(f"   ✓ 找到 {total_tex_refs} 个文件引用（在 {len(tex_file_refs)} 个文件中）")
        print_and_save()
        
        # 10. 检查缺失的 LaTeX 文件引用
        print_and_save("10. 检查缺失的 LaTeX 文件引用...")
        missing_tex_refs = []
        for tex_file, ref_paths in tex_file_refs.items():
            for ref_path in ref_paths:
                ref_file = self.docs_dir / ref_path
                if not ref_file.exists():
                    missing_tex_refs.append((tex_file, ref_path))
        
        if missing_tex_refs:
            print_and_save(f"   ✗ 发现 {len(missing_tex_refs)} 个缺失的文件引用:")
            display_count = len(missing_tex_refs) if verbose else min(20, len(missing_tex_refs))
            for tex_file, ref_path in missing_tex_refs[:display_count]:
                print_and_save(f"      - {tex_file}: {ref_path}")
            if not verbose and len(missing_tex_refs) > 20:
                print_and_save(f"      ... 还有 {len(missing_tex_refs) - 20} 个")
        else:
            print_and_save("   ✓ 所有引用的文件都存在")
        print_and_save()
        
        # 11. 检查对应的 .md 和 .tex 文件的图片引用一致性
        print_and_save("11. 检查对应的 .md 和 .tex 文件的图片引用一致性...")
        md_tex_image_mismatches = self.check_md_tex_image_consistency(image_refs)
        if md_tex_image_mismatches:
            print_and_save(f"   ⚠️  发现 {len(md_tex_image_mismatches)} 个不一致的文件对:")
            display_count = len(md_tex_image_mismatches) if verbose else min(20, len(md_tex_image_mismatches))
            for md_file, tex_file, md_images, tex_images in md_tex_image_mismatches[:display_count]:
                print_and_save(f"      - {md_file} <-> {tex_file}")
                only_in_md = md_images - tex_images
                only_in_tex = tex_images - md_images
                if only_in_md:
                    img_list = sorted(only_in_md) if verbose else list(only_in_md)[:3]
                    print_and_save(f"        仅在 .md 中: {', '.join(img_list)}")
                if only_in_tex:
                    img_list = sorted(only_in_tex) if verbose else list(only_in_tex)[:3]
                    print_and_save(f"        仅在 .tex 中: {', '.join(img_list)}")
            if not verbose and len(md_tex_image_mismatches) > 20:
                print_and_save(f"      ... 还有 {len(md_tex_image_mismatches) - 20} 个")
        else:
            print_and_save("   ✓ 所有对应的文件对都有一致的图片引用")
        print_and_save()
        
        # 总结
        print_and_save("=" * 80)
        print_and_save("扫描总结")
        print_and_save("=" * 80)
        print_and_save(f"缺失的链接: {len(missing_links)}")
        print_and_save(f"未收录的文件: {len(unlisted_files)}")
        print_and_save(f"缺失的图片: {len(missing_images)}")
        print_and_save(f"未引用的图片: {len(unreferenced_images)}")
        print_and_save(f"缺失的 LaTeX 文件引用: {len(missing_tex_refs)}")
        print_and_save(f".md/.tex 图片引用不一致: {len(md_tex_image_mismatches)}")
        print_and_save()
        
        # 保存到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(output_lines))
            print(f"✓ 结果已保存到: {output_file}")
        
        # 返回是否有问题
        has_issues = bool(missing_links or missing_images or missing_tex_refs)
        return 1 if has_issues else 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='扫描文档问题')
    parser.add_argument('-o', '--output', type=str, help='将结果保存到文件')
    parser.add_argument('-v', '--verbose', action='store_true', help='输出详细信息（显示所有结果，不限制数量）')
    args = parser.parse_args()
    
    # 获取脚本所在目录的父目录（项目根目录）
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    docs_dir = project_root / "docs"
    summary_file = docs_dir / "SUMMARY.md"
    
    if not docs_dir.exists():
        print(f"✗ docs 目录不存在: {docs_dir}")
        sys.exit(1)
    
    scanner = DocScanner(docs_dir, summary_file)
    output_file = Path(args.output) if args.output else None
    exit_code = scanner.scan(output_file=output_file, verbose=args.verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
