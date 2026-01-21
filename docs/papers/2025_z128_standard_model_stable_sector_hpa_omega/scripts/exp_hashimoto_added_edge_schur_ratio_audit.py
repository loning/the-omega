# -*- coding: utf-8 -*-
"""
Hashimoto (non-backtracking) determinant update under added edge via Schur complement (toy).

Goal:
  When adding an undirected edge to a graph, the Hashimoto matrix B grows in dimension because
  the oriented-edge set grows. This is not a same-dimension finite-rank perturbation.
  However, with the block partition (old oriented edges | new oriented edges), one has
    det(I - u B_new) = det(I - u B_old) * det(S(u)),
  where S(u) is a small Schur complement matrix of size (#new oriented edges) x (#new oriented edges).

Toy:
  - base: cycle graph C6 (degree 2)
  - update: add chord edge (0,3), which adds exactly 2 oriented edges.
  - We compute ratio_direct := det(I-uB_new)/det(I-uB_old)
    and ratio_schur := det(S(u)) and compare.

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.

Outputs (LaTeX fragments):
  - sections/generated/hashimoto_added_edge_schur_rows.tex
  - sections/generated/hashimoto_added_edge_schur_summary.tex
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

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


def _mat_mul(a: Matrix, b: Matrix) -> Matrix:
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


def _mat_add(a: Matrix, b: Matrix) -> Matrix:
    p = len(a)
    q = len(a[0]) if a else 0
    return [[float(a[i][j] + b[i][j]) for j in range(q)] for i in range(p)]


def _mat_sub(a: Matrix, b: Matrix) -> Matrix:
    p = len(a)
    q = len(a[0]) if a else 0
    return [[float(a[i][j] - b[i][j]) for j in range(q)] for i in range(p)]


def _mat_scale(a: Matrix, s: float) -> Matrix:
    p = len(a)
    q = len(a[0]) if a else 0
    return [[float(s) * float(a[i][j]) for j in range(q)] for i in range(p)]


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
    aug = [row[:] + eye_row[:] for row, eye_row in zip(_mat_copy(a), _eye(n))]
    for k in range(n):
        piv = k
        best = abs(float(aug[k][k]))
        for i in range(k + 1, n):
            v = abs(float(aug[i][k]))
            if v > best:
                best = v
                piv = i
        if best == 0.0:
            raise ValueError("matrix is singular")
        if piv != k:
            aug[k], aug[piv] = aug[piv], aug[k]
        pivot = float(aug[k][k])
        inv_p = 1.0 / pivot
        for j in range(2 * n):
            aug[k][j] = float(aug[k][j]) * inv_p
        for i in range(n):
            if i == k:
                continue
            f = float(aug[i][k])
            if f == 0.0:
                continue
            for j in range(2 * n):
                aug[i][j] = float(aug[i][j]) - f * float(aug[k][j])
    return [row[n:] for row in aug]


def _cycle_edges(n: int) -> List[Tuple[int, int]]:
    return [(i, (i + 1) % n) for i in range(n)]


def _add_edge(edges: List[Tuple[int, int]], i: int, j: int) -> List[Tuple[int, int]]:
    a, b = (i, j) if i < j else (j, i)
    s = {(min(x, y), max(x, y)) for (x, y) in edges}
    s.add((a, b))
    return sorted(list(s))


def _oriented_edges(edges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    for (u, v) in edges:
        out.append((u, v))
        out.append((v, u))
    return out


def _hashimoto_B(oriented: List[Tuple[int, int]]) -> Matrix:
    idx: Dict[Tuple[int, int], int] = {e: k for k, e in enumerate(oriented)}
    m = len(oriented)
    B = [[0.0 for _ in range(m)] for _ in range(m)]
    for e in oriented:
        a, b = e
        e_inv = (b, a)
        ie = idx[e]
        for f in oriented:
            c, d = f
            if b == c and f != e_inv:
                B[ie][idx[f]] = 1.0
    return B


def _submatrix(B: Matrix, rows: List[int], cols: List[int]) -> Matrix:
    return [[float(B[i][j]) for j in cols] for i in rows]


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "hashimoto_added_edge_schur_rows.tex"
    sum_path = out_dir / "hashimoto_added_edge_schur_summary.tex"

    nV = 6
    base_edges = _cycle_edges(nV)
    edge_edges = _add_edge(base_edges, 0, 3)

    oriented_old = _oriented_edges(base_edges)
    oriented_new = _oriented_edges(edge_edges)

    # Ensure old oriented edges appear first, then new-only edges.
    old_set = set(oriented_old)
    new_only = [e for e in oriented_new if e not in old_set]
    oriented_order = oriented_old + new_only
    k_new = len(new_only)
    if k_new != 2:
        raise RuntimeError("expected exactly 2 new oriented edges in this toy")

    B_old = _hashimoto_B(oriented_old)
    B_new = _hashimoto_B(oriented_order)

    m_old = len(oriented_old)
    m_new = len(oriented_order)
    if m_new != m_old + k_new:
        raise RuntimeError("dimension mismatch in block partition")

    # Block partition indices.
    I_old = list(range(m_old))
    I_new = list(range(m_old, m_new))
    B_oo = _submatrix(B_new, I_old, I_old)
    B_on = _submatrix(B_new, I_old, I_new)
    B_no = _submatrix(B_new, I_new, I_old)
    B_nn = _submatrix(B_new, I_new, I_new)

    # Sanity: B_oo should equal B_old exactly for this update.
    # (Old-old transitions unaffected; only additional transitions to/from new edges.)
    for i in range(m_old):
        for j in range(m_old):
            if float(B_oo[i][j]) != float(B_old[i][j]):
                raise RuntimeError("B_oo differs from B_old; ordering assumption violated")

    u_grid = [0.05, 0.10, 0.15, 0.20]
    rows: List[str] = []
    max_err = 0.0
    max_at = 0.0

    for u in u_grid:
        Ioo = _eye(m_old)
        Inn = _eye(k_new)
        Aoo = _mat_sub(Ioo, _mat_scale(B_oo, float(u)))
        Ann = _mat_sub(Inn, _mat_scale(B_nn, float(u)))
        Aon = _mat_scale(B_on, float(-u))
        Ano = _mat_scale(B_no, float(-u))

        det_old = _det(Aoo)
        det_new = _det(_mat_sub(_eye(m_new), _mat_scale(B_new, float(u))))
        ratio_direct = float(det_new / det_old) if det_old != 0.0 else float("nan")

        # Schur complement: det([[Aoo,Aon],[Ano,Ann]]) = det(Aoo) det(Ann - Ano Aoo^{-1} Aon)
        Aoo_inv = _inv(Aoo)
        correction = _mat_mul(_mat_mul(Ano, Aoo_inv), Aon)  # (k x k)
        Schur = _mat_sub(Ann, correction)
        ratio_schur = _det(Schur)

        err = abs(float(ratio_direct) - float(ratio_schur)) if math.isfinite(ratio_direct) else float("nan")
        if math.isfinite(err) and err > max_err:
            max_err = float(err)
            max_at = float(u)

        rows.append(
            " & ".join(
                [
                    _fmt(u, 3),
                    _fmt(det_old, 6),
                    _fmt(det_new, 6),
                    _fmt(ratio_direct, 6),
                    _fmt(ratio_schur, 6),
                    _fmt(err, 6),
                    str(int(k_new)),
                    str(int(m_old)),
                ]
            )
            + r" \\"
        )

    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])

    write_lines(
        sum_path,
        [
            r"\paragraph{Added-edge update ratio via Schur complement (Hashimoto determinant).} \AuditTag "
            + r"Adding one undirected edge increases the oriented-edge space, so the Hashimoto matrix $B$ grows in dimension. "
            + r"With the block split (old oriented edges | new oriented edges), the block determinant identity yields "
            + r"$\det(I-uB_{\mathrm{new}})=\det(I-uB_{\mathrm{old}})\det(S(u))$ where $S(u)$ is a $k\times k$ Schur complement "
            + r"with $k=2$ in this toy. We compare the direct ratio to $\det(S(u))$ on a declared $u$ grid.",
            r"\paragraph{Deterministic agreement.} \AuditTag "
            + rf"On u-grid {u_grid}, the maximum absolute discrepancy is {max_err:.6f} (at u={max_at:.3f}).",
        ],
    )


if __name__ == "__main__":
    main()

