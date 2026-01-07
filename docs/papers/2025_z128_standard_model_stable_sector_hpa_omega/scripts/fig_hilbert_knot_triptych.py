# -*- coding: utf-8 -*-
"""
Generate a conceptual triptych for Figure 1: Vacuum / Matter (cyclic) / Force (boundary).

This figure is narrative-facing: it visualizes the "scan-to-knot" intuition without
changing any theorem-level content (which is anchored on a 2D Hilbert screen for
finite diagnostics elsewhere in the paper).

Outputs:
  - figures/hilbert_knot_triptych.png
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Tuple

import numpy as np

# Force a non-interactive backend for deterministic headless rendering.
import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402

from common_paths import figures_dir  # noqa: E402


def _cube_edges(origin: Tuple[float, float, float], size: float) -> Iterable[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    ox, oy, oz = origin
    s = size
    # 8 corners
    pts = [
        (ox, oy, oz),
        (ox + s, oy, oz),
        (ox + s, oy + s, oz),
        (ox, oy + s, oz),
        (ox, oy, oz + s),
        (ox + s, oy, oz + s),
        (ox + s, oy + s, oz + s),
        (ox, oy + s, oz + s),
    ]
    # 12 edges by corner indices
    edges = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),
    ]
    for i, j in edges:
        x = np.array([pts[i][0], pts[j][0]])
        y = np.array([pts[i][1], pts[j][1]])
        z = np.array([pts[i][2], pts[j][2]])
        yield x, y, z


def _draw_cube(ax, origin: Tuple[float, float, float], size: float, color: str = "0.7", lw: float = 0.8) -> None:
    for x, y, z in _cube_edges(origin, size):
        ax.plot(x, y, z, color=color, linewidth=lw, zorder=0)


def _set_equal_3d(ax) -> None:
    # Matplotlib 3D equal aspect workaround.
    xs = np.array(ax.get_xlim3d())
    ys = np.array(ax.get_ylim3d())
    zs = np.array(ax.get_zlim3d())
    xmid = float(xs.mean())
    ymid = float(ys.mean())
    zmid = float(zs.mean())
    r = float(max(np.ptp(xs), np.ptp(ys), np.ptp(zs)) / 2.0)
    ax.set_xlim3d(xmid - r, xmid + r)
    ax.set_ylim3d(ymid - r, ymid + r)
    ax.set_zlim3d(zmid - r, zmid + r)


def _vacuum_curve(n: int = 400) -> np.ndarray:
    # Smooth non-closed scan segment through a voxel.
    t = np.linspace(0.0, 1.0, n)
    x = t
    y = 0.5 + 0.18 * np.sin(2.0 * math.pi * t)
    z = 0.5 + 0.18 * np.cos(2.0 * math.pi * t)
    return np.stack([x, y, z], axis=1)


def _trefoil_knot(n: int = 700) -> np.ndarray:
    # A classic smooth knot (trefoil), scaled into a unit voxel.
    t = np.linspace(0.0, 2.0 * math.pi, n)
    x = (2.0 + np.cos(3.0 * t)) * np.cos(2.0 * t)
    y = (2.0 + np.cos(3.0 * t)) * np.sin(2.0 * t)
    z = np.sin(3.0 * t)
    pts = np.stack([x, y, z], axis=1)
    # Normalize to roughly [-1,1] then map to [0.15,0.85] for margin inside the cube.
    pts = pts / float(np.max(np.abs(pts)))
    pts = 0.5 + 0.35 * pts
    return pts


def _bridge_curve(left_center: np.ndarray, right_center: np.ndarray, n: int = 200) -> np.ndarray:
    # A smooth open bridge between two voxel-local centers.
    t = np.linspace(0.0, 1.0, n)
    # Cubic easing for a gentle S-curve.
    s = t * t * (3.0 - 2.0 * t)
    pts = (1.0 - s)[:, None] * left_center[None, :] + s[:, None] * right_center[None, :]
    # Small transverse wiggle to visually separate from cube edges.
    wig = 0.04 * np.sin(2.0 * math.pi * t)
    pts[:, 1] += wig
    pts[:, 2] += 0.03 * np.cos(2.0 * math.pi * t)
    return pts


def _style_ax(ax, title: str) -> None:
    ax.set_title(title, fontsize=10, pad=6)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    ax.set_box_aspect((1, 1, 1))
    ax.grid(False)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_edgecolor("0.9")
        axis.pane.set_facecolor((1.0, 1.0, 1.0, 0.0))


def main() -> None:
    out_dir: Path = figures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(10.5, 3.6))
    axs = [
        fig.add_subplot(1, 3, 1, projection="3d"),
        fig.add_subplot(1, 3, 2, projection="3d"),
        fig.add_subplot(1, 3, 3, projection="3d"),
    ]

    # Panel 1: Vacuum (single voxel, open smooth segment)
    ax = axs[0]
    _draw_cube(ax, origin=(0.0, 0.0, 0.0), size=1.0, color="0.75", lw=0.8)
    vac = _vacuum_curve()
    ax.plot(vac[:, 0], vac[:, 1], vac[:, 2], color="#1565C0", linewidth=2.2)
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_zlim(0.0, 1.0)
    ax.view_init(elev=18, azim=-55)
    _style_ax(ax, "Vacuum: smooth scan (no closure)")
    _set_equal_3d(ax)

    # Panel 2: Matter (single voxel, closed knot)
    ax = axs[1]
    _draw_cube(ax, origin=(0.0, 0.0, 0.0), size=1.0, color="0.75", lw=0.8)
    knot = _trefoil_knot()
    ax.plot(knot[:, 0], knot[:, 1], knot[:, 2], color="#2E7D32", linewidth=2.2)
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_zlim(0.0, 1.0)
    ax.view_init(elev=18, azim=-55)
    _style_ax(ax, "Matter: cyclic knot (localized)")
    _set_equal_3d(ax)

    # Panel 3: Force (two voxels, open bridge between them)
    ax = axs[2]
    gap = 0.20
    left_origin = np.array([0.0, 0.0, 0.0])
    right_origin = np.array([1.0 + gap, 0.0, 0.0])
    _draw_cube(ax, origin=tuple(left_origin), size=1.0, color="0.75", lw=0.8)
    _draw_cube(ax, origin=tuple(right_origin), size=1.0, color="0.75", lw=0.8)

    # Small loops in each voxel (to suggest two localized knots) + an open bridge.
    loop_left = _trefoil_knot(n=520) * 0.55 + np.array([0.15, 0.225, 0.225])
    loop_right = loop_left + np.array([1.0 + gap, 0.0, 0.0])
    ax.plot(loop_left[:, 0], loop_left[:, 1], loop_left[:, 2], color="#6A1B9A", linewidth=1.8, alpha=0.9)
    ax.plot(loop_right[:, 0], loop_right[:, 1], loop_right[:, 2], color="#6A1B9A", linewidth=1.8, alpha=0.9)

    left_c = np.array([0.95, 0.50, 0.50])
    right_c = right_origin + np.array([0.05, 0.50, 0.50])
    bridge = _bridge_curve(left_c, right_c)
    ax.plot(bridge[:, 0], bridge[:, 1], bridge[:, 2], color="#D84315", linewidth=2.4)

    ax.set_xlim(0.0, 2.0 + gap)
    ax.set_ylim(0.0, 1.0)
    ax.set_zlim(0.0, 1.0)
    ax.view_init(elev=18, azim=-55)
    _style_ax(ax, "Force: boundary bridge (connects voxels)")
    _set_equal_3d(ax)

    fig.tight_layout(w_pad=1.2)
    fig.savefig(out_dir / "hilbert_knot_triptych.png", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    main()

