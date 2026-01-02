# -*- coding: utf-8 -*-
"""
Bounded-complexity inverse diagnostic: recover the sign of hypercharge Y from intrinsic invariants.

Targets are the sign classes of the SM hypercharge numerator (in units of 1/6):
  sign(Y_num) in {-1,0,+1}.

We use a bounded-complexity linear score on each cyclic stable type w:
  S(w) = a*V(w) + b*g(w) + c*wt(w),
with |a|,|b|,|c|<=B, where:
  - V(w): Zeckendorf value at m=6
  - g(w): Fold_6 degeneracy
  - wt(w): Hamming weight of w

We then classify by two thresholds t1<t2 and an interval-to-class order (a permutation
of {-1,0,+1}):
  class = π0 if S<=t1, π1 if t1<S<=t2, π2 otherwise.

Selection is lexicographic minimization of:
  (errors, complexity, a,b,c, t1,t2, π)
where complexity = |a|+|b|+|c|+|t1|+|t2|.

Outputs (LaTeX fragment):
  - sections/generated/inverse_hypercharge_sign_fit_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
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
    y_sign: int  # -1,0,+1


def sign(x: int) -> int:
    return -1 if x < 0 else (1 if x > 0 else 0)


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
        g = sml.degeneracy_g(w)
        wt = w.count("1")
        out.append(Datum(V=V, g=g, wt=wt, y_sign=sign(f.Y_num)))
    return out


def main() -> None:
    data = build_dataset()
    n = len(data)
    if n != 18:
        raise AssertionError("Expected 18 cyclic points.")

    B = 4
    classes = (-1, 0, 1)
    perms = list(itertools.permutations(classes, 3))

    best = None  # (errors, complexity, a,b,c, t1,t2, pi)
    for a in range(-B, B + 1):
        for b in range(-B, B + 1):
            for c in range(-B, B + 1):
                if a == 0 and b == 0 and c == 0:
                    continue
                scores = [a * d.V + b * d.g + c * d.wt for d in data]
                vals = sorted(set(scores))
                for t1 in vals:
                    for t2 in vals:
                        if t2 <= t1:
                            continue
                        for pi in perms:
                            err = 0
                            for d, s in zip(data, scores):
                                pred = pi[0] if s <= t1 else (pi[1] if s <= t2 else pi[2])
                                if pred != d.y_sign:
                                    err += 1
                            comp = abs(a) + abs(b) + abs(c) + abs(t1) + abs(t2)
                            cand = (err, comp, a, b, c, t1, t2, pi)
                            if best is None or cand < best:
                                best = cand

    if best is None:
        raise AssertionError("No candidates enumerated.")
    err, comp, a, b, c, t1, t2, pi = best
    acc = 1.0 - float(err) / float(n)

    row = (
        f"$|a|,|b|,|c|\\le {B}$ & $\\mathrm{{sign}}(Y)$ & "
        f"$(a,b,c,t_1,t_2,\\pi)=({a},{b},{c},{t1},{t2},{pi})$ & {err} & {acc:.3f} \\\\"
    )
    rows = [row, "\\bottomrule"]

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "inverse_hypercharge_sign_fit_rows.tex", rows)
    print("Wrote sections/generated/inverse_hypercharge_sign_fit_rows.tex")


if __name__ == "__main__":
    main()


