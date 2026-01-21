# -*- coding: utf-8 -*-
"""
Figure: locality-optimal holographic boundary curve via an nD Hilbert scan on the face.

Goal:
  Emphasize the "best locality" curve in a way compatible with the holographic
  boundary-face encoding:
    - all occupied sites lie on a boundary face x0=0,
    - the traversal order is an nD Hilbert curve (unit-step adjacency in L1),
      hence maximal locality (max jump = 1).

Construction for arbitrary (m,n):
  - choose face dimension D_face := ceil(m/n) (capacity 2^{D_face n} >= 2^m),
  - use the D_face-dimensional Hilbert curve of order n as the scan order on the face,
  - take the first 2^m sites along this curve (prefix),
  - embed as bulk boundary by inserting x0=0, so D_bulk = D_face + 1.

This is a visualization / addressing convention designed to maximize locality under
the boundary constraint; it does not replace theorem-level diagnostics based on the
2D Hilbert screen at the anchor.

Output:
  - figures/universal_screen_holo_hilbert_face_gallery.png
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

from common_paths import figures_dir  # noqa: E402
from hilbert_nd import hilbert_index_to_coords  # noqa: E402
from screen_universal_vfs import embedding_dimension, effective_dimension  # noqa: E402


def style_grid(ax, L: int) -> None:
    if L <= 64:
        for i in range(L + 1):
            ax.plot([-0.5, L - 0.5], [i - 0.5, i - 0.5], color="#ECEFF1", lw=0.6, zorder=0)
            ax.plot([i - 0.5, i - 0.5], [-0.5, L - 0.5], color="#ECEFF1", lw=0.6, zorder=0)
    ax.set_aspect("equal")
    ax.set_xlim(-0.6, L - 0.4)
    ax.set_ylim(-0.6, L - 0.4)
    ax.set_xticks([])
    ax.set_yticks([])


def max_l1_jump(coords: np.ndarray) -> int:
    if coords.shape[0] < 2:
        return 0
    dif = np.abs(coords[1:, :] - coords[:-1, :])
    return int(np.max(np.sum(dif, axis=1)))


def main() -> None:
    out_dir: Path = figures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Representative pairs: include D_face=2,3,4 cases.
    pairs: List[Tuple[int, int]] = [
        (6, 3),   # D_face=2
        (7, 3),   # D_face=3
        (10, 3),  # D_face=4
        (11, 3),  # D_face=4
    ]

    nrows = len(pairs)
    fig, axes = plt.subplots(nrows=nrows, ncols=2, figsize=(16.8, 4.4 * nrows))
    if nrows == 1:
        axes = np.array([axes])  # type: ignore

    c_text = "#263238"

    for r, (m, n) in enumerate(pairs):
        axB, axT = axes[r]
        N = 1 << m
        L = 1 << n

        d_eff = effective_dimension(m, n)
        D_face = embedding_dimension(m, n)
        D_bulk = D_face + 1

        # Face Hilbert scan (prefix length 2^m).
        face_coords = np.array([hilbert_index_to_coords(k, p=n, n=D_face) for k in range(N)], dtype=float)  # (N,D_face)
        bulk_coords = np.concatenate([np.zeros((N, 1), dtype=float), face_coords], axis=1)  # x0=0 boundary face

        # ---- B: pairwise 2D projections (to avoid "looks compressed" confusion) ----
        axB.axis("off")
        axB.set_xlim(0, 1)
        axB.set_ylim(0, 1)

        # Use face axes only: bulk x0 is fixed (boundary face); face axes are x1..x_{D_face}.
        d_show = min(D_face, 4)
        if d_show == 1:
            projs = [(1, 1)]
        elif d_show == 2:
            projs = [(1, 2)]
        elif d_show == 3:
            projs = [(1, 2), (1, 3), (2, 3)]
        else:
            projs = [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]

        def _proj(outer_ax, x0, y0, w, h, a, b, title):
            iax = outer_ax.inset_axes([x0, y0, w, h])
            style_grid(iax, L)
            xy = bulk_coords[:, [a, b]]
            segs = np.stack([xy[:-1], xy[1:]], axis=1)
            t_segs = np.linspace(0.0, 1.0, len(segs))
            t_pts = np.linspace(0.0, 1.0, len(xy))
            iax.add_collection(LineCollection(segs, array=t_segs, cmap="viridis", linewidths=1.05, alpha=0.72, zorder=2))
            iax.scatter(xy[:, 0], xy[:, 1], s=10 if L >= 64 else 14, c=t_pts, cmap="viridis", alpha=0.22, edgecolors="none", zorder=1.5)
            # Start/end markers.
            iax.scatter([xy[0, 0]], [xy[0, 1]], s=55, c="#D84315", edgecolors="white", linewidths=0.7, zorder=5)
            iax.scatter([xy[-1, 0]], [xy[-1, 1]], s=55, c="#1B5E20", edgecolors="white", linewidths=0.7, zorder=5)
            iax.set_title(title, fontsize=10, color=c_text, pad=2)
            return xy

        # Layout: 1 panel (D_face=2), 3 panels (D_face=3), 6 panels (D_face>=4).
        if len(projs) == 1:
            (a, b) = projs[0]
            _proj(axB, 0.06, 0.14, 0.88, 0.78, a, b, f"x{a}–x{b}")
            axB.text(
                0.06,
                0.04,
                "B. Exact face view (D_face=2). Unit-step adjacency holds in the shown grid.",
                fontsize=11,
                color=c_text,
            )
        elif len(projs) == 3:
            (a0, b0), (a1, b1), (a2, b2) = projs
            _proj(axB, 0.02, 0.54, 0.31, 0.42, a0, b0, f"x{a0}–x{b0}")
            _proj(axB, 0.35, 0.54, 0.31, 0.42, a1, b1, f"x{a1}–x{b1}")
            _proj(axB, 0.68, 0.54, 0.31, 0.42, a2, b2, f"x{a2}–x{b2}")
            axB.text(
                0.02,
                0.48,
                "B. Pairwise 2D projections of the D_face-dim boundary face (not compression).\n"
                "Overlaps in one projection can occur when D_face>2 (hidden coordinates).",
                fontsize=11,
                color=c_text,
            )
        else:
            (a0, b0), (a1, b1), (a2, b2), (a3, b3), (a4, b4), (a5, b5) = projs
            _proj(axB, 0.02, 0.54, 0.31, 0.40, a0, b0, f"x{a0}–x{b0}")
            _proj(axB, 0.35, 0.54, 0.31, 0.40, a1, b1, f"x{a1}–x{b1}")
            _proj(axB, 0.68, 0.54, 0.31, 0.40, a2, b2, f"x{a2}–x{b2}")
            _proj(axB, 0.02, 0.08, 0.31, 0.40, a3, b3, f"x{a3}–x{b3}")
            _proj(axB, 0.35, 0.08, 0.31, 0.40, a4, b4, f"x{a4}–x{b4}")
            _proj(axB, 0.68, 0.08, 0.31, 0.40, a5, b5, f"x{a5}–x{b5}")
            axB.text(
                0.02,
                0.01,
                "B. Pairwise 2D projections among the first 4 face axes (D_face≥4).\n"
                "Each k maps to a unique D_face-dim gridpoint; projection overlaps are expected.",
                fontsize=11,
                color=c_text,
            )

        # ---- Right: explanation and locality stats ----
        axT.axis("off")
        mx_face = max_l1_jump(face_coords)
        mx_bulk = max_l1_jump(bulk_coords)
        # Projection overlap stats on the first shown face projection x1-x2 (when available).
        if D_face >= 2:
            proj12 = bulk_coords[:, [1, 2]]
            unique12 = len({(int(x), int(y)) for x, y in proj12.tolist()})
        else:
            unique12 = N
        avg_mult = float(N) / float(unique12) if unique12 > 0 else float("inf")
        lines: List[str] = []
        lines.append(f"(m,n)=({m},{n})  N=2^{m}={N}")
        lines.append(f"d_eff=m/n={d_eff:.3f}")
        lines.append(f"D_face=ceil(d_eff)={D_face},  D_bulk=D_face+1={D_bulk}")
        lines.append(f"2D projection x1–x2 uses ≤ 2^{2*n} = {L*L} cells; here unique={unique12}, avg multiplicity≈{avg_mult:.2f}")
        lines.append("")
        lines.append("Mapping (locality-optimal under boundary constraint):")
        lines.append("  coord_face(k) := Hilbert_{D_face,n}(k)")
        lines.append("  coord_bulk(k) := (0, coord_face(k))   # boundary face x0=0")
        lines.append("")
        lines.append("Locality (L1 jump along k→k+1):")
        lines.append(f"  max jump on face = {mx_face}   (Hilbert adjacency ⇒ 1)")
        lines.append(f"  max jump in bulk = {mx_bulk}   (x0 fixed ⇒ same)")
        lines.append("")
        lines.append("Important:")
        lines.append("  - No repeats in full coord_face (bijection on the face prefix).")
        lines.append("  - Repeats/overlaps can appear only in 2D projections when D_face>2.")
        axT.text(0.0, 0.98, "\n".join(lines), va="top", ha="left", family="monospace", fontsize=10, color=c_text)

    fig.suptitle("Locality-optimal holographic boundary curve: nD Hilbert scan on the boundary face (x0=0)", fontsize=14, y=0.995)
    out_png = out_dir / "universal_screen_holo_hilbert_face_gallery.png"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")


if __name__ == "__main__":
    main()

