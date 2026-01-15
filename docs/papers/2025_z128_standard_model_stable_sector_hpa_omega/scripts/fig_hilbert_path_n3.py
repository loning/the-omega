# -*- coding: utf-8 -*-
"""
Figure: Hilbert curve *path* on the n=3 (8×8) grid.

This explicitly draws the polyline that visits the 64 grid points in Hilbert order.
In the paper, H_n is used as a locality-preserving addressing bijection; at finite n,
the "Hilbert curve" is represented by this discrete path (a sequence of unit steps).

Output:
  - figures/hilbert_path_n3.png
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

import exp_hilbert_chirality_index as hil  # noqa: E402
from common_paths import figures_dir  # noqa: E402


def main() -> None:
    out_dir: Path = figures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    n_bits = 3
    L = 1 << n_bits  # 8
    path = hil.hilbert_curve(n_bits)  # list[(x,y)] length 64
    pts = np.array(path, dtype=float)

    # Build line segments between consecutive points.
    segs = np.stack([pts[:-1], pts[1:]], axis=1)  # (63,2,2)
    t = np.linspace(0.0, 1.0, len(segs))
    lc = LineCollection(segs, array=t, cmap="viridis", linewidths=2.6)

    fig, ax = plt.subplots(figsize=(7.2, 7.2))
    ax.add_collection(lc)

    # Draw grid.
    for i in range(L + 1):
        ax.plot([-0.5, L - 0.5], [i - 0.5, i - 0.5], color="#ECEFF1", lw=1.0, zorder=0)
        ax.plot([i - 0.5, i - 0.5], [-0.5, L - 0.5], color="#ECEFF1", lw=1.0, zorder=0)

    # Scatter the visited points lightly.
    t_pts = np.linspace(0.0, 1.0, len(pts))
    ax.scatter(pts[:, 0], pts[:, 1], s=18, c=t_pts, cmap="viridis", alpha=0.30, zorder=3, edgecolors="none")

    # Start/end markers.
    ax.scatter([pts[0, 0]], [pts[0, 1]], s=90, c="#D84315", edgecolors="white", linewidths=0.8, zorder=5)
    ax.text(pts[0, 0] + 0.15, pts[0, 1] + 0.15, "start (k=0)", fontsize=10, color="#D84315")
    ax.scatter([pts[-1, 0]], [pts[-1, 1]], s=90, c="#1B5E20", edgecolors="white", linewidths=0.8, zorder=5)
    ax.text(pts[-1, 0] + 0.15, pts[-1, 1] + 0.15, "end (k=63)", fontsize=10, color="#1B5E20")

    # A few index labels for orientation (every 8 steps).
    for k in range(0, 64, 8):
        x, y = pts[k]
        ax.text(x - 0.25, y - 0.35, f"{k}", fontsize=9, color="#37474F")

    ax.set_aspect("equal")
    ax.set_xlim(-0.6, L - 0.4)
    ax.set_ylim(-0.6, L - 0.4)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Hilbert path on the n=3 (8×8) grid (color = scan index k)", pad=10)

    out_png = out_dir / "hilbert_path_n3.png"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")


if __name__ == "__main__":
    main()

