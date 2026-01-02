# -*- coding: utf-8 -*-
"""
Sweep the Hilbert chirality index chi over multiple Hilbert orders n.

We compute:
  - chi(path)
  - chi(reversed path)
  - chi(reflected path)

for a small list of n values relevant to the balanced coupling m=2n chain.

Output (LaTeX fragment):
  - sections/generated/hilbert_chi_sweep_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import exp_hilbert_chirality_index as hil


def main() -> None:
    n_list = [3, 4, 5, 6, 7, 8]
    rows: List[str] = []
    for n_bits in n_list:
        path = hil.hilbert_curve(n_bits)
        L = (1 << n_bits) - 1
        chi = hil.chirality_index(path)
        chi_rev = hil.chirality_index(list(reversed(path)))
        chi_ref = hil.chirality_index([hil.reflect_y(L, p) for p in path])
        if chi_rev != -chi:
            raise AssertionError(f"Expected reversal to flip chi at n={n_bits}.")
        if chi_ref != -chi:
            raise AssertionError(f"Expected reflection to flip chi at n={n_bits}.")
        rows.append(f"{n_bits} & {len(path)} & {chi} & {chi_rev} & {chi_ref} \\\\")

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "hilbert_chi_sweep_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/hilbert_chi_sweep_rows.tex")


if __name__ == "__main__":
    main()



