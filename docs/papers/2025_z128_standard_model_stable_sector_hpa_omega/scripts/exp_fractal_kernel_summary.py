# -*- coding: utf-8 -*-
"""
Kernel-summary table: cross-m sweep of core kernel quantities.

This script is a compact companion to the "kernel view" section. It reports,
for a small m-sweep:
  - admissible counts |X_m| and the pi-channel split,
  - folding maximal degeneracy r_m := max_w |Fold_m^{-1}(w)|,
  - per-step log rates (1/m) log |X_m| and (1/m) log r_m.

Output (LaTeX fragment):
  - sections/generated/fractal_kernel_sweep_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import List

from common_paths import generated_dir
from common_tex import write_lines
from protocol_kernel import all_xm, max_degeneracy, split_cyc_bdry


def main() -> None:
    # Keep the sweep consistent with other uplift tables in this paper.
    m_list = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

    rows: List[str] = []
    for m in m_list:
        Xm = all_xm(m)
        cyc, bdry = split_cyc_bdry(Xm)

        rm = max_degeneracy(m)

        # Natural-log rates; \log is defined as natural log in the paper conventions.
        cap_rate = math.log(len(Xm)) / float(m)
        red_rate = math.log(float(rm)) / float(m)

        rows.append(
            f"{m} & {len(Xm)} & {len(cyc)} & {len(bdry)} & {rm} & {cap_rate:.6f} & {red_rate:.6f} \\\\"
        )

    rows.append("\\bottomrule")

    out_path = generated_dir() / "fractal_kernel_sweep_rows.tex"
    write_lines(out_path, rows)
    print("Wrote sections/generated/fractal_kernel_sweep_rows.tex")


if __name__ == "__main__":
    main()

