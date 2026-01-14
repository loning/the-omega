# -*- coding: utf-8 -*-
"""
Det/resolvent delay resonance -> linewidth (Gamma) audit (toy).

Goal:
  Provide an auditable, frequency-domain certificate that aligns:
    det packaging D(z)=det(I - zA), z=r e^{i omega}
      -> delay proxy tau_tr(omega)=Im(-i z Tr(A(I-zA)^{-1}))
      -> resonance peaks in tau_tr(omega)
      -> linewidth proxy Gamma via half-maximum width
      -> consistency check with Breit-Wigner benchmark: tau_max ~ 4/Gamma

This is audit-only: a finite-window proxy mapping (not physical scattering derivation).
We compare base vs added-edge update on a fixed finite graph adjacency A.

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.

Outputs (LaTeX fragments):
  - sections/generated/det_delay_linewidth_rows.tex
  - sections/generated/det_delay_linewidth_summary.tex
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


def _tau_tr(A: MatrixC, z: complex) -> float:
    B = _mat_sub(_eye(len(A)), _mat_scale(A, z))
    Binv = _inv(B)
    tr_term = _trace(_mat_mul(A, Binv))
    return float((-1j * z * tr_term).imag)


def _find_peaks(xs: List[float]) -> List[int]:
    idx: List[int] = []
    for i in range(1, len(xs) - 1):
        if xs[i] > xs[i - 1] and xs[i] >= xs[i + 1]:
            idx.append(i)
    return idx


def _halfwidth(omegas: List[float], taus: List[float], i0: int) -> float:
    # Return full width at half maximum (FWHM) around a peak i0.
    peak = float(taus[i0])
    if not math.isfinite(peak) or peak <= 0.0:
        return float("nan")
    half = 0.5 * peak
    # left
    il = i0
    while il > 0 and float(taus[il]) >= half:
        il -= 1
    # right
    ir = i0
    while ir < len(taus) - 1 and float(taus[ir]) >= half:
        ir += 1
    if il == i0 or ir == i0:
        return float("nan")
    # linear interpolate crossing points
    def _interp(i_a: int, i_b: int) -> float:
        wa, wb = float(omegas[i_a]), float(omegas[i_b])
        ta, tb = float(taus[i_a]), float(taus[i_b])
        if tb == ta:
            return wa
        t = (half - ta) / (tb - ta)
        return wa + t * (wb - wa)

    w_left = _interp(il, il + 1)
    w_right = _interp(ir, ir - 1)
    return float(w_right - w_left)


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "det_delay_linewidth_rows.tex"
    sum_path = out_dir / "det_delay_linewidth_summary.tex"

    n = 6
    i, j = 0, 3
    A0 = _path_adjacency(n)
    A1 = _mat_add(A0, _added_edge_delta(n, i, j))

    r = 0.35
    omega_min = 0.0
    omega_max = 2.0 * math.pi
    domega = 0.01
    k = int(round((omega_max - omega_min) / domega)) + 1
    omegas = [omega_min + domega * t for t in range(k)]

    # compute tau curves
    tau0: List[float] = []
    tau1: List[float] = []
    for w in omegas:
        z = complex(r) * cmath.exp(1j * complex(w))
        tau0.append(_tau_tr(A0, z))
        tau1.append(_tau_tr(A1, z))

    # pick top peaks by height (positive peaks only)
    peaks0 = [p for p in _find_peaks(tau0) if float(tau0[p]) > 0.0]
    peaks1 = [p for p in _find_peaks(tau1) if float(tau1[p]) > 0.0]
    peaks0.sort(key=lambda idx: float(tau0[idx]), reverse=True)
    peaks1.sort(key=lambda idx: float(tau1[idx]), reverse=True)
    top = 3
    peaks0 = peaks0[:top]
    peaks1 = peaks1[:top]

    rows: List[str] = []
    def _emit_rows(tag: str, peaks: List[int], taus: List[float]) -> None:
        for rank, idx in enumerate(peaks, start=1):
            w0 = float(omegas[idx])
            tmax = float(taus[idx])
            gamma_from_tau = float(4.0 / tmax) if tmax > 0.0 else float("nan")
            fwhm = _halfwidth(omegas, taus, idx)
            gamma_from_half = float(fwhm)
            mismatch = abs(float(gamma_from_half) - float(gamma_from_tau)) if math.isfinite(gamma_from_half) and math.isfinite(gamma_from_tau) else float("nan")
            rows.append(
                " & ".join(
                    [
                        tag,
                        str(int(rank)),
                        _fmt(r, 3),
                        _fmt(w0, 6),
                        _fmt(tmax, 6),
                        _fmt(gamma_from_tau, 6),
                        _fmt(gamma_from_half, 6),
                        _fmt(mismatch, 6),
                    ]
                )
                + r" \\\\"
            )

    _emit_rows("base", peaks0, tau0)
    _emit_rows("edge", peaks1, tau1)
    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])

    write_lines(
        sum_path,
        [
            r"\paragraph{Resonance linewidth proxy from determinant/resolvent delay (toy).} \AuditTag "
            + r"Using the resolvent-trace delay proxy $\tau(\omega)=\Im(-\iu z\,\Tr(A(I-zA)^{-1}))$ at $z=r\e^{\iu\omega}$, "
            + r"we detect the highest positive peaks and extract a full width at half maximum (FWHM) as a linewidth proxy $\Gamma_{\mathrm{FWHM}}$. "
            + r"We also report the Breit--Wigner consistency proxy $\Gamma_{\tau}:=4/\tau_{\max}$ and their mismatch. "
            + r"This is an audit-only finite-window certificate aligning det packaging, phase-delay readouts, and linewidth vocabulary.",
            r"\paragraph{Determinism.} \AuditTag "
            + rf"Parameters are fixed (n={n}, added edge ({i},{j}), r={_fmt(r,3)}, omega in [0,2pi] with step {domega}). "
            + r"Only the top 3 positive peaks are reported for each case (base vs added-edge).",
        ],
    )


if __name__ == "__main__":
    main()

