#!/usr/bin/env python3
"""
Batch translate all Chinese LaTeX files to English versions (_en.tex).
This script reads Chinese .tex files and creates corresponding _en.tex files.
"""

import os
import sys
import time
from pathlib import Path
from anthropic import Anthropic

# Initialize Anthropic client
client = Anthropic()

BASE_DIR = Path(__file__).parent
SECTIONS_DIR = BASE_DIR / "sections"

TRANSLATION_SYSTEM_PROMPT = """You are a professional academic translator specializing in mathematics and theoretical physics.
Translate the following Chinese LaTeX document to English, maintaining:
1. All LaTeX commands, labels, and references exactly as they are
2. Mathematical notation and formatting
3. Academic rigor and precision
4. Technical terminology accuracy
5. The original document structure

Guidelines:
- Translate only the Chinese text content, not LaTeX commands
- Keep all \\label{}, \\ref{}, \\cite{} references unchanged
- Maintain mathematical expressions in LaTeX unchanged
- Use formal academic English
- Preserve paragraph breaks and formatting
- Do NOT add any commentary, notes, or explanations
- Output ONLY the translated LaTeX content"""


def find_files_to_translate():
    """Find all .tex files that need translation (excluding *_en.tex and generated/)."""
    files_to_translate = []

    for tex_file in SECTIONS_DIR.rglob("*.tex"):
        # Skip if already English version
        if tex_file.name.endswith("_en.tex"):
            continue

        # Skip generated files
        if "generated" in tex_file.parts:
            continue

        # Check if English version already exists
        en_version = tex_file.with_name(tex_file.stem + "_en.tex")

        # Add to list (we'll translate/update all)
        files_to_translate.append(tex_file)

    return sorted(files_to_translate)


def translate_file_content(content: str) -> str:
    """Translate Chinese LaTeX content to English using Claude API."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=16000,
            temperature=0.3,
            system=TRANSLATION_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Translate this LaTeX document to English:\n\n{content}"
                }
            ]
        )

        return message.content[0].text.strip()

    except Exception as e:
        print(f"  ERROR during translation: {e}", file=sys.stderr)
        raise


def translate_file(source_file: Path, force: bool = False):
    """Translate a single file to its _en.tex version."""

    en_file = source_file.with_name(source_file.stem + "_en.tex")

    # Check if already exists and not forcing
    if en_file.exists() and not force:
        print(f"  SKIP (already exists): {en_file.relative_to(BASE_DIR)}")
        return

    print(f"  TRANSLATING: {source_file.relative_to(BASE_DIR)}")

    # Read source file
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  ERROR reading {source_file}: {e}", file=sys.stderr)
        return

    # If file is already in English (no Chinese characters), just copy
    if not any('\u4e00' <= char <= '\u9fff' for char in content):
        print(f"  NO CHINESE FOUND, copying: {source_file.relative_to(BASE_DIR)}")
        with open(en_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return

    # Translate content
    try:
        translated = translate_file_content(content)
    except Exception as e:
        print(f"  FAILED: {source_file.relative_to(BASE_DIR)}", file=sys.stderr)
        return

    # Write translated file
    try:
        with open(en_file, 'w', encoding='utf-8') as f:
            f.write(translated)
        print(f"  WRITTEN: {en_file.relative_to(BASE_DIR)}")
    except Exception as e:
        print(f"  ERROR writing {en_file}: {e}", file=sys.stderr)
        return


def main():
    """Main translation workflow."""

    print("=" * 80)
    print("LaTeX Translation Tool: Chinese to English")
    print("=" * 80)

    # Find all files
    files_to_translate = find_files_to_translate()
    total = len(files_to_translate)

    print(f"\nFound {total} files to process")
    print("-" * 80)

    # Process each file
    start_time = time.time()
    for idx, file_path in enumerate(files_to_translate, 1):
        elapsed = time.time() - start_time
        avg_time = elapsed / idx if idx > 0 else 0
        remaining = avg_time * (total - idx)

        print(f"\n[{idx}/{total}] Progress: {idx/total*100:.1f}% | "
              f"Elapsed: {elapsed:.1f}s | ETA: {remaining:.1f}s")

        try:
            translate_file(file_path, force=False)
        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Exiting gracefully...")
            sys.exit(1)
        except Exception as e:
            print(f"  UNEXPECTED ERROR: {e}", file=sys.stderr)
            continue

    # Summary
    total_time = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"Translation complete!")
    print(f"Total files processed: {total}")
    print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print("=" * 80)


if __name__ == "__main__":
    main()
