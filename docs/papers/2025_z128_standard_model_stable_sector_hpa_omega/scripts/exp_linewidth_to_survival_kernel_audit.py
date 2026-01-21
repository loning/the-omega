# -*- coding: utf-8 -*-
"""
Linewidth -> lifetime -> survival kernel audit (toy).

Goal:
  Close the ladder segment "decay/evaporation as exit from tick traps" by making the
  linewidth vocabulary compatible with the leakage-kernel dictionary:
    Gamma (width / exit-rate proxy) -> tau=1/Gamma (lifetime proxy) -> P(t)=exp(-Gamma t).

We reuse the same determinant/resolvent delay carrier as the det-delay linewidth audit:
  tau(omega)=Im(-i z Tr(A(I-zA)^{-1})), z=r e^{i omega},
extract a peak and a linewidth proxy (Gamma_FWHM) and Gamma_tau=4/tau_max,
then report the implied lifetime proxies and survival values at declared times.

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.

Outputs (LaTeX fragments):
  - sections/generated/linewidth_survival_kernel_rows.tex
  - sections/generated/linewidth_survival_kernel_summary.tex
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
    peak = float(taus[i0])
    if not math.isfinite(peak) or peak <= 0.0:
        return float("nan")
    half = 0.5 * peak
    il = i0
    while il > 0 and float(taus[il]) >= half:
        il -= 1
    ir = i0
    while ir < len(taus) - 1 and float(taus[ir]) >= half:
        ir += 1
    if il == i0 or ir == i0:
        return float("nan")

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


def _survival_exp(gamma: float, t: float) -> float:
    g = float(gamma)
    if g < 0.0:
        return float("nan")
    return float(math.exp(-g * float(t)))


def _extract_top_peak_gamma(A: MatrixC, *, r: float, domega: float) -> Tuple[float, float, float]:
    omega_min = 0.0
    omega_max = 2.0 * math.pi
    k = int(round((omega_max - omega_min) / domega)) + 1
    omegas = [omega_min + domega * t for t in range(k)]
    taus: List[float] = []
    for w in omegas:
        z = complex(r) * cmath.exp(1j * complex(w))
        taus.append(_tau_tr(A, z))
    peaks = [p for p in _find_peaks(taus) if float(taus[p]) > 0.0]
    if not peaks:
        return float("nan"), float("nan"), float("nan")
    peaks.sort(key=lambda idx: float(taus[idx]), reverse=True)
    idx0 = peaks[0]
    tau_max = float(taus[idx0])
    gamma_tau = float(4.0 / tau_max) if tau_max > 0.0 else float("nan")
    gamma_fwhm = float(_halfwidth(omegas, taus, idx0))
    return tau_max, gamma_tau, gamma_fwhm


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "linewidth_survival_kernel_rows.tex"
    sum_path = out_dir / "linewidth_survival_kernel_summary.tex"

    n = 6
    i, j = 0, 3
    r = 0.35
    domega = 0.01
    times = [0.25, 0.50, 1.00]

    A0 = _path_adjacency(n)
    A1 = _mat_add(A0, _added_edge_delta(n, i, j))

    rows: List[str] = []
    for tag, A in [("base", A0), ("edge", A1)]:
        tau_max, gamma_tau, gamma_fwhm = _extract_top_peak_gamma(A, r=r, domega=domega)
        tau_tau = float(1.0 / gamma_tau) if gamma_tau > 0.0 else float("nan")
        tau_fwhm = float(1.0 / gamma_fwhm) if gamma_fwhm > 0.0 else float("nan")
        for t in times:
            P_tau = _survival_exp(gamma_tau, t) if math.isfinite(gamma_tau) else float("nan")
            P_fwhm = _survival_exp(gamma_fwhm, t) if math.isfinite(gamma_fwhm) else float("nan")
            rows.append(
                " & ".join(
                    [
                        tag,
                        _fmt(r, 3),
                        _fmt(tau_max, 6),
                        _fmt(gamma_tau, 6),
                        _fmt(gamma_fwhm, 6),
                        _fmt(tau_tau, 6),
                        _fmt(tau_fwhm, 6),
                        _fmt(float(t), 3),
                        _fmt(P_tau, 6),
                        _fmt(P_fwhm, 6),
                    ]
                )
                + r" \\\\"
            )
    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])

    write_lines(
        sum_path,
        [
            r"\paragraph{Linewidth $\Gamma$ to survival kernel (toy).} \AuditTag "
            + r"We map the linewidth vocabulary to the leakage-kernel dictionary by treating a width proxy $\Gamma$ as an exit-rate proxy "
            + r"and defining the exponential survival law $P(t)=\exp(-\Gamma t)$ with lifetime proxy $\tau=1/\Gamma$. "
            + r"Here $\Gamma$ is extracted from the determinant/resolvent delay carrier by two auditable proxies: "
            + r"$\Gamma_\tau=4/\tau_{\max}$ (Breit--Wigner benchmark) and $\Gamma_{\mathrm{FWHM}}$ (half-maximum width). "
            + r"The table reports both along with the implied survival values on declared times.",
            r"\paragraph{Determinism.} \AuditTag "
            + rf"Parameters are fixed (n={n}, added edge ({i},{j}), r={_fmt(r,3)}, omega step {domega}, times={times}).",
        ],
    )


if __name__ == "__main__":
    main()

