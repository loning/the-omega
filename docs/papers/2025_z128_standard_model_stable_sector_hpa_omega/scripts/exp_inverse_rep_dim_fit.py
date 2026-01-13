# -*- coding: utf-8 -*-
"""
Bounded-complexity inverse diagnostics: recover SU(3)/SU(2) representation dimensions from invariants.

We use the cyclic sector data (w -> SM multiplet) induced by the closed labeling map.
Targets:
  - su3_dim in {1,3}
  - su2_dim in {1,2}

We test a small bounded linear-score family:
  S(w) = a*V(w) + b*g(w) + c*|w|_1 + d,
and predict a binary class by thresholding S at an integer T.

Selection is by lexicographic minimization of:
  (misclassifications, complexity, parameters...)

Outputs (LaTeX fragment):
  - sections/generated/inverse_rep_dim_fit_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import exp_sm_labeling_solver as sml
from common_progress import ProgressEvery
from common_tex import write_lines


@dataclass(frozen=True)
class Point:
    V: int
    g: int
    wt: int
    su3_dim: int
    su2_dim: int


def build_dataset() -> List[Point]:
    X6 = sml.all_x6()
    cyc = [w for w in X6 if not sml.is_boundary_word(w)]
    cyc_sorted = sorted(cyc, key=lambda w: sml.stable_type_sort_key(w))
    fields = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
    if len(cyc_sorted) != len(fields):
        raise AssertionError("Cyclic types and fermion targets must match in size.")
    pts: List[Point] = []
    for w, f in zip(cyc_sorted, fields):
        pts.append(
            Point(
                V=sml.zeckendorf_value(w),
                g=sml.degeneracy_g(w),
                wt=w.count("1"),
                su3_dim=f.su3_dim,
                su2_dim=f.su2_dim,
            )
        )
    return pts


def fit_binary(pts: List[Point], target: str, classes: Tuple[int, int], B: int = 8) -> Tuple[int, int, int, int, int, int]:
    """
    Return (errors, a,b,c,d,T) for best model predicting target in classes via threshold.
    """
    lo, hi = classes
    if lo == hi:
        raise ValueError("Classes must differ.")

    best = None  # (errors, complexity, a,b,c,d,T)
    total = int(2 * B + 1) ** 4
    prog = ProgressEvery(
        label=f"inverse_rep_dim_fit target={target} B={int(B)}",
        total=total,
        interval_s=60.0,
    )
    prog.start()
    k = 0
    for a in range(-B, B + 1):
        for b in range(-B, B + 1):
            for c in range(-B, B + 1):
                for d in range(-B, B + 1):
                    k += 1
                    prog.maybe(k, extra=f"a={a} b={b} c={c} d={d}")
                    # Candidate thresholds: scan a modest integer range.
                    # Score values are small; include a safety margin.
                    for T in range(-200, 201):
                        err = 0
                        for p in pts:
                            s = a * p.V + b * p.g + c * p.wt + d
                            pred = lo if s <= T else hi
                            true = getattr(p, target)
                            if true not in classes:
                                raise AssertionError("Unexpected class value.")
                            if pred != true:
                                err += 1
                        comp = abs(a) + abs(b) + abs(c) + abs(d) + abs(T)
                        cand = (err, comp, a, b, c, d, T)
                        if best is None or cand < best:
                            best = cand

    if best is None:
        raise AssertionError("No candidates enumerated.")
    prog.done(extra=f"best_err={best[0] if best else 'NA'}")
    err, _comp, a, b, c, d, T = best
    return err, a, b, c, d, T


def main() -> None:
    pts = build_dataset()
    n = len(pts)
    if n != 18:
        raise AssertionError("Expected 18 cyclic points.")

    # Fit SU(3) dimension: 1 vs 3.
    err3, a3, b3, c3, d3, T3 = fit_binary(pts, target="su3_dim", classes=(1, 3), B=6)
    acc3 = 1.0 - float(err3) / float(n)

    # Fit SU(2) dimension: 1 vs 2.
    err2, a2, b2, c2, d2, T2 = fit_binary(pts, target="su2_dim", classes=(1, 2), B=6)
    acc2 = 1.0 - float(err2) / float(n)

    rows: List[str] = []
    rows.append(
        f"$|a|,|b|,|c|,|d|\\le 6$ & $\\dim(SU(3))$ & $(a,b,c,d,T)=({a3},{b3},{c3},{d3},{T3})$ & {err3} & {acc3:.3f} \\\\"
    )
    rows.append(
        f"$|a|,|b|,|c|,|d|\\le 6$ & $\\dim(SU(2))$ & $(a,b,c,d,T)=({a2},{b2},{c2},{d2},{T2})$ & {err2} & {acc2:.3f} \\\\"
    )
    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "inverse_rep_dim_fit_rows.tex", rows)
    print("Wrote sections/generated/inverse_rep_dim_fit_rows.tex")


if __name__ == "__main__":
    main()


