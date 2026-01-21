# -*- coding: utf-8 -*-
"""
Canonical labeling (prototype) for colored graphs derived from Hilbert center-graphs.

We implement a lightweight Weisfeiler–Lehman (1-WL) refinement plus deterministic tie-breaks.
This is not a full GI engine, but it is sufficient to:
  - compute stable color partitions (a strong practical invariant)
  - build a deterministic canonical signature string for many graphs

The goal here is to support an auditable "unique layout rule" pipeline:
  constraints -> refine -> tie-break -> canonical representative.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Dict, Iterable, List, Sequence, Tuple

from hilbert_sm_center_graph import CenterGraph


def _h(s: str) -> str:
    return hashlib.blake2s(s.encode("utf-8"), digest_size=16).hexdigest()


@dataclass(frozen=True)
class WLResult:
    colors: Dict[int, str]         # node_id -> color token
    n_rounds: int
    n_colors: int


def wl_refine(
    *,
    n_nodes: int,
    neighbors: Dict[int, List[int]],
    base_colors: Dict[int, str],
    max_rounds: int = 32,
) -> WLResult:
    """
    1-WL color refinement.
    """
    colors = dict(base_colors)
    for r in range(int(max_rounds)):
        buckets: Dict[int, str] = {}
        for v in range(int(n_nodes)):
            nb = neighbors.get(int(v), [])
            sig = (colors.get(int(v), "0"), tuple(sorted(colors.get(int(u), "0") for u in nb)))
            buckets[int(v)] = _h(repr(sig))
        # compress to stable small tokens for determinism
        uniq = sorted(set(buckets.values()))
        map_tok = {c: f"c{idx:04d}" for idx, c in enumerate(uniq)}
        new_colors = {v: map_tok[buckets[v]] for v in buckets}
        if new_colors == colors:
            return WLResult(colors=colors, n_rounds=r, n_colors=len(set(colors.values())))
        colors = new_colors
    return WLResult(colors=colors, n_rounds=int(max_rounds), n_colors=len(set(colors.values())))


def center_graph_base_colors(g: CenterGraph) -> Dict[int, str]:
    """
    Build base node colors from protocol-visible labels:
      (m, u6, is_boundary, label_tex, rep_tex)
    """
    out: Dict[int, str] = {}
    for n in g.nodes:
        out[int(n.id)] = f"m={n.m}|u6={n.u6}|bdry={int(n.is_boundary)}|lab={n.label_tex}|rep={n.rep_tex}"
    return out


def center_graph_neighbors_from_scan(g: CenterGraph) -> Dict[int, List[int]]:
    """
    Convert the scan edges (a path) into an undirected adjacency for WL refinement.
    """
    adj: Dict[int, List[int]] = {i: [] for i in range(len(g.nodes))}
    for a, b in g.scan_edges:
        aa = int(a)
        bb = int(b)
        adj[aa].append(bb)
        adj[bb].append(aa)
    # make deterministic ordering
    for k in adj:
        adj[k] = sorted(set(adj[k]))
    return adj


def canonical_signature_center_graph(
    g: CenterGraph, *, include_scan_pos: bool = True, include_dim: bool = True
) -> Tuple[str, WLResult]:
    """
    Produce a deterministic canonical signature string for the scan-path graph with node colors.
    The signature is not guaranteed to be a full canonical form for adversarial instances, but it is stable and
    strong enough for the intended audit comparisons.
    """
    n = len(g.nodes)
    base = center_graph_base_colors(g)
    adj = center_graph_neighbors_from_scan(g)
    wl = wl_refine(n_nodes=n, neighbors=adj, base_colors=base)

    # tie-break order: sort nodes by (wl_color, base_color, id)
    order = sorted(range(n), key=lambda i: (wl.colors.get(i, ""), base.get(i, ""), i))
    pos = {v: idx for idx, v in enumerate(order)}

    # adjacency list in canonical order
    canon_adj: List[Tuple[int, Tuple[int, ...]]] = []
    for v in order:
        nb = tuple(sorted(pos[u] for u in adj.get(v, [])))
        canon_adj.append((pos[v], nb))

    # Optionally include a canonical scan order projection.
    # For GI-style comparisons on the underlying labeled graph, one typically sets include_scan_pos=False.
    scan_pos = tuple(pos[int(v)] for v in g.scan_path) if include_scan_pos else None

    payload = {
        "n_nodes": n,
        "wl_rounds": wl.n_rounds,
        "wl_colors": tuple(wl.colors.get(v, "") for v in order),
        "canon_adj": canon_adj,
        "scan_pos": scan_pos,
    }
    if include_dim:
        payload["dim"] = g.dim
    sig = _h(repr(payload))
    return sig, wl


def canonical_signature_type_transition_graph(g: CenterGraph) -> str:
    """
    Build a canonical signature for the induced *type transition graph* on X6 labels.

    Motivation:
      - The "18+3" structure lives on stable types, not on individual subcell centers.
      - Comparing 2D vs 3D via a 21-node type graph is closer to the physics-facing constraints,
        and avoids overfitting to display-dimension details.

    Construction:
      - Take the scan path node sequence and map to u6 labels.
      - Collapse consecutive identical labels (run-length collapse).
      - Count directed transitions between successive labels.
      - Canonicalize by sorting vertex labels lexicographically and hashing the edge multiset.
    """
    # Collapse consecutive identical stable types.
    u = [g.nodes[int(nid)].u6 for nid in g.scan_path]
    collapsed: List[str] = []
    for s in u:
        if not collapsed or collapsed[-1] != s:
            collapsed.append(s)

    # Node labels: include the closed SM label for stability.
    # (u6, label_tex, rep_tex, is_boundary) fully determines the 18+3 partition.
    node_label: Dict[str, str] = {}
    for n in g.nodes:
        node_label.setdefault(n.u6, f"u6={n.u6}|bdry={int(n.is_boundary)}|lab={n.label_tex}|rep={n.rep_tex}")
    verts = sorted(node_label.keys())
    pos = {w: i for i, w in enumerate(verts)}

    # Count directed edges.
    counts: Dict[Tuple[int, int], int] = {}
    for a, b in zip(collapsed[:-1], collapsed[1:]):
        ia = pos[a]
        ib = pos[b]
        counts[(ia, ib)] = int(counts.get((ia, ib), 0)) + 1

    # Canonical payload: ordered vertex labels + sorted edge list with multiplicities.
    edges = sorted([(ia, ib, int(c)) for (ia, ib), c in counts.items()])
    payload = {
        "nV": len(verts),
        "V": [node_label[w] for w in verts],
        "E": edges,
        "n_steps_collapsed": len(collapsed),
    }
    return _h(repr(payload))

