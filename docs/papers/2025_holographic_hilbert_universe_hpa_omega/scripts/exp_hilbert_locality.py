# -*- coding: utf-8 -*-
"""
Discrete 2D Hilbert curve addressing: index -> (x,y), and locality verification.

This script checks the one-step Manhattan locality:
  ||H_n(t+1) - H_n(t)||_1 = 1
for orders n = 1..8, and writes a small LaTeX row file into sections/generated/.
"""

from __future__ import annotations

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


def manhattan(p: tuple[int, int], q: tuple[int, int]) -> int:
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def check_order(order: int) -> tuple[int, int]:
    n = 1 << order
    total = n * n
    pts = [hilbert_d2xy(order, d) for d in range(total)]
    dists = [manhattan(pts[i], pts[i + 1]) for i in range(total - 1)]
    return min(dists), max(dists)


def write_rows(rows: list[tuple[int, int, int]]) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "hilbert_locality_rows.tex"

    lines = []
    for order, mn, mx in rows:
        lines.append(f"{order} & {mn} & {mx} \\\\")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows: list[tuple[int, int, int]] = []
    for order in range(1, 9):
        mn, mx = check_order(order)
        rows.append((order, mn, mx))
        print(f"order={order}: min_L1={mn}, max_L1={mx}")
        if mn != 1 or mx != 1:
            raise AssertionError("Hilbert one-step locality violated.")
    write_rows(rows)
    print("Wrote sections/generated/hilbert_locality_rows.tex")


if __name__ == "__main__":
    main()


