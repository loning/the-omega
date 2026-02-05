#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Figure: observer bubble generation graph (m=6, y=0^6).

We visualize the bit-level unfolding/folding semantics as a layered graph.

Nodes (depth d) are reachable states of (t, tr) where:
  - t is the L=3 tail-head bitstring packed as int with low-to-high bits (c7,c8,c9)
  - tr is the trace bitstring of length d (branch-choice record)

Unfold step (write 1 bit b):
  t' = ((t << 1) & mask) | b
  tr' = tr || b
  and we filter by:
    - no-adjacent-ones constraint on t'
    - micro bound N = 21*c7 + 34*c8 + 55*c9 <= 63 for macro y=0^6

Fold step (erase 1 bit):
  require b == (t' & 1), then t = t' >> 1 and pop(tr')

Outputs
-------
- artifacts/export/observer_bubble_graph_m6.png
- sections/generated/fig_observer_bubble_graph_m6.tex
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import export_dir, generated_dir
from common_tex_pylatex import write_lines_as_fragment


def _no_adjacent_ones(x: int) -> bool:
    return (x & (x << 1)) == 0


def _bits_c7c8c9(t: int) -> Tuple[int, int, int]:
    c7 = (t >> 0) & 1
    c8 = (t >> 1) & 1
    c9 = (t >> 2) & 1
    return int(c7), int(c8), int(c9)


def _micro_N_for_y0_m6(t: int) -> int:
    c7, c8, c9 = _bits_c7c8c9(t)
    return 21 * c7 + 34 * c8 + 55 * c9


@dataclass(frozen=True)
class Node:
    depth: int
    t: int
    tr: str


@dataclass(frozen=True)
class Edge:
    src: Node
    dst: Node
    b: int


def _expand_frontier(frontier: List[Node], depth: int) -> Tuple[List[Node], List[Edge]]:
    """Expand one unfold step from all nodes at given depth."""
    assert all(n.depth == depth for n in frontier)
    mask = 0b111  # L=3
    nxt_nodes: List[Node] = []
    nxt_edges: List[Edge] = []
    seen = set()
    for n in frontier:
        for b in (0, 1):
            tp = ((n.t << 1) & mask) | b
            if not _no_adjacent_ones(tp):
                continue
            # Macro fixed: y=0^6 => V=0 and only micro bound remains for tails.
            Np = _micro_N_for_y0_m6(tp)
            if not (0 <= Np <= 63):
                continue
            trp = n.tr + str(b)
            nd = Node(depth=depth + 1, t=tp, tr=trp)
            key = (nd.depth, nd.t, nd.tr)
            if key in seen:
                continue
            seen.add(key)
            nxt_nodes.append(nd)
            nxt_edges.append(Edge(src=n, dst=nd, b=b))
    return nxt_nodes, nxt_edges


def _beam_prune(nodes: List[Node], E: int) -> List[Node]:
    """Deterministic energy cap: keep at most E nodes by increasing micro N, then trace."""
    if E <= 0:
        return []
    if len(nodes) <= E:
        return nodes
    nodes_sorted = sorted(nodes, key=lambda n: (_micro_N_for_y0_m6(n.t), n.tr, n.t))
    return nodes_sorted[:E]


def _build_bubble(depth_max: int, E: Optional[int]) -> Tuple[List[Node], List[Edge]]:
    root = Node(depth=0, t=0, tr="")
    all_nodes = [root]
    all_edges: List[Edge] = []
    frontier = [root]
    for d in range(0, depth_max):
        nxt, edges = _expand_frontier(frontier, depth=d)
        if E is not None:
            nxt = _beam_prune(nxt, E=E)
            keep = {(n.depth, n.t, n.tr) for n in nxt}
            edges = [e for e in edges if (e.dst.depth, e.dst.t, e.dst.tr) in keep]
        all_nodes.extend(nxt)
        all_edges.extend(edges)
        frontier = nxt
    return all_nodes, all_edges


def _node_label(n: Node) -> str:
    c7, c8, c9 = _bits_c7c8c9(n.t)
    tr = n.tr if n.tr != "" else "ε"
    return f"t={c7}{c8}{c9}\ntr={tr}"


def _layout(nodes: List[Node]) -> Dict[Tuple[int, int, str], Tuple[float, float]]:
    """Layered layout by depth; within a layer sort by (t,tr)."""
    by_depth: Dict[int, List[Node]] = {}
    for n in nodes:
        by_depth.setdefault(n.depth, []).append(n)
    pos: Dict[Tuple[int, int, str], Tuple[float, float]] = {}
    for d, lst in sorted(by_depth.items()):
        lst_sorted = sorted(lst, key=lambda n: (n.t, n.tr))
        # Vertical spacing
        for i, n in enumerate(lst_sorted):
            x = float(d)
            y = float(len(lst_sorted) - 1 - i)
            pos[(n.depth, n.t, n.tr)] = (x, y)
    return pos


def _draw(ax, nodes: List[Node], edges: List[Edge], title: str) -> None:
    pos = _layout(nodes)
    # Draw edges (unfold)
    for e in edges:
        x0, y0 = pos[(e.src.depth, e.src.t, e.src.tr)]
        x1, y1 = pos[(e.dst.depth, e.dst.t, e.dst.tr)]
        ax.annotate(
            "",
            xy=(x1 - 0.06, y1),
            xytext=(x0 + 0.06, y0),
            arrowprops=dict(arrowstyle="->", lw=1.2, color="black", shrinkA=0, shrinkB=0),
        )
        ax.text((x0 + x1) / 2.0, (y0 + y1) / 2.0 + 0.08, f"b={e.b}", fontsize=8, ha="center")

    # Draw reverse (fold) hints: pop + >>1, dashed gray
    for e in edges:
        x1, y1 = pos[(e.dst.depth, e.dst.t, e.dst.tr)]
        x0, y0 = pos[(e.src.depth, e.src.t, e.src.tr)]
        ax.annotate(
            "",
            xy=(x0 + 0.06, y0 - 0.02),
            xytext=(x1 - 0.06, y1 - 0.02),
            arrowprops=dict(arrowstyle="->", lw=0.9, color="#777777", linestyle="--"),
        )

    # Draw nodes
    for n in nodes:
        x, y = pos[(n.depth, n.t, n.tr)]
        ax.scatter([x], [y], s=600, facecolor="white", edgecolor="black", linewidth=1.2, zorder=3)
        ax.text(x, y, _node_label(n), ha="center", va="center", fontsize=8, zorder=4)

    ax.set_title(title, fontsize=11)
    ax.set_axis_off()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth_max", type=int, default=3, help="max unfold depth (m=6 => L=3)")
    ap.add_argument("--E_show", type=int, default=1, help="energy cap to visualize in right panel")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    params = {"depth_max": int(args.depth_max), "E_show": int(args.E_show)}
    out_png = "observer_bubble_graph_m6.png"
    out_fig = "fig_observer_bubble_graph_m6.tex"

    from pathlib import Path

    script_path = Path(__file__).resolve()
    run = prepare_run(
        experiment="observer_bubble_graph_m6",
        params=params,
        script_path=script_path,
        required_files=[out_png, out_fig],
        force=bool(args.force),
        extra_fingerprint=None,
    )

    out_png_path = run.run_dir / out_png
    out_fig_path = run.run_dir / out_fig

    if run.cached:
        print(f"[fig_observer_bubble_graph_m6] cached: {run.run_dir.name}", flush=True)
        copy_atomic(run.run_dir / out_png, export_dir() / out_png)
        copy_atomic(run.run_dir / out_fig, generated_dir() / out_fig)
        return

    nodes_full, edges_full = _build_bubble(depth_max=int(args.depth_max), E=None)
    nodes_E, edges_E = _build_bubble(depth_max=int(args.depth_max), E=int(args.E_show))

    fig = plt.figure(figsize=(11.5, 4.2), dpi=200)
    ax1 = fig.add_subplot(1, 2, 1)
    ax2 = fig.add_subplot(1, 2, 2)
    _draw(ax1, nodes_full, edges_full, title="full bubble (no energy cap)")
    _draw(ax2, nodes_E, edges_E, title=f"energy-capped bubble (E={int(args.E_show)})")
    fig.tight_layout()

    out_png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png_path, bbox_inches="tight")
    plt.close(fig)

    write_lines_as_fragment(
        out_fig_path,
        [
            r"\centering",
            rf"\includegraphics[width=0.98\linewidth]{{artifacts/export/{out_png}}}",
        ],
    )

    manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, [out_png, out_fig])
    write_manifest(run.run_dir, manifest)

    copy_atomic(out_png_path, export_dir() / out_png)
    copy_atomic(out_fig_path, generated_dir() / out_fig)
    print("[fig_observer_bubble_graph_m6] done", flush=True)


if __name__ == "__main__":
    main()

