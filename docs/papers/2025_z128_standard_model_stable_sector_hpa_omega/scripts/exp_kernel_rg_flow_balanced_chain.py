# -*- coding: utf-8 -*-
"""
Balanced-chain kernel RG-flow table: coarse-grained scalar summaries across n=3..8.

We follow the balanced coupling m=2n used in the paper to attach microstate indices
to a 2D Hilbert screen:
  - n_bits := n (Hilbert order), side = 2^n_bits,
  - m := 2*n_bits, microstate indices k range over {0..2^m-1} = {0..4^n-1}.

At each (n,m) we:
  - label each site k by the stable word w = Fold_m(k),
  - attach intrinsic scalar observables q(w),
  - coarse-grain by block averaging on an axis-aligned 4x4 block partition
    (block size = 2^(n-2)), and
  - report the mean and variance of block averages as a compact cross-scale summary.

This is an audit artifact: it does not introduce new theorem-level claims.

Outputs (LaTeX fragment):
  - sections/generated/kernel_rg_flow_balanced_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from collections import defaultdict
import math
from typing import Callable, Dict, Iterable, List, Tuple

import exp_hilbert_chirality_index as hil
from common_paths import generated_dir
from common_tex import write_lines
from protocol_kernel import cached_degeneracy_map, cached_foldm_outputs, split_cyc_bdry


Point = Tuple[int, int]


def _mean(xs: Iterable[float]) -> float:
    xs = list(xs)
    if not xs:
        raise ValueError("mean() requires a non-empty list.")
    return sum(xs) / float(len(xs))


def _var_pop(xs: Iterable[float]) -> float:
    xs = list(xs)
    if not xs:
        raise ValueError("var() requires a non-empty list.")
    m = _mean(xs)
    return _mean([(x - m) ** 2 for x in xs])


def _fmt(x: float) -> str:
    # Keep fixed decimals for stable LaTeX diffs.
    return f"{x:.6f}"


def _block_stats_from_path(
    path: List[Point],
    values: List[float],
    *,
    n_bits: int,
    block: int,
) -> Tuple[float, float]:
    """
    Compute (mean, population variance) of block averages over a (2^n_bits)x(2^n_bits) grid,
    using a precomputed Hilbert path and per-index values aligned with the path order.
    """
    side = 1 << n_bits
    if len(path) != len(values):
        raise ValueError("path and values must have the same length.")
    if block <= 0:
        raise ValueError("block must be positive.")
    if side % block != 0:
        raise ValueError("block must divide the grid side length.")

    blocks_per_side = side // block
    sums: Dict[Tuple[int, int], float] = defaultdict(float)

    for (x, y), v in zip(path, values, strict=True):
        bx = x // block
        by = y // block
        sums[(bx, by)] += float(v)

    denom = float(block * block)
    avgs: List[float] = []
    for by in range(blocks_per_side):
        for bx in range(blocks_per_side):
            avgs.append(sums[(bx, by)] / denom)
    return _mean(avgs), _var_pop(avgs)


def _block_stats_reflected_y(
    path: List[Point],
    values: List[float],
    *,
    n_bits: int,
    block: int,
) -> Tuple[float, float]:
    """
    Same as _block_stats_from_path but with y-reflection pullback on the grid.
    """
    side = 1 << n_bits
    L = side - 1
    if len(path) != len(values):
        raise ValueError("path and values must have the same length.")
    if block <= 0:
        raise ValueError("block must be positive.")
    if side % block != 0:
        raise ValueError("block must divide the grid side length.")

    blocks_per_side = side // block
    sums: Dict[Tuple[int, int], float] = defaultdict(float)

    for (x, y), v in zip(path, values, strict=True):
        x2, y2 = hil.reflect_y(L, (x, y))
        bx = x2 // block
        by = y2 // block
        sums[(bx, by)] += float(v)

    denom = float(block * block)
    avgs: List[float] = []
    for by in range(blocks_per_side):
        for bx in range(blocks_per_side):
            avgs.append(sums[(bx, by)] / denom)
    return _mean(avgs), _var_pop(avgs)


def main() -> None:
    n_list = [3, 4, 5, 6, 7, 8]
    rows: List[str] = []

    # Columns:
    # n, m, block,
    # |X_m|, |cyc|, |bdry|,
    # q=|w|_1: (mu,var),
    # q=V_m(w): (mu,var),
    # q=D_pi(w): (mu,var),
    # q=log g_m(w): (mu,var).
    for n_bits in n_list:
        m = 2 * n_bits
        side = 1 << n_bits
        N = 1 << (2 * n_bits)
        if N != (1 << m):
            raise AssertionError("Balanced coupling mismatch: expected 4^n == 2^m.")

        # Fixed 4x4 coarse grid at every n (block size depends on n).
        block = 1 << (n_bits - 2)

        path = hil.hilbert_curve(n_bits)
        if len(path) != N:
            raise AssertionError("Unexpected Hilbert path length.")

        outs = cached_foldm_outputs(m)
        if len(outs) != N:
            raise AssertionError("Unexpected Fold_m outputs length.")

        Xm = sorted(set(outs))
        cyc, bdry = split_cyc_bdry(Xm)

        gm = cached_degeneracy_map(m)

        # Scalars at microstate sites (aligned with k index / Hilbert path index).
        q_weight: List[float] = []
        q_value: List[float] = []
        q_dpi: List[float] = []
        q_logg: List[float] = []

        # Fibonacci weights for V_m(w): [F2..F_{m+1}] = [1,2,3,5,...].
        weights: List[int] = [1, 2]
        while len(weights) < m:
            weights.append(weights[-1] + weights[-2])

        for w in outs:
            g = gm[w]
            q_weight.append(float(w.count("1")))
            q_value.append(float(sum((1 if w[i] == "1" else 0) * weights[i] for i in range(m))))
            q_dpi.append(1.0 if (w[0] == "1" and w[-1] == "1") else 0.0)
            q_logg.append(math.log(float(g)))

        def stats(q: List[float]) -> Tuple[float, float]:
            mu, var = _block_stats_from_path(path, q, n_bits=n_bits, block=block)
            mu_r, var_r = _block_stats_reflected_y(path, q, n_bits=n_bits, block=block)
            if abs(mu - mu_r) > 1e-12 or abs(var - var_r) > 1e-12:
                raise AssertionError("Expected reflection-invariant coarse-grained stats.")
            return mu, var

        mu_w, var_w = stats(q_weight)
        mu_V, var_V = stats(q_value)
        mu_dpi, var_dpi = stats(q_dpi)
        mu_logg, var_logg = stats(q_logg)

        rows.append(
            f"{n_bits} & {m} & {block} & {len(Xm)} & {len(cyc)} & {len(bdry)}"
            f" & {_fmt(mu_w)} & {_fmt(var_w)}"
            f" & {_fmt(mu_V)} & {_fmt(var_V)}"
            f" & {_fmt(mu_dpi)} & {_fmt(var_dpi)}"
            f" & {_fmt(mu_logg)} & {_fmt(var_logg)} \\\\"
        )

    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_flow_balanced_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_flow_balanced_rows.tex")


if __name__ == "__main__":
    main()

