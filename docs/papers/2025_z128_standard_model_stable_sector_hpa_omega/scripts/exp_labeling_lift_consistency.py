# -*- coding: utf-8 -*-
"""
Functorial refinement audit for the field-level labeling map under window uplift.

We define the truncation (prefix) projection:
  pi_{m->6}: X_m -> X_6,    pi_{m->6}(w_1...w_m) = w_1...w_6,

and lift the closed labeling map by composition:
  L_m := L_SM ∘ pi_{m->6}.

This script reports, for selected m values, how many stable types in X_m
map to each base label in X_6 under this functorial lift.

Outputs (LaTeX fragments):
  - sections/generated/label_lift_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import exp_sm_labeling_solver as sml


def all_xm(m: int) -> List[str]:
    if m <= 0:
        raise ValueError("m must be positive.")
    out: List[str] = []

    def rec(prefix: str, last: str) -> None:
        if len(prefix) == m:
            out.append(prefix)
            return
        rec(prefix + "0", "0")
        if last != "1":
            rec(prefix + "1", "1")

    rec("", "0")
    return out


def parse_label_map_from_rows(rows: List[str]) -> Dict[str, str]:
    """
    Build a mapping w (as a plain 6-bit string) -> label TeX (e.g. $Q_L^{(1)}$).

    The rows returned by exp_sm_labeling_solver.generate_rows() begin with:
      \\texttt{w} & V & g & wt & r_* & D_pi & label & rep \\\\
    """
    out: Dict[str, str] = {}
    for line in rows:
        cols = [c.strip() for c in line.split("&")]
        if len(cols) < 7:
            continue
        w_col = cols[0]
        if not w_col.startswith("\\texttt{") or "}" not in w_col:
            continue
        w = w_col[len("\\texttt{") : w_col.index("}")]
        label = cols[6].strip()
        out[w] = label
    if len(out) != 21:
        raise AssertionError(f"Expected 21 labels, got {len(out)}.")
    return out


def main() -> None:
    # Base labeling map on X6.
    base_rows = sml.generate_rows()
    label_of: Dict[str, str] = parse_label_map_from_rows(base_rows)

    X6 = sml.all_x6()
    if len(X6) != 21:
        raise AssertionError("Expected |X6|=21.")

    # Select uplift values (balanced coupling m=2n gives m=8,10,12,14,16 for n=4..8).
    m_list = [8, 10, 12, 14, 16]

    # Count preimages under the prefix lift.
    counts: Dict[Tuple[str, int], int] = {}
    for m in m_list:
        Xm = all_xm(m)
        for w6 in X6:
            counts[(w6, m)] = 0
        for wm in Xm:
            w6 = wm[:6]
            if w6 not in label_of:
                raise AssertionError("Prefix did not land in X6.")
            counts[(w6, m)] += 1

    # Emit rows sorted by V(w) for readability (same order as the main labeling table).
    def sort_key(w: str) -> Tuple[int, str]:
        return (sml.zeckendorf_value(w), w)

    out_rows: List[str] = []
    for w6 in sorted(X6, key=sort_key):
        lab = label_of[w6]
        last_bit = int(w6[-1])
        c8 = counts[(w6, 8)]
        c10 = counts[(w6, 10)]
        c12 = counts[(w6, 12)]
        c14 = counts[(w6, 14)]
        c16 = counts[(w6, 16)]
        out_rows.append(f"\\texttt{{{w6}}} & {lab} & {last_bit} & {c8} & {c10} & {c12} & {c14} & {c16} \\\\")

    out_rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "label_lift_rows.tex").write_text("\n".join(out_rows), encoding="utf-8")
    print("Wrote sections/generated/label_lift_rows.tex")


if __name__ == "__main__":
    main()



