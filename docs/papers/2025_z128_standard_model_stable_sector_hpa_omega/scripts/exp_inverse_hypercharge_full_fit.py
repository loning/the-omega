# -*- coding: utf-8 -*-
"""
Exploratory inverse fit: recover the full hypercharge numerator Y_num (units of 1/6).

Target set (per SM generation multiplets):
  Y_num ∈ {+1,+4,-2,-3,-6,0}

We build a dataset on cyclic stable types (18 points) paired with the 18 fermion
targets under the closed ordering used by the labeling solver.

We compare two bounded score families:

  (A) affine on (V,g,wt):
      S(w) = a*V(w) + b*g(w) + c*wt(w) + d

  (B) affine on the first five word bits:
      S(w) = Σ_{i=1..5} c_i w_i + d

Both families use bounded integer coefficients.

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

import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import exp_sm_labeling_solver as sml
from common_tex import write_lines


@dataclass(frozen=True)
class Datum:
    w: str
    V: int
    g: int
    wt: int
    ones5: Tuple[int, ...]
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
        ones5 = tuple(i for i, ch in enumerate(w[:5]) if ch == "1")
        out.append(
            Datum(
                w=w,
                V=sml.zeckendorf_value(w),
                g=sml.degeneracy_g(w),
                wt=w.count("1"),
                ones5=ones5,
                Y_num=f.Y_num,
            )
        )
    return out


def best_affine_vgwt(data: List[Datum], B: int) -> Tuple[int, int, int, int, int, int]:
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
    return best


def best_affine_bits5(data: List[Datum], B: int, d_min: int = -6, d_max: int = 6) -> Tuple[int, int, Tuple[int, int, int, int, int], int]:
    # Precompute snap on a safe integer range for speed.
    snap = {x: nearest_allowed(x) for x in range(-64, 65)}

    def snap_y(x: int) -> int:
        return snap.get(x, nearest_allowed(x))

    vals = list(range(-B, B + 1))
    d_vals = list(range(d_min, d_max + 1))
    best = None  # (errors, complexity, coeffs5, d)
    for coeffs in itertools.product(vals, repeat=5):
        if all(c == 0 for c in coeffs):
            continue
        # Precompute partial sums for each datum (only uses the 1-bits among first five positions).
        s_base = [sum(coeffs[i] for i in p.ones5) for p in data]
        for d in d_vals:
            err = 0
            for sb, p in zip(s_base, data):
                if snap_y(sb + d) != p.Y_num:
                    err += 1
            comp = sum(abs(c) for c in coeffs) + abs(d)
            cand = (err, comp, coeffs, d)
            if best is None or cand < best:
                best = cand
    if best is None:
        raise AssertionError("No candidates enumerated.")
    return best


def main() -> None:
    data = build_dataset()
    n = len(data)
    if n != 18:
        raise AssertionError("Expected 18 cyclic points.")

    rows: List[str] = []

    # (A) affine on (V,g,wt)
    B = 6
    err, _comp, a, b, c, d = best_affine_vgwt(data, B=B)
    acc = 1.0 - float(err) / float(n)
    rows.append(
        f"$|a|,|b|,|c|,|d|\\le {B}$ & $Y_{{\\mathrm{{num}}}}$ (V,g,wt) & $(a,b,c,d)=({a},{b},{c},{d})$ & {err} & {acc:.3f} \\\\"
    )

    # (B) affine on the first five word bits
    B5 = 3
    err2, _comp2, coeffs5, d5 = best_affine_bits5(data, B=B5, d_min=-6, d_max=6)
    acc2 = 1.0 - float(err2) / float(n)
    c1, c2, c3, c4, c5 = coeffs5
    rows.append(
        f"$|c_i|\\le {B5}$ & $Y_{{\\mathrm{{num}}}}$ (bits $1..5$) & $(c_1,\\dots,c_5,d)=({c1},{c2},{c3},{c4},{c5},{d5})$ & {err2} & {acc2:.3f} \\\\"
    )

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "inverse_hypercharge_full_fit_rows.tex", rows)
    print("Wrote sections/generated/inverse_hypercharge_full_fit_rows.tex")


if __name__ == "__main__":
    main()


