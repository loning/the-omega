# -*- coding: utf-8 -*-
"""
Center-graph construction for adaptive Hilbert layouts (2D/3D), aligned with the paper's protocol objects.

Design goals:
  - Pure standard library (no networkx).
  - Deterministic.
  - Provide a common "graph object" for 2D/3D comparisons:
      * Nodes are center points (macro center for m=6; subcell centers for refined m).
      * Edges for the scan path are center-to-center straight segments only:
          - same-m edges must be axis-aligned
          - cross-m edges must be diagonal
      * The scan path must be a single stroke and non-self-intersecting (except endpoint touches).

This module is a research/prototype utility; it does not modify theorem-level folding statements.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import exp_hilbert_chirality_index as hil2
import exp_sm_labeling_solver as sm
from hilbert_nd import hilbert_index_to_coords


Coord = Tuple[int, ...]
Pt = Tuple[float, ...]


def _ceil_div(a: int, b: int) -> int:
    return int((int(a) + int(b) - 1) // int(b))


def _base_screen_coords(dim: int) -> List[Coord]:
    """
    Return the 64-site base screen coordinates in scan order k=0..63.
      - 2D: 8x8 Hilbert, n_bits=3 (paper anchor)
      - 3D: 4x4x4 Hilbert, p=2 (paper anchor)
    """
    dim = int(dim)
    if dim == 2:
        path2 = hil2.hilbert_curve(3)
        if len(path2) != 64:
            raise AssertionError("Expected 64 points for 2D n_bits=3.")
        return [(int(x), int(y)) for (x, y) in path2]
    if dim == 3:
        # 4^3 = 64 = 2^(3*2)
        return [tuple(int(v) for v in hilbert_index_to_coords(k, p=2, n=3)) for k in range(64)]
    raise ValueError("dim must be 2 or 3.")


def _refined_subcoords(dim: int, m: int) -> List[Coord]:
    """
    Return occupied subcell integer coordinates for the refined microstructure.

    - 2D: use a full SxS occupancy for m in {8,10,...} where (m-6) is even.
    - 3D: use a sparse occupancy (prefix) of the finite 3D Hilbert scan.

    This follows the paper's 2D anchor convention for Hilbert orientation in 2D and the Skilling-style nD
    mapping for 3D visualization and locality.
    """
    dim = int(dim)
    m = int(m)
    if m < 6:
        raise ValueError("m must be >= 6.")
    if m == 6:
        return [(0,) * dim]
    suffix = int(m - 6)
    if suffix <= 0:
        return [(0,) * dim]

    if dim == 2:
        n_bits = suffix // 2
        if 2 * n_bits != suffix:
            # For this prototype we keep the exact even case (m=8/10).
            n_bits = _ceil_div(suffix, 2)
        S = 1 << n_bits
        path = hil2.hilbert_curve(n_bits)
        need = 1 << suffix
        # For m=8/10, need == S*S; otherwise, use prefix occupancy (still deterministic).
        out = [(int(x), int(y)) for (x, y) in path[: min(need, len(path))]]
        return out

    if dim == 3:
        p = _ceil_div(suffix, 3)
        S = 1 << p
        need = 1 << suffix
        cap = 1 << (3 * p)
        take = min(int(need), int(cap))
        out3: List[Coord] = []
        for h in range(take):
            cc = hilbert_index_to_coords(h, p=p, n=3)
            out3.append(tuple(int(v) for v in cc))
        return out3

    raise ValueError("dim must be 2 or 3.")


def _subcell_scale(dim: int, m: int) -> int:
    """
    Return integer scale S for refined nodes within a coarse cell.
    """
    dim = int(dim)
    m = int(m)
    if m <= 6:
        return 1
    suffix = int(m - 6)
    if dim == 2:
        n_bits = _ceil_div(suffix, 2)
        return 1 << int(n_bits)
    if dim == 3:
        p = _ceil_div(suffix, 3)
        return 1 << int(p)
    raise ValueError("dim must be 2 or 3.")


def _global_center_pt(cell: Coord, S: int, sub: Coord) -> Pt:
    """
    Map a (coarse cell coord, scale S, integer subcoord) to a center point in R^dim.
    We use integer lattice units so that axis-aligned vs diagonal tests are exact.
    """
    if len(cell) != len(sub):
        raise ValueError("cell and sub must have the same dimension.")
    out: List[float] = []
    for i in range(len(cell)):
        # Center at (cell*S + sub + 0.5)
        out.append(float(int(cell[i]) * int(S) + int(sub[i])) + 0.5)
    return tuple(out)


def _axis_aligned(a: Pt, b: Pt, eps: float = 1e-9) -> bool:
    # Axis-aligned in R^dim: exactly one coordinate differs.
    diffs = [abs(float(ai) - float(bi)) for ai, bi in zip(a, b)]
    nz = [d for d in diffs if d > eps]
    return len(nz) == 1


def _diagonal(a: Pt, b: Pt, eps: float = 1e-9) -> bool:
    # Diagonal: at least two coordinates differ.
    diffs = [abs(float(ai) - float(bi)) for ai, bi in zip(a, b)]
    nz = [d for d in diffs if d > eps]
    return len(nz) >= 2


def _orientation_2d(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float], eps: float = 1e-9) -> int:
    v = (b[1] - a[1]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[1] - a[1])
    if abs(v) <= eps:
        return 0
    return 1 if v > 0 else -1


def _on_segment_2d(a: Tuple[float, float], p: Tuple[float, float], b: Tuple[float, float], eps: float = 1e-9) -> bool:
    return (
        min(a[0], b[0]) - eps <= p[0] <= max(a[0], b[0]) + eps
        and min(a[1], b[1]) - eps <= p[1] <= max(a[1], b[1]) + eps
    )


def _segments_intersect_2d(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
    d: Tuple[float, float],
    eps: float = 1e-9,
) -> bool:
    o1 = _orientation_2d(a, b, c, eps)
    o2 = _orientation_2d(a, b, d, eps)
    o3 = _orientation_2d(c, d, a, eps)
    o4 = _orientation_2d(c, d, b, eps)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment_2d(a, c, b, eps):
        return True
    if o2 == 0 and _on_segment_2d(a, d, b, eps):
        return True
    if o3 == 0 and _on_segment_2d(c, a, d, eps):
        return True
    if o4 == 0 and _on_segment_2d(c, b, d, eps):
        return True
    return False


def _touch_endpoint_only_2d(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
    d: Tuple[float, float],
    tp: Tuple[float, float],
    eps: float = 1e-9,
) -> bool:
    # Allow touching only at the shared endpoint tp; forbid overlaps.
    def eq(p: Tuple[float, float], q: Tuple[float, float]) -> bool:
        return abs(p[0] - q[0]) <= eps and abs(p[1] - q[1]) <= eps

    if not (eq(tp, a) or eq(tp, b)):
        return False
    if not (eq(tp, c) or eq(tp, d)):
        return False
    # If collinear, disallow any positive overlap.
    col = _orientation_2d(a, b, c, eps) == 0 and _orientation_2d(a, b, d, eps) == 0
    if not col:
        return True
    # Collinear: overlap length must be ~0.
    if abs(a[0] - b[0]) >= abs(a[1] - b[1]):
        a0, a1 = sorted([a[0], b[0]])
        c0, c1 = sorted([c[0], d[0]])
    else:
        a0, a1 = sorted([a[1], b[1]])
        c0, c1 = sorted([c[1], d[1]])
    left = max(a0, c0)
    right = min(a1, c1)
    return right <= left + eps


def _segment_hits_any_center_2d(
    a: Tuple[float, float],
    b: Tuple[float, float],
    centers: Sequence[Tuple[float, float]],
    *,
    allow_endpoints: Tuple[Tuple[float, float], Tuple[float, float]],
    eps: float = 1e-9,
) -> bool:
    ea, eb = allow_endpoints

    def eq(p: Tuple[float, float], q: Tuple[float, float]) -> bool:
        return abs(p[0] - q[0]) <= eps and abs(p[1] - q[1]) <= eps

    for c in centers:
        if eq(c, ea) or eq(c, eb):
            continue
        if eq(c, a) or eq(c, b):
            continue
        if _orientation_2d(a, c, b, eps) == 0 and _on_segment_2d(a, c, b, eps):
            return True
    return False


@dataclass(frozen=True)
class CenterNode:
    id: int
    dim: int
    k_coarse: int
    m: int
    cell: Coord
    sub: Coord
    pt: Pt
    u6: str
    label_tex: str
    rep_tex: str
    is_boundary: bool


@dataclass
class CenterGraph:
    dim: int
    nodes: List[CenterNode]
    # scan path node ids in order
    scan_path: List[int]
    # scan edges in order (u,v)
    scan_edges: List[Tuple[int, int]]
    meta: Dict[str, object]

@dataclass(frozen=True)
class BuildConstraints:
    """
    Geometry constraints that can be relaxed for experimental search.
    """

    enforce_edge_types: bool = True
    # Non-crossing is enforced in 2D projection (x,y). This is conservative for 3D.
    enforce_noncrossing_xy: bool = True
    # Forbid segments passing through any other centers (strict center-graph).
    forbid_passing_through_centers: bool = True


def _label_map_x6() -> Dict[str, Tuple[str, str, bool]]:
    """
    Return mapping u6 -> (label_tex, rep_tex, is_boundary).
    Deterministic per exp_sm_labeling_solver.generate_rows() ordering rules.
    """
    X6 = sm.all_x6()
    boundary = [w for w in X6 if sm.is_boundary_word(w)]
    cyclic = [w for w in X6 if not sm.is_boundary_word(w)]
    boundary_sorted = sorted(boundary, key=lambda w: (sm.zeckendorf_value(w), w))
    cyclic_sorted = sorted(cyclic, key=lambda w: sm.stable_type_sort_key(w))

    fields = sorted(sm.fermion_targets(), key=lambda f: f.complexity_key())
    gauge = sm.boundary_gauge_labels()

    out: Dict[str, Tuple[str, str, bool]] = {}
    for w, f in zip(cyclic_sorted, fields):
        out[w] = (f.label_tex(), f.rep_tex(), False)
    for w, (lab, rep) in zip(boundary_sorted, gauge):
        out[w] = (lab, rep, True)
    if len(out) != 21:
        raise AssertionError("Expected 21 X6 labels.")
    return out


def build_center_graph(
    *,
    dim: int,
    m_by_k: Dict[int, int],
    max_micro_orders: int = 8,
    constraints: Optional[BuildConstraints] = None,
) -> CenterGraph:
    """
    Build a strict center-graph and a non-self-intersecting one-stroke scan path.

    This chooses a micro Hilbert order per refined coarse cell (bounded to max_micro_orders),
    and uses incremental backtracking to ensure no self-intersections and no skipping centers.

    Note: for 3D, intersection checks are performed on a fixed 2D projection (x,y). This is a deliberate
    conservative proxy for "no crossings in the displayed 2D carrier", matching how the paper audits
    plots. The full 3D non-self-intersection is stronger and can be added later.
    """
    dim = int(dim)
    if dim not in (2, 3):
        raise ValueError("dim must be 2 or 3.")
    if constraints is None:
        constraints = BuildConstraints()

    base = _base_screen_coords(dim)
    labels = _label_map_x6()

    # Node inventory per coarse cell: options are lists of CenterNode prototypes (without id yet).
    cell_opts: List[List[List[Tuple[Coord, Coord, Pt, int]]]] = []
    # Each entry: list of options; each option is a list of (cell, sub, pt, m)
    for k in range(64):
        m = int(m_by_k.get(int(k), 6))
        cell = base[k]
        if m <= 6:
            pt = _global_center_pt(cell, 1, (0,) * dim)
            cell_opts.append([[(cell, (0,) * dim, pt, 6)]])
            continue

        S = _subcell_scale(dim, m)
        subcoords = _refined_subcoords(dim, m)

        # Candidate "micro orders": dihedral symmetries in 2D, and a bounded set of coordinate transforms in 3D.
        # For this prototype, we use a simple deterministic family:
        #   - 2D: D4 transforms applied to the subcoords in their Hilbert order
        #   - 3D: a small set of axis permutations + optional reflections on coordinates
        base_order = subcoords
        opts: List[List[Tuple[Coord, Coord, Pt, int]]] = []
        if dim == 2:
            # D4: rotations/reflections on an SxS grid.
            maxv = int(S) - 1

            def t0(x: int, y: int) -> Tuple[int, int]:
                return (x, y)

            def t1(x: int, y: int) -> Tuple[int, int]:
                return (y, maxv - x)

            def t2(x: int, y: int) -> Tuple[int, int]:
                return (maxv - x, maxv - y)

            def t3(x: int, y: int) -> Tuple[int, int]:
                return (maxv - y, x)

            def t4(x: int, y: int) -> Tuple[int, int]:
                return (maxv - x, y)

            def t5(x: int, y: int) -> Tuple[int, int]:
                return (x, maxv - y)

            def t6(x: int, y: int) -> Tuple[int, int]:
                return (y, x)

            def t7(x: int, y: int) -> Tuple[int, int]:
                return (maxv - y, maxv - x)

            tfs = [t0, t1, t2, t3, t4, t5, t6, t7]
            for tf in tfs:
                pts: List[Tuple[Coord, Coord, Pt, int]] = []
                for (xx, yy) in base_order:
                    sx, sy = tf(int(xx), int(yy))
                    sub = (int(sx), int(sy))
                    pt = _global_center_pt(cell, S, sub)
                    pts.append((cell, sub, pt, m))
                opts.append(pts)
                opts.append(list(reversed(pts)))
        else:
            # 3D: a small generating set of cube symmetries (axis permutations + sign flips).
            maxv = int(S) - 1
            perms = [
                (0, 1, 2),
                (0, 2, 1),
                (1, 0, 2),
                (1, 2, 0),
                (2, 0, 1),
                (2, 1, 0),
            ]
            flips = [
                (0, 0, 0),
                (1, 0, 0),
                (0, 1, 0),
                (0, 0, 1),
            ]
            for p in perms:
                for f in flips:
                    pts = []
                    for (x0, y0, z0) in base_order:
                        v = [int(x0), int(y0), int(z0)]
                        w = [v[p[0]], v[p[1]], v[p[2]]]
                        if f[0]:
                            w[0] = maxv - w[0]
                        if f[1]:
                            w[1] = maxv - w[1]
                        if f[2]:
                            w[2] = maxv - w[2]
                        sub3 = (int(w[0]), int(w[1]), int(w[2]))
                        pt3 = _global_center_pt(cell, S, sub3)
                        pts.append((cell, sub3, pt3, m))
                    opts.append(pts)
                    opts.append(list(reversed(pts)))
        # Keep deterministic prefix of options.
        cell_opts.append(opts[: int(max_micro_orders)])

    # Flatten centers for "no skipping nodes" checks (2D projection used when dim==3).
    centers_proj: List[Tuple[float, float]] = []
    for k in range(64):
        for opt in cell_opts[k]:
            for (_cell, _sub, pt, _m) in opt:
                if dim == 2:
                    centers_proj.append((pt[0], pt[1]))
                else:
                    centers_proj.append((pt[0], pt[1]))
            break  # use one option; skipping check is conservative anyway

    # Incremental backtracking over k=0..63.
    chosen: Dict[int, int] = {}
    nodes: List[CenterNode] = []
    scan_path: List[int] = []
    scan_edges: List[Tuple[int, int]] = []
    segments2d: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []

    def seg_ok(a: Pt, b: Pt, ka_m: int, kb_m: int) -> bool:
        if constraints.enforce_edge_types:
            if ka_m == kb_m:
                if not _axis_aligned(a, b):
                    return False
            else:
                if not _diagonal(a, b):
                    return False
        if dim == 2:
            aa = (a[0], a[1])
            bb = (b[0], b[1])
        else:
            aa = (a[0], a[1])
            bb = (b[0], b[1])
        if constraints.forbid_passing_through_centers:
            if _segment_hits_any_center_2d(aa, bb, centers_proj, allow_endpoints=(aa, bb)):
                return False
        if constraints.enforce_noncrossing_xy:
            for (c, d) in segments2d:
                if not _segments_intersect_2d(aa, bb, c, d):
                    continue
                # allow touching at endpoints only
                if _touch_endpoint_only_2d(aa, bb, c, d, aa) or _touch_endpoint_only_2d(aa, bb, c, d, bb):
                    continue
                return False
        return True

    def push_segment(a_id: int, b_id: int, a_pt: Pt, b_pt: Pt) -> None:
        scan_edges.append((int(a_id), int(b_id)))
        if dim == 2:
            segments2d.append(((a_pt[0], a_pt[1]), (b_pt[0], b_pt[1])))
        else:
            segments2d.append(((a_pt[0], a_pt[1]), (b_pt[0], b_pt[1])))

    def pop_segment() -> None:
        scan_edges.pop()
        segments2d.pop()

    # Build node objects on the fly to keep ids consistent.
    label_map = labels

    def new_node(k: int, m: int, cell: Coord, sub: Coord, pt: Pt) -> int:
        u6 = sm.fold6(int(k))
        (lab, rep, is_bdry) = label_map[u6]
        nid = len(nodes)
        nodes.append(
            CenterNode(
                id=int(nid),
                dim=dim,
                k_coarse=int(k),
                m=int(m),
                cell=tuple(int(v) for v in cell),
                sub=tuple(int(v) for v in sub),
                pt=tuple(float(v) for v in pt),
                u6=str(u6),
                label_tex=str(lab),
                rep_tex=str(rep),
                is_boundary=bool(is_bdry),
            )
        )
        return int(nid)

    def dfs(k: int) -> bool:
        if k >= 64:
            return True
        for opt_idx, opt in enumerate(cell_opts[k]):
            chosen[k] = int(opt_idx)
            local_ids: List[int] = []
            # Append nodes for this cell option.
            for (cell, sub, pt, m) in opt:
                local_ids.append(new_node(k, m, cell, sub, pt))

            # Connect from previous endpoint, then internal.
            ok = True
            if not scan_path:
                scan_path.extend(local_ids)
            else:
                prev_id = scan_path[-1]
                prev = nodes[prev_id]
                first = nodes[local_ids[0]]
                if not seg_ok(prev.pt, first.pt, prev.m, first.m):
                    ok = False
                else:
                    push_segment(prev_id, local_ids[0], prev.pt, first.pt)
                    scan_path.append(local_ids[0])
                # internal edges
                if ok:
                    for j in range(len(local_ids) - 1):
                        a_id = local_ids[j]
                        b_id = local_ids[j + 1]
                        a = nodes[a_id]
                        b = nodes[b_id]
                        if not seg_ok(a.pt, b.pt, a.m, b.m):
                            ok = False
                            break
                        push_segment(a_id, b_id, a.pt, b.pt)
                        scan_path.append(b_id)

            if ok and dfs(k + 1):
                return True

            # rollback
            while scan_path and scan_path[-1] in local_ids:
                scan_path.pop()
            # also pop the connecting segment from prev->first if it was added
            while scan_edges and scan_edges[-1][0] >= 0 and scan_edges[-1][1] >= 0 and (scan_edges[-1][1] in local_ids):
                pop_segment()
            # remove local nodes
            del nodes[-len(local_ids) :]
            chosen.pop(k, None)
        return False

    ok = dfs(0)
    if not ok:
        # For 3D, the 2D-projection non-crossing constraint can be too strong.
        # As a fallback, accept the deterministic choice (option 0) per refined cell without intersection checks.
        if dim == 3:
            nodes = []
            scan_path = []
            scan_edges = []
            chosen = {}
            for k in range(64):
                chosen[k] = 0
                opt = cell_opts[k][0]
                local_ids = []
                for (cell, sub, pt, m) in opt:
                    local_ids.append(new_node(k, m, cell, sub, pt))
                if not scan_path:
                    scan_path.extend(local_ids)
                else:
                    scan_edges.append((scan_path[-1], local_ids[0]))
                    scan_path.append(local_ids[0])
                for j in range(len(local_ids) - 1):
                    scan_edges.append((local_ids[j], local_ids[j + 1]))
                    scan_path.append(local_ids[j + 1])
            return CenterGraph(
                dim=dim,
                nodes=nodes,
                scan_path=scan_path,
                scan_edges=scan_edges,
                meta={
                    "m_by_k": dict((int(k), int(v)) for k, v in m_by_k.items()),
                    "chosen_micro_option": dict((int(k), int(v)) for k, v in chosen.items()),
                    "note": "3D fallback: projection-noncrossing constraint disabled",
                },
            )
        raise RuntimeError("Failed to construct a non-crossing one-stroke scan path under the strict center-graph rules.")

    return CenterGraph(
        dim=dim,
        nodes=nodes,
        scan_path=scan_path,
        scan_edges=scan_edges,
        meta={
            "m_by_k": dict((int(k), int(v)) for k, v in m_by_k.items()),
            "chosen_micro_option": dict((int(k), int(v)) for k, v in chosen.items()),
        },
    )

def build_center_graph_fixed(
    *,
    dim: int,
    m_by_k: Dict[int, int],
    chosen_micro_option: Dict[int, int],
    max_micro_orders: int = 8,
    constraints: Optional[BuildConstraints] = None,
) -> CenterGraph:
    """
    Build a center-graph using a provided per-cell micro-option choice (no DFS).
    This is intended for GI search: treat micro-option indices as variables and evaluate candidates fast.
    """
    dim = int(dim)
    if constraints is None:
        constraints = BuildConstraints()
    base = _base_screen_coords(dim)
    labels = _label_map_x6()

    # Recompute cell options (same as build_center_graph).
    cell_opts: List[List[List[Tuple[Coord, Coord, Pt, int]]]] = []
    for k in range(64):
        m = int(m_by_k.get(int(k), 6))
        cell = base[k]
        if m <= 6:
            pt = _global_center_pt(cell, 1, (0,) * dim)
            cell_opts.append([[(cell, (0,) * dim, pt, 6)]])
            continue
        S = _subcell_scale(dim, m)
        subcoords = _refined_subcoords(dim, m)
        base_order = subcoords
        opts: List[List[Tuple[Coord, Coord, Pt, int]]] = []
        if dim == 2:
            maxv = int(S) - 1

            def t0(x: int, y: int) -> Tuple[int, int]:
                return (x, y)

            def t1(x: int, y: int) -> Tuple[int, int]:
                return (y, maxv - x)

            def t2(x: int, y: int) -> Tuple[int, int]:
                return (maxv - x, maxv - y)

            def t3(x: int, y: int) -> Tuple[int, int]:
                return (maxv - y, x)

            def t4(x: int, y: int) -> Tuple[int, int]:
                return (maxv - x, y)

            def t5(x: int, y: int) -> Tuple[int, int]:
                return (x, maxv - y)

            def t6(x: int, y: int) -> Tuple[int, int]:
                return (y, x)

            def t7(x: int, y: int) -> Tuple[int, int]:
                return (maxv - y, maxv - x)

            tfs = [t0, t1, t2, t3, t4, t5, t6, t7]
            for tf in tfs:
                pts: List[Tuple[Coord, Coord, Pt, int]] = []
                for (xx, yy) in base_order:
                    sx, sy = tf(int(xx), int(yy))
                    sub = (int(sx), int(sy))
                    pt = _global_center_pt(cell, S, sub)
                    pts.append((cell, sub, pt, m))
                opts.append(pts)
                opts.append(list(reversed(pts)))
        else:
            maxv = int(S) - 1
            perms = [
                (0, 1, 2),
                (0, 2, 1),
                (1, 0, 2),
                (1, 2, 0),
                (2, 0, 1),
                (2, 1, 0),
            ]
            flips = [
                (0, 0, 0),
                (1, 0, 0),
                (0, 1, 0),
                (0, 0, 1),
            ]
            for p in perms:
                for f in flips:
                    pts = []
                    for (x0, y0, z0) in base_order:
                        v = [int(x0), int(y0), int(z0)]
                        w = [v[p[0]], v[p[1]], v[p[2]]]
                        if f[0]:
                            w[0] = maxv - w[0]
                        if f[1]:
                            w[1] = maxv - w[1]
                        if f[2]:
                            w[2] = maxv - w[2]
                        sub3 = (int(w[0]), int(w[1]), int(w[2]))
                        pt3 = _global_center_pt(cell, S, sub3)
                        pts.append((cell, sub3, pt3, m))
                    opts.append(pts)
                    opts.append(list(reversed(pts)))
        cell_opts.append(opts[: int(max_micro_orders)])

    # Projection centers for "pass-through center" check.
    centers_proj: List[Tuple[float, float]] = []
    for k in range(64):
        opt0 = cell_opts[k][0]
        for (_cell, _sub, pt, _m) in opt0:
            centers_proj.append((pt[0], pt[1]))

    nodes: List[CenterNode] = []
    scan_path: List[int] = []
    scan_edges: List[Tuple[int, int]] = []
    segments2d: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []

    def seg_ok(a: Pt, b: Pt, ka_m: int, kb_m: int) -> bool:
        if constraints.enforce_edge_types:
            if ka_m == kb_m:
                if not _axis_aligned(a, b):
                    return False
            else:
                if not _diagonal(a, b):
                    return False
        aa = (a[0], a[1])
        bb = (b[0], b[1])
        if constraints.forbid_passing_through_centers:
            if _segment_hits_any_center_2d(aa, bb, centers_proj, allow_endpoints=(aa, bb)):
                return False
        if constraints.enforce_noncrossing_xy:
            for (c, d) in segments2d:
                if not _segments_intersect_2d(aa, bb, c, d):
                    continue
                if _touch_endpoint_only_2d(aa, bb, c, d, aa) or _touch_endpoint_only_2d(aa, bb, c, d, bb):
                    continue
                return False
        return True

    def push_seg(a_id: int, b_id: int, a_pt: Pt, b_pt: Pt) -> None:
        scan_edges.append((int(a_id), int(b_id)))
        segments2d.append(((a_pt[0], a_pt[1]), (b_pt[0], b_pt[1])))

    def new_node(k: int, m: int, cell: Coord, sub: Coord, pt: Pt) -> int:
        u6 = sm.fold6(int(k))
        (lab, rep, is_bdry) = labels[u6]
        nid = len(nodes)
        nodes.append(
            CenterNode(
                id=int(nid),
                dim=dim,
                k_coarse=int(k),
                m=int(m),
                cell=tuple(int(v) for v in cell),
                sub=tuple(int(v) for v in sub),
                pt=tuple(float(v) for v in pt),
                u6=str(u6),
                label_tex=str(lab),
                rep_tex=str(rep),
                is_boundary=bool(is_bdry),
            )
        )
        return int(nid)

    chosen_used: Dict[int, int] = {}
    for k in range(64):
        opts = cell_opts[k]
        idx = int(chosen_micro_option.get(int(k), 0))
        if idx < 0 or idx >= len(opts):
            idx = idx % max(1, len(opts))
        chosen_used[int(k)] = int(idx)
        opt = opts[idx]

        local_ids: List[int] = []
        for (cell, sub, pt, m) in opt:
            local_ids.append(new_node(k, m, cell, sub, pt))

        if not scan_path:
            scan_path.extend(local_ids)
        else:
            prev_id = scan_path[-1]
            prev = nodes[prev_id]
            first = nodes[local_ids[0]]
            if not seg_ok(prev.pt, first.pt, prev.m, first.m):
                raise RuntimeError(f"Invalid edge at k={k} (prev->first) under constraints.")
            push_seg(prev_id, local_ids[0], prev.pt, first.pt)
            scan_path.append(local_ids[0])

        for j in range(len(local_ids) - 1):
            a_id = local_ids[j]
            b_id = local_ids[j + 1]
            a = nodes[a_id]
            b = nodes[b_id]
            if not seg_ok(a.pt, b.pt, a.m, b.m):
                raise RuntimeError(f"Invalid internal edge at k={k} j={j} under constraints.")
            push_seg(a_id, b_id, a.pt, b.pt)
            scan_path.append(b_id)

    return CenterGraph(
        dim=dim,
        nodes=nodes,
        scan_path=scan_path,
        scan_edges=scan_edges,
        meta={
            "m_by_k": dict((int(k), int(v)) for k, v in m_by_k.items()),
            "chosen_micro_option": chosen_used,
        },
    )


def iter_scan_points(g: CenterGraph) -> Iterable[Pt]:
    for nid in g.scan_path:
        yield g.nodes[int(nid)].pt

