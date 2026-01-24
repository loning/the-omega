#!/usr/bin/env python3
"""
Two-defect interaction (scattering-like) experiment under driven transport dynamics.

We initialize two localized defects (two B_m seeds) separated along x, then run the
same transport dynamics as exp_emergence_transport.py (with drive_gamma option).

We measure:
  - distance between the two largest interface components over time (wrap in x)
  - min distance per run
  - event rates: "close approach" (min_dist <= d_coll), "merged at closest"
    (only one large component), and "split after merge" (two large components
    reappear after a window).

Outputs:
  - artifacts/emergence_transport_scattering/<run_id>/summary.json
  - artifacts/emergence_transport_scattering/<run_id>/dist_example.png
  - artifacts/emergence_transport_scattering/<run_id>/min_dist_hist.png
  - sections/generated/emergence_transport_scattering_summary.tex
  - stable exports under artifacts/export/
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
from common_paths import export_dir, generated_dir
from common_progress import Progress
from common_zeckendorf import iter_no_adjacent_words, no_adjacent_ones_mask_ok, word_bit


def is_in_Bm(x: int, m: int) -> bool:
    return no_adjacent_ones_mask_ok(x) and (m > 1) and (word_bit(x, 0) == 1 and word_bit(x, m - 1) == 1)


def idx_to_xyz(idx: int, nx: int, ny: int) -> Tuple[int, int, int]:
    z = idx // (nx * ny)
    rem = idx % (nx * ny)
    y = rem // nx
    x = rem % nx
    return x, y, z


def xyz_to_idx(x: int, y: int, z: int, nx: int, ny: int) -> int:
    return z * (nx * ny) + y * nx + x


def neighbors_3d(idx: int, nx: int, ny: int, nz: int) -> List[int]:
    x, y, z = idx_to_xyz(idx, nx=nx, ny=ny)
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


def wrap_signed_dx(x_new: float, x_old: float, nx: int) -> float:
    dx = float(x_new - x_old)
    dx = ((dx + 0.5 * nx) % nx) - 0.5 * nx
    return float(dx)


def wrap_l2(c_new: Tuple[float, float, float], c_old: Tuple[float, float, float], nx: int) -> float:
    dx = wrap_signed_dx(float(c_new[0]), float(c_old[0]), nx=nx)
    dy = float(c_new[1]) - float(c_old[1])
    dz = float(c_new[2]) - float(c_old[2])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def centered_mod_diff(a: int, b: int, q: int) -> int:
    if q <= 0:
        return int(a - b)
    half = q / 2.0
    d = ((int(a) - int(b) + half) % q) - half
    return int(round(d))


@dataclass
class Comp:
    size: int
    centroid: Tuple[float, float, float]


def components_sizes_centroids(iface_mask: np.ndarray, nx: int, ny: int, nz: int) -> List[Comp]:
    n = iface_mask.shape[0]
    seen = np.zeros(n, dtype=np.uint8)
    out: List[Comp] = []
    for i in range(n):
        if iface_mask[i] < 0.5 or seen[i]:
            continue
        q = [i]
        seen[i] = 1
        sx = sy = sz = 0.0
        cnt = 0
        while q:
            v = q.pop()
            cnt += 1
            x, y, z = idx_to_xyz(v, nx=nx, ny=ny)
            sx += float(x)
            sy += float(y)
            sz += float(z)
            for u in neighbors_3d(v, nx, ny, nz):
                if iface_mask[u] > 0.5 and not seen[u]:
                    seen[u] = 1
                    q.append(u)
        if cnt > 0:
            inv = 1.0 / float(cnt)
            out.append(Comp(size=int(cnt), centroid=(sx * inv, sy * inv, sz * inv)))
    out.sort(key=lambda c: c.size, reverse=True)
    return out


def write_scattering_tex(summary: Dict[str, float], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("% Auto-generated by scripts/exp_emergence_transport_scattering.py")
    lines.append("\\begin{tabular}{lr}")
    lines.append("\\toprule")
    lines.append("Quantity & Value\\\\")
    lines.append("\\midrule")
    lines.append(f"runs & {summary['n_runs']:.0f}\\\\")
    lines.append(f"close-approach rate & {summary['close_rate']:.4f}\\\\")
    lines.append(f"merged-at-closest rate & {summary['merge_rate']:.4f}\\\\")
    lines.append(f"split-after-merge rate & {summary['split_after_merge_rate']:.4f}\\\\")
    lines.append(f"mean min distance & {summary['min_dist_mean']:.3f}\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def simulate_one(
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
    advect_p: float,
    advect_dir: int,
    drive_gamma: float,
    seed: int,
    min_size: int,
) -> Tuple[List[float], List[int]]:
    rng = random.Random(seed)
    Xm = list(iter_no_adjacent_words(m))
    Xm.sort()
    n = nx * ny * nz
    nbrs = [neighbors_3d(i, nx, ny, nz) for i in range(n)]

    x = np.array([Xm[rng.randrange(len(Xm))] for _ in range(n)], dtype=np.int64)
    r = np.array([rng.randrange(qmod) for _ in range(n)], dtype=np.int64)

    # two defect seeds separated along x
    y0 = ny // 2
    z0 = nz // 2
    x1 = nx // 4
    x2 = (3 * nx) // 4
    c1 = xyz_to_idx(x1, y0, z0, nx=nx, ny=ny)
    c2 = xyz_to_idx(x2, y0, z0, nx=nx, ny=ny)
    bit0 = (m // 2)
    x[c1] = inject_interface_defect(propose_set_bit_with_local_repair(int(x[c1]), m=m, bit_i=bit0, want1=1), m=m)
    x[c2] = inject_interface_defect(propose_set_bit_with_local_repair(int(x[c2]), m=m, bit_i=bit0, want1=1), m=m)
    r[c1] = (int(r[c1]) + 2) % qmod
    r[c2] = (int(r[c2]) - 2) % qmod

    dists: List[float] = []
    n_large: List[int] = []

    for t in range(steps + 1):
        iface = np.array([1.0 if is_in_Bm(int(xx), m) else 0.0 for xx in x], dtype=np.float64)
        comps = components_sizes_centroids(iface, nx=nx, ny=ny, nz=nz)
        comps_large = [c for c in comps if c.size >= min_size]
        n_large.append(len(comps_large))
        if len(comps_large) >= 2:
            d = wrap_l2(comps_large[0].centroid, comps_large[1].centroid, nx=nx)
            dists.append(float(d))
        else:
            dists.append(float("nan"))
        if t == steps:
            break

        bit_i = (t % m)
        u_noise = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_defect = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_bit = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_r = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_adv = np.array([rng.random() for _ in range(n)], dtype=np.float64)

        x_next = x.copy()
        r_next = r.copy()
        for i in range(n):
            nm = avg_neighbor_bit(x, nbrs[i], bit_i=bit_i)
            bias = beta * (nm - threshold) + coupling * ((float(r[i]) / float(qmod)) - 0.5)
            if drive_gamma != 0.0:
                x_i, y_i, z_i = idx_to_xyz(i, nx=nx, ny=ny)
                il = xyz_to_idx((x_i - 1) % nx, y_i, z_i, nx=nx, ny=ny)
                ir = xyz_to_idx((x_i + 1) % nx, y_i, z_i, nx=nx, ny=ny)
                d = centered_mod_diff(int(r[il]), int(r[ir]), q=qmod)
                grad = float(d) / float(max(1, qmod))
                bias += drive_gamma * grad
            p1 = logistic(bias)
            want1 = 1 if (u_bit[i] < p1) else 0
            x_new = propose_set_bit_with_local_repair(int(x[i]), m=m, bit_i=bit_i, want1=want1)

            if u_noise[i] < noise:
                x_new ^= (1 << bit_i)
                if bit_i - 1 >= 0 and (((x_new >> bit_i) & 1) == 1) and (((x_new >> (bit_i - 1)) & 1) == 1):
                    x_new &= ~(1 << (bit_i - 1))
                if bit_i + 1 < m and (((x_new >> bit_i) & 1) == 1) and (((x_new >> (bit_i + 1)) & 1) == 1):
                    x_new &= ~(1 << (bit_i + 1))

            if u_defect[i] < defect_rate:
                x_new = inject_interface_defect(x_new, m=m)

            inc = 1 if is_in_Bm(x_new, m) else 0
            if bit_i % 2 == 1:
                inc = (-inc) % qmod
            r_new = (int(r[i]) + inc) % qmod

            if u_r[i] < r_diffusion:
                mnr = avg_neighbor_r(r, nbrs[i])
                dlt = mnr - float(int(r[i]))
                step = 1 if dlt > 0.25 else (-1 if dlt < -0.25 else 0)
                r_new = (r_new + step) % qmod

            if u_adv[i] < advect_p:
                x_i, y_i, z_i = idx_to_xyz(i, nx=nx, ny=ny)
                src_x = (x_i - int(advect_dir)) % nx
                src = xyz_to_idx(src_x, y_i, z_i, nx=nx, ny=ny)
                r_new = (int(r_new) + int(r[src])) % qmod

            x_next[i] = x_new
            r_next[i] = r_new
        x, r = x_next, r_next

    return dists, n_large


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=10)
    ap.add_argument("--q", type=int, default=7)
    ap.add_argument("--nx", type=int, default=15)
    ap.add_argument("--ny", type=int, default=9)
    ap.add_argument("--nz", type=int, default=5)
    ap.add_argument("--steps", type=int, default=260)
    ap.add_argument("--threshold", type=float, default=0.50)
    ap.add_argument("--beta", type=float, default=6.0)
    ap.add_argument("--coupling", type=float, default=2.0)
    ap.add_argument("--noise", type=float, default=0.02)
    ap.add_argument("--defect-rate", type=float, default=0.006)
    ap.add_argument("--r-diffusion", type=float, default=0.25)
    ap.add_argument("--advect-p", type=float, default=0.0)
    ap.add_argument("--advect-dir", type=int, default=1)
    ap.add_argument("--drive-gamma", type=float, default=6.0)
    ap.add_argument("--n-runs", type=int, default=8)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--min-size", type=int, default=3)
    ap.add_argument("--d-coll", type=float, default=2.2)
    ap.add_argument("--post-window", type=int, default=40)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    m = int(args.m)
    qmod = int(args.q)
    nx, ny, nz = int(args.nx), int(args.ny), int(args.nz)
    steps = int(args.steps)
    threshold = float(args.threshold)
    beta = float(args.beta)
    coupling = float(args.coupling)
    noise = float(args.noise)
    defect_rate = float(args.defect_rate)
    r_diffusion = float(args.r_diffusion)
    advect_p = float(args.advect_p)
    advect_dir = int(args.advect_dir)
    drive_gamma = float(args.drive_gamma)
    n_runs = int(args.n_runs)
    seed0 = int(args.seed0)
    min_size = int(args.min_size)
    d_coll = float(args.d_coll)
    post_window = int(args.post_window)

    script_path = Path(__file__).resolve()
    params = {
        "m": m,
        "q": qmod,
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
        "advect_p": advect_p,
        "advect_dir": advect_dir,
        "drive_gamma": drive_gamma,
        "n_runs": n_runs,
        "seed0": seed0,
        "min_size": min_size,
        "d_coll": d_coll,
        "post_window": post_window,
    }

    run = prepare_run(
        experiment="emergence_transport_scattering",
        params=params,
        script_path=script_path,
        required_files=["summary.json", "dist_example.png", "min_dist_hist.png"],
        force=bool(args.force),
    )

    out_json = run.run_dir / "summary.json"
    out_example = run.run_dir / "dist_example.png"
    out_hist = run.run_dir / "min_dist_hist.png"
    out_tex = generated_dir() / "emergence_transport_scattering_summary.tex"

    if run.cached:
        print(f"[emergence_transport_scattering] cached: {run.run_dir}", flush=True)
        return

    prog = Progress(every_seconds=15.0)

    min_dists: List[float] = []
    close = 0
    merged = 0
    split_after = 0
    example_series: List[float] = []

    for k in range(n_runs):
        dists, n_large = simulate_one(
            m=m,
            qmod=qmod,
            nx=nx,
            ny=ny,
            nz=nz,
            steps=steps,
            threshold=threshold,
            beta=beta,
            coupling=coupling,
            noise=noise,
            defect_rate=defect_rate,
            r_diffusion=r_diffusion,
            advect_p=advect_p,
            advect_dir=advect_dir,
            drive_gamma=drive_gamma,
            seed=seed0 + k,
            min_size=min_size,
        )

        if k == 0:
            example_series = dists[:]

        arr = np.array(dists, dtype=np.float64)
        finite = arr[np.isfinite(arr)]
        if finite.size == 0:
            md = float("nan")
            tmin = 0
        else:
            md = float(np.min(finite))
            tmin = int(np.nanargmin(arr))
        min_dists.append(md)

        if math.isfinite(md) and md <= d_coll:
            close += 1
            # merged at closest: not enough large components
            if n_large[tmin] < 2:
                merged += 1
                t2 = min(len(n_large) - 1, tmin + post_window)
                if n_large[t2] >= 2:
                    split_after += 1

        prog.maybe(f"run {k+1}/{n_runs} min_dist={md:.3f}")

    min_dists_f = [d for d in min_dists if math.isfinite(d)]
    summary = {
        "n_runs": float(n_runs),
        "close_rate": float(close) / float(max(1, n_runs)),
        "merge_rate": float(merged) / float(max(1, n_runs)),
        "split_after_merge_rate": float(split_after) / float(max(1, max(1, merged))),
        "min_dist_mean": float(np.mean(min_dists_f)) if min_dists_f else float("nan"),
    }

    plt.figure(figsize=(7.0, 4.0))
    if example_series:
        ts = np.arange(len(example_series))
        plt.plot(ts, example_series, color="#1f77b4", linewidth=2.0)
    plt.axhline(d_coll, color="#d62728", linestyle="--", linewidth=1.5)
    plt.title("Two-defect distance vs time (example run)")
    plt.xlabel("t")
    plt.ylabel("distance (top-2 large components)")
    plt.tight_layout()
    plt.savefig(out_example, dpi=160)
    plt.close()

    plt.figure(figsize=(7.0, 4.0))
    if min_dists_f:
        plt.hist(min_dists_f, bins=20, color="#ff7f0e", alpha=0.9)
    plt.axvline(d_coll, color="#d62728", linestyle="--", linewidth=1.5)
    plt.title("Min distance histogram across runs")
    plt.xlabel("min distance")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(out_hist, dpi=160)
    plt.close()

    payload = {"params": params, "summary": summary, "min_dists": min_dists}
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_scattering_tex(summary=summary, out_path=out_tex)

    manifest = build_base_manifest("emergence_transport_scattering", run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, ["summary.json", "dist_example.png", "min_dist_hist.png"])
    write_manifest(run.run_dir, manifest)

    ed = export_dir()
    ed.mkdir(parents=True, exist_ok=True)
    copy_atomic(out_example, ed / "emergence_transport_scattering_distance.png")
    copy_atomic(out_hist, ed / "emergence_transport_scattering_min_dist_hist.png")

    prog.done(f"wrote {out_json}, plots, and {out_tex}")


if __name__ == "__main__":
    main()

