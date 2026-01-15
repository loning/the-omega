# -*- coding: utf-8 -*-
"""
Batch figures: adaptive visualization across many (m,n) pairs, multi-page.

User-facing goal:
  Generate *multiple* gallery pages (not a single collage) that cover a broader
  set of (m,n) combinations, in the same "trace" style as universal_screen_vfs_trace_gallery.

We produce two complementary suites for the same (m,n) list:
  - VFS (variable-fanout dyadic refinement) : emphasizes effective dimension / density.
  - Hilbert-face (nD Hilbert scan on minimal face) : emphasizes locality (unit-step).

Each page contains several rows; each row shows:
  (A) 1D index axis highlighting k with Fold_m(k)=w0,
  (B) 2D projections of the chosen screen with gradient path (k→k+1),
  (C) a small traceability table.

Outputs (multi-page, fixed names for reproducibility):
  - figures/adaptive/adaptive_vfs_trace_p01.png, ... pNN.png
  - figures/adaptive/adaptive_hilbert_trace_p01.png, ... pNN.png
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Line3DCollection  # noqa: E402

import exp_foldm_stats as fm  # noqa: E402
import exp_hilbert_chirality_index as hil2  # noqa: E402
from common_paths import figures_dir  # noqa: E402
from hilbert_nd import hilbert_index_to_coords  # noqa: E402
from screen_universal_vfs import bits_per_level, effective_dimension, embedding_dimension, vfs_coord_from_k  # noqa: E402


Pair = Tuple[int, int]


def bits_m(k: int, m: int) -> str:
    return format(int(k), f"0{m}b")


def _make_pairs(max_m: int = 12) -> List[Pair]:
    """
    Deterministic grid of (m,n) pairs (bounded so figures remain readable).
    """
    pairs: List[Pair] = []
    for n in (2, 3, 4, 5, 6):
        candidates = [2 * n - 1, 2 * n, 2 * n + 1, 3 * n, 4 * n]
        for m in candidates:
            if m <= 0 or m > max_m:
                continue
            # Keep only pairs with a nontrivial face dimension (>=2) for readable 2D projections.
            if embedding_dimension(m, n) < 2:
                continue
            pairs.append((m, n))
    # Unique + sorted by (n,m).
    pairs = sorted(set(pairs), key=lambda t: (t[1], t[0]))
    return pairs


def _coords_vfs(m: int, n: int) -> np.ndarray:
    D = embedding_dimension(m, n)
    g = bits_per_level(m, n, D=D)
    N = 1 << m
    coords = np.array([vfs_coord_from_k(k, m, n, D=D, g=g) for k in range(N)], dtype=float)
    return coords


def _coords_hilbert_face(m: int, n: int) -> np.ndarray:
    """
    Prefix of a D_face-dimensional Hilbert scan (order n) of length N=2^m.
    For D_face=2, use the paper's canonical 2D Hilbert implementation for consistency.
    """
    D_face = embedding_dimension(m, n)
    N = 1 << m
    if D_face == 2:
        path2 = hil2.hilbert_curve(n)  # full length 2^{2n}
        if N > len(path2):
            raise AssertionError("Unexpected: prefix longer than 2D Hilbert path.")
        return np.array(path2[:N], dtype=float)  # (N,2)
    return np.array([hilbert_index_to_coords(k, p=n, n=D_face) for k in range(N)], dtype=float)


def _style_grid(ax, L: int) -> None:
    if L <= 64:
        for i in range(L + 1):
            ax.plot([-0.5, L - 0.5], [i - 0.5, i - 0.5], color="#ECEFF1", lw=0.6, zorder=0)
            ax.plot([i - 0.5, i - 0.5], [-0.5, L - 0.5], color="#ECEFF1", lw=0.6, zorder=0)
    ax.set_aspect("equal")
    ax.set_xlim(-0.6, L - 0.4)
    ax.set_ylim(-0.6, L - 0.4)
    ax.set_xticks([])
    ax.set_yticks([])

def _style_3d(ax, L: int, elev: float, azim: float) -> None:
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    ax.set_xlim(-0.6, L - 0.4)
    ax.set_ylim(-0.6, L - 0.4)
    ax.set_zlim(-0.6, L - 0.4)
    ax.view_init(elev=float(elev), azim=float(azim))
    ax.set_box_aspect((1, 1, 1))
    ax.grid(False)
    # Transparent panes for cleaner "cube" feel.
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_edgecolor("0.92")
        axis.pane.set_facecolor((1.0, 1.0, 1.0, 0.0))


def _projection_pairs(D: int) -> List[Tuple[int, int]]:
    d_show = min(D, 4)
    if d_show <= 1:
        return [(0, 0)]
    if d_show == 2:
        return [(0, 1)]
    if d_show == 3:
        return [(0, 1), (0, 2), (1, 2)]
    return [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]


def _render_row(axA, axB, axT, *, m: int, n: int, scheme: str) -> None:
    N = 1 << m
    L = 1 << n
    d_eff = effective_dimension(m, n)
    D = embedding_dimension(m, n)
    slack = int(D * n - m)

    w0 = "0" * m
    ks = [k for k in range(N) if fm.foldm(k, m) == w0]
    if not ks:
        raise AssertionError(f"Empty preimage for w0 at m={m}.")

    if scheme == "vfs":
        coords = _coords_vfs(m, n)
        scheme_name = "vfs-face"
        gi = bits_per_level(m, n, D=D)
        g_str = f"g_i={gi}"
    elif scheme == "hilbert":
        coords = _coords_hilbert_face(m, n)
        scheme_name = "hilbert-face"
        g_str = ""
    else:
        raise ValueError("Unknown scheme.")

    # ---- A: 1D index axis ----
    c_hi = "#D84315"
    c_text = "#263238"
    axA.axis("off")
    axA.set_xlim(0, N - 1)
    axA.set_ylim(0, 1)
    axA.plot([0, N - 1], [0.5, 0.5], color="#90A4AE", lw=2.0)
    axA.scatter(ks, [0.5] * len(ks), s=50, c=c_hi, edgecolors="white", linewidths=0.7, zorder=3)
    for k in ks[:10]:
        axA.text(k, 0.62, str(k), ha="center", va="bottom", fontsize=8.2, color=c_hi)
    if len(ks) > 10:
        axA.text(0.98, 0.62, f"+{len(ks)-10} more", transform=axA.transAxes, ha="right", va="bottom", fontsize=8.5, color=c_hi)
    title = f"({m},{n})  N=2^{m}={N}  D=ceil(m/n)={D}  slack={slack}  d_eff={d_eff:.3f}\n{scheme_name}"
    if g_str:
        title += f"  {g_str}"
    axA.text(0.0, 0.92, title + "\nSelect k with Fold_m(k)=w0", transform=axA.transAxes, ha="left", va="top", fontsize=9.8, color=c_text)

    # ---- B: projections ----
    axB.axis("off")
    axB.set_xlim(0, 1)
    axB.set_ylim(0, 1)

    projs = _projection_pairs(D)

    def _proj(outer_ax, x0, y0, w, h, a, b, lab):
        iax = outer_ax.inset_axes([x0, y0, w, h])
        _style_grid(iax, L)
        xy = coords[:, [a, b]]
        xy_hi = xy[np.array(ks, dtype=int), :]

        segs = np.stack([xy[:-1], xy[1:]], axis=1)
        t_segs = np.linspace(0.0, 1.0, len(segs))
        t_pts = np.linspace(0.0, 1.0, len(xy))

        iax.add_collection(LineCollection(segs, array=t_segs, cmap="viridis", linewidths=0.95, alpha=0.32, zorder=1))
        iax.scatter(xy[:, 0], xy[:, 1], s=6 if L >= 64 else 9, c=t_pts, cmap="viridis", alpha=0.12, edgecolors="none", zorder=1.5)
        iax.scatter(xy[:, 0], xy[:, 1], s=10 if L >= 64 else 12, c="#CFD8DC", alpha=0.14, edgecolors="none", zorder=2)
        iax.scatter(xy_hi[:, 0], xy_hi[:, 1], s=48, c=c_hi, edgecolors="#263238", linewidths=0.35, zorder=3)

        iax.scatter([xy[0, 0]], [xy[0, 1]], s=48, c="#D84315", edgecolors="white", linewidths=0.6, zorder=4)
        iax.scatter([xy[-1, 0]], [xy[-1, 1]], s=48, c="#1B5E20", edgecolors="white", linewidths=0.6, zorder=4)
        iax.set_title(lab, fontsize=9, pad=2)

        # Projection overlap diagnostic for the primary projection (0,1).
        return len({(int(x), int(y)) for x, y in xy.tolist()})

    # Layout rules for 1 / 3 / 6 projections.
    uniq01 = N
    if D == 3:
        # Keep the three 2D projections AND add a 3D reconstruction with three views.
        # Top row: the three pairwise projections.
        (a0, b0), (a1, b1), (a2, b2) = [(0, 1), (0, 2), (1, 2)]
        uniq01 = _proj(axB, 0.02, 0.58, 0.31, 0.36, a0, b0, f"x{a0}–x{b0}")
        _proj(axB, 0.35, 0.58, 0.31, 0.36, a1, b1, f"x{a1}–x{b1}")
        _proj(axB, 0.68, 0.58, 0.31, 0.36, a2, b2, f"x{a2}–x{b2}")

        # Bottom row: 3D reconstruction (same path), viewed from three angles.
        views = [(22, -55), (22, 35), (70, -45)]
        segs3 = np.stack([coords[:-1], coords[1:]], axis=1)  # (N-1,2,3)
        t3 = np.linspace(0.0, 1.0, len(segs3))
        t_pts = np.linspace(0.0, 1.0, len(coords))
        coords_hi = coords[np.array(ks, dtype=int), :]

        def _ax3d(x0, y0, w, h, elev, azim):
            ax3 = axB.inset_axes([x0, y0, w, h], projection="3d")
            _style_3d(ax3, L, elev=elev, azim=azim)
            lc3 = Line3DCollection(segs3, array=t3, cmap="viridis", linewidths=1.2, alpha=0.65)
            ax3.add_collection3d(lc3)
            # Keep the background uncluttered: do not scatter all points (it can look like overlaps).
            # Highlight selected preimage points.
            ax3.scatter(
                coords_hi[:, 0],
                coords_hi[:, 1],
                coords_hi[:, 2],
                s=28,
                c=c_hi,
                depthshade=False,
                edgecolors="#263238",
                linewidths=0.3,
                alpha=0.95,
            )
            # Start / end markers.
            ax3.scatter([coords[0, 0]], [coords[0, 1]], [coords[0, 2]], s=55, c="#D84315", depthshade=False, edgecolors="white", linewidths=0.6)
            ax3.scatter([coords[-1, 0]], [coords[-1, 1]], [coords[-1, 2]], s=55, c="#1B5E20", depthshade=False, edgecolors="white", linewidths=0.6)
            ax3.set_title(f"3D view (el={elev}, az={azim})", fontsize=9, pad=2)

        _ax3d(0.02, 0.10, 0.31, 0.42, elev=views[0][0], azim=views[0][1])
        _ax3d(0.35, 0.10, 0.31, 0.42, elev=views[1][0], azim=views[1][1])
        _ax3d(0.68, 0.10, 0.31, 0.42, elev=views[2][0], azim=views[2][1])

        axB.text(
            0.02,
            0.01,
            "B. D=3: keep 3×2D projections + add 3×3D reconstruction (connect the same k→k+1 segments)",
            fontsize=10.0,
            color=c_text,
        )
    elif D >= 4:
        # Keep 6×2D projections (among first 4 axes) AND add a "3D bundle of 3D objects":
        # interpret dims (x0,x1,x2) as an internal 3D object, while higher dims index a family
        # of such 3D objects (a discrete bundle). The scan polyline k→k+1 then traverses the
        # resulting 3D-object group. Show it from three viewing angles; keep the 2D projections.

        # ---- 2D projections (top): (0,1),(0,2),(0,3) and (1,2),(1,3),(2,3) ----
        p_top = [(0, 1), (0, 2), (0, 3)]
        p_bot = [(1, 2), (1, 3), (2, 3)]
        # Layout (in axB axes coordinates):
        #   - 2D projections occupy the top region
        #   - 3D object-bundle views occupy the bottom region
        y2_top = 0.74
        y2_bot = 0.52
        h2 = 0.20
        uniq01 = _proj(axB, 0.02, y2_top, 0.31, h2, p_top[0][0], p_top[0][1], f"x{p_top[0][0]}–x{p_top[0][1]}")
        _proj(axB, 0.35, y2_top, 0.31, h2, p_top[1][0], p_top[1][1], f"x{p_top[1][0]}–x{p_top[1][1]}")
        _proj(axB, 0.68, y2_top, 0.31, h2, p_top[2][0], p_top[2][1], f"x{p_top[2][0]}–x{p_top[2][1]}")
        _proj(axB, 0.02, y2_bot, 0.31, h2, p_bot[0][0], p_bot[0][1], f"x{p_bot[0][0]}–x{p_bot[0][1]}")
        _proj(axB, 0.35, y2_bot, 0.31, h2, p_bot[1][0], p_bot[1][1], f"x{p_bot[1][0]}–x{p_bot[1][1]}")
        _proj(axB, 0.68, y2_bot, 0.31, h2, p_bot[2][0], p_bot[2][1], f"x{p_bot[2][0]}–x{p_bot[2][1]}")

        # ---- 3D subspace views (bottom): use three different axis triples ----
        views = [(22, -55), (22, 35), (70, -45)]
        t_pts = np.linspace(0.0, 1.0, len(coords))

        # Bundle convention:
        #   - internal 3D object coordinates: (x0,x1,x2)
        #   - bundle index coordinates: (x3,...,x_{D-1})
        # We flatten the bundle index into a single chain coordinate s (row-major in base L),
        # and place each 3D object as a cube shifted along +x by s*(L+gap).
        gap = 0.9  # separation between 3D objects
        if D < 4:
            raise AssertionError("Bundle view requires D>=4.")
        idx = coords[:, 3:].astype(int)  # (N, D-3)
        s = np.zeros((len(coords),), dtype=int)
        base = 1
        for j in range(idx.shape[1]):
            s += idx[:, j] * base
            base *= L

        disp = np.stack([coords[:, 0] + s.astype(float) * float(L + gap), coords[:, 1], coords[:, 2]], axis=1)
        disp_hi = disp[np.array(ks, dtype=int), :]
        segs3 = np.stack([disp[:-1], disp[1:]], axis=1)  # (N-1,2,3)
        t3 = np.linspace(0.0, 1.0, len(segs3))

        # Which 3D objects (s-values) to outline.
        unique_s = sorted(set(int(x) for x in s.tolist()))
        if len(unique_s) <= 80:
            cubes_to_draw = unique_s
        else:
            # Keep a sparse set: endpoints + those touched by highlighted points + every ~8th cube.
            cubes_to_draw = set()
            cubes_to_draw.add(unique_s[0])
            cubes_to_draw.add(unique_s[-1])
            for x in s[np.array(ks, dtype=int)].tolist():
                cubes_to_draw.add(int(x))
            step = max(1, len(unique_s) // 8)
            for x in unique_s[::step]:
                cubes_to_draw.add(int(x))
            cubes_to_draw = sorted(cubes_to_draw)

        def _draw_wire_cube(ax3, s_val: int) -> None:
            # Cube bounds for a single 3D object in display coords.
            x0 = float(s_val) * float(L + gap) - 0.5
            x1 = x0 + float(L)
            y0 = -0.5
            y1 = y0 + float(L)
            z0 = -0.5
            z1 = z0 + float(L)
            c = "#B0BEC5"
            lw = 0.7
            a = 0.35
            # 12 edges
            edges = [
                ((x0, y0, z0), (x1, y0, z0)),
                ((x0, y1, z0), (x1, y1, z0)),
                ((x0, y0, z1), (x1, y0, z1)),
                ((x0, y1, z1), (x1, y1, z1)),
                ((x0, y0, z0), (x0, y1, z0)),
                ((x1, y0, z0), (x1, y1, z0)),
                ((x0, y0, z1), (x0, y1, z1)),
                ((x1, y0, z1), (x1, y1, z1)),
                ((x0, y0, z0), (x0, y0, z1)),
                ((x1, y0, z0), (x1, y0, z1)),
                ((x0, y1, z0), (x0, y1, z1)),
                ((x1, y1, z0), (x1, y1, z1)),
            ]
            for (p, q) in edges:
                ax3.plot([p[0], q[0]], [p[1], q[1]], [p[2], q[2]], color=c, lw=lw, alpha=a, zorder=0)

        def _ax3d_bundle(x0, y0, w, h, elev, azim):
            ax3 = axB.inset_axes([x0, y0, w, h], projection="3d")
            # Set limits: x spans the cube chain; y,z are within a cube.
            xmax = float(max(unique_s) if unique_s else 0) * float(L + gap) + float(L) - 0.5
            ax3.set_xlim(-0.6, xmax + 0.2)
            ax3.set_ylim(-0.6, L - 0.4)
            ax3.set_zlim(-0.6, L - 0.4)
            ax3.view_init(elev=float(elev), azim=float(azim))
            ax3.set_box_aspect((3, 1, 1))
            ax3.set_xticks([])
            ax3.set_yticks([])
            ax3.set_zticks([])
            ax3.grid(False)
            for axis in (ax3.xaxis, ax3.yaxis, ax3.zaxis):
                axis.pane.set_edgecolor("0.92")
                axis.pane.set_facecolor((1.0, 1.0, 1.0, 0.0))

            # Outline a sparse set of cubes for readability.
            for sv in cubes_to_draw:
                _draw_wire_cube(ax3, int(sv))

            lc3 = Line3DCollection(segs3, array=t3, cmap="viridis", linewidths=1.1, alpha=0.72)
            ax3.add_collection3d(lc3)
            # Do not scatter all points: keep the 3D "thread through cubes" readable.
            ax3.scatter(
                disp_hi[:, 0],
                disp_hi[:, 1],
                disp_hi[:, 2],
                s=24,
                c=c_hi,
                depthshade=False,
                edgecolors="#263238",
                linewidths=0.3,
                alpha=0.95,
            )
            ax3.scatter([disp[0, 0]], [disp[0, 1]], [disp[0, 2]], s=50, c="#D84315", depthshade=False, edgecolors="white", linewidths=0.6)
            ax3.scatter([disp[-1, 0]], [disp[-1, 1]], [disp[-1, 2]], s=50, c="#1B5E20", depthshade=False, edgecolors="white", linewidths=0.6)
            ax3.set_title(f"3D view (el={int(elev)}, az={int(azim)})", fontsize=9.2, pad=1)
            return ax3

        y3 = 0.05
        h3 = 0.40
        _ax3d_bundle(0.02, y3, 0.31, h3, elev=views[0][0], azim=views[0][1])
        _ax3d_bundle(0.35, y3, 0.31, h3, elev=views[1][0], azim=views[1][1])
        _ax3d_bundle(0.68, y3, 0.31, h3, elev=views[2][0], azim=views[2][1])

        # Guide lines connecting the 3D subspace panels (visual aid).
        y_line = y3 + h3 + 0.012
        x_mid = [0.02 + 0.31 / 2.0, 0.35 + 0.31 / 2.0, 0.68 + 0.31 / 2.0]
        axB.plot([x_mid[0], x_mid[1]], [y_line, y_line], transform=axB.transAxes, color="#B0BEC5", lw=1.8, alpha=0.85, zorder=0)
        axB.plot([x_mid[1], x_mid[2]], [y_line, y_line], transform=axB.transAxes, color="#B0BEC5", lw=1.8, alpha=0.85, zorder=0)
    elif len(projs) == 1:
        a, b = projs[0]
        uniq01 = _proj(axB, 0.04, 0.12, 0.92, 0.82, a, b, f"x{a}–x{b}")
    elif len(projs) == 3:
        (a0, b0), (a1, b1), (a2, b2) = projs
        uniq01 = _proj(axB, 0.02, 0.54, 0.31, 0.42, a0, b0, f"x{a0}–x{b0}")
        _proj(axB, 0.35, 0.54, 0.31, 0.42, a1, b1, f"x{a1}–x{b1}")
        _proj(axB, 0.68, 0.54, 0.31, 0.42, a2, b2, f"x{a2}–x{b2}")
        axB.text(0.02, 0.48, "B. Pairwise 2D projections (order gradient: k→k+1)", fontsize=10.5, color=c_text)
    else:
        (a0, b0), (a1, b1), (a2, b2), (a3, b3), (a4, b4), (a5, b5) = projs
        uniq01 = _proj(axB, 0.02, 0.54, 0.31, 0.40, a0, b0, f"x{a0}–x{b0}")
        _proj(axB, 0.35, 0.54, 0.31, 0.40, a1, b1, f"x{a1}–x{b1}")
        _proj(axB, 0.68, 0.54, 0.31, 0.40, a2, b2, f"x{a2}–x{b2}")
        _proj(axB, 0.02, 0.08, 0.31, 0.40, a3, b3, f"x{a3}–x{b3}")
        _proj(axB, 0.35, 0.08, 0.31, 0.40, a4, b4, f"x{a4}–x{b4}")
        _proj(axB, 0.68, 0.08, 0.31, 0.40, a5, b5, f"x{a5}–x{b5}")
        axB.text(0.02, 0.01, "B. Pairwise 2D projections among first 4 axes", fontsize=10.5, color=c_text)

    avg_mult = float(N) / float(uniq01) if uniq01 > 0 else float("inf")

    # ---- C: table ----
    axT.axis("off")
    lines: List[str] = []
    lines.append(f"w0 = {w0}")
    lines.append(f"|preimage| = {len(ks)}")
    lines.append(f"scheme = {scheme_name}")
    lines.append(f"D = {D}, n = {n}, slack = {slack}, d_eff = {d_eff:.3f}")
    lines.append(f"x0–x1 projection unique = {uniq01}/{N}, avg multiplicity ≈ {avg_mult:.2f}")
    if D >= 4:
        lines.append("3D bundle view: internal (x0,x1,x2), index dims = (x3,...).")
    elif D == 3:
        lines.append("3D view: full (x0,x1,x2) reconstruction shown from 3 angles.")
    lines.append("")
    lines.append("k    bits_m(k)           coord(x0,...,x_{D-1})")
    lines.append("------------------------------------------------")
    max_rows = 12
    for k in ks[:max_rows]:
        b = bits_m(k, m)
        c = tuple(int(x) for x in coords[int(k), :].tolist())
        lines.append(f"{k:4d}  {b}   {c}")
    if len(ks) > max_rows:
        lines.append("...")
    axT.text(0.0, 0.98, "\n".join(lines), va="top", ha="left", family="monospace", fontsize=9.2, color=c_text)


def _render_pages(pairs: Sequence[Pair], *, scheme: str, out_dir: Path, rows_per_page: int = 5) -> List[Path]:
    out_paths: List[Path] = []
    total = len(pairs)
    pages = (total + rows_per_page - 1) // rows_per_page
    for pi in range(pages):
        chunk = list(pairs[pi * rows_per_page : (pi + 1) * rows_per_page])
        nrows = len(chunk)
        fig, axes = plt.subplots(nrows=nrows, ncols=3, figsize=(17.8, 4.8 * nrows))
        if nrows == 1:
            axes = np.array([axes])  # type: ignore
        for r, (m, n) in enumerate(chunk):
            axA, axB, axT = axes[r]
            _render_row(axA, axB, axT, m=m, n=n, scheme=scheme)
        fig.suptitle(
            f"Adaptive trace gallery across many (m,n) pairs — scheme={scheme}  (page {pi+1}/{pages})",
            fontsize=14,
            y=0.995,
        )
        out_path = out_dir / f"adaptive_{scheme}_trace_p{pi+1:02d}.png"
        fig.savefig(out_path, dpi=220, bbox_inches="tight")
        plt.close(fig)
        out_paths.append(out_path)
        print(f"Wrote {out_path}")
    return out_paths


def main() -> None:
    base: Path = figures_dir()
    out_dir = base / "adaptive"
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs = _make_pairs(max_m=12)
    # Two complementary suites.
    _render_pages(pairs, scheme="vfs", out_dir=out_dir, rows_per_page=5)
    _render_pages(pairs, scheme="hilbert", out_dir=out_dir, rows_per_page=5)


if __name__ == "__main__":
    main()

