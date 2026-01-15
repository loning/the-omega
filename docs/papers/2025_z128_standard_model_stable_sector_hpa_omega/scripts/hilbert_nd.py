# -*- coding: utf-8 -*-
"""
N-dimensional Hilbert curve utilities (Skilling-style bit-operations).

This module implements the classical nD Hilbert mapping at finite order p (bits per axis):
  - index h in {0..2^{n*p}-1}  <->  coords x[0..n-1] in {0..2^p-1}^n

Reference:
  John Skilling, "Programming the Hilbert curve" (2004).

Notes:
  - This is used as a visualization / locality tool for multi-dimensional screens.
  - For the paper's 2D anchor Hilbert map H_n, we keep the existing 2D implementation
    in exp_hilbert_chirality_index.py to preserve orientation conventions.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


def _integer_to_transpose(h: int, p: int, n: int) -> List[int]:
    """
    Extract the 'transpose' representation: n integers with p bits each.
    """
    if p <= 0 or n <= 0:
        raise ValueError("Require p>0 and n>0.")
    # LSB-first bit layout (Skilling convention): bit i of coordinate j comes from
    # position (i*n + (n-1-j)) of the Hilbert integer.
    x = [0] * n
    for i in range(p):  # bit index within coordinate (LSB-first)
        for j in range(n):
            bit = (h >> (i * n + (n - 1 - j))) & 1
            x[j] |= int(bit) << i
    return [int(v) for v in x]


def _transpose_to_integer(x: List[int], p: int, n: int) -> int:
    """
    Inverse of _integer_to_transpose.
    """
    if len(x) != n:
        raise ValueError("x must have length n.")
    h = 0
    for i in range(p):  # bit index within coordinate (LSB-first)
        for j in range(n):
            bit = (int(x[j]) >> i) & 1
            h |= int(bit) << (i * n + (n - 1 - j))
    return int(h)


def hilbert_index_to_coords(h: int, p: int, n: int) -> List[int]:
    """
    Map Hilbert index h to nD coordinates, each with p bits (0..2^p-1).
    """
    if h < 0:
        raise ValueError("h must be non-negative.")
    if p <= 0 or n <= 0:
        raise ValueError("Require p>0 and n>0.")
    if h >= (1 << (n * p)):
        raise ValueError("h out of range for (p,n).")

    x = _integer_to_transpose(h, p, n)

    # Gray decode.
    t = x[-1] >> 1
    for i in range(n - 1, 0, -1):
        x[i] ^= x[i - 1]
    x[0] ^= t

    # Undo excess work.
    Q = 2
    while Q != (1 << p):
        P = Q - 1
        for i in range(n - 1, -1, -1):
            if x[i] & Q:
                x[0] ^= P
            else:
                t = (x[0] ^ x[i]) & P
                x[0] ^= t
                x[i] ^= t
        Q <<= 1
    return [int(v) for v in x]


_INV_CACHE: Dict[Tuple[int, int], Dict[Tuple[int, ...], int]] = {}


def hilbert_coords_to_index(coords: List[int], p: int, n: int) -> int:
    """
    Map nD coordinates (each 0..2^p-1) to Hilbert index h in {0..2^{n*p}-1}.

    Implementation note:
      For this paper we only need index->coords for constructing locality-optimal
      scan paths. When coords->index is needed (e.g. sorting by Hilbert key), we
      provide a deterministic inverse via cached full inversion of the finite map.
      This avoids subtle convention bugs and is safe at the small sizes used in
      figures (e.g. n<=5, p<=5).
    """
    if len(coords) != n:
        raise ValueError("coords must have length n.")
    if p <= 0 or n <= 0:
        raise ValueError("Require p>0 and n>0.")
    maxv = (1 << p) - 1
    c = tuple(int(v) for v in coords)
    if any(v < 0 or v > maxv for v in c):
        raise ValueError("coords out of range for p bits.")

    key = (p, n)
    inv = _INV_CACHE.get(key)
    if inv is None:
        N = 1 << (n * p)
        # Guard against accidental huge inversions.
        if N > (1 << 20):
            raise ValueError("coords->index inversion too large for this figure utility.")
        inv = {}
        for h in range(N):
            cc = tuple(hilbert_index_to_coords(h, p, n))
            inv[cc] = int(h)
        if len(inv) != N:
            raise AssertionError("Hilbert map inversion collision (unexpected).")
        _INV_CACHE[key] = inv
    if c not in inv:
        raise KeyError("Coordinate is not in the Hilbert grid (unexpected).")
    return int(inv[c])


def _manhattan_path_jumps(coords: List[List[int]]) -> int:
    """
    Return max L1 jump along a coordinate path.
    """
    if len(coords) < 2:
        return 0
    mx = 0
    for a, b in zip(coords[:-1], coords[1:]):
        mx = max(mx, sum(abs(int(ai) - int(bi)) for ai, bi in zip(a, b)))
    return int(mx)


def self_check() -> None:
    """
    Minimal sanity checks: bijection and adjacency for small cases.
    """
    for n in (2, 3, 4):
        for p in (1, 2, 3):
            N = 1 << (n * p)
            # Full-path uniqueness + adjacency.
            path = [hilbert_index_to_coords(h, p, n) for h in range(N)]
            if len({tuple(v) for v in path}) != N:
                raise AssertionError(f"Uniqueness failed n={n} p={p}.")
            mx = _manhattan_path_jumps(path)
            if mx != 1:
                raise AssertionError(f"Adjacency failed n={n} p={p} max_jump={mx}")
            # Cached inversion spot-check.
            for h in (0, 1, 2, N // 3, N // 2, N - 2, N - 1):
                hh = hilbert_coords_to_index(path[h], p, n)
                if hh != h:
                    raise AssertionError(f"Inversion failed n={n} p={p} h={h} got={hh}")


if __name__ == "__main__":
    self_check()
    print("hilbert_nd self_check OK")

