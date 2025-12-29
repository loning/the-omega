# -*- coding: utf-8 -*-
"""
Generate a small LaTeX table fragment for the mean degeneracy scaling of Fold_m.

Writes:
  sections/generated/foldm_scaling_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from pathlib import Path


def fib(n: int) -> int:
    """Fibonacci numbers with F1=1, F2=1."""
    if n <= 0:
        raise ValueError("n must be positive.")
    if n <= 2:
        return 1
    a, b = 1, 1
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    phi = (1.0 + math.sqrt(5.0)) / 2.0

    rows = []
    for m in range(2, 13):
        two_m = 1 << m
        f = fib(m + 2)
        mean = two_m / f
        normalized = mean * ((phi / 2.0) ** m)
        rows.append(f"{m} & {two_m} & {f} & {mean:.6f} & {normalized:.6f} \\\\")

    rows.append("\\bottomrule")

    # Avoid trailing blank line inside tabular (can break booktabs rules).
    (out_dir / "foldm_scaling_rows.tex").write_text("\n".join(rows), encoding="utf-8")


if __name__ == "__main__":
    main()


