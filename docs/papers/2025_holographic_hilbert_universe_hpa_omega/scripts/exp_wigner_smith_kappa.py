# -*- coding: utf-8 -*-
"""
Wigner--Smith time-delay matrix and an overhead proxy (standard-library only).

Given a unitary scattering matrix S(E), define:
  Q(E) = -i S(E)^† dS/dE
  tau_WS(E) = Tr Q(E)
  kappa_WS(E) = tau_WS(E) / tau0.

This script provides a finite-difference approximation and a small toy example.
Users can replace the toy S(E) with a model or experimental S(E).
"""

from __future__ import annotations

import cmath
import math
from pathlib import Path
from typing import Callable


Matrix = list[list[complex]]
Scattering = complex | Matrix


def _is_matrix(S: Scattering) -> bool:
    return isinstance(S, list)


def conj_transpose(A: Matrix) -> Matrix:
    n = len(A)
    if n == 0:
        raise ValueError("Empty matrix.")
    m = len(A[0])
    if any(len(row) != m for row in A):
        raise ValueError("Ragged matrix.")
    return [[A[i][j].conjugate() for i in range(n)] for j in range(m)]


def matmul(A: Matrix, B: Matrix) -> Matrix:
    n = len(A)
    if n == 0:
        raise ValueError("Empty matrix.")
    k = len(A[0])
    if any(len(row) != k for row in A):
        raise ValueError("Ragged matrix A.")
    if len(B) == 0:
        raise ValueError("Empty matrix B.")
    m = len(B[0])
    if any(len(row) != m for row in B):
        raise ValueError("Ragged matrix B.")
    if len(B) != k:
        raise ValueError("Incompatible shapes for matmul.")

    out: Matrix = [[0j for _ in range(m)] for _ in range(n)]
    for i in range(n):
        for j in range(m):
            s = 0j
            for t in range(k):
                s += A[i][t] * B[t][j]
            out[i][j] = s
    return out


def trace(A: Matrix) -> complex:
    n = len(A)
    if n == 0:
        raise ValueError("Empty matrix.")
    if any(len(row) != len(A[0]) for row in A):
        raise ValueError("Ragged matrix.")
    m = len(A[0])
    if n != m:
        raise ValueError("Trace requires a square matrix.")
    return sum(A[i][i] for i in range(n))


def wigner_smith_Q(Sm: Scattering, Sp: Scattering, dE: float) -> Scattering:
    """
    Central finite-difference approximation of Q(E) using S(E-dE) and S(E+dE).
    """
    if dE == 0:
        raise ValueError("dE must be nonzero.")

    if not _is_matrix(Sm) and not _is_matrix(Sp):
        dS = (Sp - Sm) / (2.0 * dE)
        S_mid = 0.5 * (Sp + Sm)
        return -1j * (S_mid.conjugate() * dS)

    if not _is_matrix(Sm) or not _is_matrix(Sp):
        raise ValueError("Sm and Sp must have the same representation (both scalar or both matrix).")

    dS: Matrix = [[(Sp[i][j] - Sm[i][j]) / (2.0 * dE) for j in range(len(Sp[0]))] for i in range(len(Sp))]
    S_mid: Matrix = [[0.5 * (Sp[i][j] + Sm[i][j]) for j in range(len(Sp[0]))] for i in range(len(Sp))]
    return [[(-1j) * z for z in row] for row in matmul(conj_transpose(S_mid), dS)]


def tau_ws_from_S(Sm: Scattering, Sp: Scattering, dE: float) -> float:
    Q = wigner_smith_Q(Sm, Sp, dE)
    if _is_matrix(Q):
        return float(trace(Q).real)
    return float(Q.real)


def toy_S_breit_wigner(E: float, *, E0: float = 1.0, gamma: float = 0.2) -> complex:
    """
    A 1-channel unitary Breit--Wigner resonance model:
      S(E) = (E - E0 - i gamma/2) / (E - E0 + i gamma/2).
    """
    z = (E - E0) + 0.5j * gamma
    return ((E - E0) - 0.5j * gamma) / z


def linspace(a: float, b: float, n: int) -> list[float]:
    if n < 2:
        raise ValueError("n must be >= 2.")
    step = (b - a) / float(n - 1)
    return [a + i * step for i in range(n)]


def sample_tau_ws(S: Callable[[float], Scattering], energies: list[float]) -> list[float | None]:
    """
    Compute tau_WS(E) for interior points using central differences.
    Endpoints are returned as None.
    """
    if len(energies) < 3:
        raise ValueError("Need at least 3 energy points.")

    S_list = [S(float(E)) for E in energies]
    taus: list[float | None] = [None for _ in energies]

    # Scalar 1-channel case: compute tau_WS as a phase derivative with unwrapping to
    # avoid branch-cut artifacts at resonant phase jumps.
    if not _is_matrix(S_list[0]):
        phases = [cmath.phase(z) for z in S_list]  # principal values in (-pi, pi]
        unwrapped: list[float] = [phases[0]]
        for i in range(1, len(phases)):
            p = phases[i]
            prev = unwrapped[-1]
            delta = p - prev
            while delta > math.pi:
                p -= 2.0 * math.pi
                delta = p - prev
            while delta < -math.pi:
                p += 2.0 * math.pi
                delta = p - prev
            unwrapped.append(p)

        for i in range(1, len(energies) - 1):
            dE = energies[i + 1] - energies[i - 1]
            taus[i] = (unwrapped[i + 1] - unwrapped[i - 1]) / dE
        return taus

    for i in range(1, len(energies) - 1):
        dE = energies[i + 1] - energies[i - 1]
        taus[i] = tau_ws_from_S(S_list[i - 1], S_list[i + 1], dE)
    return taus


def main() -> None:
    energies = linspace(0.0, 2.0, 17)
    tau0 = 1.0

    taus = sample_tau_ws(toy_S_breit_wigner, energies)
    kappas: list[float | None] = [None if t is None else (t / tau0) for t in taus]

    rows = []
    for E, tau, kappa in zip(energies, taus, kappas):
        if tau is None or kappa is None:
            continue
        rows.append(f"{E:.3f} & {tau:.6f} & {kappa:.6f} \\\\")

    # Write LaTeX rows into sections/generated/.
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "wigner_smith_rows.tex"
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    print("E\ttau_WS(E)\tkappa_WS(E)")
    for E, tau, kappa in zip(energies, taus, kappas):
        if tau is None or kappa is None:
            continue
        print(f"{E:.3f}\t{tau:.6f}\t{kappa:.6f}")
    print("Wrote sections/generated/wigner_smith_rows.tex")


if __name__ == "__main__":
    main()


