#!/usr/bin/env python3
"""
Scan transport drive parameters for moving objects.

We scan advect_p and coupling (with optional residual-gradient drive), and measure:
  - moving_frac (tracks with |cum_dx| >= move_min over lifetime >= min_length)
  - drift_abs_mean over moving tracks (|Δx| / lifetime)

Outputs:
  - artifacts/emergence_transport_scan/<run_id>/summary.json
  - artifacts/emergence_transport_scan/<run_id>/phase_moving.png
  - artifacts/emergence_transport_scan/<run_id>/phase_drift.png
  - sections/generated/emergence_transport_scan.tex
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


def _wrap_signed_dx(x_new: float, x_old: float, nx: int) -> float:
    dx = float(x_new - x_old)
    dx = ((dx + 0.5 * nx) % nx) - 0.5 * nx
    return float(dx)

def _wrap_l2(c_new: Tuple[float, float, float], c_old: Tuple[float, float, float], nx: int) -> float:
    dx = _wrap_signed_dx(float(c_new[0]), float(c_old[0]), nx=nx)
    dy = float(c_new[1]) - float(c_old[1])
    dz = float(c_new[2]) - float(c_old[2])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _centered_mod_diff(a: int, b: int, q: int) -> int:
    if q <= 0:
        return int(a - b)
    half = q / 2.0
    d = ((int(a) - int(b) + half) % q) - half
    return int(round(d))


@dataclass
class Component:
    ids: List[int]
    centroid: Tuple[float, float, float]


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


@dataclass
class Track:
    last_c: Tuple[float, float, float]
    cum_dx: float
    t0: int
    last_t: int
    alive: bool = True


def match_tracks(tracks: List[Track], comps: List[Component], t: int, max_match_dist: float, nx: int) -> None:
    used_tracks: set[int] = set()
    used_comps: set[int] = set()
    pairs: List[Tuple[float, int, int]] = []
    for ci, c in enumerate(comps):
        for ti, tr in enumerate(tracks):
            if not tr.alive:
                continue
            d = _wrap_l2(c.centroid, tr.last_c, nx=nx)
            if d <= max_match_dist:
                pairs.append((d, ci, ti))
    pairs.sort(key=lambda x: x[0])
    for d, ci, ti in pairs:
        if ci in used_comps or ti in used_tracks:
            continue
        tr = tracks[ti]
        c_new = comps[ci].centroid
        tr.cum_dx += _wrap_signed_dx(float(c_new[0]), float(tr.last_c[0]), nx=nx)
        tr.last_c = c_new
        tr.last_t = t
        used_tracks.add(ti)
        used_comps.add(ci)
    for ti, tr in enumerate(tracks):
        if tr.alive and ti not in used_tracks:
            tr.alive = False
    for ci, c in enumerate(comps):
        if ci in used_comps:
            continue
        tracks.append(Track(last_c=c.centroid, cum_dx=0.0, t0=t, last_t=t, alive=True))


def simulate(
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
    match_dist: float,
    min_length: int,
    move_min: float,
    seed: int,
) -> Dict[str, float]:
    rng = random.Random(seed)
    Xm = list(iter_no_adjacent_words(m))
    Xm.sort()
    n = nx * ny * nz
    center = (nz // 2) * (nx * ny) + (ny // 2) * nx + (nx // 2)
    nbrs = [neighbors_3d(i, nx, ny, nz) for i in range(n)]

    x = np.array([Xm[rng.randrange(len(Xm))] for _ in range(n)], dtype=np.int64)
    r = np.array([rng.randrange(qmod) for _ in range(n)], dtype=np.int64)
    bit0 = (m // 2)
    x[center] = inject_interface_defect(propose_set_bit_with_local_repair(int(x[center]), m=m, bit_i=bit0, want1=1), m=m)
    r[center] = (int(r[center]) + 1) % qmod

    tracks: List[Track] = []
    for t in range(steps + 1):
        iface = np.array([1.0 if is_in_Bm(int(xx), m) else 0.0 for xx in x], dtype=np.float64)
        comps = components_from_iface(iface, nx=nx, ny=ny, nz=nz)
        match_tracks(tracks, comps, t=t, max_match_dist=match_dist, nx=nx)
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
                d = _centered_mod_diff(int(r[il]), int(r[ir]), q=qmod)
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

    drifts: List[float] = []
    for tr in tracks:
        L = (tr.last_t - tr.t0 + 1)
        if L >= min_length:
            drifts.append(float(tr.cum_dx) / float(L))
    moving = [v for v in drifts if abs(v) * float(min_length) >= move_min]
    return {
        "n_tracks": float(len(drifts)),
        "moving_frac": float(len(moving)) / float(max(1, len(drifts))),
        "drift_abs_mean": float(np.mean([abs(v) for v in moving])) if moving else 0.0,
    }


def write_scan_tex(best: Dict[str, float], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("% Auto-generated by scripts/exp_emergence_transport_scan.py")
    lines.append("\\begin{tabular}{lr}")
    lines.append("\\toprule")
    lines.append("Best metric & Value\\\\")
    lines.append("\\midrule")
    lines.append(f"advect\\_p & {best['advect_p']:.3f}\\\\")
    lines.append(f"coupling & {best['coupling']:.3f}\\\\")
    lines.append(f"drive\\_gamma & {best['drive_gamma']:.3f}\\\\")
    lines.append(f"moving\\_frac & {best['moving_frac']:.4f}\\\\")
    lines.append(f"drift\\_abs\\_mean & {best['drift_abs_mean']:.4f}\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=10)
    ap.add_argument("--q", type=int, default=7)
    ap.add_argument("--nx", type=int, default=11)
    ap.add_argument("--ny", type=int, default=7)
    ap.add_argument("--nz", type=int, default=3)
    ap.add_argument("--steps", type=int, default=160)
    ap.add_argument("--threshold", type=float, default=0.50)
    ap.add_argument("--beta", type=float, default=6.0)
    ap.add_argument("--noise", type=float, default=0.02)
    ap.add_argument("--defect-rate", type=float, default=0.006)
    ap.add_argument("--r-diffusion", type=float, default=0.25)
    ap.add_argument("--advect-dir", type=int, default=1)
    ap.add_argument("--drive-gamma", type=float, default=0.0)
    ap.add_argument("--advect-ps", type=str, default="0.0,0.2,0.4,0.6,0.8")
    ap.add_argument("--couplings", type=str, default="0.5,1.0,2.0,3.0")
    ap.add_argument("--match-dist", type=float, default=2.2)
    ap.add_argument("--min-length", type=int, default=30)
    ap.add_argument("--move-min", type=float, default=1.0)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--n-seeds", type=int, default=3)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    m = int(args.m)
    qmod = int(args.q)
    nx, ny, nz = int(args.nx), int(args.ny), int(args.nz)
    steps = int(args.steps)
    threshold = float(args.threshold)
    beta = float(args.beta)
    noise = float(args.noise)
    defect_rate = float(args.defect_rate)
    r_diffusion = float(args.r_diffusion)
    advect_dir = int(args.advect_dir)
    drive_gamma = float(args.drive_gamma)
    advect_ps = [float(s.strip()) for s in args.advect_ps.split(",") if s.strip()]
    couplings = [float(s.strip()) for s in args.couplings.split(",") if s.strip()]
    match_dist = float(args.match_dist)
    min_length = int(args.min_length)
    move_min = float(args.move_min)
    seed0 = int(args.seed0)
    n_seeds = int(args.n_seeds)

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
        "noise": noise,
        "defect_rate": defect_rate,
        "r_diffusion": r_diffusion,
        "advect_dir": advect_dir,
        "drive_gamma": drive_gamma,
        "advect_ps": advect_ps,
        "couplings": couplings,
        "match_dist": match_dist,
        "min_length": min_length,
        "move_min": move_min,
        "seed0": seed0,
        "n_seeds": n_seeds,
    }

    run = prepare_run(
        experiment="emergence_transport_scan",
        params=params,
        script_path=script_path,
        required_files=["summary.json", "phase_moving.png", "phase_drift.png"],
        force=bool(args.force),
    )

    out_json = run.run_dir / "summary.json"
    out_moving = run.run_dir / "phase_moving.png"
    out_drift = run.run_dir / "phase_drift.png"
    out_tex = generated_dir() / "emergence_transport_scan.tex"

    if run.cached:
        print(f"[emergence_transport_scan] cached: {run.run_dir}", flush=True)
        return

    prog = Progress(every_seconds=15.0)
    M = np.zeros((len(couplings), len(advect_ps)), dtype=np.float64)
    D = np.zeros_like(M)

    best = {"score": -1.0, "advect_p": 0.0, "coupling": 0.0, "moving_frac": 0.0, "drift_abs_mean": 0.0}
    total = len(couplings) * len(advect_ps) * n_seeds
    done = 0
    for ic, coup in enumerate(couplings):
        for ia, apv in enumerate(advect_ps):
            mf: List[float] = []
            dm: List[float] = []
            for s in range(n_seeds):
                res = simulate(
                    m=m,
                    qmod=qmod,
                    nx=nx,
                    ny=ny,
                    nz=nz,
                    steps=steps,
                    threshold=threshold,
                    beta=beta,
                    coupling=coup,
                    noise=noise,
                    defect_rate=defect_rate,
                    r_diffusion=r_diffusion,
                    advect_p=apv,
                    advect_dir=advect_dir,
                    drive_gamma=drive_gamma,
                    match_dist=match_dist,
                    min_length=min_length,
                    move_min=move_min,
                    seed=seed0 + s,
                )
                mf.append(float(res["moving_frac"]))
                dm.append(float(res["drift_abs_mean"]))
                done += 1
                prog.maybe(f"scan {done}/{total}")

            M[ic, ia] = float(sum(mf)) / float(len(mf))
            D[ic, ia] = float(sum(dm)) / float(len(dm))
            score = M[ic, ia] + 0.5 * D[ic, ia]
            if score > best["score"]:
                best = {
                    "score": float(score),
                    "advect_p": float(apv),
                    "coupling": float(coup),
                    "moving_frac": float(M[ic, ia]),
                    "drift_abs_mean": float(D[ic, ia]),
                    "drive_gamma": float(drive_gamma),
                }

    def heatmap(data: np.ndarray, title: str, out_path: Path, cmap: str) -> None:
        plt.figure(figsize=(8.0, 4.0))
        plt.imshow(data, aspect="auto", origin="lower", cmap=cmap)
        plt.xticks(list(range(len(advect_ps))), [f"{a:.2f}" for a in advect_ps], rotation=45, ha="right")
        plt.yticks(list(range(len(couplings))), [f"{c:.2f}" for c in couplings])
        plt.xlabel("advect_p")
        plt.ylabel("coupling")
        plt.title(title)
        plt.colorbar()
        plt.tight_layout()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_path, dpi=160)
        plt.close()

    heatmap(M, "moving_frac", out_moving, cmap="magma")
    heatmap(D, "mean |drift| (moving)", out_drift, cmap="viridis")

    payload = {"params": params, "moving_frac": M.tolist(), "drift_abs_mean": D.tolist(), "best": best}
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_scan_tex(best=best, out_path=out_tex)

    manifest = build_base_manifest("emergence_transport_scan", run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, ["summary.json", "phase_moving.png", "phase_drift.png"])
    write_manifest(run.run_dir, manifest)

    ed = export_dir()
    ed.mkdir(parents=True, exist_ok=True)
    copy_atomic(out_moving, ed / "emergence_transport_phase_moving.png")
    copy_atomic(out_drift, ed / "emergence_transport_phase_drift.png")

    prog.done(f"wrote {out_json}, phase plots, and {out_tex}")


if __name__ == "__main__":
    main()

