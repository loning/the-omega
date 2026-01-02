#!/usr/bin/env python3
"""
Script to copy main.pdf files from docs/papers/ subdirectories (including nested subdirectories) to book/merged-papers/
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
    
    # Recursively find all main.pdf files in subdirectories
    main_pdfs = list(papers_dir.rglob("main.pdf"))
    
    copied_count = 0
    skipped_count = 0
    
    print(f"Scanning {papers_dir} (recursively)...")
    print(f"Found {len(main_pdfs)} main.pdf files\n")
    
    for main_pdf in sorted(main_pdfs):
        paper_dir = main_pdf.parent
        
        # Skip if directory name starts with '.'
        if paper_dir.name.startswith('.'):
            continue
        
        # Use directory name as output filename
        output_filename = f"{paper_dir.name}.pdf"
        output_path = output_dir / output_filename
        
        try:
            shutil.copy2(main_pdf, output_path)
            # Show relative path from papers_dir for nested directories
            rel_path = paper_dir.relative_to(papers_dir)
            print(f"✓  Copied: {rel_path} -> {output_filename}")
            copied_count += 1
        except Exception as e:
            rel_path = paper_dir.relative_to(papers_dir)
            print(f"✗  Error copying {rel_path}: {e}")
            skipped_count += 1
    
    print(f"\n{'='*60}")
    print(f"Done! Copied {copied_count} PDFs, skipped {skipped_count}")
    print(f"Output directory: {output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

