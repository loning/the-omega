# -*- coding: utf-8 -*-
"""
Covariant protocol RG operator: spectral gap / internal mixing diagnostic (anchor).

We build the covariant anchor operator F_3^∇ on the 4x4 block quotient with an
internal slot space of dimension r_8=max fiber degeneracy at m=8 (balanced coupling
for the transport scale n+1=4), using the deterministic Fold_m-induced edge connection.

We report:
  - max row-sum error from 1 (stochasticity sanity),
  - |lambda_2| on the global mean-zero subspace (deflating the trivial eigenvalue 1),
  - |lambda_int| on the per-block internal mean-zero subspace (kills the trivial internal rep),
  - corresponding gaps 1-|lambda|.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_operator_covariant_spectral_gap_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from typing import List

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import build_F_covariant_anchor, row_sum_stats, second_eigenvalue_abs_general, second_eigenvalue_abs_internal


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    rows: List[str] = []
    # Columns: n, m(transport), r_m, dim, row_err, |lam2|, gap, |lam_int|, gap_int
    for n in (3, 4):
        F, r = build_F_covariant_anchor(n)
        max_err, _rmin, _rmax = row_sum_stats(F)
        lam2 = second_eigenvalue_abs_general(F, iters=2000)
        gap = 1.0 - float(abs(lam2))
        lam_int = second_eigenvalue_abs_internal(F, r, iters=2000)
        gap_int = 1.0 - float(abs(lam_int))
        rows.append(
            f"{n} & {2*(n+1)} & {r} & {16*r} & {max_err:.3e} & {_fmt(lam2)} & {_fmt(gap)} & {_fmt(lam_int)} & {_fmt(gap_int)} \\\\"
        )
    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_operator_covariant_spectral_gap_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_operator_covariant_spectral_gap_rows.tex")


if __name__ == "__main__":
    main()

