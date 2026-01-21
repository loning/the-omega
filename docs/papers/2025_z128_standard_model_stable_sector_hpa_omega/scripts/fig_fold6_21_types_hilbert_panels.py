# -*- coding: utf-8 -*-
"""
Figure: show all 21 stable types at the m=6 anchor (18 cyclic + 3 boundary).

We place the 64 microstate indices k=0..63 on the n=3 (8x8) Hilbert screen using the
canonical Hilbert mapping (same as other scripts), label each site by w=Fold_6(k),
and then create 21 panels. In panel(w), we highlight exactly the sites whose label is w.

Outputs:
  - figures/fold6_21_types_hilbert_panels.png

This is a narrative/audit visualization: it does not add new premises.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# Force a non-interactive backend for deterministic headless rendering.
import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

import exp_fold6_stats as fold  # noqa: E402
import exp_hilbert_chirality_index as hil  # noqa: E402
from common_paths import figures_dir  # noqa: E402


Coord = Tuple[int, int]


def _material_palette_21() -> List[str]:
    # A fixed set of distinct Material-ish colors (hex). Deterministic order.
    return [
        "#1565C0",  # Blue 800
        "#2E7D32",  # Green 800
        "#C62828",  # Red 800
        "#6A1B9A",  # Purple 800
        "#EF6C00",  # Orange 800
        "#00897B",  # Teal 600
        "#283593",  # Indigo 800
        "#4E342E",  # Brown 800
        "#00838F",  # Cyan 800
        "#AD1457",  # Pink 800
        "#F9A825",  # Yellow 800
        "#9E9D24",  # Lime 800
        "#4527A0",  # Deep Purple 800
        "#0277BD",  # Light Blue 800
        "#558B2F",  # Light Green 900
        "#D84315",  # Deep Orange 800
        "#37474F",  # Blue Grey 800
        "#6D4C41",  # Brown 600
        "#00897B",  # Teal 600 (repeat-safe)
        "#7B1FA2",  # Purple 700
        "#1B5E20",  # Green 900
    ]


def _labels_on_hilbert_grid(n_bits: int = 3) -> Dict[Coord, str]:
    # Map each microstate index k to its Hilbert coordinate and label by Fold_6(k).
    path = hil.hilbert_curve(n_bits)
    out: Dict[Coord, str] = {}
    for k, (x, y) in enumerate(path):
        out[(int(x), int(y))] = fold.fold6(k)
    return out


def _grid_mask_for_word(labels: Dict[Coord, str], w: str, n_bits: int = 3) -> np.ndarray:
    L = 1 << n_bits
    m = np.zeros((L, L), dtype=int)
    for (x, y), ww in labels.items():
        if ww == w:
            m[y, x] = 1  # imshow uses (row=y, col=x)
    return m


def _is_boundary_word(w: str) -> bool:
    # pi-channel boundary at m=6: w_1=w_6=1 (equivalently w[0]==w[-1]=="1").
    return len(w) >= 2 and (w[0] == "1" and w[-1] == "1")


def main() -> None:
    n_bits = 3
    out_dir: Path = figures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    labels = _labels_on_hilbert_grid(n_bits=n_bits)
    X6 = fold.all_x6()
    palette = _material_palette_21()
    if len(palette) < len(X6):
        raise AssertionError("Palette must have at least 21 colors.")

    # Hilbert scan path polyline (k -> k+1) for n=3; reused as a faint overlay.
    path = hil.hilbert_curve(n_bits)
    pts = np.array(path, dtype=float)
    segs = np.stack([pts[:-1], pts[1:]], axis=1)  # (63, 2, 2)
    t_segs = np.linspace(0.0, 1.0, len(segs))
    t_pts = np.linspace(0.0, 1.0, len(pts))

    # 21 panels: 3 rows x 7 columns (wide but readable).
    nrows, ncols = 3, 7
    fig_w = 16.8
    fig_h = 7.2
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(fig_w, fig_h), constrained_layout=True)

    # Tight but readable typography.
    title_fs = 8

    for i, w in enumerate(X6):
        r = i // ncols
        c = i % ncols
        ax = axes[r][c]

        mask = _grid_mask_for_word(labels, w, n_bits=n_bits)
        v = fold.zeckendorf_value_of_word(w)
        g = int(mask.sum())
        tag = "bdry" if _is_boundary_word(w) else "cyc"

        # Two-color colormap: background white, highlight color.
        cmap = ListedColormap(["#FFFFFF", palette[i]])
        # Use origin="lower" so the panel orientation matches the other Hilbert-screen plots.
        ax.imshow(mask, cmap=cmap, vmin=0, vmax=1, interpolation="nearest", origin="lower", zorder=0)

        # Hilbert scan-path overlay with order gradient (same in every panel).
        lc = LineCollection(segs, array=t_segs, cmap="viridis", linewidths=1.15, alpha=0.38)
        lc.set_zorder(1)
        ax.add_collection(lc)
        ax.scatter(pts[:, 0], pts[:, 1], s=6, c=t_pts, cmap="viridis", alpha=0.25, edgecolors="none", zorder=2)

        # Draw 8x8 grid lines.
        L = 1 << n_bits
        ax.set_xticks(np.arange(-0.5, L, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, L, 1), minor=True)
        ax.grid(which="minor", color="#E0E0E0", linewidth=0.6)
        ax.tick_params(which="both", bottom=False, left=False, labelbottom=False, labelleft=False)

        ax.set_title(f"{w}  ({tag})  V={v}  g={g}", fontsize=title_fs, pad=2)

    # Hide any unused axes (should be none for 21 panels).
    for j in range(len(X6), nrows * ncols):
        r = j // ncols
        c = j % ncols
        axes[r][c].axis("off")

    fig.suptitle(
        "m=6 stable types on the n=3 Hilbert screen: each panel highlights Fold_6^{-1}(w)",
        fontsize=11,
        y=1.01,
    )

    out_png = out_dir / "fold6_21_types_hilbert_panels.png"
    fig.savefig(out_png, dpi=220)
    plt.close(fig)
    print(f"Wrote {out_png}")


if __name__ == "__main__":
    main()

