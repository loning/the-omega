# -*- coding: utf-8 -*-
"""
Holonomy utilities on center-node geometries (2D/3D), aligned with the paper's S4 transport construction.

This module is designed for *search-time* evaluation:
  - build axis-neighbor adjacency from center points
  - enumerate elementary plaquettes
  - compute S4 holonomy and map to SO(3) rotation angles (SU(3) proxy)
  - compute SU(2) trace proxy via 2 cos(theta/2)
  - aggregate by label and by representation key

Pure standard library + existing repo scripts (exp_holonomy_*).
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import exp_holonomy_loops as holo
import exp_holonomy_su3_representation as su3rep


Perm = Tuple[int, int, int, int]

def _rep_components(rep_tex: str) -> Tuple[int, int, int, int] | None:
    """
    Parse rep_tex like "$(3,2)_{1/6}$" into (su3_dim, su2_dim, y_num, y_den).
    Returns None for gauge/unknown.
    """
    s = str(rep_tex).strip()
    if s in ("$-$", "-"):
        return None
    m = re.search(r"\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*_\{\s*([^\}]+)\s*\}", s)
    if not m:
        return None
    su3 = int(m.group(1))
    su2 = int(m.group(2))
    y_raw = m.group(3).strip()
    if "/" in y_raw:
        a, b = y_raw.split("/", 1)
        y_num = int(a.strip())
        y_den = int(b.strip())
    else:
        y_num = int(y_raw)
        y_den = 1
    # normalize sign
    if y_den < 0:
        y_den = -y_den
        y_num = -y_num
    return (su3, su2, y_num, y_den)


def _rep_key(rep_tex: str) -> str:
    c = _rep_components(rep_tex)
    if c is None:
        return "gauge_or_unknown"
    su3, su2, y_num, y_den = c
    y = f"{y_num}" if y_den == 1 else f"{y_num}/{y_den}"
    return f"({su3},{su2})_{y}"

def _port_label(idx6: int, rep_tex: str) -> Tuple[int | None, int | None, int | None]:
    """
    Assign a (color, isospin, u1) port label to a micro index under a rep.
    Components are None when the rep is a singlet / trivial in that channel (wildcard).

    This is a *deterministic port decomposition* that injects (SU3,SU2,Y) into the allowed matchings.
    """
    comp = _rep_components(rep_tex)
    if comp is None:
        return (None, None, None)
    su3, su2, y_num, _y_den = comp
    # small deterministic salt from rep (stable within a run)
    salt = (abs(hash(_rep_key(rep_tex))) % 64)
    c3: int | None
    c2: int | None
    q: int | None
    if su3 == 3:
        c3 = int((int(idx6) + int(salt)) % 3)
    else:
        c3 = None
    if su2 == 2:
        c2 = int(((int(idx6) >> 0) & 1) ^ (int(salt) & 1))
    else:
        c2 = None
    if y_num != 0:
        q = int(((int(idx6) >> 1) & 1) ^ (1 if int(y_num) < 0 else 0))
    else:
        q = None
    return (c3, c2, q)


def _ports_compatible(a: Tuple[int | None, int | None, int | None], b: Tuple[int | None, int | None, int | None]) -> bool:
    for x, y in zip(a, b):
        if x is None or y is None:
            continue
        if int(x) != int(y):
            return False
    return True


def _best_perm_with_ports(fa: List[int], fb: List[int], rep_a: str, rep_b: str) -> Perm:
    """
    Choose the minimum-Hamming permutation subject to port-compatibility.
    Falls back to unconstrained matching if no port-compatible permutation exists.
    """
    a_bits = [holo.bits6(x) for x in fa]
    b_bits = [holo.bits6(x) for x in fb]
    pa = [_port_label(x, rep_a) for x in fa]
    pb = [_port_label(x, rep_b) for x in fb]
    best: Tuple[int, Perm] | None = None
    import itertools

    for p in itertools.permutations((0, 1, 2, 3), 4):
        ok = True
        for i in range(4):
            if not _ports_compatible(pa[i], pb[p[i]]):
                ok = False
                break
        if not ok:
            continue
        cost = 0
        for i in range(4):
            cost += holo.hamming(a_bits[i], b_bits[p[i]])
        cand = (cost, p)
        if best is None or cand < best:
            best = cand
    if best is None:
        return holo.best_perm(fa, fb)
    return best[1]



def _pt2_key(pt: Tuple[float, float]) -> Tuple[int, int]:
    return (int(round(2.0 * float(pt[0]))), int(round(2.0 * float(pt[1]))))


def _pt3_key(pt: Tuple[float, float, float]) -> Tuple[int, int, int]:
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


def _edge_perm_cache_for_nodes(nodes: List[Dict[str, Any]], edges: List[Tuple[int, int]]) -> Dict[Tuple[int, int], Perm]:
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


def _so3_to_su2_trace(R: List[List[float]]) -> float:
    tr = float(R[0][0] + R[1][1] + R[2][2])
    x = 0.5 * (tr - 1.0)
    x = max(-1.0, min(1.0, x))
    theta = math.acos(x)
    return 2.0 * math.cos(0.5 * theta)


def _parse_rep_tex(rep_tex: str) -> str:
    # Normalize rep_tex to a key like "(3,2)_1/6"; keep gauge as "gauge_or_unknown"
    s = str(rep_tex).strip()
    if s in ("$-$", "-"):
        return "gauge_or_unknown"
    m = re.search(r"\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*_\{\s*([^\}]+)\s*\}", s)
    if not m:
        return "gauge_or_unknown"
    su3 = int(m.group(1))
    su2 = int(m.group(2))
    y = m.group(3).strip()
    return f"({su3},{su2})_{y}"


def _cycle_hist_to_angle_hist(ct_hist: Dict[str, int]) -> Dict[str, int]:
    h = {str(k): int(v) for k, v in ct_hist.items()}
    return {
        "0": int(h.get("1", 0)),
        "90": int(h.get("4", 0)),
        "120": int(h.get("3", 0)),
        "180": int(h.get("2", 0)) + int(h.get("2x2", 0)),
    }


def _normalize_hist(h: Dict[str, int]) -> Dict[str, float]:
    tot = float(sum(int(v) for v in h.values()))
    if tot <= 0:
        return {k: float("nan") for k in h}
    return {k: float(v) / tot for k, v in h.items()}


@dataclass(frozen=True)
class HolonomySummary:
    n_nodes: int
    n_edges_axis: int
    n_plaquettes: int
    cycle_type_hist: Dict[str, int]
    angle_hist: Dict[str, int]
    angle_frac: Dict[str, float]
    su2_trace_mean: float
    per_rep_angle_frac: Dict[str, Dict[str, float]]  # rep_key -> angle_frac


def holonomy_summary_from_geometry_2d(nodes: List[Dict[str, Any]]) -> HolonomySummary:
    pos: Dict[Tuple[int, int], int] = {}
    for n in nodes:
        pos[_pt2_key(tuple(n["pt"]))] = int(n["id"])
    edges = _axis_neighbors_2d(pos)
    edge_p = _edge_perm_cache_for_nodes(nodes, edges)
    pls = _plaquettes_2d(pos)
    B = su3rep.basis_B()

    hist_ct = Counter()
    su2_traces: List[float] = []
    per_rep_ct: Dict[str, Counter] = defaultdict(Counter)

    for a, b, c, d in pls:
        p_ab = edge_p[(a, b)]
        p_bc = edge_p[(b, c)]
        p_cd = edge_p[(c, d)]
        p_da = edge_p[(d, a)]
        hol = holo.compose(p_da, holo.compose(p_cd, holo.compose(p_bc, p_ab)))
        ct = holo.cycle_type(hol)
        hist_ct[ct] += 1
        R = su3rep.su3_rep(hol, B=B)
        su2_traces.append(float(_so3_to_su2_trace(R)))
        # attribute to reps of corners
        for nid in (a, b, c, d):
            rep_key = _parse_rep_tex(str(nodes[int(nid)].get("rep", "$-$")))
            per_rep_ct[rep_key][ct] += 1

    angle_hist = _cycle_hist_to_angle_hist(dict(hist_ct))
    per_rep_angle_frac = {k: _normalize_hist(_cycle_hist_to_angle_hist(dict(c))) for k, c in per_rep_ct.items()}
    return HolonomySummary(
        n_nodes=len(nodes),
        n_edges_axis=len(edges),
        n_plaquettes=len(pls),
        cycle_type_hist=dict(hist_ct),
        angle_hist=angle_hist,
        angle_frac=_normalize_hist(angle_hist),
        su2_trace_mean=float(sum(su2_traces) / len(su2_traces)) if su2_traces else float("nan"),
        per_rep_angle_frac=per_rep_angle_frac,
    )


def holonomy_summary_from_geometry_3d(nodes: List[Dict[str, Any]]) -> HolonomySummary:
    pos: Dict[Tuple[int, int, int], int] = {}
    for n in nodes:
        pos[_pt3_key(tuple(n["pt"]))] = int(n["id"])
    edges = _axis_neighbors_3d(pos)
    edge_p = _edge_perm_cache_for_nodes(nodes, edges)
    pls = _plaquettes_3d(pos)
    B = su3rep.basis_B()

    hist_ct = Counter()
    su2_traces: List[float] = []
    per_rep_ct: Dict[str, Counter] = defaultdict(Counter)

    for a, b, c, d, _plane in pls:
        p_ab = edge_p[(a, b)]
        p_bc = edge_p[(b, c)]
        p_cd = edge_p[(c, d)]
        p_da = edge_p[(d, a)]
        hol = holo.compose(p_da, holo.compose(p_cd, holo.compose(p_bc, p_ab)))
        ct = holo.cycle_type(hol)
        hist_ct[ct] += 1
        R = su3rep.su3_rep(hol, B=B)
        su2_traces.append(float(_so3_to_su2_trace(R)))
        for nid in (a, b, c, d):
            rep_key = _parse_rep_tex(str(nodes[int(nid)].get("rep", "$-$")))
            per_rep_ct[rep_key][ct] += 1

    angle_hist = _cycle_hist_to_angle_hist(dict(hist_ct))
    per_rep_angle_frac = {k: _normalize_hist(_cycle_hist_to_angle_hist(dict(c))) for k, c in per_rep_ct.items()}
    return HolonomySummary(
        n_nodes=len(nodes),
        n_edges_axis=len(edges),
        n_plaquettes=len(pls),
        cycle_type_hist=dict(hist_ct),
        angle_hist=angle_hist,
        angle_frac=_normalize_hist(angle_hist),
        su2_trace_mean=float(sum(su2_traces) / len(su2_traces)) if su2_traces else float("nan"),
        per_rep_angle_frac=per_rep_angle_frac,
    )


@dataclass(frozen=True)
class TypeGraphHolonomySummary:
    """
    Holonomy computed on the induced type-graph (X6 nodes) with short cycles.
    """

    n_types: int
    n_edges_undirected: int
    n_cycles: int
    cycle_len_hist: Dict[int, int]
    cycle_type_hist: Dict[str, int]
    angle_hist: Dict[str, int]
    angle_frac: Dict[str, float]
    per_rep_angle_frac: Dict[str, Dict[str, float]]
    per_rep_count: Dict[str, int]


def _simple_cycles_len_k(adj: Dict[int, List[int]], k: int) -> List[List[int]]:
    """
    Enumerate simple cycles of length k in an undirected graph using a canonical start rule.
    k is small (3 or 4); this is safe for <=21 nodes.
    """
    if k < 3:
        return []
    cycles: List[List[int]] = []
    nodes = sorted(adj.keys())
    for start in nodes:
        stack: List[Tuple[int, List[int]]] = [(start, [start])]
        while stack:
            v, path = stack.pop()
            if len(path) == k:
                # close cycle
                if start in adj.get(v, []) and len(set(path)) == k:
                    cyc = path[:]  # length k, start at 'start'
                    # canonicalize: enforce start is minimal vertex in cycle
                    if start != min(cyc):
                        continue
                    cycles.append(cyc)
                continue
            for nb in adj.get(v, []):
                if nb in path:
                    continue
                # pruning: keep start as minimal
                if nb < start:
                    continue
                stack.append((nb, path + [nb]))
    # remove reversals duplicates
    uniq: Dict[Tuple[int, ...], bool] = {}
    out: List[List[int]] = []
    for cyc in cycles:
        r = [cyc[0]] + list(reversed(cyc[1:]))
        key = tuple(cyc)
        rkey = tuple(r)
        if rkey in uniq or key in uniq:
            continue
        uniq[key] = True
        out.append(cyc)
    return out


def holonomy_summary_from_type_graph(
    *,
    node_seq: List[Dict[str, Any]],
    max_cycle_len: int = 4,
) -> TypeGraphHolonomySummary:
    """
    Build the induced *type graph* from a scan node sequence and compute holonomy on its short cycles.

    Inputs:
      node_seq: list of center-node dicts in scan order, each carrying at least {u6, rep}.
      max_cycle_len: enumerate cycles of length 3..max_cycle_len (default 4).
    """
    # Collapse consecutive identical types.
    types: List[str] = []
    reps_of_type: Dict[str, str] = {}
    for n in node_seq:
        u6 = str(n["u6"])
        reps_of_type.setdefault(u6, str(n.get("rep", "$-$")))
        if not types or types[-1] != u6:
            types.append(u6)

    # Build undirected adjacency between types.
    idx = {t: i for i, t in enumerate(sorted(set(types)))}
    rev = {i: t for t, i in idx.items()}
    adj: Dict[int, List[int]] = {i: [] for i in idx.values()}
    for a, b in zip(types[:-1], types[1:]):
        ia = idx[a]
        ib = idx[b]
        if ib not in adj[ia]:
            adj[ia].append(ib)
        if ia not in adj[ib]:
            adj[ib].append(ia)
    for i in adj:
        adj[i] = sorted(adj[i])

    # Define oriented edge permutations from type labels (fiber matching).
    pre = holo.preimages()
    edge_p: Dict[Tuple[int, int], Perm] = {}
    for ia, nbs in adj.items():
        wa = rev[ia]
        fa = holo.fiber4(pre, wa)
        for ib in nbs:
            if (ia, ib) in edge_p:
                continue
            wb = rev[ib]
            fb = holo.fiber4(pre, wb)
            rep_a = reps_of_type.get(wa, "$-$")
            rep_b = reps_of_type.get(wb, "$-$")
            p = _best_perm_with_ports(fa, fb, str(rep_a), str(rep_b))
            edge_p[(ia, ib)] = p
            edge_p[(ib, ia)] = holo.inv_perm(p)

    # Enumerate cycles and compute holonomies.
    B = su3rep.basis_B()
    cycle_len_hist: Counter[int] = Counter()
    cycle_type_hist: Counter[str] = Counter()
    angle_hist: Counter[str] = Counter()
    per_rep_ct: Dict[str, Counter] = defaultdict(Counter)

    cycles: List[List[int]] = []
    for k in range(3, int(max_cycle_len) + 1):
        cycles.extend(_simple_cycles_len_k(adj, k))

    for cyc in cycles:
        cycle_len_hist[len(cyc)] += 1
        hol: Perm = (0, 1, 2, 3)
        for a, b in zip(cyc, cyc[1:] + [cyc[0]]):
            hol = holo.compose(edge_p[(a, b)], hol)
        ct = holo.cycle_type(hol)
        cycle_type_hist[ct] += 1

        R = su3rep.su3_rep(hol, B=B)
        ang = su3rep.rotation_angle_deg(R)
        # bin angles to the four canonical values
        if abs(ang - 0.0) < 1e-6:
            angle_hist["0"] += 1
        elif abs(ang - 90.0) < 1e-6:
            angle_hist["90"] += 1
        elif abs(ang - 120.0) < 1e-6:
            angle_hist["120"] += 1
        else:
            angle_hist["180"] += 1

        # Attribute cycle to reps of its vertices.
        for v in cyc:
            u6 = rev[v]
            rep_key = _parse_rep_tex(reps_of_type.get(u6, "$-$"))
            per_rep_ct[rep_key][ct] += 1

    ang_frac = _normalize_hist(dict(angle_hist))
    per_rep_angle_frac = {k: _normalize_hist(_cycle_hist_to_angle_hist(dict(c))) for k, c in per_rep_ct.items()}
    per_rep_count = {k: int(sum(v.values())) for k, v in per_rep_ct.items()}
    return TypeGraphHolonomySummary(
        n_types=len(idx),
        n_edges_undirected=int(sum(len(v) for v in adj.values()) // 2),
        n_cycles=len(cycles),
        cycle_len_hist={int(k): int(v) for k, v in cycle_len_hist.items()},
        cycle_type_hist=dict(cycle_type_hist),
        angle_hist=dict(angle_hist),
        angle_frac=ang_frac,
        per_rep_angle_frac=per_rep_angle_frac,
        per_rep_count=per_rep_count,
    )


def holonomy_summary_from_spatial_type_graph_2d(
    *,
    nodes: List[Dict[str, Any]],
    max_cycle_len: int = 6,
) -> TypeGraphHolonomySummary:
    """
    Build a type graph from *spatial axis-neighbor adjacency* of center nodes (2D),
    then compute holonomy on its short cycles.

    This is a stronger carrier than scan-adjacency: it includes screen locality edges and therefore
    generates many small cycles.
    """
    pos: Dict[Tuple[int, int], int] = {}
    reps_of_type: Dict[str, str] = {}
    for n in nodes:
        u6 = str(n["u6"])
        reps_of_type.setdefault(u6, str(n.get("rep", "$-$")))
        pos[_pt2_key(tuple(n["pt"]))] = int(n["id"])

    # Undirected spatial edges on center-node lattice.
    edges = _axis_neighbors_2d(pos)
    type_set = sorted({str(n["u6"]) for n in nodes})
    idx = {t: i for i, t in enumerate(type_set)}
    rev = {i: t for t, i in idx.items()}
    adj: Dict[int, List[int]] = {i: [] for i in idx.values()}
    for a, b in edges:
        ta = str(nodes[int(a)]["u6"])
        tb = str(nodes[int(b)]["u6"])
        ia = idx[ta]
        ib = idx[tb]
        if ib not in adj[ia]:
            adj[ia].append(ib)
        if ia not in adj[ib]:
            adj[ib].append(ia)
    for i in adj:
        adj[i] = sorted(adj[i])

    # Edge transport on type graph.
    pre = holo.preimages()
    edge_p: Dict[Tuple[int, int], Perm] = {}
    for ia, nbs in adj.items():
        wa = rev[ia]
        fa = holo.fiber4(pre, wa)
        for ib in nbs:
            if (ia, ib) in edge_p:
                continue
            wb = rev[ib]
            fb = holo.fiber4(pre, wb)
            rep_a = reps_of_type.get(wa, "$-$")
            rep_b = reps_of_type.get(wb, "$-$")
            p = _best_perm_with_ports(fa, fb, str(rep_a), str(rep_b))
            edge_p[(ia, ib)] = p
            edge_p[(ib, ia)] = holo.inv_perm(p)

    B = su3rep.basis_B()
    cycle_len_hist: Counter[int] = Counter()
    cycle_type_hist: Counter[str] = Counter()
    angle_hist: Counter[str] = Counter()
    per_rep_ct: Dict[str, Counter] = defaultdict(Counter)

    cycles: List[List[int]] = []
    for k in range(3, int(max_cycle_len) + 1):
        cycles.extend(_simple_cycles_len_k(adj, k))

    for cyc in cycles:
        cycle_len_hist[len(cyc)] += 1
        hol: Perm = (0, 1, 2, 3)
        for a, b in zip(cyc, cyc[1:] + [cyc[0]]):
            hol = holo.compose(edge_p[(a, b)], hol)
        ct = holo.cycle_type(hol)
        cycle_type_hist[ct] += 1
        R = su3rep.su3_rep(hol, B=B)
        ang = su3rep.rotation_angle_deg(R)
        if abs(ang - 0.0) < 1e-6:
            angle_hist["0"] += 1
        elif abs(ang - 90.0) < 1e-6:
            angle_hist["90"] += 1
        elif abs(ang - 120.0) < 1e-6:
            angle_hist["120"] += 1
        else:
            angle_hist["180"] += 1
        for v in cyc:
            u6 = rev[v]
            rep_key = _parse_rep_tex(reps_of_type.get(u6, "$-$"))
            per_rep_ct[rep_key][ct] += 1

    ang_frac = _normalize_hist(dict(angle_hist))
    per_rep_angle_frac = {k: _normalize_hist(_cycle_hist_to_angle_hist(dict(c))) for k, c in per_rep_ct.items()}
    per_rep_count = {k: int(sum(v.values())) for k, v in per_rep_ct.items()}
    return TypeGraphHolonomySummary(
        n_types=len(idx),
        n_edges_undirected=int(sum(len(v) for v in adj.values()) // 2),
        n_cycles=len(cycles),
        cycle_len_hist={int(k): int(v) for k, v in cycle_len_hist.items()},
        cycle_type_hist=dict(cycle_type_hist),
        angle_hist=dict(angle_hist),
        angle_frac=ang_frac,
        per_rep_angle_frac=per_rep_angle_frac,
        per_rep_count=per_rep_count,
    )


def holonomy_summary_from_spatial_type_graph_3d(
    *,
    nodes: List[Dict[str, Any]],
    max_cycle_len: int = 6,
) -> TypeGraphHolonomySummary:
    """
    3D analogue of holonomy_summary_from_spatial_type_graph_2d.
    """
    pos: Dict[Tuple[int, int, int], int] = {}
    reps_of_type: Dict[str, str] = {}
    for n in nodes:
        u6 = str(n["u6"])
        reps_of_type.setdefault(u6, str(n.get("rep", "$-$")))
        pos[_pt3_key(tuple(n["pt"]))] = int(n["id"])

    edges = _axis_neighbors_3d(pos)
    type_set = sorted({str(n["u6"]) for n in nodes})
    idx = {t: i for i, t in enumerate(type_set)}
    rev = {i: t for t, i in idx.items()}
    adj: Dict[int, List[int]] = {i: [] for i in idx.values()}
    for a, b in edges:
        ta = str(nodes[int(a)]["u6"])
        tb = str(nodes[int(b)]["u6"])
        ia = idx[ta]
        ib = idx[tb]
        if ib not in adj[ia]:
            adj[ia].append(ib)
        if ia not in adj[ib]:
            adj[ib].append(ia)
    for i in adj:
        adj[i] = sorted(adj[i])

    pre = holo.preimages()
    edge_p: Dict[Tuple[int, int], Perm] = {}
    for ia, nbs in adj.items():
        wa = rev[ia]
        fa = holo.fiber4(pre, wa)
        for ib in nbs:
            if (ia, ib) in edge_p:
                continue
            wb = rev[ib]
            fb = holo.fiber4(pre, wb)
            rep_a = reps_of_type.get(wa, "$-$")
            rep_b = reps_of_type.get(wb, "$-$")
            p = _best_perm_with_ports(fa, fb, str(rep_a), str(rep_b))
            edge_p[(ia, ib)] = p
            edge_p[(ib, ia)] = holo.inv_perm(p)

    B = su3rep.basis_B()
    cycle_len_hist: Counter[int] = Counter()
    cycle_type_hist: Counter[str] = Counter()
    angle_hist: Counter[str] = Counter()
    per_rep_ct: Dict[str, Counter] = defaultdict(Counter)

    cycles: List[List[int]] = []
    for k in range(3, int(max_cycle_len) + 1):
        cycles.extend(_simple_cycles_len_k(adj, k))

    for cyc in cycles:
        cycle_len_hist[len(cyc)] += 1
        hol: Perm = (0, 1, 2, 3)
        for a, b in zip(cyc, cyc[1:] + [cyc[0]]):
            hol = holo.compose(edge_p[(a, b)], hol)
        ct = holo.cycle_type(hol)
        cycle_type_hist[ct] += 1
        R = su3rep.su3_rep(hol, B=B)
        ang = su3rep.rotation_angle_deg(R)
        if abs(ang - 0.0) < 1e-6:
            angle_hist["0"] += 1
        elif abs(ang - 90.0) < 1e-6:
            angle_hist["90"] += 1
        elif abs(ang - 120.0) < 1e-6:
            angle_hist["120"] += 1
        else:
            angle_hist["180"] += 1
        for v in cyc:
            u6 = rev[v]
            rep_key = _parse_rep_tex(reps_of_type.get(u6, "$-$"))
            per_rep_ct[rep_key][ct] += 1

    ang_frac = _normalize_hist(dict(angle_hist))
    per_rep_angle_frac = {k: _normalize_hist(_cycle_hist_to_angle_hist(dict(c))) for k, c in per_rep_ct.items()}
    per_rep_count = {k: int(sum(v.values())) for k, v in per_rep_ct.items()}
    return TypeGraphHolonomySummary(
        n_types=len(idx),
        n_edges_undirected=int(sum(len(v) for v in adj.values()) // 2),
        n_cycles=len(cycles),
        cycle_len_hist={int(k): int(v) for k, v in cycle_len_hist.items()},
        cycle_type_hist=dict(cycle_type_hist),
        angle_hist=dict(angle_hist),
        angle_frac=ang_frac,
        per_rep_angle_frac=per_rep_angle_frac,
        per_rep_count=per_rep_count,
    )

