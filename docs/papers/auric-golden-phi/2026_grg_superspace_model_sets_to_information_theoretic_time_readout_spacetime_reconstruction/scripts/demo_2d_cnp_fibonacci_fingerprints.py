#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demo B: 2D cut-and-project -> 1D Fibonacci model set fingerprints.

Outputs:
- 1D diffraction/structure-factor estimate on a finite patch
- a resolution-dependent 'visibility' curve V(epsilon) via fuzzified windows
- an optional Fold_m degeneracy histogram (purely combinatorial)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from common_progress import ProgressPrinter
from fold_zeckendorf import exact_degeneracy_histogram, fold_m


@dataclass(frozen=True)
class Demo2DParams:
    lattice_L: int
    window_len: float
    window_center: float
    phases: int
    seed: int
    eps_grid: List[float]
    k_max: float
    k_steps: int
    bin_dx: float
    fold_m: int


def orthonormal_basis_fibonacci() -> Tuple[np.ndarray, np.ndarray]:
    """Return (e_parallel, e_perp) for slope phi in Z^2 embedding."""
    phi = (1.0 + 5.0**0.5) / 2.0
    e_par = np.array([1.0, phi], dtype=float)
    e_par /= np.linalg.norm(e_par)
    e_perp = np.array([-phi, 1.0], dtype=float)
    e_perp /= np.linalg.norm(e_perp)
    return e_par, e_perp


def smooth_window_weight(u: np.ndarray, a: float, b: float, eps: float) -> np.ndarray:
    """Smooth indicator for interval [a,b] using logistic boundary layers."""
    if eps <= 0:
        return ((u >= a) & (u <= b)).astype(float)
    # Product of two sigmoids: inside gives ~1, outside decays.
    x1 = (u - a) / eps
    x2 = (b - u) / eps
    s1 = 1.0 / (1.0 + np.exp(-x1))
    s2 = 1.0 / (1.0 + np.exp(-x2))
    return s1 * s2


def generate_fibonacci_model_set(
    L: int,
    window_center: float,
    window_len: float,
    phase_shift: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return physical coords x, internal coords u, and sharp acceptance mask."""
    e_par, e_perp = orthonormal_basis_fibonacci()
    pts = []
    for i in range(-L, L + 1):
        for j in range(-L, L + 1):
            pts.append((i, j))
    Z = np.array(pts, dtype=float)
    x = Z @ e_par
    u = Z @ e_perp

    a = window_center - 0.5 * window_len + phase_shift
    b = window_center + 0.5 * window_len + phase_shift
    mask = (u >= a) & (u < b)
    return x[mask], u[mask], mask


def structure_factor_1d(x: np.ndarray, weights: np.ndarray, k: np.ndarray) -> np.ndarray:
    """S(k) = |sum w exp(-2pi i k x)|^2 / (sum w)^2."""
    wsum = float(np.sum(weights))
    if wsum <= 0:
        return np.zeros_like(k)
    phases = np.exp(-2j * np.pi * np.outer(k, x))
    amp = phases @ weights
    S = (np.abs(amp) ** 2) / (wsum**2)
    return S.real


def pick_reference_peak(k: np.ndarray, S: np.ndarray) -> float:
    """Pick a representative nonzero peak location (avoid k~0)."""
    idx = np.argsort(S)[::-1]
    for i in idx[: min(200, len(idx))]:
        if abs(k[i]) > 1e-6:
            return float(k[i])
    return float(k[len(k) // 2])


def pointset_to_binned_sequence(x: np.ndarray, dx: float) -> List[int]:
    """Bin points into a 0/1 occupancy sequence along the x-axis."""
    if len(x) == 0:
        return []
    xmin = float(np.min(x))
    xmax = float(np.max(x))
    nb = int(math.ceil((xmax - xmin) / dx)) + 1
    occ = np.zeros(nb, dtype=int)
    idx = np.floor((x - xmin) / dx).astype(int)
    idx = np.clip(idx, 0, nb - 1)
    occ[idx] = 1
    return occ.tolist()


def contrast_statistic_from_bins(x: np.ndarray, weights: np.ndarray, dx: float) -> float:
    """A simple visibility/contrast statistic: coefficient of variation of binned intensity."""
    if len(x) == 0:
        return 0.0
    xmin = float(np.min(x))
    xmax = float(np.max(x))
    nb = int(math.ceil((xmax - xmin) / dx)) + 1
    if nb <= 1:
        return 0.0
    bins = np.zeros(nb, dtype=float)
    idx = np.floor((x - xmin) / dx).astype(int)
    idx = np.clip(idx, 0, nb - 1)
    np.add.at(bins, idx, weights)
    m = float(np.mean(bins))
    s = float(np.std(bins))
    return float(s / max(m, 1e-12))


def stabilized_type_sequence(bits: List[int], m: int) -> List[Tuple[int, ...]]:
    if len(bits) < m:
        return []
    out: List[Tuple[int, ...]] = []
    for i in range(len(bits) - m + 1):
        out.append(fold_m(bits[i : i + m]))
    return out


def run_demo(out_dir: Path, fig_out_dir: Path, seed: int = 0) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_out_dir.mkdir(parents=True, exist_ok=True)
    params = Demo2DParams(
        lattice_L=70,
        window_len=1.0,
        window_center=0.0,
        phases=16,
        seed=seed,
        eps_grid=[0.002, 0.005, 0.01, 0.02, 0.05, 0.1],
        k_max=12.0,
        k_steps=2401,
        bin_dx=0.18,
        fold_m=12,
    )

    rng = np.random.default_rng(params.seed)
    pp = ProgressPrinter("demo_2d")

    # Diffraction on one sharp phase (small eps ~ sharp).
    phase0 = float(rng.uniform(-0.5, 0.5))
    x0, u0, _ = generate_fibonacci_model_set(
        L=params.lattice_L,
        window_center=params.window_center,
        window_len=params.window_len,
        phase_shift=phase0,
    )
    # Normalize by subtracting mean for numerical stability (does not change |amp|^2).
    x0 = x0 - float(np.mean(x0))
    k = np.linspace(-params.k_max, params.k_max, params.k_steps)
    w0 = np.ones_like(x0)
    S0 = structure_factor_1d(x0, w0, k)
    k_ref = pick_reference_peak(k, S0)
    pp.tick(f"diffraction points={len(x0)} k_ref={k_ref:.3f}")

    # Visibility curve with phase averaging.
    V_mean = []
    V_std = []
    for eps in params.eps_grid:
        V_phase = []
        for p_i in range(params.phases):
            phase = float(rng.uniform(-0.5, 0.5))
            x, u, _ = generate_fibonacci_model_set(
                L=params.lattice_L,
                window_center=params.window_center,
                window_len=params.window_len,
                phase_shift=phase,
            )
            x = x - float(np.mean(x))
            a = params.window_center - 0.5 * params.window_len + phase
            b = params.window_center + 0.5 * params.window_len + phase
            w = smooth_window_weight(u, a=a, b=b, eps=eps)
            # Visibility/contrast as variance-based statistic (see paper Sec 07).
            V = contrast_statistic_from_bins(x, weights=w, dx=params.bin_dx)
            V_phase.append(V)
            pp.tick(f"eps={eps:.4f} phase={p_i+1}/{params.phases} V={V:.3f}")
        V_mean.append(float(np.mean(V_phase)))
        V_std.append(float(np.std(V_phase)))

    # Optional Fold demo: take a binned occupancy sequence and stabilize.
    bits = pointset_to_binned_sequence(x0, dx=params.bin_dx)
    types = stabilized_type_sequence(bits, m=params.fold_m)
    type_counts: Dict[str, int] = {}
    for t in types:
        key = "".join(str(b) for b in t)
        type_counts[key] = type_counts.get(key, 0) + 1
    deg = exact_degeneracy_histogram(params.fold_m)
    deg_hist = {str(k): int(v) for k, v in sorted(deg.histogram().items())}

    # Save JSON payload.
    json_path = out_dir / "demo_2d_fingerprints.json"
    payload = {
        "params": {
            "lattice_L": params.lattice_L,
            "window_len": params.window_len,
            "window_center": params.window_center,
            "phases": params.phases,
            "seed": params.seed,
            "eps_grid": params.eps_grid,
            "k_max": params.k_max,
            "k_steps": params.k_steps,
            "bin_dx": params.bin_dx,
            "fold_m": params.fold_m,
            "phase0": phase0,
            "k_ref": k_ref,
            "visibility_bin_dx": params.bin_dx,
        },
        "visibility": {
            "eps": params.eps_grid,
            "mean": V_mean,
            "std": V_std,
            "definition": "V(eps)=std(binned_intensity)/mean(binned_intensity), binned along x with bin width bin_dx",
        },
        "fold": {
            "degeneracy_histogram_exact": deg_hist,
            "stabilized_type_counts_empirical": type_counts,
            "raw_bits_length": len(bits),
            "stabilized_samples": len(types),
        },
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Plot diffraction S(k).
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(k, S0, lw=0.8)
    ax.set_xlabel("k")
    ax.set_ylabel("S(k)")
    ax.set_title("Finite-patch structure factor (Fibonacci model set)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig_path = fig_out_dir / "demo_2d_diffraction.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)

    # Plot visibility curve.
    fig2, ax2 = plt.subplots(figsize=(5.5, 3.6))
    ax2.errorbar(params.eps_grid, V_mean, yerr=V_std, marker="o", ms=4, lw=1.0)
    ax2.set_xscale("log")
    ax2.set_xlabel("resolution scale epsilon")
    ax2.set_ylabel("visibility V(epsilon)")
    ax2.set_title("Visibility vs resolution (phase-averaged)")
    ax2.grid(True, which="both", alpha=0.3)
    fig2.tight_layout()
    fig2_path = fig_out_dir / "demo_2d_visibility_curve.png"
    fig2.savefig(fig2_path, dpi=160)
    plt.close(fig2)

    # Plot degeneracy histogram.
    ks = np.array([int(k) for k in deg_hist.keys()], dtype=int)
    vs = np.array([deg_hist[str(k)] for k in ks], dtype=int)
    # Long-tail distributions can be visually dominated by rare large fibers.
    # Use a split view: left panel shows the bulk, right panel summarizes the tail.
    split_x = 64
    bulk = ks <= split_x
    tail = ks > split_x
    fig3, (axL, axR) = plt.subplots(1, 2, figsize=(8.6, 3.6), gridspec_kw={"width_ratios": [3, 2]})
    axL.bar(ks[bulk], vs[bulk], width=0.8, alpha=0.85)
    axL.set_xlim(0, split_x + 1)
    axL.set_xlabel("fiber size |F_m(x)| (bulk)")
    axL.set_ylabel("count of stabilized types")
    axL.grid(True, axis="y", alpha=0.3)

    if np.any(tail):
        axR.axis("off")
        # Summarize the tail as a small table, which is more readable when the
        # tail is extremely sparse (often a single outlier at modest m).
        tail_pairs = sorted([(int(k), int(v)) for k, v in zip(ks[tail], vs[tail])], reverse=True)
        top_k = tail_pairs[:8]
        lines = ["Tail summary (|F_m(x)| > 64):", ""]
        for size, count in top_k:
            lines.append(f"- size={size}: count={count}")
        if len(tail_pairs) > len(top_k):
            lines.append(f"... ({len(tail_pairs) - len(top_k)} more)")
        # If there is a unique maximum fiber, also report one representative type.
        max_size = max(int(k) for k in ks)
        max_types = [k for k, v in deg.fiber_sizes.items() if v == max_size]
        if len(max_types) == 1:
            w = "".join(str(b) for b in max_types[0])
            lines += ["", f"max type (example): {w}"]
        axR.text(0.0, 1.0, "\n".join(lines), va="top", ha="left", fontsize=9, family="monospace")
    else:
        axR.axis("off")

    fig3.suptitle(f"Exact degeneracy histogram (m={params.fold_m})", y=1.02)
    fig3.tight_layout()
    fig3_path = fig_out_dir / "demo_2d_degeneracy_hist.png"
    fig3.savefig(fig3_path, dpi=160)
    plt.close(fig3)

    return {
        "demo_2d_fingerprints.json": str(json_path),
        "demo_2d_diffraction.png": str(fig_path),
        "demo_2d_visibility_curve.png": str(fig2_path),
        "demo_2d_degeneracy_hist.png": str(fig3_path),
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
        print(f"[demo_2d] wrote {k}: {v}", flush=True)


if __name__ == "__main__":
    main()

