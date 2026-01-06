# -*- coding: utf-8 -*-
"""
Gauge-factor complexity-label sensitivity sweep (bounded audit).

This script supports Appendix "Gauge-factor complexity-label sensitivity".
It enumerates a bounded list of compact, non-abelian, simple Lie groups (via Lie algebras)
and applies CAP-style lexicographic minimization under several intrinsic complexity labels.

Outputs:
  - sections/generated/gauge_complexity_sensitivity_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Iterable, Tuple

from common_paths import generated_dir
from common_tex import write_lines


@dataclass(frozen=True)
class SimpleFactor:
    name: str
    dim: int
    rank: int
    mfd: int  # minimal faithful complex representation dimension (up to finite quotients)
    iso_id: str  # isomorphism-class id (Lie algebra)


def _a_n(n: int) -> SimpleFactor:
    # A_n: su(n+1)
    N = n + 1
    dim = N * N - 1
    rank = n
    mfd = N
    return SimpleFactor(name=f"SU({N})", dim=dim, rank=rank, mfd=mfd, iso_id=f"A{n}")


def _b_n(n: int) -> SimpleFactor:
    # B_n: so(2n+1), n>=3 here to avoid low-rank isomorphisms (B1~A1, B2~C2).
    N = 2 * n + 1
    dim = n * (2 * n + 1)
    rank = n
    mfd = N
    return SimpleFactor(name=f"SO({N})", dim=dim, rank=rank, mfd=mfd, iso_id=f"B{n}")


def _c_n(n: int) -> SimpleFactor:
    # C_n: sp(n), n>=2 here to avoid C1~A1.
    dim = n * (2 * n + 1)
    rank = n
    mfd = 2 * n
    return SimpleFactor(name=f"Sp({n})", dim=dim, rank=rank, mfd=mfd, iso_id=f"C{n}")


def _d_n(n: int) -> SimpleFactor:
    # D_n: so(2n), n>=4 here to avoid D3~A3 and D2 not simple.
    N = 2 * n
    dim = n * (2 * n - 1)
    rank = n
    mfd = N
    return SimpleFactor(name=f"SO({N})", dim=dim, rank=rank, mfd=mfd, iso_id=f"D{n}")


def _exceptionals() -> list[SimpleFactor]:
    # Minimal faithful rep dims are standard (up to finite quotients).
    return [
        SimpleFactor(name="G2", dim=14, rank=2, mfd=7, iso_id="G2"),
        SimpleFactor(name="F4", dim=52, rank=4, mfd=26, iso_id="F4"),
        SimpleFactor(name="E6", dim=78, rank=6, mfd=27, iso_id="E6"),
        SimpleFactor(name="E7", dim=133, rank=7, mfd=56, iso_id="E7"),
        SimpleFactor(name="E8", dim=248, rank=8, mfd=248, iso_id="E8"),
    ]


def enumerate_factors(max_dim: int) -> list[SimpleFactor]:
    out: list[SimpleFactor] = []

    # A_n for n>=1
    n = 1
    while True:
        g = _a_n(n)
        if g.dim > max_dim:
            break
        out.append(g)
        n += 1

    # C_n for n>=2
    n = 2
    while True:
        g = _c_n(n)
        if g.dim > max_dim:
            break
        out.append(g)
        n += 1

    # B_n for n>=3
    n = 3
    while True:
        g = _b_n(n)
        if g.dim > max_dim:
            break
        out.append(g)
        n += 1

    # D_n for n>=4
    n = 4
    while True:
        g = _d_n(n)
        if g.dim > max_dim:
            break
        out.append(g)
        n += 1

    for g in _exceptionals():
        if g.dim <= max_dim:
            out.append(g)

    # Ensure unique iso classes in this list.
    seen: set[str] = set()
    uniq: list[SimpleFactor] = []
    for g in sorted(out, key=lambda x: (x.dim, x.rank, x.name)):
        if g.iso_id in seen:
            continue
        seen.add(g.iso_id)
        uniq.append(g)
    return uniq


def select_min_pair(
    factors: Iterable[SimpleFactor],
    label: Callable[[SimpleFactor], int],
) -> Tuple[SimpleFactor, SimpleFactor, Tuple[int, int]]:
    """
    Select lexicographically minimal pair (G2,G3) with non-isomorphic factors.
    Deterministic tie-break refines by (dim, rank, name).
    """

    def factor_sort_key(g: SimpleFactor) -> tuple[int, int, int, str]:
        return (label(g), g.dim, g.rank, g.name)

    best_key: tuple[tuple[int, int, int, str], tuple[int, int, int, str], str, str] | None = None
    best_pair: tuple[SimpleFactor, SimpleFactor] | None = None

    fac_list = list(factors)
    for a, b in combinations(fac_list, 2):
        if a.iso_id == b.iso_id:
            continue
        ga, gb = sorted([a, b], key=factor_sort_key)
        key = (factor_sort_key(ga), factor_sort_key(gb), ga.name, gb.name)
        if best_key is None or key < best_key:
            best_key = key
            best_pair = (ga, gb)

    if best_pair is None:
        raise RuntimeError("No admissible pair found.")

    ga, gb = best_pair
    return ga, gb, (label(ga), label(gb))


def main() -> None:
    max_dim = 80
    factors = enumerate_factors(max_dim=max_dim)
    if not factors:
        raise RuntimeError("Empty factor list.")

    metrics: list[tuple[str, Callable[[SimpleFactor], int], str]] = [
        (r"$\dim(\mathfrak{g})$", lambda g: g.dim, "lex by (dim, rank, name)"),
        (r"$\mathrm{rank}(\mathfrak{g})$", lambda g: g.rank, "lex by (rank, dim, name)"),
        (r"$\dim(\mathfrak{g})+\mathrm{rank}(\mathfrak{g})$", lambda g: g.dim + g.rank, "lex by (dim+rank, dim, name)"),
        (r"$d_{\min}$", lambda g: g.mfd, r"lex by (d\_min, dim, name)"),
    ]

    rows: list[str] = []
    for label_tex, fn, note in metrics:
        g2, g3, key = select_min_pair(factors, label=fn)
        rows.append(
            f"{label_tex} & "
            + f"${g2.name},\\,{g3.name}$"
            + " & "
            + f"$({key[0]},{key[1]})$"
            + " & "
            + note
            + r" \\"
        )

    rows.append(r"\bottomrule")

    out_path = generated_dir() / "gauge_complexity_sensitivity_rows.tex"
    write_lines(out_path, rows)
    print(f"Wrote {out_path} (max_dim={max_dim}, n_factors={len(factors)})")


if __name__ == "__main__":
    main()


