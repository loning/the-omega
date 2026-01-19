#!/usr/bin/env python3
"""
Render a 3D "wiring geometry" JSON into a perspective PNG.

Input JSON is expected to be produced by:
  - fig_hilbert_sm_wiring_fold_geometry_full_gi.py, or
  - fig_hilbert_sm_wiring_fold_geometry_holonomy_gi.py

and to contain:
  data["graph3d"]["segments"] = [ [p0, p1], ... ] where p0/p1 are [x,y,z].
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Sequence


def _iter_points_from_segments(segments: Iterable[Sequence[Sequence[float]]]):
    for seg in segments:
        if not isinstance(seg, (list, tuple)) or len(seg) != 2:
            continue
        p0, p1 = seg
        if isinstance(p0, (list, tuple)) and len(p0) == 3:
            yield float(p0[0]), float(p0[1]), float(p0[2])
        if isinstance(p1, (list, tuple)) and len(p1) == 3:
            yield float(p1[0]), float(p1[1]), float(p1[2])


def _set_equal_3d_limits(ax, xs, ys, zs, pad: float = 0.6):
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)

    cx = 0.5 * (xmin + xmax)
    cy = 0.5 * (ymin + ymax)
    cz = 0.5 * (zmin + zmax)

    rx = (xmax - xmin) * 0.5
    ry = (ymax - ymin) * 0.5
    rz = (zmax - zmin) * 0.5
    r = max(rx, ry, rz, 1e-9) + pad

    ax.set_xlim(cx - r, cx + r)
    ax.set_ylim(cy - r, cy + r)
    ax.set_zlim(cz - r, cz + r)

    # Matplotlib >= 3.3
    try:
        ax.set_box_aspect((1, 1, 1))
    except Exception:
        pass


def _pt_key(pt: Sequence[float], ndigits: int = 6) -> tuple[float, float, float]:
    return (round(float(pt[0]), ndigits), round(float(pt[1]), ndigits), round(float(pt[2]), ndigits))


def _node_text(node: dict, mode: str) -> str:
    if mode == "id":
        return str(node.get("id"))
    if mode == "k":
        return str(node.get("k_coarse"))
    if mode == "u6":
        return str(node.get("u6"))
    if mode == "rep":
        return str(node.get("rep"))
    if mode == "label":
        # Mathtext-friendly strings are already wrapped in $...$ in the JSON.
        return str(node.get("label"))
    return ""


def _add_axis_triad(ax, origin: tuple[float, float, float], scale: float = 1.5):
    ox, oy, oz = origin
    ax.plot([ox, ox + scale], [oy, oy], [oz, oz], color="#D32F2F", lw=2.0, alpha=0.9)
    ax.plot([ox, ox], [oy, oy + scale], [oz, oz], color="#388E3C", lw=2.0, alpha=0.9)
    ax.plot([ox, ox], [oy, oy], [oz, oz + scale], color="#1976D2", lw=2.0, alpha=0.9)
    ax.text(ox + scale * 1.05, oy, oz, "x", color="#D32F2F", fontsize=12)
    ax.text(ox, oy + scale * 1.05, oz, "y", color="#388E3C", fontsize=12)
    ax.text(ox, oy, oz + scale * 1.05, "z", color="#1976D2", fontsize=12)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        required=True,
        help="Path to wiring_geometry.json",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output PNG path (default: alongside input).",
    )
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--width", type=float, default=8.5, help="Figure width (in).")
    parser.add_argument("--height", type=float, default=8.0, help="Figure height (in).")
    parser.add_argument("--elev", type=float, default=22.0, help="View elevation.")
    parser.add_argument("--azim", type=float, default=-52.0, help="View azimuth.")
    parser.add_argument("--lw", type=float, default=1.15, help="Line width.")
    parser.add_argument("--alpha", type=float, default=0.9, help="Line alpha.")
    parser.add_argument(
        "--transparent",
        action="store_true",
        help="Save PNG with transparent background (default: white).",
    )
    parser.add_argument(
        "--scatter-nodes",
        action="store_true",
        help="Also scatter all node positions from graph3d.nodes.",
    )
    parser.add_argument(
        "--color-by-m",
        action="store_true",
        help="Color nodes/edges by m (and highlight cross-m edges).",
    )
    parser.add_argument(
        "--label-mode",
        choices=["none", "id", "k", "label", "rep", "u6"],
        default="k",
        help="What to write next to labeled nodes.",
    )
    parser.add_argument(
        "--label-topk",
        type=int,
        default=35,
        help="Label top-K nodes by degree (0 disables).",
    )
    parser.add_argument(
        "--label-only-m",
        type=int,
        default=6,
        help="If set, only label nodes with this m (use -1 for no filter).",
    )
    parser.add_argument("--label-size", type=float, default=9.5)
    parser.add_argument(
        "--label-offset",
        type=float,
        default=0.12,
        help="Label offset in data units along +z (helps reduce overlap).",
    )
    args = parser.parse_args()

    in_path = Path(args.input).expanduser().resolve()
    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    graph3d = data.get("graph3d") or {}
    segments = graph3d.get("segments") or []
    if not segments:
        raise SystemExit("No graph3d.segments found in input JSON.")

    out_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else in_path.with_name("wiring_3d_perspective.png")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Import matplotlib only after parsing (faster CLI help).
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(args.width, args.height))
    ax = fig.add_subplot(111, projection="3d")

    # Build point->node map and degrees (for labeling).
    nodes = graph3d.get("nodes") or []
    pt_to_node: dict[tuple[float, float, float], dict] = {}
    for nd in nodes:
        if not isinstance(nd, dict):
            continue
        pt = nd.get("pt")
        if isinstance(pt, (list, tuple)) and len(pt) == 3:
            pt_to_node[_pt_key(pt)] = nd

    degrees: dict[tuple[float, float, float], int] = {}
    for seg in segments:
        if not isinstance(seg, (list, tuple)) or len(seg) != 2:
            continue
        p0, p1 = seg
        if not (isinstance(p0, (list, tuple)) and isinstance(p1, (list, tuple)) and len(p0) == 3 and len(p1) == 3):
            continue
        k0 = _pt_key(p0)
        k1 = _pt_key(p1)
        degrees[k0] = degrees.get(k0, 0) + 1
        degrees[k1] = degrees.get(k1, 0) + 1

    # Draw segments (optionally colored).
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []

    for (x, y, z) in _iter_points_from_segments(segments):
        xs.append(x)
        ys.append(y)
        zs.append(z)

    # Color palette (Material-ish).
    m_node_color = {6: "#1565C0", 8: "#FB8C00", 10: "#2E7D32"}
    cross_m_edge_color = "#C62828"
    default_edge_color = "#212121"

    for seg in segments:
        if not isinstance(seg, (list, tuple)) or len(seg) != 2:
            continue
        p0, p1 = seg
        if not (
            isinstance(p0, (list, tuple))
            and isinstance(p1, (list, tuple))
            and len(p0) == 3
            and len(p1) == 3
        ):
            continue
        x0, y0, z0 = float(p0[0]), float(p0[1]), float(p0[2])
        x1, y1, z1 = float(p1[0]), float(p1[1]), float(p1[2])
        edge_color = default_edge_color
        if args.color_by_m:
            n0 = pt_to_node.get(_pt_key(p0))
            n1 = pt_to_node.get(_pt_key(p1))
            m0 = n0.get("m") if isinstance(n0, dict) else None
            m1 = n1.get("m") if isinstance(n1, dict) else None
            if isinstance(m0, int) and isinstance(m1, int) and m0 != m1:
                edge_color = cross_m_edge_color
            elif isinstance(m0, int) and m0 in m_node_color:
                edge_color = m_node_color[m0]

        ax.plot(
            [x0, x1],
            [y0, y1],
            [z0, z1],
            color=edge_color,
            lw=args.lw,
            alpha=args.alpha,
        )

    if args.scatter_nodes:
        nx6, ny6, nz6 = [], [], []
        nx8, ny8, nz8 = [], [], []
        nx10, ny10, nz10 = [], [], []
        nxo, nyo, nzo = [], [], []
        for nd in nodes:
            if not isinstance(nd, dict):
                continue
            pt = nd.get("pt")
            if not (isinstance(pt, (list, tuple)) and len(pt) == 3):
                continue
            x, y, z = float(pt[0]), float(pt[1]), float(pt[2])
            m = nd.get("m")
            if args.color_by_m and isinstance(m, int):
                if m == 6:
                    nx6.append(x), ny6.append(y), nz6.append(z)
                elif m == 8:
                    nx8.append(x), ny8.append(y), nz8.append(z)
                elif m == 10:
                    nx10.append(x), ny10.append(y), nz10.append(z)
                else:
                    nxo.append(x), nyo.append(y), nzo.append(z)
            else:
                nx6.append(x), ny6.append(y), nz6.append(z)

        if nx6:
            ax.scatter(nx6, ny6, nz6, s=10, c=m_node_color[6], alpha=0.95, depthshade=False, label="m=6")
        if nx8:
            ax.scatter(nx8, ny8, nz8, s=10, c=m_node_color[8], alpha=0.95, depthshade=False, label="m=8")
        if nx10:
            ax.scatter(nx10, ny10, nz10, s=10, c=m_node_color[10], alpha=0.95, depthshade=False, label="m=10")
        if nxo:
            ax.scatter(nxo, nyo, nzo, s=10, c="#6D4C41", alpha=0.95, depthshade=False, label="m=other")

    _set_equal_3d_limits(ax, xs, ys, zs)
    ax.view_init(elev=args.elev, azim=args.azim)

    # Clean look: remove axes.
    ax.set_axis_off()

    # Label selected nodes (default: top-K by degree).
    if args.label_mode != "none" and args.label_topk > 0:
        # Candidate points to label: those present in pt_to_node.
        items = []
        for pt_k, deg in degrees.items():
            nd = pt_to_node.get(pt_k)
            if not isinstance(nd, dict):
                continue
            m = nd.get("m")
            if args.label_only_m != -1 and isinstance(m, int) and m != args.label_only_m:
                continue
            items.append((deg, pt_k, nd))
        items.sort(key=lambda t: (-t[0], t[1]))

        for deg, pt_k, nd in items[: args.label_topk]:
            x, y, z = pt_k
            txt = _node_text(nd, args.label_mode)
            if not txt:
                continue
            ax.text(
                x,
                y,
                z + args.label_offset,
                txt,
                fontsize=args.label_size,
                color="#111111",
            )

    # Legend + axis triad for orientation.
    if args.scatter_nodes and args.color_by_m:
        ax.legend(loc="upper left", frameon=False, fontsize=11)
    if xs and ys and zs:
        _add_axis_triad(ax, origin=(min(xs), min(ys), min(zs)), scale=1.7)

    fig.tight_layout(pad=0.0)
    if args.transparent:
        fig.savefig(out_path, dpi=args.dpi, transparent=True)
    else:
        fig.savefig(out_path, dpi=args.dpi, facecolor="white", transparent=False)
    plt.close(fig)

    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

