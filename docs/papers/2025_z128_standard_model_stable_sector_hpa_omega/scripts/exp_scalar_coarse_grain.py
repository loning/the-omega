# -*- coding: utf-8 -*-
"""
Reproducible experiment: coarse-grained protocol scalars on the n=3 Hilbert grid.

This script demonstrates a minimal parity contrast at finite resolution:
  - the Hilbert chirality index chi_H flips sign under a spatial reflection;
  - block-averaged (coarse-grained) scalar observables built from intrinsic stable-type
    functionals are parity-even: their coarse statistics are invariant under reflection
    up to pullback on the grid.

Outputs:
  - sections/generated/scalar_coarse_grain_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, Iterable, Tuple

import exp_fold6_stats as fold
import exp_hilbert_chirality_index as hil
from common_paths import generated_dir
from common_tex import write_lines


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


def _block_stats(grid: Dict[Point, float], *, n_bits: int, block: int) -> tuple[float, float]:
    """Return (mean, population-variance) of block averages over an (2^n_bits)x(2^n_bits) grid."""
    if block <= 0:
        raise ValueError("block must be positive.")
    side = 1 << n_bits
    if side % block != 0:
        raise ValueError("block must divide the grid side length.")

    block_avgs: list[float] = []
    for y0 in range(0, side, block):
        for x0 in range(0, side, block):
            s = 0.0
            for dy in range(block):
                for dx in range(block):
                    s += float(grid[(x0 + dx, y0 + dy)])
            block_avgs.append(s / float(block * block))
    return _mean(block_avgs), _var_pop(block_avgs)


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    n_bits = 3
    N = 1 << (2 * n_bits)  # 4^n
    side = 1 << n_bits
    L = side - 1
    block = 2

    path = hil.hilbert_curve(n_bits)
    if len(path) != N:
        raise AssertionError("Unexpected Hilbert path length.")

    chi = hil.chirality_index(path)
    path_ref = [hil.reflect_y(L, p) for p in path]
    chi_ref = hil.chirality_index(path_ref)
    if chi_ref != -chi:
        raise AssertionError("Expected reflection to flip chi sign.")

    # Precompute Fold_6 outputs and preimage sizes g(w).
    preimage: dict[str, list[int]] = defaultdict(list)
    words_by_index: list[str] = []
    for k in range(N):
        w = fold.fold6(k)
        words_by_index.append(w)
        preimage[w].append(k)
    g_map = {w: len(ns) for w, ns in preimage.items()}

    def q_weight(w: str) -> float:
        return float(w.count("1"))

    def q_value(w: str) -> float:
        return float(fold.zeckendorf_value_of_word(w))

    def q_dpi(w: str) -> float:
        # pi-channel boundary predicate at m=6: endpoints both 1
        return 1.0 if (w[0] == "1" and w[-1] == "1") else 0.0

    # A small, intrinsic scalar family (Definition~{def:coarse_grained_scalar}).
    qs: list[tuple[str, Callable[[str], float]]] = [
        (r"$\overline{|w|_1}^{(2\times 2)}$", q_weight),
        (r"$\overline{V(w)}^{(2\times 2)}$", q_value),
        (r"$\overline{D_\pi(w)}^{(2\times 2)}$", q_dpi),
    ]

    rows: list[str] = []
    rows.append(r"$\chi_H$ (chirality index) & $" + str(chi) + r"$ & $" + str(chi_ref) + r"$ \\")

    for label, q in qs:
        grid: dict[Point, float] = {}
        grid_ref: dict[Point, float] = {}
        for k, (x, y) in enumerate(path):
            w = words_by_index[k]
            # Sanity: confirm g(w) is well-defined for this stable type.
            _ = g_map[w]
            val = q(w)
            grid[(x, y)] = val
            grid_ref[hil.reflect_y(L, (x, y))] = val

        mu, var = _block_stats(grid, n_bits=n_bits, block=block)
        mu_r, var_r = _block_stats(grid_ref, n_bits=n_bits, block=block)

        if abs(mu - mu_r) > 1e-12 or abs(var - var_r) > 1e-12:
            raise AssertionError("Expected coarse-grained scalar stats to be reflection-invariant.")

        rows.append(
            f"{label} & $\\mu={_fmt(mu)},\\ \\mathrm{{Var}}={_fmt(var)}$ & "
            f"$\\mu={_fmt(mu_r)},\\ \\mathrm{{Var}}={_fmt(var_r)}$ \\\\"
        )

    rows.append(r"\bottomrule")
    out = generated_dir() / "scalar_coarse_grain_rows.tex"
    write_lines(out, rows)
    print(f"Wrote {out.relative_to(out.parents[2])}")


if __name__ == "__main__":
    main()


