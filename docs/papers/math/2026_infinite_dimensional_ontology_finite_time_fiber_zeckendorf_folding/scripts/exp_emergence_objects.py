#!/usr/bin/env python3
"""
Object/trajectory emergence experiment.

We treat interface sites (B_m) as "excited support" and extract connected components
under 6-neighborhood as candidate objects. We then build tracks by greedy matching
between consecutive frames (nearest centroid), and measure:
  - object count vs time
  - lifetime distribution
  - speed distribution (centroid displacement per step)

Outputs:
  - artifacts/emergence_objects/<run_id>/summary.json
  - artifacts/emergence_objects/<run_id>/object_count.png
  - artifacts/emergence_objects/<run_id>/lifetime_hist.png
  - artifacts/emergence_objects/<run_id>/speed_hist.png
  - sections/generated/emergence_objects_summary.tex
  - stable exports under artifacts/export/
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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


@dataclass
class Component:
    ids: List[int]
    centroid: Tuple[float, float, float]


def idx_to_xyz(idx: int, nx: int, ny: int) -> Tuple[int, int, int]:
    z = idx // (nx * ny)
    rem = idx % (nx * ny)
    y = rem // nx
    x = rem % nx
    return x, y, z


def components_from_iface(iface_mask: np.ndarray, nx: int, ny: int, nz: int) -> List[Component]:
    n = iface_mask.shape[0]
    seen = np.zeros(n, dtype=np.uint8)
    comps: List[Component] = []
    for i in range(n):
        if iface_mask[i] < 0.5 or seen[i]:
            continue
        q = [i]
        seen[i] = 1
        ids: List[int] = []
        sx = sy = sz = 0.0
        while q:
            v = q.pop()
            ids.append(v)
            x, y, z = idx_to_xyz(v, nx=nx, ny=ny)
            sx += float(x)
            sy += float(y)
            sz += float(z)
            for u in neighbors_3d(v, nx, ny, nz):
                if iface_mask[u] > 0.5 and not seen[u]:
                    seen[u] = 1
                    q.append(u)
        if ids:
            inv = 1.0 / float(len(ids))
            comps.append(Component(ids=ids, centroid=(sx * inv, sy * inv, sz * inv)))
    return comps


def l2(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


@dataclass
class Track:
    tid: int
    t0: int
    last_t: int
    last_centroid: Tuple[float, float, float]
    speeds: List[float]
    alive: bool = True


def match_tracks(tracks: List[Track], comps: List[Component], t: int, max_match_dist: float) -> None:
    # Greedy matching: for each component, attach to nearest alive track if within distance.
    used_tracks: set[int] = set()
    used_comps: set[int] = set()

    # Precompute pairs
    pairs: List[Tuple[float, int, int]] = []
    for ci, c in enumerate(comps):
        for ti, tr in enumerate(tracks):
            if not tr.alive:
                continue
            d = l2(c.centroid, tr.last_centroid)
            if d <= max_match_dist:
                pairs.append((d, ci, ti))
    pairs.sort(key=lambda x: x[0])

    for d, ci, ti in pairs:
        if ci in used_comps or ti in used_tracks:
            continue
        tr = tracks[ti]
        tr.speeds.append(float(d))
        tr.last_centroid = comps[ci].centroid
        tr.last_t = t
        used_tracks.add(ti)
        used_comps.add(ci)

    # Mark unmatched alive tracks as dead if they didn't match at this time.
    for ti, tr in enumerate(tracks):
        if tr.alive and ti not in used_tracks:
            tr.alive = False

    # Start new tracks for unmatched components.
    next_id = (max([tr.tid for tr in tracks], default=-1) + 1)
    for ci, c in enumerate(comps):
        if ci in used_comps:
            continue
        tracks.append(Track(tid=next_id, t0=t, last_t=t, last_centroid=c.centroid, speeds=[]))
        next_id += 1


def write_objects_tex(summary: Dict[str, float], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("% Auto-generated by scripts/exp_emergence_objects.py")
    lines.append("\\begin{tabular}{lr}")
    lines.append("\\toprule")
    lines.append("Quantity & Value\\\\")
    lines.append("\\midrule")
    lines.append(f"mean objects per step & {summary['obj_count_mean']:.3f}\\\\")
    lines.append(f"max objects per step & {summary['obj_count_max']:.3f}\\\\")
    lines.append(f"mean lifetime (steps) & {summary['lifetime_mean']:.3f}\\\\")
    lines.append(f"max lifetime (steps) & {summary['lifetime_max']:.3f}\\\\")
    lines.append(f"mean speed & {summary['speed_mean']:.3f}\\\\")
    lines.append(f"max speed & {summary['speed_max']:.3f}\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=10)
    ap.add_argument("--q", type=int, default=7)
    ap.add_argument("--nx", type=int, default=9)
    ap.add_argument("--ny", type=int, default=9)
    ap.add_argument("--nz", type=int, default=5)
    ap.add_argument("--steps", type=int, default=80)
    ap.add_argument("--threshold", type=float, default=0.50)
    ap.add_argument("--beta", type=float, default=6.0)
    ap.add_argument("--coupling", type=float, default=1.0)
    ap.add_argument("--noise", type=float, default=0.02)
    ap.add_argument("--defect-rate", type=float, default=0.006)
    ap.add_argument("--r-diffusion", type=float, default=0.25)
    ap.add_argument("--match-dist", type=float, default=1.8)
    ap.add_argument("--seed", type=int, default=0)
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
    match_dist = float(args.match_dist)
    seed = int(args.seed)

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
        "match_dist": match_dist,
        "seed": seed,
    }

    run = prepare_run(
        experiment="emergence_objects",
        params=params,
        script_path=script_path,
        required_files=["summary.json", "object_count.png", "lifetime_hist.png", "speed_hist.png"],
        force=bool(args.force),
    )

    out_json = run.run_dir / "summary.json"
    out_count = run.run_dir / "object_count.png"
    out_life = run.run_dir / "lifetime_hist.png"
    out_speed = run.run_dir / "speed_hist.png"
    out_tex = generated_dir() / "emergence_objects_summary.tex"

    if run.cached:
        print(f"[emergence_objects] cached: {run.run_dir}", flush=True)
        return

    prog = Progress(every_seconds=15.0)
    rng = random.Random(seed)

    Xm = list(iter_no_adjacent_words(m))
    Xm.sort()
    n = nx * ny * nz
    center = (nz // 2) * (nx * ny) + (ny // 2) * nx + (nx // 2)
    nbrs = [neighbors_3d(i, nx, ny, nz) for i in range(n)]

    x = np.array([Xm[rng.randrange(len(Xm))] for _ in range(n)], dtype=np.int64)
    r = np.array([rng.randrange(qmod) for _ in range(n)], dtype=np.int64)
    # Seed a localized perturbation to initiate motion.
    bit0 = (m // 2)
    x[center] = propose_set_bit_with_local_repair(int(x[center]), m=m, bit_i=bit0, want1=1)
    r[center] = (int(r[center]) + 1) % qmod

    tracks: List[Track] = []
    obj_counts: List[int] = []

    for t in range(steps + 1):
        iface = np.array([1.0 if is_in_Bm(int(xx), m) else 0.0 for xx in x], dtype=np.float64)
        comps = components_from_iface(iface, nx=nx, ny=ny, nz=nz)
        obj_counts.append(len(comps))
        match_tracks(tracks, comps, t=t, max_match_dist=match_dist)

        prog.maybe(f"t={t}/{steps} comps={len(comps)} tracks={sum(1 for tr in tracks if tr.alive)}")
        if t == steps:
            break

        bit_i = (t % m)
        u_noise = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_defect = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_bit = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_r = np.array([rng.random() for _ in range(n)], dtype=np.float64)

        x_next = x.copy()
        r_next = r.copy()

        for i in range(n):
            nm = avg_neighbor_bit(x, nbrs[i], bit_i=bit_i)
            bias = beta * (nm - threshold) + coupling * ((float(r[i]) / float(qmod)) - 0.5)
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
                d = mnr - float(int(r[i]))
                step = 1 if d > 0.25 else (-1 if d < -0.25 else 0)
                r_new = (r_new + step) % qmod

            x_next[i] = x_new
            r_next[i] = r_new

        x, r = x_next, r_next

    # Finalize tracks: mark any alive as ended at last_t.
    for tr in tracks:
        if tr.alive:
            tr.alive = False

    lifetimes = [float(tr.last_t - tr.t0 + 1) for tr in tracks if (tr.last_t >= tr.t0)]
    speeds = [float(v) for tr in tracks for v in tr.speeds]

    summary = {
        "obj_count_mean": float(np.mean(obj_counts)) if obj_counts else 0.0,
        "obj_count_max": float(np.max(obj_counts)) if obj_counts else 0.0,
        "lifetime_mean": float(np.mean(lifetimes)) if lifetimes else 0.0,
        "lifetime_max": float(np.max(lifetimes)) if lifetimes else 0.0,
        "speed_mean": float(np.mean(speeds)) if speeds else 0.0,
        "speed_max": float(np.max(speeds)) if speeds else 0.0,
        "n_tracks": float(len(tracks)),
    }

    # Plots
    plt.figure(figsize=(7.0, 4.0))
    plt.plot(obj_counts, color="#1f77b4", linewidth=2.0)
    plt.title("Object count (interface components) vs time")
    plt.xlabel("t")
    plt.ylabel("#components")
    plt.tight_layout()
    plt.savefig(out_count, dpi=160)
    plt.close()

    plt.figure(figsize=(7.0, 4.0))
    plt.hist(lifetimes, bins=30, color="#2ca02c", alpha=0.9)
    plt.title("Lifetime histogram")
    plt.xlabel("lifetime (steps)")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(out_life, dpi=160)
    plt.close()

    plt.figure(figsize=(7.0, 4.0))
    plt.hist(speeds, bins=30, color="#ff7f0e", alpha=0.9)
    plt.title("Speed histogram (centroid step displacement)")
    plt.xlabel("speed")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(out_speed, dpi=160)
    plt.close()

    payload = {"params": params, "summary": summary}
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_objects_tex(summary=summary, out_path=out_tex)

    manifest = build_base_manifest("emergence_objects", run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, ["summary.json", "object_count.png", "lifetime_hist.png", "speed_hist.png"])
    write_manifest(run.run_dir, manifest)

    # Stable exports
    ed = export_dir()
    ed.mkdir(parents=True, exist_ok=True)
    copy_atomic(out_count, ed / "emergence_object_count.png")
    copy_atomic(out_life, ed / "emergence_object_lifetime_hist.png")
    copy_atomic(out_speed, ed / "emergence_object_speed_hist.png")

    prog.done(f"wrote {out_json}, plots, and {out_tex}")


if __name__ == "__main__":
    main()

