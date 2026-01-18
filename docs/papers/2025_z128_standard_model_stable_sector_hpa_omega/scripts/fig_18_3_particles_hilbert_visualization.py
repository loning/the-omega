# -*- coding: utf-8 -*-
"""
Figure: Hilbert curve visualization for all 18+3 particles.

This script generates a comprehensive visualization showing all 18 cyclic types
(fermion multiplets) and 3 boundary types (gauge-factor connection classes) on
the n=3 (8x8) Hilbert screen.

Each particle type is shown in a separate panel, highlighting all grid positions
where that particle type appears according to the closed SM labeling map.

Outputs:
  - figures/18_3_particles_hilbert_visualization.png

This visualization is based on fig_adaptive_multi_mn_trace_suite.py and
fig_fold6_21_types_hilbert_panels.py.
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
import exp_sm_labeling_solver as sml  # noqa: E402
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


def _get_sm_labeling_map() -> Dict[str, str]:
    """
    Get the closed SM labeling map: w -> particle label.
    Returns a dictionary mapping stable type words to their SM labels.
    """
    X6 = sml.all_x6()
    boundary = [w for w in X6 if sml.is_boundary_word(w)]
    cyclic = [w for w in X6 if not sml.is_boundary_word(w)]

    # Sort boundary types by V(w) and assign to gauge factors
    boundary_sorted = sorted(boundary, key=lambda w: (sml.zeckendorf_value(w), w))
    gauge_labels = sml.boundary_gauge_labels()
    gauge_map = {w: label[0] for w, label in zip(boundary_sorted, gauge_labels)}

    # Sort cyclic types and assign to fermion multiplets
    cyclic_sorted = sorted(cyclic, key=lambda w: sml.stable_type_sort_key(w))
    fields = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
    fermion_map = {w: f.label_tex() for w, f in zip(cyclic_sorted, fields)}

    # Merge both maps
    labeling_map: Dict[str, str] = {}
    labeling_map.update(gauge_map)
    labeling_map.update(fermion_map)

    return labeling_map


def _labels_on_hilbert_grid(n_bits: int = 3) -> Dict[Coord, str]:
    """Map each microstate index k to its Hilbert coordinate and label by Fold_6(k)."""
    path = hil.hilbert_curve(n_bits)
    out: Dict[Coord, str] = {}
    for k, (x, y) in enumerate(path):
        out[(int(x), int(y))] = fold.fold6(k)
    return out


def _particle_labels_on_hilbert_grid(n_bits: int = 3) -> Dict[Coord, str]:
    """
    Map each Hilbert coordinate to its particle label (via w -> SM label).
    """
    w_to_coord = _labels_on_hilbert_grid(n_bits)
    labeling_map = _get_sm_labeling_map()
    coord_to_label: Dict[Coord, str] = {}
    for coord, w in w_to_coord.items():
        if w in labeling_map:
            coord_to_label[coord] = labeling_map[w]
    return coord_to_label


def _grid_mask_for_particle(labels: Dict[Coord, str], particle_label: str, n_bits: int = 3) -> np.ndarray:
    """Create a binary mask highlighting grid positions for a specific particle."""
    L = 1 << n_bits
    m = np.zeros((L, L), dtype=int)
    for (x, y), label in labels.items():
        if label == particle_label:
            m[y, x] = 1  # imshow uses (row=y, col=x)
    return m


def _get_all_particle_labels() -> List[str]:
    """Get all 18+3 particle labels in deterministic order."""
    labeling_map = _get_sm_labeling_map()
    # Sort by: boundary first (U(1), SU(2), SU(3)), then cyclic (fermions)
    # For cyclic labels, sort by the same order as fermion_targets (generation, su3_dim, Y^2, su2_dim, name)
    boundary_labels = ["$U(1)$", "$SU(2)$", "$SU(3)$"]
    
    # Get cyclic labels in the same order as fermion_targets
    cyclic_words = sorted(
        [w for w in sml.all_x6() if not sml.is_boundary_word(w)],
        key=lambda w: sml.stable_type_sort_key(w)
    )
    fields = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
    cyclic_labels = [labeling_map[w] for w in cyclic_words]
    
    return boundary_labels + cyclic_labels


def main() -> None:
    n_bits = 3
    out_dir: Path = figures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Get particle labels on Hilbert grid
    particle_labels = _particle_labels_on_hilbert_grid(n_bits=n_bits)
    all_labels = _get_all_particle_labels()
    palette = _material_palette_21()

    if len(all_labels) != 21:
        raise AssertionError(f"Expected 21 particle labels, got {len(all_labels)}")

    # Hilbert scan path polyline (k -> k+1) for n=3; reused as a faint overlay.
    path = hil.hilbert_curve(n_bits)
    pts = np.array(path, dtype=float)
    segs = np.stack([pts[:-1], pts[1:]], axis=1)  # (63, 2, 2)
    t_segs = np.linspace(0.0, 1.0, len(segs))
    t_pts = np.linspace(0.0, 1.0, len(pts))

    # 21 panels: 3 rows x 7 columns (wide but readable).
    nrows, ncols = 3, 7
    fig_w = 18.0
    fig_h = 8.0
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(fig_w, fig_h), constrained_layout=True)

    # Tight but readable typography.
    title_fs = 7.5

    for i, particle_label in enumerate(all_labels):
        r = i // ncols
        c = i % ncols
        ax = axes[r][c]

        mask = _grid_mask_for_particle(particle_labels, particle_label, n_bits=n_bits)
        count = int(mask.sum())

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

        # Determine if this is a boundary (gauge) or cyclic (fermion) particle
        is_gauge = particle_label in ["$U(1)$", "$SU(2)$", "$SU(3)$"]
        tag = "gauge" if is_gauge else "fermion"
        ax.set_title(f"{particle_label}\n({tag})  n={count}", fontsize=title_fs, pad=2)

    # Hide any unused axes (should be none for 21 panels).
    for j in range(len(all_labels), nrows * ncols):
        r = j // ncols
        c = j % ncols
        axes[r][c].axis("off")

    fig.suptitle(
        "All 18+3 particles on the n=3 Hilbert screen: each panel highlights positions for one particle type",
        fontsize=12,
        y=1.01,
    )

    out_png = out_dir / "18_3_particles_hilbert_visualization.png"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")


if __name__ == "__main__":
    main()
