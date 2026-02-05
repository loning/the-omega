#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Micro adjacency models: hypercube, bit-split lattice, Hilbert-lattice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple


def hypercube_neighbors(m: int) -> List[List[int]]:
    """Neighbor lists for hypercube on {0,1}^m (node ids 0..2^m-1)."""
    n = 1 << m
    out: List[List[int]] = [[] for _ in range(n)]
    for x in range(n):
        out[x] = [x ^ (1 << k) for k in range(m)]
    return out


def balanced_splits(m: int, d: int) -> List[int]:
    """Split m bits into d groups as evenly as possible (sum=s)."""
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


def bitsplit_neighbors(m: int, d: int, torus: bool = False) -> List[List[int]]:
    """Adjacency from axis neighbors on product grid of sizes 2^{s_j}."""
    splits = balanced_splits(m, d)
    dims = [1 << s for s in splits]
    n = 1 << m
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
    from hilbertcurve.hilbertcurve import HilbertCurve

    hc = HilbertCurve(p=power, n=ndim)
    n = 1 << (power * ndim)
    coords: List[Tuple[int, ...]] = []
    for i in range(n):
        coords.append(tuple(int(v) for v in hc.point_from_distance(i)))
    return HilbertEmbedding(dims=tuple([1 << power] * ndim), coords=coords)


def hilbert_neighbors(power: int, ndim: int, torus: bool = False) -> List[List[int]]:
    """Axis-neighbor adjacency on Hilbert-embedded lattice (pulled back to index space)."""
    emb = hilbert_embedding(power=power, ndim=ndim)
    dims = emb.dims
    n = len(emb.coords)
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

