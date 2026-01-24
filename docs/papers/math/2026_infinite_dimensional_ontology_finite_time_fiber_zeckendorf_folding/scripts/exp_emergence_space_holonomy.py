#!/usr/bin/env python3
"""
Space plaquette holonomy experiment during dynamics.

We define a minimal Z_q-valued edge connection A_e(t) on the 3D lattice:
  - for an oriented edge u->v, A=0 if both endpoints are bulk (not in B_m),
    else A=+1 or -1 depending on a simple parity rule (coordinate + bit parity).

Then for each elementary plaquette (square) we compute holonomy:
  Hol = sum_{edges in loop} A_e mod q.
We track over time:
  - fraction of plaquettes with Hol != 0
  - fraction of plaquettes touching at least one interface site
  - conditional Hol != 0 rate given 'touches interface'

Outputs:
  - artifacts/emergence_space_holonomy/<run_id>/summary.json
  - artifacts/emergence_space_holonomy/<run_id>/holonomy_rate.png
  - sections/generated/emergence_space_holonomy_summary.tex
  - stable export under artifacts/export/
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


def edge_A(u: int, v: int, x: np.ndarray, m: int, qmod: int, nx: int, ny: int) -> int:
    """
    Oriented edge u->v Z_q connection value.
    0 if both endpoints are bulk, else +/-1 by parity rule.
    """
    bu = is_in_Bm(int(x[u]), m)
    bv = is_in_Bm(int(x[v]), m)
    if not (bu or bv):
        return 0
    xu, yu, zu = idx_to_xyz(u, nx=nx, ny=ny)
    xv, yv, zv = idx_to_xyz(v, nx=nx, ny=ny)
    parity = (xu + yu + zu + xv + yv + zv + (m % 2)) % 2
    return 1 if parity == 0 else (qmod - 1)


def plaquettes(nx: int, ny: int, nz: int) -> List[List[int]]:
    """
    Return oriented plaquette loops as lists of 4 vertices [a,b,c,d] representing a->b->c->d->a.
    Include xy, xz, yz oriented squares.
    """
    loops: List[List[int]] = []
    for z in range(nz):
        for y in range(ny - 1):
            for x in range(nx - 1):
                a = xyz_to_idx(x, y, z, nx, ny)
                b = xyz_to_idx(x + 1, y, z, nx, ny)
                c = xyz_to_idx(x + 1, y + 1, z, nx, ny)
                d = xyz_to_idx(x, y + 1, z, nx, ny)
                loops.append([a, b, c, d])
    for z in range(nz - 1):
        for y in range(ny):
            for x in range(nx - 1):
                a = xyz_to_idx(x, y, z, nx, ny)
                b = xyz_to_idx(x + 1, y, z, nx, ny)
                c = xyz_to_idx(x + 1, y, z + 1, nx, ny)
                d = xyz_to_idx(x, y, z + 1, nx, ny)
                loops.append([a, b, c, d])
    for z in range(nz - 1):
        for y in range(ny - 1):
            for x in range(nx):
                a = xyz_to_idx(x, y, z, nx, ny)
                b = xyz_to_idx(x, y + 1, z, nx, ny)
                c = xyz_to_idx(x, y + 1, z + 1, nx, ny)
                d = xyz_to_idx(x, y, z + 1, nx, ny)
                loops.append([a, b, c, d])
    return loops


def write_space_holonomy_tex(summary: Dict[str, float], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("% Auto-generated by scripts/exp_emergence_space_holonomy.py")
    lines.append("\\begin{tabular}{lr}")
    lines.append("\\toprule")
    lines.append("Quantity & Value\\\\")
    lines.append("\\midrule")
    lines.append(f"mean holonomy nontrivial rate & {summary['hol_nonzero_mean']:.4f}\\\\")
    lines.append(f"max holonomy nontrivial rate & {summary['hol_nonzero_max']:.4f}\\\\")
    lines.append(f"mean interface-touch rate & {summary['touch_iface_mean']:.4f}\\\\")
    lines.append(f"cond nontrivial given touch & {summary['cond_nonzero_touch_mean']:.4f}\\\\")
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
        "seed": seed,
    }

    run = prepare_run(
        experiment="emergence_space_holonomy",
        params=params,
        script_path=script_path,
        required_files=["summary.json", "holonomy_rate.png"],
        force=bool(args.force),
    )

    out_json = run.run_dir / "summary.json"
    out_png = run.run_dir / "holonomy_rate.png"
    out_tex = generated_dir() / "emergence_space_holonomy_summary.tex"

    if run.cached:
        print(f"[emergence_space_holonomy] cached: {run.run_dir}", flush=True)
        return

    prog = Progress(every_seconds=15.0)
    rng = random.Random(seed)

    Xm = list(iter_no_adjacent_words(m))
    Xm.sort()
    n = nx * ny * nz
    center = (nz // 2) * (nx * ny) + (ny // 2) * nx + (nx // 2)
    nbrs = [neighbors_3d(i, nx, ny, nz) for i in range(n)]
    loops = plaquettes(nx=nx, ny=ny, nz=nz)

    x = np.array([Xm[rng.randrange(len(Xm))] for _ in range(n)], dtype=np.int64)
    r = np.array([rng.randrange(qmod) for _ in range(n)], dtype=np.int64)
    # seed perturbation
    bit0 = (m // 2)
    x[center] = propose_set_bit_with_local_repair(int(x[center]), m=m, bit_i=bit0, want1=1)
    r[center] = (int(r[center]) + 1) % qmod

    hol_nonzero: List[float] = []
    touch_iface: List[float] = []
    cond_nonzero_touch: List[float] = []

    for t in range(steps + 1):
        # compute plaquette holonomy stats
        nz_count = 0
        touch_count = 0
        touch_nz = 0
        for loop in loops:
            a, b, c, d = loop
            H = 0
            H += edge_A(a, b, x=x, m=m, qmod=qmod, nx=nx, ny=ny)
            H += edge_A(b, c, x=x, m=m, qmod=qmod, nx=nx, ny=ny)
            H += edge_A(c, d, x=x, m=m, qmod=qmod, nx=nx, ny=ny)
            H += edge_A(d, a, x=x, m=m, qmod=qmod, nx=nx, ny=ny)
            H %= qmod
            if H != 0:
                nz_count += 1
            touches = is_in_Bm(int(x[a]), m) or is_in_Bm(int(x[b]), m) or is_in_Bm(int(x[c]), m) or is_in_Bm(int(x[d]), m)
            if touches:
                touch_count += 1
                if H != 0:
                    touch_nz += 1

        total = float(len(loops)) if loops else 1.0
        hol_nonzero.append(float(nz_count) / total)
        touch_iface.append(float(touch_count) / total)
        cond = (float(touch_nz) / float(touch_count)) if touch_count > 0 else 0.0
        cond_nonzero_touch.append(float(cond))

        prog.maybe(f"t={t}/{steps} hol_nonzero={hol_nonzero[-1]:.3f} touch={touch_iface[-1]:.3f}")
        if t == steps:
            break

        # dynamics step (same as other emergence scripts)
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
                dlt = mnr - float(int(r[i]))
                step = 1 if dlt > 0.25 else (-1 if dlt < -0.25 else 0)
                r_new = (r_new + step) % qmod

            x_next[i] = x_new
            r_next[i] = r_new
        x, r = x_next, r_next

    # plot
    ts = np.arange(len(hol_nonzero), dtype=np.int64)
    plt.figure(figsize=(7.0, 4.0))
    plt.plot(ts, hol_nonzero, label="P(Hol!=0)", color="#d62728", linewidth=2.0)
    plt.plot(ts, touch_iface, label="P(touch interface)", color="#1f77b4", linewidth=2.0)
    plt.plot(ts, cond_nonzero_touch, label="P(Hol!=0 | touch)", color="#2ca02c", linewidth=2.0)
    plt.title("Space plaquette holonomy vs time")
    plt.xlabel("t")
    plt.ylabel("rate")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()

    summary = {
        "hol_nonzero_mean": float(np.mean(hol_nonzero)) if hol_nonzero else 0.0,
        "hol_nonzero_max": float(np.max(hol_nonzero)) if hol_nonzero else 0.0,
        "touch_iface_mean": float(np.mean(touch_iface)) if touch_iface else 0.0,
        "cond_nonzero_touch_mean": float(np.mean(cond_nonzero_touch)) if cond_nonzero_touch else 0.0,
    }

    payload = {"params": params, "summary": summary}
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_space_holonomy_tex(summary=summary, out_path=out_tex)

    manifest = build_base_manifest("emergence_space_holonomy", run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, ["summary.json", "holonomy_rate.png"])
    write_manifest(run.run_dir, manifest)

    ed = export_dir()
    ed.mkdir(parents=True, exist_ok=True)
    copy_atomic(out_png, ed / "emergence_space_holonomy_rate.png")

    prog.done(f"wrote {out_json}, plot, and {out_tex}")


if __name__ == "__main__":
    main()

