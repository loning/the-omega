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
    - **Style Guide**: Create a consistent style guide (e.g., "Abstract scientific illustration, clean lines, golden/blue color palette").
    - **Content Relevance**: Ensure the image reflects the **specific details** of the content (specific metaphors, objects, or descriptions), avoiding valid but generic representations.
    - **General Prompts**: Draft specific prompts for each file, combining the style guide with the specific detailed concepts.
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
    - Example: `mv /path/to/brain/image.png /path/to/book/assets/chapter-[n]/image.png`

3.  **Embed Images**:
    - For each generated image, embed it into ALL of the following files if they exist:
    
    - **A. Chinese Markdown (`.md`)**:
        - Use `replace_file_content`.
        - Insert after the H1 title or relevant section header.
        - Format: `![Alt Text](../../assets/chapter-[n]/image_name.png)`

6.  **Update Task List**:
    - Use `multi_replace_file_content` to mark the completed items in `task.md` as `[x]`.

# Phase 4: Finalization

1.  **Special Sections**:
    - Repeat the process for the `Foreword`, `Introduction`, and `Appendices`.

3.  **Cover Image**:
    - **Prompt Strategy**: Design a **B5 Ebook Cover (Center Safe)**.
    - **Format Requirements**:
        - **Source Canvas**: Square (1024x1024).
        - **Safe Zone**: **CRITICAL**: The B5 cut is the central 724px.
        - **Instruction**: "Ensure ALL text and key art are strictly in the central 72%. The side 14% edges must be **seamless background extensions** (e.g., continuing the stars/void)."
        - **Negative Prompt**: **NO vertical dividing lines, NO frames, NO visible borders, NO sidebars.** The image must look like one continuous scene, not a strip cut out of a page.
    - **Content Requirements**:
        - **Title**: High contrast, centered, fully inside the safe zone.
        - **Subtitle**: Centered, safe from edges.
        - **Metadata**: Centered at bottom.
        - **Design**: "Vertical Composition", "Center-Heavy", "Seamless Bleed".
    - **Process**:
        - Generate the image with 8k resolution. Save as `cover.png`.
        - **Post-Process (Center Crop to B5)**:
            - Use the Python script to crop the sides.
            - Command: `python3 .agent/scripts/crop_cover.py assets/cover.png 724 1024`
        - Embed it at the top of the root `index.md`.

3.  **Final Review**:
    - Verify all links are correct.
    - Ensure all tasks in `task.md` are marked complete.