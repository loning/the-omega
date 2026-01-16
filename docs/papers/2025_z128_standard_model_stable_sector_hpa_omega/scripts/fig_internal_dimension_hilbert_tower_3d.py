# -*- coding: utf-8 -*-
"""
Figure: 3-layer 3D "Hilbert tower" — m=6 (field ocean) -> m=10 (two particles) -> m=14 (zoom hi).

User narrative:
  - Layer 1: a quantum-field "ocean" with multiple particle species + empty state,
    all arranged on a single 3D Hilbert curve (one continuous curve is the spine).
  - Layer 2: pick two particle species and show their internal 3D structures.
  - Layer 3: zoom the higher-energy particle again (deeper microtexture).

Protocol design (audit-facing, deterministic):
  - Layer 1 is the anchor m=6: use a 3D Hilbert curve at order p=2 (cube side 4),
    so 4^3=64=2^6 and the entire microstate set occupies the cube bijectively.
    Particle species are several closed SM fermion labels (here: the 6 generation-1 multiplets)
    and all other labels are rendered as "empty" background to emphasize a mixed field state.
    Spine color uses a protocol-native scalar at m=6: normalized fiber degeneracy
      q6(k) = (g6(u)-2)/2 where u=Fold_6(k) and g6(u)=|Fold_6^{-1}(u)|.
  - Layer 2 is m=10: pick two particle species (hi/lo) by their mean uplift scalar
    q10(k)=|Fold_10(k)[6..9]|_1/4 over k with the same X6 prefix, and display each species'
    internal structure on its own 16^3 internal cube (3D Hilbert, p=4), using the internal order i=0..M-1.
  - Layer 3 is m=14: further zoom the hi species on a larger 32^3 internal cube (3D Hilbert, p=5),
    colored by deeper uplift microtexture q14(k)=|Fold_14(k)[10..13]|_1/4.
  - One continuous Hilbert spine strings all layers; a dashed connector highlights the zoom hotspot.

Outputs:
  - figures/adaptive/lattice_qft_bridge/internal_dimension_hilbert_tower_3d.png
  - figures/adaptive/lattice_qft_bridge/data/internal_dimension_hilbert_tower_3d.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import cm  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from mpl_toolkits.axes_grid1.inset_locator import inset_axes  # noqa: E402
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401,E402
from mpl_toolkits.mplot3d.art3d import Line3DCollection  # noqa: E402

import exp_foldm_stats as foldm  # noqa: E402
import exp_sm_labeling_solver as sm  # noqa: E402
from common_paths import figures_dir  # noqa: E402
from hilbert_nd import hilbert_index_to_coords  # noqa: E402
from protocol_kernel import cached_degeneracy_map  # noqa: E402


Color = str


def _hamming01(s: str) -> int:
    return sum(1 for ch in s if ch == "1")


@dataclass(frozen=True)
class Species:
    key: str          # internal key, e.g. "e_R(1)"
    tex: str          # TeX label (for consistency with paper)
    color: Color


def _material_palette() -> List[Color]:
    # Material-ish, high-contrast on white.
    return [
        "#1E88E5",  # Blue 600
        "#D81B60",  # Pink 600
        "#43A047",  # Green 600
        "#F4511E",  # Deep Orange 600
        "#8E24AA",  # Purple 600
        "#3949AB",  # Indigo 600
        "#00897B",  # Teal 600
        "#FDD835",  # Yellow 600
    ]


def _build_sm_label_map_x6() -> Dict[str, Tuple[str, str, str]]:
    """
    Return mapping u in X6 -> (kind, label_tex, key_plain).
      kind: "fermion" | "gauge"
    """
    X6 = sm.all_x6()
    boundary = [w for w in X6 if sm.is_boundary_word(w)]
    cyclic = [w for w in X6 if not sm.is_boundary_word(w)]
    boundary_sorted = sorted(boundary, key=lambda w: (sm.zeckendorf_value(w), w))
    cyclic_sorted = sorted(cyclic, key=lambda w: sm.stable_type_sort_key(w))

    fields = sorted(sm.fermion_targets(), key=lambda f: f.complexity_key())
    gauge = sm.boundary_gauge_labels()

    out: Dict[str, Tuple[str, str, str]] = {}
    for w, f in zip(cyclic_sorted, fields):
        name_plain = f.name.replace("\\", "")
        out[w] = ("fermion", f.label_tex(), f"{name_plain}({f.generation})")
    for w, (lab_tex, _rep_tex) in zip(boundary_sorted, gauge):
        out[w] = ("gauge", lab_tex, lab_tex.strip("$"))
    if len(out) != 21:
        raise AssertionError("Expected 21 labels in SM X6 map.")
    return out


def _select_generation1_species() -> List[Tuple[str, str]]:
    """
    Deterministically select the 6 generation-1 fermion multiplets by name.
    Returns list of (name_plain, tex).
    """
    # We select by expected SM multiplet names used in the paper.
    want = {"Q_L", "u_R", "d_R", "L_L", "e_R", "nu_R"}
    fields = sorted(sm.fermion_targets(), key=lambda f: f.complexity_key())
    out: List[Tuple[str, str]] = []
    for f in fields:
        name_plain = f.name.replace("\\", "")
        if f.generation == 1 and name_plain in want:
            out.append((f"{name_plain}(1)", f.label_tex()))
    if len(out) != 6:
        # Keep it deterministic and explicit: fail if naming conventions changed.
        raise AssertionError(f"Expected 6 gen-1 species, got {len(out)}: {out}")
    return out


def _segments3(coords: np.ndarray) -> np.ndarray:
    # coords: (N,3) -> segs (N-1,2,3)
    return np.stack([coords[:-1, :], coords[1:, :]], axis=1)


def _segments2(coords: np.ndarray) -> np.ndarray:
    # coords: (N,2) -> segs (N-1,2,2)
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise AssertionError("Expected coords shape (N,2).")
    return np.stack([coords[:-1, :], coords[1:, :]], axis=1)


def _add_cube_wire(ax, origin: Tuple[float, float, float], L: int, color: Color = "#B0BEC5", lw: float = 1.0, alpha: float = 0.6) -> None:
    ox, oy, oz = origin
    x0, x1 = ox, ox + (L - 1)
    y0, y1 = oy, oy + (L - 1)
    z0, z1 = oz, oz + (L - 1)
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
    for a, b in edges:
        ax.plot([a[0], b[0]], [a[1], b[1]], [a[2], b[2]], color=color, lw=lw, alpha=alpha, zorder=0)


def main() -> None:
    out_root: Path = figures_dir() / "adaptive" / "lattice_qft_bridge"
    out_data: Path = out_root / "data"
    out_root.mkdir(parents=True, exist_ok=True)
    out_data.mkdir(parents=True, exist_ok=True)

    # ---- Display parameters ----
    gap_z1 = 8.0
    gap_z2 = 10.0
    # Horizontal separation between the two m=10 internal cubes.
    # Keep it visually distinct but avoid a huge "empty mid-air" gap.
    gap_x2 = 20.0

    # Layer 1: m=6 on a 4^3 cube (p=2).
    p1 = 2
    L1 = 1 << p1  # 4
    m1 = 6
    N1 = 1 << m1  # 64
    coords1 = np.array([hilbert_index_to_coords(k, p=p1, n=3) for k in range(N1)], dtype=float)
    outs6 = foldm.cached_foldm_outputs(m1)
    if len(outs6) != N1:
        raise AssertionError("Unexpected Fold_6 output length.")
    gm6 = cached_degeneracy_map(m1)

    # Layer 2: m=10 on internal 16^3 cubes (p=4).
    p2 = 4
    L2 = 1 << p2  # 16
    m2 = 10
    N2 = 1 << m2  # 1024
    outs10 = foldm.cached_foldm_outputs(m2)
    if len(outs10) != N2:
        raise AssertionError("Unexpected Fold_10 output length.")

    # Layer 3: m=14 on a larger internal 32^3 cube (p=5).
    p3 = 5
    L3 = 1 << p3  # 32
    m3 = 14
    N3 = 1 << m3  # 16384
    outs14 = foldm.cached_foldm_outputs(m3)
    if len(outs14) != N3:
        raise AssertionError("Unexpected Fold_14 output length.")

    x6_map = _build_sm_label_map_x6()
    # Invert: fermion key_plain -> u in X6.
    u_by_key_plain: Dict[str, str] = {}
    for u, (kind, _tex, key_plain) in x6_map.items():
        if kind == "fermion":
            u_by_key_plain[key_plain] = u

    gen1 = _select_generation1_species()
    pal = _material_palette()
    species_list: List[Species] = [Species(key=k, tex=tex, color=pal[i]) for i, (k, tex) in enumerate(gen1)]
    species_by_key = {s.key: s for s in species_list}

    # ----- Layer 1 labels + spine field value (m=6) -----
    label_key1: List[str] = []
    q6 = np.zeros((N1,), dtype=float)
    for k in range(N1):
        u = outs6[k]  # u in X6
        kind, _tex, key_plain = x6_map[u]
        label_key1.append(key_plain if key_plain in species_by_key else "empty")
        g = int(gm6.get(u, 2))
        # At m=6, g in {2,3,4}; normalize to [0,1].
        q6[k] = float(max(2, min(4, g)) - 2) / 2.0

    # ----- Choose hi/lo species by mean uplift scalar at m=10 -----
    def q10_of_k(k: int) -> float:
        w10 = outs10[k]
        return float(_hamming01(w10[6:10])) / 4.0

    means10: Dict[str, float] = {}
    counts10: Dict[str, int] = {}
    ks10_by_species: Dict[str, List[int]] = {}
    for s in species_list:
        u_s = u_by_key_plain.get(s.key)
        if u_s is None:
            raise AssertionError(f"Missing X6 word for species {s.key}.")
        ks = [k for k in range(N2) if outs10[k][:6] == u_s]
        ks10_by_species[s.key] = ks
        counts10[s.key] = len(ks)
        means10[s.key] = float(np.mean([q10_of_k(k) for k in ks])) if ks else 0.0

    hi_key = max(species_list, key=lambda s: (means10[s.key], s.key)).key
    lo_key = min(species_list, key=lambda s: (means10[s.key], s.key)).key
    hi = species_by_key[hi_key]
    lo = species_by_key[lo_key]

    u_hi = u_by_key_plain[hi.key]
    u_lo = u_by_key_plain[lo.key]

    ks_hi10 = ks10_by_species[hi.key]
    ks_lo10 = ks10_by_species[lo.key]
    if not ks_hi10 or not ks_lo10:
        raise AssertionError("Selected species has empty support at m=10 (unexpected).")

    # ----- Layer 2 internal cubes (m=10) -----
    def internal_cube_m10(ks: List[int]) -> Tuple[np.ndarray, np.ndarray, int]:
        M = len(ks)
        coords = np.array([hilbert_index_to_coords(i, p=p2, n=3) for i in range(M)], dtype=float)
        q = np.array([q10_of_k(k) for k in ks], dtype=float)
        return coords, q, M

    coords2_hi, q10_hi, M_hi = internal_cube_m10(ks_hi10)
    coords2_lo, q10_lo, M_lo = internal_cube_m10(ks_lo10)

    # Hotspot for zoom: pick the internal point with maximal q10 in the hi particle.
    i_hot2 = int(np.argmax(q10_hi))
    k_hot = int(ks_hi10[i_hot2])

    # ----- Layer 3 deeper zoom (m=14 for hi) -----
    ks_hi14 = [k for k in range(N3) if outs14[k][:6] == u_hi]
    if not ks_hi14:
        raise AssertionError("Empty m=14 extension set for hi species (unexpected).")
    q14_hi = np.zeros((len(ks_hi14),), dtype=float)
    for i, k in enumerate(ks_hi14):
        w14 = outs14[k]
        q14_hi[i] = float(_hamming01(w14[10:14])) / 4.0
    coords3_hi = np.array([hilbert_index_to_coords(i, p=p3, n=3) for i in range(len(ks_hi14))], dtype=float)

    # Map hotspot microstate k_hot into the m=14 list (same k range).
    try:
        i_hot3 = ks_hi14.index(k_hot)
    except ValueError:
        i_hot3 = 0

    # ---- Assemble tower geometry (single 3D scene) ----
    o1 = (0.0, 0.0, 0.0)
    o2_hi = (0.0, 0.0, float(L1 - 1) + gap_z1)
    o2_lo = (gap_x2, 0.0, float(L1 - 1) + gap_z1)
    # Center the top zoom cube between the two m=10 cubes to reduce horizontal emptiness.
    o3x = 0.5 * float(gap_x2)
    o3 = (o3x, 0.0, float(L1 - 1) + gap_z1 + float(L2 - 1) + gap_z2)

    # Shift coordinates by origins.
    c1 = coords1 + np.array(o1)[None, :]
    c2_hi = coords2_hi + np.array(o2_hi)[None, :]
    c2_lo = coords2_lo + np.array(o2_lo)[None, :]
    c3_hi = coords3_hi + np.array(o3)[None, :]

    # Build a single "spine" polyline: L1(m=6) -> L2_hi(m=10) -> L2_lo(m=10) -> L3_hi(m=14).
    spine = np.concatenate(
        [
            c1,
            np.array([c2_hi[0, :]]),  # connector jump (visual)
            c2_hi,
            np.array([c2_lo[0, :]]),
            c2_lo,
            np.array([c3_hi[0, :]]),
            c3_hi,
        ],
        axis=0,
    )
    spine_vals = np.concatenate(
        [
            q6,
            np.array([q10_hi[0]]),
            q10_hi,
            np.array([q10_lo[0]]),
            q10_lo,
            np.array([q14_hi[0]]),
            q14_hi,
        ]
    )

    wmin, wmax = 0.85, 3.6
    spine_width = wmin + (wmax - wmin) * spine_vals

    # ---- Plot (left: 4x 2D Hilbert blocks aligned to 3D cubes; right: large 3D) ----
    fig = plt.figure(figsize=(26.0, 10.2))
    # Zero gap between left 2D blocks and right 3D panel.
    gs = fig.add_gridspec(1, 2, width_ratios=[4.7, 7.3], wspace=0.0)
    left = gs[0, 0].subgridspec(3, 2, height_ratios=[1.0, 1.0, 0.72], hspace=0.14, wspace=0.12)
    ax2d_L1 = fig.add_subplot(left[0, 0])
    ax2d_L2_hi = fig.add_subplot(left[0, 1])
    ax2d_L2_lo = fig.add_subplot(left[1, 0])
    ax2d_L3_hi = fig.add_subplot(left[1, 1])
    axInfo = fig.add_subplot(left[2, :])

    ax = fig.add_subplot(gs[0, 1], projection="3d")
    ax.set_axis_off()
    for a in (ax2d_L1, ax2d_L2_hi, ax2d_L2_lo, ax2d_L3_hi, axInfo):
        a.set_axis_off()

    norm01 = Normalize(vmin=0.0, vmax=1.0)
    # Tight outer margins (avoid large canvas whitespace).
    fig.subplots_adjust(left=0.01, right=0.985, top=0.95, bottom=0.05, wspace=0.0)

    # Cubes
    _add_cube_wire(ax, o1, L1, color="#B0BEC5", lw=1.1, alpha=0.70)
    _add_cube_wire(ax, o2_hi, L2, color="#B0BEC5", lw=1.1, alpha=0.65)
    _add_cube_wire(ax, o2_lo, L2, color="#B0BEC5", lw=1.1, alpha=0.65)
    _add_cube_wire(ax, o3, L3, color="#B0BEC5", lw=1.1, alpha=0.60)

    # Spine (one continuous curve).
    segs = _segments3(spine)
    lc = Line3DCollection(segs, cmap="viridis", linewidths=spine_width[:-1], alpha=0.98, norm=norm01)
    lc.set_array(spine_vals[:-1])
    lc.set_clim(0.0, 1.0)
    ax.add_collection(lc)

    # Layer 1 particles + empty (m=6).
    empty_idx = [k for k in range(N1) if label_key1[k] not in species_by_key]
    if empty_idx:
        ce = c1[empty_idx, :]
        ax.scatter(ce[:, 0], ce[:, 1], ce[:, 2], s=38, c="#B0BEC5", alpha=0.20, depthshade=False)

    for s in species_list:
        idx = [k for k in range(N1) if label_key1[k] == s.key]
        if not idx:
            continue
        cp = c1[idx, :]
        ax.scatter(cp[:, 0], cp[:, 1], cp[:, 2], s=68, c=s.color, alpha=0.86, depthshade=False)

    # Layer 2 point clouds (internal structures, m=10): hi/lo.
    ax.scatter(c2_hi[:, 0], c2_hi[:, 1], c2_hi[:, 2], s=22, c=hi.color, alpha=0.70, depthshade=False)
    ax.scatter(c2_lo[:, 0], c2_lo[:, 1], c2_lo[:, 2], s=22, c=lo.color, alpha=0.70, depthshade=False)

    # Layer 3 point cloud (deeper hi, m=14).
    ax.scatter(c3_hi[:, 0], c3_hi[:, 1], c3_hi[:, 2], s=10, c=hi.color, alpha=0.25, depthshade=False)

    # Highlight hotspot on layer-2-hi and show a dashed connector to layer 3.
    hot_pt2 = c2_hi[i_hot2, :]
    hot_pt3 = c3_hi[i_hot3, :]
    ax.scatter([hot_pt2[0]], [hot_pt2[1]], [hot_pt2[2]], s=160, c="#D84315", edgecolors="white", linewidths=0.9, depthshade=False)
    ax.scatter([hot_pt3[0]], [hot_pt3[1]], [hot_pt3[2]], s=160, c="#D84315", edgecolors="white", linewidths=0.9, depthshade=False)
    ax.plot([hot_pt2[0], hot_pt3[0]], [hot_pt2[1], hot_pt3[1]], [hot_pt2[2], hot_pt3[2]], color="#455A64", lw=1.6, ls="--", alpha=0.85)

    # View: a stable 3D camera.
    ax.view_init(elev=22, azim=-50)

    # Make the 3D view fill its panel better.
    all_pts = np.concatenate([c1, c2_hi, c2_lo, c3_hi], axis=0)
    xmin, ymin, zmin = np.min(all_pts, axis=0)
    xmax, ymax, zmax = np.max(all_pts, axis=0)
    pad = 0.6
    ax.set_xlim(float(xmin - pad), float(xmax + pad))
    ax.set_ylim(float(ymin - pad), float(ymax + pad))
    ax.set_zlim(float(zmin - pad), float(zmax + pad))
    # Make the 3D axes fill its panel (avoid large internal whitespace).
    ax.set_box_aspect((float(xmax - xmin), float(ymax - ymin), float(zmax - zmin)))
    ax.dist = 7.0  # zoom in (matplotlib 3D camera distance)

    # Colorbar for spine (field value proxy) as an inset,
    # so it does NOT shrink/push the 3D axes and create a big horizontal blank.
    mappable = cm.ScalarMappable(cmap="viridis", norm=norm01)
    mappable.set_array(spine_vals)
    cax = inset_axes(ax, width="2.8%", height="78%", loc="center right", borderpad=1.4)
    cbar = fig.colorbar(mappable, cax=cax)
    cbar.set_label("spine color = field value (layer-dependent uplift proxy)", fontsize=10)

    # -------- Left: 4 blocks, each matches a 3D cube's dataset (same indices, same scalars) --------
    title_box = dict(boxstyle="round,pad=0.28", facecolor="white", edgecolor="#CFD8DC", alpha=0.96)

    def draw_2d_block(
        ax2d,
        coords_xy: np.ndarray,
        values: np.ndarray,
        title: str,
        *,
        highlight_xy: np.ndarray | None = None,
        highlight_color: str | None = None,
        hotspot_xy: np.ndarray | None = None,
    ) -> None:
        segs2 = _segments2(coords_xy)
        lc2 = LineCollection(segs2, cmap="viridis", linewidths=1.6, alpha=0.98, norm=norm01)
        lc2.set_array(values[:-1])
        lc2.set_clim(0.0, 1.0)
        ax2d.add_collection(lc2)
        if highlight_xy is not None and highlight_color is not None and len(highlight_xy) > 0:
            ax2d.scatter(highlight_xy[:, 0], highlight_xy[:, 1], s=26, c=highlight_color, alpha=0.55, edgecolors="none")
        if hotspot_xy is not None:
            ax2d.scatter([hotspot_xy[0]], [hotspot_xy[1]], s=64, c="#D84315", edgecolors="white", linewidths=0.55, alpha=0.98)
        ax2d.set_aspect("equal", adjustable="box")
        xmin, ymin = np.min(coords_xy, axis=0)
        xmax, ymax = np.max(coords_xy, axis=0)
        ax2d.set_xlim(float(xmin - 1.0), float(xmax + 1.0))
        ax2d.set_ylim(float(ymin - 1.0), float(ymax + 1.0))
        ax2d.text(0.02, 0.98, title, transform=ax2d.transAxes, ha="left", va="top", fontsize=12, color="#263238", bbox=title_box)

    # Block 1 (matches 3D Layer-1 cube): m=6 on 8x8 2D Hilbert (order p=3).
    coords_L1_2d = np.array([hilbert_index_to_coords(k, p=3, n=2) for k in range(N1)], dtype=float)
    idx_hi6 = [k for k in range(N1) if label_key1[k] == hi.key]
    idx_lo6 = [k for k in range(N1) if label_key1[k] == lo.key]
    # For L1, overlay both species as small markers (two colors).
    draw_2d_block(ax2d_L1, coords_L1_2d, q6, "2D Hilbert block: L1 (m=6, 8×8)")
    if idx_hi6:
        p_hi = coords_L1_2d[idx_hi6, :]
        ax2d_L1.scatter(p_hi[:, 0], p_hi[:, 1], s=38, c=hi.color, alpha=0.90, edgecolors="white", linewidths=0.30)
    if idx_lo6:
        p_lo = coords_L1_2d[idx_lo6, :]
        ax2d_L1.scatter(p_lo[:, 0], p_lo[:, 1], s=38, c=lo.color, alpha=0.90, edgecolors="white", linewidths=0.30)

    # Block 2 (matches 3D Layer-2A cube): hi internal at m=10, ordered by i=0..M_hi-1 on 8x8.
    coords_L2hi_2d = np.array([hilbert_index_to_coords(i, p=3, n=2) for i in range(M_hi)], dtype=float)
    draw_2d_block(
        ax2d_L2_hi,
        coords_L2hi_2d,
        q10_hi,
        f"2D Hilbert block: L2A (m=10, hi {hi.tex}, 8×8)",
        hotspot_xy=coords_L2hi_2d[i_hot2, :],
    )

    # Block 3 (matches 3D Layer-2B cube): lo internal at m=10, ordered by i=0..M_lo-1 on 8x8.
    coords_L2lo_2d = np.array([hilbert_index_to_coords(i, p=3, n=2) for i in range(M_lo)], dtype=float)
    # hotspot in lo is not used for zoom; do not mark it.
    draw_2d_block(
        ax2d_L2_lo,
        coords_L2lo_2d,
        q10_lo,
        f"2D Hilbert block: L2B (m=10, lo {lo.tex}, 8×8)",
    )

    # Block 4 (matches 3D Layer-3 cube): hi deeper at m=14, ordered by i=0..len(ks_hi14)-1 on 32x32.
    p_L3_2d = 5  # 32x32 capacity = 1024 >= ~913 typical for m=14 hi support
    coords_L3hi_2d = np.array([hilbert_index_to_coords(i, p=p_L3_2d, n=2) for i in range(len(ks_hi14))], dtype=float)
    draw_2d_block(
        ax2d_L3_hi,
        coords_L3hi_2d,
        q14_hi,
        f"2D Hilbert block: L3 (m=14, zoom hi {hi.tex}, 32×32)",
        hotspot_xy=coords_L3hi_2d[i_hot3, :],
    )

    legend_items = [
        Line2D([0], [0], color="#455A64", lw=2.0, label="spine (one continuous Hilbert curve)"),
        Patch(facecolor=hi.color, edgecolor="none", label=f"hi species: {hi.tex}"),
        Patch(facecolor=lo.color, edgecolor="none", label=f"lo species: {lo.tex}"),
        Patch(facecolor="#B0BEC5", edgecolor="none", alpha=0.45, label="empty/other labels"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#D84315", markeredgecolor="white", markersize=9, label="zoom hotspot"),
    ]
    axInfo.legend(
        handles=legend_items,
        loc="lower left",
        frameon=True,
        framealpha=0.96,
        facecolor="white",
        edgecolor="#CFD8DC",
        fontsize=10,
    )
    axInfo.text(
        0.02,
        0.98,
        "Left: 4× 2D Hilbert blocks aligned to the 4 cubes on the right (same index sets and same scalars)\nRight: 3D tower (one continuous spine) + hotspot link",
        transform=axInfo.transAxes,
        ha="left",
        va="top",
        fontsize=11,
        color="#263238",
        bbox=dict(boxstyle="round,pad=0.45", facecolor="white", edgecolor="#CFD8DC", alpha=0.96),
    )

    fig.suptitle("3D Hilbert tower (one spine):  m=6  →  m=10  →  m=14", fontsize=14, y=0.98)
    out_png = out_root / "internal_dimension_hilbert_tower_3d.png"
    fig.savefig(out_png, dpi=320, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")

    payload = {
        "layers": [
            {"name": "L1", "m": m1, "p": p1, "offset": list(o1), "N": int(N1)},
            {"name": "L2_hi", "m": m2, "p": p2, "offset": list(o2_hi), "N": int(M_hi), "species": hi.key},
            {"name": "L2_lo", "m": m2, "p": p2, "offset": list(o2_lo), "N": int(M_lo), "species": lo.key},
            {"name": "L3_hi", "m": m3, "p": p3, "offset": list(o3), "N": int(len(ks_hi14)), "species": hi.key},
        ],
        "species": {
            "shown_gen1": [
                {"key": s.key, "tex": s.tex, "color": s.color, "count_m10": int(counts10[s.key]), "mean_q10": float(means10[s.key])}
                for s in species_list
            ],
            "chosen": {"hi": {"key": hi.key, "tex": hi.tex}, "lo": {"key": lo.key, "tex": lo.tex}},
        },
        "zoom": {"k_hot": int(k_hot), "i_hot2": int(i_hot2), "i_hot3": int(i_hot3)},
        "stats": {
            "layer1_q6_mean": float(np.mean(q6)),
            "layer2_hi_q10_mean": float(np.mean(q10_hi)),
            "layer2_lo_q10_mean": float(np.mean(q10_lo)),
            "layer3_hi_q14_mean": float(np.mean(q14_hi)),
        },
    }
    out_json = out_data / "internal_dimension_hilbert_tower_3d.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()

