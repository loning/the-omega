# -*- coding: utf-8 -*-
"""
Universal variable-fanout screen (VFS): a deterministic addressing for arbitrary (m,n).

Motivation (reader/audit facing):
  In the paper we often "balance" cardinalities by choosing a screen so that
    |Ω_m| = 2^m  matches  |screen| = 2^{d n}
  for some embedding dimension d and a resolution parameter n.

  For the 2D Hilbert screen used in theorem-level diagnostics, d=2 and the exact
  bijection occurs at m=2n. For other (m,n), one needs an explicit convention.

This module provides a CAP-style deterministic convention that works for any m,n:
  - define effective dimension      d_eff := m/n,
  - define embedding dimension      D := ceil(d_eff),
  - view the screen as a D-dim dyadic grid of side 2^n (capacity 2^{Dn}),
  - populate exactly 2^m cells via an n-level dyadic refinement with variable fanout,
    allocating g_i bits to level i so sum_i g_i = m and 0 <= g_i <= D.

The resulting occupied set is a self-similar (dyadic) subset of the D-cube whose
box dimension equals d_eff = m/n, interpolating smoothly between integer-D cases.

This is intended as a *visualization addressing choice*; it does not replace the
2D Hilbert addressing used elsewhere for finite diagnostics.
"""

from __future__ import annotations

import math
from typing import List, Tuple


def effective_dimension(m: int, n: int) -> float:
    if n <= 0:
        raise ValueError("n must be positive.")
    if m < 0:
        raise ValueError("m must be non-negative.")
    return float(m) / float(n)


def embedding_dimension(m: int, n: int) -> int:
    """
    Minimal integer D such that 2^{D n} >= 2^m, i.e. Dn >= m.
    """
    if n <= 0:
        raise ValueError("n must be positive.")
    if m < 0:
        raise ValueError("m must be non-negative.")
    return int((m + n - 1) // n)  # ceil(m/n)


def bits_per_level(m: int, n: int, D: int | None = None) -> List[int]:
    """
    Balanced per-level bit allocation g_0,...,g_{n-1} with:
      - sum g_i = m
      - each g_i in {floor(m/n), ceil(m/n)}
      - each g_i <= D, where D defaults to ceil(m/n).
    """
    if n <= 0:
        raise ValueError("n must be positive.")
    if m < 0:
        raise ValueError("m must be non-negative.")
    if D is None:
        D = embedding_dimension(m, n)
    q, r = divmod(m, n)
    g = [q + 1] * r + [q] * (n - r)
    if sum(g) != m:
        raise AssertionError("Internal error: bad bit allocation.")
    if any(gi < 0 or gi > D for gi in g):
        raise AssertionError("Internal error: allocation violates 0<=g_i<=D.")
    return g


def vfs_coord_from_k(k: int, m: int, n: int, *, D: int | None = None, g: List[int] | None = None) -> Tuple[int, ...]:
    """
    Map scan index k in {0..2^m-1} to a D-dimensional coordinate on a dyadic grid
    of side 2^n, using variable-fanout refinement with per-level bit counts g_i.

    Implementation detail:
      - consume k's bits level-by-level, LSB-first, in chunks of size g_i;
      - embed each g_i-bit chunk into a D-bit dyadic choice by writing those bits
        into a rotating subset of axes (cyclic schedule) and setting remaining axes to 0;
      - write the resulting D bits as the i-th (LSB) bit of each coordinate component.
    """
    if m < 0 or n <= 0:
        raise ValueError("Require m>=0, n>0.")
    if D is None:
        D = embedding_dimension(m, n)
    if g is None:
        g = bits_per_level(m, n, D=D)
    if len(g) != n:
        raise ValueError("g must have length n.")
    if sum(g) != m:
        raise ValueError("g must sum to m.")
    if D <= 0:
        raise ValueError("D must be positive.")

    N = 1 << m
    if k < 0 or k >= N:
        raise ValueError("k out of range for given m.")

    coords = [0] * D
    kk = int(k)
    for level in range(n):
        gi = int(g[level])
        if gi == 0:
            continue
        mask = (1 << gi) - 1
        u = kk & mask
        kk >>= gi

        start = level % D
        for j in range(gi):
            axis = (start + j) % D
            bit = (u >> j) & 1
            coords[axis] |= int(bit) << level

    if kk != 0:
        # Should never happen when sum(g)=m.
        raise AssertionError("Internal error: did not consume exactly m bits.")
    return tuple(int(c) for c in coords)


def holo_bulk_dimension(m: int, n: int) -> int:
    """
    Minimal bulk dimension for a "boundary-face" holographic embedding:
      - face dimension is D_face = ceil(m/n),
      - bulk dimension is D_face + 1.
    """
    return embedding_dimension(m, n) + 1


def vfs_holo_face_coord_from_k(
    k: int,
    m: int,
    n: int,
    *,
    face_axis: int = 0,
    face_side: int = 0,
) -> Tuple[int, ...]:
    """
    Holographic boundary-face embedding for arbitrary (m,n):

      k ∈ {0..2^m-1}
        -> coord_face ∈ {0..2^n-1}^{D_face}  via VFS with D_face=ceil(m/n)
        -> coord_bulk ∈ {0..2^n-1}^{D_face+1} by inserting a fixed boundary coordinate.

    The occupied set lies entirely on one bulk boundary face:
      x_{face_axis} = 0   if face_side=0
      x_{face_axis} = 2^n-1 if face_side=1

    This is a visualization convention for expressing "all information on the boundary"
    in a finite discrete setting; it is deterministic and bijective onto its image.
    """
    if face_side not in (0, 1):
        raise ValueError("face_side must be 0 or 1.")
    D_face = embedding_dimension(m, n)
    D_bulk = D_face + 1
    if not (0 <= face_axis < D_bulk):
        raise ValueError("face_axis out of range for the chosen bulk dimension.")
    L = 1 << n
    face_value = 0 if face_side == 0 else (L - 1)

    g = bits_per_level(m, n, D=D_face)
    coord_face = vfs_coord_from_k(k, m, n, D=D_face, g=g)
    coord = list(coord_face)
    coord.insert(int(face_axis), int(face_value))
    return tuple(int(x) for x in coord)

