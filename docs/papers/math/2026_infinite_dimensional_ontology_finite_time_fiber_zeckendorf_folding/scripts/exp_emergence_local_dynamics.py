#!/usr/bin/env python3
"""
Toy local dynamics on a 3D grid to probe 'emergent physics' observables.

State at each voxel v:
  - x_v in X_m  (no-adjacent-ones word)
  - r_v in Z_q  (finite residual carrier)

We run two coupled simulations:
  - baseline
  - perturbed (a localized change at the center at t=0)
and track:
  - disturbance radius over time (graph distance on the 3D lattice)
  - correlation vs distance for interface indicator (B_m membership)
  - residual activity contrast: interface vs bulk

Outputs:
  - artifacts/emergence_local_dynamics/<run_id>/summary.json
  - artifacts/emergence_local_dynamics/<run_id>/disturbance_radius.png
  - artifacts/emergence_local_dynamics/<run_id>/correlation.png
  - artifacts/emergence_local_dynamics/<run_id>/residual_activity.png
  - sections/generated/emergence_metrics.tex
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import export_dir
from common_paths import generated_dir
from common_progress import Progress
from common_zeckendorf import iter_no_adjacent_words, no_adjacent_ones_mask_ok, word_bit, word_bits_high_to_low_str


def is_in_Cm(x: int, m: int) -> bool:
    if not no_adjacent_ones_mask_ok(x):
        return False
    if m <= 1:
        return True
    return not (word_bit(x, 0) == 1 and word_bit(x, m - 1) == 1)


def is_in_Bm(x: int, m: int) -> bool:
    return no_adjacent_ones_mask_ok(x) and (m > 1) and (word_bit(x, 0) == 1 and word_bit(x, m - 1) == 1)


def neighbors_3d(idx: int, nx: int, ny: int, nz: int) -> List[int]:
    z = idx // (nx * ny)
    rem = idx % (nx * ny)
    y = rem // nx
    x = rem % nx
    out: List[int] = []
    if x > 0:
        out.append(idx - 1)
    if x + 1 < nx:
        out.append(idx + 1)
    if y > 0:
        out.append(idx - nx)
    if y + 1 < ny:
        out.append(idx + nx)
    if z > 0:
        out.append(idx - nx * ny)
    if z + 1 < nz:
        out.append(idx + nx * ny)
    return out


def avg_neighbor_bit(x_grid: np.ndarray, nbrs: List[int], bit_i: int) -> float:
    if not nbrs:
        return 0.0
    s = 0.0
    for j in nbrs:
        s += float((int(x_grid[j]) >> bit_i) & 1)
    return s / float(len(nbrs))

def avg_neighbor_r(r_grid: np.ndarray, nbrs: List[int]) -> float:
    if not nbrs:
        return float(r_grid[0]) if r_grid.shape[0] > 0 else 0.0
    s = 0.0
    for j in nbrs:
        s += float(int(r_grid[j]))
    return s / float(len(nbrs))


def propose_update_x(x: int, m: int, bit_i: int, nbr_mean: float, threshold: float) -> int:
    """
    Update a single bit using neighbor mean, while enforcing no-adjacent-ones constraint.
    """
    want1 = 1 if (nbr_mean >= threshold) else 0
    if want1 == 0:
        return x & ~(1 << bit_i)

    # want1 == 1: allowed only if adjacent bits are 0 (linear adjacency inside word)
    left_ok = True
    right_ok = True
    if bit_i - 1 >= 0:
        left_ok = (((x >> (bit_i - 1)) & 1) == 0)
    if bit_i + 1 < m:
        right_ok = (((x >> (bit_i + 1)) & 1) == 0)
    if left_ok and right_ok:
        return x | (1 << bit_i)
    return x & ~(1 << bit_i)

def inject_interface_defect(x: int, m: int) -> int:
    """
    Force x into B_m (interface/defect state) by setting end bits to 1 and clearing adjacent bits.
    This keeps linear no-adjacent-ones validity.
    """
    if m <= 1:
        return x
    x |= (1 << 0)
    x |= (1 << (m - 1))
    # Clear adjacent bits to satisfy linear constraint near ends.
    if m >= 2:
        x &= ~(1 << 1)
        x &= ~(1 << (m - 2))
    return x

def logistic(u: float) -> float:
    if u >= 60.0:
        return 1.0
    if u <= -60.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-u))


@dataclass(frozen=True)
class StepStats:
    disturbance_radius: float
    interface_frac: float
    residual_activity_mean: float
    residual_activity_interface_mean: float
    residual_activity_bulk_mean: float


def disturbance_radius(diff_mask: np.ndarray, nx: int, ny: int, nz: int, center: int) -> float:
    """
    Max Manhattan distance from center among sites where diff_mask is True.
    """
    if not bool(diff_mask.any()):
        return 0.0
    cz = center // (nx * ny)
    cre = center % (nx * ny)
    cy = cre // nx
    cx = cre % nx
    idxs = np.nonzero(diff_mask)[0]
    rmax = 0
    for idx in idxs.tolist():
        z = idx // (nx * ny)
        rem = idx % (nx * ny)
        y = rem // nx
        x = rem % nx
        d = abs(x - cx) + abs(y - cy) + abs(z - cz)
        if d > rmax:
            rmax = d
    return float(rmax)


def correlation_by_distance(values: np.ndarray, nx: int, ny: int, ny2: int, nz: int, max_d: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute C(d) = E[(v_i - mu)(v_j - mu)] over pairs at Manhattan distance d.
    """
    # Note: ny2 is unused; kept to avoid accidental signature mismatch in edits.
    mu = float(values.mean())
    vals = values.astype(np.float64) - mu
    num = np.zeros(max_d + 1, dtype=np.float64)
    den = np.zeros(max_d + 1, dtype=np.float64)

    # Precompute coordinates.
    coords = []
    for idx in range(values.shape[0]):
        z = idx // (nx * ny)
        rem = idx % (nx * ny)
        y = rem // nx
        x = rem % nx
        coords.append((x, y, z))

    for i in range(values.shape[0]):
        xi, yi, zi = coords[i]
        vi = vals[i]
        # Only look forward to avoid double count.
        for j in range(i + 1, values.shape[0]):
            xj, yj, zj = coords[j]
            d = abs(xi - xj) + abs(yi - yj) + abs(zi - zj)
            if d <= max_d:
                num[d] += vi * vals[j]
                den[d] += 1.0

    C = np.zeros(max_d + 1, dtype=np.float64)
    for d in range(max_d + 1):
        C[d] = (num[d] / den[d]) if den[d] > 0 else 0.0
    ds = np.arange(max_d + 1, dtype=np.int64)
    return ds, C


def write_emergence_tex(m: int, q: int, nx: int, ny: int, nz: int, steps: int, summary: Dict[str, float], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("% Auto-generated by scripts/exp_emergence_local_dynamics.py")
    lines.append("\\begin{tabular}{lr}")
    lines.append("\\toprule")
    lines.append("Quantity & Value\\\\")
    lines.append("\\midrule")
    lines.append(f"$m$ & {m}\\\\")
    lines.append(f"$q$ & {q}\\\\")
    lines.append(f"grid $(n_x,n_y,n_z)$ & ({nx},{ny},{nz})\\\\")
    lines.append(f"steps & {steps}\\\\")
    lines.append(f"final disturbance radius & {summary['radius_final']:.3f}\\\\")
    lines.append(f"max disturbance radius & {summary['radius_max']:.3f}\\\\")
    lines.append(f"final interface fraction & {summary['interface_frac_final']:.4f}\\\\")
    lines.append(f"max interface fraction & {summary['interface_frac_max']:.4f}\\\\")
    lines.append(f"max cluster size (interface) & {summary['cluster_max']:.3f}\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def interface_clusters_6n(iface_mask: np.ndarray, nx: int, ny: int, nz: int) -> Tuple[int, float, float]:
    """
    6-neighborhood connected components on the 3D grid.
    Returns (n_clusters, mean_size, max_size).
    """
    n = iface_mask.shape[0]
    seen = np.zeros(n, dtype=np.uint8)
    sizes: List[int] = []
    for i in range(n):
        if iface_mask[i] == 0.0 or seen[i]:
            continue
        # BFS
        q = [i]
        seen[i] = 1
        sz = 0
        while q:
            v = q.pop()
            sz += 1
            for u in neighbors_3d(v, nx, ny, nz):
                if iface_mask[u] > 0.5 and not seen[u]:
                    seen[u] = 1
                    q.append(u)
        sizes.append(sz)
    if not sizes:
        return 0, 0.0, 0.0
    return len(sizes), float(sum(sizes)) / float(len(sizes)), float(max(sizes))

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=10)
    ap.add_argument("--q", type=int, default=7)
    ap.add_argument("--nx", type=int, default=9)
    ap.add_argument("--ny", type=int, default=9)
    ap.add_argument("--nz", type=int, default=5)
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--threshold", type=float, default=0.55)
    ap.add_argument("--beta", type=float, default=6.0, help="Inverse temperature for stochastic bit updates.")
    ap.add_argument("--coupling", type=float, default=1.0, help="Coupling strength from residual r to macro update.")
    ap.add_argument("--noise", type=float, default=0.02, help="Random bit-flip noise probability per site per step (applied to the active bit).")
    ap.add_argument("--defect-rate", type=float, default=0.005, help="Interface defect injection probability per site per step.")
    ap.add_argument("--r-diffusion", type=float, default=0.25, help="Residual diffusion probability per site per step (toward neighbor mean).")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    m = int(args.m)
    q = int(args.q)
    nx, ny, nz = int(args.nx), int(args.ny), int(args.nz)
    steps = int(args.steps)
    threshold = float(args.threshold)
    beta = float(args.beta)
    coupling = float(args.coupling)
    noise = float(args.noise)
    defect_rate = float(args.defect_rate)
    r_diffusion = float(args.r_diffusion)
    seed = int(args.seed)

    script_path = Path(__file__).resolve()
    params = {
        "m": m,
        "q": q,
        "nx": nx,
        "ny": ny,
        "nz": nz,
        "steps": steps,
        "threshold": threshold,
        "beta": beta,
        "coupling": coupling,
        "noise": noise,
        "defect_rate": defect_rate,
        "r_diffusion": r_diffusion,
        "seed": seed,
    }
    run = prepare_run(
        experiment="emergence_local_dynamics",
        params=params,
        script_path=script_path,
        required_files=["summary.json", "disturbance_radius.png", "correlation.png", "residual_activity.png"],
        force=bool(args.force),
    )

    out_json = run.run_dir / "summary.json"
    out_png_radius = run.run_dir / "disturbance_radius.png"
    out_png_corr = run.run_dir / "correlation.png"
    out_png_res = run.run_dir / "residual_activity.png"
    out_tex = generated_dir() / "emergence_metrics.tex"

    if run.cached:
        print(f"[emergence] cached: {run.run_dir}", flush=True)
        return

    rng = random.Random(seed)
    prog = Progress(every_seconds=15.0)

    # Prepare macro state sampling.
    Xm = list(iter_no_adjacent_words(m))
    Xm.sort()
    if not Xm:
        raise RuntimeError("X_m is empty")

    n = nx * ny * nz
    center = (nz // 2) * (nx * ny) + (ny // 2) * nx + (nx // 2)
    nbrs = [neighbors_3d(i, nx, ny, nz) for i in range(n)]

    # Initialize baseline and perturbed.
    x0 = np.array([Xm[rng.randrange(len(Xm))] for _ in range(n)], dtype=np.int64)
    r0 = np.array([rng.randrange(q) for _ in range(n)], dtype=np.int64)

    x1 = x0.copy()
    r1 = r0.copy()

    # Localized perturbation at center: flip a mid bit if legal, else force 0.
    bit0 = (m // 2)
    x1_center = int(x1[center])
    x1[center] = propose_update_x(x1_center, m=m, bit_i=bit0, nbr_mean=1.0, threshold=0.5)
    # Also perturb residual to create a propagating signal channel.
    r1[center] = (int(r1[center]) + 1) % q

    radii: List[float] = []
    iface_fracs: List[float] = []
    res_mean: List[float] = []
    res_iface_mean: List[float] = []
    res_bulk_mean: List[float] = []
    cluster_max_series: List[float] = []

    for t in range(steps + 1):
        diff = (x0 != x1) | (r0 != r1)
        rad = disturbance_radius(diff, nx=nx, ny=ny, nz=nz, center=center)
        radii.append(rad)

        iface1 = np.array([1.0 if is_in_Bm(int(x), m) else 0.0 for x in x1], dtype=np.float64)
        iface_frac = float(iface1.mean())
        iface_fracs.append(iface_frac)
        _, _, cluster_max = interface_clusters_6n(iface1, nx=nx, ny=ny, nz=nz)
        cluster_max_series.append(cluster_max)

        # Residual activity proxy: per-step absolute delta in r (wrap-aware for Z_q)
        if t == 0:
            delta_r = np.zeros(n, dtype=np.float64)
        else:
            # Filled below during update.
            delta_r = delta_r  # type: ignore[name-defined]

        res_mean.append(float(delta_r.mean()))
        if_mask = (iface1 > 0.5)
        if if_mask.any():
            res_iface_mean.append(float(delta_r[if_mask].mean()))
        else:
            res_iface_mean.append(0.0)
        if (~if_mask).any():
            res_bulk_mean.append(float(delta_r[~if_mask].mean()))
        else:
            res_bulk_mean.append(0.0)

        prog.maybe(f"t={t}/{steps} radius={rad}")
        if t == steps:
            break

        # Update both simulations synchronously.
        x0_next = x0.copy()
        r0_next = r0.copy()
        x1_next = x1.copy()
        r1_next = r1.copy()

        delta_r = np.zeros(n, dtype=np.float64)

        bit_i = (t % m)
        # Shared randomness for baseline and perturbed so that differences reflect initial perturbation.
        # Use per-site uniforms to decide noise/defect injection and Bernoulli bit update.
        u_noise = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_defect = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_bit = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_r = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        for i in range(n):
            nm0 = avg_neighbor_bit(x0, nbrs[i], bit_i=bit_i)
            nm1 = avg_neighbor_bit(x1, nbrs[i], bit_i=bit_i)

            # Stochastic bit update with residual coupling.
            # bias = beta*(nbr_mean-threshold) + coupling*(r/q - 0.5)
            bias0 = beta * (nm0 - threshold) + coupling * ((float(r0[i]) / float(q)) - 0.5)
            bias1 = beta * (nm1 - threshold) + coupling * ((float(r1[i]) / float(q)) - 0.5)
            p1_0 = logistic(bias0)
            p1_1 = logistic(bias1)

            # Use shared u_bit[i] but different p1 values => divergence can propagate.
            want1_0 = 1.0 if (u_bit[i] < p1_0) else 0.0
            want1_1 = 1.0 if (u_bit[i] < p1_1) else 0.0

            x0_cur = int(x0[i])
            x1_cur = int(x1[i])
            if want1_0 >= 0.5:
                x0_new = propose_update_x(x0_cur, m=m, bit_i=bit_i, nbr_mean=1.0, threshold=0.5)
            else:
                x0_new = propose_update_x(x0_cur, m=m, bit_i=bit_i, nbr_mean=0.0, threshold=0.5)
            if want1_1 >= 0.5:
                x1_new = propose_update_x(x1_cur, m=m, bit_i=bit_i, nbr_mean=1.0, threshold=0.5)
            else:
                x1_new = propose_update_x(x1_cur, m=m, bit_i=bit_i, nbr_mean=0.0, threshold=0.5)

            # Noise: flip the active bit with small probability, then re-project locally by clearing neighbors if needed.
            if u_noise[i] < noise:
                x0_new ^= (1 << bit_i)
                x1_new ^= (1 << bit_i)
                # Repair adjacency locally around bit_i
                if bit_i - 1 >= 0 and (((x0_new >> bit_i) & 1) == 1) and (((x0_new >> (bit_i - 1)) & 1) == 1):
                    x0_new &= ~(1 << (bit_i - 1))
                if bit_i + 1 < m and (((x0_new >> bit_i) & 1) == 1) and (((x0_new >> (bit_i + 1)) & 1) == 1):
                    x0_new &= ~(1 << (bit_i + 1))
                if bit_i - 1 >= 0 and (((x1_new >> bit_i) & 1) == 1) and (((x1_new >> (bit_i - 1)) & 1) == 1):
                    x1_new &= ~(1 << (bit_i - 1))
                if bit_i + 1 < m and (((x1_new >> bit_i) & 1) == 1) and (((x1_new >> (bit_i + 1)) & 1) == 1):
                    x1_new &= ~(1 << (bit_i + 1))

            # Defect injection: occasionally force interface defect state.
            if u_defect[i] < defect_rate:
                x0_new = inject_interface_defect(x0_new, m=m)
                x1_new = inject_interface_defect(x1_new, m=m)

            # Residual update: if interface (B_m), add +/-1 depending on local bit parity.
            inc0 = 1 if is_in_Bm(x0_new, m) else 0
            inc1 = 1 if is_in_Bm(x1_new, m) else 0
            if bit_i % 2 == 1:
                inc0 = (-inc0) % q
                inc1 = (-inc1) % q

            r0_new = (int(r0[i]) + inc0) % q
            r1_new = (int(r1[i]) + inc1) % q

            # Residual diffusion: drift toward neighbor mean with small probability.
            if u_r[i] < r_diffusion:
                mnr0 = avg_neighbor_r(r0, nbrs[i])
                mnr1 = avg_neighbor_r(r1, nbrs[i])
                d0 = mnr0 - float(int(r0[i]))
                d1 = mnr1 - float(int(r1[i]))
                step0 = 1 if d0 > 0.25 else (-1 if d0 < -0.25 else 0)
                step1 = 1 if d1 > 0.25 else (-1 if d1 < -0.25 else 0)
                r0_new = (r0_new + step0) % q
                r1_new = (r1_new + step1) % q

            x0_next[i] = x0_new
            x1_next[i] = x1_new
            r0_next[i] = r0_new
            r1_next[i] = r1_new

            # Activity: minimal distance on Z_q (wrap-aware)
            dr = (r1_new - int(r1[i])) % q
            dr = min(dr, q - dr)
            delta_r[i] = float(dr)

        x0, r0 = x0_next, r0_next
        x1, r1 = x1_next, r1_next

    # Disturbance radius plot.
    plt.figure(figsize=(7.0, 4.0))
    plt.plot(list(range(steps + 1)), radii, color="#2ca02c", linewidth=2.0)
    plt.title("Disturbance radius vs time")
    plt.xlabel("t")
    plt.ylabel("max Manhattan radius")
    plt.tight_layout()
    plt.savefig(out_png_radius, dpi=160)
    plt.close()

    # Correlation plot for interface indicator at final time.
    iface_final = np.array([1.0 if is_in_Bm(int(x), m) else 0.0 for x in x1], dtype=np.float64)
    max_d = int(nx + ny + nz)
    ds, Cs = correlation_by_distance(iface_final, nx=nx, ny=ny, ny2=ny, nz=nz, max_d=max_d)
    plt.figure(figsize=(7.0, 4.0))
    plt.plot(ds, Cs, color="#1f77b4", linewidth=2.0)
    plt.title("Interface indicator correlation vs distance (final time)")
    plt.xlabel("Manhattan distance d")
    plt.ylabel("C(d)")
    plt.tight_layout()
    plt.savefig(out_png_corr, dpi=160)
    plt.close()

    # Residual activity plot.
    plt.figure(figsize=(7.0, 4.0))
    plt.plot(res_mean, label="all", color="#ff7f0e", linewidth=2.0)
    plt.plot(res_iface_mean, label="interface", color="#d62728", linewidth=2.0)
    plt.plot(res_bulk_mean, label="bulk", color="#9467bd", linewidth=2.0)
    plt.title("Residual activity proxy vs time")
    plt.xlabel("t")
    plt.ylabel("mean |Δr|")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png_res, dpi=160)
    plt.close()

    summary = {
        "radius_final": float(radii[-1]),
        "radius_max": float(max(radii) if radii else 0.0),
        "interface_frac_final": float(iface_fracs[-1] if iface_fracs else 0.0),
        "interface_frac_max": float(max(iface_fracs) if iface_fracs else 0.0),
        "cluster_max": float(max(cluster_max_series) if cluster_max_series else 0.0),
    }

    payload = {"params": params, "summary": summary}
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_emergence_tex(m=m, q=q, nx=nx, ny=ny, nz=nz, steps=steps, summary=summary, out_path=out_tex)

    manifest = build_base_manifest("emergence_local_dynamics", run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(
        manifest,
        run.run_dir,
        ["summary.json", "disturbance_radius.png", "correlation.png", "residual_activity.png"],
    )
    write_manifest(run.run_dir, manifest)

    # Stable exports for LaTeX inclusion.
    ed = export_dir()
    ed.mkdir(parents=True, exist_ok=True)
    copy_atomic(out_png_radius, ed / "emergence_disturbance_radius.png")
    copy_atomic(out_png_corr, ed / "emergence_correlation.png")
    copy_atomic(out_png_res, ed / "emergence_residual_activity.png")

    prog.done(f"wrote {out_json} and plots + {out_tex}")


if __name__ == "__main__":
    main()

