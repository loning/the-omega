# -*- coding: utf-8 -*-
"""
Determinant phase -> unitary S-matrix -> WS delay (toy audit).

Goal:
  Close the ladder step from determinant packaging to scattering dictionary objects:
    D(z)=det(I - zA), z=r e^{i omega}
      -> phase phi(omega)=arg D(z)
      -> define a strict unitary 2x2 toy S(omega)=exp(i phi(omega)) I_2
      -> Wigner–Smith operator Q(omega)=-i S^† dS/domega
      -> Tr Q(omega)=2 * dphi/domega
  Compare 0.5 * Tr Q (finite-difference) to the resolvent-trace delay proxy tau_tr(omega)
  from the identity tau_tr = Im d/domega log D(z) = Im(-i z Tr(A(I-zA)^{-1})).

This is audit-only: it is a controlled dictionary closure, not a claim of physical S-matrices.

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.

Outputs (LaTeX fragments):
  - sections/generated/det_to_smatrix_ws_delay_rows.tex
  - sections/generated/det_to_smatrix_ws_delay_summary.tex
"""

from __future__ import annotations

import cmath
import math
from typing import List

from common_paths import generated_dir
from common_tex import write_lines

MatrixC = List[List[complex]]


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(float(x)):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


def _eye(n: int) -> MatrixC:
    return [[1.0 + 0.0j if i == j else 0.0 + 0.0j for j in range(n)] for i in range(n)]


def _mat_copy(a: MatrixC) -> MatrixC:
    return [row[:] for row in a]


def _mat_scale(a: MatrixC, s: complex) -> MatrixC:
    p = len(a)
    q = len(a[0]) if a else 0
    return [[complex(s) * complex(a[i][j]) for j in range(q)] for i in range(p)]


def _mat_add(a: MatrixC, b: MatrixC) -> MatrixC:
    p = len(a)
    q = len(a[0]) if a else 0
    return [[complex(a[i][j]) + complex(b[i][j]) for j in range(q)] for i in range(p)]


def _mat_sub(a: MatrixC, b: MatrixC) -> MatrixC:
    p = len(a)
    q = len(a[0]) if a else 0
    return [[complex(a[i][j]) - complex(b[i][j]) for j in range(q)] for i in range(p)]


def _mat_mul(a: MatrixC, b: MatrixC) -> MatrixC:
    p = len(a)
    q = len(a[0]) if a else 0
    if q == 0:
        return []
    if len(b) != q:
        raise ValueError("mat_mul: dimension mismatch")
    r = len(b[0]) if b else 0
    out: MatrixC = [[0.0 + 0.0j for _ in range(r)] for _ in range(p)]
    for i in range(p):
        for k in range(q):
            aik = complex(a[i][k])
            if aik == 0.0:
                continue
            bk = b[k]
            for j in range(r):
                out[i][j] += aik * complex(bk[j])
    return out


def _det(a: MatrixC) -> complex:
    m = _mat_copy(a)
    n = len(m)
    det = 1.0 + 0.0j
    sign = 1.0
    for k in range(n):
        piv = k
        best = abs(m[k][k])
        for i in range(k + 1, n):
            v = abs(m[i][k])
            if v > best:
                best = v
                piv = i
        if best == 0.0:
            return 0.0 + 0.0j
        if piv != k:
            m[k], m[piv] = m[piv], m[k]
            sign *= -1.0
        pivot = m[k][k]
        det *= pivot
        for i in range(k + 1, n):
            f = m[i][k] / pivot
            m[i][k] = 0.0 + 0.0j
            if f == 0.0:
                continue
            for j in range(k + 1, n):
                m[i][j] = m[i][j] - f * m[k][j]
    return complex(sign) * det


def _inv(a: MatrixC) -> MatrixC:
    n = len(a)
    aug: MatrixC = [row[:] + eye_row[:] for row, eye_row in zip(_mat_copy(a), _eye(n))]
    for k in range(n):
        piv = k
        best = abs(aug[k][k])
        for i in range(k + 1, n):
            v = abs(aug[i][k])
            if v > best:
                best = v
                piv = i
        if best == 0.0:
            raise ValueError("matrix is singular")
        if piv != k:
            aug[k], aug[piv] = aug[piv], aug[k]
        pivot = aug[k][k]
        inv_p = 1.0 / pivot
        for j in range(2 * n):
            aug[k][j] = aug[k][j] * inv_p
        for i in range(n):
            if i == k:
                continue
            f = aug[i][k]
            if f == 0.0:
                continue
            for j in range(2 * n):
                aug[i][j] = aug[i][j] - f * aug[k][j]
    return [row[n:] for row in aug]


def _trace(a: MatrixC) -> complex:
    return sum(a[i][i] for i in range(len(a)))


def _path_adjacency(n: int) -> MatrixC:
    a: MatrixC = [[0.0 + 0.0j for _ in range(n)] for _ in range(n)]
    for i in range(n - 1):
        a[i][i + 1] = 1.0 + 0.0j
        a[i + 1][i] = 1.0 + 0.0j
    return a


def _added_edge_delta(n: int, i: int, j: int) -> MatrixC:
    d: MatrixC = [[0.0 + 0.0j for _ in range(n)] for _ in range(n)]
    d[i][j] = 1.0 + 0.0j
    d[j][i] = 1.0 + 0.0j
    return d


def _phase(z: complex) -> float:
    return float(cmath.phase(z))


def _unwrap(phases: List[float]) -> List[float]:
    if not phases:
        return []
    out = [float(phases[0])]
    for p in phases[1:]:
        p = float(p)
        prev = out[-1]
        dp = p - prev
        while dp > math.pi:
            p -= 2.0 * math.pi
            dp = p - prev
        while dp < -math.pi:
            p += 2.0 * math.pi
            dp = p - prev
        out.append(float(p))
    return out


def _central_diff(xs: List[float], h: float) -> List[float]:
    n = len(xs)
    if n < 3:
        return [float("nan")] * n
    out = [float("nan")] * n
    for i in range(1, n - 1):
        out[i] = float((xs[i + 1] - xs[i - 1]) / (2.0 * float(h)))
    out[0] = out[1]
    out[-1] = out[-2]
    return out


def _tau_tr(A: MatrixC, z: complex) -> float:
    B = _mat_sub(_eye(len(A)), _mat_scale(A, z))
    Binv = _inv(B)
    tr_term = _trace(_mat_mul(A, Binv))
    return float((-1j * z * tr_term).imag)


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "det_to_smatrix_ws_delay_rows.tex"
    sum_path = out_dir / "det_to_smatrix_ws_delay_summary.tex"

    n = 6
    i, j = 0, 3
    A0 = _path_adjacency(n)
    A1 = _mat_add(A0, _added_edge_delta(n, i, j))

    r = 0.35
    domega = 0.05
    k = 41
    omegas = [domega * t for t in range(k)]
    eps_det = 1e-3

    # Build phase from D for base and updated graphs.
    phi0_raw: List[float] = []
    phi1_raw: List[float] = []
    absD0: List[float] = []
    absD1: List[float] = []
    for w in omegas:
        z = complex(r) * cmath.exp(1j * complex(w))
        D0 = _det(_mat_sub(_eye(n), _mat_scale(A0, z)))
        D1 = _det(_mat_sub(_eye(n), _mat_scale(A1, z)))
        phi0_raw.append(_phase(D0))
        phi1_raw.append(_phase(D1))
        absD0.append(float(abs(D0)))
        absD1.append(float(abs(D1)))

    phi0 = _unwrap(phi0_raw)
    phi1 = _unwrap(phi1_raw)
    phi0_p = _central_diff(phi0, domega)
    phi1_p = _central_diff(phi1, domega)

    rows: List[str] = []
    max_err0 = 0.0
    max_err1 = 0.0
    max_errd = 0.0
    n_used = 0

    for w, p0p, p1p, a0, a1 in zip(omegas, phi0_p, phi1_p, absD0, absD1):
        z = complex(r) * cmath.exp(1j * complex(w))
        tau0_tr = _tau_tr(A0, z)
        tau1_tr = _tau_tr(A1, z)
        dtau_tr = float(tau1_tr - tau0_tr)

        # Define a strict 2x2 unitary toy S(omega)=exp(i phi(omega)) I2.
        # Then Q=-i S^† dS/domega = (dphi/domega) I2 and Tr Q = 2 dphi/domega.
        tau0_ws = float(p0p) if float(a0) >= float(eps_det) else float("nan")
        tau1_ws = float(p1p) if float(a1) >= float(eps_det) else float("nan")
        dtau_ws = float(tau1_ws - tau0_ws) if math.isfinite(tau0_ws) and math.isfinite(tau1_ws) else float("nan")

        err0 = abs(float(tau0_ws) - float(tau0_tr)) if math.isfinite(tau0_ws) else float("nan")
        err1 = abs(float(tau1_ws) - float(tau1_tr)) if math.isfinite(tau1_ws) else float("nan")
        errd = abs(float(dtau_ws) - float(dtau_tr)) if math.isfinite(dtau_ws) else float("nan")

        if math.isfinite(err0):
            max_err0 = max(max_err0, float(err0))
            n_used += 1
        if math.isfinite(err1):
            max_err1 = max(max_err1, float(err1))
        if math.isfinite(errd):
            max_errd = max(max_errd, float(errd))

        rows.append(
            " & ".join(
                [
                    _fmt(float(w), 3),
                    _fmt(float(tau0_tr), 6),
                    _fmt(float(tau0_ws), 6),
                    _fmt(float(err0), 6),
                    _fmt(float(tau1_tr), 6),
                    _fmt(float(tau1_ws), 6),
                    _fmt(float(err1), 6),
                    _fmt(float(dtau_tr), 6),
                    _fmt(float(dtau_ws), 6),
                    _fmt(float(errd), 6),
                ]
            )
            + r" \\\\"
        )

    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])

    write_lines(
        sum_path,
        [
            r"\paragraph{Det phase $\Rightarrow$ unitary $S(\omega)$ and WS delay (toy).} \AuditTag "
            + r"Given a determinant package $D(r\e^{\iu\omega})=\det(I-r\e^{\iu\omega}A)$ we form the unwrapped phase "
            + r"$\phi(\omega)=\arg D(r\e^{\iu\omega})$ and define a strict $2\times2$ unitary toy "
            + r"$S(\omega)=\exp(\iu\phi(\omega))I_2$. Then the Wigner--Smith operator satisfies "
            + r"$Q(\omega)=-\iu S^\dagger \frac{\dd S}{\dd\omega}=(\dd\phi/\dd\omega)\,I_2$, hence $\tfrac12\Tr Q=\dd\phi/\dd\omega$. "
            + r"We compare this WS delay proxy to the resolvent-trace delay identity "
            + r"$\tau_{\mathrm{tr}}(\omega)=\Im(-\iu z\,\Tr(A(I-zA)^{-1}))$ with $z=r\e^{\iu\omega}$.",
            r"\paragraph{Gate and deterministic error.} \AuditTag "
            + rf"We gate phase-difference auditing by requiring $|D(r\e^{{\iu\omega}})|\ge {eps_det:g}$ and use domega={domega}. "
            + rf"Over the gated points (count={n_used}), the maximum absolute discrepancies are "
            + rf"$\max|\tau_{{0,\mathrm{{ws}}}}-\tau_{{0,\mathrm{{tr}}}}|\approx{_fmt(max_err0,6)}$, "
            + rf"$\max|\tau_{{1,\mathrm{{ws}}}}-\tau_{{1,\mathrm{{tr}}}}|\approx{_fmt(max_err1,6)}$, "
            + rf"and $\max|\Delta\tau_{{\mathrm{{ws}}}}-\Delta\tau_{{\mathrm{{tr}}}}|\approx{_fmt(max_errd,6)}$.",
        ],
    )


if __name__ == "__main__":
    main()

