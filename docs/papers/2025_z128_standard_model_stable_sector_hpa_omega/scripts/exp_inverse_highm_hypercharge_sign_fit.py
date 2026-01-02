# -*- coding: utf-8 -*-
"""
High-m inverse diagnostic: recover sign(Y) using lift-fiber invariants.

We work on the cyclic base types u in X6 (18 points) paired with the 18 fermion
targets under the closed ordering used by the labeling solver.

For a higher window length m, define the lift fiber:
  Ext_m(u) := { w in X_m : w[:6] = u }.

We compute a small set of lift-fiber invariants:
  - ext := |Ext_m(u)|
  - bdry := number of boundary words in Ext_m(u) under the pi-channel predicate w1=wm=1
  - g_min, g_max := min/max Fold_m degeneracy over w in Ext_m(u)
  - V_min, V_max := min/max V_m(w) over the fiber, where V_m uses Fibonacci weights [F2..F_{m+1}]
  - V_width := V_max - V_min

We search bounded-complexity linear scores S(u)=<a,features(u)> with integer coefficients,
then classify sign(Y) in {-1,0,+1} using two thresholds t1 < t2 and an interval-to-class
permutation pi:
  class = pi0 if S<=t1, pi1 if t1<S<=t2, pi2 otherwise.

Selection is lexicographic minimization of:
  (errors, complexity, coeffs, t1, t2, pi),
where complexity = sum|coeffs| + |t1| + |t2|.

Outputs (LaTeX fragment):
  - sections/generated/inverse_highm_hypercharge_sign_fit_rows.tex

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


def sign(x: int) -> int:
    return -1 if x < 0 else (1 if x > 0 else 0)


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
    y_sign: int  # -1,0,+1
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
        out.append((u, sign(f.Y_num)))
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
    for u, y_sign in build_base_targets():
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
                y_sign=y_sign,
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


def best_sign_fit(
    feats: List[Tuple[int, ...]],
    ys: List[int],
    B: int,
    progress: ProgressEvery | None = None,
) -> Tuple[int, int, Tuple[int, ...], int, int, Tuple[int, int, int]]:
    """
    Return best (errors, complexity, coeffs, t1, t2, pi) over:
      coeffs in [-B,B]^d (not all zero),
      thresholds t1<t2 chosen from observed score values,
      pi a permutation of (-1,0,1).
    """
    classes = (-1, 0, 1)
    perms = list(itertools.permutations(classes, 3))
    n = len(ys)
    if n == 0:
        raise AssertionError("Empty dataset.")
    d = len(feats[0]) if feats else 0
    if d <= 0:
        raise AssertionError("Empty feature dimension.")
    vals = list(range(-B, B + 1))

    best = None  # (errors, complexity, coeffs, t1, t2, pi)
    i = 0
    for coeffs in itertools.product(vals, repeat=d):
        if progress is not None:
            progress.maybe(i)
        i += 1
        if all(a == 0 for a in coeffs):
            continue

        # Scores on the dataset.
        scores = [sum(a * v for a, v in zip(coeffs, x)) for x in feats]
        uniq = sorted(set(scores))
        if len(uniq) < 2:
            continue

        # Bucket counts per unique score value.
        idx_of = {v: i for i, v in enumerate(uniq)}
        counts = [[0, 0, 0] for _ in uniq]  # [-1,0,+1]
        for s, y in zip(scores, ys):
            i = idx_of[s]
            j = 0 if y == -1 else (1 if y == 0 else 2)
            counts[i][j] += 1

        # Prefix sums.
        pref = [[0] * len(uniq) for _ in range(3)]
        for j in range(3):
            run = 0
            for i in range(len(uniq)):
                run += counts[i][j]
                pref[j][i] = run
        tot = [pref[j][-1] for j in range(3)]

        # Enumerate permutations; for each pi compute the optimal (t1,t2) in O(k).
        k = len(uniq)
        for pi in perms:
            j0 = 0 if pi[0] == -1 else (1 if pi[0] == 0 else 2)
            j1 = 0 if pi[1] == -1 else (1 if pi[1] == 0 else 2)
            j2 = 0 if pi[2] == -1 else (1 if pi[2] == 0 else 2)

            # A[i1] = pref[j0][i1] - pref[j1][i1]
            # B[i2] = pref[j1][i2] - pref[j2][i2]
            bestA_val = pref[j0][0] - pref[j1][0]
            bestA_i1 = 0

            best_correct = -1
            best_t1 = uniq[0]
            best_t2 = uniq[1]

            for i2 in range(1, k):
                # Expand the admissible i1 range to include i2-1.
                i1cand = i2 - 1
                Acand = pref[j0][i1cand] - pref[j1][i1cand]
                if Acand > bestA_val:
                    bestA_val = Acand
                    bestA_i1 = i1cand
                # If tie, keep earlier i1 (smaller t1) deterministically.

                Bval = pref[j1][i2] - pref[j2][i2]
                correct = bestA_val + Bval + tot[j2]
                if correct > best_correct:
                    best_correct = correct
                    best_t1 = uniq[bestA_i1]
                    best_t2 = uniq[i2]
                elif correct == best_correct:
                    # Deterministic tie-break: prefer smaller t1, then smaller t2.
                    t1 = uniq[bestA_i1]
                    t2 = uniq[i2]
                    if (t1, t2) < (best_t1, best_t2):
                        best_t1, best_t2 = t1, t2

            err = n - best_correct
            comp = sum(abs(a) for a in coeffs) + abs(best_t1) + abs(best_t2)
            cand = (err, comp, tuple(coeffs), best_t1, best_t2, pi)
            if best is None or cand < best:
                best = cand

    if best is None:
        raise AssertionError("No candidates enumerated.")
    err, comp, coeffs, t1, t2, pi = best
    return int(err), int(comp), tuple(coeffs), int(t1), int(t2), pi


def main() -> None:
    m_list = [8, 10, 12, 14, 16]
    families = [
        ("ext,bdry,gmin,gmax,Vwidth", 2, lambda p: (p.ext, p.bdry, p.g_min, p.g_max, p.v_width, 1)),
        ("ext,bdry,Vmin,Vmax", 2, lambda p: (p.ext, p.bdry, p.v_min, p.v_max, 1)),
    ]

    rows: List[str] = []
    for m in m_list:
        data = dataset_for_m(m)
        ys = [p.y_sign for p in data]
        for fam_name, B, feat_fn in families:
            feats = [feat_fn(p) for p in data]
            total = (2 * B + 1) ** len(feats[0])
            prog = ProgressEvery(label=f"inverse_highm_sign m={m} fam={fam_name}", total=total, interval_s=60.0)
            prog.start()
            err, comp, coeffs, t1, t2, pi = best_sign_fit(feats=feats, ys=ys, B=B, progress=prog)
            prog.done()
            acc = 1.0 - float(err) / float(len(ys))
            c_tex = ",".join(str(x) for x in coeffs)
            rows.append(
                f"{m} & \\texttt{{{fam_name}}} & $|a_i|\\le {B}$ & "
                f"$(a,\\dots,t_1,t_2,\\pi)=({c_tex},{t1},{t2},{pi})$ & {err} & {acc:.3f} \\\\"
            )
    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "inverse_highm_hypercharge_sign_fit_rows.tex", rows)
    print("Wrote sections/generated/inverse_highm_hypercharge_sign_fit_rows.tex")


if __name__ == "__main__":
    main()


