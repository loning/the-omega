# -*- coding: utf-8 -*-
"""
Ghost-sector diagnostics: minimal repair cost to reach admissibility.

We treat:
  - Omega_m = {0,1}^m as the full word alphabet,
  - X_m as the admissible subset (no consecutive ones).

For a word w in Omega_m, define a minimal "repair" cost c(w):
the minimum number of bit flips 1->0 required to eliminate all occurrences of "11".
Equivalently, for each maximal run of consecutive ones of length L, one must flip
at least floor(L/2) ones to break adjacency; hence
  c(w) = sum_over_runs floor(L_run / 2).

This provides a discrete distance-to-stability proxy: X_m = { w : c(w) = 0 }.

Outputs (LaTeX fragment):
  - sections/generated/ghost_sector_repair_cost_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import List


def repair_cost(word: str) -> int:
    c = 0
    run = 0
    for ch in word:
        if ch == "1":
            run += 1
        else:
            if run >= 2:
                c += run // 2
            run = 0
    if run >= 2:
        c += run // 2
    return c


def main() -> None:
    m_list = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

    rows: List[str] = []
    for m in m_list:
        total = 1 << m
        hist = Counter()
        for x in range(total):
            w = format(x, f"0{m}b")
            hist[repair_cost(w)] += 1

        stable = hist.get(0, 0)
        ghost = total - stable
        frac = float(ghost) / float(total) if total else 0.0

        c1 = hist.get(1, 0)
        c2 = hist.get(2, 0)
        c3 = hist.get(3, 0)
        c4 = hist.get(4, 0)
        c5p = sum(v for k, v in hist.items() if k >= 5)

        mean_ghost = 0.0
        if ghost > 0:
            mean_ghost = sum(float(k) * float(v) for k, v in hist.items() if k >= 1) / float(ghost)

        rows.append(f"{m} & {stable} & {ghost} & {frac:.6f} & {c1} & {c2} & {c3} & {c4} & {c5p} & {mean_ghost:.4f} \\\\")

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ghost_sector_repair_cost_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/ghost_sector_repair_cost_rows.tex")


if __name__ == "__main__":
    main()


