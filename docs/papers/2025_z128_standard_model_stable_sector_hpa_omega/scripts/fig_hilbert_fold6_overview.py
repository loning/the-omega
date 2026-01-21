# -*- coding: utf-8 -*-
"""
Figure: End-to-end overview linking
  (i) Hilbert path on the 8×8 screen (n=3),
  (ii) coloring each site by its Fold_6 stable label w,
  (iii) grouping into the 21 stable types (18+3) as small multiples.

Output:
  - figures/hilbert_fold6_overview.png
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.gridspec import GridSpec  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402

import exp_fold6_stats as fold  # noqa: E402
import exp_hilbert_chirality_index as hil  # noqa: E402
from common_paths import figures_dir  # noqa: E402


Coord = Tuple[int, int]


def _material_palette_21() -> List[str]:
    # Deterministic set of distinct Material-ish colors (hex).
    return [
        "#1565C0",
        "#2E7D32",
        "#C62828",
        "#6A1B9A",
        "#EF6C00",
        "#00897B",
        "#283593",
        "#4E342E",
        "#00838F",
        "#AD1457",
        "#F9A825",
        "#9E9D24",
        "#4527A0",
        "#0277BD",
        "#558B2F",
        "#D84315",
        "#37474F",
        "#6D4C41",
        "#00796B",
        "#7B1FA2",
        "#1B5E20",
    ]


def _is_boundary_word(w: str) -> bool:
    return len(w) == 6 and w[0] == "1" and w[-1] == "1"


def main() -> None:
    out_dir: Path = figures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    n_bits = 3
    L = 1 << n_bits  # 8
    path = hil.hilbert_curve(n_bits)  # list[(x,y)] length 64, in scan order k
    pts = np.array(path, dtype=float)

    # Stable labels w for each scan index k.
    w_of_k = [fold.fold6(k) for k in range(64)]
    X6 = sorted(fold.all_x6(), key=lambda w: (fold.zeckendorf_value_of_word(w), w))
    w_to_idx: Dict[str, int] = {w: i for i, w in enumerate(X6)}
    palette = _material_palette_21()

    # Build per-coordinate label for the 8×8 screen.
    label_at: Dict[Coord, str] = {}
    idx_at: Dict[Coord, int] = {}
    for k, (x, y) in enumerate(path):
        w = w_of_k[k]
        label_at[(int(x), int(y))] = w
        idx_at[(int(x), int(y))] = w_to_idx[w]

    fig = plt.figure(figsize=(16.5, 7.8))
    gs = GridSpec(nrows=1, ncols=3, width_ratios=[1.05, 1.05, 1.35], wspace=0.18, figure=fig)

    axA = fig.add_subplot(gs[0, 0])
    axB = fig.add_subplot(gs[0, 1])

    # Right: a 3×7 grid of small multiples.
    gsR = gs[0, 2].subgridspec(3, 7, wspace=0.12, hspace=0.22)
    axesR = [fig.add_subplot(gsR[r, c]) for r in range(3) for c in range(7)]

    # ---------- Panel A: Hilbert path polyline ----------
    segs = np.stack([pts[:-1], pts[1:]], axis=1)  # (63,2,2)
    t = np.linspace(0.0, 1.0, len(segs))
    lc = LineCollection(segs, array=t, cmap="viridis", linewidths=2.2)
    axA.add_collection(lc)
    # Grid
    for i in range(L + 1):
        axA.plot([-0.5, L - 0.5], [i - 0.5, i - 0.5], color="#ECEFF1", lw=1.0, zorder=0)
        axA.plot([i - 0.5, i - 0.5], [-0.5, L - 0.5], color="#ECEFF1", lw=1.0, zorder=0)
    axA.scatter(pts[:, 0], pts[:, 1], s=14, c="#263238", alpha=0.25, zorder=3)
    axA.scatter([pts[0, 0]], [pts[0, 1]], s=70, c="#D84315", edgecolors="white", linewidths=0.8, zorder=5)
    axA.scatter([pts[-1, 0]], [pts[-1, 1]], s=70, c="#1B5E20", edgecolors="white", linewidths=0.8, zorder=5)
    axA.set_aspect("equal")
    axA.set_xlim(-0.6, L - 0.4)
    axA.set_ylim(-0.6, L - 0.4)
    axA.set_xticks([])
    axA.set_yticks([])
    axA.set_title("A. Hilbert scan path (n=3)\npolyline connects k→k+1", fontsize=12, pad=10)

    # ---------- Panel B: 8×8 screen colored by stable type ----------
    # Draw grid
    for i in range(L + 1):
        axB.plot([-0.5, L - 0.5], [i - 0.5, i - 0.5], color="#ECEFF1", lw=1.0, zorder=0)
        axB.plot([i - 0.5, i - 0.5], [-0.5, L - 0.5], color="#ECEFF1", lw=1.0, zorder=0)
    # Hilbert scan-path overlay with order gradient + faint order-colored points.
    t_pts = np.linspace(0.0, 1.0, len(pts))
    axB.add_collection(LineCollection(segs, array=t, cmap="viridis", linewidths=1.25, alpha=0.28, zorder=1))
    axB.scatter(pts[:, 0], pts[:, 1], s=18, c=t_pts, cmap="viridis", alpha=0.14, edgecolors="none", zorder=1.5)
    # Plot each site in the color of its stable label.
    xs = []
    ys = []
    cs = []
    for (x, y), i in idx_at.items():
        xs.append(x)
        ys.append(y)
        cs.append(palette[i])
    axB.scatter(xs, ys, s=70, c=cs, edgecolors="#263238", linewidths=0.35, alpha=0.95, zorder=3)
    axB.set_aspect("equal")
    axB.set_xlim(-0.6, L - 0.4)
    axB.set_ylim(-0.6, L - 0.4)
    axB.set_xticks([])
    axB.set_yticks([])
    axB.set_title("B. Same 8×8 screen, colored by w = Fold₆(k)\n(21 colors = 21 stable types)", fontsize=12, pad=10)

    # ---------- Panel C: 21 small multiples (grouping) ----------
    for ax in axesR:
        for i in range(L + 1):
            ax.plot([-0.5, L - 0.5], [i - 0.5, i - 0.5], color="#F5F5F5", lw=0.8, zorder=0)
            ax.plot([i - 0.5, i - 0.5], [-0.5, L - 0.5], color="#F5F5F5", lw=0.8, zorder=0)
        # Hilbert scan-path overlay in each small panel (order gradient).
        ax.add_collection(LineCollection(segs, array=t, cmap="viridis", linewidths=0.85, alpha=0.20, zorder=1))
        ax.scatter(pts[:, 0], pts[:, 1], s=6, c=t_pts, cmap="viridis", alpha=0.10, edgecolors="none", zorder=1.5)
        ax.set_aspect("equal")
        ax.set_xlim(-0.6, L - 0.4)
        ax.set_ylim(-0.6, L - 0.4)
        ax.set_xticks([])
        ax.set_yticks([])

    for i, w in enumerate(X6):
        ax = axesR[i]
        # Highlight only sites whose label is w.
        mask_x = []
        mask_y = []
        for (x, y), ww in label_at.items():
            if ww == w:
                mask_x.append(x)
                mask_y.append(y)
        ax.scatter(mask_x, mask_y, s=55, c=palette[i], edgecolors="#263238", linewidths=0.35, alpha=0.98, zorder=3)
        tag = "bdry" if _is_boundary_word(w) else "cyc"
        ax.set_title(f"{w} ({tag})", fontsize=8, pad=1)

    # Hide unused axes (none, should be exactly 21).
    for j in range(len(X6), len(axesR)):
        axesR[j].axis("off")

    # Add a title for Panel C
    axesR[0].text(
        -0.2,
        1.15,
        "C. Group the same colored sites into 21 panels\n(one panel per stable type w)",
        transform=axesR[0].transAxes,
        fontsize=12,
        ha="left",
        va="bottom",
        color="#263238",
    )

    # ---------- Flow arrows between panels ----------
    def _arrow_between(ax_from, ax_to, text: str) -> None:
        p0 = ax_from.transAxes.transform((1.02, 0.50))
        p1 = ax_to.transAxes.transform((-0.02, 0.50))
        inv = fig.transFigure.inverted()
        fp0 = inv.transform(p0)
        fp1 = inv.transform(p1)
        arr = FancyArrowPatch(
            fp0,
            fp1,
            transform=fig.transFigure,
            arrowstyle="-|>",
            mutation_scale=16,
            lw=2.0,
            color="#546E7A",
        )
        fig.patches.append(arr)
        fig.text((fp0[0] + fp1[0]) / 2, fp0[1] + 0.03, text, ha="center", va="bottom", fontsize=11, color="#546E7A")

    _arrow_between(axA, axB, "place k on screen via H₃(k)")
    _arrow_between(axB, axesR[3], "compute w=Fold₆(k)\nthen group by w")

    fig.suptitle("How the Hilbert 8×8 screen relates to the 21 stable types (m=6, n=3)", fontsize=14, y=0.995)

    out_png = out_dir / "hilbert_fold6_overview.png"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")


if __name__ == "__main__":
    main()

