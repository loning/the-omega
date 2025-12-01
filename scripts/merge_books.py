#!/usr/bin/env python3
"""
Script to merge markdown files from docs/books/ into single files in book/merged-books/
Parses SUMMARY.md to extract book structure and merges chapters in order.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Optional


def parse_summary(summary_path: Path) -> List[Tuple[str, List[str]]]:
    """
    Parse SUMMARY.md and extract book titles and their chapter file paths.
    
    Returns:
        List of tuples: (book_title, list of chapter_file_paths)
    """
    books = []
    current_book = None
    current_book_index_path = None
    current_chapters = []
    
    with open(summary_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.rstrip()
        
        # Match book title: lines starting with "- [" that have a link
        book_match = re.match(r'^- \[([^\]]+)\]\(([^)]+)\)', line)
        if book_match:
            # Save previous book if exists
            if current_book is not None:
                # If no chapters found but we have an index path, use it
                if not current_chapters and current_book_index_path:
                    current_chapters = [current_book_index_path]
                books.append((current_book, current_chapters))
            
            # Start new book
            current_book = book_match.group(1)
            index_path = book_match.group(2)
            # Remove leading ./ if present
            if index_path.startswith('./'):
                index_path = index_path[2:]
            current_book_index_path = index_path
            current_chapters = []
            continue
        
        # Match chapter links: lines with markdown links that point to .md files
        # This matches both direct links and nested links
        chapter_match = re.search(r'\(\.?/?([^)]+\.md)\)', line)
        if chapter_match:
            chapter_path = chapter_match.group(1)
            # Remove leading ./ if present
            if chapter_path.startswith('./'):
                chapter_path = chapter_path[2:]
            current_chapters.append(chapter_path)
    
    # Don't forget the last book
    if current_book is not None:
        # If no chapters found but we have an index path, use it
        if not current_chapters and current_book_index_path:
            current_chapters = [current_book_index_path]
        books.append((current_book, current_chapters))
    
    return books


def read_markdown_file(file_path: Path) -> Optional[str]:
    """Read a markdown file and return its content."""
    if not file_path.exists():
        print(f"Warning: File not found: {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def merge_book_chapters(
    book_title: str,
    chapter_paths: List[str],
    docs_dir: Path,
    output_dir: Path
) -> None:
    """
    Merge all chapters of a book into a single markdown file.
    
    Args:
        book_title: Title of the book
        chapter_paths: List of relative paths to chapter files
        docs_dir: Base directory for docs (where chapter_paths are relative to)
        output_dir: Directory to write merged file
    """
    merged_content = []
    
    # Add book title as main heading
    merged_content.append(f"# {book_title}\n\n")
    
    # Process each chapter
    for i, chapter_path in enumerate(chapter_paths):
        full_path = docs_dir / chapter_path
        
        if not full_path.exists():
            print(f"Warning: Chapter file not found: {full_path}")
            continue
        
        content = read_markdown_file(full_path)
        if content is None:
            continue
        
        # Add separator between chapters (except before first chapter)
        if i > 0:
            merged_content.append("\n\n---\n\n")
        
        # Add chapter content
        merged_content.append(content)
        
        # Ensure there's a newline at the end
        if not content.endswith('\n'):
            merged_content.append('\n')
    
    # Write merged file
    # Sanitize filename from book title
    safe_filename = re.sub(r'[^\w\s-]', '', book_title)
    safe_filename = re.sub(r'[-\s]+', '-', safe_filename)
    safe_filename = safe_filename.lower()
    
    output_file = output_dir / f"{safe_filename}.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(merged_content))
    
    print(f"Created merged book: {output_file}")


def main():
    """Main function to merge all books."""
    # Get script directory and project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    docs_dir = project_root / "docs"
    summary_path = docs_dir / "SUMMARY.md"
    output_dir = project_root / "book" / "merged-books"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse SUMMARY.md
    print(f"Parsing {summary_path}...")
    books = parse_summary(summary_path)
    
    print(f"Found {len(books)} books")
    
    # Merge each book
    total_chapters = 0
    for book_title, chapter_paths in books:
        print(f"\nProcessing: {book_title}")
        print(f"  Chapters: {len(chapter_paths)}")
        total_chapters += len(chapter_paths)
        merge_book_chapters(book_title, chapter_paths, docs_dir, output_dir)
    
    print(f"\n{'='*60}")
    print(f"Done! Merged {len(books)} books ({total_chapters} total chapters)")
    print(f"Output directory: {output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

