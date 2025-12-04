# Book Generation Instructions

## Overview

This document provides detailed instructions for converting English Markdown files (`*_en.md`) in a book directory to LaTeX format and compiling them into PDF and EPUB books.

## Prerequisites

1. **LaTeX Distribution**: Install a LaTeX distribution (e.g., MacTeX on macOS, TeX Live on Linux)
2. **Pandoc**: Install `pandoc` for EPUB generation:
   ```bash
   brew install pandoc  # macOS
   ```
3. **Python 3**: For any helper scripts (if needed)

## Book Directory Structure

Books are typically organized as follows:

```
book-name/
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
- Adjust paths relative to the main `.tex` file location

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

### Step 5: Compile EPUB

1. Check if pandoc is installed:
   ```bash
   which pandoc
   ```

2. Convert LaTeX to EPUB:
   ```bash
   pandoc book-name.tex -o book-name.epub \
     --metadata title="Book Title" \
     --metadata author="Author Name" \
     --metadata subtitle="Subtitle (if any)" \
     --toc --toc-depth=3 \
     --mathml
   ```

3. Verify EPUB generation:
   ```bash
   ls -lh book-name.epub
   ```

## Conversion Guidelines

### File Naming Convention

- Input: `*_en.md` files
- Output: Corresponding `*_en.tex` files (same name, different extension)
- Main file: `book-name.tex` (derived from directory name)

### Path Handling

- All `\input{}` and `\include{}` paths should be relative to the main `.tex` file
- Image paths in `\includegraphics{}` should be relative to the main `.tex` file or use `\graphicspath{{./}}`

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
- [ ] EPUB file is generated successfully
- [ ] All images are included (if any)
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

# 6. Compile EPUB
pandoc book-name.tex -o book-name.epub \
  --metadata title="Book Title" \
  --metadata author="Author Name" \
  --toc --toc-depth=3 --mathml
```

## Notes

- **Do NOT use scripts** for conversion - use LLM for content transformation
- **Do NOT edit plan files** - only implement the plan
- **Mark todos as in_progress** when starting work
- **Fix errors immediately** - don't leave compilation errors unresolved
- **Preserve academic rigor** - maintain formatting and mathematical notation accuracy

