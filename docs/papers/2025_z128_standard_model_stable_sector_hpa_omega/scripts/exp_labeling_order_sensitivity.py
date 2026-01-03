# -*- coding: utf-8 -*-
"""
Ordering sensitivity audit: how much does the induced cyclic labeling depend on the SM-side ordering key?

The closed labeling map on the cyclic sector is constructed as an order isomorphism between:
  - cyclic stable types ordered by (r_star, V, w),
  - SM fermion multiplets ordered by (generation, su3_dim, (6Y)^2, su2_dim, name).

A reviewer can reasonably ask whether this ordering choice is arbitrary.
This audit tests a small family of alternative SM-side ordering keys obtained by permuting
the component order among {su3_dim, (6Y)^2, su2_dim} while keeping generation first and
name as a final deterministic tie-break.

For each alternative ordering, we induce a cyclic assignment by rank matching and report
how many of the 18 cyclic labels change relative to the baseline ordering used in the paper
(Hamming distance on the ordered label list).

Output (LaTeX fragment):
  - sections/generated/labeling_order_sensitivity_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import exp_sm_labeling_solver as sml
from common_tex import write_lines


CLASSES = [0, 1, 4, 9, 16, 36]  # (6Y)^2 allowed set


def snap_to_class(x: int) -> int:
    best = None  # (absdiff, cls)
    for c in CLASSES:
        cand = (abs(x - c), c)
        if best is None or cand < best:
            best = cand
    if best is None:
        raise AssertionError("No classes enumerated.")
    return best[1]


@dataclass(frozen=True)
class Point:
    V: int
    g: int
    wt: int
    y2: int


def best_accuracy_y2(points: List[Point], B: int = 8) -> Tuple[float, float, Tuple[int, int, int, int]]:
    """
    Return (best_acc, second_acc, best_coeffs) for the bounded affine family on (V,g,wt).
    """
    n = len(points)
    if n <= 0:
        raise AssertionError("Empty dataset.")

    best = None  # (-correct, complexity, a,b,c,d, acc)
    second = None
    for a in range(-B, B + 1):
        for b in range(-B, B + 1):
            for c in range(-B, B + 1):
                for d in range(-B, B + 1):
                    correct = 0
                    for p in points:
                        s = a * p.V + b * p.g + c * p.wt + d
                        if snap_to_class(s) == p.y2:
                            correct += 1
                    acc = float(correct) / float(n)
                    complexity = abs(a) + abs(b) + abs(c) + abs(d)
                    cand = (-correct, complexity, a, b, c, d, acc)
                    if best is None or cand < best:
                        second = best
                        best = cand
                    elif second is None or cand < second:
                        if best is None or (a, b, c, d) != (best[2], best[3], best[4], best[5]):
                            second = cand

    if best is None:
        raise AssertionError("No candidates enumerated.")
    _neg1, _comp1, a1, b1, c1, d1, acc1 = best
    if second is None:
        acc2 = 0.0
    else:
        acc2 = second[6]
    return acc1, acc2, (a1, b1, c1, d1)


def cyclic_types_sorted() -> List[str]:
    X6 = sml.all_x6()
    cyc = [w for w in X6 if not sml.is_boundary_word(w)]
    if len(cyc) != 18:
        raise AssertionError("Expected 18 cyclic types.")
    return sorted(cyc, key=lambda w: sml.stable_type_sort_key(w))


def fields_sorted_by_key(order: Tuple[str, str, str]) -> List[sml.SMField]:
    # order permutes among ("su3","y2","su2"), generation is always first, name always last.
    fields = sml.fermion_targets()

    def key(f: sml.SMField) -> Tuple[int, int, int, int, str]:
        comp: Dict[str, int] = {
            "su3": f.su3_dim,
            "y2": f.Y_num * f.Y_num,  # (6Y)^2
            "su2": f.su2_dim,
        }
        return (f.generation, comp[order[0]], comp[order[1]], comp[order[2]], f.name)

    return sorted(fields, key=key)


def build_points_for_mapping(fields_sorted: List[sml.SMField]) -> List[Point]:
    cyc_sorted = cyclic_types_sorted()
    if len(fields_sorted) != len(cyc_sorted):
        raise AssertionError("Fields and cyclic types must match in size.")
    pts: List[Point] = []
    for w, f in zip(cyc_sorted, fields_sorted):
        pts.append(
            Point(
                V=sml.zeckendorf_value(w),
                g=sml.degeneracy_g(w),
                wt=w.count("1"),
                y2=f.Y_num * f.Y_num,
            )
        )
    return pts


def order_tex(order: Tuple[str, str, str]) -> str:
    name = {
        "su3": r"\dim(SU(3))",
        "y2": r"(6Y)^2",
        "su2": r"\dim(SU(2))",
    }
    return rf"$(g,{name[order[0]]},{name[order[1]]},{name[order[2]]})$"


def main() -> None:
    # Six permutations of the three nontrivial SM-key components (generation fixed first).
    orders = list(itertools.permutations(("su3", "y2", "su2"), 3))
    baseline = ("su3", "y2", "su2")

    rows: List[str] = []
    base_fields = fields_sorted_by_key(baseline)
    base_names = [f.name for f in base_fields]
    for order in orders:
        fields = fields_sorted_by_key(order)
        names = [f.name for f in fields]
        diff = sum(1 for a, b in zip(names, base_names) if a != b)
        frac = float(diff) / float(len(base_names))
        key_tex = order_tex(order)
        diff_tex = f"{diff}"
        frac_tex = f"{frac:.3f}"
        if order == baseline:
            key_tex = rf"\textbf{{{key_tex}}}"
            diff_tex = rf"\textbf{{{diff_tex}}}"
            frac_tex = rf"\textbf{{{frac_tex}}}"
        rows.append(f"{key_tex} & {diff_tex} & {frac_tex} \\\\")
    rows.append(r"\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "labeling_order_sensitivity_rows.tex", rows)
    print("Wrote sections/generated/labeling_order_sensitivity_rows.tex")


if __name__ == "__main__":
    main()


