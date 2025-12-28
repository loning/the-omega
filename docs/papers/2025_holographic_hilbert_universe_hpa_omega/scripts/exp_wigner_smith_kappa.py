# -*- coding: utf-8 -*-
"""
Wigner--Smith time-delay matrix and an overhead proxy (standard-library only).

Given a unitary scattering matrix S(E), define:
  Q(E) = -i S(E)^dagger dS/dE
  tau_WS(E) = Tr Q(E)
  kappa_WS(E) = tau_WS(E) / tau0.

This script provides a finite-difference approximation and a small toy example.
Users can replace the toy S(E) with a model or experimental S(E).
"""

from __future__ import annotations

import argparse
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


def moving_average(values: list[float], window: int) -> list[float]:
    if window <= 1:
        return list(values)
    if window % 2 == 0:
        raise ValueError("Smoothing window must be odd.")
    n = len(values)
    half = window // 2
    out: list[float] = []
    for i in range(n):
        a = max(0, i - half)
        b = min(n, i + half + 1)
        out.append(sum(values[a:b]) / float(b - a))
    return out


def sample_tau_ws_from_scalar_samples(
    energies: list[float],
    S_list: list[complex],
    *,
    smooth_window: int = 1,
) -> list[float | None]:
    """
    Compute tau_WS(E) from sampled 1-channel complex S(E) values.
    Uses phase unwrapping and central differences; optional smoothing is applied
    to the unwrapped phase before differentiating.
    """
    if len(energies) != len(S_list):
        raise ValueError("energies and S_list must have the same length.")
    if len(energies) < 3:
        raise ValueError("Need at least 3 sample points.")

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

    unwrapped = moving_average(unwrapped, window=smooth_window)

    taus: list[float | None] = [None for _ in energies]
    for i in range(1, len(energies) - 1):
        dE = energies[i + 1] - energies[i - 1]
        if dE == 0.0:
            raise ValueError("Repeated energy value encountered.")
        taus[i] = (unwrapped[i + 1] - unwrapped[i - 1]) / dE
    return taus


def load_scalar_S_data(path: str) -> tuple[list[float], list[complex]]:
    """
    Load sampled 1-channel scattering data from a text file.

    Supported formats (whitespace or comma separated, comments start with '#'):
      - E  phase_radians
      - E  Re(S)  Im(S)
    """
    energies: list[float] = []
    values: list[complex] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.replace(",", " ").split()
            if len(parts) == 2:
                E = float(parts[0])
                phase = float(parts[1])
                S = cmath.exp(1j * phase)
            elif len(parts) == 3:
                E = float(parts[0])
                re = float(parts[1])
                im = float(parts[2])
                S = complex(re, im)
            else:
                raise ValueError("Expected 2 or 3 columns per row.")
            energies.append(E)
            values.append(S)

    if len(energies) < 3:
        raise ValueError("Need at least 3 sample points.")

    # Sort by energy.
    pairs = sorted(zip(energies, values), key=lambda t: t[0])
    energies_sorted = [p[0] for p in pairs]
    values_sorted = [p[1] for p in pairs]
    return energies_sorted, values_sorted


def write_latex_rows(energies: list[float], taus: list[float | None], tau0: float, out_path: Path) -> None:
    kappas: list[float | None] = [None if t is None else (t / tau0) for t in taus]
    rows: list[str] = []
    for E, tau, kappa in zip(energies, taus, kappas):
        if tau is None or kappa is None:
            continue
        rows.append(f"{E:.6g} & {tau:.6g} & {kappa:.6g} \\\\")
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Compute Wigner-Smith time delay and kappa_WS(E).")
    ap.add_argument("--input", type=str, default="", help="Optional input data file for 1-channel S(E).")
    ap.add_argument("--tau0", type=float, default=1.0, help="Reference tick duration tau0 for kappa_WS.")
    ap.add_argument("--smooth", type=int, default=1, help="Odd moving-average window for phase smoothing (1=off).")
    ap.add_argument("--E0", type=float, default=1.0, help="Toy model resonance center E0.")
    ap.add_argument("--gamma", type=float, default=0.2, help="Toy model linewidth gamma.")
    ap.add_argument("--Emin", type=float, default=0.0, help="Toy model: minimum energy.")
    ap.add_argument("--Emax", type=float, default=2.0, help="Toy model: maximum energy.")
    ap.add_argument("--n", type=int, default=17, help="Toy model: number of energy points.")
    ap.add_argument(
        "--output",
        type=str,
        default="",
        help="Optional output path for LaTeX rows (default: sections/generated/wigner_smith_rows.tex).",
    )
    args = ap.parse_args()

    tau0 = float(args.tau0)
    if tau0 <= 0.0:
        raise ValueError("tau0 must be positive.")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = Path(args.output) if args.output else (out_dir / "wigner_smith_rows.tex")

    if args.input:
        energies, S_list = load_scalar_S_data(args.input)
        # Basic unitarity diagnostic for the 1-channel case.
        mags = [abs(z) for z in S_list]
        mean_mag = sum(mags) / float(len(mags))
        max_dev = max(abs(m - 1.0) for m in mags)
        print(f"Loaded {len(energies)} samples. mean|S|={mean_mag:.6f}, max||S|-1|={max_dev:.6f}")

        taus = sample_tau_ws_from_scalar_samples(energies, S_list, smooth_window=int(args.smooth))
    else:
        energies = linspace(float(args.Emin), float(args.Emax), int(args.n))

        def S(E: float) -> complex:
            return toy_S_breit_wigner(E, E0=float(args.E0), gamma=float(args.gamma))

        taus = sample_tau_ws(S, energies)

    write_latex_rows(energies, taus, tau0=tau0, out_path=out_path)

    print("E\ttau_WS(E)\tkappa_WS(E)")
    for E, tau in zip(energies, taus):
        if tau is None:
            continue
        kappa = tau / tau0
        print(f"{E:.6g}\t{tau:.6g}\t{kappa:.6g}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()


