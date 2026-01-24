#!/usr/bin/env python3
"""
Parameter scan for emergence local dynamics.

We scan (threshold, defect_rate) on a small 3D grid and measure:
  - max disturbance radius (baseline vs perturbed, shared randomness)
  - max interface fraction (B_m density)
  - max interface cluster size

Outputs:
  - artifacts/emergence_scan/<run_id>/summary.json
  - artifacts/emergence_scan/<run_id>/phase_radius.png
  - artifacts/emergence_scan/<run_id>/phase_interface.png
  - artifacts/emergence_scan/<run_id>/phase_cluster.png
  - sections/generated/emergence_phase_scan.tex
  - stable exports under artifacts/export/
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import export_dir, generated_dir
from common_progress import Progress
from common_zeckendorf import iter_no_adjacent_words, no_adjacent_ones_mask_ok, word_bit


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


def inject_interface_defect(x: int, m: int) -> int:
    if m <= 1:
        return x
    x |= (1 << 0)
    x |= (1 << (m - 1))
    if m >= 2:
        x &= ~(1 << 1)
        x &= ~(1 << (m - 2))
    return x


def propose_set_bit_with_local_repair(x: int, m: int, bit_i: int, want1: int) -> int:
    if want1 == 0:
        return x & ~(1 << bit_i)
    # want1==1, only if adjacent bits are 0
    if bit_i - 1 >= 0 and (((x >> (bit_i - 1)) & 1) == 1):
        return x & ~(1 << bit_i)
    if bit_i + 1 < m and (((x >> (bit_i + 1)) & 1) == 1):
        return x & ~(1 << bit_i)
    return x | (1 << bit_i)


def logistic(u: float) -> float:
    if u >= 60.0:
        return 1.0
    if u <= -60.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-u))


def disturbance_radius(diff_mask: np.ndarray, nx: int, ny: int, nz: int, center: int) -> float:
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


def interface_cluster_max(iface_mask: np.ndarray, nx: int, ny: int, nz: int) -> float:
    n = iface_mask.shape[0]
    seen = np.zeros(n, dtype=np.uint8)
    best = 0
    for i in range(n):
        if iface_mask[i] < 0.5 or seen[i]:
            continue
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
        if sz > best:
            best = sz
    return float(best)


def simulate_summary(
    *,
    m: int,
    qmod: int,
    nx: int,
    ny: int,
    nz: int,
    steps: int,
    threshold: float,
    beta: float,
    coupling: float,
    noise: float,
    defect_rate: float,
    r_diffusion: float,
    seed: int,
) -> Dict[str, float]:
    rng = random.Random(seed)
    Xm = list(iter_no_adjacent_words(m))
    Xm.sort()
    n = nx * ny * nz
    center = (nz // 2) * (nx * ny) + (ny // 2) * nx + (nx // 2)
    nbrs = [neighbors_3d(i, nx, ny, nz) for i in range(n)]

    x0 = np.array([Xm[rng.randrange(len(Xm))] for _ in range(n)], dtype=np.int64)
    r0 = np.array([rng.randrange(qmod) for _ in range(n)], dtype=np.int64)
    x1 = x0.copy()
    r1 = r0.copy()

    # localized perturbation
    bit0 = (m // 2)
    x1[center] = propose_set_bit_with_local_repair(int(x1[center]), m=m, bit_i=bit0, want1=1)
    r1[center] = (int(r1[center]) + 1) % qmod

    rad_max = 0.0
    iface_max = 0.0
    cluster_max = 0.0

    for t in range(steps + 1):
        diff = (x0 != x1) | (r0 != r1)
        rad = disturbance_radius(diff, nx=nx, ny=ny, nz=nz, center=center)
        rad_max = max(rad_max, rad)

        iface1 = np.array([1.0 if is_in_Bm(int(x), m) else 0.0 for x in x1], dtype=np.float64)
        iface_max = max(iface_max, float(iface1.mean()))
        cluster_max = max(cluster_max, interface_cluster_max(iface1, nx=nx, ny=ny, nz=nz))
        if t == steps:
            break

        bit_i = (t % m)
        u_noise = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_defect = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_bit = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_r = np.array([rng.random() for _ in range(n)], dtype=np.float64)

        x0_next = x0.copy()
        r0_next = r0.copy()
        x1_next = x1.copy()
        r1_next = r1.copy()

        for i in range(n):
            nm0 = avg_neighbor_bit(x0, nbrs[i], bit_i=bit_i)
            nm1 = avg_neighbor_bit(x1, nbrs[i], bit_i=bit_i)

            bias0 = beta * (nm0 - threshold) + coupling * ((float(r0[i]) / float(qmod)) - 0.5)
            bias1 = beta * (nm1 - threshold) + coupling * ((float(r1[i]) / float(qmod)) - 0.5)
            p1_0 = logistic(bias0)
            p1_1 = logistic(bias1)
            want1_0 = 1 if (u_bit[i] < p1_0) else 0
            want1_1 = 1 if (u_bit[i] < p1_1) else 0

            x0_new = propose_set_bit_with_local_repair(int(x0[i]), m=m, bit_i=bit_i, want1=want1_0)
            x1_new = propose_set_bit_with_local_repair(int(x1[i]), m=m, bit_i=bit_i, want1=want1_1)

            if u_noise[i] < noise:
                x0_new ^= (1 << bit_i)
                x1_new ^= (1 << bit_i)
                # local repair by clearing adjacent conflicts
                if bit_i - 1 >= 0 and (((x0_new >> bit_i) & 1) == 1) and (((x0_new >> (bit_i - 1)) & 1) == 1):
                    x0_new &= ~(1 << (bit_i - 1))
                if bit_i + 1 < m and (((x0_new >> bit_i) & 1) == 1) and (((x0_new >> (bit_i + 1)) & 1) == 1):
                    x0_new &= ~(1 << (bit_i + 1))
                if bit_i - 1 >= 0 and (((x1_new >> bit_i) & 1) == 1) and (((x1_new >> (bit_i - 1)) & 1) == 1):
                    x1_new &= ~(1 << (bit_i - 1))
                if bit_i + 1 < m and (((x1_new >> bit_i) & 1) == 1) and (((x1_new >> (bit_i + 1)) & 1) == 1):
                    x1_new &= ~(1 << (bit_i + 1))

            if u_defect[i] < defect_rate:
                x0_new = inject_interface_defect(x0_new, m=m)
                x1_new = inject_interface_defect(x1_new, m=m)

            inc0 = 1 if is_in_Bm(x0_new, m) else 0
            inc1 = 1 if is_in_Bm(x1_new, m) else 0
            if bit_i % 2 == 1:
                inc0 = (-inc0) % qmod
                inc1 = (-inc1) % qmod

            r0_new = (int(r0[i]) + inc0) % qmod
            r1_new = (int(r1[i]) + inc1) % qmod

            if u_r[i] < r_diffusion:
                mnr0 = avg_neighbor_r(r0, nbrs[i])
                mnr1 = avg_neighbor_r(r1, nbrs[i])
                d0 = mnr0 - float(int(r0[i]))
                d1 = mnr1 - float(int(r1[i]))
                step0 = 1 if d0 > 0.25 else (-1 if d0 < -0.25 else 0)
                step1 = 1 if d1 > 0.25 else (-1 if d1 < -0.25 else 0)
                r0_new = (r0_new + step0) % qmod
                r1_new = (r1_new + step1) % qmod

            x0_next[i] = x0_new
            x1_next[i] = x1_new
            r0_next[i] = r0_new
            r1_next[i] = r1_new

        x0, r0 = x0_next, r0_next
        x1, r1 = x1_next, r1_next

    return {
        "radius_max": float(rad_max),
        "interface_frac_max": float(iface_max),
        "cluster_max": float(cluster_max),
    }


def write_phase_tex(best: Dict[str, float], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("% Auto-generated by scripts/exp_emergence_scan.py")
    lines.append("\\begin{tabular}{lr}")
    lines.append("\\toprule")
    lines.append("Best metric & Value\\\\")
    lines.append("\\midrule")
    lines.append(f"threshold & {best['threshold']:.3f}\\\\")
    lines.append(f"defect\\_rate & {best['defect_rate']:.5f}\\\\")
    lines.append(f"radius\\_max & {best['radius_max']:.3f}\\\\")
    lines.append(f"interface\\_frac\\_max & {best['interface_frac_max']:.4f}\\\\")
    lines.append(f"cluster\\_max & {best['cluster_max']:.3f}\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=10)
    ap.add_argument("--q", type=int, default=7)
    ap.add_argument("--nx", type=int, default=7)
    ap.add_argument("--ny", type=int, default=7)
    ap.add_argument("--nz", type=int, default=3)
    ap.add_argument("--steps", type=int, default=50)
    ap.add_argument("--beta", type=float, default=6.0)
    ap.add_argument("--coupling", type=float, default=1.0)
    ap.add_argument("--noise", type=float, default=0.02)
    ap.add_argument("--r-diffusion", type=float, default=0.25)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--n-seeds", type=int, default=3)
    ap.add_argument("--thresholds", type=str, default="0.40,0.45,0.50,0.55,0.60,0.65")
    ap.add_argument("--defect-rates", type=str, default="0.000,0.002,0.004,0.006,0.008,0.010")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    m = int(args.m)
    qmod = int(args.q)
    nx, ny, nz = int(args.nx), int(args.ny), int(args.nz)
    steps = int(args.steps)
    beta = float(args.beta)
    coupling = float(args.coupling)
    noise = float(args.noise)
    r_diffusion = float(args.r_diffusion)
    seed0 = int(args.seed0)
    n_seeds = int(args.n_seeds)
    thresholds = [float(x.strip()) for x in args.thresholds.split(",") if x.strip()]
    defect_rates = [float(x.strip()) for x in args.defect_rates.split(",") if x.strip()]

    script_path = Path(__file__).resolve()
    params = {
        "m": m,
        "q": qmod,
        "nx": nx,
        "ny": ny,
        "nz": nz,
        "steps": steps,
        "beta": beta,
        "coupling": coupling,
        "noise": noise,
        "r_diffusion": r_diffusion,
        "seed0": seed0,
        "n_seeds": n_seeds,
        "thresholds": thresholds,
        "defect_rates": defect_rates,
    }

    run = prepare_run(
        experiment="emergence_scan",
        params=params,
        script_path=script_path,
        required_files=["summary.json", "phase_radius.png", "phase_interface.png", "phase_cluster.png"],
        force=bool(args.force),
    )

    out_json = run.run_dir / "summary.json"
    out_radius = run.run_dir / "phase_radius.png"
    out_iface = run.run_dir / "phase_interface.png"
    out_cluster = run.run_dir / "phase_cluster.png"
    out_tex = generated_dir() / "emergence_phase_scan.tex"

    if run.cached:
        print(f"[emergence_scan] cached: {run.run_dir}", flush=True)
        return

    prog = Progress(every_seconds=15.0)

    R = np.zeros((len(defect_rates), len(thresholds)), dtype=np.float64)
    I = np.zeros_like(R)
    C = np.zeros_like(R)

    best = {"score": -1.0, "threshold": 0.0, "defect_rate": 0.0, "radius_max": 0.0, "interface_frac_max": 0.0, "cluster_max": 0.0}

    total = len(defect_rates) * len(thresholds) * n_seeds
    done = 0
    for ir, dr in enumerate(defect_rates):
        for it, th in enumerate(thresholds):
            rs: List[float] = []
            is_: List[float] = []
            cs: List[float] = []
            for s in range(n_seeds):
                summ = simulate_summary(
                    m=m,
                    qmod=qmod,
                    nx=nx,
                    ny=ny,
                    nz=nz,
                    steps=steps,
                    threshold=th,
                    beta=beta,
                    coupling=coupling,
                    noise=noise,
                    defect_rate=dr,
                    r_diffusion=r_diffusion,
                    seed=seed0 + s,
                )
                rs.append(float(summ["radius_max"]))
                is_.append(float(summ["interface_frac_max"]))
                cs.append(float(summ["cluster_max"]))
                done += 1
                prog.maybe(f"scan {done}/{total}")

            R[ir, it] = float(sum(rs)) / float(len(rs))
            I[ir, it] = float(sum(is_)) / float(len(is_))
            C[ir, it] = float(sum(cs)) / float(len(cs))

            # Score: favor propagation and nontrivial defects
            score = R[ir, it] + 10.0 * I[ir, it] + 0.1 * C[ir, it]
            if score > best["score"]:
                best = {
                    "score": float(score),
                    "threshold": float(th),
                    "defect_rate": float(dr),
                    "radius_max": float(R[ir, it]),
                    "interface_frac_max": float(I[ir, it]),
                    "cluster_max": float(C[ir, it]),
                }

    def heatmap(data: np.ndarray, title: str, out_path: Path, cmap: str) -> None:
        plt.figure(figsize=(8.0, 4.0))
        plt.imshow(data, aspect="auto", origin="lower", cmap=cmap)
        plt.xticks(list(range(len(thresholds))), [f"{t:.2f}" for t in thresholds], rotation=45, ha="right")
        plt.yticks(list(range(len(defect_rates))), [f"{d:.3f}" for d in defect_rates])
        plt.xlabel("threshold")
        plt.ylabel("defect_rate")
        plt.title(title)
        plt.colorbar()
        plt.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_path, dpi=160)
        plt.close()

    heatmap(R, "mean radius_max", out_radius, cmap="viridis")
    heatmap(I, "mean interface_frac_max", out_iface, cmap="magma")
    heatmap(C, "mean cluster_max", out_cluster, cmap="plasma")

    payload = {
        "params": params,
        "radius_max": R.tolist(),
        "interface_frac_max": I.tolist(),
        "cluster_max": C.tolist(),
        "best": best,
    }
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_phase_tex(best=best, out_path=out_tex)

    manifest = build_base_manifest("emergence_scan", run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, ["summary.json", "phase_radius.png", "phase_interface.png", "phase_cluster.png"])
    write_manifest(run.run_dir, manifest)

    # Stable exports for LaTeX inclusion.
    ed = export_dir()
    ed.mkdir(parents=True, exist_ok=True)
    copy_atomic(out_radius, ed / "emergence_phase_radius.png")
    copy_atomic(out_iface, ed / "emergence_phase_interface.png")
    copy_atomic(out_cluster, ed / "emergence_phase_cluster.png")

    prog.done(f"wrote {out_json}, phase plots, and {out_tex}")


if __name__ == "__main__":
    main()

