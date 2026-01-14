# -*- coding: utf-8 -*-
"""
Wormhole-like shortcut as a finite-rank update: delay/logdet bookkeeping audit (toy).

This script produces a deterministic artifact demonstrating that a finite-rank update
to an operator (a "shortcut channel" in audit language) induces measurable increments
in determinant bookkeeping (logdet proxy) and in a resolvent/determinant-derived
delay proxy.

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.

Outputs (LaTeX fragments):
  - sections/generated/wormhole_finite_rank_delay_logdet_rows.tex
  - sections/generated/wormhole_finite_rank_delay_logdet_summary.tex
"""

from __future__ import annotations

import math
from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(float(x)):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


Matrix = List[List[float]]


def _eye(n: int) -> Matrix:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _mat_copy(a: Matrix) -> Matrix:
    return [row[:] for row in a]


def _mat_add(a: Matrix, b: Matrix) -> Matrix:
    n = len(a)
    return [[float(a[i][j] + b[i][j]) for j in range(n)] for i in range(n)]


def _mat_scale(a: Matrix, s: float) -> Matrix:
    n = len(a)
    return [[float(s) * float(a[i][j]) for j in range(n)] for i in range(n)]


def _mat_sub(a: Matrix, b: Matrix) -> Matrix:
    n = len(a)
    return [[float(a[i][j] - b[i][j]) for j in range(n)] for i in range(n)]


def _outer(u: List[float], v: List[float]) -> Matrix:
    n = len(u)
    if len(v) != n:
        raise ValueError("outer: length mismatch")
    return [[float(u[i] * v[j]) for j in range(n)] for i in range(n)]


def _mat_mul(a: Matrix, b: Matrix) -> Matrix:
    n = len(a)
    out = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        ai = a[i]
        for k in range(n):
            aik = float(ai[k])
            if aik == 0.0:
                continue
            bk = b[k]
            for j in range(n):
                out[i][j] += aik * float(bk[j])
    return out


def _trace(a: Matrix) -> float:
    return float(sum(float(a[i][i]) for i in range(len(a))))


def _det(a: Matrix) -> float:
    # LU with partial pivoting; returns determinant as float.
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
    # Gauss-Jordan inversion with partial pivoting.
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


def _delay_proxy(F: Matrix, r: float) -> float:
    # Determinant/resolvent delay proxy on an Abel-like parameter r:
    #   d/dr log det(I - rF) = -Tr(F (I - rF)^{-1})
    # We report tau(r) := Tr(F (I - rF)^{-1}).
    n = len(F)
    A = _mat_sub(_eye(n), _mat_scale(F, float(r)))
    Ainv = _inv(A)
    return _trace(_mat_mul(F, Ainv))


def _logabs_det_I_minus_rF(F: Matrix, r: float) -> float:
    n = len(F)
    A = _mat_sub(_eye(n), _mat_scale(F, float(r)))
    d = float(_det(A))
    return float(math.log(abs(d))) if d != 0.0 else float("inf")


def _toy_base_operator() -> Matrix:
    # A stable finite operator with spectral radius < 1 (heuristically).
    return [
        [0.22, 0.05, 0.00, 0.03],
        [0.07, 0.18, 0.04, 0.00],
        [0.01, 0.06, 0.16, 0.05],
        [0.00, 0.02, 0.08, 0.14],
    ]


def _toy_rank_one_update(alpha: float) -> Matrix:
    u = [1.0, -0.5, 0.25, -0.125]
    v = [0.6, 0.2, -0.3, 0.1]
    return _mat_scale(_outer(u, v), float(alpha))


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "wormhole_finite_rank_delay_logdet_rows.tex"
    sum_path = out_dir / "wormhole_finite_rank_delay_logdet_summary.tex"

    F0 = _toy_base_operator()
    r_grid = [0.20, 0.40, 0.60, 0.80]
    alpha_grid = [0.00, 0.10, 0.20, 0.30]

    rows: List[str] = []
    best_tau = (0.0, ("", 0.0, 0.0))
    best_log = (0.0, ("", 0.0, 0.0))

    for alpha in alpha_grid:
        dF = _toy_rank_one_update(alpha)
        F1 = _mat_add(F0, dF)
        cost = float(abs(alpha))  # declared ledger cost proxy (rank-1 amplitude)
        for r in r_grid:
            tau0 = _delay_proxy(F0, r)
            tau1 = _delay_proxy(F1, r)
            dtau = float(tau1 - tau0)

            L0 = _logabs_det_I_minus_rF(F0, r)
            L1 = _logabs_det_I_minus_rF(F1, r)
            dL = float(L1 - L0)

            if abs(dtau) > best_tau[0]:
                best_tau = (abs(dtau), ("dtau", float(alpha), float(r)))
            if abs(dL) > best_log[0]:
                best_log = (abs(dL), ("dlogabsdet", float(alpha), float(r)))

            rows.append(
                " & ".join(
                    [
                        _fmt(alpha, 3),
                        _fmt(cost, 3),
                        _fmt(r, 2),
                        _fmt(L0, 6),
                        _fmt(L1, 6),
                        _fmt(dL, 6),
                        _fmt(tau0, 6),
                        _fmt(tau1, 6),
                        _fmt(dtau, 6),
                    ]
                )
                + r" \\"
            )

    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])

    # Summarize the strongest observed increments on the declared grid.
    _, (_, a_tau, r_tau) = best_tau
    _, (_, a_log, r_log) = best_log
    dtau_star = _delay_proxy(_mat_add(F0, _toy_rank_one_update(a_tau)), r_tau) - _delay_proxy(F0, r_tau)
    dL_star = _logabs_det_I_minus_rF(_mat_add(F0, _toy_rank_one_update(a_log)), r_log) - _logabs_det_I_minus_rF(F0, r_log)

    write_lines(
        sum_path,
        [
            r"\paragraph{Finite-rank update induces logdet and delay-proxy increments (toy).} \AuditTag "
            + r"We compare a baseline finite operator $F$ to a rank-one updated operator $F+\Delta$ (``wormhole-on''), "
            + r"where the update amplitude $\alpha$ is treated as an explicit ledger-cost proxy. "
            + r"On an Abel-like parameter grid $r\in(0,1)$ we report: "
            + r"(i) a logdet bookkeeping proxy $\log|\det(I-rF)|$ and its increment, "
            + r"and (ii) a determinant/resolvent-derived delay proxy $\tau(r)=\mathrm{Tr}\,F(I-rF)^{-1}$ and its increment "
            + r"(via $\frac{\dd}{\dd r}\log\det(I-rF)=-\tau(r)$).",
            r"\paragraph{Deterministic witness on the declared grid.} \AuditTag "
            + rf"Over the fixed grid (r={r_grid}, alpha={alpha_grid}), the largest observed increments are "
            + rf"$\Delta\tau\approx {_fmt(dtau_star,6)}$ at $(\alpha,r)=({_fmt(a_tau,3)},{_fmt(r_tau,2)})$ "
            + rf"and $\Delta\log|\det|\approx {_fmt(dL_star,6)}$ at $(\alpha,r)=({_fmt(a_log,3)},{_fmt(r_log,2)})$. "
            + r"The full row table is provided in \texttt{sections/generated/wormhole\_finite\_rank\_delay\_logdet\_rows.tex}.",
        ],
    )


if __name__ == "__main__":
    main()

