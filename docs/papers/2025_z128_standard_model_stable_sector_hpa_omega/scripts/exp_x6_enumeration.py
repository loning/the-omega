# -*- coding: utf-8 -*-
"""
Enumerate the length-6 golden-mean admissible set X6 (no consecutive ones).

Reproduces:
  - |X6| = 21
  - Hamming-weight distribution
  - cyclic/boundary split (wrap-around admissibility)

It writes small LaTeX table-row fragments into sections/generated/.
Only the Python standard library is used.
"""

from __future__ import annotations

from collections import Counter
from itertools import product
from pathlib import Path


def is_admissible(bits: tuple[int, ...]) -> bool:
    return all(bits[i] + bits[i + 1] <= 1 for i in range(len(bits) - 1))


def bits_to_str(bits: tuple[int, ...]) -> str:
    return "".join(str(b) for b in bits)


def hamming_weight(s: str) -> int:
    return s.count("1")


def is_boundary_cyclic(s: str) -> bool:
    # cyclic boundary defect: wrap-around would create "11"
    return s[0] == "1" and s[-1] == "1"


def write_tex_rows(weight_hist: Counter[int], cyclic_count: int, boundary_count: int) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for k in sorted(weight_hist):
        rows.append(f"{k} & {weight_hist[k]} \\\\")
    (out_dir / "x6_weight_rows.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")

    (out_dir / "x6_cyclic_boundary_rows.tex").write_text(
        f"{cyclic_count} & {boundary_count} \\\\\n", encoding="utf-8"
    )


def main() -> None:
    X6 = []
    for bits in product([0, 1], repeat=6):
        if is_admissible(bits):
            X6.append(bits_to_str(bits))

    X6_sorted = sorted(X6)
    print("count |X6|:", len(X6_sorted))
    weight_hist = Counter(hamming_weight(s) for s in X6_sorted)
    print("weight histogram:", dict(sorted(weight_hist.items())))

    boundary = [s for s in X6_sorted if is_boundary_cyclic(s)]
    cyclic = [s for s in X6_sorted if not is_boundary_cyclic(s)]
    print("cyclic count:", len(cyclic))
    print("boundary count:", len(boundary))
    print("boundary words:", boundary)

    if len(X6_sorted) != 21:
        raise AssertionError("Expected |X6|=21.")
    if len(boundary) != 3 or len(cyclic) != 18:
        raise AssertionError("Expected cyclic/boundary split 18/3.")

    write_tex_rows(weight_hist=weight_hist, cyclic_count=len(cyclic), boundary_count=len(boundary))
    print("Wrote sections/generated/x6_weight_rows.tex and x6_cyclic_boundary_rows.tex")


if __name__ == "__main__":
    main()


