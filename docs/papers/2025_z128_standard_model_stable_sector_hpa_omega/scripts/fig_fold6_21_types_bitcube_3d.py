# -*- coding: utf-8 -*-
"""
Figure: 21 stable types as 3D voxel shapes (bio-style intuition) at the m=6 anchor.

We provide a *visualization-only* 3D embedding of 6-bit microstates into a 4×4×4 cube:
  - x := (b1 b2)_2 in {0..3}
  - y := (b3 b4)_2 in {0..3}
  - z := (b5 b6)_2 in {0..3}

For each stable label w in X6, we highlight the voxel set corresponding to the
preimage indices k in Fold_6^{-1}(w). This yields 21 small 3D "shapes", one per
stable type, arranged as a 3×7 panel overview.

To resemble protein "folded chain" cartoons, we also draw a thin backbone polyline
through the centers of the highlighted voxels, connecting them in increasing-k order.
This backbone is a visualization convention (not a theorem-level object).

Output:
  - figures/fold6_21_types_bitcube_3d.png
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Line3DCollection  # noqa: E402

import exp_fold6_stats as fold  # noqa: E402
from common_paths import figures_dir  # noqa: E402


def bits6(k: int) -> str:
    return format(int(k), "06b")


def bitcube_coord_from_k(k: int) -> Tuple[int, int, int]:
    b = bits6(k)
    x = int(b[0:2], 2)
    y = int(b[2:4], 2)
    z = int(b[4:6], 2)
    return x, y, z


def is_boundary_word(w: str) -> bool:
    return len(w) == 6 and w[0] == "1" and w[-1] == "1"


def _catmull_rom_spline(points: np.ndarray, samples_per_seg: int = 20) -> np.ndarray:
    """
    Simple Catmull–Rom spline through 3D points.
    - points: (N,3), N>=2
    Returns dense points of shape (M,3).
    For N==2, returns the endpoints (straight segment).
    """
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must have shape (N,3).")
    n = points.shape[0]
    if n <= 2:
        return points.copy()

    # Duplicate endpoints for natural-looking end tangents.
    P = np.vstack([points[0], points, points[-1]])

    out: List[np.ndarray] = []
    for i in range(1, n):
        p0 = P[i - 1]
        p1 = P[i]
        p2 = P[i + 1]
        p3 = P[i + 2]
        for j in range(samples_per_seg):
            t = float(j) / float(samples_per_seg)
            t2 = t * t
            t3 = t2 * t
            # Catmull–Rom basis (uniform, tension=0.5)
            a = 2.0 * p1
            b = -p0 + p2
            c = 2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3
            d = -p0 + 3.0 * p1 - 3.0 * p2 + p3
            out.append(0.5 * (a + b * t + c * t2 + d * t3))
    out.append(points[-1])
    return np.vstack(out)


def main() -> None:
    out_dir: Path = figures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build preimages Fold_6^{-1}(w) over k in 0..63.
    pre = {w: [] for w in fold.all_x6()}
    for k in range(64):
        w = fold.fold6(k)
        pre[w].append(k)

    X6 = sorted(pre.keys(), key=lambda w: (fold.zeckendorf_value_of_word(w), w))
    if len(X6) != 21:
        raise AssertionError(f"Expected 21 stable types at m=6, got {len(X6)}.")

    # Layout: 3×7 panels.
    nrows, ncols = 3, 7
    fig = plt.figure(figsize=(18.0, 7.6))

    # Colors (Material-ish).
    c_cyc = "#1565C0"  # Blue 800
    c_bdry = "#2E7D32"  # Green 800
    c_backbone_core = "#D84315"  # Deep Orange 800 (protein-like cartoon accent)
    c_backbone_tube = "#FFCCBC"  # Deep Orange 100 (soft tube highlight)

    for i, w in enumerate(X6):
        ax = fig.add_subplot(nrows, ncols, i + 1, projection="3d")
        ax.set_facecolor("white")

        vox = np.zeros((4, 4, 4), dtype=bool)
        for k in pre[w]:
            x, y, z = bitcube_coord_from_k(k)
            vox[x, y, z] = True

        # Draw a faint cube grid via voxel edges by plotting all-voxels in transparent white.
        # Then overlay active voxels.
        colors = np.empty(vox.shape, dtype=object)
        fc = c_bdry if is_boundary_word(w) else c_cyc
        colors[vox] = fc

        ax.voxels(vox, facecolors=colors, edgecolor="#263238", linewidth=0.6, alpha=0.92)

        # Backbone: smooth "folded chain" through voxel centers in increasing-k order (visualization-only).
        ks = sorted(pre[w])
        if len(ks) >= 2:
            pts = np.array([bitcube_coord_from_k(k) for k in ks], dtype=float) + 0.5
            smooth = _catmull_rom_spline(pts, samples_per_seg=22)

            # Tube effect with scan-order gradient (increasing k): draw a thick faint tube,
            # then a thinner stronger core. This makes direction visible in each 3D panel.
            segs = np.stack([smooth[:-1], smooth[1:]], axis=1)  # (M-1,2,3)
            tt = np.linspace(0.0, 1.0, len(segs))

            tube = Line3DCollection(segs, array=tt, cmap="viridis", linewidths=4.6, alpha=0.28)
            core = Line3DCollection(segs, array=tt, cmap="viridis", linewidths=2.4, alpha=0.92)
            ax.add_collection3d(tube)
            ax.add_collection3d(core)

            # Small "Cα-like" beads on the backbone (at original voxel centers).
            ax.scatter(
                pts[:, 0],
                pts[:, 1],
                pts[:, 2],
                s=22,
                c=np.linspace(0.0, 1.0, len(pts)),
                cmap="viridis",
                depthshade=False,
                edgecolors="white",
                linewidths=0.4,
                alpha=0.95,
            )

        # Clean axis: no ticks, consistent view.
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 4)
        ax.set_zlim(0, 4)
        ax.view_init(elev=22, azim=-52)

        g = len(pre[w])
        tag = "bdry" if is_boundary_word(w) else "cyc"
        ax.set_title(f"{w} ({tag})  g={g}", fontsize=9, pad=2)

    # Hide any unused axes (none).
    fig.suptitle(
        "m=6 stable types as 3D voxel shapes in a 4×4×4 bit-cube embedding (visualization-only)",
        fontsize=13,
        y=0.98,
    )
    fig.tight_layout(rect=[0.0, 0.0, 1.0, 0.95])

    out_png = out_dir / "fold6_21_types_bitcube_3d.png"
    fig.savefig(out_png, dpi=220)
    plt.close(fig)
    print(f"Wrote {out_png}")


if __name__ == "__main__":
    main()

