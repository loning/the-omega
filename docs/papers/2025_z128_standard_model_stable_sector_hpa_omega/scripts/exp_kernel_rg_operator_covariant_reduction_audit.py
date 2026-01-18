# -*- coding: utf-8 -*-
"""
Covariant RG operator reduction / decomposition audit (anchor).

We audit that the covariant anchor operator F_3^∇ reduces exactly to the scalar
16x16 RG operator F_3 under the trivial-representation projection (slot average).

Define:
  - E: R^16 -> R^(16*r)  (replicate into r slots per block),
  - S: R^(16*r) -> R^16  (average over r slots per block).

We verify on a deterministic test family that:
  S (F_3^∇ (E v)) = F_3 v,
and that the lifted subspace Im(E) is invariant up to numerical tolerance via:
  ||F_3^∇ (E v) - E (S F_3^∇ E v)||.

We also report the spectral contractions:
  - |lambda_2(F_3)| on the block mean-zero subspace,
  - |lambda_int(F_3^∇)| on the per-block internal mean-zero subspace.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_operator_covariant_reduction_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from typing import List

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import (
    build_F_covariant_anchor,
    build_F_matrix,
    mat_vec,
    second_eigenvalue_abs,
    second_eigenvalue_abs_internal,
)


def lift_E(v: List[float], r: int) -> List[float]:
    out: List[float] = []
    for b in range(16):
        for _ in range(r):
            out.append(float(v[b]))
    return out


def proj_S(x: List[float], r: int) -> List[float]:
    if len(x) != 16 * r:
        raise ValueError("Dimension mismatch.")
    out = [0.0] * 16
    for b in range(16):
        s = 0.0
        for j in range(r):
            s += float(x[b * r + j])
        out[b] = s / float(r)
    return out


def max_abs(v: List[float]) -> float:
    return max(abs(float(x)) for x in v) if v else 0.0


def max_abs_diff(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Dimension mismatch.")
    return max(abs(float(x) - float(y)) for x, y in zip(a, b, strict=True))


def _fmt(x: float) -> str:
    return f"{x:.3e}"


def main() -> None:
    rows: List[str] = []
    # Deterministic test vectors on R^16 (include mean-zero and non-mean-zero).
    tests: List[List[float]] = [
        [1.0] * 16,
        [float((i % 7) - 3) for i in range(16)],
        [float((i % 5) - 2) for i in range(16)],
        [0.0] * 8 + [1.0] * 8,
    ]

    # Columns: n, m=2(n+1), r, dim, reduction_err, invariance_err, |lam2_scalar|, gap_scalar, |lam_int|, gap_int
    for n in (3, 4):
        F_cov, r = build_F_covariant_anchor(n)
        F = build_F_matrix(n)

        red_err = 0.0
        inv_err = 0.0
        for v in tests:
            x = lift_E(v, r)
            y = mat_vec(F_cov, x)
            Sv = proj_S(y, r)
            Fv = mat_vec(F, v)
            red_err = max(red_err, max_abs_diff(Sv, Fv))

            # invariance of Im(E) measured by distance to its projection E S.
            ESy = lift_E(proj_S(y, r), r)
            inv_err = max(inv_err, max_abs_diff(y, ESy))

        lam2_scalar = second_eigenvalue_abs(F, iters=1600)
        gap_scalar = 1.0 - float(abs(lam2_scalar))
        lam_int = second_eigenvalue_abs_internal(F_cov, r, iters=1600)
        gap_int = 1.0 - float(abs(lam_int))

        rows.append(
            f"{n} & {2*(n+1)} & {r} & {16*r} & {_fmt(red_err)} & {_fmt(inv_err)} & {lam2_scalar:.6f} & {gap_scalar:.6f} & {lam_int:.6f} & {gap_int:.6f} \\\\"
        )
    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_operator_covariant_reduction_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_operator_covariant_reduction_rows.tex")


if __name__ == "__main__":
    main()

