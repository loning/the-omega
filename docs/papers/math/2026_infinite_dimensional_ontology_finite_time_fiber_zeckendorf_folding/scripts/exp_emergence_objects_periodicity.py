#!/usr/bin/env python3
"""
Periodicity / quasi-periodicity detection on defect-cluster tracks.

We reuse the same dynamics and tracking protocol as exp_emergence_objects.py,
but for each track we analyze the centroid time series and detect the smallest
period p such that positions repeat within tolerance for at least K cycles.

Outputs:
  - artifacts/emergence_objects_periodicity/<run_id>/summary.json
  - artifacts/emergence_objects_periodicity/<run_id>/period_hist.png
  - artifacts/emergence_objects_periodicity/<run_id>/periodic_fraction.png
  - sections/generated/emergence_objects_periodicity_summary.tex
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


def idx_to_xyz(idx: int, nx: int, ny: int) -> Tuple[int, int, int]:
    z = idx // (nx * ny)
    rem = idx % (nx * ny)
    y = rem // nx
    x = rem % nx
    return x, y, z


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
    times: List[int]
    centroids: List[Tuple[float, float, float]]
    alive: bool = True


def match_tracks(tracks: List[Track], comps: List[Component], t: int, max_match_dist: float) -> None:
    used_tracks: set[int] = set()
    used_comps: set[int] = set()
    pairs: List[Tuple[float, int, int]] = []
    for ci, c in enumerate(comps):
        for ti, tr in enumerate(tracks):
            if not tr.alive:
                continue
            d = l2(c.centroid, tr.centroids[-1])
            if d <= max_match_dist:
                pairs.append((d, ci, ti))
    pairs.sort(key=lambda x: x[0])

    for d, ci, ti in pairs:
        if ci in used_comps or ti in used_tracks:
            continue
        tr = tracks[ti]
        tr.times.append(t)
        tr.centroids.append(comps[ci].centroid)
        used_tracks.add(ti)
        used_comps.add(ci)

    for ti, tr in enumerate(tracks):
        if tr.alive and ti not in used_tracks:
            tr.alive = False

    next_id = (max([tr.tid for tr in tracks], default=-1) + 1)
    for ci, c in enumerate(comps):
        if ci in used_comps:
            continue
        tracks.append(Track(tid=next_id, t0=t, times=[t], centroids=[c.centroid], alive=True))
        next_id += 1


def detect_period(centroids: List[Tuple[float, float, float]], tol: float, min_cycles: int, p_max: int) -> int:
    """
    Return smallest period p>=1 if repeats within tol for >= min_cycles cycles, else 0.
    """
    n = len(centroids)
    if n < (min_cycles + 1):
        return 0
    # test p from 1..p_max
    for p in range(1, min(p_max, n // min_cycles) + 1):
        ok = True
        # check for k cycles: compare c[t] to c[t+p]
        checks = 0
        for t in range(0, n - p):
            if l2(centroids[t], centroids[t + p]) > tol:
                ok = False
                break
            checks += 1
            if checks >= (p * min_cycles):
                break
        if ok and checks >= (p * min_cycles):
            return p
    return 0


def write_periodicity_tex(summary: Dict[str, float], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("% Auto-generated by scripts/exp_emergence_objects_periodicity.py")
    lines.append("\\begin{tabular}{lr}")
    lines.append("\\toprule")
    lines.append("Quantity & Value\\\\")
    lines.append("\\midrule")
    lines.append(f"tracks analyzed & {summary['n_tracks']:.0f}\\\\")
    lines.append(f"periodic fraction & {summary['periodic_frac']:.4f}\\\\")
    lines.append(f"mean detected period & {summary['period_mean']:.3f}\\\\")
    lines.append(f"max detected period & {summary['period_max']:.3f}\\\\")
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
    ap.add_argument("--steps", type=int, default=150)
    ap.add_argument("--threshold", type=float, default=0.50)
    ap.add_argument("--beta", type=float, default=6.0)
    ap.add_argument("--coupling", type=float, default=1.0)
    ap.add_argument("--noise", type=float, default=0.02)
    ap.add_argument("--defect-rate", type=float, default=0.006)
    ap.add_argument("--r-diffusion", type=float, default=0.25)
    ap.add_argument("--match-dist", type=float, default=1.8)
    ap.add_argument("--tol", type=float, default=0.6)
    ap.add_argument("--min-cycles", type=int, default=3)
    ap.add_argument("--p-max", type=int, default=30)
    ap.add_argument("--min-length", type=int, default=20, help="Only analyze tracks with at least this many points.")
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
    tol = float(args.tol)
    min_cycles = int(args.min_cycles)
    p_max = int(args.p_max)
    min_length = int(args.min_length)
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
        "tol": tol,
        "min_cycles": min_cycles,
        "p_max": p_max,
        "min_length": min_length,
        "seed": seed,
    }

    run = prepare_run(
        experiment="emergence_objects_periodicity",
        params=params,
        script_path=script_path,
        required_files=["summary.json", "period_hist.png", "periodic_fraction.png"],
        force=bool(args.force),
    )

    out_json = run.run_dir / "summary.json"
    out_hist = run.run_dir / "period_hist.png"
    out_frac = run.run_dir / "periodic_fraction.png"
    out_tex = generated_dir() / "emergence_objects_periodicity_summary.tex"

    if run.cached:
        print(f"[emergence_objects_periodicity] cached: {run.run_dir}", flush=True)
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
    bit0 = (m // 2)
    x[center] = propose_set_bit_with_local_repair(int(x[center]), m=m, bit_i=bit0, want1=1)
    r[center] = (int(r[center]) + 1) % qmod

    tracks: List[Track] = []
    periodic_rate_ts: List[float] = []
    periods_all: List[int] = []

    for t in range(steps + 1):
        iface = np.array([1.0 if is_in_Bm(int(xx), m) else 0.0 for xx in x], dtype=np.float64)
        comps = components_from_iface(iface, nx=nx, ny=ny, nz=nz)
        match_tracks(tracks, comps, t=t, max_match_dist=match_dist)

        # compute periodic fraction among sufficiently long tracks up to time t
        det_periods: List[int] = []
        for tr in tracks:
            if len(tr.centroids) < min_length:
                continue
            p = detect_period(tr.centroids, tol=tol, min_cycles=min_cycles, p_max=p_max)
            if p > 0:
                det_periods.append(p)
        frac = (float(len(det_periods)) / float(max(1, len([tr for tr in tracks if len(tr.centroids) >= min_length]))))
        periodic_rate_ts.append(frac)
        periods_all.extend(det_periods)

        prog.maybe(f"t={t}/{steps} comps={len(comps)} periodic_frac={frac:.3f}")
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

    # Summaries
    analyzed = [tr for tr in tracks if len(tr.centroids) >= min_length]
    periods = []
    for tr in analyzed:
        p = detect_period(tr.centroids, tol=tol, min_cycles=min_cycles, p_max=p_max)
        if p > 0:
            periods.append(p)

    periodic_frac = float(len(periods)) / float(max(1, len(analyzed)))
    summary = {
        "n_tracks": float(len(analyzed)),
        "periodic_frac": float(periodic_frac),
        "period_mean": float(np.mean(periods)) if periods else 0.0,
        "period_max": float(np.max(periods)) if periods else 0.0,
    }

    # Plots
    plt.figure(figsize=(7.0, 4.0))
    plt.hist(periods, bins=range(1, p_max + 2), color="#1f77b4", alpha=0.9)
    plt.title("Detected period histogram")
    plt.xlabel("period p")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(out_hist, dpi=160)
    plt.close()

    plt.figure(figsize=(7.0, 4.0))
    plt.plot(periodic_rate_ts, color="#2ca02c", linewidth=2.0)
    plt.title("Periodic track fraction vs time")
    plt.xlabel("t")
    plt.ylabel("fraction")
    plt.tight_layout()
    plt.savefig(out_frac, dpi=160)
    plt.close()

    payload = {"params": params, "summary": summary}
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_periodicity_tex(summary=summary, out_path=out_tex)

    manifest = build_base_manifest("emergence_objects_periodicity", run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, ["summary.json", "period_hist.png", "periodic_fraction.png"])
    write_manifest(run.run_dir, manifest)

    ed = export_dir()
    ed.mkdir(parents=True, exist_ok=True)
    copy_atomic(out_hist, ed / "emergence_object_period_hist.png")
    copy_atomic(out_frac, ed / "emergence_object_periodic_fraction.png")

    prog.done(f"wrote {out_json}, plots, and {out_tex}")


if __name__ == "__main__":
    main()

