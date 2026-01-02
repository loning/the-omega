# -*- coding: utf-8 -*-
"""
Reproducible experiment: Hilbert curve chirality index.

This script reproduces:
  - chi(path) for the standard Hilbert d->(x,y) algorithm at order n_bits=3
  - chi(reversed path) flips sign (traversal reversal)
  - chi(reflected path) flips sign (parity / reflection)

It writes a small LaTeX summary fragment into sections/generated/.
Only the Python standard library is used.
"""

from __future__ import annotations

from pathlib import Path

from common_cache import CACHE_VERSION, cache_path, load_or_compute


def rot(s: int, x: int, y: int, rx: int, ry: int) -> tuple[int, int]:
    if ry == 0:
        if rx == 1:
            x = s - 1 - x
            y = s - 1 - y
        x, y = y, x
    return x, y


def d2xy(n_bits: int, d: int) -> tuple[int, int]:
    n = 1 << n_bits
    x = y = 0
    t = d
    s = 1
    while s < n:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        x, y = rot(s, x, y, rx, ry)
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2
    return x, y


def hilbert_curve(n_bits: int) -> list[tuple[int, int]]:
    key = cache_path(f"hilbert_curve_n{n_bits}_v{CACHE_VERSION}.pkl")

    def compute() -> list[tuple[int, int]]:
        N = 1 << (2 * n_bits)  # 4^n
        return [d2xy(n_bits, d) for d in range(N)]

    return load_or_compute(key, compute)


def chirality_index(path: list[tuple[int, int]]) -> int:
    total = 0
    for i in range(1, len(path) - 1):
        x0, y0 = path[i - 1]
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        v1 = (x1 - x0, y1 - y0)
        v2 = (x2 - x1, y2 - y1)
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        if cross > 0:
            total += 1
        elif cross < 0:
            total -= 1
    return total


def reflect_y(L: int, p: tuple[int, int]) -> tuple[int, int]:
    x, y = p
    return (x, L - y)


def write_tex_summary(n_bits: int, chi: int, chi_rev: int, chi_ref: int) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    n = n_bits
    text = (
        "\\noindent "
        f"For Hilbert order $n={n}$: "
        f"$\\chi(\\text{{path}})={chi}$, "
        f"$\\chi(\\text{{reversed path}})={chi_rev}$, and "
        f"$\\chi(\\text{{reflected path}})={chi_ref}$."
    )
    (out_dir / "hilbert_chi_summary.tex").write_text(text + "\n", encoding="utf-8")


def main() -> None:
    n_bits = 3
    path = hilbert_curve(n_bits)
    L = (1 << n_bits) - 1

    chi = chirality_index(path)
    chi_rev = chirality_index(list(reversed(path)))
    chi_ref = chirality_index([reflect_y(L, p) for p in path])

    print("Hilbert order n_bits =", n_bits, ", points =", len(path))
    print("chi(path) =", chi)
    print("chi(reversed path) =", chi_rev)
    print("chi(reflected path) =", chi_ref)

    if chi_rev != -chi:
        raise AssertionError("Expected traversal reversal to flip chi sign.")
    if chi_ref != -chi:
        raise AssertionError("Expected reflection to flip chi sign.")

    write_tex_summary(n_bits=n_bits, chi=chi, chi_rev=chi_rev, chi_ref=chi_ref)
    print("Wrote sections/generated/hilbert_chi_summary.tex")


if __name__ == "__main__":
    main()


