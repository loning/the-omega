# -*- coding: utf-8 -*-
"""
High-m inverse diagnostic: recover the full hypercharge numerator Y_num = 6Y
using lift-fiber invariants.

Targets:
  Y_num ∈ {-6,-3,-2,0,1,4}  (PDG convention Q=T3+Y).

We work on the cyclic base types u in X6 (18 points) paired with the 18 fermion
targets under the closed ordering used by the labeling solver.

For a higher window length m, define the lift fiber:
  Ext_m(u) := { w in X_m : w[:6] = u }.

We compute a small set of lift-fiber invariants and test bounded-complexity affine
scores S(u)=<a,features(u)>, predicting Y_num by snapping to the nearest allowed
value with deterministic tie-break (smaller |Y|, then smaller Y).

We report best and second-best solutions and the accuracy gap.

Outputs (LaTeX fragment):
  - sections/generated/inverse_highm_hypercharge_full_fit_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import exp_foldm_stats as foldm
import exp_sm_labeling_solver as sml
import exp_xm_enumeration as xm
from common_tex import write_lines
from common_progress import ProgressEvery


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


def fib_weights(m: int) -> List[int]:
    # Weights [F2, F3, ..., F_{m+1}] with F1=F2=1.
    if m < 0:
        raise ValueError("m must be nonnegative.")
    if m == 0:
        return []
    if m == 1:
        return [1]
    w = [1, 2]
    while len(w) < m:
        w.append(w[-1] + w[-2])
    return w


def zeckendorf_value_m(w: str) -> int:
    ws = fib_weights(len(w))
    return sum(int(bit) * ws[i] for i, bit in enumerate(w))


def is_boundary_word(w: str) -> bool:
    return w[0] == "1" and w[-1] == "1"


@dataclass(frozen=True)
class Datum:
    u: str
    y_num: int
    ext: int
    bdry: int
    g_min: int
    g_max: int
    v_min: int
    v_max: int
    v_width: int


def build_base_targets() -> List[Tuple[str, int]]:
    X6 = sml.all_x6()
    cyc = [w for w in X6 if not sml.is_boundary_word(w)]
    cyc_sorted = sorted(cyc, key=lambda w: sml.stable_type_sort_key(w))
    fields = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
    if len(cyc_sorted) != len(fields):
        raise AssertionError("Cyclic types and fermion targets must match in size.")
    out: List[Tuple[str, int]] = []
    for u, f in zip(cyc_sorted, fields):
        out.append((u, f.Y_num))
    return out


def foldm_degeneracy_map(m: int, Xm: List[str]) -> Dict[str, int]:
    gm = foldm.cached_degeneracy_map(m)
    if set(gm.keys()) != set(Xm):
        raise AssertionError("Fold_m image mismatch.")
    return gm


def dataset_for_m(m: int) -> List[Datum]:
    if m < 6:
        raise ValueError("m must be >= 6.")
    Xm = xm.all_xm(m)
    gm = foldm_degeneracy_map(m, Xm=Xm)

    lifts_of: Dict[str, List[str]] = defaultdict(list)
    for w in Xm:
        lifts_of[w[:6]].append(w)

    out: List[Datum] = []
    for u, y_num in build_base_targets():
        lifts = lifts_of.get(u, [])
        if not lifts:
            raise AssertionError("Missing lift fiber.")
        ext = len(lifts)
        bdry = sum(1 for w in lifts if is_boundary_word(w))
        gs = [gm[w] for w in lifts]
        g_min = min(gs)
        g_max = max(gs)
        Vs = [zeckendorf_value_m(w) for w in lifts]
        v_min = min(Vs)
        v_max = max(Vs)
        v_width = v_max - v_min
        out.append(
            Datum(
                u=u,
                y_num=y_num,
                ext=ext,
                bdry=bdry,
                g_min=g_min,
                g_max=g_max,
                v_min=v_min,
                v_max=v_max,
                v_width=v_width,
            )
        )
    if len(out) != 18:
        raise AssertionError("Expected 18 cyclic base points.")
    return out


def best_two_affine(
    feats: List[Tuple[int, ...]],
    ys: List[int],
    B: int,
    progress: ProgressEvery | None = None,
) -> Tuple[Tuple, Tuple | None]:
    """
    Return best/second candidate in the domain coeffs in [-B,B]^d, minimizing:
      (errors, complexity, coeffs) lexicographically,
    where complexity = sum|coeffs|.
    """
    if not feats:
        raise AssertionError("Empty dataset.")
    d = len(feats[0])
    vals = list(range(-B, B + 1))

    best = None  # (errors, complexity, coeffs, acc)
    second = None
    i = 0
    for coeffs in itertools.product(vals, repeat=d):
        if progress is not None:
            progress.maybe(i)
        i += 1
        if all(a == 0 for a in coeffs):
            continue
        err = 0
        for x, y in zip(feats, ys):
            s = sum(a * v for a, v in zip(coeffs, x))
            pred = nearest_allowed(s)
            if pred != y:
                err += 1
        comp = sum(abs(a) for a in coeffs)
        acc = 1.0 - float(err) / float(len(ys))
        cand = (err, comp, tuple(coeffs), acc)
        if best is None or cand < best:
            second = best
            best = cand
        elif second is None or cand < second:
            if best is None or tuple(coeffs) != best[2]:
                second = cand
    if best is None:
        raise AssertionError("No candidates enumerated.")
    return best, second


def main() -> None:
    m_list = [8, 10, 12, 14, 16]
    families = [
        ("ext,bdry,gmin,gmax,Vwidth", 3, lambda p: (p.ext, p.bdry, p.g_min, p.g_max, p.v_width, 1)),
        ("ext,bdry,Vmin,Vmax", 3, lambda p: (p.ext, p.bdry, p.v_min, p.v_max, 1)),
    ]

    rows: List[str] = []
    for m in m_list:
        data = dataset_for_m(m)
        ys = [p.y_num for p in data]
        for fam_name, B, feat_fn in families:
            feats = [feat_fn(p) for p in data]
            total = (2 * B + 1) ** len(feats[0])
            prog = ProgressEvery(label=f"inverse_highm_ynum m={m} fam={fam_name}", total=total, interval_s=60.0)
            prog.start()
            best, second = best_two_affine(feats=feats, ys=ys, B=B, progress=prog)
            prog.done()
            err1, comp1, coeffs1, acc1 = best
            if second is None:
                coeffs2 = tuple(0 for _ in coeffs1)
                acc2 = 0.0
            else:
                _err2, _comp2, coeffs2, acc2 = second
            gap = acc1 - acc2
            c1_tex = ",".join(str(x) for x in coeffs1)
            c2_tex = ",".join(str(x) for x in coeffs2)
            rows.append(
                f"{m} & \\texttt{{{fam_name}}} & $|a_i|\\le {B}$ & "
                f"$({c1_tex})$ & {err1} & {acc1:.3f} & $({c2_tex})$ & {gap:.3f} & {comp1} \\\\"
            )
    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "inverse_highm_hypercharge_full_fit_rows.tex", rows)
    print("Wrote sections/generated/inverse_highm_hypercharge_full_fit_rows.tex")


if __name__ == "__main__":
    main()


