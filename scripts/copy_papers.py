#!/usr/bin/env python3
"""
Script to copy main.pdf files from docs/papers/ subdirectories to book/merged-papers/
Each PDF is renamed using the subdirectory name.
"""

import os
import shutil
from pathlib import Path


def main():
    """Main function to copy all paper PDFs."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    papers_dir = project_root / "docs" / "papers"
    output_dir = project_root / "book" / "merged-papers"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all subdirectories in papers_dir
    paper_dirs = [d for d in papers_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    copied_count = 0
    skipped_count = 0
    
    print(f"Scanning {papers_dir}...")
    print(f"Found {len(paper_dirs)} paper directories\n")
    
    for paper_dir in sorted(paper_dirs):
        main_pdf = paper_dir / "main.pdf"
        
        if not main_pdf.exists():
            print(f"⚠️  Skipping {paper_dir.name}: main.pdf not found")
            skipped_count += 1
            continue
        
        # Use directory name as output filename
        output_filename = f"{paper_dir.name}.pdf"
        output_path = output_dir / output_filename
        
        try:
            shutil.copy2(main_pdf, output_path)
            print(f"✓  Copied: {paper_dir.name} -> {output_filename}")
            copied_count += 1
        except Exception as e:
            print(f"✗  Error copying {paper_dir.name}: {e}")
            skipped_count += 1
    
    print(f"\n{'='*60}")
    print(f"Done! Copied {copied_count} PDFs, skipped {skipped_count}")
    print(f"Output directory: {output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

