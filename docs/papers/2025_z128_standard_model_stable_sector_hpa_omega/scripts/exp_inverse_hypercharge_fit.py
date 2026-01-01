# -*- coding: utf-8 -*-
"""
Exploratory inverse fit: recover (6Y)^2 classes from intrinsic invariants on X6.

We treat the closed labeling assignment on the cyclic sector as supervised data:
  cyclic stable types w in X6  ->  SM fermion multiplets  ->  (6Y)^2 class.

We test a bounded-complexity family of integer linear scores:
  S(w) = a*V(w) + b*g(w) + c*|w|_1 + d,
and predict the target class by snapping S(w) to the nearest allowed value in:
  C = {0,1,4,9,16,36},
with deterministic tie-break rules.

We report the best and second-best solutions and the accuracy gap in a bounded box.

Outputs (LaTeX fragment):
  - sections/generated/inverse_hypercharge_fit_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import exp_sm_labeling_solver as sml
from common_tex import write_lines


CLASSES = [0, 1, 4, 9, 16, 36]


def snap_to_class(x: int) -> int:
    # Nearest in absolute difference; ties to smaller class (deterministic).
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
    w: str
    V: int
    g: int
    wt: int
    y2: int  # (6Y)^2


def build_dataset() -> List[Point]:
    X6 = sml.all_x6()
    cyc = [w for w in X6 if not sml.is_boundary_word(w)]
    if len(cyc) != 18:
        raise AssertionError("Expected 18 cyclic types.")
    cyc_sorted = sorted(cyc, key=lambda w: sml.stable_type_sort_key(w))
    fields = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
    if len(cyc_sorted) != len(fields):
        raise AssertionError("Cyclic types and fermion targets must match in size.")

    pts: List[Point] = []
    for w, f in zip(cyc_sorted, fields):
        V = sml.zeckendorf_value(w)
        g = sml.degeneracy_g(w)
        wt = w.count("1")
        y2 = f.Y_num * f.Y_num
        pts.append(Point(w=w, V=V, g=g, wt=wt, y2=y2))
    return pts


def accuracy_for(a: int, b: int, c: int, d: int, pts: List[Point]) -> Tuple[int, int]:
    correct = 0
    for p in pts:
        s = a * p.V + b * p.g + c * p.wt + d
        pred = snap_to_class(s)
        if pred == p.y2:
            correct += 1
    return correct, len(pts)


def main() -> None:
    pts = build_dataset()

    # Bounded search box.
    B = 8

    best = None  # (neg_correct, complexity, a,b,c,d)
    second = None

    for a in range(-B, B + 1):
        for b in range(-B, B + 1):
            for c in range(-B, B + 1):
                for d in range(-B, B + 1):
                    correct, total = accuracy_for(a, b, c, d, pts)
                    acc = float(correct) / float(total)
                    complexity = abs(a) + abs(b) + abs(c) + abs(d)
                    cand = (-correct, complexity, a, b, c, d, acc)
                    if best is None or cand < best:
                        second = best
                        best = cand
                    elif second is None or cand < second:
                        # Keep the second-best distinct from best in (a,b,c,d).
                        if best is None or (a, b, c, d) != (best[2], best[3], best[4], best[5]):
                            second = cand

    if best is None:
        raise AssertionError("No candidates enumerated.")

    _neg1, comp1, a1, b1, c1, d1, acc1 = best
    if second is None:
        _neg2, comp2, a2, b2, c2, d2, acc2 = (0, 0, 0, 0, 0, 0, 0.0)
    else:
        _neg2, comp2, a2, b2, c2, d2, acc2 = second

    gap = acc1 - acc2
    # Provide a compact row.
    # "notes" column can record class set.
    row = (
        f"$|a|,|b|,|c|,|d|\\le {B}$ & "
        f"$({a1},{b1},{c1},{d1})$ & {acc1:.3f} & "
        f"$({a2},{b2},{c2},{d2})$ & {gap:.3f} & {comp1} & "
        f"$\\{{0,1,4,9,16,36\\}}$ \\\\"
    )

    out_lines = [row, "\\bottomrule"]

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "inverse_hypercharge_fit_rows.tex", out_lines)
    print("Wrote sections/generated/inverse_hypercharge_fit_rows.tex")


if __name__ == "__main__":
    main()


