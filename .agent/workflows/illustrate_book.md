---
description: How to illustrate a book project by generating and managing AI images.
---

This workflow outlines the process for illustrating a book project using AI-generated images. It covers preparation, planning, and generation.

# Phase 1: Preparation & Discovery

1.  **Analyze Book Structure**:
    - Use `list_dir` to understand the directory structure (Parts, Chapters, Sections).
    - Identify the root directory of the book (e.g., `docs/books/book-name`).
    - Locate or create an `assets` directory for storing images.

2.  **Initialize Task Tracking**:
    - Create or update `task.md` in the brain directory.
    - List all parts and chapters as checklist items.
    - Add subtasks for "Plan Prompts" and "Generate Images" for each section.

3.  **Art Style**:
    - 赛博科幻未来时间与光

# Phase 2: Cover Image

2.  **Cover Image**:
    - **Prompt Strategy**: Design a **B5 Ebook Cover (Center Safe)**.
    - **Format Requirements**:
        - **Source Canvas**: Square (1024x1024).
        - **Safe Zone**: **CRITICAL**: The B5 cut is the central 724px.
        - **Instruction**: "Ensure ALL text and key art are strictly in the central 74%. The side 12% edges must be **seamless background extensions** (e.g., continuing the stars/void)."
        - **Negative Prompt**: **NO vertical dividing lines, NO frames, NO visible borders, NO sidebars.** The image must look like one continuous scene, not a strip cut out of a page.
    - **Content Requirements**:
        - **Title**: High contrast, centered, fully inside the safe zone.
        - **Subtitle**: Centered, safe from edges.
        - **Metadata**: Centered at bottom.
        - **Design**: "Vertical Composition", "Center-Heavy", "Seamless Bleed".
    - **Process**:
        - Generate the image with 8k resolution. Save as `assets/cover.png`.
        - **Post-Process (Center Crop to B5)**:
            - Use the Python script to crop the sides.
            - Command: `python3 .agent/scripts/crop_cover.py assets/cover.png 724 1024`

# Phase 3: Illustration Loop

*Repeat this cycle for each Chapter or Section.*

1.  **Read & Analyze**:
    - Use `view_file` to read the content of the target chapter or section.
    - Identify core themes, key metaphors, and visualizable concepts (e.g., "Gravity as Slope", "Observer as Seed").
    - **Identify Complex Concepts**: Specifically look for complex mathematical formulas, abstract theories, or dense logic that requires visual decoding.

2.  **Design Prompts & Generate**:
    - **Style Guide**: Create a consistent style guide (e.g., "Abstract scientific illustration, clean lines, golden/blue color palette").
    - **Content Relevance**: Ensure the image reflects the **specific details** of the content (specific metaphors, objects, or descriptions), avoiding valid but generic representations.
    - **Explanatory Images**: For identified complex concepts/formulas, design "Diagrammatic" or "Explanatory" prompts.
        - *Goal*: Explain the logic/structure visually.
        - *Keywords*: Use terms like "infographic," "diagram," "schematic," "exploded view," "visual breakdown," "annotated structure."
        - *Detail*: Describe the elements of the formula/concept metaphorically.
    - **Generate**:
        - Use `generate_image` immediately with the designed prompt.
        - Use descriptive `ImageName`.

3.  **Organize & Track**:
    - **Move Images**: Use `run_command` to move generated images from the brain directory to the book's `assets` folder.
        - Rename pattern: `mv /path/to/brain/image.png /path/to/book/assets/chapter-[n]/[n-n]-position-image.png`
    - **Update Task List**: Use `multi_replace_file_content` to mark the completed items in `task.md` as `[x]`.

# Phase 4: Finalization

1.  **Special Sections**:
    - Repeat the process for the `Foreword`, `Introduction`, and `Appendices`.

2.  **Final Review**:
    - Ensure all tasks in `task.md` are marked complete.