# -*- coding: utf-8 -*-
"""
Weight statistics for admissible sets X_m (no consecutive ones) in an m-sweep.

For each m in a small sweep, we enumerate X_m and compute:
  - |X_m|
  - mean and variance of Hamming weight |w|_1 over w in X_m
  - a compact Hamming-weight histogram (k:count)

Output (LaTeX fragment):
  - sections/generated/xm_weight_sweep_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import List

import exp_xm_enumeration as xm


def hist_to_tex(hist: Counter[int]) -> str:
    parts = [f"{k}:{hist[k]}" for k in sorted(hist)]
    return "\\texttt{" + ", ".join(parts) + "}"


def main() -> None:
    m_list = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

    rows: List[str] = []
    for m in m_list:
        Xm = xm.all_xm(m)
        ws = [w.count("1") for w in Xm]
        hist = Counter(ws)
        mean = float(sum(ws)) / float(len(ws)) if ws else 0.0
        var = float(sum((x - mean) ** 2 for x in ws)) / float(len(ws)) if ws else 0.0
        rows.append(f"{m} & {len(Xm)} & {mean:.4f} & {var:.4f} & {hist_to_tex(hist)} \\\\")

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "xm_weight_sweep_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/xm_weight_sweep_rows.tex")


if __name__ == "__main__":
    main()


