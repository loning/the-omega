import numpy as np


def poisson_periodic_green_3d(n: int, source_pos=None) -> np.ndarray:
    """
    Solve Laplacian(phi) = 4*pi*rho on an n x n x n periodic grid (spacing 1) via FFT.
    Gauge: set k=0 mode to 0 (zero-mean potential).
    """
    if source_pos is None:
        source_pos = (n // 2, n // 2, n // 2)

    rho = np.zeros((n, n, n), dtype=float)
    rho[source_pos] = 1.0

    rho_k = np.fft.fftn(rho)

    k = 2 * np.pi * np.fft.fftfreq(n)
    KX, KY, KZ = np.meshgrid(k, k, k, indexing="ij")
    k2 = KX**2 + KY**2 + KZ**2

    phi_k = np.zeros_like(rho_k, dtype=complex)
    mask = k2 != 0
    phi_k[mask] = -4 * np.pi * rho_k[mask] / k2[mask]

    phi = np.real(np.fft.ifftn(phi_k))
    return phi


def radial_average(phi: np.ndarray):
    n = phi.shape[0]
    center = np.array([n // 2, n // 2, n // 2], dtype=float)
    coords = np.indices(phi.shape).reshape(3, -1).T.astype(float)
    r = np.linalg.norm(coords - center, axis=1)
    phi_flat = phi.ravel()

    out = []
    for rad in range(1, n // 4):
        shell = (r >= rad - 0.5) & (r < rad + 0.5)
        if shell.sum() == 0:
            continue
        out.append((rad, float(phi_flat[shell].mean()), float(phi_flat[shell].std()), int(shell.sum())))
    return out


def fit_inverse_r(stats, r_min: int, r_max: int):
    """
    Fit <Phi>(r) approx C0 - M/r over integer radii r in [r_min, r_max].
    Returns (C0, M, rms).
    """
    rows = [(r, mean) for (r, mean, _std, _cnt) in stats if r_min <= r <= r_max]
    if len(rows) < 2:
        raise ValueError("Need at least two radii for fitting.")

    r = np.asarray([rr for rr, _ in rows], dtype=float)
    y = np.asarray([yy for _, yy in rows], dtype=float)
    x = 1.0 / r

    # y = a + b x, with b = -M and a = C0
    A = np.vstack([np.ones_like(x), x]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    C0, b = float(coef[0]), float(coef[1])
    M = -b
    resid = y - (C0 + b * x)
    rms = float(np.sqrt(np.mean(resid**2)))
    return C0, M, rms


if __name__ == "__main__":
    n = 64
    phi = poisson_periodic_green_3d(n)
    stats = radial_average(phi)

    print("r | <Phi> | r*<Phi> | std | count")
    for r, mean, std, cnt in stats[:12]:
        print(f"{r:2d} | {mean: .6f} | {r*mean: .6f} | {std: .6f} | {cnt}")

    # Example near-field fit window; adjust as needed to avoid periodic-image effects.
    r_min, r_max = 2, 6
    C0, M, rms = fit_inverse_r(stats, r_min=r_min, r_max=r_max)
    print(f"\nFit over r in [{r_min},{r_max}]: <Phi>(r) approx C0 - M/r")
    print(f"C0={C0:.6f}, M={M:.6f}, RMS={rms:.6e}")


