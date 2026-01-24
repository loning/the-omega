#!/usr/bin/env python3
"""
Driven transport experiment: try to induce moving (p>=2) objects.

We add a directional drive along +x by advecting the residual r field:
  with probability advect_p, r(x,y,z) <- r(x-1,y,z) (wrap at boundary)
This breaks detailed balance and can generate traveling structures.

We track interface-cluster objects (B_m components) and measure:
  - net displacement along x over lifetime
  - drift velocity = Δx / lifetime
  - moving fraction: fraction of tracks with |Δx| >= move_min

Outputs:
  - artifacts/emergence_transport/<run_id>/summary.json
  - artifacts/emergence_transport/<run_id>/drift_hist.png
  - artifacts/emergence_transport/<run_id>/moving_fraction.png
  - sections/generated/emergence_transport_summary.tex
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


def l2(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


@dataclass
class Track:
    tid: int
    t0: int
    last_t: int
    c0: Tuple[float, float, float]
    last_c: Tuple[float, float, float]
    cum_dx: float
    alive: bool = True


def _wrap_signed_dx(x_new: float, x_old: float, nx: int) -> float:
    """
    Signed shortest displacement on a ring of length nx, in (-nx/2, nx/2].
    """
    dx = float(x_new - x_old)
    # map to (-nx/2, nx/2]
    dx = ((dx + 0.5 * nx) % nx) - 0.5 * nx
    return float(dx)


def _wrap_l2(c_new: Tuple[float, float, float], c_old: Tuple[float, float, float], nx: int) -> float:
    dx = _wrap_signed_dx(float(c_new[0]), float(c_old[0]), nx=nx)
    dy = float(c_new[1]) - float(c_old[1])
    dz = float(c_new[2]) - float(c_old[2])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _centered_mod_diff(a: int, b: int, q: int) -> int:
    """
    Smallest signed difference a-b on Z_q in (-q/2, q/2].
    """
    if q <= 0:
        return int(a - b)
    half = q / 2.0
    d = ((int(a) - int(b) + half) % q) - half
    # ensure integer-ish (q is small); keep sign
    return int(round(d))


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
    next_id = (max([tr.tid for tr in tracks], default=-1) + 1)
    for ci, c in enumerate(comps):
        if ci in used_comps:
            continue
        c0 = c.centroid
        tracks.append(Track(tid=next_id, t0=t, last_t=t, c0=c0, last_c=c0, cum_dx=0.0, alive=True))
        next_id += 1


def write_transport_tex(summary: Dict[str, float], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("% Auto-generated by scripts/exp_emergence_transport.py")
    lines.append("\\begin{tabular}{lr}")
    lines.append("\\toprule")
    lines.append("Quantity & Value\\\\")
    lines.append("\\midrule")
    lines.append(f"moving fraction & {summary['moving_frac']:.4f}\\\\")
    lines.append(f"mean drift velocity & {summary['drift_mean']:.4f}\\\\")
    lines.append(f"max drift velocity & {summary['drift_max']:.4f}\\\\")
    lines.append(f"tracks analyzed & {summary['n_tracks']:.0f}\\\\")
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
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--threshold", type=float, default=0.50)
    ap.add_argument("--beta", type=float, default=6.0)
    ap.add_argument("--coupling", type=float, default=1.0)
    ap.add_argument("--noise", type=float, default=0.02)
    ap.add_argument("--defect-rate", type=float, default=0.006)
    ap.add_argument("--r-diffusion", type=float, default=0.25)
    ap.add_argument("--advect-p", type=float, default=0.6, help="Residual advection probability along +x.")
    ap.add_argument("--advect-dir", type=int, default=1, help="Advection direction along x: +1 uses src=x-1 (right-moving), -1 uses src=x+1.")
    ap.add_argument("--drive-gamma", type=float, default=0.0, help="Residual x-gradient drive strength added to macro bias.")
    ap.add_argument("--match-dist", type=float, default=2.2)
    ap.add_argument("--min-length", type=int, default=30)
    ap.add_argument("--move-min", type=float, default=3.0, help="Minimum |Δx| to count as moving.")
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
    move_min = float(args.move_min)
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
        "move_min": move_min,
        "seed": seed,
    }

    run = prepare_run(
        experiment="emergence_transport",
        params=params,
        script_path=script_path,
        required_files=["summary.json", "drift_hist.png", "moving_fraction.png"],
        force=bool(args.force),
    )

    out_json = run.run_dir / "summary.json"
    out_hist = run.run_dir / "drift_hist.png"
    out_frac = run.run_dir / "moving_fraction.png"
    out_tex = generated_dir() / "emergence_transport_summary.tex"

    if run.cached:
        print(f"[emergence_transport] cached: {run.run_dir}", flush=True)
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
    moving_frac_ts: List[float] = []

    for t in range(steps + 1):
        iface = np.array([1.0 if is_in_Bm(int(xx), m) else 0.0 for xx in x], dtype=np.float64)
        comps = components_from_iface(iface, nx=nx, ny=ny, nz=nz)
        match_tracks(tracks, comps, t=t, max_match_dist=match_dist, nx=nx)

        # compute current moving fraction among tracks longer than min_length (terminated or alive)
        drifts_now: List[float] = []
        for tr in tracks:
            L = (tr.last_t - tr.t0 + 1)
            if L >= min_length:
                drifts_now.append(float(tr.cum_dx) / float(L))
        if drifts_now:
            moving_frac_ts.append(float(sum(1 for v in drifts_now if abs(v) * float(min_length) >= move_min) ) / float(len(drifts_now)))
        else:
            moving_frac_ts.append(0.0)

        prog.maybe(f"t={t}/{steps} comps={len(comps)} moving_frac~{moving_frac_ts[-1]:.3f}")
        if t == steps:
            break

        # dynamics step
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
                # centered mod gradient (left - right) in [-0.5, 0.5] approximately
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

            # directional drive: advect r along +x (wrap)
            if u_adv[i] < advect_p:
                x_i, y_i, z_i = idx_to_xyz(i, nx=nx, ny=ny)
                src_x = (x_i - int(advect_dir)) % nx
                src = xyz_to_idx(src_x, y_i, z_i, nx=nx, ny=ny)
                # mix in advected neighbor (prevents quick homogenization)
                r_new = (int(r_new) + int(r[src])) % qmod

            x_next[i] = x_new
            r_next[i] = r_new

        x, r = x_next, r_next

    # finalize drifts for tracks with sufficient length
    drifts: List[float] = []
    for tr in tracks:
        L = (tr.last_t - tr.t0 + 1)
        if L >= min_length:
            drifts.append(float(tr.cum_dx) / float(L))

    moving = [v for v in drifts if abs(v) * float(min_length) >= move_min]
    summary = {
        "n_tracks": float(len(drifts)),
        "moving_frac": float(len(moving)) / float(max(1, len(drifts))),
        "drift_mean": float(np.mean(moving)) if moving else 0.0,
        "drift_max": float(np.max(np.abs(moving))) if moving else 0.0,
    }

    plt.figure(figsize=(7.0, 4.0))
    plt.hist(drifts, bins=40, color="#ff7f0e", alpha=0.9)
    plt.title("Drift velocity histogram (Δx / lifetime)")
    plt.xlabel("drift velocity")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(out_hist, dpi=160)
    plt.close()

    plt.figure(figsize=(7.0, 4.0))
    plt.plot(moving_frac_ts, color="#2ca02c", linewidth=2.0)
    plt.title("Moving fraction vs time")
    plt.xlabel("t")
    plt.ylabel("fraction")
    plt.tight_layout()
    plt.savefig(out_frac, dpi=160)
    plt.close()

    payload = {"params": params, "summary": summary}
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_transport_tex(summary=summary, out_path=out_tex)

    manifest = build_base_manifest("emergence_transport", run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, ["summary.json", "drift_hist.png", "moving_fraction.png"])
    write_manifest(run.run_dir, manifest)

    ed = export_dir()
    ed.mkdir(parents=True, exist_ok=True)
    copy_atomic(out_hist, ed / "emergence_transport_drift_hist.png")
    copy_atomic(out_frac, ed / "emergence_transport_moving_fraction.png")

    prog.done(f"wrote {out_json}, plots, and {out_tex}")


if __name__ == "__main__":
    main()

