#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demo C: 6D icosahedral cut-and-project approximation fingerprints.

This is a minimal, fully reproducible numerical demonstration:
- generate a finite 3D point cloud from a 6D lattice (Z^6) with an icosahedral
  physical/perp splitting (using the golden ratio and its Galois conjugate)
- compute a 2D diffraction slice via FFT of a binned density
- compute a resolution-dependent visibility curve V(epsilon) by fuzzifying
  the internal-space ball window and phase-averaging over window shifts

Figures are written to --fig-out (typically sections/generated/).
Data (JSON) are written to --out (typically artifacts/).
"""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

from common_progress import ProgressPrinter
from fold_zeckendorf import exact_degeneracy_histogram, fold_m


@dataclass(frozen=True)
class Demo6DParams:
    L: int
    R: float
    phases: int
    eps_grid: List[float]
    seed: int
    grid_n: int
    grid_dx: float
    scan_T: int
    scan_beta: Tuple[float, float, float]
    scan_h0: Tuple[float, float, float]
    scan_R: float
    scan_fold_m: int
    entropy_block_max: int
    tau_prefix_max: int
    probabilistic_readout: bool
    # Correlated noise model for U_t (optional robustness check).
    noise_rho: float
    # Optional: closed-form Fourier-envelope check for a box window in H=R^3.
    box_L: Tuple[float, float, float]
    box_eps: float
    module_K: int
    module_max_points: int


def icosa_matrices() -> Tuple[np.ndarray, np.ndarray]:
    """Return (A_T, Astar_T) as (6,3) matrices mapping Z^6 -> R^3."""
    phi = (1.0 + 5.0**0.5) / 2.0
    phis = 1.0 - phi  # Galois conjugate = -1/phi
    cols = [
        (1.0, phi, 0.0),
        (-1.0, phi, 0.0),
        (0.0, 1.0, phi),
        (0.0, -1.0, phi),
        (phi, 0.0, 1.0),
        (phi, 0.0, -1.0),
    ]
    cols_star = [
        (1.0, phis, 0.0),
        (-1.0, phis, 0.0),
        (0.0, 1.0, phis),
        (0.0, -1.0, phis),
        (phis, 0.0, 1.0),
        (phis, 0.0, -1.0),
    ]
    A_T = np.array(cols, dtype=float)  # (6,3)
    Astar_T = np.array(cols_star, dtype=float)  # (6,3)
    # Normalize overall scale for numerical stability (arbitrary).
    A_T /= np.linalg.norm(A_T, axis=1, keepdims=True)
    Astar_T /= np.linalg.norm(Astar_T, axis=1, keepdims=True)
    return A_T, Astar_T


def smooth_ball_weight(u: np.ndarray, R: float, eps: float) -> np.ndarray:
    """Smooth window weight for a ball: ~1 inside, decays across boundary layer."""
    r = np.linalg.norm(u, axis=1)
    if eps <= 0:
        return (r <= R).astype(float)
    x = (R - r) / eps
    return 1.0 / (1.0 + np.exp(-x))


def smooth_box_weight(u: np.ndarray, L: Tuple[float, float, float], eps: float) -> np.ndarray:
    """Smooth indicator for an axis-aligned box centered at 0 with side lengths L."""
    if len(u) == 0:
        return np.zeros((0,), dtype=float)
    Lx, Ly, Lz = (float(L[0]), float(L[1]), float(L[2]))
    hx, hy, hz = (0.5 * Lx, 0.5 * Ly, 0.5 * Lz)
    x = u[:, 0]
    y = u[:, 1]
    z = u[:, 2]
    if eps <= 0:
        return ((np.abs(x) <= hx) & (np.abs(y) <= hy) & (np.abs(z) <= hz)).astype(float)
    # Product of two sigmoids per axis: inside ~1, outside decays.
    def _axis_weight(coord: np.ndarray, half: float) -> np.ndarray:
        a = (-half - coord) / eps
        b = (half - coord) / eps
        # sigmoid(half - coord) * sigmoid(half + coord)
        s1 = 1.0 / (1.0 + np.exp(-b))
        s2 = 1.0 / (1.0 + np.exp(-a))
        return s1 * s2

    return _axis_weight(x, hx) * _axis_weight(y, hy) * _axis_weight(z, hz)


def _sinc(x: np.ndarray) -> np.ndarray:
    """sinc(x) = sin(pi x)/(pi x), with sinc(0)=1."""
    out = np.ones_like(x, dtype=float)
    m = np.abs(x) > 1e-15
    out[m] = np.sin(np.pi * x[m]) / (np.pi * x[m])
    return out


def box_window_fourier_hat(xi: np.ndarray, L: Tuple[float, float, float]) -> np.ndarray:
    """Closed-form Fourier transform of box indicator under exp(-2pi i <xi,y>) convention."""
    Lx, Ly, Lz = (float(L[0]), float(L[1]), float(L[2]))
    xi = np.asarray(xi, dtype=float)
    sx = Lx * _sinc(Lx * xi[..., 0])
    sy = Ly * _sinc(Ly * xi[..., 1])
    sz = Lz * _sinc(Lz * xi[..., 2])
    return sx * sy * sz


def _pearson_r(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    if len(a) != len(b) or len(a) == 0:
        return float("nan")
    a0 = a - float(np.mean(a))
    b0 = b - float(np.mean(b))
    na = float(np.linalg.norm(a0))
    nb = float(np.linalg.norm(b0))
    if na <= 0 or nb <= 0:
        return float("nan")
    return float(np.dot(a0, b0) / (na * nb))


def _spearman_r(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    if len(a) != len(b) or len(a) == 0:
        return float("nan")
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return _pearson_r(ra, rb)


def _r2_fit(y: np.ndarray, x: np.ndarray) -> float:
    """R^2 for least-squares fit y ~ a*x + b."""
    y = np.asarray(y, dtype=float).ravel()
    x = np.asarray(x, dtype=float).ravel()
    if len(x) != len(y) or len(x) == 0:
        return float("nan")
    A = np.stack([x, np.ones_like(x)], axis=1)
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    yhat = A @ coef
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    if ss_tot <= 0:
        return float("nan")
    return float(1.0 - ss_res / ss_tot)


def lattice_points_box(L: int) -> np.ndarray:
    """Enumerate Z^6 points in [-L,L]^6 as (N,6) int array."""
    rng = np.arange(-L, L + 1, dtype=int)
    grid = np.stack(np.meshgrid(rng, rng, rng, rng, rng, rng, indexing="ij"), axis=-1)
    pts = grid.reshape(-1, 6)
    return pts


def generate_model_set_points(
    pts6: np.ndarray,
    A_T: np.ndarray,
    Astar_T: np.ndarray,
    R: float,
    phase_shift: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (x,u) with u inside ball window centered at phase_shift."""
    x = pts6 @ A_T  # (N,3)
    u = pts6 @ Astar_T  # (N,3)
    uu = u + phase_shift[None, :]
    mask = np.linalg.norm(uu, axis=1) <= R
    return x[mask], uu[mask]


def binned_density_2d(x: np.ndarray, w: np.ndarray, n: int, dx: float) -> Tuple[np.ndarray, Tuple[float, float]]:
    """Bin (x,y) into an n-by-n array centered around the data mean."""
    if len(x) == 0:
        return np.zeros((n, n), dtype=float), (0.0, 0.0)
    xy = x[:, :2]
    c = np.mean(xy, axis=0)
    xy = xy - c[None, :]
    # Map to indices in [-n/2, n/2).
    ix = np.floor(xy[:, 0] / dx + n / 2.0).astype(int)
    iy = np.floor(xy[:, 1] / dx + n / 2.0).astype(int)
    good = (0 <= ix) & (ix < n) & (0 <= iy) & (iy < n)
    ix = ix[good]
    iy = iy[good]
    ww = w[good]
    img = np.zeros((n, n), dtype=float)
    np.add.at(img, (iy, ix), ww)
    return img, (float(c[0]), float(c[1]))


def fft_intensity(img: np.ndarray) -> np.ndarray:
    F = np.fft.fftshift(np.fft.fft2(img))
    I = np.abs(F) ** 2
    # Normalize for display.
    I /= max(float(np.max(I)), 1e-12)
    return I


def pick_peak_index(I: np.ndarray) -> Tuple[int, int]:
    """Pick a strong non-DC peak index from intensity array."""
    n = I.shape[0]
    cy = n // 2
    cx = n // 2
    # Zero out a small DC neighborhood.
    J = I.copy()
    r0 = max(2, n // 64)
    J[cy - r0 : cy + r0 + 1, cx - r0 : cx + r0 + 1] = 0.0
    iy, ix = np.unravel_index(np.argmax(J), J.shape)
    return int(iy), int(ix)


def contrast_statistic_from_image(img: np.ndarray) -> float:
    """Coefficient of variation of a 2D intensity image."""
    m = float(np.mean(img))
    s = float(np.std(img))
    return float(s / max(m, 1e-12))


def _wrap_pm_half(x: np.ndarray) -> np.ndarray:
    """Wrap coordinates to [-0.5, 0.5) componentwise."""
    return (x + 0.5) % 1.0 - 0.5


def internal_scan(h0: np.ndarray, beta: np.ndarray, T: int) -> np.ndarray:
    """Return (T,3) scan points on a 3-torus, represented in [-0.5,0.5)^3."""
    t = np.arange(T, dtype=float)[:, None]
    h = h0[None, :] + t * beta[None, :]
    return _wrap_pm_half(h)


def kappa_ball(h: np.ndarray, R: float, eps: float) -> np.ndarray:
    """Window kernel kappa_eps(h) in [0,1] for internal ball window."""
    r = np.linalg.norm(h, axis=1)
    if eps <= 0:
        return (r <= R).astype(float)
    x = (R - r) / eps
    return 1.0 / (1.0 + np.exp(-x))


def H_b(p: np.ndarray) -> np.ndarray:
    """Binary entropy H_b(p) in nats, with 0 log 0 := 0."""
    p = np.asarray(p, dtype=float)
    p = np.clip(p, 0.0, 1.0)
    out = np.zeros_like(p, dtype=float)
    m1 = p > 0.0
    out[m1] -= p[m1] * np.log(p[m1])
    q = 1.0 - p
    m2 = q > 0.0
    out[m2] -= q[m2] * np.log(q[m2])
    return out


def orbit_points_1d(alpha: float, x0: float, N: int) -> np.ndarray:
    n = np.arange(N, dtype=float)
    return (float(x0) + n * (float(alpha) % 1.0)) % 1.0


def discrepancy_1d(points: np.ndarray) -> float:
    """Star discrepancy proxy in 1D (exact for given points)."""
    x = np.sort(np.asarray(points, dtype=float))
    N = len(x)
    if N <= 0:
        return 0.0
    i = np.arange(1, N + 1, dtype=float)
    d1 = np.max(np.abs(i / N - x))
    d2 = np.max(np.abs(x - (i - 1.0) / N))
    return float(max(d1, d2))


def three_gap_stats(points: np.ndarray, tol: float = 1e-12) -> Dict[str, object]:
    """Compute gap lengths on the circle and report distinct-gap counts."""
    x = np.sort(np.asarray(points, dtype=float))
    N = len(x)
    if N <= 1:
        return {"N": int(N), "distinct_gaps": 0, "gaps": [], "counts": []}
    gaps = np.diff(np.concatenate([x, [x[0] + 1.0]]))
    keys: Dict[float, int] = {}
    for g in gaps:
        k = float(round(float(g) / tol) * tol)
        keys[k] = keys.get(k, 0) + 1
    ks = sorted(keys.keys())
    return {
        "N": int(N),
        "distinct_gaps": int(len(ks)),
        "gaps": [float(k) for k in ks],
        "counts": [int(keys[k]) for k in ks],
    }


def continued_fraction_convergents(alpha: float, max_q: int = 200) -> List[Tuple[int, int]]:
    """Return convergents p/q for alpha in (0,1), with q<=max_q."""
    a = float(alpha) % 1.0
    if not (0.0 < a < 1.0):
        return []
    conv: List[Tuple[int, int]] = []
    p0, q0 = 0, 1
    p1, q1 = 1, 0
    x = a
    while True:
        ai = int(math.floor(1.0 / x))
        p2 = ai * p1 + p0
        q2 = ai * q1 + q0
        if q2 > max_q:
            break
        conv.append((p2, q2))
        p0, q0 = p1, q1
        p1, q1 = p2, q2
        r = 1.0 / x - ai
        if r <= 1e-15:
            break
        x = r
    out = [(q, p) for (p, q) in conv if p > 0]  # convert from 1/alpha to alpha
    uniq = list(dict.fromkeys(out))
    uniq.sort(key=lambda t: t[1])
    return uniq


def bernoulli_readout(rng: np.random.Generator, p: np.ndarray) -> List[int]:
    """Sample bits with P(bit=1)=p (independent given the scan)."""
    u = rng.random(size=len(p))
    return (u < p).astype(int).tolist()


def correlated_uniform_ar1(rng: np.random.Generator, T: int, rho: float) -> np.ndarray:
    """Generate U_t in [0,1] with AR(1) Gaussian copula correlation.

    z_t = rho z_{t-1} + sqrt(1-rho^2) e_t, e_t ~ N(0,1)
    U_t = Phi(z_t), so marginals are Uniform[0,1] but temporal correlation persists.
    """
    rho = float(rho)
    if T <= 0:
        return np.zeros((0,), dtype=float)
    rho = max(min(rho, 0.999), -0.999)
    sig = math.sqrt(max(1.0 - rho * rho, 1e-12))
    z = 0.0
    out = np.zeros((T,), dtype=float)
    inv_sqrt2 = 1.0 / math.sqrt(2.0)
    for t in range(T):
        z = rho * z + sig * float(rng.normal())
        # Standard normal CDF via erf: Phi(z) = 0.5*(1+erf(z/sqrt(2))).
        out[t] = 0.5 * (1.0 + math.erf(z * inv_sqrt2))
    return out


def lag1_autocorr_bits(bits: Sequence[int]) -> float:
    if len(bits) < 2:
        return 0.0
    x = np.asarray(bits, dtype=float)
    x0 = x[:-1]
    x1 = x[1:]
    x0 -= float(np.mean(x0))
    x1 -= float(np.mean(x1))
    d = float(np.linalg.norm(x0) * np.linalg.norm(x1))
    if d <= 1e-12:
        return 0.0
    return float(np.dot(x0, x1) / d)


def deterministic_threshold_readout(p: np.ndarray, thresh: float = 0.5) -> List[int]:
    """Deterministic readout bit = 1[p >= thresh]."""
    return (p >= thresh).astype(int).tolist()


def stabilized_type_sequence(bits: Sequence[int], m: int) -> List[Tuple[int, ...]]:
    """Sliding-window stabilization: x_t = Fold_m(bits[t:t+m])."""
    if len(bits) < m:
        return []
    out: List[Tuple[int, ...]] = []
    for i in range(len(bits) - m + 1):
        out.append(fold_m(bits[i : i + m]))
    return out


def block_entropy_rate_proxy(seq: Sequence[int], max_block_len: int) -> Dict[str, float]:
    """Return H(block_n)/n for n=1..max_block_len (natural log units)."""
    n_total = len(seq)
    out: Dict[str, float] = {}
    if n_total <= 0:
        return out
    for n in range(1, max_block_len + 1):
        if n_total < n:
            out[str(n)] = 0.0
            continue
        total = n_total - n + 1
        counts: Dict[Tuple[int, ...], int] = {}
        for i in range(total):
            w = tuple(seq[i : i + n])
            counts[w] = counts.get(w, 0) + 1
        H = 0.0
        for c in counts.values():
            p = c / total
            H -= p * math.log(p)
        out[str(n)] = float(H / n)
    return out


def empirical_tau_prefix(seq: Sequence[int], tau_prefix_max: int) -> List[float]:
    """Estimate tau(t)=-log P(prefix_t) by counting prefix occurrences in seq."""
    T = len(seq)
    out: List[float] = []
    if T <= 0:
        return out
    prefix: List[int] = []
    for t in range(1, min(tau_prefix_max, T) + 1):
        prefix = list(seq[:t])
        total = T - t + 1
        if total <= 0:
            out.append(float("inf"))
            continue
        c = 0
        for i in range(total):
            if list(seq[i : i + t]) == prefix:
                c += 1
        p = max(c / total, 1.0 / (total + 1.0))
        out.append(float(-math.log(p)))
    return out


def _normal_cdf(z: np.ndarray) -> np.ndarray:
    """Standard normal CDF via erf (vectorized)."""
    return 0.5 * (1.0 + scipy_special_erf(z / math.sqrt(2.0)))


def scipy_special_erf(x: np.ndarray) -> np.ndarray:
    # Avoid adding scipy dependency: use numpy.vectorize(math.erf).
    # This is fast enough at the demo scale (T up to ~5e4).
    vf = np.vectorize(math.erf)
    return vf(x).astype(float)


def ar1_filter_from_innovations(e: np.ndarray, rho: float) -> np.ndarray:
    """AR(1) filter: z_t = rho z_{t-1} + sqrt(1-rho^2) e_t."""
    rho = float(rho)
    if e.size == 0:
        return e.astype(float)
    rho = max(min(rho, 0.999), -0.999)
    sig = math.sqrt(max(1.0 - rho * rho, 1e-12))
    z = np.zeros_like(e, dtype=float)
    z0 = 0.0
    for t in range(e.size):
        z0 = rho * z0 + sig * float(e[t])
        z[t] = z0
    return z


def sequential_markov_tau(
    seq: Sequence[int],
    order: int,
    beta: float,
    max_len: int,
) -> Dict[str, object]:
    """Sequential K-order Markov log-loss as tau proxy.

    Returns a dict with:
    - tau: cumulative -log P_hat(seq[:t]) for t=1..T0
    - order, beta
    - h_hat: average log-loss at T0
    """
    T = len(seq)
    T0 = int(min(max_len, T))
    if T0 <= 0:
        return {"tau": [], "order": int(order), "beta": float(beta), "h_hat": 0.0}
    K = int(max(order, 0))
    beta = float(max(beta, 1e-9))
    # Counts keyed by context (tuple of last K bits): [c0, c1]
    counts: Dict[Tuple[int, ...], List[int]] = {}
    tau: List[float] = []
    acc = 0.0
    for t in range(T0):
        ctx = tuple(seq[max(0, t - K) : t]) if K > 0 else tuple()
        c01 = counts.get(ctx)
        if c01 is None:
            c01 = [0, 0]
            counts[ctx] = c01
        n = c01[0] + c01[1]
        p1 = (c01[1] + beta) / (n + 2.0 * beta)
        yt = int(seq[t])
        p = p1 if yt == 1 else (1.0 - p1)
        p = max(min(p, 1.0 - 1e-12), 1e-12)
        acc += -math.log(p)
        tau.append(float(acc))
        c01[yt] += 1
    h_hat = float(acc / T0)
    return {"tau": tau, "order": K, "beta": beta, "h_hat": h_hat, "T": int(T0)}


def mismatch_rate(a: Sequence[int], b: Sequence[int]) -> float:
    n = min(len(a), len(b))
    if n <= 0:
        return 0.0
    aa = np.asarray(a[:n], dtype=int)
    bb = np.asarray(b[:n], dtype=int)
    return float(np.mean(aa != bb))


def sturmian_bits(alpha: float, x0: float, I_len: float, N: int) -> List[int]:
    pts = orbit_points_1d(alpha=float(alpha), x0=float(x0), N=int(N))
    return (pts < float(I_len)).astype(int).tolist()


def periodicity_error(bits: Sequence[int], q: int) -> float:
    q = int(q)
    if q <= 0 or len(bits) <= q:
        return 0.0
    a = np.asarray(bits[:-q], dtype=int)
    b = np.asarray(bits[q:], dtype=int)
    return float(np.mean(a != b))

def transition_counts(types: Sequence[Tuple[int, ...]]) -> Dict[str, int]:
    """Return edge counts for successive stabilized types, keyed by 'u->v'."""
    edges: Dict[str, int] = {}
    if len(types) <= 1:
        return edges
    for a, b in zip(types, types[1:]):
        ka = "".join(str(x) for x in a)
        kb = "".join(str(x) for x in b)
        k = f"{ka}->{kb}"
        edges[k] = edges.get(k, 0) + 1
    return edges


def module_candidates(K: int) -> np.ndarray:
    """Enumerate Z^6 dual candidates in [-K,K]^6 excluding 0."""
    K = int(K)
    rng = np.arange(-K, K + 1, dtype=int)
    grid = np.stack(np.meshgrid(rng, rng, rng, rng, rng, rng, indexing="ij"), axis=-1).reshape(-1, 6)
    nonzero = np.any(grid != 0, axis=1)
    return grid[nonzero]


def empirical_structure_factor(points: np.ndarray, k_phys: np.ndarray) -> np.ndarray:
    """Compute S(k)=|mean exp(-2pi i <k, x>)|^2 for k in rows of k_phys."""
    if len(points) == 0 or len(k_phys) == 0:
        return np.zeros((len(k_phys),), dtype=float)
    X = np.asarray(points, dtype=float)
    K = np.asarray(k_phys, dtype=float)
    phases = np.exp(-2j * np.pi * (X @ K.T))  # (N,M)
    amp = np.mean(phases, axis=0)  # (M,)
    return (np.abs(amp) ** 2).real


def run_demo(out_dir: Path, fig_out_dir: Path, seed: int = 0) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_out_dir.mkdir(parents=True, exist_ok=True)

    params = Demo6DParams(
        L=4,
        R=2.35,
        phases=8,
        eps_grid=[0.01, 0.02, 0.05, 0.1, 0.2],
        seed=seed,
        grid_n=512,
        grid_dx=0.35,
        scan_T=50000,
        scan_beta=(0.38196601125, 0.2360679775, 0.14589803375),
        scan_h0=(0.123456789, -0.234567891, 0.345678912),
        scan_R=0.35,
        scan_fold_m=12,
        entropy_block_max=10,
        tau_prefix_max=64,
        probabilistic_readout=True,
        noise_rho=0.85,
        box_L=(2.2, 2.2, 2.2),
        box_eps=0.03,
        module_K=1,
        module_max_points=20000,
    )
    rng = np.random.default_rng(params.seed)
    pp = ProgressPrinter("demo_6d")

    A_T, Astar_T = icosa_matrices()
    pts6 = lattice_points_box(params.L)

    # Diffraction slice for one sharp phase.
    phase0 = rng.uniform(-0.5, 0.5, size=3)
    x0, u0 = generate_model_set_points(pts6, A_T, Astar_T, R=params.R, phase_shift=phase0)
    w0 = np.ones(len(x0), dtype=float)
    img0, _ = binned_density_2d(x0, w0, n=params.grid_n, dx=params.grid_dx)
    I0 = fft_intensity(img0)
    peak_iy, peak_ix = pick_peak_index(I0)
    pp.tick(f"N={len(x0)} peak=({peak_ix},{peak_iy})")

    # Visibility curve with phase averaging (variance-based contrast statistic).
    V_mean: List[float] = []
    V_std: List[float] = []
    for eps in params.eps_grid:
        V_phase: List[float] = []
        for p_i in range(params.phases):
            ph = rng.uniform(-0.5, 0.5, size=3)
            x, u = generate_model_set_points(pts6, A_T, Astar_T, R=params.R, phase_shift=ph)
            w = smooth_ball_weight(u, R=params.R, eps=float(eps))
            img, _ = binned_density_2d(x, w, n=params.grid_n, dx=params.grid_dx)
            V = contrast_statistic_from_image(img)
            V_phase.append(V)
            pp.tick(f"eps={eps:.3f} phase={p_i+1}/{params.phases} V={V:.4f}")
        V_mean.append(float(np.mean(V_phase)))
        V_std.append(float(np.std(V_phase)))

    # Symbolic: Fold + fibers + transition graph (computed at each eps).
    beta = np.array(params.scan_beta, dtype=float)
    h0 = np.array(params.scan_h0, dtype=float)
    h_scan = internal_scan(h0=h0, beta=beta, T=params.scan_T)

    deg = exact_degeneracy_histogram(params.scan_fold_m)
    deg_hist = {str(k): int(v) for k, v in sorted(deg.histogram().items())}

    symbolic_by_eps: Dict[str, object] = {}
    Hrate_by_eps: List[float] = []
    Htheory_by_eps: List[float] = []
    Hrate_corr_by_eps: List[float] = []
    Hrate_markov_by_eps: List[float] = []
    for eps in params.eps_grid:
        kappa = kappa_ball(h_scan, R=float(params.scan_R), eps=float(eps))
        h_theory = float(np.mean(H_b(kappa)))
        Htheory_by_eps.append(h_theory)
        if params.probabilistic_readout:
            # Coupled randomness for multiple protocol variants:
            # e_t are i.i.d. N(0,1) innovations. rho=0 gives i.i.d. uniforms.
            e = rng.normal(size=len(kappa))
            U_iid = _normal_cdf(np.asarray(e, dtype=float))
            bits = (U_iid < np.asarray(kappa, dtype=float)).astype(int).tolist()
        else:
            bits = deterministic_threshold_readout(kappa, thresh=0.5)

        types = stabilized_type_sequence(bits, m=params.scan_fold_m)
        total_types = max(len(types), 1)
        type_counts = Counter(types)
        p_types = {("".join(str(b) for b in k)): (v / total_types) for k, v in type_counts.items()}

        H_type = 0.0
        for p in p_types.values():
            if p > 0:
                H_type -= p * math.log(p)

        edges = transition_counts(types)
        hr = block_entropy_rate_proxy(bits, max_block_len=params.entropy_block_max)
        h_proxy = float(hr.get(str(params.entropy_block_max), 0.0))
        Hrate_by_eps.append(h_proxy)
        tau_est = empirical_tau_prefix(bits, tau_prefix_max=params.tau_prefix_max)

        # A more stable tau estimator: sequential Markov log-loss (prefix likelihood proxy).
        tau_markov = sequential_markov_tau(seq=bits, order=8, beta=0.5, max_len=512)
        Hrate_markov_by_eps.append(float(tau_markov["h_hat"]))

        # Correlated-noise robustness check (coupled via shared innovations e_t).
        # Use AR(1)-Gaussian-copula uniforms U_corr = Phi(z_t), z = AR1(e).
        if params.probabilistic_readout:
            z_corr = ar1_filter_from_innovations(np.asarray(e, dtype=float), rho=params.noise_rho)
            U_corr = _normal_cdf(z_corr)
            bits_corr = (U_corr < np.asarray(kappa, dtype=float)).astype(int).tolist()
        else:
            bits_corr = bits
        hr_corr = block_entropy_rate_proxy(bits_corr, max_block_len=params.entropy_block_max)
        h_proxy_corr = float(hr_corr.get(str(params.entropy_block_max), 0.0))
        Hrate_corr_by_eps.append(h_proxy_corr)

        # Protocol-parameter sensitivity: compare eps vs eps*(1+delta) under the same uniforms.
        eps2 = float(eps) * 1.05
        kappa2 = kappa_ball(h_scan, R=float(params.scan_R), eps=float(eps2))
        if params.probabilistic_readout:
            bits_eps2 = (U_iid < np.asarray(kappa2, dtype=float)).astype(int).tolist()
        else:
            bits_eps2 = deterministic_threshold_readout(kappa2, thresh=0.5)
        eps_mismatch = mismatch_rate(bits, bits_eps2)
        corr_mismatch = mismatch_rate(bits, bits_corr)

        symbolic_by_eps[str(eps)] = {
            "raw_bits": {
                "T": int(len(bits)),
                "mean": float(np.mean(bits)) if bits else 0.0,
                "block_entropy_rate_proxy": hr,
                "tau_prefix_plugin": tau_est,
                "tau_sequential_markov": tau_markov,
            },
            "raw_bits_correlated": {
                "noise_model": "AR1-Gaussian-copula-uniform",
                "rho": float(params.noise_rho),
                "lag1_autocorr": lag1_autocorr_bits(bits_corr),
                "block_entropy_rate_proxy": hr_corr,
                "h_proxy": float(h_proxy_corr),
            },
            "mismatch": {
                "definition": "epsilon = P(A_t != B_t) under a coupling (shared randomness / shared scan)",
                "eps2": float(eps2),
                "epsilon_eps_vs_eps2": float(eps_mismatch),
                "epsilon_iid_vs_correlated": float(corr_mismatch),
            },
            "stabilized": {
                "fold_m": int(params.scan_fold_m),
                "type_probabilities": {k: float(v) for k, v in p_types.items()},
                "entropy_H_type": float(H_type),
                "support_size": int(len(p_types)),
                "transition_edges": edges,
                "samples": int(total_types),
            },
            "summary": {
                "h_proxy": float(h_proxy),
                "h_theory": float(h_theory),
                "h_proxy_minus_theory": float(h_proxy - h_theory),
                "h_proxy_correlated": float(h_proxy_corr),
                "h_proxy_markov": float(tau_markov["h_hat"]),
            },
        }
        pp.tick(f"symbolic eps={eps:.3f} h_proxy={h_proxy:.4f} support={len(p_types)}")

    # Save JSON.
    json_path = out_dir / "demo_6d_fingerprints.json"
    # 1D factor diagnostics (from scan_beta / scan_h0 first coordinate).
    alpha = float(params.scan_beta[0] % 1.0)
    x0_1d = float(params.scan_h0[0] % 1.0)
    N_gap = 800
    pts_alpha = orbit_points_1d(alpha=alpha, x0=x0_1d, N=N_gap)
    gaps_alpha = three_gap_stats(pts_alpha)
    conv = continued_fraction_convergents(alpha, max_q=200)
    conv_pick = conv[-2:] if len(conv) >= 2 else conv
    gap_by_conv: Dict[str, object] = {}
    for p, q in conv_pick:
        pts = orbit_points_1d(alpha=float(p / q), x0=x0_1d, N=N_gap)
        gap_by_conv[f"{p}/{q}"] = three_gap_stats(pts)
    I_len = float(1.0 - (1.0 / ((1.0 + 5.0**0.5) / 2.0)))  # 1/phi^2
    Ns = np.array([50, 100, 200, 400, 800, 1200, 1600, 2000], dtype=int)
    bias_alpha: List[float] = []
    disc_alpha: List[float] = []
    for N in Ns:
        pts = orbit_points_1d(alpha=alpha, x0=x0_1d, N=int(N))
        bias_alpha.append(float(np.mean(pts < I_len) - I_len))
        disc_alpha.append(discrepancy_1d(pts))
    one_d_factor = {
        "alpha": alpha,
        "x0": x0_1d,
        "interval_I_len": I_len,
        "Ns": Ns.tolist(),
        "bias_abs": [float(abs(b)) for b in bias_alpha],
        "discrepancy": disc_alpha,
        "three_gap_alpha": gaps_alpha,
        "three_gap_convergents": gap_by_conv,
        "convergents_used": conv_pick,
    }

    # Rational approximant deviation: compare alpha vs convergents on a fixed-length prefix.
    N_sym = 5000
    bits_alpha = sturmian_bits(alpha=alpha, x0=x0_1d, I_len=I_len, N=N_sym)
    approx_dev: List[Dict[str, object]] = []
    for p, q in conv_pick:
        a_pq = float(p / q)
        pts_pq = orbit_points_1d(alpha=a_pq, x0=x0_1d, N=N_sym)
        pts_a = orbit_points_1d(alpha=alpha, x0=x0_1d, N=N_sym)
        d = np.abs(pts_a - pts_pq)
        d = np.minimum(d, 1.0 - d)
        bits_pq = (pts_pq < I_len).astype(int).tolist()
        approx_dev.append(
            {
                "p": int(p),
                "q": int(q),
                "p_over_q": float(a_pq),
                "abs_alpha_minus_p_over_q": float(abs(alpha - a_pq)),
                "max_phase_error_over_N": float(np.max(d)) if d.size > 0 else 0.0,
                "hamming_mismatch_bits_over_N": float(mismatch_rate(bits_alpha, bits_pq)),
                "periodicity_error_alpha_at_q": float(periodicity_error(bits_alpha, q)),
                "periodicity_error_p_over_q_at_q": float(periodicity_error(bits_pq, q)),
            }
        )
    one_d_factor["rational_approx_deviation"] = approx_dev

    payload = {
        "params": {
            "L": params.L,
            "R": params.R,
            "phases": params.phases,
            "eps_grid": params.eps_grid,
            "seed": params.seed,
            "grid_n": params.grid_n,
            "grid_dx": params.grid_dx,
            "phase0": phase0.tolist(),
            "peak_index": [peak_iy, peak_ix],
            "scan_T": params.scan_T,
            "scan_beta": list(params.scan_beta),
            "scan_h0": list(params.scan_h0),
            "scan_R": float(params.scan_R),
            "scan_fold_m": params.scan_fold_m,
            "entropy_block_max": params.entropy_block_max,
            "tau_prefix_max": params.tau_prefix_max,
            "probabilistic_readout": bool(params.probabilistic_readout),
        },
        "counts": {
            "points_in_patch": int(len(x0)),
            "lattice_points_box": int(len(pts6)),
        },
        "visibility": {
            "eps": params.eps_grid,
            "mean": V_mean,
            "std": V_std,
            "definition": "V(eps)=std(binned_density)/mean(binned_density) on a 2D slice of projected density",
        },
        "symbolic": {
            "params": {
                "readout": "A_t ~ Bernoulli(kappa_eps(h_t)) if probabilistic_readout else A_t = 1[kappa_eps(h_t)>=0.5]",
                "window_kernel": "kappa_eps(h)=1/(1+exp(-(R-||h||)/eps)) with sharp limit eps->0",
                "torus_representation": "internal phases represented in [-0.5,0.5)^3 with componentwise wrap",
                "scan_R": float(params.scan_R),
                "tau_estimator": "tau_sequential_markov: cumulative sequential K-order Markov log-loss (Laplace smoothing), a prefix likelihood proxy",
            },
            "degeneracy_histogram_exact": deg_hist,
            "by_eps": symbolic_by_eps,
            "h_theory_by_eps": {str(eps): float(ht) for eps, ht in zip(params.eps_grid, Htheory_by_eps)},
        },
        "one_dim_factor": one_d_factor,
        "notes": [
            "This uses a spherical window in internal space (boundary measure zero).",
            "Diffraction is a 2D slice from FFT of a binned projected density.",
            "Symbolic demo uses an internal scan on a 3-torus and a ball window kernel, then applies Zeckendorf Fold_m.",
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Additional output: closed-form Fourier-envelope check for a box window.
    # This is meant to concretize Sec 7.1.1 by providing an explicit w-hat.
    box_phase = rng.uniform(-0.5, 0.5, size=3)
    xB, uB = generate_model_set_points(pts6, A_T, Astar_T, R=params.R, phase_shift=box_phase)
    wB = smooth_box_weight(uB, L=params.box_L, eps=float(params.box_eps))
    # Subsample points to keep module evaluation lightweight.
    if len(xB) > params.module_max_points:
        idx = rng.choice(len(xB), size=int(params.module_max_points), replace=False)
        xB_sub = xB[idx]
    else:
        xB_sub = xB
    cand = module_candidates(params.module_K)
    k_phys = cand @ A_T
    k_int = cand @ Astar_T
    S_emp = empirical_structure_factor(xB_sub, k_phys)
    w_hat = box_window_fourier_hat(k_int, L=params.box_L)
    env = (np.abs(w_hat) ** 2).astype(float)
    # Report a simple scale-free comparison by normalizing both by their maxima.
    S_emp_n = (S_emp / max(float(np.max(S_emp)), 1e-12)).astype(float)
    env_n = (env / max(float(np.max(env)), 1e-12)).astype(float)

    # Quantitative goodness-of-fit metrics (scale-free, on normalized arrays).
    fit = {
        "pearson_r": _pearson_r(S_emp_n, env_n),
        "spearman_r": _spearman_r(S_emp_n, env_n),
        "r2_linear": _r2_fit(S_emp_n, env_n),
    }
    mlog = (S_emp_n > 1e-12) & (env_n > 1e-12)
    if np.any(mlog):
        fit["r2_log10"] = _r2_fit(np.log10(S_emp_n[mlog]), np.log10(env_n[mlog]))
        fit["pearson_r_log10"] = _pearson_r(np.log10(S_emp_n[mlog]), np.log10(env_n[mlog]))

    # A more robust "envelope consistency" check: strong empirical peaks should,
    # on average, have higher predicted envelope values than a random module point.
    k_phys_norm = np.linalg.norm(k_phys, axis=1)
    non_dc = k_phys_norm > 1e-9
    idx = np.argsort(S_emp_n[non_dc])[::-1]
    top_k = int(min(50, len(idx)))
    if top_k > 0:
        S_sub = S_emp_n[non_dc]
        E_sub = env_n[non_dc]
        top_idx = idx[:top_k]
        fit["top_peaks_K"] = int(top_k)
        fit["mean_envelope_top_peaks"] = float(np.mean(E_sub[top_idx]))
        fit["mean_envelope_all_non_dc"] = float(np.mean(E_sub))
        fit["envelope_lift_ratio"] = float(
            fit["mean_envelope_top_peaks"] / max(fit["mean_envelope_all_non_dc"], 1e-12)
        )

    box_json_path = out_dir / "demo_6d_box_window_fourier.json"
    box_payload = {
        "params": {
            "seed": int(params.seed),
            "L": int(params.L),
            "phase_shift": box_phase.tolist(),
            "box_L": list(params.box_L),
            "box_eps": float(params.box_eps),
            "module_K": int(params.module_K),
            "module_candidates": int(len(cand)),
            "module_max_points": int(params.module_max_points),
            "fourier_convention": "w_hat(xi)=int w(y) exp(-2pi i <xi,y>) dy",
        },
        "sample": {
            "points_total": int(len(xB)),
            "points_used": int(len(xB_sub)),
        },
        "fit": fit,
        "module": {
            "n": cand.astype(int).tolist(),
            "k_phys": k_phys.astype(float).tolist(),
            "k_int": k_int.astype(float).tolist(),
            "S_empirical": S_emp_n.tolist(),
            "envelope_predicted": env_n.tolist(),
        },
        "notes": [
            "This is a lightweight consistency check: module points are taken from Z^6 candidates and mapped using the same (A_T, Astar_T) matrices as the point embedding.",
            "S_empirical is computed from a subsampled accepted point cloud; envelope_predicted is |w_hat(k_int)|^2 for a box window (closed form).",
            "Both arrays are normalized by their maxima to remove overall scaling.",
        ],
    }
    box_json_path.write_text(json.dumps(box_payload, indent=2), encoding="utf-8")

    # Figure 1: diffraction slice (log-scaled).
    import matplotlib.pyplot as plt

    # Figure 0: tau(t) proxy for a reference epsilon (Markov sequential log-loss).
    eps_ref = float(params.eps_grid[len(params.eps_grid) // 2])
    ref = symbolic_by_eps[str(eps_ref)]["raw_bits"]["tau_sequential_markov"]
    tau_ref = ref["tau"]
    t_ref = np.arange(1, len(tau_ref) + 1, dtype=float)
    hth = float(symbolic_by_eps[str(eps_ref)]["summary"]["h_theory"])
    fig_tau, ax_tau = plt.subplots(figsize=(5.5, 3.8))
    ax_tau.plot(t_ref, tau_ref, lw=1.0, label=r"$\widehat{\tau}(t)$ (sequential Markov)")
    ax_tau.plot(t_ref, hth * t_ref, lw=1.0, ls="--", label=r"$t\,\mathbb{E}[H_b(\kappa_\epsilon)]$")
    ax_tau.set_xlabel("prefix length t")
    ax_tau.set_ylabel(r"$\widehat{\tau}(t)$ (nats)")
    ax_tau.set_title(f"6D demo: tau(t) proxy at epsilon={eps_ref:g}")
    ax_tau.grid(True, alpha=0.3)
    ax_tau.legend(fontsize=8)
    fig_tau.tight_layout()
    fig_tau_path = fig_out_dir / "demo_6d_tau_markov.png"
    fig_tau.savefig(fig_tau_path, dpi=160)
    plt.close(fig_tau)

    fig, ax = plt.subplots(figsize=(6.5, 5.4))
    ax.imshow(np.log10(I0 + 1e-6), cmap="magma", origin="lower")
    ax.set_title("6D icosahedral demo: diffraction slice (log10 intensity)")
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    fig_path = fig_out_dir / "demo_6d_diffraction_slice.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)

    # Figure 2: visibility curve.
    fig2, ax2 = plt.subplots(figsize=(5.5, 3.8))
    ax2.errorbar(params.eps_grid, V_mean, yerr=V_std, marker="o", ms=4, lw=1.0)
    ax2.set_xscale("log")
    ax2.set_xlabel("resolution scale epsilon")
    ax2.set_ylabel("visibility V(epsilon)")
    ax2.set_title("6D icosahedral demo: visibility vs resolution")
    ax2.grid(True, which="both", alpha=0.3)
    fig2.tight_layout()
    fig2_path = fig_out_dir / "demo_6d_visibility_curve.png"
    fig2.savefig(fig2_path, dpi=160)
    plt.close(fig2)

    # Figure 3: entropy-rate proxy vs resolution (from symbolic scan).
    fig3, ax3 = plt.subplots(figsize=(5.5, 3.8))
    ax3.plot(params.eps_grid, Hrate_by_eps, marker="o", ms=4, lw=1.0, label="block-entropy proxy")
    ax3.plot(params.eps_grid, Hrate_corr_by_eps, marker="^", ms=4, lw=1.0, label="proxy (correlated noise)")
    ax3.plot(params.eps_grid, Htheory_by_eps, marker="s", ms=4, lw=1.0, label="theory: mean H_b(kappa_eps)")
    ax3.set_xscale("log")
    ax3.set_xlabel("resolution scale epsilon")
    ax3.set_ylabel("entropy-rate proxy h_hat(eps)")
    ax3.set_title("6D icosahedral demo: h(eps) vs resolution (proxy vs theory)")
    ax3.grid(True, which="both", alpha=0.3)
    ax3.legend(fontsize=8)
    fig3.tight_layout()
    fig3_path = fig_out_dir / "demo_6d_entropy_rate_proxy.png"
    fig3.savefig(fig3_path, dpi=160)
    plt.close(fig3)

    # Figure 5: 1D factor diagnostics (finite-prefix bias + three-gap).
    fig5, (axA, axB) = plt.subplots(1, 2, figsize=(9.2, 3.6))
    axA.plot(Ns, np.abs(bias_alpha), marker="o", ms=4, lw=1.0, label="|empirical bias|")
    axA.plot(Ns, disc_alpha, marker="s", ms=4, lw=1.0, label="discrepancy D_N")
    axA.set_yscale("log")
    axA.set_xlabel("prefix length N")
    axA.set_title("1D factor: finite-prefix bias and discrepancy")
    axA.grid(True, which="both", alpha=0.3)
    axA.legend(fontsize=8)

    def _plot_gaps(ax: plt.Axes, stats: Dict[str, object], label: str) -> None:
        gaps = stats["gaps"]
        counts = stats["counts"]
        if not gaps:
            return
        ax.bar(np.arange(len(gaps)), counts, alpha=0.5, label=f"{label} (k={stats['distinct_gaps']})")

    _plot_gaps(axB, gaps_alpha, f"alpha≈{alpha:.6f}")
    for lab, st in gap_by_conv.items():
        _plot_gaps(axB, st, lab)
    axB.set_xlabel("distinct gap bins (quantized)")
    axB.set_ylabel("count")
    axB.set_title("three-gap statistics (N=800)")
    axB.grid(True, axis="y", alpha=0.3)
    axB.legend(fontsize=8)
    fig5.tight_layout()
    fig5_path = fig_out_dir / "demo_6d_1d_factor_gap_stats.png"
    fig5.savefig(fig5_path, dpi=160)
    plt.close(fig5)

    # Figure 6: diffraction slice vs window geometry/resolution.
    eps_pair = [float(params.eps_grid[0]), float(params.eps_grid[-2]) if len(params.eps_grid) >= 2 else float(params.eps_grid[-1])]
    fig6, axes = plt.subplots(2, 2, figsize=(8.4, 7.0))
    for j, epsw in enumerate(eps_pair):
        wb = smooth_ball_weight(u0, R=float(params.R), eps=float(epsw))
        imgb, _ = binned_density_2d(x0, wb, n=params.grid_n, dx=params.grid_dx)
        Ib = fft_intensity(imgb)
        axes[0, j].imshow(np.log10(Ib + 1e-6), cmap="magma", origin="lower")
        axes[0, j].set_title(f"ball window, eps={epsw:g}")
        axes[0, j].set_xticks([])
        axes[0, j].set_yticks([])

        wx = smooth_box_weight(u0, L=params.box_L, eps=float(epsw))
        imgx, _ = binned_density_2d(x0, wx, n=params.grid_n, dx=params.grid_dx)
        Ix = fft_intensity(imgx)
        axes[1, j].imshow(np.log10(Ix + 1e-6), cmap="magma", origin="lower")
        axes[1, j].set_title(f"box window, eps={epsw:g}")
        axes[1, j].set_xticks([])
        axes[1, j].set_yticks([])
    fig6.suptitle("6D demo: diffraction slice vs window geometry/resolution", y=0.995)
    fig6.tight_layout()
    fig6_path = fig_out_dir / "demo_6d_window_geometry_diffraction.png"
    fig6.savefig(fig6_path, dpi=160)
    plt.close(fig6)

    # Figure 4: box-window Fourier envelope vs empirical module intensities.
    fig4, ax4 = plt.subplots(figsize=(5.6, 4.2))
    ax4.scatter(env_n, S_emp_n, s=10, alpha=0.6)
    ax4.set_xlabel("predicted envelope |w_hat(k*)|^2 (normalized)")
    ax4.set_ylabel("empirical S(k) (normalized)")
    ax4.set_title("6D demo (box window): envelope vs empirical module intensities")
    ax4.grid(True, alpha=0.3)
    fig4.tight_layout()
    fig4_path = fig_out_dir / "demo_6d_box_window_envelope_scatter.png"
    fig4.savefig(fig4_path, dpi=160)
    plt.close(fig4)

    return {
        "demo_6d_fingerprints.json": str(json_path),
        "demo_6d_diffraction_slice.png": str(fig_path),
        "demo_6d_visibility_curve.png": str(fig2_path),
        "demo_6d_entropy_rate_proxy.png": str(fig3_path),
        "demo_6d_tau_markov.png": str(fig_tau_path),
        "demo_6d_box_window_fourier.json": str(box_json_path),
        "demo_6d_box_window_envelope_scatter.png": str(fig4_path),
        "demo_6d_1d_factor_gap_stats.png": str(fig5_path),
        "demo_6d_window_geometry_diffraction.png": str(fig6_path),
    }


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=str, required=True, help="Output directory for data artifacts/")
    ap.add_argument("--fig-out", type=str, required=True, help="Output directory for figures/")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    out_dir = Path(args.out)
    fig_out_dir = Path(args.fig_out)
    outputs = run_demo(out_dir=out_dir, fig_out_dir=fig_out_dir, seed=int(args.seed))
    for k, v in outputs.items():
        print(f"[demo_6d] wrote {k}: {v}", flush=True)


if __name__ == "__main__":
    main()

