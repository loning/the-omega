# -*- coding: utf-8 -*-
"""
Resolvent-trace audit for the finite-dimensional protocol RG operator.

We verify (numerically, at small fixed truncation order) the standard identities:
  - one-point: sum_{t>=0} z^t * mean(F^t v) = mean((I - zF)^{-1} v)
  - two-point: sum_{t>=0} z^t * M2(F^t v) = M2(W(z)),
    where W(z) solves the linear fixed-point equation W = W0 + z F W F^T,
    and M2(W) = (1/16) * trace(W) for W = v v^T propagated by F.

This script is an audit artifact; it does not introduce new theorem-level claims.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_resolvent_trace_rows.tex
"""

from __future__ import annotations

import math
from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import build_F_matrix, mat_mul, mat_transpose, mat_vec, micro_q_fields_for_balanced_chain, solve_linear


def _mean(v: List[float]) -> float:
    return sum(v) / float(len(v))


def _m2(v: List[float]) -> float:
    return sum(float(x) * float(x) for x in v) / float(len(v))


def _outer(v: List[float]) -> List[List[float]]:
    return [[float(vi) * float(vj) for vj in v] for vi in v]


def _trace(M: List[List[float]]) -> float:
    return sum(float(M[i][i]) for i in range(len(M)))


def _fmt(x: float) -> str:
    return f"{x:.3e}"


def _solve_resolvent(F: List[List[float]], z: float, v: List[float]) -> List[float]:
    I_minus_zF = [[(1.0 if i == j else 0.0) - z * float(F[i][j]) for j in range(16)] for i in range(16)]
    return solve_linear(I_minus_zF, v)


def _fixed_point_W(F: List[List[float]], z: float, W0: List[List[float]], iters: int = 60) -> Tuple[List[List[float]], float]:
    """
    Solve W = W0 + z F W F^T by fixed-point iteration (converges for small z).
    Returns (W, residual_max_abs).
    """
    Ft = mat_transpose(F)
    W = [row[:] for row in W0]
    for _ in range(max(1, iters)):
        FW = mat_mul(F, W)
        FWFt = mat_mul(FW, Ft)
        W = [[float(W0[i][j]) + z * float(FWFt[i][j]) for j in range(16)] for i in range(16)]

    # Residual: W - (W0 + z F W F^T).
    FW = mat_mul(F, W)
    FWFt = mat_mul(FW, Ft)
    resid = 0.0
    for i in range(16):
        for j in range(16):
            r = float(W[i][j]) - (float(W0[i][j]) + z * float(FWFt[i][j]))
            resid = max(resid, abs(r))
    return W, resid


def main() -> None:
    rows: List[str] = []

    z = 0.25
    T = 10  # truncation order for partial sums

    # Columns:
    # n, z, T, mean_diff, m2_diff, W_resid.
    for n in range(3, 9):
        F = build_F_matrix(n)

        # Use one representative observable for the audit (log g).
        qn = micro_q_fields_for_balanced_chain(n)
        v0 = qn["logg"]

        # Convert to 16-vector by the same block averaging used elsewhere.
        # We reuse the existing balanced-chain script's definition implicitly via rg_operator helpers.
        from rg_operator import block_average_vector

        v = block_average_vector(n, v0)

        # One-point resolvent check.
        x = _solve_resolvent(F, z=z, v=v)
        mean_res = _mean(x)

        vt = v[:]
        s_mean = 0.0
        for t in range(T + 1):
            s_mean += (z**t) * _mean(vt)
            vt = mat_vec(F, vt)

        mean_diff = abs(mean_res - s_mean)

        # Two-point (second moment) resolvent check via matrix fixed point.
        W0 = _outer(v)
        W, resid = _fixed_point_W(F, z=z, W0=W0, iters=80)
        m2_res = _trace(W) / 16.0

        vt = v[:]
        s_m2 = 0.0
        for t in range(T + 1):
            s_m2 += (z**t) * _m2(vt)
            vt = mat_vec(F, vt)

        m2_diff = abs(m2_res - s_m2)

        rows.append(f"{n} & {z:.2f} & {T} & {_fmt(mean_diff)} & {_fmt(m2_diff)} & {_fmt(resid)} \\\\")

    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_resolvent_trace_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_resolvent_trace_rows.tex")


if __name__ == "__main__":
    main()

