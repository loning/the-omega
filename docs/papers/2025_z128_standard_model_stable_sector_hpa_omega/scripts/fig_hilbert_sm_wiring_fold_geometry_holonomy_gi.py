# -*- coding: utf-8 -*-
"""
Render the concrete wiring/folding geometry for the best candidate from the holonomy+GI search.

Reads:
  figures/adaptive/sm_hilbert_isomorphism/data/sm_hilbert_holonomy_gi_search_report.json

Outputs:
  figures/adaptive/sm_hilbert_isomorphism/wiring_fold_geometry_holonomy_gi/
    - wiring_2d.svg
    - wiring_3d_xy.svg
    - wiring_3d_xz.svg
    - wiring_3d_yz.svg
    - wiring_geometry.json

Notes:
  - English-only output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt

from common_paths import figures_dir
from hilbert_sm_center_graph import BuildConstraints, build_center_graph_fixed


def _read_best_candidate() -> Dict[str, Any]:
    in_json = (
        figures_dir()
        / "adaptive"
        / "sm_hilbert_isomorphism"
        / "data"
        / "sm_hilbert_holonomy_gi_search_report.json"
    )
    obj = json.loads(in_json.read_text(encoding="utf-8"))
    bm = obj.get("best_match")
    if isinstance(bm, dict):
        return bm
    best = obj.get("best")
    if not isinstance(best, dict):
        raise RuntimeError("No best/best_match in report (run exp_hilbert_sm_search_holonomy_gi.py first).")
    return best


def _as_int_dict(d: Dict[str, Any]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for k, v in d.items():
        out[int(k)] = int(v)
    return out


def _plot_polyline_2d(xs: List[float], ys: List[float], out_path: Path, title: str) -> None:
    fig = plt.figure(figsize=(8, 8), dpi=180)
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(xs, ys, "-", lw=0.7, alpha=0.9)
    ax.scatter(xs, ys, s=2.0, alpha=0.9)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(out_path, format="svg")
    plt.close(fig)


def _extract_segments(points: List[Tuple[float, ...]]) -> List[Tuple[Tuple[float, ...], Tuple[float, ...]]]:
    segs: List[Tuple[Tuple[float, ...], Tuple[float, ...]]] = []
    for a, b in zip(points[:-1], points[1:]):
        segs.append((tuple(float(x) for x in a), tuple(float(x) for x in b)))
    return segs


def main() -> None:
    cand = _read_best_candidate()
    m_sched = _as_int_dict(cand.get("m_schedule_by_k", {}))
    choice2 = _as_int_dict(cand.get("choice2", {}))
    choice3 = _as_int_dict(cand.get("choice3", {}))
    cons_d = cand.get("constraints", {})
    cons = BuildConstraints(
        enforce_edge_types=bool(cons_d.get("enforce_edge_types", False)),
        enforce_noncrossing_xy=bool(cons_d.get("enforce_noncrossing_xy", False)),
        forbid_passing_through_centers=bool(cons_d.get("forbid_passing_through_centers", False)),
    )

    out_dir = figures_dir() / "adaptive" / "sm_hilbert_isomorphism" / "wiring_fold_geometry_holonomy_gi"
    out_dir.mkdir(parents=True, exist_ok=True)

    g2 = build_center_graph_fixed(dim=2, m_by_k=m_sched, chosen_micro_option=choice2, max_micro_orders=16, constraints=cons)
    g3 = build_center_graph_fixed(dim=3, m_by_k=m_sched, chosen_micro_option=choice3, max_micro_orders=48, constraints=cons)

    pts2 = [g2.nodes[int(nid)].pt for nid in g2.scan_path]
    xs2 = [float(p[0]) for p in pts2]
    ys2 = [float(p[1]) for p in pts2]
    _plot_polyline_2d(xs2, ys2, out_dir / "wiring_2d.svg", title="Wiring/Folding geometry (2D) [holonomy-GI best]")

    pts3 = [g3.nodes[int(nid)].pt for nid in g3.scan_path]
    xs3 = [float(p[0]) for p in pts3]
    ys3 = [float(p[1]) for p in pts3]
    zs3 = [float(p[2]) for p in pts3]
    _plot_polyline_2d(xs3, ys3, out_dir / "wiring_3d_xy.svg", title="Wiring/Folding geometry (3D, XY projection) [holonomy-GI best]")
    _plot_polyline_2d(xs3, zs3, out_dir / "wiring_3d_xz.svg", title="Wiring/Folding geometry (3D, XZ projection) [holonomy-GI best]")
    _plot_polyline_2d(ys3, zs3, out_dir / "wiring_3d_yz.svg", title="Wiring/Folding geometry (3D, YZ projection) [holonomy-GI best]")

    geo = {
        "source": {
            "report": "sm_hilbert_holonomy_gi_search_report.json",
            "picked": "best_match" if isinstance(cand, dict) and cand is cand else "best",
            "score": float(cand.get("score", float("nan"))),
            "rep_distance_L1": float(cand.get("rep_distance_L1", float("nan"))),
            "sep2_col_minus_ncol_120": float(cand.get("sep2_col_minus_ncol_120", float("nan"))),
            "sep3_col_minus_ncol_120": float(cand.get("sep3_col_minus_ncol_120", float("nan"))),
            "pi2_doublet_minus_singlet_180": float(cand.get("pi2_doublet_minus_singlet_180", float("nan"))),
            "pi3_doublet_minus_singlet_180": float(cand.get("pi3_doublet_minus_singlet_180", float("nan"))),
            "type_sig": str(cand.get("type_sig", "")),
        },
        "constraints": {
            "enforce_edge_types": cons.enforce_edge_types,
            "enforce_noncrossing_xy": cons.enforce_noncrossing_xy,
            "forbid_passing_through_centers": cons.forbid_passing_through_centers,
        },
        "m_schedule_by_k": {str(k): int(v) for k, v in sorted(m_sched.items())},
        "choice2": {str(k): int(v) for k, v in sorted(choice2.items())},
        "choice3": {str(k): int(v) for k, v in sorted(choice3.items())},
        "graph2d": {
            "n_nodes": len(g2.nodes),
            "scan_path_node_ids": [int(x) for x in g2.scan_path],
            "segments": [([a[0], a[1]], [b[0], b[1]]) for a, b in _extract_segments(pts2)],
            "nodes": [
                {
                    "id": int(n.id),
                    "k_coarse": int(n.k_coarse),
                    "m": int(n.m),
                    "pt": [float(n.pt[0]), float(n.pt[1])],
                    "u6": n.u6,
                    "label": n.label_tex,
                    "rep": n.rep_tex,
                    "is_boundary": bool(n.is_boundary),
                }
                for n in g2.nodes
            ],
        },
        "graph3d": {
            "n_nodes": len(g3.nodes),
            "scan_path_node_ids": [int(x) for x in g3.scan_path],
            "segments": [([a[0], a[1], a[2]], [b[0], b[1], b[2]]) for a, b in _extract_segments(pts3)],
            "nodes": [
                {
                    "id": int(n.id),
                    "k_coarse": int(n.k_coarse),
                    "m": int(n.m),
                    "pt": [float(n.pt[0]), float(n.pt[1]), float(n.pt[2])],
                    "u6": n.u6,
                    "label": n.label_tex,
                    "rep": n.rep_tex,
                    "is_boundary": bool(n.is_boundary),
                }
                for n in g3.nodes
            ],
        },
    }
    (out_dir / "wiring_geometry.json").write_text(json.dumps(geo, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Wrote {out_dir / 'wiring_2d.svg'}")
    print(f"Wrote {out_dir / 'wiring_3d_xy.svg'}")
    print(f"Wrote {out_dir / 'wiring_3d_xz.svg'}")
    print(f"Wrote {out_dir / 'wiring_3d_yz.svg'}")
    print(f"Wrote {out_dir / 'wiring_geometry.json'}")


if __name__ == "__main__":
    main()

