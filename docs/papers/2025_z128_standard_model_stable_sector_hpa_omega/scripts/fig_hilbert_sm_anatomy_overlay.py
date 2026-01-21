# -*- coding: utf-8 -*-
"""
One-page "anatomy" overlay for a concrete wiring geometry (wiring_geometry.json).

We visualize:
  - the scan polyline (center-to-center wiring)
  - refined nodes (m=8/m=10)
  - cross-level scan segments (m changes along the scan)
  - representative plaquettes (2D squares) whose holonomy angle bin is 120° or 180°

Outputs:
  <wiring-dir>/anatomy_overlay.svg

English-only plot text (repo convention).
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import exp_holonomy_loops as holo
import exp_holonomy_su3_representation as su3rep
from hilbert_sm_holonomy import _best_perm_with_ports


Perm = Tuple[int, int, int, int]


def _read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _pt2_key(pt: List[float]) -> Tuple[int, int]:
    return (int(round(2.0 * float(pt[0]))), int(round(2.0 * float(pt[1]))))


def _pt3_key(pt: List[float]) -> Tuple[int, int, int]:
    return (int(round(2.0 * float(pt[0]))), int(round(2.0 * float(pt[1]))), int(round(2.0 * float(pt[2]))))


def _axis_neighbors_2d(pos: Dict[Tuple[int, int], int], step: int = 2) -> List[Tuple[int, int]]:
    edges: List[Tuple[int, int]] = []
    for (x, y), a in pos.items():
        for dx, dy in ((step, 0), (0, step)):
            b = pos.get((x + dx, y + dy))
            if b is None:
                continue
            edges.append((int(a), int(b)))
    return edges


def _plaquettes_2d(pos: Dict[Tuple[int, int], int], step: int = 2) -> List[Tuple[int, int, int, int, Tuple[int, int]]]:
    # return (a,b,c,d,(x,y)) for squares with bottom-left (x,y)
    pls: List[Tuple[int, int, int, int, Tuple[int, int]]] = []
    for (x, y), a in pos.items():
        b = pos.get((x + step, y))
        c = pos.get((x + step, y + step))
        d = pos.get((x, y + step))
        if b is None or c is None or d is None:
            continue
        pls.append((int(a), int(b), int(c), int(d), (int(x), int(y))))
    return pls


def _angle_bin_deg(ang: float) -> str:
    if abs(float(ang) - 0.0) < 1e-6:
        return "0"
    if abs(float(ang) - 90.0) < 1e-6:
        return "90"
    if abs(float(ang) - 120.0) < 1e-6:
        return "120"
    return "180"


def _edge_perm_cache(nodes: List[Dict[str, Any]], edges: List[Tuple[int, int]]) -> Dict[Tuple[int, int], Perm]:
    pre = holo.preimages()
    out: Dict[Tuple[int, int], Perm] = {}
    for a, b in edges:
        wa = str(nodes[int(a)]["u6"])
        wb = str(nodes[int(b)]["u6"])
        rep_a = str(nodes[int(a)].get("rep", "$-$"))
        rep_b = str(nodes[int(b)].get("rep", "$-$"))
        fa = holo.fiber4(pre, wa)
        fb = holo.fiber4(pre, wb)
        p = _best_perm_with_ports(fa, fb, rep_a, rep_b)
        out[(int(a), int(b))] = p
        out[(int(b), int(a))] = holo.inv_perm(p)
    return out


def _strip_generation(label_tex: str) -> str:
    # Best-effort: remove ^{(n)} in TeX label.
    s = str(label_tex)
    return s.replace("^{(1)}", "").replace("^{(2)}", "").replace("^{(3)}", "")


@dataclass(frozen=True)
class PlaqMark:
    ang_bin: str          # "120" or "180"
    x0: float             # bottom-left x (float)
    y0: float             # bottom-left y
    score: float          # for picking "typical" ones
    note: str             # short annotation


def _pick_typical_plaquettes_2d(nodes: List[Dict[str, Any]], max_n: int) -> List[PlaqMark]:
    # Map positions to node id.
    pos: Dict[Tuple[int, int], int] = {}
    for n in nodes:
        pos[_pt2_key(n["pt"])] = int(n["id"])

    edges = _axis_neighbors_2d(pos)
    edge_p = _edge_perm_cache(nodes, edges)

    B = su3rep.basis_B()
    pls = _plaquettes_2d(pos)

    picks_120: List[PlaqMark] = []
    picks_180: List[PlaqMark] = []

    for a, b, c, d, (x, y) in pls:
        # a->b->c->d->a
        holp = holo.compose(edge_p[(d, a)], holo.compose(edge_p[(c, d)], holo.compose(edge_p[(b, c)], edge_p[(a, b)])))
        R = su3rep.su3_rep(holp, B=B)
        ang = float(su3rep.rotation_angle_deg(R))
        ab = _angle_bin_deg(ang)
        if ab not in ("120", "180"):
            continue

        ma = int(nodes[int(a)].get("m", 6))
        mb = int(nodes[int(b)].get("m", 6))
        mc = int(nodes[int(c)].get("m", 6))
        md = int(nodes[int(d)].get("m", 6))
        score = float(ma + mb + mc + md) + (0.01 if ab == "120" else 0.0)

        lab = _strip_generation(str(nodes[int(a)].get("label", "")))
        rep = str(nodes[int(a)].get("rep", ""))
        note = f"{ab}°, {lab}, {rep}"

        x0 = float(x) / 2.0
        y0 = float(y) / 2.0
        m = PlaqMark(ang_bin=ab, x0=x0, y0=y0, score=score, note=note)
        if ab == "120":
            picks_120.append(m)
        else:
            picks_180.append(m)

    picks_120.sort(key=lambda z: z.score, reverse=True)
    picks_180.sort(key=lambda z: z.score, reverse=True)
    return picks_120[: int(max_n)] + picks_180[: int(max_n)]


def _plot_overlay(ax: Any, *, nodes: List[Dict[str, Any]], scan_ids: List[int], dim: int, title: str, max_plaq: int) -> None:
    # Polyline
    pts = [nodes[int(i)]["pt"] for i in scan_ids]
    if dim == 2:
        xs = [float(p[0]) for p in pts]
        ys = [float(p[1]) for p in pts]
    else:
        xs = [float(p[0]) for p in pts]
        ys = [float(p[1]) for p in pts]  # XY projection

    ax.plot(xs, ys, "-", lw=0.6, alpha=0.55, color="#263238")

    # Refined nodes
    r8x: List[float] = []
    r8y: List[float] = []
    r10x: List[float] = []
    r10y: List[float] = []
    for n in nodes:
        m = int(n.get("m", 6))
        p = n["pt"]
        x = float(p[0])
        y = float(p[1]) if dim == 2 else float(p[1])
        if m == 8:
            r8x.append(x)
            r8y.append(y)
        elif m == 10:
            r10x.append(x)
            r10y.append(y)

    if r8x:
        ax.scatter(r8x, r8y, s=6.0, color="#1565C0", alpha=0.85, label="m=8 nodes")
    if r10x:
        ax.scatter(r10x, r10y, s=7.0, color="#C62828", alpha=0.85, label="m=10 nodes")

    # Cross-level scan segments (m changes along scan)
    diag_segs_x: List[float] = []
    diag_segs_y: List[float] = []
    for a, b in zip(scan_ids[:-1], scan_ids[1:]):
        na = nodes[int(a)]
        nb = nodes[int(b)]
        if int(na.get("m", 6)) == int(nb.get("m", 6)):
            continue
        pa = na["pt"]
        pb = nb["pt"]
        diag_segs_x.extend([float(pa[0]), float(pb[0]), math.nan])
        diag_segs_y.extend([float(pa[1]), float(pb[1]), math.nan])
    if diag_segs_x:
        ax.plot(diag_segs_x, diag_segs_y, "-", lw=1.2, alpha=0.85, color="#EF6C00", label="cross-m scan segments")

    # Plaquette marks (only for 2D, since 3D plaquettes live in xy/xz/yz planes)
    if dim == 2 and int(max_plaq) > 0:
        marks = _pick_typical_plaquettes_2d(nodes, max_n=int(max_plaq))
        for mk in marks:
            ec = "#6A1B9A" if mk.ang_bin == "180" else "#2E7D32"
            ax.add_patch(Rectangle((mk.x0, mk.y0), 1.0, 1.0, fill=False, lw=1.5, ec=ec, alpha=0.9))
        # annotate a few (avoid clutter)
        for mk in marks[: min(6, len(marks))]:
            ax.text(mk.x0 + 0.02, mk.y0 + 0.02, mk.ang_bin, fontsize=7, color="#000000", alpha=0.9)

    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title, fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiring-dir", type=str, required=True, help="Directory containing wiring_geometry.json")
    ap.add_argument("--max-plaquettes", type=int, default=8, help="Number of typical 120° and 180° plaquettes to mark (each).")
    args = ap.parse_args()

    wdir = Path(str(args.wiring_dir))
    obj = _read_json(wdir / "wiring_geometry.json")

    g2 = obj.get("graph2d", {})
    g3 = obj.get("graph3d", {})
    nodes2 = list(g2.get("nodes", []))
    nodes3 = list(g3.get("nodes", []))
    scan2 = [int(x) for x in g2.get("scan_path_node_ids", [])]
    scan3 = [int(x) for x in g3.get("scan_path_node_ids", [])]

    fig = plt.figure(figsize=(12, 6), dpi=180)
    ax1 = fig.add_subplot(1, 2, 1)
    ax2 = fig.add_subplot(1, 2, 2)

    _plot_overlay(
        ax1,
        nodes=nodes2,
        scan_ids=scan2,
        dim=2,
        title="2D wiring anatomy (refinement, cross-m segments, plaquette holonomy bins)",
        max_plaq=int(args.max_plaquettes),
    )
    _plot_overlay(
        ax2,
        nodes=nodes3,
        scan_ids=scan3,
        dim=3,
        title="3D wiring anatomy (XY projection; refinement, cross-m segments)",
        max_plaq=0,
    )

    # Shared legend (deduplicate)
    handles, labels = ax1.get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, fontsize=9)

    fig.tight_layout(rect=(0.0, 0.06, 1.0, 1.0))
    out = wdir / "anatomy_overlay.svg"
    fig.savefig(out, format="svg")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

