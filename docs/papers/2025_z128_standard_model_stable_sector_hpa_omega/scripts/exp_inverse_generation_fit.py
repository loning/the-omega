# -*- coding: utf-8 -*-
"""
Exploratory inverse fit: recover the generation index from intrinsic invariants.

In the closed SM labeling, cyclic stable types (|X6|_cyc = 18) are paired with the
18 chiral fermion multiplets ordered by a deterministic complexity key.
This script checks whether the generation index g in {1,2,3} can be recovered
from simple intrinsic scores on the stable words.

We consider scalar scores S(w) and search for two integer thresholds t1 < t2:
  gen=1 if S<=t1, gen=2 if t1<S<=t2, gen=3 if S>t2,
selected by lexicographic minimization of (errors, t2-t1, t1, t2).

Scores tested:
  - V(w): Zeckendorf value at m=6
  - r_star(w) = V(w) + n*(g(w)-2) with n=3 (the same monotone used in stable ordering)

Outputs (LaTeX fragment):
  - sections/generated/inverse_generation_fit_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Tuple

import exp_sm_labeling_solver as sml
from common_tex import write_lines


@dataclass(frozen=True)
class Datum:
    V: int
    deg: int
    wt: int
    r_star: int
    generation: int


def build_dataset() -> List[Datum]:
    X6 = sml.all_x6()
    cyc = [w for w in X6 if not sml.is_boundary_word(w)]
    cyc_sorted = sorted(cyc, key=lambda w: sml.stable_type_sort_key(w))
    fields = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
    if len(cyc_sorted) != len(fields):
        raise AssertionError("Cyclic types and fermion targets must match in size.")
    out: List[Datum] = []
    for w, f in zip(cyc_sorted, fields):
        V = sml.zeckendorf_value(w)
        deg = sml.degeneracy_g(w)
        wt = w.count("1")
        r_star = V + 3 * (deg - 2)
        out.append(Datum(V=V, deg=deg, wt=wt, r_star=r_star, generation=f.generation))
    return out


def best_thresholds(data: List[Datum], score: Callable[[Datum], int]) -> Tuple[int, int, int]:
    """
    Return (errors, t1, t2) for the best two-threshold classifier.
    """
    vals = sorted({score(d) for d in data})
    if not vals:
        raise AssertionError("Empty dataset.")
    # Allow thresholds between distinct observed values; use integer thresholds.
    candidates = sorted(set(vals))
    best = None  # (errors, gap, t1, t2)
    for t1 in candidates:
        for t2 in candidates:
            if t2 <= t1:
                continue
            err = 0
            for d in data:
                s = score(d)
                pred = 1 if s <= t1 else (2 if s <= t2 else 3)
                if pred != d.generation:
                    err += 1
            cand = (err, t2 - t1, t1, t2)
            if best is None or cand < best:
                best = cand
    if best is None:
        raise AssertionError("No threshold pairs enumerated.")
    err, _gap, t1, t2 = best
    return err, t1, t2


def best_linear_score(data: List[Datum], B: int = 3) -> Tuple[int, int, int, int, int, int]:
    """
    Search for a small integer linear score S = a*V + b*deg + c*wt with |a|,|b|,|c|<=B.
    Return (errors, a, b, c, t1, t2) for the best model, where (t1,t2) are the
    best thresholds for that score under the same two-threshold rule.
    """
    best = None  # (errors, complexity, l1, a,b,c,t1,t2)
    for a in range(-B, B + 1):
        for b in range(-B, B + 1):
            for c in range(-B, B + 1):
                if a == 0 and b == 0 and c == 0:
                    continue
                err, t1, t2 = best_thresholds(data, score=lambda d: a * d.V + b * d.deg + c * d.wt)
                l1 = abs(a) + abs(b) + abs(c)
                comp = l1 + abs(t1) + abs(t2)
                cand = (err, comp, l1, a, b, c, t1, t2)
                if best is None or cand < best:
                    best = cand

    if best is None:
        raise AssertionError("No candidates enumerated.")
    err, _comp, _l1, a, b, c, t1, t2 = best
    return err, a, b, c, t1, t2


def main() -> None:
    data = build_dataset()
    n = len(data)
    if n != 18:
        raise AssertionError("Expected 18 cyclic points.")

    rows: List[str] = []
    for name, fn in [
        ("$V(w)$", lambda d: d.V),
        ("$r_\\ast(w)=V(w)+3(g(w)-2)$", lambda d: d.r_star),
    ]:
        err, t1, t2 = best_thresholds(data, score=fn)
        acc = 1.0 - float(err) / float(n)
        rows.append(f"{name} & $(t_1,t_2)=({t1},{t2})$ & {err} & {acc:.3f} \\\\")

    # A small bounded linear search on (V,deg,wt) to see whether a simple combination sharpens the split.
    err, a, b, c, t1, t2 = best_linear_score(data, B=4)
    acc = 1.0 - float(err) / float(n)
    rows.append(
        f"$S(w)=aV(w)+b\\,\\deg(w)+c\\,\\mathrm{{wt}}(w)$ (best) & $(a,b,c,t_1,t_2)=({a},{b},{c},{t1},{t2})$ & {err} & {acc:.3f} \\\\"
    )
    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "inverse_generation_fit_rows.tex", rows)
    print("Wrote sections/generated/inverse_generation_fit_rows.tex")


if __name__ == "__main__":
    main()


