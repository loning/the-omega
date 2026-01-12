# -*- coding: utf-8 -*-
"""
Generate a bounded finite family of scale maps a(n) on the balanced chain.

We normalize all scale maps by fixing a(3)=1 (anchor at n=3, m=6), so only
relative ratios across scales are recorded. This keeps the output theorem-facing
and avoids introducing an absolute physical length input.

Outputs (LaTeX fragment):
  - sections/generated/scale_map_balanced_chain_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from common_tex import write_lines


def main() -> None:
    chain = [1, 2, 3, 4, 5, 6, 7, 8]
    # Finite candidate family: normalize to a(3)=1.
    # (S1) dyadic (grid) spacing proxy: a(n) = 2^{-(n-3)}
    # (S2) window proxy (in m=2n units): a(n) = 2^{-(m-6)} = 2^{-2(n-3)}
    # (S3) geometric mean proxy between S1 and S2: a(n) = 2^{-3/2 (n-3)}
    rows: List[str] = []
    for n in chain:
        m = 2 * n
        dn = n - 3
        a1 = 2.0 ** (-dn)
        a2 = 2.0 ** (-2 * dn)
        a3 = 2.0 ** (-1.5 * dn)
        rows.append(f"{n} & {m} & {a1:.6g} & {a2:.6g} & {a3:.6g} \\\\")

    rows.append("\\bottomrule")
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "scale_map_balanced_chain_rows.tex", rows)


if __name__ == "__main__":
    main()

