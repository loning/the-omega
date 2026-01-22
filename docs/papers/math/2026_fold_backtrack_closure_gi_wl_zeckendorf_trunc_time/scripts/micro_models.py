#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Micro adjacency models and Hilbert/bit-split embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from hilbertcurve.hilbertcurve import HilbertCurve


def hypercube_neighbors(n: int, m: int) -> List[List[int]]:
    """Explicit neighbor lists for hypercube on {0,1}^m (node ids 0..2^m-1)."""
    out: List[List[int]] = [[] for _ in range(n)]
    for x in range(n):
        nb = []
        for k in range(m):
            nb.append(x ^ (1 << k))
        out[x] = nb
    return out


def balanced_splits(m: int, d: int) -> List[int]:
    if d <= 0 or d > m:
        raise ValueError("invalid d")
    base = m // d
    r = m % d
    return [base + (1 if i < r else 0) for i in range(d)]


def bitsplit_coords(x: int, splits: Sequence[int]) -> Tuple[int, ...]:
    coords = []
    shift = 0
    for s in splits:
        mask = (1 << s) - 1
        coords.append((x >> shift) & mask)
        shift += s
    return tuple(coords)


def bitsplit_index(coords: Sequence[int], splits: Sequence[int]) -> int:
    x = 0
    shift = 0
    for c, s in zip(coords, splits):
        x |= (c & ((1 << s) - 1)) << shift
        shift += s
    return x


def bitsplit_neighbors(n: int, splits: Sequence[int], torus: bool) -> List[List[int]]:
    """Adjacency from axis neighbors on product grid of sizes 2^{s_j}."""
    dims = [1 << s for s in splits]
    out: List[List[int]] = [[] for _ in range(n)]
    for x in range(n):
        c = list(bitsplit_coords(x, splits))
        nb: List[int] = []
        for j, L in enumerate(dims):
            for delta in (-1, 1):
                c2 = c.copy()
                if torus:
                    c2[j] = (c2[j] + delta) % L
                    nb.append(bitsplit_index(c2, splits))
                else:
                    v = c2[j] + delta
                    if 0 <= v < L:
                        c2[j] = v
                        nb.append(bitsplit_index(c2, splits))
        out[x] = nb
    return out


@dataclass(frozen=True)
class HilbertEmbedding:
    dims: Tuple[int, ...]
    coords: List[Tuple[int, ...]]  # index -> coord


def hilbert_embedding(power: int, ndim: int) -> HilbertEmbedding:
    """Hilbert embedding for a (2^power)^ndim lattice; index 0..2^{power*ndim}-1."""
    hc = HilbertCurve(p=power, n=ndim)
    n = 1 << (power * ndim)
    coords: List[Tuple[int, ...]] = []
    for i in range(n):
        coords.append(tuple(int(v) for v in hc.point_from_distance(i)))
    return HilbertEmbedding(dims=tuple([1 << power] * ndim), coords=coords)


def hilbert_neighbors(emb: HilbertEmbedding, torus: bool) -> List[List[int]]:
    """Adjacency from axis neighbors in coord space, pulled back to Hilbert index space."""
    dims = emb.dims
    ndim = len(dims)
    n = len(emb.coords)
    # Build inverse map coord -> index (unique by construction).
    inv = {emb.coords[i]: i for i in range(n)}
    out: List[List[int]] = [[] for _ in range(n)]
    for i in range(n):
        c = list(emb.coords[i])
        nb: List[int] = []
        for j, L in enumerate(dims):
            for delta in (-1, 1):
                c2 = c.copy()
                if torus:
                    c2[j] = (c2[j] + delta) % L
                else:
                    v = c2[j] + delta
                    if not (0 <= v < L):
                        continue
                    c2[j] = v
                nb.append(inv[tuple(c2)])
        out[i] = nb
    return out


def degree_stats(adj: List[List[int]]) -> Tuple[float, int, int]:
    degs = [len(x) for x in adj]
    return (sum(degs) / len(degs), min(degs), max(degs))

