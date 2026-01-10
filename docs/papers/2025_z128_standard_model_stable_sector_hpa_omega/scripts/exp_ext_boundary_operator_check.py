# -*- coding: utf-8 -*-
"""
Operator-evaluation check for prefix-extension counts and pi-boundary subsets.

This script audits, for m=6..16:
  - Ext_m(u) := { w in X_m : w[:6] = u } counts,
  - the subset ending in 1 (w_m = 1),
  - and the pi-channel boundary subset (w_1 = w_m = 1),

against the 2x2 operator-evaluation formulas with A^L, where
  A = [[1,1],[1,0]] is the golden-mean transition matrix,
  L = m-6 is the extension length.

This is a deterministic consistency check: enumeration is over X_m (Fibonacci size),
not over all dyadic microstates.

Outputs (LaTeX fragment):
  - sections/generated/ext_boundary_operator_check_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from common_paths import generated_dir
from common_tex import write_lines
from protocol_kernel import all_xm


Mat2 = Tuple[Tuple[int, int], Tuple[int, int]]


def mat_mul(A: Mat2, B: Mat2) -> Mat2:
    (a00, a01), (a10, a11) = A
    (b00, b01), (b10, b11) = B
    return (
        (a00 * b00 + a01 * b10, a00 * b01 + a01 * b11),
        (a10 * b00 + a11 * b10, a10 * b01 + a11 * b11),
    )


def mat_pow(A: Mat2, n: int) -> Mat2:
    if n < 0:
        raise ValueError("n must be nonnegative.")
    # Exponentiation by squaring.
    R: Mat2 = ((1, 0), (0, 1))
    X = A
    k = n
    while k > 0:
        if k & 1:
            R = mat_mul(R, X)
        X = mat_mul(X, X)
        k >>= 1
    return R


def row_sum(M: Mat2, row: int) -> int:
    if row == 0:
        return M[0][0] + M[0][1]
    if row == 1:
        return M[1][0] + M[1][1]
    raise ValueError("row must be 0 or 1.")


def entry(M: Mat2, i: int, j: int) -> int:
    return M[i][j]


def main() -> None:
    # A is the golden-mean transition matrix used throughout the e-channel.
    A: Mat2 = ((1, 1), (1, 0))

    X6 = all_xm(6)
    if len(X6) != 21:
        raise AssertionError("Expected |X6|=21.")

    rows: List[str] = []
    # Columns:
    # m, L, row-sums (u6=0/1), end-1 counts (u6=0/1),
    # max_err_Ext, max_err_end1, max_err_boundary.
    for m in range(6, 17):
        L = m - 6
        Xm = all_xm(m)

        # Group lifts by prefix u in X6.
        lifts_of: Dict[str, List[str]] = {u: [] for u in X6}
        for w in Xm:
            u = w[:6]
            if u in lifts_of:
                lifts_of[u].append(w)
            else:
                # Should be impossible: any 6-prefix of an admissible word is admissible.
                raise AssertionError("Unexpected 6-prefix not in X6.")

        AL = mat_pow(A, L)

        # Operator predictions depend only on u6.
        ext_u6_0 = row_sum(AL, 0)
        ext_u6_1 = row_sum(AL, 1)
        end1_u6_0 = entry(AL, 0, 1)
        end1_u6_1 = entry(AL, 1, 1)

        max_err_ext = 0
        max_err_end1 = 0
        max_err_bdry = 0
        for u, lifts in lifts_of.items():
            u1 = 1 if u[0] == "1" else 0
            u6 = 1 if u[-1] == "1" else 0

            ext_enum = len(lifts)
            end1_enum = sum(1 for w in lifts if w[-1] == "1")
            bdry_enum = sum(1 for w in lifts if (w[0] == "1" and w[-1] == "1"))

            ext_op = ext_u6_1 if u6 == 1 else ext_u6_0
            end1_op = end1_u6_1 if u6 == 1 else end1_u6_0
            bdry_op = end1_op if u1 == 1 else 0

            max_err_ext = max(max_err_ext, abs(ext_enum - ext_op))
            max_err_end1 = max(max_err_end1, abs(end1_enum - end1_op))
            max_err_bdry = max(max_err_bdry, abs(bdry_enum - bdry_op))

        rows.append(
            f"{m} & {L} & {ext_u6_0} & {ext_u6_1} & {end1_u6_0} & {end1_u6_1}"
            f" & {max_err_ext} & {max_err_end1} & {max_err_bdry} \\\\"
        )

    rows.append("\\bottomrule")

    out = generated_dir() / "ext_boundary_operator_check_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/ext_boundary_operator_check_rows.tex")


if __name__ == "__main__":
    main()

