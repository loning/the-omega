---
description: How to illustrate a book project by generating, managing, and embedding AI images.
---

This workflow outlines the process for illustrating a book project using AI-generated images. It covers preparation, planning, generation, and embedding.

# Phase 1: Preparation & Discovery

1.  **Analyze Book Structure**:
    - Use `list_dir` to understand the directory structure (Parts, Chapters, Sections).
    - Identify the root directory of the book (e.g., `docs/books/book-name`).
    - Locate or create an `assets` directory for storing images.

2.  **Initialize Task Tracking**:
    - Create or update `task.md` in the brain directory.
    - List all parts and chapters as checklist items.
    - Add subtasks for "Plan Prompts", "Generate Images", and "Embed Images" for each section.

3.  **Analyze Art Style**:
    - Check the book root directory for existing visual assets like `architecture.png`.
    - If available, analyze its visual style (color palette, line weight, mood) to maintain consistency throughout the book.
    - Use this analysis to inform the Style Guide in Phase 2.

# Phase 2: Planning Prompts

1.  **Read Content**:
    - Use `view_file` to read the content of the target chapter or section.
    - Identify core themes, key metaphors, and visualizable concepts (e.g., "Gravity as Slope", "Observer as Seed").
    - **Identify Complex Concepts**: Specifically look for complex mathematical formulas, abstract theories, or dense logic that requires visual decoding.

2.  **Design Prompts**:
    - **Style Guide**: Create a consistent style guide (e.g., "Abstract scientific illustration, clean lines, golden/blue color palette, 8k resolution").
    - **General Prompts**: Draft specific prompts for each file, combining the style guide with the specific concept.
    - **Explanatory Images**: For identified complex concepts/formulas, design "Diagrammatic" or "Explanatory" prompts.
        - *Goal*: Explain the logic/structure visually.
        - *Keywords*: Use terms like "infographic," "diagram," "schematic," "exploded view," "visual breakdown," "annotated structure."
        - *Detail*: Describe the elements of the formula/concept metaphorically if exact text rendering is impossible. e.g., "Represent the equation terms as balancing weights on a scale."
    - *Tip*: Keep prompts concise but descriptive.

# Phase 3: Execution Loop (Per Batch)

*Repeat this cycle for each Part or batch of chapters.*

1.  **Generate Images**:
    - Use `generate_image` for each defined prompt.
    - Use descriptive `ImageName` (e.g., `the_slope`, `observer_trap`).
    - *Note*: Images are initially saved to the brain directory.

2.  **Move Images to Assets**:
    - Use `run_command` to move generated images from the brain directory to the book's `assets` folder.
    - Example: `mv /path/to/brain/image.png /path/to/book/assets/image.png`

3.  **Embed Images**:
    - For each generated image, embed it into ALL of the following files if they exist:
    
    - **A. Chinese Markdown (`.md`)**:
        - Use `replace_file_content`.
        - Insert after the H1 title or relevant section header.
        - Format: `![Alt Text](../../assets/image_name.png)`
    
    - **B. English Markdown (`_en.md`)**:
        - Use `replace_file_content`.
        - Insert after the H1 title or relevant section header.
        - Format: `![Alt Text](../../assets/image_name.png)`
    
    - **C. English LaTeX (`_en.tex`)**:
        - Use `replace_file_content`.
        - Locate the relevant `\section{...}` or `\chapter{...}`.
        - Insert standard LaTeX figure code **using relative path from the root .tex file** (usually `assets/image_name.png`).
        - Format:
          ```latex
          \begin{figure}[h]
              \centering
              \includegraphics[width=\textwidth]{assets/image_name.png}
              \caption{Image Title}
              \label{fig:image_name}
          \end{figure}
          ```
    
    - **D. Chinese LaTeX (`.tex`)**:
        - Same logic as English LaTeX.
        - Look for the file ending in `.tex` (without `_en`).
        - Insert the same LaTeX figure code.

6.  **Update Task List**:
    - Use `multi_replace_file_content` to mark the completed items in `task.md` as `[x]`.

# Phase 4: Finalization

1.  **Special Sections**:
    - Repeat the process for the `Foreword`, `Introduction`, and `Appendices`.

2.  **Cover Image**:
    - Design a premium cover image that encapsulates the book's entire theme.
    - Generate it and save it as `cover.png` in `assets`.
    - Embed it at the top of the root `index.md`.

3.  **Final Review**:
    - Verify all links are correct.
    - Ensure all tasks in `task.md` are marked complete.
