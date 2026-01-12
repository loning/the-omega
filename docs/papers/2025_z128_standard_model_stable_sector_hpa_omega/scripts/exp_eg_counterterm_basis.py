# -*- coding: utf-8 -*-
"""
Generate a deterministic EG counterterm-basis registry table as a LaTeX fragment.

This does NOT attempt symbolic enumeration of all gauge-invariant monomials.
Instead, it records an auditable basis principle by (dimension, ghost number) sectors,
and points to the paper's operator-basis dictionary.

Only the Python standard library is used.
"""

from __future__ import annotations

from common_paths import generated_dir
from common_tex import write_lines


def main() -> None:
    # Keep entries ASCII-only (pdfLaTeX compatibility).
    rows = [
        r"2 & 0 & Mass-dimension-2 sectors (e.g. gauge-fixing/auxiliary terms if declared) \\",
        r"3 & 0 & No CPT-even renormalizable local invariants in the minimal SM gauge sector (registry-specific) \\",
        r"4 & 0 & Renormalizable gauge-invariant operators (SM kinetic + Yukawa + Higgs potential) \\",
        r"4 & 1 & Ghost-number-1 local functionals controlling ST breaking (candidate anomaly sector) \\",
        r"5 & 0 & Dimension-5 EFT operators (e.g. Weinberg operator sector, if included in truncation) \\",
        r"6 & 0 & Dimension-6 EFT basis sector (finite operator dictionary at fixed truncation) \\",
    ]
    out = generated_dir() / "eg_counterterm_basis_rows.tex"
    write_lines(out, rows)


if __name__ == "__main__":
    main()

