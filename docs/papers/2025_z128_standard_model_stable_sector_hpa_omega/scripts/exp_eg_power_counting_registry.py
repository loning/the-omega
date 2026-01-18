# -*- coding: utf-8 -*-
"""
Generate a compact EG power-counting / extension registry as a LaTeX fragment.

This is a small deterministic registry table used by the strong-closure appendices.
Only the Python standard library is used.
"""

from __future__ import annotations

from common_paths import generated_dir
from common_tex import write_lines


def main() -> None:
    # Keep the registry explicit and auditable; no computation is required here.
    rows = [
        r"$\mathrm{sd}(t)<d$ & unique extension (no counterterm freedom) \\",
        r"$\mathrm{sd}(t)\ge d$ & finite-dimensional local ambiguity (counterterms) \\",
        r"fixed truncation $(D_{\max},L_{\max})$ & finite normalization freedom at each order \\",
        r"anomaly-free cohomology & ST/BRST restoration by local counterterms \\",
        # No trailing \\ before \bottomrule to avoid booktabs alignment edge cases.
        r"nontrivial anomaly class & obstruction (no ST restoration)",
    ]

    out = generated_dir() / "eg_power_counting_registry_rows.tex"
    write_lines(out, rows)


if __name__ == "__main__":
    main()

