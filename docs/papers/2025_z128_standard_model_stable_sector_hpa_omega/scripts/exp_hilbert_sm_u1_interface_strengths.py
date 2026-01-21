# -*- coding: utf-8 -*-
"""
U(1) interface strengths on cross-m scan edges (wiring -> audit report).

We treat scan edges where m changes (m(a)!=m(b)) as "interface events".
On each such edge, we compute a port-compatible transport permutation p (same rule as holonomy)
and then extract U(1)-only port statistics:

  flow_u1 := number of matched fiber pairs where both have concrete u1 labels (not None)
  mis_u1  := number of those pairs where u1 labels differ

We also compute the full Hamming mismatch cost under the chosen p for context.

Outputs (written under the wiring dir):
  - u1_interface_strengths.json

English-only output (repo convention).
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import exp_holonomy_loops as holo
from hilbert_sm_holonomy import _best_perm_with_ports, _port_label


Perm = Tuple[int, int, int, int]


def _read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _perm_cost_hamming_on_fibers(fa: List[int], fb: List[int], p: Perm) -> int:
    a_bits = [holo.bits6(x) for x in fa]
    b_bits = [holo.bits6(x) for x in fb]
    cost = 0
    for i in range(4):
        cost += int(holo.hamming(a_bits[i], b_bits[int(p[i])]))
    return int(cost)


def _parse_rep_key(rep_tex: str) -> str:
    # Normalize to "(su3,su2)_Y" like other reports; fallback to "gauge_or_unknown".
    s = str(rep_tex).strip()
    if s in ("$-$", "-"):
        return "gauge_or_unknown"
    # expected "$(3,2)_{1/6}$"
    try:
        a = s.split("(")[1].split(")")[0]
        su3 = int(a.split(",")[0].strip())
        su2 = int(a.split(",")[1].strip())
        y = s.split("_{", 1)[1].split("}", 1)[0].strip()
        return f"({su3},{su2})_{y}"
    except Exception:
        return "gauge_or_unknown"


@dataclass(frozen=True)
class EdgeU1:
    a: int
    b: int
    ma: int
    mb: int
    rep_a: str
    rep_b: str
    rep_key_a: str
    rep_key_b: str
    flow_u1: int
    mis_u1: int
    hamming_cost: int


def _analyze_graph(nodes: List[Dict[str, Any]], scan_ids: List[int]) -> Dict[str, Any]:
    id_to_node: Dict[int, Dict[str, Any]] = {int(n.get("id")): n for n in nodes if "id" in n}
    pre = holo.preimages()

    edges: List[EdgeU1] = []
    for a, b in zip(scan_ids[:-1], scan_ids[1:]):
        na = id_to_node.get(int(a))
        nb = id_to_node.get(int(b))
        if na is None or nb is None:
            continue
        ma = int(na.get("m", 6))
        mb = int(nb.get("m", 6))
        if ma == mb:
            continue

        ua = str(na.get("u6", ""))
        ub = str(nb.get("u6", ""))
        rep_a = str(na.get("rep", "$-$"))
        rep_b = str(nb.get("rep", "$-$"))
        rep_key_a = _parse_rep_key(rep_a)
        rep_key_b = _parse_rep_key(rep_b)
        fa = holo.fiber4(pre, ua)
        fb = holo.fiber4(pre, ub)
        p = _best_perm_with_ports(fa, fb, rep_a, rep_b)

        pa = [_port_label(int(x), rep_a) for x in fa]
        pb = [_port_label(int(x), rep_b) for x in fb]
        flow_u1 = 0
        mis_u1 = 0
        for i in range(4):
            qa = pa[i][2]
            qb = pb[int(p[i])][2]
            if qa is None or qb is None:
                continue
            flow_u1 += 1
            if int(qa) != int(qb):
                mis_u1 += 1

        edges.append(
            EdgeU1(
                a=int(a),
                b=int(b),
                ma=int(ma),
                mb=int(mb),
                rep_a=rep_a,
                rep_b=rep_b,
                rep_key_a=rep_key_a,
                rep_key_b=rep_key_b,
                flow_u1=int(flow_u1),
                mis_u1=int(mis_u1),
                hamming_cost=int(_perm_cost_hamming_on_fibers(fa, fb, p)),
            )
        )

    # Aggregate by endpoint rep keys (attribute edge to both ends).
    by_rep: Dict[str, Dict[str, float]] = defaultdict(lambda: {"n_edges_incident": 0.0, "flow_u1": 0.0, "mis_u1": 0.0, "hamming_cost": 0.0})
    for e in edges:
        for rk in (e.rep_key_a, e.rep_key_b):
            by_rep[rk]["n_edges_incident"] += 1.0
            by_rep[rk]["flow_u1"] += float(e.flow_u1)
            by_rep[rk]["mis_u1"] += float(e.mis_u1)
            by_rep[rk]["hamming_cost"] += float(e.hamming_cost)

    # Totals
    tot_flow = sum(e.flow_u1 for e in edges)
    tot_mis = sum(e.mis_u1 for e in edges)
    tot_ham = sum(e.hamming_cost for e in edges)

    return {
        "n_nodes": int(len(nodes)),
        "n_scan_edges": int(max(0, len(scan_ids) - 1)),
        "n_cross_m_edges": int(len(edges)),
        "totals": {"flow_u1": int(tot_flow), "mis_u1": int(tot_mis), "hamming_cost": int(tot_ham)},
        "by_rep_key": {k: {kk: (int(v) if kk in ("n_edges_incident",) else float(v)) for kk, v in obj.items()} for k, obj in by_rep.items()},
        "edges": [
            {
                "a": e.a,
                "b": e.b,
                "m_a": e.ma,
                "m_b": e.mb,
                "rep_key_a": e.rep_key_a,
                "rep_key_b": e.rep_key_b,
                "flow_u1": e.flow_u1,
                "mis_u1": e.mis_u1,
                "hamming_cost": e.hamming_cost,
            }
            for e in edges
        ],
    }

def _coarse_project(nodes: List[Dict[str, Any]], scan_ids: List[int]) -> Tuple[List[Dict[str, Any]], List[int]]:
    """
    Collapse micro nodes into coarse cells (id := k_coarse) and collapse scan accordingly.
    """
    id_to_k: Dict[int, int] = {}
    rep_by_k: Dict[int, Dict[str, Any]] = {}
    for n in nodes:
        if "id" not in n or "k_coarse" not in n:
            continue
        nid = int(n["id"])
        k = int(n["k_coarse"])
        id_to_k[nid] = k
        if k not in rep_by_k:
            rep = dict(n)
            rep["id"] = int(k)
            rep_by_k[int(k)] = rep

    scan_k: List[int] = []
    prev: int | None = None
    for nid in scan_ids:
        k = id_to_k.get(int(nid))
        if k is None:
            continue
        if prev is None or int(k) != int(prev):
            scan_k.append(int(k))
            prev = int(k)
    coarse_nodes = [rep_by_k[k] for k in sorted(rep_by_k.keys())]
    return coarse_nodes, scan_k


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiring-dir", type=str, required=True, help="Directory containing wiring_geometry.json")
    args = ap.parse_args()

    wdir = Path(str(args.wiring_dir))
    geo = _read_json(wdir / "wiring_geometry.json")

    out: Dict[str, Any] = {"wiring_dir": str(wdir)}
    for key in ("graph2d", "graph3d"):
        g = geo.get(key, {})
        nodes = list(g.get("nodes", []))
        scan_ids = [int(x) for x in g.get("scan_path_node_ids", [])]
        coarse_nodes, coarse_scan = _coarse_project(nodes, scan_ids)
        out[key] = {
            "selected": "coarse",
            "coarse": _analyze_graph(coarse_nodes, coarse_scan),
            "micro": _analyze_graph(nodes, scan_ids),
        }

    out_path = wdir / "u1_interface_strengths.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

