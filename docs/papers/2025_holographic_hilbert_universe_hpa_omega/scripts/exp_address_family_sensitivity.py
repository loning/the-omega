# -*- coding: utf-8 -*-
"""
Address-family sensitivity on a 2D screen lattice.

For a finite-resolution address map A_n : {0..2^(2n)-1} -> {0..2^n-1}^2,
define the neighbor separation on screen edges:
  Δ_A(x,y) = |A_n^{-1}(x) - A_n^{-1}(y)|
and the local scan-chain overhead proxy:
  kappa_tilde(x) = max_{y~x} Δ_A(x,y).

This script compares Hilbert vs Morton (Z-order) for orders n=1..8 and writes
LaTeX table rows into sections/generated/.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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


def build_index_map(order: int, d2xy) -> list[list[int]]:
    m = 1 << order
    total = m * m
    idx = [[0] * m for _ in range(m)]
    for d in range(total):
        x, y = d2xy(order, d)
        idx[x][y] = d
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


def local_kappa_proxy(idx: list[list[int]]) -> list[int]:
    m = len(idx)
    prox: list[int] = []
    for x in range(m):
        for y in range(m):
            best = 0
            if x > 0:
                best = max(best, abs(idx[x][y] - idx[x - 1][y]))
            if x + 1 < m:
                best = max(best, abs(idx[x][y] - idx[x + 1][y]))
            if y > 0:
                best = max(best, abs(idx[x][y] - idx[x][y - 1]))
            if y + 1 < m:
                best = max(best, abs(idx[x][y] - idx[x][y + 1]))
            prox.append(best)
    return prox


def write_rows(rows: list[str], filename: str) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / filename).write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    maps = [
        ("Hilbert", hilbert_d2xy),
        ("Z-order", morton_d2xy),
    ]

    edge_rows: list[str] = []
    proxy_rows: list[str] = []

    for order in range(1, 9):
        for name, d2xy in maps:
            idx = build_index_map(order, d2xy)

            deltas = neighbor_separations(idx)
            s_edge = stats_int(deltas)
            edge_rows.append(
                f"{order} & {name} & {s_edge.mean:.2f} & {s_edge.p50} & {s_edge.p90} & {s_edge.p99} & {s_edge.mx} \\\\"
            )

            prox = local_kappa_proxy(idx)
            s_prox = stats_int(prox)
            proxy_rows.append(
                f"{order} & {name} & {s_prox.mean:.2f} & {s_prox.p50} & {s_prox.p90} & {s_prox.p99} & {s_prox.mx} \\\\"
            )

        print(f"order={order}: ok")

    write_rows(edge_rows, "address_neighbor_separation_rows.tex")
    write_rows(proxy_rows, "address_kappa_proxy_rows.tex")
    print("Wrote sections/generated/address_neighbor_separation_rows.tex")
    print("Wrote sections/generated/address_kappa_proxy_rows.tex")


if __name__ == "__main__":
    main()


