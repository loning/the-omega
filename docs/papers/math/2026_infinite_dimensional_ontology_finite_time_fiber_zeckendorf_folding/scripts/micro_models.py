#!/usr/bin/env python3
"""
Micro display models (finite, auditable).

This paper primarily uses a bit-split lattice display:
  - microstates are indices 0..2^m-1 (packed m-bit words)
  - split bits into d blocks of sizes s_j with sum s_j=m
  - interpret each block as a coordinate in [0, 2^{s_j}-1]
  - connect axis-adjacent coordinates (open boundary or torus)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


def balanced_splits(m: int, d: int) -> List[int]:
    if m <= 0:
        raise ValueError("m must be positive")
    if d <= 0:
        raise ValueError("d must be positive")
    if d > m:
        # Allow empty dimensions? We forbid it to keep displays meaningful.
        raise ValueError("d must be <= m")
    base = m // d
    rem = m % d
    return [base + (1 if i < rem else 0) for i in range(d)]


@dataclass(frozen=True)
class BitSplitSpec:
    m: int
    d: int
    splits: Tuple[int, ...]
    offsets: Tuple[int, ...]
    masks: Tuple[int, ...]
    sizes: Tuple[int, ...]


def bit_split_spec(m: int, d: int, splits: Optional[Sequence[int]] = None) -> BitSplitSpec:
    if splits is None:
        splits = balanced_splits(m, d)
    splits_t = tuple(int(x) for x in splits)
    if sum(splits_t) != m:
        raise ValueError("splits must sum to m")
    if len(splits_t) != d:
        raise ValueError("len(splits) must equal d")
    if any(x <= 0 for x in splits_t):
        raise ValueError("splits must be positive")

    offsets: List[int] = []
    masks: List[int] = []
    sizes: List[int] = []

    off = 0
    for s in splits_t:
        offsets.append(off)
        masks.append(((1 << s) - 1) << off)
        sizes.append(1 << s)
        off += s

    return BitSplitSpec(
        m=int(m),
        d=int(d),
        splits=splits_t,
        offsets=tuple(offsets),
        masks=tuple(masks),
        sizes=tuple(sizes),
    )


def _get_block(word: int, mask: int, offset: int) -> int:
    return (word & mask) >> offset


def _set_block(word: int, mask: int, offset: int, value: int) -> int:
    return (word & ~mask) | ((value << offset) & mask)


def bitsplit_neighbors(m: int, d: int, torus: bool = False, splits: Optional[Sequence[int]] = None) -> List[List[int]]:
    """
    Return adjacency list for the bit-split lattice on 2^m microstates.
    Nodes are micro words packed into ints 0..2^m-1.
    """
    spec = bit_split_spec(m=m, d=d, splits=splits)
    n = 1 << m
    adj: List[List[int]] = [[] for _ in range(n)]

    for w in range(n):
        for j in range(spec.d):
            mask = spec.masks[j]
            off = spec.offsets[j]
            size = spec.sizes[j]
            c = _get_block(w, mask, off)

            if torus:
                # wrap around
                c1 = (c + 1) % size
                c2 = (c - 1) % size
                w1 = _set_block(w, mask, off, c1)
                w2 = _set_block(w, mask, off, c2)
                adj[w].append(w1)
                adj[w].append(w2)
            else:
                if c + 1 < size:
                    w1 = _set_block(w, mask, off, c + 1)
                    adj[w].append(w1)
                if c - 1 >= 0:
                    w2 = _set_block(w, mask, off, c - 1)
                    adj[w].append(w2)

    return adj


def degree_stats(adj: Sequence[Sequence[int]]) -> Tuple[float, int, int]:
    if not adj:
        return (0.0, 0, 0)
    degs = [len(xs) for xs in adj]
    return (sum(degs) / float(len(degs)), min(degs), max(degs))

