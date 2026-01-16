# -*- coding: utf-8 -*-
"""
Figure: 21 refinement trees (m=6..12), node = (2D Hilbert + 3D Hilbert).

Requirements (user)
-------------------
- Use a tree structure to connect m=6,7,8,9,10,11,12.
- Produce 21 trees (one per base stable type u ∈ X_6).
- Top (m=6) node annotated with: 6-bit code u and particle label (18⊕3 closure at m=6).
- Each node contains both a 2D and a 3D Hilbert-only visualization.
- No external parameters; deterministic outputs under figures/adaptive/.

Deterministic screen choices
----------------------------
For each node at window length m:
  - 2D Hilbert order: n2 = ceil(m/2), screen side L2 = 2^{n2}, path length 4^{n2}.
    Use exp_hilbert_chirality_index.hilbert_curve for consistency with paper conventions.
  - 3D Hilbert order: n3 = ceil(m/3), cube side L3 = 2^{n3}, path length 2^{3 n3}.
    Use hilbert_nd.hilbert_index_to_coords (Skilling-style) for 3D.

Embedding
---------
We use the prefix embedding of length N=2^m along the Hilbert scan, and highlight
sites corresponding to the stable type w under Fold_m(k).

Outputs
-------
Under figures/adaptive/hilbert_tree/:
  - hilbert_tree_m6to12_u_<u>.png   for each u ∈ X_6 (sorted by V(u), then u).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Line3DCollection  # noqa: E402

import exp_foldm_stats as foldm  # noqa: E402
import exp_hilbert_chirality_index as hil2  # noqa: E402
import exp_sm_labeling_solver as sml  # noqa: E402
import exp_xm_enumeration as xm  # noqa: E402
from common_paths import figures_dir  # noqa: E402
from hilbert_nd import hilbert_index_to_coords  # noqa: E402


Coord2 = Tuple[int, int]

M_MIN = 6
M_MAX = 12
OUT_TAG = f"m{M_MIN}to{M_MAX}"


def _ceil_div(a: int, b: int) -> int:
    return int((int(a) + int(b) - 1) // int(b))


def _material_palette_21() -> List[str]:
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
        "#00897B",
        "#7B1FA2",
        "#1B5E20",
    ]


def _get_sm_labeling_map() -> Dict[str, str]:
    X6 = sml.all_x6()
    boundary = [w for w in X6 if sml.is_boundary_word(w)]
    cyclic = [w for w in X6 if not sml.is_boundary_word(w)]

    boundary_sorted = sorted(boundary, key=lambda w: (sml.zeckendorf_value(w), w))
    gauge_labels = sml.boundary_gauge_labels()
    gauge_map = {w: label[0] for w, label in zip(boundary_sorted, gauge_labels)}

    cyclic_sorted = sorted(cyclic, key=lambda w: sml.stable_type_sort_key(w))
    fields = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
    fermion_map = {w: f.label_tex() for w, f in zip(cyclic_sorted, fields)}

    out: Dict[str, str] = {}
    out.update(gauge_map)
    out.update(fermion_map)
    if len(out) != 21:
        raise AssertionError("Expected 21 labels at m=6.")
    return out


def _prefix_grouped_order(words: List[str], parent_len: int) -> List[str]:
    return sorted(words, key=lambda w: (w[:parent_len], w))


def _labels_2d_prefix(*, m_bits: int, n_bits: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """
    Return (grid_pts, segs, t_segs, outs) for 2D, where:
      - grid_pts: (N,2) coords on the 2D screen (prefix of Hilbert path)
      - segs: (N-1,2,2) polyline segments
      - t_segs: (N-1,) color parameter for segments
      - outs: list of Fold_m(k) for k=0..N-1
    """
    N = 1 << int(m_bits)
    path = hil2.hilbert_curve(int(n_bits))
    if N > len(path):
        raise ValueError(f"Need 2^m <= 4^n. Got 2^{m_bits}={N} > 4^{n_bits}={len(path)}.")
    pts = np.array(path[:N], dtype=float)
    segs = np.stack([pts[:-1], pts[1:]], axis=1)
    t_segs = np.linspace(0.0, 1.0, len(segs))
    outs = [foldm.foldm(k, int(m_bits)) for k in range(N)]
    return pts, segs, t_segs, outs


def _coords_3d_prefix(*, m_bits: int, n_bits: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]:
    """
    Return (coords, segs3, t3, outs) for 3D, where:
      - coords: (N,3) integer cube coords
      - segs3: (N-1,2,3) segments
      - t3: (N-1,) color parameter
      - outs: list of Fold_m(k) for k=0..N-1
    """
    N = 1 << int(m_bits)
    cap = 1 << (3 * int(n_bits))
    if N > cap:
        raise ValueError(f"Need 2^m <= 2^{{3n}}. Got 2^{m_bits}={N} > 2^{{3*{n_bits}}}={cap}.")
    coords = np.array([hilbert_index_to_coords(k, p=int(n_bits), n=3) for k in range(N)], dtype=float)
    segs3 = np.stack([coords[:-1], coords[1:]], axis=1)
    t3 = np.linspace(0.0, 1.0, len(segs3))
    outs = [foldm.foldm(k, int(m_bits)) for k in range(N)]
    return coords, segs3, t3, outs


def _mask_grid_from_indices(*, pts_int: np.ndarray, L: int, idxs: List[int]) -> np.ndarray:
    """
    pts_int: (N,2) integer coords, idxs: indices into pts_int.
    """
    m = np.zeros((L, L), dtype=int)
    if len(idxs) == 0:
        return m
    xy = pts_int[np.array(idxs, dtype=int), :]
    for x, y in xy.tolist():
        m[int(y), int(x)] = 1
    return m


def _style_2d(ax, L: int) -> None:
    ax.set_aspect("equal")
    ax.set_xlim(-0.6, L - 0.4)
    ax.set_ylim(-0.6, L - 0.4)
    ax.set_xticks([])
    ax.set_yticks([])
    if L <= 16:
        ax.set_xticks(np.arange(-0.5, L, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, L, 1), minor=True)
        ax.grid(which="minor", color="#E0E0E0", linewidth=0.45)
    else:
        ax.set_xticks(np.arange(-0.5, L, 2), minor=True)
        ax.set_yticks(np.arange(-0.5, L, 2), minor=True)
        ax.grid(which="minor", color="#ECEFF1", linewidth=0.32)


def _style_3d(ax3, L: int) -> None:
    ax3.set_xticks([])
    ax3.set_yticks([])
    ax3.set_zticks([])
    ax3.set_xlim(-0.6, L - 0.4)
    ax3.set_ylim(-0.6, L - 0.4)
    ax3.set_zlim(-0.6, L - 0.4)
    ax3.view_init(elev=22.0, azim=-55.0)
    ax3.set_box_aspect((1, 1, 1))
    ax3.grid(False)
    for axis in (ax3.xaxis, ax3.yaxis, ax3.zaxis):
        axis.pane.set_edgecolor("0.92")
        axis.pane.set_facecolor((1.0, 1.0, 1.0, 0.0))


def _render_node_2d(
    *,
    fig: plt.Figure,
    box: Tuple[float, float, float, float],
    m_bits: int,
    n_bits: int,
    w: str,
    color: str,
    cache: Dict[Tuple[int, int], Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]],
) -> int:
    """
    Render 2D in the left half of node box. Returns g=|preimage|.
    """
    (x, y, w_box, h_box) = box
    ax = fig.add_axes([x, y, w_box, h_box])
    ax.set_facecolor("#FFFFFF")

    key = (m_bits, n_bits)
    if key not in cache:
        cache[key] = _labels_2d_prefix(m_bits=m_bits, n_bits=n_bits)
    pts, segs, t_segs, outs = cache[key]

    N = len(outs)
    idxs = [i for i in range(N) if outs[i] == w]
    L = 1 << int(n_bits)

    pts_int = pts.astype(int)
    mask = _mask_grid_from_indices(pts_int=pts_int, L=L, idxs=idxs)
    cmap = ListedColormap(["#FFFFFF", color])
    ax.imshow(mask, cmap=cmap, vmin=0, vmax=1, interpolation="nearest", origin="lower", zorder=0)
    _style_2d(ax, L)

    # Hilbert polyline overlay (always connected).
    alpha = 0.22 if (1 << m_bits) <= 128 else 0.12
    lw = 0.85 if (1 << m_bits) <= 128 else 0.55
    lc = LineCollection(segs, array=t_segs, cmap="viridis", linewidths=lw, alpha=alpha, zorder=1)
    ax.add_collection(lc)

    return int(len(idxs))


def _render_node_3d(
    *,
    fig: plt.Figure,
    box: Tuple[float, float, float, float],
    m_bits: int,
    n_bits: int,
    w: str,
    color: str,
    cache: Dict[Tuple[int, int], Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]],
) -> int:
    """
    Render 3D in the right half of node box. Returns g=|preimage|.
    """
    (x, y, w_box, h_box) = box
    ax3 = fig.add_axes([x, y, w_box, h_box], projection="3d")
    ax3.set_facecolor("#FFFFFF")

    key = (m_bits, n_bits)
    if key not in cache:
        cache[key] = _coords_3d_prefix(m_bits=m_bits, n_bits=n_bits)
    coords, segs3, t3, outs = cache[key]
    N = len(outs)
    idxs = [i for i in range(N) if outs[i] == w]

    L = 1 << int(n_bits)
    _style_3d(ax3, L)

    alpha = 0.18 if (1 << m_bits) <= 128 else 0.12
    lw = 0.55 if (1 << m_bits) >= 256 else 0.70
    lc3 = Line3DCollection(segs3, array=t3, cmap="viridis", linewidths=lw, alpha=alpha)
    ax3.add_collection3d(lc3)

    if idxs:
        pts = coords[np.array(idxs, dtype=int), :]
        ax3.scatter(
            pts[:, 0],
            pts[:, 1],
            pts[:, 2],
            s=12,
            c=color,
            depthshade=False,
            edgecolors="white",
            linewidths=0.25,
            alpha=0.92,
        )
    return int(len(idxs))


def _build_tree_nodes(u: str) -> Dict[int, List[str]]:
    """
    Nodes at each m are exactly Ext_m(u) = { w ∈ X_m : w[:6]=u } for m>=6.
    """
    out: Dict[int, List[str]] = {6: [u]}
    for m in range(7, M_MAX + 1):
        out[m] = [w for w in xm.all_xm(m) if w[:6] == u]
    # Deterministic per-level ordering: group by parent prefix.
    out[6] = sorted(out[6])
    for m in range(7, M_MAX + 1):
        out[m] = _prefix_grouped_order(out[m], parent_len=m - 1)
    return out


def _edges(levels: Dict[int, List[str]]) -> List[Tuple[int, str, int, str]]:
    es: List[Tuple[int, str, int, str]] = []
    for mp in range(M_MIN, M_MAX):
        mc = mp + 1
        parent_set = set(levels[mp])
        for w in levels[mc]:
            p = w[:mp]
            if p in parent_set:
                es.append((mp, p, mc, w))
    return es


def _build_tree_catalog_for_u(*, u: str, label: str) -> Dict[str, object]:
    """
    Build a deterministic, machine-readable catalog of the refinement tree:
      - nodes grouped by m
      - parent relation via prefix projection
      - per-node invariants: boundary tag and g_m(w)
    """
    levels = _build_tree_nodes(u)
    es = _edges(levels)

    # Precompute degeneracy maps (cached on disk by exp_foldm_stats).
    gm_by_m: Dict[int, Dict[str, int]] = {m: foldm.cached_degeneracy_map(m) for m in range(M_MIN, M_MAX + 1)}

    def node_obj(m: int, w: str) -> Dict[str, object]:
        gm = int(gm_by_m[int(m)][w])
        return {
            "m": int(m),
            "w": str(w),
            "prefix6": str(w[:6]),
            "is_boundary": bool(xm.is_boundary_word(w)),
            "g": gm,
        }

    nodes: Dict[str, List[Dict[str, object]]] = {}
    for m in range(M_MIN, M_MAX + 1):
        nodes[str(m)] = [node_obj(m, w) for w in levels[m]]

    edges: List[Dict[str, object]] = []
    for mp, wp, mc, wc in es:
        edges.append(
            {
                "parent": {"m": int(mp), "w": str(wp)},
                "child": {"m": int(mc), "w": str(wc)},
            }
        )

    return {
        "root_u": str(u),
        "root_label": str(label),
        "root_V": int(sml.zeckendorf_value(u)),
        "levels": nodes,
        "edges": edges,
    }


def _render_tree_for_u(*, u: str, label: str, base_color: str, out_png: Path) -> None:
    levels = _build_tree_nodes(u)
    es = _edges(levels)

    # Layout constants
    levels_m = list(range(M_MIN, M_MAX + 1))
    max_nodes = max(len(levels[m]) for m in levels_m)
    x0 = 0.06
    x1 = 0.98
    y_top = 0.90
    y_bot = 0.08
    dy = (y_top - y_bot) / float(len(levels_m) - 1)

    node_w = min(0.20, (x1 - x0) / float(max(1, max_nodes)) * 0.92)
    # Slightly shorter to fit more levels (m=6..12) with legible spacing.
    node_h = 0.10
    pad_x = 0.010
    pad_y = 0.008
    # Split node into vertical stack: 2D (top) / 3D (bottom).
    gap_mid = 0.006
    h2 = (node_h - gap_mid) * 0.5
    h3 = (node_h - gap_mid) * 0.5

    # Keep output readable while avoiding excessive memory use.
    fig = plt.figure(figsize=(20.0, 14.0))
    ax_bg = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax_bg.axis("off")

    # Assign positions (center) for each node.
    pos: Dict[Tuple[int, str], Tuple[float, float]] = {}
    for li, m in enumerate(levels_m):
        ws = levels[m]
        n = len(ws)
        if n == 1:
            xs = [0.5 * (x0 + x1)]
        else:
            span = (x1 - x0) - node_w
            xs = [x0 + (span * float(i) / float(n - 1)) + node_w / 2.0 for i in range(n)]
        y = y_top - float(li) * dy
        for w, xc in zip(ws, xs):
            pos[(m, w)] = (float(xc), float(y))

    # Draw edges as lines between node centers.
    for mp, wp, mc, wc in es:
        (xA, yA) = pos[(mp, wp)]
        (xB, yB) = pos[(mc, wc)]
        ax_bg.plot([xA, xB], [yA, yB], color=base_color, lw=1.6, alpha=0.35, zorder=1)

    # Caches for per-(m,n) Hilbert assets.
    cache2d: Dict[Tuple[int, int], Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]] = {}
    cache3d: Dict[Tuple[int, int], Tuple[np.ndarray, np.ndarray, np.ndarray, List[str]]] = {}

    # Render each node as two inset panels (2D + 3D) inside a light box.
    for m in levels_m:
        n2 = _ceil_div(m, 2)
        n3 = _ceil_div(m, 3)
        for w in levels[m]:
            (xc, yc) = pos[(m, w)]
            left = xc - node_w / 2.0
            bottom = yc - node_h / 2.0

            # Node background box.
            rect = plt.Rectangle(
                (left, bottom),
                node_w,
                node_h,
                transform=ax_bg.transAxes,
                fill=True,
                facecolor="#FAFAFA",
                edgecolor=base_color,
                linewidth=2.0 if m == 6 else 1.2,
                alpha=0.92,
                zorder=2,
            )
            ax_bg.add_patch(rect)

            # Titles
            if m == 6:
                title = f"m=6  u={w}\n{label}"
            else:
                title = f"m={m}  w={w}"
            ax_bg.text(
                xc,
                bottom + node_h + 0.006,
                title,
                transform=ax_bg.transAxes,
                ha="center",
                va="bottom",
                fontsize=9.0 if m == 6 else 7.8,
                color="#263238",
                zorder=3,
            )

            # 2D (top)
            box2 = (
                left + pad_x,
                bottom + h3 + gap_mid + pad_y,
                node_w - 2 * pad_x,
                h2 - 2 * pad_y,
            )
            g2 = _render_node_2d(fig=fig, box=box2, m_bits=m, n_bits=n2, w=w, color=base_color, cache=cache2d)

            # 3D (bottom)
            box3 = (
                left + pad_x,
                bottom + pad_y,
                node_w - 2 * pad_x,
                h3 - 2 * pad_y,
            )
            g3 = _render_node_3d(fig=fig, box=box3, m_bits=m, n_bits=n3, w=w, color=base_color, cache=cache3d)

            # Consistency (same preimage count by construction).
            if g2 != g3:
                ax_bg.text(
                    left + node_w - 0.004,
                    bottom + 0.004,
                    f"g mismatch {g2}/{g3}",
                    transform=ax_bg.transAxes,
                    ha="right",
                    va="bottom",
                    fontsize=7.5,
                    color="#C62828",
                    zorder=4,
                )
            ax_bg.text(
                xc,
                bottom - 0.006,
                f"g={g2}   (2D n={n2}, 3D n={n3})",
                transform=ax_bg.transAxes,
                ha="center",
                va="top",
                fontsize=7.6,
                color="#455A64",
                zorder=3,
            )

    fig.suptitle(
        f"Hilbert-only refinement tree for base type u ∈ X_6 (m=6..12)  —  2D (top) + 3D (bottom) per node\n"
        f"root: u={u}  label={label}",
        fontsize=13.5,
        y=0.995,
    )
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")


def main() -> None:
    out_dir = figures_dir() / "adaptive" / "hilbert_tree"
    out_dir.mkdir(parents=True, exist_ok=True)
    data_dir = out_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    label_map = _get_sm_labeling_map()
    X6 = sml.all_x6()
    X6_sorted = sorted(X6, key=lambda u: (sml.zeckendorf_value(u), u))
    palette = _material_palette_21()
    if len(X6_sorted) != 21 or len(palette) < 21:
        raise AssertionError("Expected 21 base types/colors.")

    catalog_all: Dict[str, object] = {"m_range": [M_MIN, M_MAX], "trees": []}
    for i, u in enumerate(X6_sorted):
        lab = label_map[u]
        col = palette[i]
        out_png = out_dir / f"hilbert_tree_{OUT_TAG}_u_{u}.png"
        _render_tree_for_u(u=u, label=lab, base_color=col, out_png=out_png)

        # Also write a deterministic per-tree data file with all "new states" at m>6.
        cat = _build_tree_catalog_for_u(u=u, label=lab)
        (data_dir / f"hilbert_tree_{OUT_TAG}_u_{u}.json").write_text(
            json.dumps(cat, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        cast_list = catalog_all["trees"]
        if not isinstance(cast_list, list):
            raise AssertionError("catalog_all['trees'] must be a list.")
        cast_list.append(cat)

    # One combined catalog for convenience.
    (data_dir / f"hilbert_tree_{OUT_TAG}_catalog.json").write_text(
        json.dumps(catalog_all, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Wrote {data_dir / f'hilbert_tree_{OUT_TAG}_catalog.json'}")


if __name__ == "__main__":
    main()

