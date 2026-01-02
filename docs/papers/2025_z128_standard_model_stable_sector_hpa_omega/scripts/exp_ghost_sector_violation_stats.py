# -*- coding: utf-8 -*-
"""
Ghost-sector diagnostics: count local admissibility violations in Omega_m \\ X_m.

We treat:
  - Omega_m = {0,1}^m as the full word alphabet,
  - X_m as the golden-mean admissible subset (no consecutive ones).

A simple instability witness for a word w in Omega_m is the number of adjacent
violations:
  N_11(w) := #{ i in {1..m-1} : w_i = w_{i+1} = 1 }.

Then X_m is exactly the zero-violation sector: X_m = { w : N_11(w) = 0 }.

For a small m-sweep, we record:
  - |X_m|
  - |Omega_m \\ X_m|
  - histogram mass in the first few violation bins
  - mean N_11 among the ghost sector (N_11 >= 1)

Output (LaTeX fragment):
  - sections/generated/ghost_sector_violation_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import List


def n11(word: str) -> int:
    c = 0
    for i in range(len(word) - 1):
        if word[i] == "1" and word[i + 1] == "1":
            c += 1
    return c


def main() -> None:
    m_list = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

    rows: List[str] = []
    for m in m_list:
        total = 1 << m
        hist = Counter()
        for x in range(total):
            w = format(x, f"0{m}b")
            hist[n11(w)] += 1

        stable = hist.get(0, 0)
        ghost = total - stable
        ghost_frac = float(ghost) / float(total) if total else 0.0

        c1 = hist.get(1, 0)
        c2 = hist.get(2, 0)
        c3 = hist.get(3, 0)
        c4p = sum(v for k, v in hist.items() if k >= 4)

        mean_ghost = 0.0
        if ghost > 0:
            mean_ghost = sum(float(k) * float(v) for k, v in hist.items() if k >= 1) / float(ghost)

        rows.append(
            f"{m} & {stable} & {ghost} & {ghost_frac:.6f} & {c1} & {c2} & {c3} & {c4p} & {mean_ghost:.4f} \\\\"
        )

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ghost_sector_violation_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/ghost_sector_violation_rows.tex")


if __name__ == "__main__":
    main()


