# -*- coding: utf-8 -*-
"""
Determinant packaging -> phase -> delay (scattering proxy) audit (toy).

Goal:
  Extend the equivalence ladder by an auditable frequency-domain proxy:
    det packaging D(z)=det(I - zA)
      -> phase phi(omega)=arg D(r e^{i omega})
      -> scalar unitary S(omega)=exp(i phi(omega))
      -> delay proxy tau(omega)=d phi / d omega = Im d/domega log D(...)

This is audit-only: it records a deterministic proxy mapping (not a claim of 4D QFT scattering).
We use a fixed finite graph adjacency A and compare base vs added-edge update.

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.

Outputs (LaTeX fragments):
  - sections/generated/det_phase_delay_proxy_rows.tex
  - sections/generated/det_phase_delay_proxy_summary.tex
  - sections/generated/det_phase_delay_trace_identity_rows.tex
  - sections/generated/det_phase_delay_trace_identity_summary.tex
"""

from __future__ import annotations

import cmath
import math
from typing import List, Tuple

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
    n = len(a)
    return [[complex(s) * complex(a[i][j]) for j in range(len(a[0]))] for i in range(n)]


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


def _path_adjacency(n: int) -> MatrixC:
    a: MatrixC = [[0.0 + 0.0j for _ in range(n)] for _ in range(n)]
    for i in range(n - 1):
        a[i][i + 1] = 1.0 + 0.0j
        a[i + 1][i] = 1.0 + 0.0j
    return a


def _added_edge_delta(n: int, i: int, j: int) -> MatrixC:
    if i == j:
        raise ValueError("self-loop not supported in this toy")
    d: MatrixC = [[0.0 + 0.0j for _ in range(n)] for _ in range(n)]
    d[i][j] = 1.0 + 0.0j
    d[j][i] = 1.0 + 0.0j
    return d


def _det(a: MatrixC) -> complex:
    # LU with partial pivoting for complex matrices.
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
    # Gauss-Jordan inversion with partial pivoting (complex).
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


def _tau_trace(A: MatrixC, z: complex) -> float:
    # D(z)=det(I-zA). Identity:
    #   d/dz log D(z) = -Tr(A (I-zA)^{-1})
    # For z=r e^{iω}, dz/dω = i z, hence
    #   d/dω log D(z(ω)) = -i z Tr(A (I-zA)^{-1}).
    # The phase derivative is tau(ω) = Im d/dω log D.
    B = _mat_sub(_eye(len(A)), _mat_scale(A, z))
    Binv = _inv(B)
    tr_term = _trace(_mat_mul(A, Binv))
    return float((-1j * z * tr_term).imag)


def _phase(z: complex) -> float:
    # principal value in (-pi, pi]
    return float(cmath.phase(z))


def _unwrap(phases: List[float]) -> List[float]:
    # simple phase unwrapping along the list
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


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "det_phase_delay_proxy_rows.tex"
    sum_path = out_dir / "det_phase_delay_proxy_summary.tex"
    id_rows_path = out_dir / "det_phase_delay_trace_identity_rows.tex"
    id_sum_path = out_dir / "det_phase_delay_trace_identity_summary.tex"

    n = 6
    i, j = 0, 3
    A0 = _path_adjacency(n)
    A1 = _mat_add(A0, _added_edge_delta(n, i, j))

    # Choose parameters away from determinant zeros to keep phase-difference auditing stable.
    r = 0.35  # Abel-like radius inside unit disk
    omega0 = 0.0
    domega = 0.05
    k = 41  # number of points
    omegas = [omega0 + domega * t for t in range(k)]
    eps_det = 1e-3  # gate for phase-difference stability: ignore points with |D| too small

    # Compute phases (and magnitudes) of D(r e^{i omega}) for base and updated graphs.
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
    dphi0 = _central_diff(phi0, domega)
    dphi1 = _central_diff(phi1, domega)

    rows: List[str] = []
    id_rows: List[str] = []
    max_dtau = 0.0
    max_dphi = 0.0
    max_id_err0 = 0.0
    max_id_err1 = 0.0
    max_id_errd = 0.0
    for w, p0, p1, t0, t1, a0, a1 in zip(omegas, phi0, phi1, dphi0, dphi1, absD0, absD1):
        dphi = float(p1 - p0)
        dtau = float(t1 - t0)
        max_dphi = max(max_dphi, abs(dphi))
        max_dtau = max(max_dtau, abs(dtau))
        z = complex(r) * cmath.exp(1j * complex(w))
        tau0_tr = _tau_trace(A0, z)
        tau1_tr = _tau_trace(A1, z)
        # Gate phase-difference auditing: near zeros of D the phase is ill-conditioned and finite differences blow up.
        t0_fd = float(t0) if float(a0) >= float(eps_det) else float("nan")
        t1_fd = float(t1) if float(a1) >= float(eps_det) else float("nan")
        err0 = abs(t0_fd - float(tau0_tr)) if math.isfinite(t0_fd) else float("nan")
        err1 = abs(t1_fd - float(tau1_tr)) if math.isfinite(t1_fd) else float("nan")
        dtau_fd = float(dtau) if math.isfinite(t0_fd) and math.isfinite(t1_fd) else float("nan")
        errd = abs(dtau_fd - float(tau1_tr - tau0_tr)) if math.isfinite(dtau_fd) else float("nan")
        if math.isfinite(err0):
            max_id_err0 = max(max_id_err0, float(err0))
        if math.isfinite(err1):
            max_id_err1 = max(max_id_err1, float(err1))
        if math.isfinite(errd):
            max_id_errd = max(max_id_errd, float(errd))
        rows.append(
            " & ".join(
                [
                    str(n),
                    f"({i},{j})",
                    _fmt(r, 3),
                    _fmt(float(w), 3),
                    _fmt(float(p0), 6),
                    _fmt(float(p1), 6),
                    _fmt(float(dphi), 6),
                    _fmt(float(t0), 6),
                    _fmt(float(t1), 6),
                    _fmt(float(dtau), 6),
                ]
            )
            + r" \\\\"
        )
        id_rows.append(
            " & ".join(
                [
                    _fmt(float(w), 3),
                    _fmt(float(t0_fd), 6),
                    _fmt(float(tau0_tr), 6),
                    _fmt(float(err0), 6),
                    _fmt(float(t1_fd), 6),
                    _fmt(float(tau1_tr), 6),
                    _fmt(float(err1), 6),
                    _fmt(float(dtau_fd), 6),
                    _fmt(float(tau1_tr - tau0_tr), 6),
                    _fmt(float(errd), 6),
                ]
            )
            + r" \\\\"
        )

    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])

    id_rows.append(r"\bottomrule")
    write_lines(id_rows_path, id_rows if id_rows else ["% (no rows)"])

    write_lines(
        sum_path,
        [
            r"\paragraph{Determinant packaging $\Rightarrow$ scalar phase and delay proxy (toy).} \AuditTag "
            + r"For a fixed finite graph adjacency $A$ we define the determinant package $D(z)=\det(I-zA)$. "
            + r"On a fixed Abel-like radius $r<1$ we sample $z=r\e^{\iu\omega}$ and take the phase "
            + r"$\phi(\omega)=\arg D(r\e^{\iu\omega})$. This induces a scalar unitary proxy "
            + r"$S(\omega)=\exp(\iu\phi(\omega))$, whose delay proxy is $\tau(\omega)=\dd\phi/\dd\omega$. "
            + r"We compare base vs added-edge update and report the increments $\Delta\phi$ and $\Delta\tau$ on a declared grid.",
            r"\paragraph{Deterministic grid witness.} \AuditTag "
            + rf"With n={n}, added edge ({i},{j}), r={_fmt(r,3)}, omega-grid size k={k} with step {domega}, "
            + rf"the maximal observed magnitudes are $\max|\Delta\phi|\approx{_fmt(max_dphi,6)}$ and $\max|\Delta\tau|\approx{_fmt(max_dtau,6)}$.",
        ],
    )

    write_lines(
        id_sum_path,
        [
            r"\paragraph{Trace identity audit: phase-derivative delay vs resolvent-trace formula.} \AuditTag "
            + r"For $D(z)=\det(I-zA)$ one has $\frac{\dd}{\dd z}\log D(z)=-\Tr(A(I-zA)^{-1})$. "
            + r"On $z=r\e^{\iu\omega}$ this yields the phase-derivative delay proxy "
            + r"$\tau(\omega)=\Im\frac{\dd}{\dd\omega}\log D(r\e^{\iu\omega})=\Im\bigl(-\iu z\,\Tr(A(I-zA)^{-1})\bigr)$. "
            + r"We compare this trace formula to the finite-difference estimate from the unwrapped phase on the same declared grid.",
            r"\paragraph{Deterministic error on the declared grid.} \AuditTag "
            + rf"With r={_fmt(r,3)} and domega={domega}, we gate phase-difference auditing by requiring "
            + rf"$|D(r\e^{{\iu\omega}})|\ge {eps_det:g}$. Over the remaining points, the maximum absolute discrepancies are "
            + rf"$\max|\tau_{{0,\mathrm{{fd}}}}-\tau_{{0,\mathrm{{tr}}}}|\approx{_fmt(max_id_err0,6)}$, "
            + rf"$\max|\tau_{{1,\mathrm{{fd}}}}-\tau_{{1,\mathrm{{tr}}}}|\approx{_fmt(max_id_err1,6)}$, "
            + rf"and $\max|\Delta\tau_{{\mathrm{{fd}}}}-\Delta\tau_{{\mathrm{{tr}}}}|\approx{_fmt(max_id_errd,6)}$.",
        ],
    )


if __name__ == "__main__":
    main()

