# Resolution Folding and Auditable Sofic Factors (English, multi-tex)

本目录是一篇英文、多 `.tex` 拆分论文工程，主线为
\[
\Omega_m\ (\text{finite-window microstates})
\;\xrightarrow{\ \Fold_m\ }\;
X_m\ (\text{canonical folded types})
\;\xrightarrow{\ \Phi_m\ }\;
Y_m\ (\text{sofic factor with computable covers})
\;\Longrightarrow\;
\text{information ledger identity and auditable certificates}.
\]

## Structure

- `main_en.tex`: Root compilation entry (full build).
- `main_fast_en.tex`: Fast build entry (`\FASTBUILD`).
- `references.bib`: BibTeX database (copied from the source paper for consistency).
- `sections/`
  - `frontmatter/`: title, abstract, contribution list, structure overview.
  - `body/`: Section 1–9 (each in its own subdirectory with `main_en.tex`).
  - `appendix/`: Appendix A–D.
  - `backmatter/`: bibliography entry.
  - `generated/`: pipeline-generated LaTeX snippets (write-only; do not edit by hand).
- `scripts/`: reproducibility pipeline entry (`run_all.py`) and path helpers.
- `artifacts/`: exported audit artifacts (CSV/PNG/JSON, etc.). (Created by scripts.)

## Compile (do not run unless explicitly requested)

Fast build:

```bash
latexmk -pdfxe -interaction=nonstopmode -halt-on-error -file-line-error main_fast_en.tex
```

Full build:

```bash
latexmk -pdfxe -interaction=nonstopmode -halt-on-error -file-line-error main_en.tex
```

Directory-level compilation (quick check): enter a directory containing `main_en.tex` and compile it.

## Reproducible pipeline

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run the pipeline:

```bash
python3 scripts/run_all.py
```

The pipeline will write:

- `sections/generated/*.tex`
- `artifacts/export/*`

Registered steps (see `python3 scripts/run_all.py --list`):

- **collision_moments**: brute-force enumerations of collision moments \(S_k(m)\) for small \(m\); exports `artifacts/export/collision_moments.csv` and `sections/generated/tab_collision_rates.tex`.
- **moment_kernel_spectra**: compiles moment-kernel spectra from the delay-\(3\) online transducer; exports `artifacts/export/moment_kernel_spectra.csv` and `sections/generated/tab_moment_kernel_spectra.tex`.

## Writing and splitting conventions

- Each content file should define a **primary label** at its first major anchor (e.g. `\section`, `\subsection`, `\begin{theorem}`).
- A single `.tex` file should stay under **800 lines**; split if needed.
- `sections/generated/` is script-generated and must not be edited by hand.

