# -*- coding: utf-8 -*-
"""
Edge mismatch decomposition on the n=3 Hilbert-addressed grid.

We embed indices k=0..63 into an 8x8 grid via the Hilbert curve H_3(k) and label
each site by its stable type w = Fold_6(k).

To model "compensation as connection", we attach to each undirected grid edge a
deterministic discrete transport map between the microstate fibers underlying
the two endpoint stable types:
  - For each stable type w, its fiber is the preimage set P(w)={k: Fold_6(k)=w}.
  - We pad each fiber deterministically to length 4 (the maximum degeneracy at m=6).
  - For an edge {a,b}, we choose the minimum-cost bijection between the padded
    fibers using Hamming distance on 6-bit binary words, yielding a permutation
    in S4 that acts as a finite discrete connection element.

This script reports basic distributions needed for an auditable, finite-resolution
connection model.

Outputs (LaTeX fragments):
  - sections/generated/edge_mismatch_deg_pair_rows.tex
  - sections/generated/edge_mismatch_cost_quantiles_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import exp_fold6_stats as fold
import exp_hilbert_chirality_index as hil


Coord = Tuple[int, int]
Perm = Tuple[int, int, int, int]  # permutation of (0,1,2,3)


def bits6(n: int) -> str:
    return format(n, "06b")


def hamming(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)


def preimages() -> Dict[str, List[int]]:
    pre: Dict[str, List[int]] = defaultdict(list)
    for k in range(64):
        pre[fold.fold6(k)].append(k)
    for w in pre:
        pre[w] = sorted(pre[w])
    return dict(pre)


def fiber4(pre: Dict[str, List[int]], w: str) -> List[int]:
    xs = list(pre[w])
    if not xs:
        raise AssertionError("Empty fiber.")
    while len(xs) < 4:
        xs.append(xs[-1])
    if len(xs) != 4:
        raise AssertionError("Fiber padding error.")
    return xs


def best_perm(fa: List[int], fb: List[int]) -> Tuple[Perm, int]:
    """
    Return the minimum-cost permutation p (mapping positions 0..3 in fa to fb),
    plus the total Hamming cost.
    Deterministic tie-break: lexicographic p.
    """
    if len(fa) != 4 or len(fb) != 4:
        raise ValueError("best_perm requires length-4 lists.")
    a_bits = [bits6(x) for x in fa]
    b_bits = [bits6(x) for x in fb]
    best: Tuple[int, Perm] | None = None
    for p in itertools.permutations((0, 1, 2, 3), 4):
        cost = 0
        for i in range(4):
            cost += hamming(a_bits[i], b_bits[p[i]])
        cand = (cost, p)  # tie-break by p
        if best is None or cand < best:
            best = cand
    if best is None:
        raise AssertionError("No permutations enumerated.")
    return best[1], best[0]


def inv_perm(p: Perm) -> Perm:
    inv = [0, 0, 0, 0]
    for i, j in enumerate(p):
        inv[j] = i
    return (inv[0], inv[1], inv[2], inv[3])


def grid_labels(n_bits: int = 3) -> Dict[Coord, str]:
    path = hil.hilbert_curve(n_bits)
    idx_of: Dict[Coord, int] = {}
    for k, c in enumerate(path):
        idx_of[(int(c[0]), int(c[1]))] = k
    out: Dict[Coord, str] = {}
    for coord, k in idx_of.items():
        out[coord] = fold.fold6(k)
    return out


def all_edges(L: int) -> List[Tuple[Coord, Coord]]:
    edges: List[Tuple[Coord, Coord]] = []
    for y in range(L + 1):
        for x in range(L + 1):
            if x + 1 <= L:
                edges.append(((x, y), (x + 1, y)))
            if y + 1 <= L:
                edges.append(((x, y), (x, y + 1)))
    return edges


def quantile(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        raise ValueError("quantile requires a non-empty list.")
    if not (0.0 <= q <= 1.0):
        raise ValueError("q must be in [0,1].")
    n = len(sorted_vals)
    idx = int(round(q * float(n - 1)))
    return sorted_vals[idx]


def main() -> None:
    L = 7  # 8x8 grid
    labels = grid_labels(n_bits=3)
    pre = preimages()

    deg_pair = Counter()  # (min_deg,max_deg) -> count
    costs: List[int] = []

    for a, b in all_edges(L):
        wa = labels[a]
        wb = labels[b]
        da = len(pre[wa])
        db = len(pre[wb])
        deg_pair[(min(da, db), max(da, db))] += 1

        fa = fiber4(pre, wa)
        fb = fiber4(pre, wb)
        _p, cost = best_perm(fa, fb)
        costs.append(cost)

    total_edges = sum(deg_pair.values())
    if total_edges != 112:
        raise AssertionError(f"Expected 112 edges at 8x8, got {total_edges}.")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Degree-pair table rows.
    deg_rows: List[str] = []
    for (d1, d2) in sorted(deg_pair):
        cnt = deg_pair[(d1, d2)]
        frac = float(cnt) / float(total_edges)
        deg_rows.append(f"$({d1},{d2})$ & {cnt} & {frac:.3f} \\\\")
    deg_rows.append("\\bottomrule")
    (out_dir / "edge_mismatch_deg_pair_rows.tex").write_text("\n".join(deg_rows), encoding="utf-8")

    # Cost quantiles.
    s = sorted(float(c) for c in costs)
    q_rows: List[str] = []
    for q in [0.0, 0.5, 0.9, 0.99, 1.0]:
        q_rows.append(f"{q:.2f} & {quantile(s, q):.3f} \\\\")
    q_rows.append("\\bottomrule")
    (out_dir / "edge_mismatch_cost_quantiles_rows.tex").write_text("\n".join(q_rows), encoding="utf-8")

    print("Wrote sections/generated/edge_mismatch_deg_pair_rows.tex and edge_mismatch_cost_quantiles_rows.tex")


if __name__ == "__main__":
    main()


