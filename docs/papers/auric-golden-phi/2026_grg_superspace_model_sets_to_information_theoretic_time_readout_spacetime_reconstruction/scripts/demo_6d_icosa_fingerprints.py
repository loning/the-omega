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


def bernoulli_readout(rng: np.random.Generator, p: np.ndarray) -> List[int]:
    """Sample bits with P(bit=1)=p (independent given the scan)."""
    u = rng.random(size=len(p))
    return (u < p).astype(int).tolist()


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
    for eps in params.eps_grid:
        kappa = kappa_ball(h_scan, R=float(params.scan_R), eps=float(eps))
        if params.probabilistic_readout:
            bits = bernoulli_readout(rng, kappa)
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

        symbolic_by_eps[str(eps)] = {
            "raw_bits": {
                "T": int(len(bits)),
                "mean": float(np.mean(bits)) if bits else 0.0,
                "block_entropy_rate_proxy": hr,
                "tau_prefix_plugin": tau_est,
            },
            "stabilized": {
                "fold_m": int(params.scan_fold_m),
                "type_probabilities": {k: float(v) for k, v in p_types.items()},
                "entropy_H_type": float(H_type),
                "support_size": int(len(p_types)),
                "transition_edges": edges,
                "samples": int(total_types),
            },
            "summary": {"h_proxy": float(h_proxy)},
        }
        pp.tick(f"symbolic eps={eps:.3f} h_proxy={h_proxy:.4f} support={len(p_types)}")

    # Save JSON.
    json_path = out_dir / "demo_6d_fingerprints.json"
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
            },
            "degeneracy_histogram_exact": deg_hist,
            "by_eps": symbolic_by_eps,
        },
        "notes": [
            "This uses a spherical window in internal space (boundary measure zero).",
            "Diffraction is a 2D slice from FFT of a binned projected density.",
            "Symbolic demo uses an internal scan on a 3-torus and a ball window kernel, then applies Zeckendorf Fold_m.",
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Figure 1: diffraction slice (log-scaled).
    import matplotlib.pyplot as plt

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
    ax3.plot(params.eps_grid, Hrate_by_eps, marker="o", ms=4, lw=1.0)
    ax3.set_xscale("log")
    ax3.set_xlabel("resolution scale epsilon")
    ax3.set_ylabel("entropy-rate proxy h_hat(eps)")
    ax3.set_title("6D icosahedral demo: entropy-rate proxy vs resolution")
    ax3.grid(True, which="both", alpha=0.3)
    fig3.tight_layout()
    fig3_path = fig_out_dir / "demo_6d_entropy_rate_proxy.png"
    fig3.savefig(fig3_path, dpi=160)
    plt.close(fig3)

    return {
        "demo_6d_fingerprints.json": str(json_path),
        "demo_6d_diffraction_slice.png": str(fig_path),
        "demo_6d_visibility_curve.png": str(fig2_path),
        "demo_6d_entropy_rate_proxy.png": str(fig3_path),
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

