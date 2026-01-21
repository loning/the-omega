# -*- coding: utf-8 -*-
"""
Added-edge <-> finite-rank update: determinant update audit (toy).

Purpose:
  Provide a deterministic toy artifact for the ladder step
    added edge (graph/topology) <-> finite-rank update (operator) <-> det/logdet packaging.

Model:
  - Base graph: a 6-node path graph adjacency A0.
  - Update: add an undirected shortcut edge (i,j), giving A1 = A0 + Delta,
    where Delta = e_i e_j^T + e_j e_i^T (rank-2).
  - Packaging: D(z) = det(I - z A). Report ratios and logabs increments.
  - Certificate identity: use the finite-rank determinant lemma (Woodbury) to compute
    det(I - z A1)/det(I - z A0) from a 2x2 determinant and compare to direct det.

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.

Outputs (LaTeX fragments):
  - sections/generated/added_edge_det_update_rows.tex
  - sections/generated/added_edge_det_update_summary.tex
"""

from __future__ import annotations

import math
from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines

Matrix = List[List[float]]


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(float(x)):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


def _eye(n: int) -> Matrix:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _mat_copy(a: Matrix) -> Matrix:
    return [row[:] for row in a]


def _mat_add(a: Matrix, b: Matrix) -> Matrix:
    n = len(a)
    return [[float(a[i][j] + b[i][j]) for j in range(n)] for i in range(n)]


def _mat_sub(a: Matrix, b: Matrix) -> Matrix:
    n = len(a)
    return [[float(a[i][j] - b[i][j]) for j in range(n)] for i in range(n)]


def _mat_scale(a: Matrix, s: float) -> Matrix:
    n = len(a)
    return [[float(s) * float(a[i][j]) for j in range(n)] for i in range(n)]


def _mat_mul(a: Matrix, b: Matrix) -> Matrix:
    # Generic matrix multiplication: (p x q) * (q x r) -> (p x r)
    p = len(a)
    q = len(a[0]) if a else 0
    if q == 0:
        return []
    if len(b) != q:
        raise ValueError("mat_mul: dimension mismatch")
    r = len(b[0]) if b else 0
    out = [[0.0 for _ in range(r)] for _ in range(p)]
    for i in range(p):
        for k in range(q):
            aik = float(a[i][k])
            if aik == 0.0:
                continue
            bk = b[k]
            for j in range(r):
                out[i][j] += aik * float(bk[j])
    return out


def _det(a: Matrix) -> float:
    m = _mat_copy(a)
    n = len(m)
    det = 1.0
    sign = 1.0
    for k in range(n):
        piv = k
        best = abs(float(m[k][k]))
        for i in range(k + 1, n):
            v = abs(float(m[i][k]))
            if v > best:
                best = v
                piv = i
        if best == 0.0:
            return 0.0
        if piv != k:
            m[k], m[piv] = m[piv], m[k]
            sign *= -1.0
        pivot = float(m[k][k])
        det *= pivot
        for i in range(k + 1, n):
            f = float(m[i][k]) / pivot
            m[i][k] = 0.0
            if f == 0.0:
                continue
            rowi = m[i]
            rowk = m[k]
            for j in range(k + 1, n):
                rowi[j] = float(rowi[j]) - f * float(rowk[j])
    return float(sign * det)


def _inv(a: Matrix) -> Matrix:
    n = len(a)
    m = [row[:] + eye_row[:] for row, eye_row in zip(_mat_copy(a), _eye(n))]
    for k in range(n):
        piv = k
        best = abs(float(m[k][k]))
        for i in range(k + 1, n):
            v = abs(float(m[i][k]))
            if v > best:
                best = v
                piv = i
        if best == 0.0:
            raise ValueError("matrix is singular")
        if piv != k:
            m[k], m[piv] = m[piv], m[k]
        pivot = float(m[k][k])
        inv_p = 1.0 / pivot
        for j in range(2 * n):
            m[k][j] = float(m[k][j]) * inv_p
        for i in range(n):
            if i == k:
                continue
            f = float(m[i][k])
            if f == 0.0:
                continue
            for j in range(2 * n):
                m[i][j] = float(m[i][j]) - f * float(m[k][j])
    return [row[n:] for row in m]


def _path_adjacency(n: int) -> Matrix:
    a = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n - 1):
        a[i][i + 1] = 1.0
        a[i + 1][i] = 1.0
    return a


def _added_edge_delta(n: int, i: int, j: int) -> Matrix:
    if i == j:
        raise ValueError("self-loop not supported in this toy")
    d = [[0.0 for _ in range(n)] for _ in range(n)]
    d[i][j] = 1.0
    d[j][i] = 1.0
    return d


def _u_v_for_added_edge(n: int, i: int, j: int) -> Tuple[Matrix, Matrix]:
    # Delta = e_i e_j^T + e_j e_i^T = U V^T with k=2 using:
    #   U = [e_i, e_j], V = [e_j, e_i]
    U = [[0.0, 0.0] for _ in range(n)]
    V = [[0.0, 0.0] for _ in range(n)]
    U[i][0] = 1.0
    U[j][1] = 1.0
    V[j][0] = 1.0
    V[i][1] = 1.0
    return U, V


def _transpose(a: Matrix) -> Matrix:
    n = len(a)
    m = len(a[0]) if a else 0
    return [[float(a[i][j]) for i in range(n)] for j in range(m)]


def _small2_det(m: Matrix) -> float:
    return float(m[0][0] * m[1][1] - m[0][1] * m[1][0])


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "added_edge_det_update_rows.tex"
    sum_path = out_dir / "added_edge_det_update_summary.tex"

    n = 6
    i, j = 0, 3  # add a long shortcut edge
    A0 = _path_adjacency(n)
    Delta = _added_edge_delta(n, i, j)
    A1 = _mat_add(A0, Delta)

    # z-grid stays away from singular points for numerical stability.
    z_grid = [0.05, 0.10, 0.15, 0.20, 0.25]

    rows: List[str] = []
    max_err = 0.0
    arg_max = (0.0, 0.0)

    for z in z_grid:
        B0 = _mat_sub(_eye(n), _mat_scale(A0, float(z)))
        B1 = _mat_sub(_eye(n), _mat_scale(A1, float(z)))
        det0 = _det(B0)
        det1 = _det(B1)
        ratio_direct = float(det1 / det0) if det0 != 0.0 else float("nan")
        dlogabs = float(math.log(abs(det1)) - math.log(abs(det0))) if det0 != 0.0 and det1 != 0.0 else float("nan")

        # Woodbury 2x2 ratio:
        # B1 = B0 - z Delta = B0 + U W V^T with W = (-z) I2 and Delta = U V^T.
        U, V = _u_v_for_added_edge(n, i, j)
        B0inv = _inv(B0)
        Vt = _transpose(V)
        Vt_B0inv = _mat_mul(Vt, B0inv)          # (2 x n)
        Vt_B0inv_U = _mat_mul(Vt_B0inv, U)      # (2 x 2)
        # M = I2 + (-z) * (V^T B0^{-1} U)
        M = [
            [1.0 - float(z) * float(Vt_B0inv_U[0][0]), 0.0 - float(z) * float(Vt_B0inv_U[0][1])],
            [0.0 - float(z) * float(Vt_B0inv_U[1][0]), 1.0 - float(z) * float(Vt_B0inv_U[1][1])],
        ]
        ratio_woodbury = _small2_det(M)
        err = abs(float(ratio_direct) - float(ratio_woodbury)) if math.isfinite(ratio_direct) else float("nan")
        if math.isfinite(err) and err > max_err:
            max_err = float(err)
            arg_max = (float(z), float(err))

        rows.append(
            " & ".join(
                [
                    str(n),
                    f"({i},{j})",
                    _fmt(z, 3),
                    _fmt(det0, 6),
                    _fmt(det1, 6),
                    _fmt(ratio_direct, 6),
                    _fmt(ratio_woodbury, 6),
                    _fmt(dlogabs, 6),
                    _fmt(err, 6),
                ]
            )
            + r" \\"
        )

    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])

    write_lines(
        sum_path,
        [
            r"\paragraph{Added edge $\leftrightarrow$ finite-rank update (det packaging toy).} \AuditTag "
            + r"On a fixed 6-node path graph adjacency $A_0$ we add a shortcut edge $(0,3)$, obtaining $A_1=A_0+\Delta$ with a rank-2 update "
            + r"$\Delta=e_0e_3^\top+e_3e_0^\top$. We compare determinant packages $D(z)=\det(I-zA)$ and report the ratio "
            + r"$D_1(z)/D_0(z)$ and the logabs increment $\Delta\log|D|$. "
            + r"The ratio is also computed via the finite-rank determinant lemma (Woodbury) as a $2\times2$ determinant built from $(I-zA_0)^{-1}$.",
            r"\paragraph{Deterministic agreement on the declared grid.} \AuditTag "
            + rf"On z-grid {z_grid}, the maximum absolute discrepancy between the direct ratio and the Woodbury ratio is "
            + rf"{_fmt(max_err,6)} (at z={_fmt(arg_max[0],3)}).",
        ],
    )


if __name__ == "__main__":
    main()

