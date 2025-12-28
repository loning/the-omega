# -*- coding: utf-8 -*-
"""
Address-family sensitivity on a 2D screen lattice.

For a finite-resolution address map A_n : {0..2^(2n)-1} -> {0..2^n-1}^2,
define the neighbor separation on screen edges:
  Delta_A(x,y) = |A_n^{-1}(x) - A_n^{-1}(y)|
and the local scan-chain overhead proxy:
  kappa_tilde(x) = max_{y~x} Delta_A(x,y).

This script compares Hilbert vs Morton (Z-order) plus a shuffled baseline for
orders n=1..8 (2D), and writes LaTeX table rows into sections/generated/.

It also reports:
  (i) sensitivity to the neighborhood model (Manhattan vs Chebyshev neighbors),
  (ii) a simple finite-size trend fit for the growth of high quantiles.

As an additional robustness check, it also computes the same proxy for a 3D
screen using Morton vs shuffled baselines (orders n=1..5).
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import random
from typing import Callable


def _rot(s: int, x: int, y: int, rx: int, ry: int) -> tuple[int, int]:
    """Rotate/flip a quadrant (standard Hilbert helper)."""
    if ry == 0:
        if rx == 1:
            x = s - 1 - x
            y = s - 1 - y
        x, y = y, x
    return x, y


def hilbert_d2xy(order: int, d: int) -> tuple[int, int]:
    """
    2D Hilbert mapping: d in [0, 2^(2*order)-1] -> (x,y) in [0, 2^order-1]^2.
    """
    n = 1 << order
    x = 0
    y = 0
    t = int(d)
    s = 1
    while s < n:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        x, y = _rot(s, x, y, rx, ry)
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2
    return x, y


def morton_d2xy(order: int, d: int) -> tuple[int, int]:
    """
    2D Morton / Z-order mapping via bit de-interleaving.
    """
    x = 0
    y = 0
    for i in range(order):
        x |= ((d >> (2 * i)) & 1) << i
        y |= ((d >> (2 * i + 1)) & 1) << i
    return x, y


def morton_d2xyz(order: int, d: int) -> tuple[int, int, int]:
    """
    3D Morton / Z-order mapping via bit de-interleaving.
    """
    x = 0
    y = 0
    z = 0
    for i in range(order):
        x |= ((d >> (3 * i)) & 1) << i
        y |= ((d >> (3 * i + 1)) & 1) << i
        z |= ((d >> (3 * i + 2)) & 1) << i
    return x, y, z


def build_index_map(order: int, d2xy) -> list[list[int]]:
    m = 1 << order
    total = m * m
    idx = [[0] * m for _ in range(m)]
    for d in range(total):
        x, y = d2xy(order, d)
        idx[x][y] = d
    return idx


def build_index_map_shuffled(order: int, seed: int) -> list[list[int]]:
    """
    A deterministic shuffled baseline: assign indices to uniformly shuffled coordinates.
    """
    m = 1 << order
    total = m * m
    coords = [(x, y) for x in range(m) for y in range(m)]
    rng = random.Random(seed)
    rng.shuffle(coords)
    idx = [[0] * m for _ in range(m)]
    for d in range(total):
        x, y = coords[d]
        idx[x][y] = d
    return idx


def build_index_map_3d(order: int, d2xyz) -> list[int]:
    m = 1 << order
    total = m * m * m
    idx = [0] * total
    for d in range(total):
        x, y, z = d2xyz(order, d)
        idx[(x * m + y) * m + z] = d
    return idx


def build_index_map_shuffled_3d(order: int, seed: int) -> list[int]:
    m = 1 << order
    total = m * m * m
    coords = [(x, y, z) for x in range(m) for y in range(m) for z in range(m)]
    rng = random.Random(seed)
    rng.shuffle(coords)
    idx = [0] * total
    for d in range(total):
        x, y, z = coords[d]
        idx[(x * m + y) * m + z] = d
    return idx


def percentile(sorted_values: list[int], p: float) -> int:
    if not sorted_values:
        raise ValueError("Empty sample.")
    if p <= 0.0:
        return sorted_values[0]
    if p >= 1.0:
        return sorted_values[-1]
    i = int(p * (len(sorted_values) - 1))
    return sorted_values[i]


@dataclass(frozen=True)
class Stats:
    mean: float
    p50: int
    p90: int
    p99: int
    mx: int


def stats_int(values: list[int]) -> Stats:
    if not values:
        raise ValueError("Empty sample.")
    values_sorted = sorted(values)
    n = len(values_sorted)
    mean = sum(values_sorted) / float(n)
    return Stats(
        mean=mean,
        p50=percentile(values_sorted, 0.50),
        p90=percentile(values_sorted, 0.90),
        p99=percentile(values_sorted, 0.99),
        mx=values_sorted[-1],
    )


def neighbor_separations(idx: list[list[int]]) -> list[int]:
    m = len(idx)
    deltas: list[int] = []
    for x in range(m):
        for y in range(m):
            if x + 1 < m:
                deltas.append(abs(idx[x][y] - idx[x + 1][y]))
            if y + 1 < m:
                deltas.append(abs(idx[x][y] - idx[x][y + 1]))
    return deltas


@dataclass(frozen=True)
class NeighborModel:
    name: str
    offsets: tuple[tuple[int, int], ...]


MANHATTAN_1 = NeighborModel(name="Manhattan", offsets=((1, 0), (-1, 0), (0, 1), (0, -1)))
CHEBYSHEV_1 = NeighborModel(
    name="Chebyshev",
    offsets=(
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    ),
)


def local_kappa_proxy(idx: list[list[int]], neighbors: NeighborModel) -> list[int]:
    m = len(idx)
    prox: list[int] = []
    for x in range(m):
        for y in range(m):
            best = 0
            for dx, dy in neighbors.offsets:
                xx = x + dx
                yy = y + dy
                if 0 <= xx < m and 0 <= yy < m:
                    best = max(best, abs(idx[x][y] - idx[xx][yy]))
            prox.append(best)
    return prox


def local_kappa_proxy_3d(idx: list[int], m: int) -> list[int]:
    """
    3D Manhattan (6-neighbor) local proxy field on an m x m x m grid.
    """
    prox: list[int] = []
    for x in range(m):
        for y in range(m):
            for z in range(m):
                p = (x * m + y) * m + z
                base = idx[p]
                best = 0
                if x > 0:
                    best = max(best, abs(base - idx[((x - 1) * m + y) * m + z]))
                if x + 1 < m:
                    best = max(best, abs(base - idx[((x + 1) * m + y) * m + z]))
                if y > 0:
                    best = max(best, abs(base - idx[(x * m + (y - 1)) * m + z]))
                if y + 1 < m:
                    best = max(best, abs(base - idx[(x * m + (y + 1)) * m + z]))
                if z > 0:
                    best = max(best, abs(base - idx[(x * m + y) * m + (z - 1)]))
                if z + 1 < m:
                    best = max(best, abs(base - idx[(x * m + y) * m + (z + 1)]))
                prox.append(best)
    return prox


def linear_fit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """
    Ordinary least squares fit for y = a + b x. Returns (b, a, R^2).
    """
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("Need at least 2 points for a fit.")
    n = float(len(xs))
    x_bar = sum(xs) / n
    y_bar = sum(ys) / n
    sxx = sum((x - x_bar) ** 2 for x in xs)
    if sxx == 0.0:
        raise ValueError("Degenerate x values.")
    sxy = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = y_bar - b * x_bar
    ss_tot = sum((y - y_bar) ** 2 for y in ys)
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0.0 else 1.0
    return b, a, r2


@dataclass(frozen=True)
class AddressMap:
    name: str
    build_idx: Callable[[int], list[list[int]]]


def write_rows(rows: list[str], filename: str) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / filename).write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    maps = [
        AddressMap(name="Hilbert", build_idx=lambda order: build_index_map(order, hilbert_d2xy)),
        AddressMap(name="Z-order", build_idx=lambda order: build_index_map(order, morton_d2xy)),
        AddressMap(name="Shuffled", build_idx=lambda order: build_index_map_shuffled(order, seed=123456 + order)),
    ]

    edge_rows: list[str] = []
    proxy_rows: list[str] = []
    fit_rows: list[str] = []
    neighbor_model_rows: list[str] = []

    # Accumulate per-map proxy stats across orders for a simple scaling fit.
    by_map: dict[str, list[tuple[int, Stats]]] = {m.name: [] for m in maps}

    for order in range(1, 9):
        for amap in maps:
            idx = amap.build_idx(order)

            deltas = neighbor_separations(idx)
            s_edge = stats_int(deltas)
            edge_rows.append(
                f"{order} & {amap.name} & {s_edge.mean:.2f} & {s_edge.p50} & {s_edge.p90} & {s_edge.p99} & {s_edge.mx} \\\\"
            )

            prox = local_kappa_proxy(idx, MANHATTAN_1)
            s_prox = stats_int(prox)
            by_map[amap.name].append((order, s_prox))
            proxy_rows.append(
                f"{order} & {amap.name} & {s_prox.mean:.2f} & {s_prox.p50} & {s_prox.p90} & {s_prox.p99} & {s_prox.mx} \\\\"
            )

        print(f"order={order}: ok")

    # Neighborhood-model sensitivity at a fixed resolution.
    fixed_order = 8
    for amap in maps:
        idx = amap.build_idx(fixed_order)
        s_m = stats_int(local_kappa_proxy(idx, MANHATTAN_1))
        s_c = stats_int(local_kappa_proxy(idx, CHEBYSHEV_1))
        ratio_p99 = (float(s_c.p99) / float(s_m.p99)) if s_m.p99 > 0 else float("inf")
        ratio_max = (float(s_c.mx) / float(s_m.mx)) if s_m.mx > 0 else float("inf")
        neighbor_model_rows.append(
            f"{amap.name} & {s_m.p99} & {s_c.p99} & {ratio_p99:.3f} & {s_m.mx} & {s_c.mx} & {ratio_max:.3f} \\\\"
        )

    # Simple finite-size trend fits for high quantiles of the Manhattan proxy.
    for amap in maps:
        data = by_map[amap.name]
        xs = [float(order) for order, _ in data]
        ys_p99 = [math.log2(float(s.p99)) for _, s in data]
        ys_max = [math.log2(float(s.mx)) for _, s in data]
        b_p99, _a_p99, r2_p99 = linear_fit(xs, ys_p99)
        b_max, _a_max, r2_max = linear_fit(xs, ys_max)
        fit_rows.append(f"{amap.name} & {b_p99:.3f} & {r2_p99:.3f} & {b_max:.3f} & {r2_max:.3f} \\\\")

    write_rows(edge_rows, "address_neighbor_separation_rows.tex")
    write_rows(proxy_rows, "address_kappa_proxy_rows.tex")
    write_rows(neighbor_model_rows, "address_neighbor_model_sensitivity_rows.tex")
    write_rows(fit_rows, "address_kappa_proxy_fit_rows.tex")
    # 3D robustness rows.
    proxy_3d_rows: list[str] = []
    for order in range(1, 6):
        m = 1 << order
        for name, idx3 in [
            ("Z-order", build_index_map_3d(order, morton_d2xyz)),
            ("Shuffled", build_index_map_shuffled_3d(order, seed=654321 + order)),
        ]:
            prox3 = local_kappa_proxy_3d(idx3, m=m)
            s3 = stats_int(prox3)
            proxy_3d_rows.append(
                f"{order} & {name} & {s3.mean:.2f} & {s3.p50} & {s3.p90} & {s3.p99} & {s3.mx} \\\\"
            )
        print(f"order={order} (3D): ok")
    write_rows(proxy_3d_rows, "address_kappa_proxy_3d_rows.tex")
    print("Wrote sections/generated/address_neighbor_separation_rows.tex")
    print("Wrote sections/generated/address_kappa_proxy_rows.tex")
    print("Wrote sections/generated/address_neighbor_model_sensitivity_rows.tex")
    print("Wrote sections/generated/address_kappa_proxy_fit_rows.tex")
    print("Wrote sections/generated/address_kappa_proxy_3d_rows.tex")


if __name__ == "__main__":
    main()


