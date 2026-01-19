# -*- coding: utf-8 -*-
"""
Bridge: concrete SM-Hilbert wiring geometry -> electroweak constants (audit-style).

We reuse the manuscript's electroweak "weighted-volume" normalization:

  W_Y_eff := 21 * Σ_{u∈X6} μ6(u) * b(u)
  b(u)    := mult(u) * Y(u)^2  for cyclic u; 0 for boundary u

where:
  mult(u) = su3_dim(u) * su2_dim(u)
  Y(u) is PDG hypercharge (Q = T3 + Y), represented via Y_num = 6Y in SMField.

Given W_Y_eff, define:

  alpha_inv(mu_Z) := (3 + W_Y_eff) * pi^2
  sin^2(theta_W)  := 3 / (3 + W_Y_eff)

This script reads a concrete wiring candidate (wiring_geometry.json) and induces μ6(u)
by counting center-nodes by their stable type u6. This is a protocol-native pushforward
measure tied to the actual wiring (m-schedule + micro orientations), rather than the
global Fold_m microstate baseline.

Outputs:
  - sections/generated/sm_hilbert_constants_bridge_rows.tex
  - sections/generated/sm_hilbert_constants_bridge_summary.tex

English-only output (repo convention for scripts).
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from common_constants import ALPHAZ_INV_PDG, SIN2_THETAW_PDG
from common_paths import generated_dir
import exp_sm_labeling_solver as sml

import exp_holonomy_loops as holo
import exp_holonomy_su3_representation as su3rep
from hilbert_sm_holonomy import _best_perm_with_ports, _port_label


@dataclass(frozen=True)
class EWFromWiring:
    mode: str  # "node" or "holonomy"
    tag: str
    n_nodes: int
    p_cyc: float
    n_cyc_eff: float
    w_y_eff: float
    alpha_inv: float
    e_alpha: float
    sin2: float
    e_sin2: float


def _build_x6_to_field_map() -> Dict[str, sml.SMField]:
    """
    Reproduce the cyclic assignment logic used by the closed labeling solver:
      cyclic types ordered by stable_type_sort_key
      fermion targets ordered by SMField.complexity_key()
    """
    X6 = sml.all_x6()
    cyc = [w for w in X6 if not sml.is_boundary_word(w)]
    cyc_sorted = sorted(cyc, key=lambda w: sml.stable_type_sort_key(w))
    fields_sorted = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
    if len(cyc_sorted) != len(fields_sorted):
        raise AssertionError("Cyclic base types and fermion targets must have same size (18).")
    return {u: f for (u, f) in zip(cyc_sorted, fields_sorted)}


def _b_weight_for_u(u: str, u_to_field: Dict[str, sml.SMField]) -> float:
    if sml.is_boundary_word(u):
        return 0.0
    f = u_to_field.get(u)
    if f is None:
        raise AssertionError("Missing cyclic u in u_to_field map.")
    mult = int(f.su3_dim) * int(f.su2_dim)
    y = float(f.Y_num) / 6.0
    return float(mult) * (y * y)


def _mu6_from_nodes(nodes: List[Dict[str, Any]]) -> Dict[str, float]:
    X6 = sml.all_x6()
    counts: Dict[str, int] = {u: 0 for u in X6}
    for n in nodes:
        u = str(n.get("u6", ""))
        if u not in counts:
            # wiring should only carry X6 stable types
            continue
        counts[u] += 1
    denom = float(sum(counts.values()))
    if denom <= 0.0:
        return {u: float("nan") for u in counts}
    return {u: float(c) / denom for (u, c) in counts.items()}

def _coarse_nodes_and_scan(nodes: List[Dict[str, Any]], scan_path_ids: List[int]) -> Tuple[List[Dict[str, Any]], List[int]]:
    """
    Build a coarse-cell projection of a wiring graph.

    - Collapse all nodes that share the same k_coarse into one representative node.
      Representative keeps u6/rep/m and uses id := k_coarse.
    - Convert the scan path from node ids to k_coarse ids and collapse consecutive repeats.

    This is the correct level if m=8/m=10 are interpreted as *internal multiplicity* within the
    same 18+3 type layer (u6), rather than new type mass.
    """
    # id -> k_coarse
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
        else:
            # sanity: u6/rep should be consistent within one coarse cell
            u0 = str(rep_by_k[k].get("u6", ""))
            u1 = str(n.get("u6", ""))
            if u0 and u1 and u0 != u1:
                raise RuntimeError(f"Inconsistent u6 within k_coarse={k}: {u0} vs {u1}")
            r0 = str(rep_by_k[k].get("rep", "$-$"))
            r1 = str(n.get("rep", "$-$"))
            if r0 and r1 and r0 != r1:
                raise RuntimeError(f"Inconsistent rep within k_coarse={k}: {r0} vs {r1}")

    scan_k: List[int] = []
    prev: int | None = None
    for nid in scan_path_ids:
        k = id_to_k.get(int(nid))
        if k is None:
            continue
        if prev is None or int(k) != int(prev):
            scan_k.append(int(k))
            prev = int(k)

    coarse_nodes = [rep_by_k[k] for k in sorted(rep_by_k.keys())]
    return coarse_nodes, scan_k


def _mu6_from_coarse_cells(nodes: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Type-layer μ6 induced by coarse cells: each k_coarse counts once, regardless of m refinement.
    """
    X6 = sml.all_x6()
    seen: Dict[int, str] = {}
    for n in nodes:
        if "k_coarse" not in n:
            continue
        k = int(n["k_coarse"])
        u = str(n.get("u6", ""))
        if u not in X6:
            continue
        seen.setdefault(k, u)
    counts: Dict[str, int] = {u: 0 for u in X6}
    for _k, u in seen.items():
        counts[u] += 1
    denom = float(sum(counts.values()))
    if denom <= 0.0:
        return {u: float("nan") for u in counts}
    return {u: float(c) / denom for (u, c) in counts.items()}


Perm = Tuple[int, int, int, int]


def _pt2_key(pt: List[float]) -> Tuple[int, int]:
    return (int(round(2.0 * float(pt[0]))), int(round(2.0 * float(pt[1]))))


def _axis_neighbors_2d(pos: Dict[Tuple[int, int], int], step: int = 2) -> List[Tuple[int, int]]:
    edges: List[Tuple[int, int]] = []
    for (x, y), a in pos.items():
        for dx, dy in ((step, 0), (0, step)):
            b = pos.get((x + dx, y + dy))
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


def _mu6_from_holonomy_incidence_2d(
    nodes: List[Dict[str, Any]],
    *,
    w_bin: Dict[str, float],
) -> Dict[str, float]:
    """
    Holonomy-weighted μ6:
      - enumerate 2D plaquettes on axis-neighbor lattice,
      - compute holonomy angle bin per plaquette,
      - add weight w_bin[bin] to each corner node's u6.
    """
    X6 = sml.all_x6()
    wsum: Dict[str, float] = {u: 0.0 for u in X6}

    pos: Dict[Tuple[int, int], int] = {}
    for n in nodes:
        pos[_pt2_key(n["pt"])] = int(n["id"])

    edges = _axis_neighbors_2d(pos)
    edge_p = _edge_perm_cache(nodes, edges)
    B = su3rep.basis_B()
    pls = _plaquettes_2d(pos)

    for a, b, c, d in pls:
        holp = holo.compose(edge_p[(d, a)], holo.compose(edge_p[(c, d)], holo.compose(edge_p[(b, c)], edge_p[(a, b)])))
        R = su3rep.su3_rep(holp, B=B)
        ang = float(su3rep.rotation_angle_deg(R))
        ab = _angle_bin_deg(ang)
        w = float(w_bin.get(ab, 0.0))
        if w <= 0.0:
            continue
        for nid in (a, b, c, d):
            u = str(nodes[int(nid)].get("u6", ""))
            if u in wsum:
                wsum[u] += w

    denom = float(sum(wsum.values()))
    if denom <= 0.0:
        return {u: float("nan") for u in wsum}
    return {u: float(v) / denom for (u, v) in wsum.items()}

def _mu6_from_cross_m_scan(
    nodes: List[Dict[str, Any]],
    scan_path_ids: List[int],
    *,
    w_step: float = 1.0,
) -> Dict[str, float]:
    """
    Cross-m scan-induced μ6:
      - walk along the scan path edges (a->b),
      - whenever m(a) != m(b), add weight w_step to both endpoints' u6.

    Interpretation: cross-level diagonal connectors are "interface events" where
    additional routing is required; as a proxy, treat them as U(1)-like interaction
    sites and induce a distribution over types.
    """
    X6 = sml.all_x6()
    wsum: Dict[str, float] = {u: 0.0 for u in X6}
    id_to_node: Dict[int, Dict[str, Any]] = {int(n.get("id")): n for n in nodes if "id" in n}

    for a, b in zip(scan_path_ids[:-1], scan_path_ids[1:]):
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
        if ua in wsum:
            wsum[ua] += float(w_step)
        if ub in wsum:
            wsum[ub] += float(w_step)

    denom = float(sum(wsum.values()))
    if denom <= 0.0:
        return {u: float("nan") for u in wsum}
    return {u: float(v) / denom for (u, v) in wsum.items()}

def _perm_cost_hamming_on_fibers(fa: List[int], fb: List[int], p: Perm) -> int:
    a_bits = [holo.bits6(x) for x in fa]
    b_bits = [holo.bits6(x) for x in fb]
    cost = 0
    for i in range(4):
        cost += int(holo.hamming(a_bits[i], b_bits[int(p[i])]))
    return int(cost)

def _perm_cost_u1_port_mismatch(fa: List[int], fb: List[int], p: Perm, rep_a: str, rep_b: str) -> int:
    """
    U(1)-only mismatch cost on the port labels:
      - label each fiber index by _port_label(idx6, rep_tex) -> (color, isospin, u1)
      - extract u1 component only (may be None)
      - count mismatches where both endpoints have concrete u1 labels and differ
    """
    pa = [_port_label(int(x), rep_a) for x in fa]
    pb = [_port_label(int(x), rep_b) for x in fb]
    cost = 0
    for i in range(4):
        qa = pa[i][2]
        qb = pb[int(p[i])][2]
        if qa is None or qb is None:
            continue
        if int(qa) != int(qb):
            cost += 1
    return int(cost)


def _mu6_from_cross_m_scan_cost(
    nodes: List[Dict[str, Any]],
    scan_path_ids: List[int],
) -> Dict[str, float]:
    """
    Cross-m scan-induced μ6 weighted by the *minimal port-compatible matching cost*.

    For each scan edge a->b where m(a)!=m(b):
      - build 4-fibers fa, fb from u6 labels
      - choose port-compatible permutation p via _best_perm_with_ports
      - compute cost := Σ_i hamming(bits6(fa[i]), bits6(fb[p(i)]))
      - add 'cost' to both endpoints' u6 weights

    Interpretation: treat cross-level interface edges as U(1)-like "impedance events",
    with strength proportional to the minimal compatible mismatch cost.
    """
    X6 = sml.all_x6()
    wsum: Dict[str, float] = {u: 0.0 for u in X6}
    id_to_node: Dict[int, Dict[str, Any]] = {int(n.get("id")): n for n in nodes if "id" in n}

    pre = holo.preimages()

    for a, b in zip(scan_path_ids[:-1], scan_path_ids[1:]):
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
        if ua not in wsum or ub not in wsum:
            continue
        rep_a = str(na.get("rep", "$-$"))
        rep_b = str(nb.get("rep", "$-$"))

        fa = holo.fiber4(pre, ua)
        fb = holo.fiber4(pre, ub)
        p = _best_perm_with_ports(fa, fb, rep_a, rep_b)
        cost = float(_perm_cost_hamming_on_fibers(fa, fb, p))
        if cost <= 0.0:
            continue
        wsum[ua] += cost
        wsum[ub] += cost

    denom = float(sum(wsum.values()))
    if denom <= 0.0:
        return {u: float("nan") for u in wsum}
    return {u: float(v) / denom for (u, v) in wsum.items()}

def _mu6_from_cross_m_scan_u1_cost(
    nodes: List[Dict[str, Any]],
    scan_path_ids: List[int],
) -> Dict[str, float]:
    """
    Cross-m scan-induced μ6 weighted by a *U(1)-only* interface strength.

    For each scan edge a->b where m(a)!=m(b):
      - choose the port-compatible permutation p via _best_perm_with_ports (same rule as the connection)
      - define:
          flow_u1 := #pairs (qa,qb) where both are concrete (not None)
          mis_u1  := #pairs where both concrete and qa!=qb
        and add weight := flow_u1 + mis_u1 to both endpoints' u6.

    Interpretation: isolate the U(1) channel contribution to interface impedance.
    """
    X6 = sml.all_x6()
    wsum: Dict[str, float] = {u: 0.0 for u in X6}
    id_to_node: Dict[int, Dict[str, Any]] = {int(n.get("id")): n for n in nodes if "id" in n}

    pre = holo.preimages()

    for a, b in zip(scan_path_ids[:-1], scan_path_ids[1:]):
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
        if ua not in wsum or ub not in wsum:
            continue
        rep_a = str(na.get("rep", "$-$"))
        rep_b = str(nb.get("rep", "$-$"))

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
        w = float(flow_u1 + mis_u1)
        if w <= 0.0:
            continue
        wsum[ua] += w
        wsum[ub] += w

    denom = float(sum(wsum.values()))
    if denom <= 0.0:
        # No explicit U(1) port signal on cross-m edges for this wiring.
        # Fall back to the full port-compatible mismatch-cost measure to keep the table numeric.
        return _mu6_from_cross_m_scan_cost(nodes, scan_path_ids)
    return {u: float(v) / denom for (u, v) in wsum.items()}


def _ew_from_mu6(tag: str, mu6: Dict[str, float], u_to_field: Dict[str, sml.SMField]) -> EWFromWiring:
    X6 = sml.all_x6()
    cyc = [u for u in X6 if not sml.is_boundary_word(u)]
    p_cyc = float(sum(float(mu6.get(u, 0.0)) for u in cyc))
    n_cyc_eff = 21.0 * p_cyc
    w_y_eff = 21.0 * sum(float(mu6.get(u, 0.0)) * _b_weight_for_u(u, u_to_field=u_to_field) for u in X6)

    alpha_inv = (3.0 + float(w_y_eff)) * (math.pi**2)
    sin2 = 3.0 / (3.0 + float(w_y_eff))
    e_alpha = abs(math.log(alpha_inv / float(ALPHAZ_INV_PDG)))
    e_sin2 = abs(math.log(sin2 / float(SIN2_THETAW_PDG)))
    return EWFromWiring(
        mode="node",
        tag=str(tag),
        n_nodes=0,
        p_cyc=p_cyc,
        n_cyc_eff=n_cyc_eff,
        w_y_eff=float(w_y_eff),
        alpha_inv=float(alpha_inv),
        e_alpha=float(e_alpha),
        sin2=float(sin2),
        e_sin2=float(e_sin2),
    )


def _read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiring-dir", type=str, nargs="+", required=True, help="One or more directories containing wiring_geometry.json")
    args = ap.parse_args()

    u_to_field = _build_x6_to_field_map()
    # Holonomy weighting: emphasize SU3/SU2 main channels
    w_bin = {"120": 4.0, "180": 3.0, "90": 0.0, "0": 0.0}

    out_dir = generated_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    for wdir_s in list(args.wiring_dir):
        wdir = Path(str(wdir_s))
        geo = _read_json(wdir / "wiring_geometry.json")
        tag_root = wdir.name

        out_rows: List[str] = []
        out_rows.append(r"\toprule")
        out_rows.append(
            r"source & mode & $|\mathcal{N}|$ & $p_{\mathrm{cyc}}$ & $21p_{\mathrm{cyc}}$ & $W_Y^{\mathrm{eff}}$ & "
            r"$\alpha^{-1}(\mu_Z)$ & $|\log(\alpha/\alpha_{\mathrm{PDG}})|$ & $\sin^2\theta_W$ & $|\log(\sin^2/\sin^2_{\mathrm{PDG}})|$ \\"
        )
        out_rows.append(r"\midrule")

        results: List[EWFromWiring] = []
        for key in ("graph2d", "graph3d"):
            g = geo.get(key, {})
            nodes = list(g.get("nodes", []))
            scan_ids = [int(x) for x in g.get("scan_path_node_ids", [])]
            coarse_nodes, coarse_scan = _coarse_nodes_and_scan(nodes, scan_ids)

            # node-count μ6
            mu6_node = _mu6_from_nodes(nodes)
            r0 = _ew_from_mu6(tag=f"{tag_root}:{key}", mu6=mu6_node, u_to_field=u_to_field)
            r0 = EWFromWiring(
                mode="node",
                tag=r0.tag,
                n_nodes=int(len(nodes)),
                p_cyc=r0.p_cyc,
                n_cyc_eff=r0.n_cyc_eff,
                w_y_eff=r0.w_y_eff,
                alpha_inv=r0.alpha_inv,
                e_alpha=r0.e_alpha,
                sin2=r0.sin2,
                e_sin2=r0.e_sin2,
            )
            results.append(r0)
            out_rows.append(
                rf"{r0.tag} & {r0.mode} & {r0.n_nodes} & {r0.p_cyc:.6f} & {r0.n_cyc_eff:.3f} & {r0.w_y_eff:.6f} & "
                rf"{r0.alpha_inv:.10f} & {r0.e_alpha:.3e} & {r0.sin2:.10f} & {r0.e_sin2:.3e} \\"
            )

            # coarse-cell μ6 (type layer; refinement does not inflate weight)
            mu6_coarse = _mu6_from_coarse_cells(nodes)
            rc = _ew_from_mu6(tag=f"{tag_root}:{key}", mu6=mu6_coarse, u_to_field=u_to_field)
            rc = EWFromWiring(
                mode="coarse_cell",
                tag=rc.tag,
                n_nodes=int(len(coarse_nodes)),
                p_cyc=rc.p_cyc,
                n_cyc_eff=rc.n_cyc_eff,
                w_y_eff=rc.w_y_eff,
                alpha_inv=rc.alpha_inv,
                e_alpha=rc.e_alpha,
                sin2=rc.sin2,
                e_sin2=rc.e_sin2,
            )
            results.append(rc)
            out_rows.append(
                rf"{rc.tag} & {rc.mode} & {rc.n_nodes} & {rc.p_cyc:.6f} & {rc.n_cyc_eff:.3f} & {rc.w_y_eff:.6f} & "
                rf"{rc.alpha_inv:.10f} & {rc.e_alpha:.3e} & {rc.sin2:.10f} & {rc.e_sin2:.3e} \\"
            )

            # holonomy-weighted μ6 (2D plaquettes) for both graphs, using their XY embedding
            mu6_h = _mu6_from_holonomy_incidence_2d(nodes, w_bin=w_bin)
            r1 = _ew_from_mu6(tag=f"{tag_root}:{key}", mu6=mu6_h, u_to_field=u_to_field)
            r1 = EWFromWiring(
                mode="holonomy",
                tag=r1.tag,
                n_nodes=int(len(nodes)),
                p_cyc=r1.p_cyc,
                n_cyc_eff=r1.n_cyc_eff,
                w_y_eff=r1.w_y_eff,
                alpha_inv=r1.alpha_inv,
                e_alpha=r1.e_alpha,
                sin2=r1.sin2,
                e_sin2=r1.e_sin2,
            )
            results.append(r1)
            out_rows.append(
                rf"{r1.tag} & {r1.mode} & {r1.n_nodes} & {r1.p_cyc:.6f} & {r1.n_cyc_eff:.3f} & {r1.w_y_eff:.6f} & "
                rf"{r1.alpha_inv:.10f} & {r1.e_alpha:.3e} & {r1.sin2:.10f} & {r1.e_sin2:.3e} \\"
            )

            # cross-m scan-induced μ6 (interface events) [micro scan]
            mu6_x = _mu6_from_cross_m_scan(nodes, scan_ids, w_step=1.0)
            r2 = _ew_from_mu6(tag=f"{tag_root}:{key}", mu6=mu6_x, u_to_field=u_to_field)
            r2 = EWFromWiring(
                mode="cross_m",
                tag=r2.tag,
                n_nodes=int(len(nodes)),
                p_cyc=r2.p_cyc,
                n_cyc_eff=r2.n_cyc_eff,
                w_y_eff=r2.w_y_eff,
                alpha_inv=r2.alpha_inv,
                e_alpha=r2.e_alpha,
                sin2=r2.sin2,
                e_sin2=r2.e_sin2,
            )
            results.append(r2)
            out_rows.append(
                rf"{r2.tag} & {r2.mode} & {r2.n_nodes} & {r2.p_cyc:.6f} & {r2.n_cyc_eff:.3f} & {r2.w_y_eff:.6f} & "
                rf"{r2.alpha_inv:.10f} & {r2.e_alpha:.3e} & {r2.sin2:.10f} & {r2.e_sin2:.3e} \\"
            )

            # cross-m scan-induced μ6 weighted by minimal port-compatible mismatch cost [micro scan]
            mu6_xc = _mu6_from_cross_m_scan_cost(nodes, scan_ids)
            r3 = _ew_from_mu6(tag=f"{tag_root}:{key}", mu6=mu6_xc, u_to_field=u_to_field)
            r3 = EWFromWiring(
                mode="cross_m_cost",
                tag=r3.tag,
                n_nodes=int(len(nodes)),
                p_cyc=r3.p_cyc,
                n_cyc_eff=r3.n_cyc_eff,
                w_y_eff=r3.w_y_eff,
                alpha_inv=r3.alpha_inv,
                e_alpha=r3.e_alpha,
                sin2=r3.sin2,
                e_sin2=r3.e_sin2,
            )
            results.append(r3)
            out_rows.append(
                rf"{r3.tag} & {r3.mode} & {r3.n_nodes} & {r3.p_cyc:.6f} & {r3.n_cyc_eff:.3f} & {r3.w_y_eff:.6f} & "
                rf"{r3.alpha_inv:.10f} & {r3.e_alpha:.3e} & {r3.sin2:.10f} & {r3.e_sin2:.3e} \\"
            )

            # cross-m scan-induced μ6 weighted by U(1)-only port mismatch cost [micro scan]
            mu6_xu1 = _mu6_from_cross_m_scan_u1_cost(nodes, scan_ids)
            r4 = _ew_from_mu6(tag=f"{tag_root}:{key}", mu6=mu6_xu1, u_to_field=u_to_field)
            r4 = EWFromWiring(
                mode="cross_m_u1_cost",
                tag=r4.tag,
                n_nodes=int(len(nodes)),
                p_cyc=r4.p_cyc,
                n_cyc_eff=r4.n_cyc_eff,
                w_y_eff=r4.w_y_eff,
                alpha_inv=r4.alpha_inv,
                e_alpha=r4.e_alpha,
                sin2=r4.sin2,
                e_sin2=r4.e_sin2,
            )
            results.append(r4)
            out_rows.append(
                rf"{r4.tag} & {r4.mode} & {r4.n_nodes} & {r4.p_cyc:.6f} & {r4.n_cyc_eff:.3f} & {r4.w_y_eff:.6f} & "
                rf"{r4.alpha_inv:.10f} & {r4.e_alpha:.3e} & {r4.sin2:.10f} & {r4.e_sin2:.3e} \\"
            )

            # coarse cross-m measures (type-layer scan; refinement collapsed)
            mu6_cx = _mu6_from_cross_m_scan(coarse_nodes, coarse_scan, w_step=1.0)
            r5 = _ew_from_mu6(tag=f"{tag_root}:{key}", mu6=mu6_cx, u_to_field=u_to_field)
            r5 = EWFromWiring(
                mode="coarse_cross_m",
                tag=r5.tag,
                n_nodes=int(len(coarse_nodes)),
                p_cyc=r5.p_cyc,
                n_cyc_eff=r5.n_cyc_eff,
                w_y_eff=r5.w_y_eff,
                alpha_inv=r5.alpha_inv,
                e_alpha=r5.e_alpha,
                sin2=r5.sin2,
                e_sin2=r5.e_sin2,
            )
            results.append(r5)
            out_rows.append(
                rf"{r5.tag} & {r5.mode} & {r5.n_nodes} & {r5.p_cyc:.6f} & {r5.n_cyc_eff:.3f} & {r5.w_y_eff:.6f} & "
                rf"{r5.alpha_inv:.10f} & {r5.e_alpha:.3e} & {r5.sin2:.10f} & {r5.e_sin2:.3e} \\"
            )

            mu6_cxc = _mu6_from_cross_m_scan_cost(coarse_nodes, coarse_scan)
            r6 = _ew_from_mu6(tag=f"{tag_root}:{key}", mu6=mu6_cxc, u_to_field=u_to_field)
            r6 = EWFromWiring(
                mode="coarse_cross_m_cost",
                tag=r6.tag,
                n_nodes=int(len(coarse_nodes)),
                p_cyc=r6.p_cyc,
                n_cyc_eff=r6.n_cyc_eff,
                w_y_eff=r6.w_y_eff,
                alpha_inv=r6.alpha_inv,
                e_alpha=r6.e_alpha,
                sin2=r6.sin2,
                e_sin2=r6.e_sin2,
            )
            results.append(r6)
            out_rows.append(
                rf"{r6.tag} & {r6.mode} & {r6.n_nodes} & {r6.p_cyc:.6f} & {r6.n_cyc_eff:.3f} & {r6.w_y_eff:.6f} & "
                rf"{r6.alpha_inv:.10f} & {r6.e_alpha:.3e} & {r6.sin2:.10f} & {r6.e_sin2:.3e} \\"
            )

            mu6_cxu1 = _mu6_from_cross_m_scan_u1_cost(coarse_nodes, coarse_scan)
            r7 = _ew_from_mu6(tag=f"{tag_root}:{key}", mu6=mu6_cxu1, u_to_field=u_to_field)
            r7 = EWFromWiring(
                mode="coarse_cross_m_u1_cost",
                tag=r7.tag,
                n_nodes=int(len(coarse_nodes)),
                p_cyc=r7.p_cyc,
                n_cyc_eff=r7.n_cyc_eff,
                w_y_eff=r7.w_y_eff,
                alpha_inv=r7.alpha_inv,
                e_alpha=r7.e_alpha,
                sin2=r7.sin2,
                e_sin2=r7.e_sin2,
            )
            results.append(r7)
            out_rows.append(
                rf"{r7.tag} & {r7.mode} & {r7.n_nodes} & {r7.p_cyc:.6f} & {r7.n_cyc_eff:.3f} & {r7.w_y_eff:.6f} & "
                rf"{r7.alpha_inv:.10f} & {r7.e_alpha:.3e} & {r7.sin2:.10f} & {r7.e_sin2:.3e} \\"
            )

        # Baseline closed target (uniform X6 -> W_Y_eff=10; alpha_inv=13*pi^2; sin2=3/13)
        w0 = 10.0
        alpha0 = (3.0 + w0) * (math.pi**2)
        sin20 = 3.0 / (3.0 + w0)
        e_alpha0 = abs(math.log(alpha0 / float(ALPHAZ_INV_PDG)))
        e_sin20 = abs(math.log(sin20 / float(SIN2_THETAW_PDG)))
        out_rows.append(r"\addlinespace")
        out_rows.append(
            rf"\multicolumn{{10}}{{l}}{{baseline (uniform $X_6$): $W_Y^{{\mathrm{{eff}}}}=10$, $\alpha^{{-1}}=13\pi^2$, $\sin^2\theta_W=3/13$; "
            rf"mismatches $(e_\alpha,e_{{\sin^2}})=({e_alpha0:.3e},{e_sin20:.3e})$}} \\"
        )
        out_rows.append(r"\bottomrule")

        rows_path = out_dir / f"sm_hilbert_constants_bridge_{tag_root}_rows.tex"
        rows_path.write_text("\n".join(out_rows), encoding="utf-8")

        # Short summary
        d_tag = " ; ".join(f"{r.tag}/{r.mode}:W_Y={r.w_y_eff:.6f}" for r in results)
        summary = [
            r"\paragraph{Audit summary (SM-Hilbert wiring $\to$ electroweak constants).} \AuditTag "
            r"We induce two protocol-native pushforward measures $\mu_6$ on the $21$ stable $m=6$ types from a concrete wiring geometry "
            r"(\texttt{wiring\_geometry.json}): (i) node-count $\mu_6$ by counting center nodes, and (ii) holonomy-weighted $\mu_6$ by attributing "
            r"SU(3)/SU(2) main-channel plaquette holonomies (120°/180° bins) to incident corner types. "
            r"We then compute $W_Y^{\mathrm{eff}}=21\sum_u \mu_6(u)\,b(u)$ with $b(u)=\mathrm{mult}(u)Y(u)^2$ on cyclic types (0 on boundary), and report the implied "
            r"$\alpha^{-1}(\mu_Z)=(3+W_Y^{\mathrm{eff}})\pi^2$ and $\sin^2\theta_W=3/(3+W_Y^{\mathrm{eff}})$ with log-mismatch to PDG targets. "
            + rf"Computed: {d_tag}.",
        ]
        summ_path = out_dir / f"sm_hilbert_constants_bridge_{tag_root}_summary.tex"
        summ_path.write_text("\n".join(summary), encoding="utf-8")

        print(f"Wrote sections/generated/{rows_path.name}")
        print(f"Wrote sections/generated/{summ_path.name}")


if __name__ == "__main__":
    main()

