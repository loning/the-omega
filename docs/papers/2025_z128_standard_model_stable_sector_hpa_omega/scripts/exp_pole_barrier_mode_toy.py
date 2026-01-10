# -*- coding: utf-8 -*-
"""
Pole-barrier mode toy (audit / explanatory alignment).

This script emits a tiny deterministic table illustrating an \"interior pole\"
threshold in a normalized unit-disc parameter r:
  r_* = exp(-delta), delta >= 0.

The point is not to claim a theorem-level identification, but to provide a clean,
reproducible numeric placeholder that aligns the paper's pole-barrier normalization
language with companion trace-formula discussions.

Outputs (LaTeX fragment):
  - sections/generated/pole_barrier_mode_toy_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import List

from common_paths import generated_dir
from common_tex import write_lines


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    delta_list = [0.0, 0.05, 0.10, 0.20]
    rows: List[str] = []
    for delta in delta_list:
        r_star = math.exp(-delta)
        rows.append(f"{_fmt(delta)} & {_fmt(r_star)} \\\\")

    rows.append("\\bottomrule")

    out = generated_dir() / "pole_barrier_mode_toy_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/pole_barrier_mode_toy_rows.tex")


if __name__ == "__main__":
    main()

