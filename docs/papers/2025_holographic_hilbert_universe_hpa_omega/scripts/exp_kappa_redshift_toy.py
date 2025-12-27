# -*- coding: utf-8 -*-
"""
Toy redshift from a computed overhead landscape on a scan chain.

We build a position-dependent overhead proxy kappa(x) on the 2D screen lattice
using a fixed address map A_n and a scan-chain placement pi(x)=A_n^{-1}(x):

  kappa(x) := max_{y~x} |A_n^{-1}(x) - A_n^{-1}(y)|

Interpreting one local "clock cycle" at x as taking kappa(x) global ticks,
the relational time scaling predicts:
  d tau_loc = (kappa0 / kappa(x)) dt
and the redshift ratio between x1 and x2 is kappa(x2)/kappa(x1).

This script demonstrates the ratio numerically by counting completed cycles
over a long horizon t_max and writes LaTeX rows into sections/generated/.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def _rot(s: int, x: int, y: int, rx: int, ry: int) -> tuple[int, int]:
    if ry == 0:
        if rx == 1:
            x = s - 1 - x
            y = s - 1 - y
        x, y = y, x
    return x, y


def hilbert_d2xy(order: int, d: int) -> tuple[int, int]:
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


def kappa_proxy_field(idx: list[list[int]]) -> tuple[list[int], tuple[int, int], int, tuple[int, int], int]:
    m = len(idx)
    vals: list[int] = []
    min_xy = (0, 0)
    max_xy = (0, 0)
    min_k = 10**18
    max_k = -1

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

            vals.append(best)
            if best < min_k:
                min_k = best
                min_xy = (x, y)
            if best > max_k:
                max_k = best
                max_xy = (x, y)

    return vals, min_xy, int(min_k), max_xy, int(max_k)


def find_any_coordinate_with_kappa(idx: list[list[int]], target_k: int) -> tuple[int, int] | None:
    m = len(idx)
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
            if best == target_k:
                return (x, y)
    return None


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
class PairRow:
    x1: int
    y1: int
    k1: int
    x2: int
    y2: int
    k2: int
    pred: float
    meas: float


def cycles(t_max: int, kappa: int) -> int:
    if kappa <= 0:
        raise ValueError("kappa must be positive.")
    return t_max // kappa


def write_rows(rows: list[str], filename: str) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / filename).write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    order = 8
    t_max = 200_000_000

    maps = [
        ("Hilbert", hilbert_d2xy),
        ("Z-order", morton_d2xy),
    ]

    rows: list[str] = []

    for name, d2xy in maps:
        idx = build_index_map(order, d2xy)
        vals, min_xy, min_k, max_xy, max_k = kappa_proxy_field(idx)

        vals_sorted = sorted(vals)
        med_k = percentile(vals_sorted, 0.50)
        med_xy = find_any_coordinate_with_kappa(idx, med_k)
        if med_xy is None:
            med_xy = (0, 0)

        points = [
            ("min", min_xy, min_k),
            ("median", med_xy, med_k),
            ("max", max_xy, max_k),
        ]

        pairs: list[PairRow] = []
        for (tag1, (x1, y1), k1), (tag2, (x2, y2), k2) in [
            (points[0], points[1]),
            (points[0], points[2]),
            (points[1], points[2]),
        ]:
            pred = float(k2) / float(k1)
            c1 = cycles(t_max, k1)
            c2 = cycles(t_max, k2)
            meas = float(c1) / float(c2) if c2 != 0 else float("inf")
            pairs.append(PairRow(x1=x1, y1=y1, k1=k1, x2=x2, y2=y2, k2=k2, pred=pred, meas=meas))

        for p in pairs:
            rows.append(
                f"{order} & {name} & ({p.x1},{p.y1}) & {p.k1} & ({p.x2},{p.y2}) & {p.k2} & {p.pred:.6f} & {p.meas:.6f} \\\\"
            )

        print(f"{name}: min_k={min_k} at {min_xy}, median_k={med_k} at {med_xy}, max_k={max_k} at {max_xy}")

    write_rows(rows, "kappa_redshift_toy_rows.tex")
    print("Wrote sections/generated/kappa_redshift_toy_rows.tex")


if __name__ == "__main__":
    main()


