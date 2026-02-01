#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1D slice phase curve for arity-charge: t -> (P_chi(t), log Mfrak_chi(t)).

We take the chi-direction slice
  theta(t) = (theta_e, theta_neg, theta_2) = (t, 0, -t),
so that exp(theta · Phi) includes the linear arity-charge chi = phi_e - phi_2.

Closed form interface used (Möbius tail, k>=2):
  log Mfrak(theta) = log C(theta) + sum_{k>=2} mu(k)/k * log zeta_theta(z_star(theta)^k)

where zeta_theta(z) = 1 / det(I - z M_theta), lambda(theta)=rho(M_theta),
z_star(theta)=1/lambda(theta), and C(theta) is the residue constant at z_star.

Outputs (default):
- artifacts/export/sync_kernel_real_input_40_logM_chi.json
- artifacts/export/sync_kernel_real_input_40_logM_chi.png
- sections/generated/fig_real_input_40_logM_chi.tex
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

from common_paths import export_dir, generated_dir
from common_phi_fold import Progress
from exp_sync_kernel_real_input_40 import (
    build_kernel_edges,
    build_kernel_map,
    build_real_input_states,
    build_weighted_matrix,
    mobius,
    spectral_radius,
)


@dataclass(frozen=True)
class SliceSpec:
    t_min: float
    t_max: float
    t_steps: int
    theta_neg: float


def linspace(min_val: float, max_val: float, steps: int) -> List[float]:
    if steps <= 1:
        return [0.5 * (min_val + max_val)]
    return [min_val + (max_val - min_val) * i / float(steps - 1) for i in range(steps)]


def log_zeta_from_matrix(M: np.ndarray, z: float) -> float:
    """Return log zeta(z) = -log det(I - z M) via slogdet."""
    n = M.shape[0]
    sign, logabs = np.linalg.slogdet(np.eye(n) - z * M)
    if sign == 0:
        raise ValueError("singular det in log_zeta_from_matrix")
    return -float(logabs)


def logC_from_eigvals(eigs: np.ndarray, lam_idx: int) -> float:
    """Compute log C from eigenvalues (simple PF eigenvalue).

    det(I - z M) = Π_j (1 - z λ_j).
    At z_star = 1/lambda, the residue constant satisfies
      C = 1 / Π_{j≠PF} (1 - λ_j / lambda).
    """
    lam = eigs[lam_idx]
    prod = 1.0 + 0.0j
    for j, ev in enumerate(eigs):
        if j == lam_idx:
            continue
        prod *= (1.0 - ev / lam)
    C = 1.0 / prod
    C_re = float(np.real(C))
    if not math.isfinite(C_re) or C_re <= 0.0:
        raise ValueError("invalid C from eigvals")
    return math.log(C_re)


def logM_mobius_tail(
    M: np.ndarray,
    lam: float,
    logC: float,
    k_max: int,
) -> float:
    z_star = 1.0 / lam
    s = 0.0
    for k in range(2, k_max + 1):
        mu = mobius(k)
        if mu == 0:
            continue
        s += (float(mu) / float(k)) * log_zeta_from_matrix(M, z_star**k)
    return logC + s


def compute_at_t(
    t: float,
    theta_neg: float,
    k_max: int,
    states: List[Tuple[str, int, int]],
    kernel_map: Dict[Tuple[str, int], Tuple[str, int]],
) -> Tuple[float, float, float]:
    """Return (lambda(t), P_chi(t), logM_chi(t))."""
    theta_e = t
    theta_2 = -t
    M = build_weighted_matrix(theta_e, theta_neg, theta_2, states, kernel_map)
    eigs = np.linalg.eigvals(M)
    lam_idx = int(np.argmax(np.abs(eigs)))
    lam = float(np.real(eigs[lam_idx]))
    if lam <= 0.0 or not math.isfinite(lam):
        lam = spectral_radius(M)
    if lam <= 0.0 or not math.isfinite(lam):
        raise ValueError("invalid spectral radius")
    logC = logC_from_eigvals(eigs, lam_idx=lam_idx)
    P = math.log(lam)
    logM = logM_mobius_tail(M, lam=lam, logC=logC, k_max=k_max)
    return lam, P, logM


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_fig_tex(fig_name: str, png_rel: str, caption: str, label: str) -> None:
    p = generated_dir() / f"{fig_name}.tex"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "\\begin{figure}[H]\n"
        "\\centering\n"
        f"\\includegraphics[width=0.92\\linewidth]{{{png_rel}}}\n"
        f"\\caption{{{caption}}}\n"
        f"\\label{{{label}}}\n"
        "\\end{figure}\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Real-input-40: chi-slice logM and pressure curve")
    parser.add_argument("--t-min", type=float, default=-1.0)
    parser.add_argument("--t-max", type=float, default=1.0)
    parser.add_argument("--t-steps", type=int, default=161)
    parser.add_argument("--theta-neg", type=float, default=0.0)
    parser.add_argument("--k-max", type=int, default=250, help="Max k for Möbius tail series")
    parser.add_argument("--diff-step", type=float, default=1e-4, help="Step for derivatives at t=0")
    parser.add_argument("--no-output", action="store_true", help="Skip writing outputs")
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Output JSON path (default: artifacts/export/sync_kernel_real_input_40_logM_chi.json)",
    )
    args = parser.parse_args()

    prog = Progress(label="real-input-40-logM-chi", every_seconds=20.0)
    edges = build_kernel_edges()
    kernel_map = build_kernel_map(edges)
    states = build_real_input_states()

    spec = SliceSpec(
        t_min=args.t_min,
        t_max=args.t_max,
        t_steps=args.t_steps,
        theta_neg=args.theta_neg,
    )
    ts = linspace(spec.t_min, spec.t_max, spec.t_steps)

    lam_vals: List[float] = []
    P_vals: List[float] = []
    logM_vals: List[float] = []
    for i, t in enumerate(ts):
        lam, P, logM = compute_at_t(
            t=t,
            theta_neg=spec.theta_neg,
            k_max=args.k_max,
            states=states,
            kernel_map=kernel_map,
        )
        lam_vals.append(lam)
        P_vals.append(P)
        logM_vals.append(logM)
        prog.tick(f"chi-slice i={i+1}/{len(ts)}")

    # Derivatives at t=0 (finite differences)
    h = float(args.diff_step)
    _, Pp, _ = compute_at_t(
        t=+h,
        theta_neg=spec.theta_neg,
        k_max=max(10, args.k_max // 10),
        states=states,
        kernel_map=kernel_map,
    )
    _, Pm, _ = compute_at_t(
        t=-h,
        theta_neg=spec.theta_neg,
        k_max=max(10, args.k_max // 10),
        states=states,
        kernel_map=kernel_map,
    )
    _, P0, _ = compute_at_t(
        t=0.0,
        theta_neg=spec.theta_neg,
        k_max=max(10, args.k_max // 10),
        states=states,
        kernel_map=kernel_map,
    )
    P_chi_prime_0 = (Pp - Pm) / (2.0 * h)
    P_chi_second_0 = (Pp - 2.0 * P0 + Pm) / (h * h)

    print(
        f"[real-input-40-logM-chi] sample t=0 lambda={math.exp(P0):.12g} P_chi(0)={P0:.12g} "
        f"P_chi'(0)={P_chi_prime_0:.12g} P_chi''(0)={P_chi_second_0:.12g}",
        flush=True,
    )

    # Plot
    out_png = export_dir() / "sync_kernel_real_input_40_logM_chi.png"
    plt.figure(figsize=(7.2, 4.8))
    plt.plot(ts, logM_vals, linewidth=1.6, label=r"$\log\mathfrak{M}_\chi(t)$")
    plt.plot(ts, P_vals, linewidth=1.3, linestyle="--", label=r"$P_\chi(t)$")
    plt.axvline(0.0, color="k", linewidth=0.8, alpha=0.35)
    plt.xlabel(r"$t$ (chi-slice: $\theta=(t,0,-t)$)")
    plt.ylabel("value")
    plt.title("Real-input-40: chi-slice phase curve")
    plt.legend(loc="best", fontsize=9)
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=200)
    plt.close()

    payload: Dict[str, object] = {
        "theta_slice": {"theta_e": "t", "theta_neg": spec.theta_neg, "theta_2": "-t"},
        "t_values": ts,
        "lambda_values": lam_vals,
        "P_chi_values": P_vals,
        "logM_chi_values": logM_vals,
        "k_max": args.k_max,
        "diff_step": h,
        "P_chi_prime_0": P_chi_prime_0,
        "P_chi_second_0": P_chi_second_0,
        "gamma": 0.5772156649015329,
    }

    if not args.no_output:
        out_json = Path(args.output) if args.output else export_dir() / "sync_kernel_real_input_40_logM_chi.json"
        write_json(out_json, payload)
        write_fig_tex(
            fig_name="fig_real_input_40_logM_chi",
            png_rel="artifacts/export/sync_kernel_real_input_40_logM_chi.png",
            caption="真实输入 40 状态核下，沿 arity-charge 方向 $\\theta=(t,0,-t)$ 的一维切片相图：压力 $P_\\chi(t)=\\log\\rho(M_{\\theta(t)})$ 与 Abel 有限部常数曲线 $\\log\\mathfrak{M}_\\chi(t)$（脚本生成）。",
            label="fig:real_input_40_logM_chi",
        )
        print(f"[real-input-40-logM-chi] wrote {out_json}", flush=True)
        print(f"[real-input-40-logM-chi] wrote {out_png}", flush=True)
        print(
            f"[real-input-40-logM-chi] wrote {generated_dir() / 'fig_real_input_40_logM_chi.tex'}",
            flush=True,
        )

    print("[real-input-40-logM-chi] done", flush=True)


if __name__ == "__main__":
    main()

