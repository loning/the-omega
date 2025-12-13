"""
Generate reproducible numerical figures for the 1D Fibonacci-textured DQCA.

This script is intentionally parameter-fixed (no CLI) to make repeated runs identical.
Outputs are written to ../images/ (relative to this script).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import scipy.sparse as sp
from scipy.sparse.linalg import eigsh


@dataclass(frozen=True)
class Config:
    # Discrete-to-continuum scaling
    epsilon: float = 0.05

    # Coin parameters (small-angle regime; theta ~ m * epsilon)
    m_L: float = 0.60
    m_S: float = 0.40

    # Sturmian intercept (phason shift)
    rho0: float = 0.123456

    # Periodic approximants (n values; N = F_n)
    # Keep a small set so the script runs fast but still shows convergence.
    n_list: tuple[int, ...] = (11, 12, 13)  # N = 89, 144, 233

    # k sampling in the small-k regime: |k| <= p_max * epsilon
    p_max: float = 2.5
    # Odd so we can exploit E(k)=E(-k) and compute only the nonnegative half exactly.
    k_points: int = 17

    # Fit range in physical momentum units (p)
    p_fit_max: float = 1.0

    # Residual evaluation range
    p_eval_max: float = 2.5

    # Phason-strain scan (periodic sinusoidal rho(j))
    phason_amplitudes: tuple[float, ...] = (0.0, 0.02, 0.05)


def fibonacci_numbers(n_max: int) -> list[int]:
    if n_max < 0:
        raise ValueError("n_max must be >= 0")
    if n_max == 0:
        return [0]
    F = [0, 1]
    for _ in range(2, n_max + 1):
        F.append(F[-1] + F[-2])
    return F


def fib_pair(n: int) -> tuple[int, int]:
    if n < 1:
        raise ValueError("n must be >= 1")
    F = fibonacci_numbers(n)
    return F[n - 1], F[n]


def sturmian_sigma(alpha: float, rho: float | np.ndarray, N: int) -> np.ndarray:
    """
    Return sigma[j] in {0,1} where 0=L and 1=S for Sturmian coding.
    """
    j = np.arange(N, dtype=np.float64)
    u = (j * float(alpha) + rho) % 1.0
    return (u >= (1.0 - float(alpha))).astype(np.int8)


def rho_field_sinusoidal(N: int, rho0: float, amp: float) -> np.ndarray:
    j = np.arange(N, dtype=np.float64)
    return (float(rho0) + float(amp) * np.sin(2.0 * pi * j / float(N))) % 1.0


def wrapped_diff_unit_interval(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = a - b
    return (d + 0.5) % 1.0 - 0.5


def phason_eta_inf(rho_field: np.ndarray) -> float:
    eta = wrapped_diff_unit_interval(np.roll(rho_field, -1), rho_field)
    return float(np.max(np.abs(eta)))


def coin_y(theta: float) -> np.ndarray:
    c = float(np.cos(theta))
    s = float(np.sin(theta))
    return np.array([[c, -s], [s, c]], dtype=np.complex128)


def build_U_k_sparse(sigma: np.ndarray, *, theta_L: float, theta_S: float, k: float) -> sp.csr_matrix:
    """
    Sparse 2N x 2N Floquet matrix for U(k) = S(k) C with an N-periodic coin texture.
    The matrix has O(N) nonzeros (exactly 4N here), so sparse eigen-solvers are fast.
    """
    sigma = np.asarray(sigma, dtype=np.int8)
    N = int(sigma.shape[0])
    dim = 2 * N

    C_L = coin_y(theta_L)
    C_S = coin_y(theta_S)

    def idx(j: int, is_R: bool) -> int:
        return 2 * j + (0 if is_R else 1)

    phase_R = np.exp(1j * float(k))
    phase_L = np.exp(-1j * float(k))

    rows: list[int] = []
    cols: list[int] = []
    data: list[complex] = []

    # Each input column (j,R) or (j,L) produces two outputs after coin, then shifts.
    for j in range(N):
        Cj = C_L if sigma[j] == 0 else C_S

        # column for (j,R) and (j,L)
        for is_R_in, a in ((True, 0), (False, 1)):
            col = idx(j, is_R_in)
            amp_R = complex(Cj[0, a])
            amp_L = complex(Cj[1, a])

            # R shift: to (j+1, R)
            jR = j + 1
            phR = 1.0 + 0j
            if jR >= N:
                jR = 0
                phR = complex(phase_R)
            rows.append(idx(jR, True))
            cols.append(col)
            data.append(phR * amp_R)

            # L shift: to (j-1, L)
            jL = j - 1
            phL = 1.0 + 0j
            if jL < 0:
                jL = N - 1
                phL = complex(phase_L)
            rows.append(idx(jL, False))
            cols.append(col)
            data.append(phL * amp_L)

    U = sp.coo_matrix((np.array(data), (np.array(rows), np.array(cols))), shape=(dim, dim)).tocsr()
    return U


def low_energy_branch_quasienergy_sparse(
    U: sp.csr_matrix,
    *,
    tol_phase: float = 1e-10,
    v0: np.ndarray | None = None,
) -> tuple[float, np.ndarray]:
    """
    Compute the smallest nonzero quasienergy magnitude |E| near 0 without full diagonalization.

    For unitary U with eigenvalues exp(iE_j), the Hermitian matrix
        H = (U + U^\dagger)/2
    has eigenvalues cos(E_j).
    We compute a few largest eigenvalues of H (near 1), then convert via arccos.
    """
    H = (U + U.getH()) * 0.5
    # We only need the top of the spectrum (near 1). Use loose tolerances for speed and
    # warm-start with the previous eigenvector so k-sweeps converge quickly.
    w, V = eigsh(
        H,
        k=2,
        which="LA",
        tol=1e-6,
        maxiter=80,
        v0=v0,
        return_eigenvectors=True,
    )
    order = np.argsort(-np.real(w))
    w = np.real(w)[order]
    V = V[:, order]
    for j in range(w.shape[0]):
        lam = float(np.clip(w[j], -1.0, 1.0))
        E = float(np.arccos(lam))
        if E > tol_phase:
            return E, V[:, j]
    return 0.0, V[:, 0]


def fit_dirac(p: np.ndarray, E: np.ndarray, *, p_fit_max: float) -> tuple[float, float]:
    """
    Fit E(p) to Dirac form: E^2 = c_eff^2 p^2 + m_eff^2 over |p|<=p_fit_max.
    """
    p = np.asarray(p, dtype=np.float64)
    E = np.asarray(E, dtype=np.float64)
    mask = np.abs(p) <= float(p_fit_max)
    if np.count_nonzero(mask) < 3:
        raise ValueError("Not enough points for Dirac fit.")
    x = (p[mask] ** 2).reshape(-1, 1)
    y = (E[mask] ** 2).reshape(-1, 1)
    A = np.concatenate([x, np.ones_like(x)], axis=1)
    coeff, *_ = np.linalg.lstsq(A, y, rcond=None)
    a = max(float(coeff[0, 0]), 0.0)
    b = max(float(coeff[1, 0]), 0.0)
    return float(np.sqrt(a)), float(np.sqrt(b))


def dirac_E(p: np.ndarray, c_eff: float, m_eff: float) -> np.ndarray:
    p = np.asarray(p, dtype=np.float64)
    return np.sqrt((c_eff * p) ** 2 + (m_eff) ** 2)


def compute_dispersion_for_N(
    N: int,
    alpha_n: float,
    rho: float | np.ndarray,
    *,
    cfg: Config,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Return (k_grid, p_grid, E_phys_grid) for the low-energy branch.
    """
    theta_L = cfg.m_L * cfg.epsilon
    theta_S = cfg.m_S * cfg.epsilon

    k_max = cfg.p_max * cfg.epsilon
    # Use symmetry E(k)=E(-k) for this real-coin walk: compute only nonnegative ks.
    k_half = np.linspace(0.0, k_max, (cfg.k_points + 1) // 2, dtype=np.float64)

    sigma = sturmian_sigma(alpha_n, rho, N)
    E_half = np.empty_like(k_half)
    v0 = np.ones(2 * N, dtype=np.complex128) / np.sqrt(2.0 * N)
    for i, k in enumerate(k_half):
        U = build_U_k_sparse(sigma, theta_L=theta_L, theta_S=theta_S, k=float(k))
        E_half[i], v0 = low_energy_branch_quasienergy_sparse(U, v0=v0)

    # Reflect to negative ks.
    k_grid = np.concatenate([-k_half[:0:-1], k_half])
    E = np.concatenate([E_half[:0:-1], E_half])

    p_grid = k_grid / cfg.epsilon
    E_phys = E / cfg.epsilon
    return k_grid, p_grid, E_phys


def compute_low_energy_quasienergy_at_k(
    N: int,
    alpha_n: float,
    rho: float | np.ndarray,
    *,
    k: float,
    cfg: Config,
) -> float:
    """
    Return the smallest nonzero quasienergy magnitude at a single Bloch momentum k.
    """
    theta_L = cfg.m_L * cfg.epsilon
    theta_S = cfg.m_S * cfg.epsilon
    sigma = sturmian_sigma(alpha_n, rho, N)
    U = build_U_k_sparse(sigma, theta_L=theta_L, theta_S=theta_S, k=float(k))
    v0 = np.ones(2 * N, dtype=np.complex128) / np.sqrt(2.0 * N)
    E, _ = low_energy_branch_quasienergy_sparse(U, v0=v0)
    return float(E)


def ensure_images_dir() -> Path:
    out_dir = Path(__file__).resolve().parent.parent / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def main() -> None:
    cfg = Config()
    phi = (1.0 + np.sqrt(5.0)) / 2.0
    alpha = 1.0 / (phi * phi)

    out_dir = ensure_images_dir()

    # --- Dispersion for periodic approximants ---
    all_disp = []
    for n in cfg.n_list:
        Fprev, N = fib_pair(n)
        alpha_n = Fprev / N
        k, p, E = compute_dispersion_for_N(N, alpha_n, cfg.rho0, cfg=cfg)
        all_disp.append((N, p, E))

    # Fit on the largest N
    N_max, p_maxN, E_maxN = all_disp[-1]
    c_eff, m_eff = fit_dirac(p_maxN, E_maxN, p_fit_max=cfg.p_fit_max)
    E_fit = dirac_E(p_maxN, c_eff, m_eff)

    plt.figure(figsize=(8, 5))
    for N, p, E in all_disp:
        plt.plot(p, E, linewidth=2, label=f"N={N}")
    plt.plot(p_maxN, E_fit, "k--", linewidth=2.5, label=f"Dirac fit (N={N_max})")
    plt.xlabel("Physical momentum p = k/ε")
    plt.ylabel("Physical energy E = phase/ε")
    plt.title("Fibonacci-textured DQCA: low-energy dispersion (periodic approximants)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "fib_dqca_dispersion.png", dpi=300)
    plt.close()

    # --- Group velocity for the largest N ---
    # v_g = dE/dk = d(E_phys)/d(p)
    # Using E_phys(p), we estimate v_g via gradient in p.
    v_g = np.gradient(E_maxN, p_maxN)
    plt.figure(figsize=(8, 5))
    plt.plot(p_maxN, v_g, linewidth=2)
    plt.axhline(c_eff, color="k", linestyle="--", linewidth=1.5, label="c_eff (fit)")
    plt.xlabel("Physical momentum p")
    plt.ylabel("Group velocity v_g = dE/dp")
    plt.title(f"Group velocity on low-energy branch (N={N_max})")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "fib_dqca_group_velocity.png", dpi=300)
    plt.close()

    # --- Dirac-fit residual vs N ---
    Ns = []
    max_res = []
    rms_res = []
    for N, p, E in all_disp:
        cN, mN = fit_dirac(p, E, p_fit_max=cfg.p_fit_max)
        mask = np.abs(p) <= cfg.p_eval_max
        residual = E[mask] - dirac_E(p[mask], cN, mN)
        Ns.append(N)
        max_res.append(float(np.max(np.abs(residual))))
        rms_res.append(float(np.sqrt(np.mean(residual**2))))

    plt.figure(figsize=(8, 5))
    plt.plot(Ns, max_res, "o-", linewidth=2, label="max |residual|")
    plt.plot(Ns, rms_res, "s-", linewidth=2, label="RMS residual")
    plt.xlabel("Approximant size N")
    plt.ylabel("Residual in physical energy")
    plt.title("Dirac-fit residual vs Fibonacci approximant size")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "fib_dqca_dirac_fit_error_vs_N.png", dpi=300)
    plt.close()

    # --- Doubler diagnostic: smallest quasienergy at k = pi ---
    # If a second Dirac cone (doubler) existed, E(k=pi) would become small.
    Epi_phys = []
    for n in cfg.n_list:
        Fprev, N = fib_pair(n)
        alpha_n = Fprev / N
        Epi = compute_low_energy_quasienergy_at_k(N, alpha_n, cfg.rho0, k=pi, cfg=cfg)
        Epi_phys.append(Epi / cfg.epsilon)

    plt.figure(figsize=(8, 5))
    plt.plot(Ns, Epi_phys, "o-", linewidth=2)
    plt.xlabel("Approximant size N")
    plt.ylabel("E_min(k=π)/ε (physical units)")
    plt.title("Doubler diagnostic: low-energy gap at Brillouin edge k=π")
    plt.tight_layout()
    plt.savefig(out_dir / "fib_dqca_doubler_gap_at_pi.png", dpi=300)
    plt.close()

    # --- Sensitivity to periodic phason strain ---
    # Fix N to the largest approximant and scan rho(j)=rho0 + A sin(2π j/N).
    Fprev, N = fib_pair(cfg.n_list[-1])
    alpha_n = Fprev / N

    eta_inf_list = []
    residual_list = []
    for amp in cfg.phason_amplitudes:
        rho_field = rho_field_sinusoidal(N, cfg.rho0, amp)
        eta_inf = phason_eta_inf(rho_field)
        _, p, E = compute_dispersion_for_N(N, alpha_n, rho_field, cfg=cfg)
        cN, mN = fit_dirac(p, E, p_fit_max=cfg.p_fit_max)
        mask = np.abs(p) <= cfg.p_eval_max
        residual = E[mask] - dirac_E(p[mask], cN, mN)
        eta_inf_list.append(eta_inf)
        residual_list.append(float(np.sqrt(np.mean(residual**2))))

    plt.figure(figsize=(8, 5))
    plt.plot(eta_inf_list, residual_list, "o-", linewidth=2)
    plt.xlabel("Wrapped phason strain metric η_inf")
    plt.ylabel("RMS Dirac-fit residual (physical energy)")
    plt.title(f"Dirac-fit residual vs phason strain (N={N})")
    plt.tight_layout()
    plt.savefig(out_dir / "fib_dqca_dirac_fit_error_vs_phason.png", dpi=300)
    plt.close()

    print("Generated figures:")
    for name in [
        "fib_dqca_dispersion.png",
        "fib_dqca_group_velocity.png",
        "fib_dqca_dirac_fit_error_vs_N.png",
        "fib_dqca_dirac_fit_error_vs_phason.png",
        "fib_dqca_doubler_gap_at_pi.png",
    ]:
        print(f"  - {out_dir / name}")
    print("\nFixed parameters (Config):")
    print(cfg)


if __name__ == "__main__":
    main()


