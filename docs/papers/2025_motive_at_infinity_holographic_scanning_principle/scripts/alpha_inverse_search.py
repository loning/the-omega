#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Exhaustive low-complexity search for alpha^{-1} in the ansatz:
  v(a,b,c) = a*pi^3 + b*pi^2 + c*pi
with a,b,c >= 0 and a+b+c <= 10.

Writes LaTeX rows into:
  sections/generated/alpha_integer_search_rows.tex

No third-party dependencies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass(frozen=True)
class Candidate:
    abs_err: float
    a: int
    b: int
    c: int
    value: float
    delta: float
    rel: float


def fmt_sci_signed(x: float, sig: int = 3) -> str:
    """LaTeX scientific notation with explicit sign: $+a\\times 10^{b}$."""
    if x == 0.0:
        return "$+0$"
    sign = "+" if x > 0 else "-"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = ax / (10.0 ** exp)
    mant = round(mant, max(sig - 1, 0))
    if mant >= 10.0:
        mant /= 10.0
        exp += 1
    mant_str = f"{mant:.{max(sig - 1, 0)}f}".rstrip("0").rstrip(".")
    return f"${sign}{mant_str}\\times 10^{{{exp}}}$"


def write_rows(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = list(lines)
    if out:
        last = out[-1].rstrip()
        if last.endswith("\\\\"):
            last = last[:-2].rstrip()
        out[-1] = last
    content = "\n".join(out).rstrip() + "\n"
    path.write_text(content, encoding="utf-8")


def search_alpha_integer_rigidity(target: float, max_sum: int = 10) -> List[Candidate]:
    pi = math.pi
    pi2 = pi * pi
    pi3 = pi2 * pi
    cands: List[Candidate] = []
    for a in range(0, max_sum + 1):
        for b in range(0, max_sum + 1 - a):
            for c in range(0, max_sum + 1 - a - b):
                if a + b + c > max_sum:
                    continue
                value = a * pi3 + b * pi2 + c * pi
                delta = value - target
                abs_err = abs(delta)
                rel = delta / target
                cands.append(Candidate(abs_err, a, b, c, value, delta, rel))
    cands.sort(key=lambda t: t.abs_err)
    return cands


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    gen = root / "sections" / "generated"

    alpha_inv_codata = 137.035999177  # CODATA 2022 central value used across the papers
    max_sum = 10
    top_k = 5

    cands = search_alpha_integer_rigidity(alpha_inv_codata, max_sum=max_sum)
    top = cands[:top_k]

    rows: List[str] = []
    for cand in top:
        a, b, c = cand.a, cand.b, cand.c
        s = a + b + c
        rows.append(
            f"$({a},{b},{c})$ & {s} & {cand.value:.10f} & {fmt_sci_signed(cand.delta)} & {fmt_sci_signed(cand.rel)} \\\\"
        )

    out_path = gen / "alpha_integer_search_rows.tex"
    write_rows(out_path, rows)

    print(f"Wrote LaTeX rows into: {out_path}")
    print(f"Top candidate: (a,b,c)=({top[0].a},{top[0].b},{top[0].c})  value={top[0].value:.10f}  abs_err={top[0].abs_err:.6e}")
    if len(top) >= 2:
        gap = top[1].abs_err / top[0].abs_err if top[0].abs_err != 0 else float("inf")
        print(f"Second best abs_err={top[1].abs_err:.6e}  gap(second/best)={gap:.3e}")


if __name__ == "__main__":
    main()


