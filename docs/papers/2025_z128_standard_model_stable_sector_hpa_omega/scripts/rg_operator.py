# -*- coding: utf-8 -*-
"""
Finite-dimensional protocol RG operators on the balanced Hilbert screen.

This module implements the explicit 16x16 coarse RG operator used in the
"protocol RG operator closure" narrative:
  - microstate index set Omega_n = {0..4^n-1}, placed on a 2^n x 2^n Hilbert screen,
  - a fixed axis-aligned 4x4 block partition (block side = 2^(n-2)),
  - block projection P_n (averaging) and lift P_n^* (block-constant pullback),
  - Hilbert-recursive uplift u_n via parent-cell projection on the 2D screen,
  - a protocol-local transport (parallel-transport) operator T_n on the screen graph,
  - F_n = P_{n+1} T_{n+1} U_n P_n^* as a 16x16 matrix,
  - a weighted family \\hat{F}_n(t) = P_{n+1} T_{n+1} U_n exp(t * phi_n) P_n^*,
    where phi_n(k)=log g_{2n}(Fold_{2n}(k)).

Only the Python standard library is used, but we reuse deterministic local
helpers from this paper's scripts (Hilbert curve and folding caches).
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List, Tuple

import exp_hilbert_chirality_index as hil
from common_cache import CACHE_VERSION, cache_path, load_or_compute
from common_progress import ProgressEvery
from protocol_kernel import cached_degeneracy_map, cached_foldm_outputs


Mat = List[List[float]]
Vec = List[float]


def _n_micro(n_bits: int) -> int:
    if n_bits < 0:
        raise ValueError("n_bits must be nonnegative.")
    return 1 << (2 * n_bits)


def block_size(n_bits: int) -> int:
    if n_bits < 3:
        raise ValueError("n_bits must be >= 3 for a 4x4 block partition.")
    return 1 << (n_bits - 2)


def _block_id_from_xy(x: int, y: int, *, bsz: int) -> int:
    bx = x // bsz
    by = y // bsz
    if not (0 <= bx < 4 and 0 <= by < 4):
        raise ValueError("Computed block index out of range.")
    return by * 4 + bx


def block_id_by_index(n_bits: int) -> List[int]:
    """
    Return a list block_id[k] in {0..15} for k in {0..4^n-1}, using the
    deterministic Hilbert path ordering as the microstate index order.
    """
    if n_bits < 3:
        raise ValueError("n_bits must be >= 3.")

    key = cache_path(f"rg_block_id_n{n_bits}_v{CACHE_VERSION}.pkl")

    def compute() -> List[int]:
        path = hil.hilbert_curve(n_bits)
        if len(path) != _n_micro(n_bits):
            raise AssertionError("Unexpected Hilbert path length.")
        bsz = block_size(n_bits)
        out: List[int] = []
        for (x, y) in path:
            out.append(_block_id_from_xy(x, y, bsz=bsz))
        return out

    return load_or_compute(key, compute)


def hilbert_inverse_index_map(n_bits: int) -> Dict[Tuple[int, int], int]:
    """
    Invert the deterministic Hilbert addressing map H_n by tabulating (x,y) -> k.
    """
    if n_bits < 0:
        raise ValueError("n_bits must be nonnegative.")

    key = cache_path(f"hilbert_inv_xy_to_k_n{n_bits}_v{CACHE_VERSION}.pkl")

    def compute() -> Dict[Tuple[int, int], int]:
        path = hil.hilbert_curve(n_bits)
        out: Dict[Tuple[int, int], int] = {}
        for k, (x, y) in enumerate(path):
            out[(int(x), int(y))] = int(k)
        # Basic sanity: full grid.
        side = 1 << n_bits
        if len(out) != side * side:
            raise AssertionError("Unexpected inverse-map size for Hilbert curve.")
        return out

    return load_or_compute(key, compute)


def parent_index_map(n_bits: int) -> List[int]:
    """
    Hilbert-recursive parent map u_n: Omega_{n+1} -> Omega_n, realized in index space.

    For k' in {0..4^{n+1}-1} with H_{n+1}(k')=(x',y'), define the parent cell
    (x,y)=(floor(x'/2), floor(y'/2)) on the 2^n x 2^n screen, and set
    u_n(k') := H_n^{-1}(x,y).

    Returns a list parent[k'] = u_n(k') of length 4^{n+1}.
    """
    if n_bits < 0:
        raise ValueError("n_bits must be nonnegative.")

    key = cache_path(f"rg_parent_map_n{n_bits}_v{CACHE_VERSION}.pkl")

    def compute() -> List[int]:
        path_np1 = hil.hilbert_curve(n_bits + 1)
        inv_n = hilbert_inverse_index_map(n_bits)
        out: List[int] = []
        for (x2, y2) in path_np1:
            x = int(x2) >> 1
            y = int(y2) >> 1
            out.append(inv_n[(x, y)])
        if len(out) != _n_micro(n_bits + 1):
            raise AssertionError("Unexpected parent-map length.")
        return out

    return load_or_compute(key, compute)

def _neighbors_4(x: int, y: int, *, L: int) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    if x > 0:
        out.append((x - 1, y))
    if x < L:
        out.append((x + 1, y))
    if y > 0:
        out.append((x, y - 1))
    if y < L:
        out.append((x, y + 1))
    return out


def _transport_source_weights_for_dest(
    x: int, y: int, *, inv: Dict[Tuple[int, int], int], L: int, p_stay: float
) -> List[Tuple[int, float]]:
    """
    Return a list of (k_source, weight) contributing to (T f)(k_dest) for a lazy
    nearest-neighbor random walk on the 2D grid with reflecting boundary.
    """
    k_self = inv[(x, y)]
    neigh = _neighbors_4(x, y, L=L)
    deg = len(neigh)
    out: List[Tuple[int, float]] = [(k_self, float(p_stay))]
    if deg > 0 and p_stay < 1.0:
        w = (1.0 - float(p_stay)) / float(deg)
        for (xn, yn) in neigh:
            out.append((inv[(xn, yn)], w))
    return out


def block_average_vector(n_bits: int, values: List[float]) -> Vec:
    """
    Compute the 16-vector of block averages for a micro-field `values[k]`
    aligned with Hilbert index order k in {0..4^n-1}.
    """
    N = _n_micro(n_bits)
    if len(values) != N:
        raise ValueError("values must have length 4^n.")
    bids = block_id_by_index(n_bits)
    sums = [0.0] * 16
    for k, v in enumerate(values):
        sums[bids[k]] += float(v)
    denom = float(N // 16)
    return [s / denom for s in sums]


def mat_vec(A: Mat, x: Vec) -> Vec:
    if not A:
        raise ValueError("Empty matrix.")
    n = len(A)
    m = len(A[0])
    if len(x) != m:
        raise ValueError("Dimension mismatch.")
    out = [0.0] * n
    for i in range(n):
        row = A[i]
        s = 0.0
        for j in range(m):
            s += float(row[j]) * float(x[j])
        out[i] = s
    return out


def mat_transpose(A: Mat) -> Mat:
    if not A:
        raise ValueError("Empty matrix.")
    n = len(A)
    m = len(A[0])
    return [[A[i][j] for i in range(n)] for j in range(m)]


def vec_mean(x: Vec) -> float:
    if not x:
        raise ValueError("Empty vector.")
    return sum(float(v) for v in x) / float(len(x))


def vec_norm2(x: Vec) -> float:
    return math.sqrt(sum(float(v) * float(v) for v in x))


def project_mean_zero(x: Vec) -> Vec:
    """
    Project onto the codimension-1 subspace orthogonal to the constant vector,
    using the uniform mean on the 16-block quotient.
    """
    m = vec_mean(x)
    return [float(v) - m for v in x]


def second_eigenvalue_abs(A: Mat, *, iters: int = 800) -> float:
    """
    Estimate |lambda_2| for a row-stochastic 16x16 matrix A by power iteration
    on the mean-zero subspace (deflating the trivial eigenvalue 1).
    """
    n = len(A)
    if n == 0 or any(len(row) != n for row in A):
        raise ValueError("A must be a square matrix.")
    if iters <= 0:
        raise ValueError("iters must be positive.")

    # Deterministic non-constant seed.
    v = [float((i % 7) - 3) for i in range(n)]
    v = project_mean_zero(v)
    nv = vec_norm2(v)
    if nv == 0.0:
        raise AssertionError("Unexpected zero seed after projection.")
    v = [vv / nv for vv in v]

    lam = 0.0
    for _ in range(iters):
        w = mat_vec(A, v)
        w = project_mean_zero(w)
        nw = vec_norm2(w)
        if nw == 0.0:
            return 0.0
        # Rayleigh-like ratio in norm.
        lam = nw
        v = [ww / nw for ww in w]

    return float(abs(lam))


def row_sum_stats(A: Mat) -> Tuple[float, float, float]:
    """
    Return (max_abs_row_sum_err_from_1, row_sum_min, row_sum_max).
    """
    if not A:
        raise ValueError("Empty matrix.")
    errs: List[float] = []
    sums: List[float] = []
    for row in A:
        s = sum(float(v) for v in row)
        sums.append(s)
        errs.append(abs(s - 1.0))
    return (max(errs), min(sums), max(sums))


def pf_right_eigenpair(A: Mat, *, iters: int = 1200) -> Tuple[float, Vec]:
    """
    Approximate the Perron-Frobenius dominant eigenpair (lambda, h) for a
    nonnegative square matrix A using power iteration on the right.
    """
    n = len(A)
    if n == 0 or any(len(row) != n for row in A):
        raise ValueError("A must be a square matrix.")
    if iters <= 0:
        raise ValueError("iters must be positive.")

    # Positive deterministic seed (L1-normalized).
    v = [1.0 / float(n)] * n
    lam = 1.0
    for _ in range(iters):
        w = mat_vec(A, v)
        s = sum(float(x) for x in w)
        if s <= 0.0:
            raise ValueError("Nonpositive iterate; A may be zero.")
        lam = float(s)  # since sum(v)=1, use L1 growth as eigenvalue proxy
        v = [float(x) / lam for x in w]

    # Normalize h to mean 1 for stability.
    m = vec_mean(v)
    if m <= 0.0:
        raise AssertionError("Unexpected nonpositive PF eigenvector mean.")
    h = [float(x) / m for x in v]
    return (float(lam), h)


def doob_row_stochastic(A: Mat, lam: float, h: Vec) -> Mat:
    """
    Doob transform (finite-dimensional): build a row-stochastic matrix P from A
    given a positive right eigenpair A h = lam h:

      P_ij = A_ij * h_j / (lam * h_i).
    """
    n = len(A)
    if n == 0 or any(len(row) != n for row in A):
        raise ValueError("A must be a square matrix.")
    if len(h) != n:
        raise ValueError("Dimension mismatch for h.")
    if lam <= 0.0:
        raise ValueError("lam must be positive.")

    P: Mat = [[0.0] * n for _ in range(n)]
    for i in range(n):
        hi = float(h[i])
        if hi <= 0.0:
            raise ValueError("h must be positive.")
        for j in range(n):
            P[i][j] = float(A[i][j]) * float(h[j]) / (float(lam) * hi)
    return P


def mat_mul(A: Mat, B: Mat) -> Mat:
    if not A or not B:
        raise ValueError("Empty matrix.")
    n = len(A)
    k = len(A[0])
    if len(B) != k:
        raise ValueError("Dimension mismatch.")
    m = len(B[0])
    out: Mat = [[0.0] * m for _ in range(n)]
    for i in range(n):
        for t in range(k):
            a = float(A[i][t])
            if a == 0.0:
                continue
            bt = B[t]
            for j in range(m):
                out[i][j] += a * float(bt[j])
    return out


def det(A: Mat) -> float:
    """
    Determinant by Gaussian elimination with partial pivoting (float).
    Intended for small matrices (<= 16).
    """
    n = len(A)
    if n == 0 or any(len(row) != n for row in A):
        raise ValueError("A must be a non-empty square matrix.")
    M = [row[:] for row in A]
    sign = 1.0
    d = 1.0
    for i in range(n):
        # Pivot.
        piv = i
        piv_abs = abs(M[i][i])
        for r in range(i + 1, n):
            ar = abs(M[r][i])
            if ar > piv_abs:
                piv_abs = ar
                piv = r
        if piv_abs == 0.0:
            return 0.0
        if piv != i:
            M[i], M[piv] = M[piv], M[i]
            sign *= -1.0
        pivv = float(M[i][i])
        d *= pivv
        # Eliminate below.
        for r in range(i + 1, n):
            fac = float(M[r][i]) / pivv
            if fac == 0.0:
                continue
            for c in range(i, n):
                M[r][c] -= fac * float(M[i][c])
    return sign * d


def solve_linear(A: Mat, b: Vec) -> Vec:
    """
    Solve A x = b by Gaussian elimination with partial pivoting (float).
    """
    n = len(A)
    if n == 0 or any(len(row) != n for row in A):
        raise ValueError("A must be a non-empty square matrix.")
    if len(b) != n:
        raise ValueError("Dimension mismatch.")
    M = [row[:] + [float(bi)] for row, bi in zip(A, b, strict=True)]
    # Forward elimination.
    for i in range(n):
        piv = i
        piv_abs = abs(M[i][i])
        for r in range(i + 1, n):
            ar = abs(M[r][i])
            if ar > piv_abs:
                piv_abs = ar
                piv = r
        if piv_abs == 0.0:
            raise ValueError("Singular matrix.")
        if piv != i:
            M[i], M[piv] = M[piv], M[i]
        pivv = float(M[i][i])
        for r in range(i + 1, n):
            fac = float(M[r][i]) / pivv
            if fac == 0.0:
                continue
            for c in range(i, n + 1):
                M[r][c] -= fac * float(M[i][c])
    # Back substitution.
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = float(M[i][n])
        for j in range(i + 1, n):
            s -= float(M[i][j]) * x[j]
        x[i] = s / float(M[i][i])
    return x


def power_iteration_rho(A: Mat, iters: int = 200) -> float:
    """
    Crude spectral-radius estimate for nonnegative matrices.
    """
    n = len(A)
    x = [1.0] * n
    lam = 0.0
    for _ in range(max(1, iters)):
        y = mat_vec(A, x)
        norm = max(abs(v) for v in y)
        if norm == 0.0:
            return 0.0
        y = [v / norm for v in y]
        x = y
        lam = norm
    return float(lam)


def build_F_matrix(n_bits: int) -> Mat:
    """
    Build the 16x16 matrix for
      F_n = P_{n+1} T_{n+1} U_n P_n^*,
    where T_{n+1} is the scalar (lazy random-walk) parallel-transport operator
    on the 2^{n+1} x 2^{n+1} screen graph.
    """
    if n_bits < 3:
        raise ValueError("n_bits must be >= 3.")
    p_stay = 0.5
    bids_n = block_id_by_index(n_bits)
    bids_np1 = block_id_by_index(n_bits + 1)
    parents_np1 = parent_index_map(n_bits)  # maps Omega_{n+1} index -> Omega_n index
    path_np1 = hil.hilbert_curve(n_bits + 1)
    inv_np1 = hilbert_inverse_index_map(n_bits + 1)
    L = (1 << (n_bits + 1)) - 1

    Np1 = _n_micro(n_bits + 1)
    denom = float(Np1 // 16)

    counts: List[List[float]] = [[0.0] * 16 for _ in range(16)]
    prog = ProgressEvery(label=f"build_F_matrix n={n_bits}", total=Np1, interval_s=60.0)
    prog.start()
    for k_dest, (x, y) in enumerate(path_np1):
        if k_dest % 4096 == 0:
            prog.maybe(k_dest)
        i = bids_np1[k_dest]
        srcs = _transport_source_weights_for_dest(int(x), int(y), inv=inv_np1, L=L, p_stay=p_stay)
        for k_src, w in srcs:
            j = bids_n[parents_np1[k_src]]
            counts[i][j] += float(w)
    prog.done()

    return [[counts[i][j] / denom for j in range(16)] for i in range(16)]


def build_weighted_F_matrix(n_bits: int, t: float) -> Mat:
    """
    Build the 16x16 weighted matrix:
      \\hat F_n(t) = P_{n+1} T_{n+1} U_n exp(t * phi_n) P_n^*,
    where phi_n(k)=log g_{2n}(Fold_{2n}(k)) for k in Omega_n.
    """
    if n_bits < 3:
        raise ValueError("n_bits must be >= 3.")
    m = 2 * n_bits
    outs = cached_foldm_outputs(m)
    gm = cached_degeneracy_map(m)
    if len(outs) != _n_micro(n_bits):
        raise AssertionError("Unexpected Fold_m output length for balanced coupling.")
    phi = [math.log(float(gm[w])) for w in outs]

    p_stay = 0.5
    bids_n = block_id_by_index(n_bits)
    bids_np1 = block_id_by_index(n_bits + 1)
    parents_np1 = parent_index_map(n_bits)
    path_np1 = hil.hilbert_curve(n_bits + 1)
    inv_np1 = hilbert_inverse_index_map(n_bits + 1)
    L = (1 << (n_bits + 1)) - 1
    Np1 = _n_micro(n_bits + 1)
    denom = float(Np1 // 16)

    sums: List[List[float]] = [[0.0] * 16 for _ in range(16)]
    prog = ProgressEvery(label=f"build_weighted_F_matrix n={n_bits} t={t}", total=Np1, interval_s=60.0)
    prog.start()
    for k_dest, (x, y) in enumerate(path_np1):
        if k_dest % 4096 == 0:
            prog.maybe(k_dest)
        i = bids_np1[k_dest]
        srcs = _transport_source_weights_for_dest(int(x), int(y), inv=inv_np1, L=L, p_stay=p_stay)
        for k_src, wT in srcs:
            parent = parents_np1[k_src]
            j = bids_n[parent]
            w = float(wT) * math.exp(float(t) * float(phi[parent]))
            sums[i][j] += w
    prog.done()

    return [[sums[i][j] / denom for j in range(16)] for i in range(16)]


def micro_q_fields_for_balanced_chain(n_bits: int) -> Dict[str, List[float]]:
    """
    Return micro-fields aligned with k in {0..4^n-1} for the four intrinsic scalars
    used by the balanced-chain RG-flow table:
      - weight: |w|_1
      - value:  V_m(w) (Fibonacci-weight value)
      - dpi:    D_pi(w)=1_{w1=wm=1}
      - logg:   log g_m(w)
    """
    if n_bits < 3:
        raise ValueError("n_bits must be >= 3.")
    m = 2 * n_bits
    outs = cached_foldm_outputs(m)
    gm = cached_degeneracy_map(m)

    # Fibonacci weights for V_m(w): [F2..F_{m+1}] = [1,2,3,5,...].
    weights: List[int] = [1, 2]
    while len(weights) < m:
        weights.append(weights[-1] + weights[-2])

    q_weight: List[float] = []
    q_value: List[float] = []
    q_dpi: List[float] = []
    q_logg: List[float] = []

    for w in outs:
        g = gm[w]
        q_weight.append(float(w.count("1")))
        q_value.append(float(sum((1 if w[i] == "1" else 0) * weights[i] for i in range(m))))
        q_dpi.append(1.0 if (w[0] == "1" and w[-1] == "1") else 0.0)
        q_logg.append(math.log(float(g)))

    return {"weight": q_weight, "value": q_value, "dpi": q_dpi, "logg": q_logg}

