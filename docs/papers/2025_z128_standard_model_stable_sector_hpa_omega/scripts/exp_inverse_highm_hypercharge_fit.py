# -*- coding: utf-8 -*-
"""
High-m inverse diagnostic: recover (6Y)^2 classes using lift-fiber invariants.

We work on the cyclic base types u in X6 (18 points) paired with the 18 fermion
targets under the closed ordering used by the labeling solver.

For a higher window length m, we consider the prefix lift fiber:
  Ext_m(u) := { w in X_m : w[:6] = u }.

We compute simple intrinsic invariants of this fiber:
  - ext := |Ext_m(u)|
  - bdry := number of boundary words in Ext_m(u) under the pi-channel predicate w1=wm=1
  - g_min, g_max := min/max Fold_m degeneracy over w in Ext_m(u)
  - V_min, V_max := min/max V_m(w) over the fiber, where V_m uses Fibonacci weights [F2..F_{m+1}]
  - V_width := V_max - V_min

We then test bounded-complexity integer affine scores on small feature families and
predict the target class (6Y)^2 by snapping the score to the nearest allowed value:
  {0,1,4,9,16,36}
with deterministic tie-break.

Outputs (LaTeX fragment):
  - sections/generated/inverse_highm_hypercharge_fit_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import exp_foldm_stats as foldm
import exp_sm_labeling_solver as sml
import exp_xm_enumeration as xm
from common_tex import write_lines
from common_progress import ProgressEvery


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
    y2: int  # (6Y)^2 target class
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
        out.append((u, f.Y_num * f.Y_num))
    return out


def foldm_degeneracy_map(m: int, Xm: List[str]) -> Dict[str, int]:
    pre: Dict[str, int] = defaultdict(int)
    for k in range(1 << m):
        pre[foldm.foldm(k, m)] += 1
    if set(pre.keys()) != set(Xm):
        raise AssertionError("Fold_m image mismatch.")
    return dict(pre)


def dataset_for_m(m: int) -> List[Datum]:
    if m < 6:
        raise ValueError("m must be >= 6.")
    Xm = xm.all_xm(m)
    gm = foldm_degeneracy_map(m, Xm=Xm)

    lifts_of: Dict[str, List[str]] = defaultdict(list)
    for w in Xm:
        lifts_of[w[:6]].append(w)

    out: List[Datum] = []
    for u, y2 in build_base_targets():
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
                y2=y2,
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


def accuracy_for(coeffs: Tuple[int, ...], feats: List[Tuple[int, ...]], y2s: List[int]) -> Tuple[int, int]:
    correct = 0
    for x, y2 in zip(feats, y2s):
        s = 0
        for a, v in zip(coeffs, x):
            s += a * v
        pred = snap_to_class(s)
        if pred == y2:
            correct += 1
    return correct, len(y2s)


def best_two_affine(
    feats: List[Tuple[int, ...]],
    y2s: List[int],
    B: int,
    progress: ProgressEvery | None = None,
) -> Tuple[Tuple, Tuple | None]:
    best = None
    second = None
    d = len(feats[0]) if feats else 0
    if d <= 0:
        raise AssertionError("Empty feature dimension.")
    vals = list(range(-B, B + 1))
    # Enumerate coefficient tuples by product; deterministic ordering.
    import itertools

    i = 0
    for coeffs in itertools.product(vals, repeat=d):
        if progress is not None:
            progress.maybe(i)
        i += 1
        correct, total = accuracy_for(tuple(coeffs), feats=feats, y2s=y2s)
        acc = float(correct) / float(total)
        comp = sum(abs(a) for a in coeffs)
        cand = (-correct, comp, tuple(coeffs), acc)
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
        ("ext,bdry,gmin,gmax,Vwidth", 4, lambda p: (p.ext, p.bdry, p.g_min, p.g_max, p.v_width, 1)),
        ("ext,bdry,gmin,gmax,Vmin,Vmax", 3, lambda p: (p.ext, p.bdry, p.g_min, p.g_max, p.v_min, p.v_max, 1)),
        ("ext,bdry,Vmin,Vmax", 4, lambda p: (p.ext, p.bdry, p.v_min, p.v_max, 1)),
    ]

    rows: List[str] = []
    for m in m_list:
        data = dataset_for_m(m)
        y2s = [p.y2 for p in data]
        for fam_name, B, feat_fn in families:
            feats = [feat_fn(p) for p in data]
            # Heartbeat for potentially long coefficient scans.
            total = (2 * B + 1) ** len(feats[0])
            prog = ProgressEvery(label=f"inverse_highm_y2 m={m} fam={fam_name}", total=total, interval_s=60.0)
            prog.start()

            best, second = best_two_affine(feats=feats, y2s=y2s, B=B, progress=prog)
            _neg1, comp1, coeffs1, acc1 = best
            if second is None:
                coeffs2 = tuple(0 for _ in coeffs1)
                acc2 = 0.0
            else:
                _neg2, _comp2, coeffs2, acc2 = second
            gap = acc1 - acc2
            c1_tex = ",".join(str(x) for x in coeffs1)
            c2_tex = ",".join(str(x) for x in coeffs2)
            rows.append(
                f"{m} & \\texttt{{{fam_name}}} & $|a_i|\\le {B}$ & "
                f"$({c1_tex})$ & {acc1:.3f} & "
                f"$({c2_tex})$ & {gap:.3f} & {comp1} \\\\"
            )
            prog.done()
    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "inverse_highm_hypercharge_fit_rows.tex", rows)
    print("Wrote sections/generated/inverse_highm_hypercharge_fit_rows.tex")


if __name__ == "__main__":
    main()


