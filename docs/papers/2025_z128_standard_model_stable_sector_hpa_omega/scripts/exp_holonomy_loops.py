# -*- coding: utf-8 -*-
"""
Toy holonomy computation on elementary plaquettes of the n=3 Hilbert grid.

We use the same discrete-connection construction as exp_edge_mismatch_decomposition.py:
an S4-valued transport map on each undirected edge, defined by a minimum-cost
matching between padded preimage fibers.

For each unit square (plaquette) in the 8x8 grid, we compute the loop holonomy as
the product of the four oriented edge permutations. The result is a permutation in S4.

We summarize the distribution by S4 cycle type.

Outputs (LaTeX fragment):
  - sections/generated/holonomy_cycle_type_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import exp_fold6_stats as fold
import exp_hilbert_chirality_index as hil


Coord = Tuple[int, int]
Perm = Tuple[int, int, int, int]


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
    while len(xs) < 4:
        xs.append(xs[-1])
    return xs[:4]


def best_perm(fa: List[int], fb: List[int]) -> Perm:
    a_bits = [bits6(x) for x in fa]
    b_bits = [bits6(x) for x in fb]
    best: Tuple[int, Perm] | None = None
    for p in itertools.permutations((0, 1, 2, 3), 4):
        cost = 0
        for i in range(4):
            cost += hamming(a_bits[i], b_bits[p[i]])
        cand = (cost, p)
        if best is None or cand < best:
            best = cand
    if best is None:
        raise AssertionError("No permutations enumerated.")
    return best[1]


def inv_perm(p: Perm) -> Perm:
    inv = [0, 0, 0, 0]
    for i, j in enumerate(p):
        inv[j] = i
    return (inv[0], inv[1], inv[2], inv[3])


def compose(p: Perm, q: Perm) -> Perm:
    # Return p ∘ q (apply q then p).
    return (p[q[0]], p[q[1]], p[q[2]], p[q[3]])


def cycle_type(p: Perm) -> str:
    # Canonical cycle-type string for S4: 1, 2, 2x2, 3, 4.
    seen = [False, False, False, False]
    lengths: List[int] = []
    for i in range(4):
        if seen[i]:
            continue
        j = i
        k = 0
        while not seen[j]:
            seen[j] = True
            j = p[j]
            k += 1
        lengths.append(k)
    lengths.sort(reverse=True)
    if lengths == [1, 1, 1, 1]:
        return "1"
    if lengths == [2, 1, 1]:
        return "2"
    if lengths == [2, 2]:
        return "2x2"
    if lengths == [3, 1]:
        return "3"
    if lengths == [4]:
        return "4"
    return "other"


def grid_labels(n_bits: int = 3) -> Dict[Coord, str]:
    path = hil.hilbert_curve(n_bits)
    idx_of: Dict[Coord, int] = {}
    for k, c in enumerate(path):
        idx_of[(int(c[0]), int(c[1]))] = k
    out: Dict[Coord, str] = {}
    for coord, k in idx_of.items():
        out[coord] = fold.fold6(k)
    return out


def edge_perm_cache(labels: Dict[Coord, str], pre: Dict[str, List[int]]) -> Dict[Tuple[Coord, Coord], Perm]:
    # Cache undirected-edge permutations and expose both orientations with inverse.
    cache: Dict[Tuple[Coord, Coord], Perm] = {}

    def key(a: Coord, b: Coord) -> Tuple[Coord, Coord]:
        return (a, b) if a < b else (b, a)

    # Build for all neighbor edges.
    for x in range(8):
        for y in range(8):
            a = (x, y)
            for dx, dy in [(1, 0), (0, 1)]:
                nx, ny = x + dx, y + dy
                if nx >= 8 or ny >= 8:
                    continue
                b = (nx, ny)
                ka, kb = key(a, b)
                wa = labels[ka]
                wb = labels[kb]
                pa = fiber4(pre, wa)
                pb = fiber4(pre, wb)
                p = best_perm(pa, pb)
                cache[(ka, kb)] = p
    # Expand both orientations.
    out: Dict[Tuple[Coord, Coord], Perm] = {}
    for (a, b), p in cache.items():
        out[(a, b)] = p
        out[(b, a)] = inv_perm(p)
    return out


def main() -> None:
    labels = grid_labels(n_bits=3)
    pre = preimages()
    edge_p = edge_perm_cache(labels, pre)

    # Plaquettes: (x,y) for lower-left corner.
    hist = Counter()
    total = 0
    for x in range(7):
        for y in range(7):
            a = (x, y)
            b = (x + 1, y)
            c = (x + 1, y + 1)
            d = (x, y + 1)
            # Loop a->b->c->d->a
            p_ab = edge_p[(a, b)]
            p_bc = edge_p[(b, c)]
            p_cd = edge_p[(c, d)]
            p_da = edge_p[(d, a)]
            hol = compose(p_da, compose(p_cd, compose(p_bc, p_ab)))
            hist[cycle_type(hol)] += 1
            total += 1

    if total != 49:
        raise AssertionError(f"Expected 49 plaquettes at 8x8, got {total}.")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[str] = []
    for ct in ["1", "2", "2x2", "3", "4", "other"]:
        cnt = hist.get(ct, 0)
        frac = float(cnt) / float(total) if total else 0.0
        rows.append(f"\\texttt{{{ct}}} & {cnt} & {frac:.3f} \\\\")
    rows.append("\\bottomrule")
    (out_dir / "holonomy_cycle_type_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/holonomy_cycle_type_rows.tex")


if __name__ == "__main__":
    main()


