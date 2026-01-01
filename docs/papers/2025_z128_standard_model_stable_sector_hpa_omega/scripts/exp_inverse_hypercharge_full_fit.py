# -*- coding: utf-8 -*-
"""
Exploratory inverse fit: recover the full hypercharge numerator Y_num (units of 1/6).

Target set (per SM generation multiplets):
  Y_num ∈ {+1,+4,-2,-3,-6,0}

We build a dataset on cyclic stable types (18 points) paired with the 18 fermion
targets under the closed ordering used by the labeling solver.

We search a bounded integer affine score:
  S(w) = a*V(w) + b*g(w) + c*wt(w) + d
with |a|,|b|,|c|,|d| <= B.

Prediction rule (projection):
  predict Y_num as the nearest value in the allowed target set to S(w),
  with deterministic tie-break by smaller |Y| then by value.

Selection criterion:
  lexicographic minimization of (errors, complexity, a,b,c,d),
  where complexity = |a|+|b|+|c|+|d|.

Outputs (LaTeX fragment):
  - sections/generated/inverse_hypercharge_full_fit_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import exp_sm_labeling_solver as sml
from common_tex import write_lines


@dataclass(frozen=True)
class Datum:
    V: int
    g: int
    wt: int
    Y_num: int


ALLOWED = (-6, -3, -2, 0, 1, 4)


def nearest_allowed(x: int) -> int:
    # tie-break by smaller |y| then by y
    best = None  # (dist, abs_y, y)
    for y in ALLOWED:
        cand = (abs(x - y), abs(y), y)
        if best is None or cand < best:
            best = cand
    if best is None:
        raise AssertionError("No allowed values.")
    return best[2]


def build_dataset() -> List[Datum]:
    X6 = sml.all_x6()
    cyc = [w for w in X6 if not sml.is_boundary_word(w)]
    cyc_sorted = sorted(cyc, key=lambda w: sml.stable_type_sort_key(w))
    fields = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
    if len(cyc_sorted) != len(fields):
        raise AssertionError("Cyclic types and fermion targets must match in size.")
    out: List[Datum] = []
    for w, f in zip(cyc_sorted, fields):
        out.append(
            Datum(
                V=sml.zeckendorf_value(w),
                g=sml.degeneracy_g(w),
                wt=w.count("1"),
                Y_num=f.Y_num,
            )
        )
    return out


def main() -> None:
    data = build_dataset()
    n = len(data)
    if n != 18:
        raise AssertionError("Expected 18 cyclic points.")

    B = 6
    best = None  # (errors, complexity, a,b,c,d)
    for a in range(-B, B + 1):
        for b in range(-B, B + 1):
            for c in range(-B, B + 1):
                for d in range(-B, B + 1):
                    if a == 0 and b == 0 and c == 0:
                        continue
                    err = 0
                    for p in data:
                        s = a * p.V + b * p.g + c * p.wt + d
                        pred = nearest_allowed(s)
                        if pred != p.Y_num:
                            err += 1
                    comp = abs(a) + abs(b) + abs(c) + abs(d)
                    cand = (err, comp, a, b, c, d)
                    if best is None or cand < best:
                        best = cand

    if best is None:
        raise AssertionError("No candidates enumerated.")
    err, comp, a, b, c, d = best
    acc = 1.0 - float(err) / float(n)

    row = (
        f"$|a|,|b|,|c|,|d|\\le {B}$ & $Y$ (full) & "
        f"$(a,b,c,d)=({a},{b},{c},{d})$ & {err} & {acc:.3f} \\\\"
    )
    rows = [row, "\\bottomrule"]

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "inverse_hypercharge_full_fit_rows.tex", rows)
    print("Wrote sections/generated/inverse_hypercharge_full_fit_rows.tex")


if __name__ == "__main__":
    main()


