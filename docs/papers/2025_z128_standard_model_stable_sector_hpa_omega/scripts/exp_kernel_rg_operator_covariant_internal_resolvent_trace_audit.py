# -*- coding: utf-8 -*-
"""
Internal-mode resolvent-trace audit for the covariant RG operator (anchor).

We reduce the covariant operator F_3^∇ (dim 16*r_8) to an internal-mode operator
F_int of dimension 16*(r_8-1) by an exact coordinate transform:
  F_int = L F_3^∇ Q,
where Q embeds internal coordinates into per-block slot-sum-zero vectors, and L
takes differences against a reference slot (so LQ=I).

We then audit standard resolvent identities on this reduced operator:
  - one-point: mean((I - z F_int)^{-1} v) equals truncated sum of z^t mean(F_int^t v),
  - two-point: fixed-point W = W0 + z F_int W F_int^T yields trace(W)/dim matching
    truncated sum of z^t second-moment.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_operator_covariant_internal_resolvent_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import build_F_covariant_internal_anchor, mat_mul, mat_transpose, mat_vec, solve_linear


def _mean(v: List[float]) -> float:
    return sum(float(x) for x in v) / float(len(v))


def _m2(v: List[float]) -> float:
    return sum(float(x) * float(x) for x in v) / float(len(v))


def _outer(v: List[float]) -> List[List[float]]:
    return [[float(vi) * float(vj) for vj in v] for vi in v]


def _trace(M: List[List[float]]) -> float:
    return sum(float(M[i][i]) for i in range(len(M)))


def _fmt(x: float) -> str:
    return f"{x:.3e}"


def _solve_resolvent(F: List[List[float]], z: float, v: List[float]) -> List[float]:
    n = len(F)
    A = [[(1.0 if i == j else 0.0) - z * float(F[i][j]) for j in range(n)] for i in range(n)]
    return solve_linear(A, v)


def _fixed_point_W(F: List[List[float]], z: float, W0: List[List[float]], iters: int = 80) -> Tuple[List[List[float]], float]:
    Ft = mat_transpose(F)
    W = [row[:] for row in W0]
    for _ in range(max(1, iters)):
        FW = mat_mul(F, W)
        FWFt = mat_mul(FW, Ft)
        n = len(W0)
        W = [[float(W0[i][j]) + z * float(FWFt[i][j]) for j in range(n)] for i in range(n)]
    # residual
    FW = mat_mul(F, W)
    FWFt = mat_mul(FW, Ft)
    resid = 0.0
    n = len(W0)
    for i in range(n):
        for j in range(n):
            r = float(W[i][j]) - (float(W0[i][j]) + z * float(FWFt[i][j]))
            resid = max(resid, abs(r))
    return W, resid


def main() -> None:
    F, r = build_F_covariant_internal_anchor(3)
    dim = len(F)
    if dim != 16 * (r - 1):
        raise AssertionError("Unexpected internal dimension.")

    # deterministic internal test vector (non-constant)
    v = [float((i % 11) - 5) for i in range(dim)]

    # Choose z conservatively for convergence of both series and the matrix fixed point:
    # need roughly z * rho(F)^2 < 1 for the two-point equation.
    abs_row_sum = 0.0
    for row in F:
        abs_row_sum = max(abs_row_sum, sum(abs(float(x)) for x in row))
    # Use a safe margin.
    if abs_row_sum <= 0.0:
        z = 0.1
    else:
        z = min(0.1, 0.10 / (abs_row_sum * abs_row_sum))
    T = 12

    # one-point
    x = _solve_resolvent(F, z=z, v=v)
    mean_res = _mean(x)
    vt = v[:]
    s_mean = 0.0
    for t in range(T + 1):
        s_mean += (z**t) * _mean(vt)
        vt = mat_vec(F, vt)
    mean_diff = abs(mean_res - s_mean)

    # two-point
    W0 = _outer(v)
    W, resid = _fixed_point_W(F, z=z, W0=W0, iters=160)
    m2_res = _trace(W) / float(dim)
    vt = v[:]
    s_m2 = 0.0
    for t in range(T + 1):
        s_m2 += (z**t) * _m2(vt)
        vt = mat_vec(F, vt)
    m2_diff = abs(m2_res - s_m2)

    rows: List[str] = []
    # Columns: n, m=2(n+1), r, dim_int, z, T, mean_diff, m2_diff, W_resid
    rows.append(f"3 & 8 & {r} & {dim} & {z:.3e} & {T} & {_fmt(mean_diff)} & {_fmt(m2_diff)} & {_fmt(resid)} \\\\")
    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_operator_covariant_internal_resolvent_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_operator_covariant_internal_resolvent_rows.tex")


if __name__ == "__main__":
    main()

