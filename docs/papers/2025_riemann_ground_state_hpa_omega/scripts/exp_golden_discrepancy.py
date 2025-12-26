#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experiment A: exact 1D star discrepancy for the golden-branch Kronecker scan.

This script writes a LaTeX table row file into:
  sections/generated/golden_discrepancy_rows.tex

No third-party dependencies.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Sequence


def golden_points(n: int) -> List[float]:
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    alpha = 1.0 / phi  # golden branch
    return [(t * alpha) % 1.0 for t in range(n)]


def star_discrepancy_1d(points: Sequence[float]) -> float:
    """
    Exact 1D star discrepancy:
      D_N^* = sup_{u in [0,1]} | (1/N) #{x_i < u} - u |
    computed from sorted points.
    """
    n = len(points)
    if n <= 0:
        return 0.0
    xs = sorted(points)
    inv_n = 1.0 / float(n)
    d_plus = 0.0
    d_minus = 0.0
    for i, x in enumerate(xs):
        a = (float(i + 1) * inv_n) - x
        b = x - (float(i) * inv_n)
        if a > d_plus:
            d_plus = a
        if b > d_minus:
            d_minus = b
    return max(d_plus, d_minus)


def bound_gold(n: int) -> float:
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    return 2.0 * (2.0 + math.log(float(n), phi)) / float(n)


def fmt_sci_unsigned(x: float, sig: int = 4) -> str:
    """LaTeX scientific notation without sign, for nonnegative quantities."""
    if x <= 0.0:
        return "$0$"
    exp = int(math.floor(math.log10(x)))
    mant = x / (10.0 ** exp)
    mant = round(mant, max(sig - 1, 0))
    if mant >= 10.0:
        mant /= 10.0
        exp += 1
    mant_str = f"{mant:.{max(sig - 1, 0)}f}".rstrip("0").rstrip(".")
    return f"${mant_str}\\times 10^{{{exp}}}$"


def fmt_decimal(x: float, digits: int = 4) -> str:
    return f"${x:.{digits}f}$"


def write_rows(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = list(lines)
    if out:
        last = out[-1].rstrip()
        if last.endswith("\\\\"):
            last = last[:-2].rstrip()
        out[-1] = last
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    gen = root / "sections" / "generated"

    ns = [1000, 5000, 10000, 50000]
    rows: List[str] = []
    for n in ns:
        pts = golden_points(n)
        dstar = star_discrepancy_1d(pts)
        bound = bound_gold(n)
        ratio = dstar / bound if bound > 0.0 else 0.0
        rows.append(
            f"{n:,} & {fmt_sci_unsigned(dstar)} & {fmt_sci_unsigned(bound)} & {fmt_decimal(ratio, digits=4)} \\\\"
        )

    write_rows(gen / "golden_discrepancy_rows.tex", rows)
    print(f"Wrote LaTeX rows into: {gen}")
    print("File: golden_discrepancy_rows.tex")


if __name__ == "__main__":
    main()


