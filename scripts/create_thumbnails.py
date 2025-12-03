#!/usr/bin/env python3
"""
Create thumbnails for all architecture.png files in the docs/books directory.
"""
import os
from pathlib import Path
from PIL import Image

def create_thumbnail(input_path, output_path, max_size=(800, 800), quality=85):
    """Create a thumbnail from an image."""
    try:
        img = Image.open(input_path)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        img.save(output_path, 'PNG', optimize=True)
        print(f"✓ Created thumbnail: {output_path}")
        return True
    except Exception as e:
        print(f"✗ Error processing {input_path}: {e}")
        return False

def main():
    # Base directory
    base_dir = Path(__file__).parent.parent
    books_dir = base_dir / "docs" / "books"
    
    # Find all architecture.png files
    architecture_files = list(books_dir.rglob("architecture.png"))
    
    if not architecture_files:
        print("No architecture.png files found.")
        return
    
    print(f"Found {len(architecture_files)} architecture.png files.")
    print("Creating thumbnails...\n")
    
    success_count = 0
    for arch_file in architecture_files:
        # Create thumbnail path
        thumb_path = arch_file.parent / "architecture-thumb.png"
        
        # Create thumbnail
        if create_thumbnail(arch_file, thumb_path):
            success_count += 1
    
    print(f"\n✓ Successfully created {success_count}/{len(architecture_files)} thumbnails.")

if __name__ == "__main__":
    main()

