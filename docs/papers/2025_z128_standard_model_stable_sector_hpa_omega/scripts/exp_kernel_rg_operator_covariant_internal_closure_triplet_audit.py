# -*- coding: utf-8 -*-
"""
Internal-mode closure triplet audit (anchor): conjugacy + gauge-invariant readout + resolvent identity.

This script produces a single audit artifact that closes three points at once:
  (A) internal orthonormal coordinates (standard representation) gauge covariance:
        F_std,g = H F_std H^T
  (B) gauge-invariant quadratic readout invariance under gauge:
        Tr(W_g)/dim = Tr(W)/dim  (up to float tolerance)
  (C) gauge-invariant quadratic resolvent-trace identity:
        Tr(W)/dim matches Σ_{t<=T} z^t ||F^t v||^2/dim

We compute all quantities both for the baseline operator and for a deterministically
sampled blockwise gauge field g_B.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_operator_covariant_internal_closure_triplet_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
import random
from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import (
    build_F_covariant_anchor,
    build_F_covariant_anchor_block_gauge,
    build_F_covariant_internal_orthonormal_from_full,
    build_sum_zero_orthonormal_basis,
    block_diag_internal_gauge,
    mat_mul,
    mat_transpose,
    mat_vec,
    solve_linear,
)


def _outer(v: List[float]) -> List[List[float]]:
    return [[float(vi) * float(vj) for vj in v] for vi in v]


def _trace(M: List[List[float]]) -> float:
    return sum(float(M[i][i]) for i in range(len(M)))


def _m2(v: List[float]) -> float:
    return sum(float(x) * float(x) for x in v) / float(len(v))


def _fmt(x: float) -> str:
    return f"{x:.3e}"


def max_abs_diff_mat(A: List[List[float]], B: List[List[float]]) -> float:
    m = 0.0
    for ra, rb in zip(A, B, strict=True):
        for a, b in zip(ra, rb, strict=True):
            d = abs(float(a) - float(b))
            if d > m:
                m = d
    return m


def _fixed_point_W(F: List[List[float]], z: float, W0: List[List[float]], iters: int = 160) -> Tuple[List[List[float]], float]:
    Ft = mat_transpose(F)
    W = [row[:] for row in W0]
    n = len(W0)
    for _ in range(max(1, iters)):
        FW = mat_mul(F, W)
        FWFt = mat_mul(FW, Ft)
        W = [[float(W0[i][j]) + z * float(FWFt[i][j]) for j in range(n)] for i in range(n)]
    # residual
    FW = mat_mul(F, W)
    FWFt = mat_mul(FW, Ft)
    resid = 0.0
    for i in range(n):
        for j in range(n):
            r = float(W[i][j]) - (float(W0[i][j]) + z * float(FWFt[i][j]))
            resid = max(resid, abs(r))
    return W, resid


def quadratic_resolvent_audit(F: List[List[float]], *, z: float, T: int, v: List[float]) -> Tuple[float, float, float]:
    """
    Return (quad_diff, resid, trW_over_dim).
    """
    dim = len(F)
    W0 = _outer(v)
    W, resid = _fixed_point_W(F, z=z, W0=W0, iters=200)
    trW = _trace(W)
    m2_res = trW / float(dim)
    vt = v[:]
    s_m2 = 0.0
    for t in range(T + 1):
        s_m2 += (z**t) * _m2(vt)
        vt = mat_vec(F, vt)
    return abs(m2_res - s_m2), float(resid), float(m2_res)


def choose_safe_z(F: List[List[float]]) -> tuple[float, float, float]:
    """
    Return (rho_bound, z, margin) where margin := z * rho_bound^2.
    We use the operator-norm upper bound rho_bound := max_i sum_j |F_ij|
    and choose z so that margin <= 0.10.
    """
    rho_bound = 0.0
    for row in F:
        rho_bound = max(rho_bound, sum(abs(float(x)) for x in row))
    if rho_bound <= 0.0:
        z = 0.1
    else:
        z = min(0.1, 0.10 / (rho_bound * rho_bound))
    margin = float(z) * float(rho_bound) * float(rho_bound)
    return float(rho_bound), float(z), float(margin)


def orth_err(H: List[List[float]]) -> float:
    # max abs of (H H^T - I)
    Ht = mat_transpose(H)
    HHt = mat_mul(H, Ht)
    n = len(HHt)
    m = 0.0
    for i in range(n):
        for j in range(n):
            target = 1.0 if i == j else 0.0
            d = abs(float(HHt[i][j]) - target)
            if d > m:
                m = d
    return m


def main() -> None:
    F_full, r = build_F_covariant_anchor(3)
    rng = random.Random(20260111)
    perms = list(itertools.permutations(range(r), r))
    g_block: List[Tuple[int, ...]] = [perms[rng.randrange(len(perms))] for _ in range(16)]
    Fg_full, _ = build_F_covariant_anchor_block_gauge(3, g_block=g_block)

    F_std = build_F_covariant_internal_orthonormal_from_full(F_full, r)
    F_std_g = build_F_covariant_internal_orthonormal_from_full(Fg_full, r)

    B = build_sum_zero_orthonormal_basis(r)
    H = block_diag_internal_gauge(g_block, B)
    Ht = mat_transpose(H)
    conj = mat_mul(mat_mul(H, F_std), Ht)
    conj_err = max_abs_diff_mat(F_std_g, conj)

    dim_int = len(F_std)
    # deterministic test vector in internal coordinates
    v = [float((i % 11) - 5) for i in range(dim_int)]
    # Under gauge, internal coordinates transform by v_g = H v for the same physical field.
    v_g = mat_vec(H, v)

    rho_bound, z, margin = choose_safe_z(F_std)
    T = 12
    quad_diff, resid, trW = quadratic_resolvent_audit(F_std, z=z, T=T, v=v)
    quad_diff_g, resid_g, trW_g = quadratic_resolvent_audit(F_std_g, z=z, T=T, v=v_g)
    tr_invar_err = abs(trW_g - trW)

    ortho = orth_err(H)
    rows = [
        f"3 & 8 & {r} & {dim_int} & {rho_bound:.3e} & {z:.3e} & {margin:.3e} & {T} & {_fmt(conj_err)} & {_fmt(ortho)} & {_fmt(tr_invar_err)} & {_fmt(quad_diff)} & {_fmt(resid)} \\\\",
        "\\bottomrule",
    ]
    out = generated_dir() / "kernel_rg_operator_covariant_internal_closure_triplet_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_operator_covariant_internal_closure_triplet_rows.tex")


if __name__ == "__main__":
    main()

