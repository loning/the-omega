# -*- coding: utf-8 -*-
"""
Poisson solver in 3D (periodic box) for a point source.

We solve:
  -Delta Phi = 4*pi rho
on a periodic cube using either:
  (A) an FFT-based solver (if numpy is available), or
  (B) a pure-Python iterative Jacobi/SOR fallback (if numpy is unavailable).

We set the zero mode to 0 (zero-mean gauge) by subtracting the mean of rho.

The script outputs radial shell averages <Phi>(r) and writes a small LaTeX row
file into sections/generated/poisson_rows.tex.
"""

from __future__ import annotations

import math
from pathlib import Path

try:
    import numpy as np  # type: ignore
except ModuleNotFoundError:
    np = None  # type: ignore


def poisson_solve_fft(rho: "np.ndarray", L: float = 1.0) -> "np.ndarray":
    """
    Solve -Delta Phi = 4*pi rho on a periodic cube [0,L)^3 using FFT.
    The k=0 mode is set to 0 (zero-mean gauge).
    """
    if np is None:
        raise RuntimeError("numpy is required for the FFT solver.")

    N = int(rho.shape[0])
    assert rho.shape == (N, N, N)

    # Ensure solvability in the periodic setting by removing the mean (zero mode).
    rho = rho - float(rho.mean())
    rho_k = np.fft.fftn(rho)

    k = 2 * np.pi * np.fft.fftfreq(N, d=L / N)
    kx, ky, kz = np.meshgrid(k, k, k, indexing="ij")
    k2 = kx * kx + ky * ky + kz * kz

    phi_k = np.zeros_like(rho_k, dtype=np.complex128)
    mask = k2 != 0.0
    phi_k[mask] = (4 * np.pi) * rho_k[mask] / k2[mask]
    phi_k[~mask] = 0.0

    phi = np.fft.ifftn(phi_k).real
    return phi


def radial_shell_average_numpy(phi: "np.ndarray", r_max: int = 12):
    """
    Return shell averages for integer radii r=1..r_max (in lattice steps).
    """
    if np is None:
        raise RuntimeError("numpy is required for the numpy radial averaging.")

    N = int(phi.shape[0])
    assert phi.shape == (N, N, N)

    center = np.array([N // 2, N // 2, N // 2], dtype=float)
    coords = np.indices((N, N, N), dtype=float).reshape(3, -1).T
    r = np.linalg.norm(coords - center, axis=1)
    phi_flat = phi.reshape(-1)

    out = []
    for rad in range(1, r_max + 1):
        shell = (r >= rad - 0.5) & (r < rad + 0.5)
        if int(shell.sum()) == 0:
            continue
        mean = float(phi_flat[shell].mean())
        out.append((rad, mean))
    return out


def poisson_solve_jacobi_periodic(
    N: int,
    rho: list[float],
    max_iter: int = 4000,
    omega: float = 0.9,
) -> list[float]:
    """
    Pure-Python periodic Poisson solver for -Delta phi = 4*pi rho using damped Jacobi/SOR.

    The grid spacing is 1. rho is a flat list of length N^3.
    """
    n3 = N * N * N
    if len(rho) != n3:
        raise ValueError("rho must have length N^3.")

    # Enforce solvability by subtracting mean (zero mode).
    mean_rho = sum(rho) / n3
    rho = [v - mean_rho for v in rho]

    phi = [0.0] * n3
    phi_new = [0.0] * n3

    for _it in range(max_iter):
        for i in range(N):
            ip = (i + 1) % N
            im = (i - 1) % N
            for j in range(N):
                jp = (j + 1) % N
                jm = (j - 1) % N
                base_ip = ip * N * N
                base_im = im * N * N
                base_i = i * N * N
                base_jp = jp * N
                base_jm = jm * N
                base_j = j * N
                for k in range(N):
                    kp = (k + 1) % N
                    km = (k - 1) % N
                    p = base_i + base_j + k

                    neigh = (
                        phi[base_ip + base_j + k]
                        + phi[base_im + base_j + k]
                        + phi[base_i + base_jp + k]
                        + phi[base_i + base_jm + k]
                        + phi[base_i + base_j + kp]
                        + phi[base_i + base_j + km]
                    )

                    # Discrete stencil for -Delta phi = 6 phi - sum(neigh) = 4*pi rho
                    candidate = (neigh + 4.0 * math.pi * rho[p]) / 6.0
                    phi_new[p] = (1.0 - omega) * phi[p] + omega * candidate

        phi, phi_new = phi_new, phi

    # Gauge-fix to zero mean.
    mean_phi = sum(phi) / n3
    phi = [v - mean_phi for v in phi]
    return phi


def radial_shell_average_pure(phi: list[float], N: int, r_max: int = 12) -> list[tuple[int, float]]:
    """
    Pure-Python shell averages for integer radii r=1..r_max (in lattice steps).
    """
    n3 = N * N * N
    if len(phi) != n3:
        raise ValueError("phi must have length N^3.")

    cx = N // 2
    cy = N // 2
    cz = N // 2

    sums = [0.0] * (r_max + 1)
    counts = [0] * (r_max + 1)

    for i in range(N):
        dx = i - cx
        for j in range(N):
            dy = j - cy
            for k in range(N):
                dz = k - cz
                r = (dx * dx + dy * dy + dz * dz) ** 0.5
                rad = int(round(r))
                if 1 <= rad <= r_max and abs(r - rad) < 0.5:
                    p = (i * N + j) * N + k
                    sums[rad] += phi[p]
                    counts[rad] += 1

    out: list[tuple[int, float]] = []
    for rad in range(1, r_max + 1):
        if counts[rad] == 0:
            continue
        out.append((rad, sums[rad] / counts[rad]))
    return out


def write_rows(rows: list[tuple[int, float]]) -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "poisson_rows.tex"

    lines = []
    for r, mean in rows:
        lines.append(f"{r} & {mean:+.6f} & {(r*mean):+.6f} \\\\")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    r_max = 12

    if np is not None:
        N = 64
        L = 1.0

        rho = np.zeros((N, N, N), dtype=float)
        rho[N // 2, N // 2, N // 2] = 1.0

        phi = poisson_solve_fft(rho, L=L)
        stats = radial_shell_average_numpy(phi, r_max=r_max)
    else:
        # Pure-Python fallback: smaller grid and iterative solver.
        N = 24
        n3 = N * N * N
        rho = [0.0] * n3
        center = (N // 2, N // 2, N // 2)
        center_idx = (center[0] * N + center[1]) * N + center[2]
        rho[center_idx] = 1.0

        phi_flat = poisson_solve_jacobi_periodic(N=N, rho=rho, max_iter=5000, omega=0.9)
        stats = radial_shell_average_pure(phi_flat, N=N, r_max=r_max)

    print("r | <Phi> | r*<Phi>")
    for r, mean in stats[:12]:
        print(f"{r:2d} | {mean:+.6f} | {(r*mean):+.6f}")

    write_rows(stats[:10])
    print("Wrote sections/generated/poisson_rows.tex")


if __name__ == "__main__":
    main()


