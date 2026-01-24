#!/usr/bin/env python3
"""
Walking periodic orbits in driven transport dynamics.

Goal:
  Detect p>=2 "walking" periodic tracks where the cluster shape repeats while the
  support translates (net displacement per period != 0).

Method:
  - Simulate the same local transport dynamics as exp_emergence_transport.py.
  - Extract interface clusters (B_m components) and track them with 3D centroid
    matching (wrap in x).
  - For each track, build a shape signature: relative voxel coordinates centered
    at the rounded centroid, with x-differences wrapped to (-nx/2,nx/2].
  - Detect smallest period p such that signatures repeat for >=K cycles and the
    per-period x-displacement is consistent and nonzero.

Outputs:
  - artifacts/emergence_transport_walkers/<run_id>/summary.json
  - artifacts/emergence_transport_walkers/<run_id>/period_hist.png
  - artifacts/emergence_transport_walkers/<run_id>/step_hist.png
  - artifacts/emergence_transport_walkers/<run_id>/stability_scatter.png
  - sections/generated/emergence_transport_walkers_summary.tex
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


def shape_signature(ids: List[int], centroid: Tuple[float, float, float], nx: int, ny: int) -> Tuple[Tuple[int, int, int], ...]:
    cx = int(round(float(centroid[0])))
    cy = int(round(float(centroid[1])))
    cz = int(round(float(centroid[2])))
    sig: List[Tuple[int, int, int]] = []
    for idx in ids:
        x, y, z = idx_to_xyz(idx, nx=nx, ny=ny)
        dx = int(round(wrap_signed_dx(float(x), float(cx), nx=nx)))
        dy = int(y - cy)
        dz = int(z - cz)
        sig.append((dx, dy, dz))
    sig.sort()
    return tuple(sig)


@dataclass
class Component:
    ids: List[int]
    centroid: Tuple[float, float, float]
    sig: Tuple[Tuple[int, int, int], ...]


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
            c = (sx * inv, sy * inv, sz * inv)
            comps.append(Component(ids=ids, centroid=c, sig=shape_signature(ids, c, nx=nx, ny=ny)))
    return comps


@dataclass
class Track:
    tid: int
    t0: int
    times: List[int]
    centroids: List[Tuple[float, float, float]]
    sigs: List[Tuple[Tuple[int, int, int], ...]]
    cum_dx: List[float]
    alive: bool = True


def match_tracks(tracks: List[Track], comps: List[Component], t: int, max_match_dist: float, nx: int) -> None:
    used_tracks: set[int] = set()
    used_comps: set[int] = set()
    pairs: List[Tuple[float, int, int]] = []
    for ci, c in enumerate(comps):
        for ti, tr in enumerate(tracks):
            if not tr.alive:
                continue
            d = wrap_l2(c.centroid, tr.centroids[-1], nx=nx)
            if d <= max_match_dist:
                pairs.append((d, ci, ti))
    pairs.sort(key=lambda x: x[0])
    for d, ci, ti in pairs:
        if ci in used_comps or ti in used_tracks:
            continue
        tr = tracks[ti]
        c_new = comps[ci].centroid
        dx = wrap_signed_dx(float(c_new[0]), float(tr.centroids[-1][0]), nx=nx)
        tr.times.append(t)
        tr.centroids.append(c_new)
        tr.sigs.append(comps[ci].sig)
        tr.cum_dx.append(float(tr.cum_dx[-1] + dx))
        used_tracks.add(ti)
        used_comps.add(ci)
    for ti, tr in enumerate(tracks):
        if tr.alive and ti not in used_tracks:
            tr.alive = False
    next_id = (max([tr.tid for tr in tracks], default=-1) + 1)
    for ci, c in enumerate(comps):
        if ci in used_comps:
            continue
        tracks.append(
            Track(
                tid=next_id,
                t0=t,
                times=[t],
                centroids=[c.centroid],
                sigs=[c.sig],
                cum_dx=[0.0],
                alive=True,
            )
        )
        next_id += 1


def detect_walking_period(
    *,
    sigs: List[Tuple[Tuple[int, int, int], ...]],
    cum_dx: List[float],
    tol_dx: float,
    min_cycles: int,
    p_max: int,
    step_min: float,
    shape_jaccard_min: float,
) -> Tuple[int, float]:
    """
    Return (p, step_per_period) where p>=2 and step_per_period!=0 if found, else (0,0).
    """
    n = len(sigs)
    if n < (min_cycles + 1):
        return 0, 0.0
    for p in range(2, min(p_max, n // max(1, min_cycles)) + 1):
        ok = True
        checks = 0
        step0: float | None = None
        for t in range(0, n - p):
            a = sigs[t]
            b = sigs[t + p]
            # Robust shape similarity via Jaccard on voxel-relative coordinates.
            ia = ib = 0
            inter = 0
            while ia < len(a) and ib < len(b):
                if a[ia] == b[ib]:
                    inter += 1
                    ia += 1
                    ib += 1
                elif a[ia] < b[ib]:
                    ia += 1
                else:
                    ib += 1
            union = len(a) + len(b) - inter
            jac = (float(inter) / float(union)) if union > 0 else 1.0
            if jac < shape_jaccard_min:
                ok = False
                break
            step = float(cum_dx[t + p] - cum_dx[t])
            if step0 is None:
                step0 = step
            else:
                if abs(step - step0) > tol_dx:
                    ok = False
                    break
            checks += 1
            if checks >= (p * min_cycles):
                break
        if ok and checks >= (p * min_cycles) and step0 is not None and abs(step0) >= step_min:
            return p, float(step0)
    return 0, 0.0


def shape_jaccard(a: Tuple[Tuple[int, int, int], ...], b: Tuple[Tuple[int, int, int], ...]) -> float:
    ia = ib = 0
    inter = 0
    while ia < len(a) and ib < len(b):
        if a[ia] == b[ib]:
            inter += 1
            ia += 1
            ib += 1
        elif a[ia] < b[ib]:
            ia += 1
        else:
            ib += 1
    union = len(a) + len(b) - inter
    return (float(inter) / float(union)) if union > 0 else 1.0


def write_walkers_tex(summary: Dict[str, float], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("% Auto-generated by scripts/exp_emergence_transport_walkers.py")
    lines.append("\\begin{tabular}{lr}")
    lines.append("\\toprule")
    lines.append("Quantity & Value\\\\")
    lines.append("\\midrule")
    lines.append(f"tracks analyzed & {summary['n_tracks']:.0f}\\\\")
    lines.append(f"walking fraction & {summary['walking_frac']:.4f}\\\\")
    lines.append(f"mean walking period & {summary['p_mean']:.3f}\\\\")
    lines.append(f"max walking period & {summary['p_max']:.3f}\\\\")
    lines.append(f"mean |step| per period & {summary['step_abs_mean']:.3f}\\\\")
    lines.append("\\midrule")
    lines.append(f"quasi-walker fraction & {summary['quasi_frac']:.4f}\\\\")
    lines.append(f"mean |drift| (quasi) & {summary['quasi_drift_abs_mean']:.4f}\\\\")
    lines.append(f"mean stability (quasi) & {summary['quasi_stability_mean']:.4f}\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    ap.add_argument("--match-dist", type=float, default=2.2)
    ap.add_argument("--min-length", type=int, default=60)
    ap.add_argument("--p-max", type=int, default=30)
    ap.add_argument("--min-cycles", type=int, default=3)
    ap.add_argument("--tol-dx", type=float, default=0.75)
    ap.add_argument("--step-min", type=float, default=0.75, help="Minimum |Δx| per period to count as walking.")
    ap.add_argument("--shape-jaccard", type=float, default=0.90, help="Minimum Jaccard similarity of shapes across a period.")
    ap.add_argument("--drift-min", type=float, default=0.02, help="Minimum |mean drift| per step for quasi-walker.")
    ap.add_argument("--stability-min", type=float, default=0.85, help="Minimum median shape Jaccard between consecutive frames.")
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
    advect_p = float(args.advect_p)
    advect_dir = int(args.advect_dir)
    drive_gamma = float(args.drive_gamma)
    match_dist = float(args.match_dist)
    min_length = int(args.min_length)
    p_max = int(args.p_max)
    min_cycles = int(args.min_cycles)
    tol_dx = float(args.tol_dx)
    step_min = float(args.step_min)
    shape_jaccard_thr = float(args.shape_jaccard)
    drift_min = float(args.drift_min)
    stability_min = float(args.stability_min)
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
        "advect_p": advect_p,
        "advect_dir": advect_dir,
        "drive_gamma": drive_gamma,
        "match_dist": match_dist,
        "min_length": min_length,
        "p_max": p_max,
        "min_cycles": min_cycles,
        "tol_dx": tol_dx,
        "step_min": step_min,
        "shape_jaccard": shape_jaccard_thr,
        "drift_min": drift_min,
        "stability_min": stability_min,
        "seed": seed,
    }

    run = prepare_run(
        experiment="emergence_transport_walkers",
        params=params,
        script_path=script_path,
        required_files=["summary.json", "period_hist.png", "step_hist.png", "stability_scatter.png"],
        force=bool(args.force),
    )

    out_json = run.run_dir / "summary.json"
    out_period = run.run_dir / "period_hist.png"
    out_step = run.run_dir / "step_hist.png"
    out_scatter = run.run_dir / "stability_scatter.png"
    out_tex = generated_dir() / "emergence_transport_walkers_summary.tex"

    if run.cached:
        print(f"[emergence_transport_walkers] cached: {run.run_dir}", flush=True)
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

    # seed a localized defect
    bit0 = (m // 2)
    x[center] = inject_interface_defect(propose_set_bit_with_local_repair(int(x[center]), m=m, bit_i=bit0, want1=1), m=m)
    r[center] = (int(r[center]) + 1) % qmod

    tracks: List[Track] = []

    for t in range(steps + 1):
        iface = np.array([1.0 if is_in_Bm(int(xx), m) else 0.0 for xx in x], dtype=np.float64)
        comps = components_from_iface(iface, nx=nx, ny=ny, nz=nz)
        match_tracks(tracks, comps, t=t, max_match_dist=match_dist, nx=nx)
        prog.maybe(f"t={t}/{steps} comps={len(comps)} tracks={len(tracks)}")
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

    # analyze walking periodic tracks
    periods: List[int] = []
    steps_per_period: List[float] = []
    drifts_abs: List[float] = []
    stabilities: List[float] = []
    quasi_idx: List[int] = []
    n_an = 0
    for tr in tracks:
        if len(tr.times) < min_length:
            continue
        n_an += 1
        p, step = detect_walking_period(
            sigs=tr.sigs,
            cum_dx=tr.cum_dx,
            tol_dx=tol_dx,
            min_cycles=min_cycles,
            p_max=p_max,
            step_min=step_min,
            shape_jaccard_min=shape_jaccard_thr,
        )
        if p > 0:
            periods.append(int(p))
            steps_per_period.append(float(step))

        # quasi-walker: stable shape + nontrivial mean drift
        if len(tr.sigs) >= 2:
            jacs = [shape_jaccard(tr.sigs[i], tr.sigs[i + 1]) for i in range(len(tr.sigs) - 1)]
            med_j = float(np.median(jacs)) if jacs else 0.0
        else:
            med_j = 0.0
        mean_drift = float(tr.cum_dx[-1]) / float(max(1, len(tr.cum_dx) - 1))
        drifts_abs.append(abs(mean_drift))
        stabilities.append(med_j)
        if abs(mean_drift) >= drift_min and med_j >= stability_min:
            quasi_idx.append(len(drifts_abs) - 1)

    summary = {
        "n_tracks": float(n_an),
        "walking_frac": float(len(periods)) / float(max(1, n_an)),
        "p_mean": float(np.mean(periods)) if periods else 0.0,
        "p_max": float(np.max(periods)) if periods else 0.0,
        "step_abs_mean": float(np.mean([abs(s) for s in steps_per_period])) if steps_per_period else 0.0,
        "quasi_frac": float(len(quasi_idx)) / float(max(1, n_an)),
        "quasi_drift_abs_mean": float(np.mean([drifts_abs[i] for i in quasi_idx])) if quasi_idx else 0.0,
        "quasi_stability_mean": float(np.mean([stabilities[i] for i in quasi_idx])) if quasi_idx else 0.0,
    }

    plt.figure(figsize=(7.0, 4.0))
    if periods:
        plt.hist(periods, bins=min(30, max(5, len(set(periods)) * 2)), color="#1f77b4", alpha=0.9)
    plt.title("Walking period histogram (p>=2)")
    plt.xlabel("period p")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(out_period, dpi=160)
    plt.close()

    plt.figure(figsize=(7.0, 4.0))
    if steps_per_period:
        plt.hist([abs(s) for s in steps_per_period], bins=30, color="#d62728", alpha=0.9)
    plt.title("Walking step per period |Δx_p|")
    plt.xlabel("|Δx| per period")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(out_step, dpi=160)
    plt.close()

    plt.figure(figsize=(7.0, 5.0))
    if drifts_abs:
        plt.scatter(drifts_abs, stabilities, s=18, alpha=0.75, color="#9467bd")
    plt.axvline(drift_min, color="#d62728", linestyle="--", linewidth=1.5)
    plt.axhline(stability_min, color="#2ca02c", linestyle="--", linewidth=1.5)
    plt.title("Quasi-walker: drift vs shape stability")
    plt.xlabel("|mean drift| per step")
    plt.ylabel("median Jaccard(shape_t, shape_{t+1})")
    plt.ylim(0.0, 1.02)
    plt.tight_layout()
    plt.savefig(out_scatter, dpi=160)
    plt.close()

    payload = {
        "params": params,
        "summary": summary,
        "periods": periods,
        "steps_per_period": steps_per_period,
        "drifts_abs": drifts_abs,
        "stabilities": stabilities,
    }
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_walkers_tex(summary=summary, out_path=out_tex)

    manifest = build_base_manifest("emergence_transport_walkers", run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, ["summary.json", "period_hist.png", "step_hist.png", "stability_scatter.png"])
    write_manifest(run.run_dir, manifest)

    ed = export_dir()
    ed.mkdir(parents=True, exist_ok=True)
    copy_atomic(out_period, ed / "emergence_transport_walkers_period_hist.png")
    copy_atomic(out_step, ed / "emergence_transport_walkers_step_hist.png")
    copy_atomic(out_scatter, ed / "emergence_transport_walkers_stability_scatter.png")

    prog.done(f"wrote {out_json}, plots, and {out_tex}")


if __name__ == "__main__":
    main()

