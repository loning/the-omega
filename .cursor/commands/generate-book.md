# Book Generation Instructions

## Overview

This document provides detailed instructions for converting English Markdown files (`*_en.md`) in a book directory to LaTeX format and compiling them into PDF and EPUB books.

## Prerequisites

1. **LaTeX Distribution**: Install a LaTeX distribution (e.g., MacTeX on macOS, TeX Live on Linux)
2. **Pandoc**: Install `pandoc` for EPUB generation:
   ```bash
   brew install pandoc  # macOS
   ```
3. **latexpand**: Usually included with LaTeX distributions. If not available, install via:
   ```bash
   # On macOS with MacTeX, it's included
   # On Linux with TeX Live, install texlive-extra-utils
   ```
4. **Python 3**: For any helper scripts (if needed)

## Book Directory Structure

Books are typically organized as follows:

```
book-name/
├── assets/cover.png (book cover image, optional)
├── foreword_en.md (or preface_en.md, prologue_en.md)
├── part01-name/
│   └── chapter01-name/
│       ├── 01-01-section-name_en.md
│       ├── 01-02-section-name_en.md
│       └── ...
├── part02-name/
│   └── ...
├── appendix/
│   ├── appendix-a-name_en.md
│   ├── appendix-b-name_en.md
│   └── ...
├── afterword_en.md (or epilogue_en.md, back-cover_en.md)
└── index_en.md (optional, not converted)
```

## Step-by-Step Build Process

### Step 1: List and Verify Files

1. Navigate to the book directory
2. List all `*_en.md` files:
   ```bash
   find . -name "*_en.md" -type f | sort
   ```
3. Verify the count matches expected structure (exclude `index_en.md`)

### Step 2: Convert Markdown to LaTeX

For each `*_en.md` file, convert it to a corresponding `.tex` file using LLM conversion (NOT scripts). Key conversion rules:

#### 2.1 Header Conversion

- `# Title` → `\section{Title}` (for subsections within chapters)
- `## Subtitle` → `\subsection{Subtitle}`
- `### Sub-subtitle` → `\subsubsection{Sub-subtitle}`
- Note: Chapter and part titles are handled by the main LaTeX file

#### 2.2 Math Conversion

- Inline math: `$...$` → `$...$` (keep as is)
- Display math: `$$...$$` → `\[...\]` or `\begin{equation}...\end{equation}`
- Math blocks: Ensure proper LaTeX math mode syntax

#### 2.3 Image Conversion

- Markdown: `![alt](path/to/image.png)`
- LaTeX: `\begin{figure}[h]\centering\includegraphics[width=0.8\textwidth]{path/to/image.png}\caption{alt}\end{figure}`

**Critical: Image Path Resolution**

When converting images from Markdown to LaTeX, **image paths must be relative to the main LaTeX file location**, NOT relative to the individual `.tex` file being converted.

**Common Issue**: Markdown files often use paths like `../../assets/images/chapter01/image.png` which are relative to the Markdown file's location. When converting to LaTeX, these paths must be adjusted to be relative to the main `.tex` file.

**Example**:
- If main LaTeX file is at: `book-name/book-name.tex`
- If images are at: `book-name/assets/images/chapter01/image.png`
- If chapter file is at: `book-name/volume01/chapter01/01-01-section_en.tex`

Then in the `.tex` file, use: `assets/images/chapter01/image.png` (NOT `../../assets/images/chapter01/image.png`)

**Conversion Rule**:
- Replace `../../assets/images/` → `assets/images/` (or adjust based on actual directory structure)
- Always verify paths are correct relative to where the main `.tex` file will be located
- Use `\graphicspath{{./}}` in the preamble to set the base path for images

#### 2.4 List Conversion

- Unordered lists: `- item` → `\begin{itemize}\item item\end{itemize}`
- Ordered lists: `1. item` → `\begin{enumerate}\item item\end{enumerate}`
- Nested lists: Preserve nesting structure

#### 2.5 Emphasis Conversion

- `**bold**` → `\textbf{bold}`
- `*italic*` → `\textit{italic}`
- `` `code` `` → `\texttt{code}`

#### 2.6 Special Characters

- Escape special LaTeX characters: `&`, `%`, `$`, `#`, `^`, `_`, `{`, `}`, `~`, `\`
- Handle underscores in text: Use `\_` or wrap in `\texttt{}` for code-like text (e.g., `Self_v1.0` → `\texttt{Self\_v1.0}` or `$Self_{v1.0}$`)

#### 2.7 Code Blocks

- Markdown code blocks: Convert to `\begin{verbatim}...\end{verbatim}` or `\texttt{}` for inline code

### Step 3: Create Main LaTeX File

Create a main `.tex` file (e.g., `book-name.tex`) with the following structure:

#### 3.1 Preamble

```latex
\documentclass[11pt,a4paper,twoside]{book}

% Packages
\usepackage[english]{babel}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{geometry}
\geometry{a4paper,left=2.5cm,right=2.5cm,top=3cm,bottom=3cm}
\usepackage{graphicx}
\graphicspath{{./}}
\usepackage{hyperref}
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    filecolor=magenta,
    urlcolor=cyan,
    pdftitle={Book Title},
    pdfauthor={Author Name}
}
\usepackage{microtype}
\usepackage{enumitem}
\usepackage{csquotes}

% Title information
\title{Book Title\\[0.5em]
\large Subtitle (if any)}
\author{Author Name}
\date{Date}

\begin{document}
```

#### 3.2 Document Structure

```latex
% Title page
\maketitle
\thispagestyle{empty}

% Cover page (if assets/cover.png exists)
\IfFileExists{assets/cover.png}{
  \newpage
  \thispagestyle{empty}
  \centering
  \includegraphics[width=\paperwidth,height=\paperheight,keepaspectratio]{assets/cover.png}
  \newpage
}{}

\frontmatter

% Table of contents
\tableofcontents

% Foreword/Preface/Prologue
\include{foreword_en}  % or preface_en, prologue_en

\mainmatter

% Part I
\part{Part Title}

% Chapter 1
\chapter{Chapter Title}
\input{path/to/01-01-section-name_en.tex}
\input{path/to/01-02-section-name_en.tex}
% ... more sections

% Chapter 2
\chapter{Chapter Title}
\input{path/to/02-01-section-name_en.tex}
% ... more sections

% Part II
\part{Part Title}
% ... more chapters

\appendix

% Appendix A
\chapter{Appendix Title}
\input{appendix/appendix-a-name_en.tex}

% Appendix B
\chapter{Appendix Title}
\input{appendix/appendix-b-name_en.tex}

\backmatter

% Afterword/Epilogue/Back Cover
\include{afterword_en}  % or epilogue_en, back-cover_en

\end{document}
```

#### 3.3 Important Notes

- Use `\include{}` for major sections (foreword, afterword) that should start on new pages
- Use `\input{}` for chapter subsections
- Ensure all paths are relative to the main `.tex` file location
- Do NOT use `\subtitle{}` command (not standard in `book` class)
- **Cover image**: If `assets/cover.png` exists in the book directory, it will be automatically included as a cover page in PDF after the title page. For EPUB, use `--epub-cover-image=assets/cover.png` option with pandoc.

### Step 4: Compile PDF

1. First compilation:
   ```bash
   cd /path/to/book-directory
   pdflatex book-name.tex
   ```

2. Second compilation (for table of contents and cross-references):
   ```bash
   pdflatex book-name.tex
   ```

3. Verify PDF generation:
   ```bash
   ls -lh book-name.pdf
   ```

#### 4.1 Common LaTeX Errors and Fixes

- **Undefined control sequence**: Check for non-standard commands (e.g., `\subtitle`) and remove or replace
- **Missing $ inserted**: Ensure math mode is properly closed, or escape underscores in text
- **Extra }, or forgotten $**: Check for unclosed math mode or mismatched braces
- **Command invalid in math mode**: Ensure `\item`, `\end{itemize}`, etc. are outside math mode
- **Package pdftex.def Error: File `...` not found**: This indicates image path errors
  - **Cause**: Image paths in `\includegraphics{}` are incorrect relative to the main `.tex` file
  - **Fix**: Update all image paths in `.tex` files to be relative to the main `.tex` file location
  - **Example**: Change `../../assets/images/chapter01/image.png` to `assets/images/chapter01/image.png`
  - **Verification**: Check that PDF file size increases significantly after fixing (images are embedded)
  - **Quick fix script**: Use regex to replace `../../assets/images/` with `assets/images/` in all `*_en.tex` files

### Step 5: Compile EPUB

**Important**: Pandoc cannot directly process LaTeX `\include{}` and `\input{}` commands. You must first merge all included files into a single LaTeX file using `latexpand`.

1. Check if required tools are installed:
   ```bash
   which pandoc
   which latexpand
   ```

2. Merge all LaTeX files into a single file:
   ```bash
   cd /path/to/book-directory
   latexpand book-name.tex > book-name-merged.tex
   ```
   
   **Note**: If `latexpand` reports errors, check the merged file and fix any syntax issues (e.g., extra braces, unclosed math mode).

3. Convert merged LaTeX file to EPUB:
   ```bash
   # If assets/cover.png exists, add --epub-cover-image=assets/cover.png
   if [ -f assets/cover.png ]; then
     pandoc book-name-merged.tex -o book-name.epub \
       --from=latex+raw_tex \
       --to=epub3 \
       --metadata title="Book Title" \
       --metadata author="Author Name" \
       --epub-cover-image=assets/cover.png \
       --toc --toc-depth=3 \
       --mathml
   else
     pandoc book-name-merged.tex -o book-name.epub \
       --from=latex+raw_tex \
       --to=epub3 \
       --metadata title="Book Title" \
       --metadata author="Author Name" \
       --toc --toc-depth=3 \
       --mathml
   fi
   ```
   
   **Key options**:
   - `--from=latex+raw_tex`: Enables raw LaTeX processing for better compatibility
   - `--to=epub3`: Generates EPUB3 format
   - `--mathml`: Ensures math formulas are properly rendered
   - `--epub-cover-image=assets/cover.png`: Sets the cover image (if assets/cover.png exists in the book directory)
   
   \*\*Note\*\*: If `assets/cover.png` doesn\\'t exist, omit the `--epub-cover-image` option or the command will fail.

4. Fix MathML property declaration (EPUB3 compliance):
   ```bash
   # Fix MathML property in nav.xhtml if needed
   ./scripts/fix_epub_mathml.sh book-name.epub
   ```
   
   **Note**: Pandoc doesn't automatically add the `mathml` property to `nav.xhtml` in the OPF manifest when the navigation document contains MathML. This script automatically detects and fixes this issue to ensure EPUB3 compliance.

5. Verify EPUB generation:
   ```bash
   ls -lh book-name.epub
   ```
   
   **Check file size**: The EPUB should be significantly larger than a few KB (typically 50KB+ for a complete book). If the file is too small (e.g., < 20KB), it likely means content wasn't included properly.

6. Clean up temporary merged file:
   ```bash
   rm book-name-merged.tex
   ```

#### 5.1 Common EPUB Generation Issues

- **EPUB file too small (< 20KB)**: This usually means `\include{}` and `\input{}` commands weren't processed. Use `latexpand` to merge files first.
- **Pandoc parsing errors**: Check the merged LaTeX file for syntax errors (extra braces, unclosed math mode, etc.) and fix them before regenerating EPUB.
- **Missing content in EPUB**: Verify that all included `.tex` files exist and are readable.
- **EPUB validation error (OPF-014)**: If `nav.xhtml` contains MathML, the `mathml` property must be declared in the OPF manifest. Use `fix_epub_mathml.sh` script to automatically fix this issue.

## Conversion Guidelines

### File Naming Convention

- Input: `*_en.md` files
- Output: Corresponding `*_en.tex` files (same name, different extension)
- Main file: `book-name.tex` (derived from directory name)

### Path Handling

- All `\input{}` and `\include{}` paths should be relative to the main `.tex` file
- **Image paths in `\includegraphics{}` must be relative to the main `.tex` file location**
  - When converting from Markdown, paths like `../../assets/images/` need to be changed to `assets/images/`
  - The path is resolved from the main `.tex` file's directory, not from individual chapter `.tex` files
  - Use `\graphicspath{{./}}` in the preamble to set the base search path for images
  - **Common mistake**: Using paths relative to the chapter file (e.g., `../../assets/`) instead of relative to the main file (e.g., `assets/`)

### Content Preservation

- Preserve all mathematical notation exactly
- Maintain original formatting and structure
- Keep all citations and references intact
- Preserve code blocks and technical content

## Quality Checklist

Before finalizing, verify:

- [ ] All `*_en.md` files have been converted to `.tex`
- [ ] Main LaTeX file includes all parts, chapters, and appendices
- [ ] PDF compiles without errors
- [ ] Table of contents is generated correctly
- [ ] EPUB file is generated successfully and has reasonable size (> 50KB for a complete book)
- [ ] MathML property is correctly declared in OPF manifest (use `fix_epub_mathml.sh` if needed)
- [ ] All images are included (if any)
  - [ ] Verify image paths are correct relative to main `.tex` file
  - [ ] Check PDF file size is reasonable (should be larger if images are embedded)
  - [ ] No "File not found" errors in compilation log for images
- [ ] Cover image (if assets/cover.png exists)
  - [ ] Cover page appears correctly in PDF after title page
  - [ ] EPUB cover image is set using `--epub-cover-image=assets/cover.png` option
- [ ] Mathematical formulas render correctly
- [ ] Special characters are properly escaped

## Example Workflow

```bash
# 1. Navigate to book directory
cd /path/to/book-directory

# 2. List all files to convert
find . -name "*_en.md" -type f | sort

# 3. Convert each file (using LLM, not scripts)
# ... convert foreword_en.md to foreword_en.tex
# ... convert all chapter files
# ... convert appendix files
# ... convert afterword_en.md to afterword_en.tex

# 4. Create main LaTeX file
# ... create book-name.tex with proper structure

# 5. Compile PDF
pdflatex book-name.tex
pdflatex book-name.tex

# 6. Merge LaTeX files for EPUB generation
latexpand book-name.tex > book-name-merged.tex

# 7. Compile EPUB
# If assets/cover.png exists, add --epub-cover-image=assets/cover.png
if [ -f assets/cover.png ]; then
  pandoc book-name-merged.tex -o book-name.epub \
    --from=latex+raw_tex \
    --to=epub3 \
    --metadata title="Book Title" \
    --metadata author="Author Name" \
    --epub-cover-image=assets/cover.png \
    --toc --toc-depth=3 \
    --mathml
else
  pandoc book-name-merged.tex -o book-name.epub \
    --from=latex+raw_tex \
    --to=epub3 \
    --metadata title="Book Title" \
    --metadata author="Author Name" \
    --toc --toc-depth=3 \
    --mathml
fi


# 8. Fix MathML property declaration (EPUB3 compliance)
./scripts/fix_epub_mathml.sh book-name.epub

# 9. Clean up
rm book-name-merged.tex
```

## Helper Scripts

### `build_epub.sh` - Complete EPUB Build Script

Automates the entire EPUB generation process from LaTeX source:

```bash
./scripts/build_epub.sh <book-directory> [main-tex-file]
```

**Features**:
- Merges LaTeX files using `latexpand`
- Generates EPUB with `pandoc`
- Automatically fixes MathML property declaration
- Extracts metadata from LaTeX file
- Cleans up all temporary files

**Example**:
```bash
./scripts/build_epub.sh docs/books/book-name book-name.tex
```

### `fix_epub_mathml.sh` - EPUB MathML Property Fix

Fixes MathML property declaration in existing EPUB files:

```bash
./scripts/fix_epub_mathml.sh <epub-file>
```

**Features**:
- Only processes existing EPUB files (no recompilation)
- Automatically detects if `nav.xhtml` contains MathML
- Adds `mathml` property to OPF manifest
- Creates backup before modification
- Cleans up all temporary files

**Example**:
```bash
./scripts/fix_epub_mathml.sh docs/books/book-name/book-name.epub
```

**Use cases**:
- Quick fix for existing EPUB files
- Batch processing multiple EPUB files
- Post-processing EPUB files generated by other tools

## Notes

- **Do NOT use scripts** for conversion - use LLM for content transformation
- **Do NOT edit plan files** - only implement the plan
- **Mark todos as in_progress** when starting work
- **Fix errors immediately** - don't leave compilation errors unresolved
- **Preserve academic rigor** - maintain formatting and mathematical notation accuracy
- **EPUB3 compliance**: Always run `fix_epub_mathml.sh` after generating EPUB files to ensure MathML properties are correctly declared

