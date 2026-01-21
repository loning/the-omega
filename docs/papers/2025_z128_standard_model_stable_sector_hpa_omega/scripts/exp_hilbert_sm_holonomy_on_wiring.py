# -*- coding: utf-8 -*-
"""
Holonomy diagnostics on the *concrete wiring geometry* (center nodes), for SU(2)/SU(3)-level analysis.

We treat the wiring as giving a set of center nodes with stable type labels (u6),
embed them on an integer lattice (by doubling coordinates), build an axis-neighbor adjacency,
enumerate elementary plaquettes (2D squares / 3D face squares), and compute:
  - S4-valued transport on each adjacency edge via minimum-cost fiber matching (same as exp_holonomy_loops)
  - plaquette holonomy cycle types
  - SU(3) SO(3) rotation-angle proxy via exp_holonomy_su3_representation.su3_rep
  - SU(2) Wilson-loop proxy by lifting SO(3) axis-angle to SU(2) trace (spin-1/2 double cover)

Outputs JSON under:
  figures/adaptive/sm_hilbert_isomorphism/wiring_fold_geometry/holonomy_report.json
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import exp_holonomy_loops as holo
import exp_holonomy_su3_representation as su3rep
from common_paths import figures_dir
from hilbert_sm_holonomy import _best_perm_with_ports


Perm = Tuple[int, int, int, int]


def _read_wiring(wiring_dir: Path) -> Dict:
    p = wiring_dir / "wiring_geometry.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _pt2_key(pt: List[float]) -> Tuple[int, int]:
    # center points are half-integers; multiply by 2 -> odd integers
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


def _axis_neighbors_3d(pos: Dict[Tuple[int, int, int], int], step: int = 2) -> List[Tuple[int, int]]:
    edges: List[Tuple[int, int]] = []
    for (x, y, z), a in pos.items():
        for dx, dy, dz in ((step, 0, 0), (0, step, 0), (0, 0, step)):
            b = pos.get((x + dx, y + dy, z + dz))
            if b is None:
                continue
            edges.append((int(a), int(b)))
    return edges


def _plaquettes_2d(pos: Dict[Tuple[int, int], int], step: int = 2) -> List[Tuple[int, int, int, int]]:
    # return cycles (a,b,c,d) for squares a->b->c->d->a
    pls: List[Tuple[int, int, int, int]] = []
    for (x, y), a in pos.items():
        b = pos.get((x + step, y))
        c = pos.get((x + step, y + step))
        d = pos.get((x, y + step))
        if b is None or c is None or d is None:
            continue
        pls.append((int(a), int(b), int(c), int(d)))
    return pls


def _plaquettes_3d(pos: Dict[Tuple[int, int, int], int], step: int = 2) -> List[Tuple[int, int, int, int, str]]:
    # return (a,b,c,d,plane) squares in xy/xz/yz planes
    pls: List[Tuple[int, int, int, int, str]] = []
    for (x, y, z), a in pos.items():
        # xy
        b = pos.get((x + step, y, z))
        c = pos.get((x + step, y + step, z))
        d = pos.get((x, y + step, z))
        if b is not None and c is not None and d is not None:
            pls.append((int(a), int(b), int(c), int(d), "xy"))
        # xz
        b = pos.get((x + step, y, z))
        c = pos.get((x + step, y, z + step))
        d = pos.get((x, y, z + step))
        if b is not None and c is not None and d is not None:
            pls.append((int(a), int(b), int(c), int(d), "xz"))
        # yz
        b = pos.get((x, y + step, z))
        c = pos.get((x, y + step, z + step))
        d = pos.get((x, y, z + step))
        if b is not None and c is not None and d is not None:
            pls.append((int(a), int(b), int(c), int(d), "yz"))
    return pls


def _edge_perm_cache_for_nodes(nodes: List[Dict], edges: List[Tuple[int, int]]) -> Dict[Tuple[int, int], Perm]:
    pre = holo.preimages()
    # Build oriented edge permutation for each adjacency edge using u6 labels,
    # with rep-aware port constraints (SU3/SU2/Y injected into the connection).
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


def _so3_to_su2_trace(R: List[List[float]]) -> float:
    """
    Lift SO(3) rotation matrix to SU(2) trace proxy: tr(U) = 2 cos(theta/2).
    We extract theta from trace(R)=1+2cos(theta).
    """
    tr = float(R[0][0] + R[1][1] + R[2][2])
    x = 0.5 * (tr - 1.0)
    x = max(-1.0, min(1.0, x))
    theta = math.acos(x)  # in [0,pi]
    return 2.0 * math.cos(0.5 * theta)


def _holonomy_on_plaquettes_2d(nodes: List[Dict], pos: Dict[Tuple[int, int], int]) -> Dict:
    edges = _axis_neighbors_2d(pos)
    edge_p = _edge_perm_cache_for_nodes(nodes, edges)
    B = su3rep.basis_B()

    hist_ct = Counter()
    angles_by_ct: Dict[str, List[float]] = defaultdict(list)
    su2_trace_by_ct: Dict[str, List[float]] = defaultdict(list)
    # Per-SM label aggregation (18 fermions + 3 gauge classes in label_tex).
    per_label_ct: Dict[str, Counter] = defaultdict(Counter)
    per_label_angles: Dict[str, List[float]] = defaultdict(list)
    per_label_su2_trace: Dict[str, List[float]] = defaultdict(list)

    pls = _plaquettes_2d(pos)
    for a, b, c, d in pls:
        # a->b->c->d->a
        p_ab = edge_p[(a, b)]
        p_bc = edge_p[(b, c)]
        p_cd = edge_p[(c, d)]
        p_da = edge_p[(d, a)]
        hol = holo.compose(p_da, holo.compose(p_cd, holo.compose(p_bc, p_ab)))
        ct = holo.cycle_type(hol)
        hist_ct[ct] += 1

        R = su3rep.su3_rep(hol, B=B)
        ang = su3rep.rotation_angle_deg(R)
        angles_by_ct[ct].append(float(ang))
        su2_trace_by_ct[ct].append(float(_so3_to_su2_trace(R)))

        # Attribute this plaquette holonomy to its corner labels.
        corners = [a, b, c, d]
        for nid in corners:
            lab = str(nodes[int(nid)]["label"])
            per_label_ct[lab][ct] += 1
            per_label_angles[lab].append(float(ang))
            per_label_su2_trace[lab].append(float(_so3_to_su2_trace(R)))

    return {
        "n_nodes": len(nodes),
        "n_edges_axis": len(edges),
        "n_plaquettes": len(pls),
        "cycle_type_hist": dict(hist_ct),
        "su3_angle_deg_by_cycle_type": {ct: {"count": len(xs), "mean": sum(xs) / len(xs), "min": min(xs), "max": max(xs)} for ct, xs in angles_by_ct.items()},
        "su2_trace_by_cycle_type": {ct: {"count": len(xs), "mean": sum(xs) / len(xs), "min": min(xs), "max": max(xs)} for ct, xs in su2_trace_by_ct.items()},
        "per_label": {
            lab: {
                "n_incident_plaquettes": int(sum(per_label_ct[lab].values())),
                "cycle_type_hist": dict(per_label_ct[lab]),
                "su3_angle_deg": {
                    "count": int(len(per_label_angles[lab])),
                    "mean": float(sum(per_label_angles[lab]) / len(per_label_angles[lab])) if per_label_angles[lab] else float("nan"),
                    "min": float(min(per_label_angles[lab])) if per_label_angles[lab] else float("nan"),
                    "max": float(max(per_label_angles[lab])) if per_label_angles[lab] else float("nan"),
                },
                "su2_trace": {
                    "count": int(len(per_label_su2_trace[lab])),
                    "mean": float(sum(per_label_su2_trace[lab]) / len(per_label_su2_trace[lab])) if per_label_su2_trace[lab] else float("nan"),
                    "min": float(min(per_label_su2_trace[lab])) if per_label_su2_trace[lab] else float("nan"),
                    "max": float(max(per_label_su2_trace[lab])) if per_label_su2_trace[lab] else float("nan"),
                },
            }
            for lab in sorted(per_label_ct.keys())
        },
    }


def _holonomy_on_plaquettes_3d(nodes: List[Dict], pos: Dict[Tuple[int, int, int], int]) -> Dict:
    edges = _axis_neighbors_3d(pos)
    edge_p = _edge_perm_cache_for_nodes(nodes, edges)
    B = su3rep.basis_B()

    hist_ct = Counter()
    hist_plane = Counter()
    angles_by_ct: Dict[str, List[float]] = defaultdict(list)
    su2_trace_by_ct: Dict[str, List[float]] = defaultdict(list)
    per_label_ct: Dict[str, Counter] = defaultdict(Counter)
    per_label_angles: Dict[str, List[float]] = defaultdict(list)
    per_label_su2_trace: Dict[str, List[float]] = defaultdict(list)

    pls = _plaquettes_3d(pos)
    for a, b, c, d, plane in pls:
        p_ab = edge_p[(a, b)]
        p_bc = edge_p[(b, c)]
        p_cd = edge_p[(c, d)]
        p_da = edge_p[(d, a)]
        hol = holo.compose(p_da, holo.compose(p_cd, holo.compose(p_bc, p_ab)))
        ct = holo.cycle_type(hol)
        hist_ct[ct] += 1
        hist_plane[plane] += 1

        R = su3rep.su3_rep(hol, B=B)
        ang = su3rep.rotation_angle_deg(R)
        angles_by_ct[ct].append(float(ang))
        su2_trace_by_ct[ct].append(float(_so3_to_su2_trace(R)))

        corners = [a, b, c, d]
        for nid in corners:
            lab = str(nodes[int(nid)]["label"])
            per_label_ct[lab][ct] += 1
            per_label_angles[lab].append(float(ang))
            per_label_su2_trace[lab].append(float(_so3_to_su2_trace(R)))

    return {
        "n_nodes": len(nodes),
        "n_edges_axis": len(edges),
        "n_plaquettes": len(pls),
        "plane_hist": dict(hist_plane),
        "cycle_type_hist": dict(hist_ct),
        "su3_angle_deg_by_cycle_type": {ct: {"count": len(xs), "mean": sum(xs) / len(xs), "min": min(xs), "max": max(xs)} for ct, xs in angles_by_ct.items()},
        "su2_trace_by_cycle_type": {ct: {"count": len(xs), "mean": sum(xs) / len(xs), "min": min(xs), "max": max(xs)} for ct, xs in su2_trace_by_ct.items()},
        "per_label": {
            lab: {
                "n_incident_plaquettes": int(sum(per_label_ct[lab].values())),
                "cycle_type_hist": dict(per_label_ct[lab]),
                "su3_angle_deg": {
                    "count": int(len(per_label_angles[lab])),
                    "mean": float(sum(per_label_angles[lab]) / len(per_label_angles[lab])) if per_label_angles[lab] else float("nan"),
                    "min": float(min(per_label_angles[lab])) if per_label_angles[lab] else float("nan"),
                    "max": float(max(per_label_angles[lab])) if per_label_angles[lab] else float("nan"),
                },
                "su2_trace": {
                    "count": int(len(per_label_su2_trace[lab])),
                    "mean": float(sum(per_label_su2_trace[lab]) / len(per_label_su2_trace[lab])) if per_label_su2_trace[lab] else float("nan"),
                    "min": float(min(per_label_su2_trace[lab])) if per_label_su2_trace[lab] else float("nan"),
                    "max": float(max(per_label_su2_trace[lab])) if per_label_su2_trace[lab] else float("nan"),
                },
            }
            for lab in sorted(per_label_ct.keys())
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--wiring-dir",
        type=str,
        default=str(figures_dir() / "adaptive" / "sm_hilbert_isomorphism" / "wiring_fold_geometry"),
        help="Directory containing wiring_geometry.json (and where outputs will be written).",
    )
    args = ap.parse_args()

    wiring_dir = Path(str(args.wiring_dir))
    obj = _read_wiring(wiring_dir)
    g2_nodes = obj["graph2d"]["nodes"]
    g3_nodes = obj["graph3d"]["nodes"]

    pos2: Dict[Tuple[int, int], int] = {}
    for n in g2_nodes:
        pos2[_pt2_key(n["pt"])] = int(n["id"])

    pos3: Dict[Tuple[int, int, int], int] = {}
    for n in g3_nodes:
        pos3[_pt3_key(n["pt"])] = int(n["id"])

    rep2 = _holonomy_on_plaquettes_2d(g2_nodes, pos2)
    rep3 = _holonomy_on_plaquettes_3d(g3_nodes, pos3)

    out = {
        "constraints": obj.get("constraints", {}),
        "m_schedule_by_k": obj.get("m_schedule_by_k", {}),
        "summary": {
            "2d": rep2,
            "3d": rep3,
        },
    }

    out_path = wiring_dir / "holonomy_report.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

