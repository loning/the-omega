# -*- coding: utf-8 -*-
"""
Ihara/Hashimoto/Bass determinant packaging + added-edge update audit (toy).

Goal:
  Provide a minimal reproducible certificate in the graph-zeta mother language:
    Z_G(u)^{-1} = det(I - u B)  (Hashimoto form, degree>=2)
              = (1-u^2)^{|E|-|V|} det(I - u A + (D-I)u^2)  (Bass form)
  and show that an added edge update G -> G' changes the same determinant packaging
  in a controlled, auditable way (report ratios).

Toy graphs:
  - base: cycle graph C6 (all degrees 2; satisfies assumptions)
  - update: add one undirected chord edge (0,3)

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.

Outputs (LaTeX fragments):
  - sections/generated/ihara_hashimoto_added_edge_rows.tex
  - sections/generated/ihara_hashimoto_added_edge_summary.tex
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


def _mat_sub(a: Matrix, b: Matrix) -> Matrix:
    p = len(a)
    q = len(a[0]) if a else 0
    return [[float(a[i][j] - b[i][j]) for j in range(q)] for i in range(p)]


def _mat_scale(a: Matrix, s: float) -> Matrix:
    p = len(a)
    q = len(a[0]) if a else 0
    return [[float(s) * float(a[i][j]) for j in range(q)] for i in range(p)]


def _mat_add(a: Matrix, b: Matrix) -> Matrix:
    p = len(a)
    q = len(a[0]) if a else 0
    return [[float(a[i][j] + b[i][j]) for j in range(q)] for i in range(p)]


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


def _cycle_graph(n: int) -> List[Tuple[int, int]]:
    edges: List[Tuple[int, int]] = []
    for i in range(n):
        edges.append((i, (i + 1) % n))
    return edges


def _add_edge(edges: List[Tuple[int, int]], i: int, j: int) -> List[Tuple[int, int]]:
    if i == j:
        raise ValueError("self-loop not allowed")
    a, b = (i, j) if i < j else (j, i)
    s = {(min(x, y), max(x, y)) for (x, y) in edges}
    s.add((a, b))
    return sorted(list(s))


def _adjacency(n: int, edges: List[Tuple[int, int]]) -> Matrix:
    A = [[0.0 for _ in range(n)] for _ in range(n)]
    for (u, v) in edges:
        A[u][v] = 1.0
        A[v][u] = 1.0
    return A


def _degree_diag(n: int, edges: List[Tuple[int, int]]) -> Matrix:
    deg = [0 for _ in range(n)]
    for (u, v) in edges:
        deg[u] += 1
        deg[v] += 1
    D = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        D[i][i] = float(deg[i])
    return D


def _oriented_edges(edges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    for (u, v) in edges:
        out.append((u, v))
        out.append((v, u))
    return out


def _hashimoto_B(n: int, edges: List[Tuple[int, int]]) -> Matrix:
    # B_{e,f}=1 if term(e)=orig(f) and f != e^{-1}
    oe = _oriented_edges(edges)
    idx: Dict[Tuple[int, int], int] = {e: k for k, e in enumerate(oe)}
    m = len(oe)
    B = [[0.0 for _ in range(m)] for _ in range(m)]
    for e in oe:
        a, b = e
        e_inv = (b, a)
        ie = idx[e]
        for f in oe:
            c, d = f
            if b == c and f != e_inv:
                B[ie][idx[f]] = 1.0
    return B


def _det_hashimoto(u: float, B: Matrix) -> float:
    m = len(B)
    return _det(_mat_sub(_eye(m), _mat_scale(B, float(u))))


def _det_bass(u: float, A: Matrix, D: Matrix, nV: int, nE: int) -> float:
    # Bass: Z^{-1}=(1-u^2)^{|E|-|V|} det(I-uA+(D-I)u^2)
    I = _eye(nV)
    DI = _mat_sub(D, I)
    M = _mat_add(_mat_sub(I, _mat_scale(A, float(u))), _mat_scale(DI, float(u * u)))
    pref = float((1.0 - u * u) ** float(nE - nV))
    return float(pref * _det(M))


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "ihara_hashimoto_added_edge_rows.tex"
    sum_path = out_dir / "ihara_hashimoto_added_edge_summary.tex"

    nV = 6
    base_edges = _cycle_graph(nV)
    edge_edges = _add_edge(base_edges, 0, 3)
    graphs = [("base", base_edges), ("edge", edge_edges)]

    u_grid = [0.05, 0.10, 0.15, 0.20]

    rows: List[str] = []
    max_rel_err = 0.0
    max_err_at = ("", 0.0)
    max_ratio_shift = 0.0

    # Precompute determinants per graph and u.
    detH: Dict[Tuple[str, float], float] = {}
    for tag, edges in graphs:
        nE = len(edges)
        A = _adjacency(nV, edges)
        D = _degree_diag(nV, edges)
        B = _hashimoto_B(nV, edges)
        for u in u_grid:
            h = _det_hashimoto(u, B)
            b = _det_bass(u, A, D, nV, nE)
            detH[(tag, u)] = float(h)
            rel = abs(float(h - b)) / max(1e-12, abs(float(h)))
            if rel > max_rel_err:
                max_rel_err = float(rel)
                max_err_at = (tag, float(u))
            rows.append(
                " & ".join(
                    [
                        tag,
                        _fmt(u, 3),
                        _fmt(h, 6),
                        _fmt(b, 6),
                        _fmt(rel, 6),
                        _fmt(float(nE), 0),
                        _fmt(float(nV), 0),
                    ]
                )
                + r" \\"
            )

    # Add ratio rows (edge/base) for Hashimoto determinant.
    for u in u_grid:
        hb = detH[("base", u)]
        he = detH[("edge", u)]
        ratio = float(he / hb) if hb != 0.0 else float("nan")
        dlogabs = float(math.log(abs(he)) - math.log(abs(hb))) if hb != 0.0 and he != 0.0 else float("nan")
        if math.isfinite(dlogabs):
            max_ratio_shift = max(max_ratio_shift, abs(float(dlogabs)))
        rows.append(
            " & ".join(
                [
                    "ratio(edge/base)",
                    _fmt(u, 3),
                    _fmt(ratio, 6),
                    _fmt(dlogabs, 6),
                    _fmt(0.0, 6),
                    _fmt(0.0, 0),
                    _fmt(0.0, 0),
                ]
            )
            + r" \\"
        )

    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])

    write_lines(
        sum_path,
        [
            r"\paragraph{Ihara/Hashimoto/Bass determinant packaging and added-edge update (toy).} \AuditTag "
            + r"We compare the Hashimoto determinant $\det(I-uB)$ to the Bass determinant form "
            + r"$(1-u^2)^{|E|-|V|}\det(I-uA+(D-I)u^2)$ on a degree-2 cycle graph $C_6$ and its added-edge (chord) update. "
            + r"We also report the added-edge ratio $\det(I-uB_{\mathrm{edge}})/\det(I-uB_{\mathrm{base}})$ and its logabs increment as a zeta/det update proxy.",
            r"\paragraph{Deterministic agreement and update magnitude.} \AuditTag "
            + rf"On u-grid {u_grid}, the maximum relative discrepancy between Hashimoto and Bass determinants is {max_rel_err:.6f} "
            + rf"(at case={max_err_at[0]}, u={max_err_at[1]:.3f}). "
            + rf"The maximum observed magnitude of $\Delta\log|\det(I-uB)|$ for the edge/base ratio is {max_ratio_shift:.6f}.",
        ],
    )


if __name__ == "__main__":
    main()

