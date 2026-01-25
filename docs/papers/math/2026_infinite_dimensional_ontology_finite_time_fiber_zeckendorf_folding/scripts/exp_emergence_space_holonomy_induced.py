#!/usr/bin/env python3
"""
Induced connection variants for space plaquette holonomy.

We compare three Z_q edge connections during the same dynamics:
  (A) interface-gated connection (similar to exp_emergence_space_holonomy.py)
  (B) bit-difference induced connection (exact 1-form):
        pick active bit b = t mod m
        A_{u->v} = (bit_b(x_v) - bit_b(x_u)) mod q
      This is a discrete gauge field derived from the macro configuration x(t).
      Note: as an exact 1-form it yields (approximately) zero plaquette holonomy.
  (C) directional-bit induced connection (not exact in general):
        for x-edges use bit b
        for y-edges use bit (b+1)
        for z-edges use bit (b+2)

For each time step we compute over all plaquettes:
  - rate Hol!=0 for A, B, C
  - interface-touch rate
  - correlations corr(Hol!=0, touch) for A, B, C over time series

Outputs:
  - artifacts/emergence_space_holonomy_induced/<run_id>/summary.json
  - artifacts/emergence_space_holonomy_induced/<run_id>/holonomy_compare.png
  - sections/generated/emergence_space_holonomy_induced_summary.tex
  - stable exports under sections/generated/assets/

Dynamic resolution variant (per-site m):
  - artifacts/emergence_space_holonomy_induced_dynamic_m/<run_id>/summary.json
  - artifacts/emergence_space_holonomy_induced_dynamic_m/<run_id>/holonomy_compare.png
  - artifacts/emergence_space_holonomy_induced_dynamic_m/<run_id>/error_terms.png
  - sections/generated/emergence_space_holonomy_induced_dynamic_m_summary.tex
  - stable export under sections/generated/assets/emergence_space_holonomy_induced_dynamic_m_compare.png
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
from common_paths import export_dir, generated_assets_dir, generated_dir
from common_progress import Progress
from common_pylatex import NoEscape, booktabs_tabular, write_tex_fragment
from common_zeckendorf import iter_no_adjacent_words, no_adjacent_ones_mask_ok, word_bit


def is_in_Bm(x: int, m: int) -> bool:
    return no_adjacent_ones_mask_ok(x) and (m > 1) and (word_bit(x, 0) == 1 and word_bit(x, m - 1) == 1)


def project_word_to_m(x: int, m: int) -> int:
    if m <= 0:
        return 0
    return int(x) & ((1 << int(m)) - 1)


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


def plaquettes(nx: int, ny: int, nz: int) -> List[List[int]]:
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


def A_iface(u: int, v: int, x: np.ndarray, m_u: int, m_v: int, qmod: int, nx: int, ny: int) -> int:
    bu = is_in_Bm(int(x[u]), int(m_u))
    bv = is_in_Bm(int(x[v]), int(m_v))
    if not (bu or bv):
        return 0
    xu, yu, zu = idx_to_xyz(u, nx=nx, ny=ny)
    xv, yv, zv = idx_to_xyz(v, nx=nx, ny=ny)
    parity = (xu + yu + zu + xv + yv + zv + ((int(m_u) + int(m_v)) % 2)) % 2
    return 1 if parity == 0 else (qmod - 1)


def bit_of_word(w: int, bit_i: int) -> int:
    return (w >> bit_i) & 1


def A_bitdiff(u: int, v: int, x: np.ndarray, active_bit: int, qmod: int) -> int:
    du = bit_of_word(int(x[u]), active_bit)
    dv = bit_of_word(int(x[v]), active_bit)
    return (dv - du) % qmod


def A_dirbit(u: int, v: int, x: np.ndarray, base_bit: int, qmod: int, nx: int, ny: int, m: int) -> int:
    xu, yu, zu = idx_to_xyz(u, nx=nx, ny=ny)
    xv, yv, zv = idx_to_xyz(v, nx=nx, ny=ny)
    if xv != xu:
        bit_i = base_bit % m
    elif yv != yu:
        bit_i = (base_bit + 1) % m
    else:
        bit_i = (base_bit + 2) % m
    du = bit_of_word(int(x[u]), bit_i)
    dv = bit_of_word(int(x[v]), bit_i)
    return (dv - du) % qmod


def corr(a: List[float], b: List[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    aa = np.array(a, dtype=np.float64)
    bb = np.array(b, dtype=np.float64)
    sa = float(aa.std())
    sb = float(bb.std())
    if sa <= 1e-12 or sb <= 1e-12:
        return 0.0
    return float(np.corrcoef(aa, bb)[0, 1])


def write_induced_tex(summary: Dict[str, float], out_path: Path) -> None:
    has_m = "m_mean" in summary
    has_E = "E_total_mean" in summary
    tab = booktabs_tabular(
        col_spec="l r",
        header=[NoEscape("Quantity"), NoEscape("Value")],
        rows=[
            [NoEscape("mean Hol!=0 (iface-A)"), f"{summary['holA_mean']:.4f}"],
            [NoEscape("mean Hol!=0 (bitdiff-A)"), f"{summary['holB_mean']:.4f}"],
            [NoEscape("mean Hol!=0 (dirbit-A)"), f"{summary['holC_mean']:.4f}"],
            [NoEscape("mean touch interface"), f"{summary['touch_mean']:.4f}"],
            [NoEscape("corr(HolA, touch)"), f"{summary['corrA_touch']:.4f}"],
            [NoEscape("corr(HolB, touch)"), f"{summary['corrB_touch']:.4f}"],
            [NoEscape("corr(HolC, touch)"), f"{summary['corrC_touch']:.4f}"],
            *(
                [
                    [NoEscape(r"mean $E_{\mathrm{view}}$"), f"{summary['E_view_mean']:.4f}"],
                    [NoEscape(r"mean $E_{\mathrm{constraint}}$"), f"{summary['E_constraint_mean']:.4f}"],
                    [NoEscape(r"mean $E_{\mathrm{res}}$"), f"{summary['E_res_mean']:.4f}"],
                    [NoEscape(r"mean $E_{\mathrm{total}}$"), f"{summary['E_total_mean']:.4f}"],
                    [NoEscape(r"mean $E_{\mathrm{norm}}$"), f"{summary['E_norm_mean']:.4f}"],
                ]
                if has_E
                else []
            ),
            *(
                [
                    [NoEscape("mean m(v)"), f"{summary['m_mean']:.3f}"],
                    [NoEscape("min m(v)"), str(int(summary["m_min"]))],
                    [NoEscape("max m(v)"), str(int(summary["m_max"]))],
                ]
                if has_m
                else []
            ),
        ],
    )
    write_tex_fragment(out_path, tab, comment="Auto-generated by scripts/exp_emergence_space_holonomy_induced.py")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=10)
    ap.add_argument("--dynamic-m", action="store_true", help="Enable per-site dynamic resolution m(v,t).")
    ap.add_argument("--m-min", type=int, default=6)
    ap.add_argument("--m-max", type=int, default=14)
    ap.add_argument("--delta-m", type=int, default=2)
    ap.add_argument("--tau-up", type=float, default=0.55)
    ap.add_argument("--tau-down", type=float, default=0.35)
    ap.add_argument("--m-update-every", type=int, default=4)
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
    dynamic_m = bool(args.dynamic_m)
    m_min = int(args.m_min)
    m_max = int(args.m_max)
    delta_m = int(args.delta_m)
    tau_up = float(args.tau_up)
    tau_down = float(args.tau_down)
    m_update_every = int(args.m_update_every)
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

    if dynamic_m:
        if m_min < 2:
            raise ValueError("m_min must be >= 2")
        if m_max < m_min:
            raise ValueError("m_max must be >= m_min")
        if delta_m <= 0:
            raise ValueError("delta_m must be positive")
        if m_update_every <= 0:
            raise ValueError("m_update_every must be positive")
        m = m_min

    script_path = Path(__file__).resolve()
    params = {
        "m": m,
        "dynamic_m": dynamic_m,
        "m_min": m_min,
        "m_max": m_max,
        "delta_m": delta_m,
        "tau_up": tau_up,
        "tau_down": tau_down,
        "m_update_every": m_update_every,
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

    experiment_name = "emergence_space_holonomy_induced_dynamic_m" if dynamic_m else "emergence_space_holonomy_induced"
    required_files = ["summary.json", "holonomy_compare.png"] + (["error_terms.png"] if dynamic_m else [])
    run = prepare_run(
        experiment=experiment_name,
        params=params,
        script_path=script_path,
        required_files=required_files,
        force=bool(args.force),
    )

    out_json = run.run_dir / "summary.json"
    out_png = run.run_dir / "holonomy_compare.png"
    out_err_png = run.run_dir / "error_terms.png"
    out_tex = generated_dir() / ("emergence_space_holonomy_induced_dynamic_m_summary.tex" if dynamic_m else "emergence_space_holonomy_induced_summary.tex")

    if run.cached:
        print(f"[{experiment_name}] cached: {run.run_dir}", flush=True)
        return

    prog = Progress(every_seconds=15.0)
    rng = random.Random(seed)

    n = nx * ny * nz
    center = (nz // 2) * (nx * ny) + (ny // 2) * nx + (nx // 2)
    nbrs = [neighbors_3d(i, nx, ny, nz) for i in range(n)]
    loops = plaquettes(nx=nx, ny=ny, nz=nz)

    m_grid = np.array([m for _ in range(n)], dtype=np.int64)
    if dynamic_m:
        m_grid[:] = int(m_min)

    # Initialize x from X_{m_grid[i]} per site (simple random stable generator).
    x = np.zeros(n, dtype=np.int64)
    for i in range(n):
        mi = int(m_grid[i])
        prev1 = 0
        w = 0
        for bit in range(mi):
            if prev1 == 1:
                want1 = 0
            else:
                want1 = 1 if (rng.random() < 0.35) else 0
            if want1 == 1:
                w |= (1 << bit)
                prev1 = 1
            else:
                prev1 = 0
        x[i] = int(w)
    r = np.array([rng.randrange(qmod) for _ in range(n)], dtype=np.int64)
    bit0 = int(m_grid[center]) // 2
    x[center] = propose_set_bit_with_local_repair(int(x[center]), m=int(m_grid[center]), bit_i=bit0, want1=1)
    r[center] = (int(r[center]) + 1) % qmod

    holA: List[float] = []
    holB: List[float] = []
    holC: List[float] = []
    touch: List[float] = []
    E_view_ts: List[float] = []
    E_constraint_ts: List[float] = []
    E_res_ts: List[float] = []
    E_total_ts: List[float] = []
    E_norm_ts: List[float] = []

    for t in range(steps + 1):
        # Optional dynamic resolution update.
        if dynamic_m and (t % m_update_every == 0):
            for i in range(n):
                mi = int(m_grid[i])
                iface = 1.0 if is_in_Bm(int(x[i]), mi) else 0.0
                bit_i_loc = (t % max(2, mi))
                nm = avg_neighbor_bit(x, nbrs[i], bit_i=bit_i_loc)
                e_view = abs(nm - threshold)
                mnr = avg_neighbor_r(r, nbrs[i])
                e_res = abs(float(mnr) - float(int(r[i]))) / float(qmod)
                E_norm = (float(e_view) + float(iface) + float(e_res)) / 3.0
                if E_norm > tau_up and (mi + delta_m) <= m_max:
                    m_grid[i] = mi + delta_m
                elif E_norm < tau_down and (mi - delta_m) >= m_min:
                    mi2 = mi - delta_m
                    m_grid[i] = mi2
                    x[i] = project_word_to_m(int(x[i]), mi2)

        # Dynamic-m error decomposition (computed on current state).
        if dynamic_m:
            e_view_sum = 0.0
            e_con_sum = 0.0
            e_res_sum = 0.0
            for i in range(n):
                mi = int(m_grid[i])
                bit_i_loc = (t % max(2, mi))
                nm = avg_neighbor_bit(x, nbrs[i], bit_i=bit_i_loc)
                e_view = abs(nm - threshold)
                e_con = 1.0 if is_in_Bm(int(x[i]), mi) else 0.0
                mnr = avg_neighbor_r(r, nbrs[i])
                e_res = abs(float(mnr) - float(int(r[i]))) / float(qmod)
                e_view_sum += float(e_view)
                e_con_sum += float(e_con)
                e_res_sum += float(e_res)
            e_view_mean = e_view_sum / float(n)
            e_con_mean = e_con_sum / float(n)
            e_res_mean = e_res_sum / float(n)
            e_total = e_view_mean + e_con_mean + e_res_mean
            e_norm = e_total / 3.0
            E_view_ts.append(float(e_view_mean))
            E_constraint_ts.append(float(e_con_mean))
            E_res_ts.append(float(e_res_mean))
            E_total_ts.append(float(e_total))
            E_norm_ts.append(float(e_norm))

        active_bit = (t % max(2, int(np.max(m_grid))))
        nzA = nzB = 0
        nzC = 0
        touch_cnt = 0
        total = float(len(loops)) if loops else 1.0
        for loop in loops:
            a, b, c, d = loop
            HA = 0
            HA += A_iface(a, b, x=x, m_u=int(m_grid[a]), m_v=int(m_grid[b]), qmod=qmod, nx=nx, ny=ny)
            HA += A_iface(b, c, x=x, m_u=int(m_grid[b]), m_v=int(m_grid[c]), qmod=qmod, nx=nx, ny=ny)
            HA += A_iface(c, d, x=x, m_u=int(m_grid[c]), m_v=int(m_grid[d]), qmod=qmod, nx=nx, ny=ny)
            HA += A_iface(d, a, x=x, m_u=int(m_grid[d]), m_v=int(m_grid[a]), qmod=qmod, nx=nx, ny=ny)
            HA %= qmod
            if HA != 0:
                nzA += 1

            HB = 0
            HB += A_bitdiff(a, b, x=x, active_bit=active_bit % max(2, int(m_grid[a])), qmod=qmod)
            HB += A_bitdiff(b, c, x=x, active_bit=active_bit % max(2, int(m_grid[b])), qmod=qmod)
            HB += A_bitdiff(c, d, x=x, active_bit=active_bit % max(2, int(m_grid[c])), qmod=qmod)
            HB += A_bitdiff(d, a, x=x, active_bit=active_bit % max(2, int(m_grid[d])), qmod=qmod)
            HB %= qmod
            if HB != 0:
                nzB += 1

            HC = 0
            HC += A_dirbit(a, b, x=x, base_bit=active_bit, qmod=qmod, nx=nx, ny=ny, m=int(m_grid[a]))
            HC += A_dirbit(b, c, x=x, base_bit=active_bit, qmod=qmod, nx=nx, ny=ny, m=int(m_grid[b]))
            HC += A_dirbit(c, d, x=x, base_bit=active_bit, qmod=qmod, nx=nx, ny=ny, m=int(m_grid[c]))
            HC += A_dirbit(d, a, x=x, base_bit=active_bit, qmod=qmod, nx=nx, ny=ny, m=int(m_grid[d]))
            HC %= qmod
            if HC != 0:
                nzC += 1

            if (
                is_in_Bm(int(x[a]), int(m_grid[a]))
                or is_in_Bm(int(x[b]), int(m_grid[b]))
                or is_in_Bm(int(x[c]), int(m_grid[c]))
                or is_in_Bm(int(x[d]), int(m_grid[d]))
            ):
                touch_cnt += 1

        holA.append(float(nzA) / total)
        holB.append(float(nzB) / total)
        holC.append(float(nzC) / total)
        touch.append(float(touch_cnt) / total)

        prog.maybe(
            f"t={t}/{steps} holA={holA[-1]:.3f} holB={holB[-1]:.3f} holC={holC[-1]:.3f} touch={touch[-1]:.3f}"
        )
        if t == steps:
            break

        # Update uses per-site active bit.
        u_noise = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_defect = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_bit = np.array([rng.random() for _ in range(n)], dtype=np.float64)
        u_r = np.array([rng.random() for _ in range(n)], dtype=np.float64)

        x_next = x.copy()
        r_next = r.copy()
        for i in range(n):
            mi = int(m_grid[i])
            bit_i = (t % max(2, mi))
            nm = avg_neighbor_bit(x, nbrs[i], bit_i=bit_i)
            bias = beta * (nm - threshold) + coupling * ((float(r[i]) / float(qmod)) - 0.5)
            p1 = logistic(bias)
            want1 = 1 if (u_bit[i] < p1) else 0
            x_new = propose_set_bit_with_local_repair(int(x[i]), m=mi, bit_i=bit_i, want1=want1)

            if u_noise[i] < noise:
                x_new ^= (1 << bit_i)
                if bit_i - 1 >= 0 and (((x_new >> bit_i) & 1) == 1) and (((x_new >> (bit_i - 1)) & 1) == 1):
                    x_new &= ~(1 << (bit_i - 1))
                if bit_i + 1 < m and (((x_new >> bit_i) & 1) == 1) and (((x_new >> (bit_i + 1)) & 1) == 1):
                    x_new &= ~(1 << (bit_i + 1))

            if u_defect[i] < defect_rate:
                x_new = inject_interface_defect(x_new, m=mi)

            inc = 1 if is_in_Bm(x_new, mi) else 0
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

    plt.figure(figsize=(7.0, 4.0))
    plt.plot(holA, label="Hol!=0 (iface-A)", color="#d62728", linewidth=2.0)
    plt.plot(holB, label="Hol!=0 (bitdiff-A)", color="#9467bd", linewidth=2.0)
    plt.plot(holC, label="Hol!=0 (dirbit-A)", color="#ff7f0e", linewidth=2.0)
    plt.plot(touch, label="touch interface", color="#1f77b4", linewidth=2.0)
    plt.title("Holonomy rate comparison vs time")
    plt.xlabel("t")
    plt.ylabel("rate")
    plt.ylim(-0.02, 1.02)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()

    if dynamic_m:
        tsE = np.arange(len(E_norm_ts), dtype=np.int64)
        plt.figure(figsize=(7.0, 4.0))
        plt.plot(tsE, E_norm_ts, label=r"$E_{\mathrm{norm}}$", color="#000000", linewidth=2.2)
        plt.plot(tsE, E_view_ts, label=r"$E_{\mathrm{view}}$", color="#1f77b4", linewidth=2.0)
        plt.plot(tsE, E_constraint_ts, label=r"$E_{\mathrm{constraint}}$", color="#d62728", linewidth=2.0)
        plt.plot(tsE, E_res_ts, label=r"$E_{\mathrm{res}}$", color="#2ca02c", linewidth=2.0)
        plt.plot(tsE, E_total_ts, label=r"$E_{\mathrm{total}}$", color="#9467bd", linewidth=1.8, alpha=0.9)
        plt.title("Dynamic-m error decomposition vs time")
        plt.xlabel("t")
        plt.ylabel("error")
        plt.ylim(-0.02, 1.02)
        plt.legend(ncol=2, fontsize=9)
        plt.tight_layout()
        plt.savefig(out_err_png, dpi=160)
        plt.close()

    summary = {
        "holA_mean": float(np.mean(holA)) if holA else 0.0,
        "holB_mean": float(np.mean(holB)) if holB else 0.0,
        "holC_mean": float(np.mean(holC)) if holC else 0.0,
        "touch_mean": float(np.mean(touch)) if touch else 0.0,
        "corrA_touch": float(corr(holA, touch)),
        "corrB_touch": float(corr(holB, touch)),
        "corrC_touch": float(corr(holC, touch)),
        "m_mean": float(np.mean(m_grid)) if dynamic_m else float(m),
        "m_min": int(np.min(m_grid)) if dynamic_m else int(m),
        "m_max": int(np.max(m_grid)) if dynamic_m else int(m),
    }
    if dynamic_m:
        summary.update(
            {
                "E_view_mean": float(np.mean(E_view_ts)) if E_view_ts else 0.0,
                "E_constraint_mean": float(np.mean(E_constraint_ts)) if E_constraint_ts else 0.0,
                "E_res_mean": float(np.mean(E_res_ts)) if E_res_ts else 0.0,
                "E_total_mean": float(np.mean(E_total_ts)) if E_total_ts else 0.0,
                "E_norm_mean": float(np.mean(E_norm_ts)) if E_norm_ts else 0.0,
                "E_total_max": float(np.max(E_total_ts)) if E_total_ts else 0.0,
                "E_norm_max": float(np.max(E_norm_ts)) if E_norm_ts else 0.0,
            }
        )

    payload = {"params": params, "summary": summary}
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_induced_tex(summary=summary, out_path=out_tex)

    manifest = build_base_manifest("emergence_space_holonomy_induced", run.run_id, params=params, script_path=script_path)
    manifest_outputs = ["summary.json", "holonomy_compare.png"] + (["error_terms.png"] if dynamic_m else [])
    manifest = add_output_hashes(manifest, run.run_dir, manifest_outputs)
    write_manifest(run.run_dir, manifest)

    # stable exports
    ed = export_dir()
    ed.mkdir(parents=True, exist_ok=True)
    ga = generated_assets_dir()
    ga.mkdir(parents=True, exist_ok=True)
    if dynamic_m:
        copy_atomic(out_png, ed / "emergence_space_holonomy_induced_dynamic_m_compare.png")
        copy_atomic(out_png, ga / "emergence_space_holonomy_induced_dynamic_m_compare.png")
        copy_atomic(out_err_png, ed / "emergence_space_holonomy_induced_error_terms_dynamic_m.png")
        copy_atomic(out_err_png, ga / "emergence_space_holonomy_induced_error_terms_dynamic_m.png")
    else:
        copy_atomic(out_png, ed / "emergence_space_holonomy_compare.png")
        copy_atomic(out_png, ga / "emergence_space_holonomy_compare.png")

    prog.done(f"wrote {out_json}, plot, and {out_tex}")


if __name__ == "__main__":
    main()

