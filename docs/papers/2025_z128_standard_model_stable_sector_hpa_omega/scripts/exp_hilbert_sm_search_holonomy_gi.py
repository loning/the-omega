# -*- coding: utf-8 -*-
"""
Search experiment: find wiring candidates that satisfy:
  1) 2D/3D type-transition graph signature match (18+3 layer GI)
  2) holonomy-by-representation patterns are similar between 2D/3D (SU2/SU3 layer match)

We score candidates by:
  - type_sig_match (hard gate)
  - holonomy distance on per-rep angle fractions (0/90/120/180)
  - simple "separation" objective: colored reps (su3_dim=3) should have higher 120° fraction than colorless.

Outputs:
  figures/adaptive/sm_hilbert_isomorphism/data/sm_hilbert_holonomy_gi_search_report.json
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re

from common_paths import figures_dir
from common_progress import ProgressEvery

from hilbert_sm_center_graph import BuildConstraints, build_center_graph_fixed
from hilbert_sm_canonical import canonical_signature_type_transition_graph
from hilbert_sm_holonomy import holonomy_summary_from_spatial_type_graph_2d, holonomy_summary_from_spatial_type_graph_3d
from hilbert_sm_schedule_search import sample_richer_schedule, schedule_stats
import exp_sm_labeling_solver as sml
import exp_holonomy_loops as holo
from hilbert_sm_holonomy import _best_perm_with_ports


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


def _w_y_eff_from_coarse_cells(g: Any, u_to_field: Dict[str, sml.SMField]) -> float:
    """
    Type-layer (coarse) electroweak weight:
      μ6(u) induced by unique k_coarse cells (each coarse cell counts once),
      then W_Y_eff := 21 * Σ μ6(u) b(u).
    """
    X6 = sml.all_x6()
    seen: Dict[int, str] = {}
    for n in g.nodes:
        seen.setdefault(int(n.k_coarse), str(n.u6))
    counts: Dict[str, int] = {u: 0 for u in X6}
    for _k, u in seen.items():
        if u in counts:
            counts[u] += 1
    denom = float(sum(counts.values()))
    if denom <= 0.0:
        return float("nan")
    mu6 = {u: float(c) / denom for (u, c) in counts.items()}
    return 21.0 * sum(mu6[u] * _b_weight_for_u(u, u_to_field=u_to_field) for u in X6)


Perm = Tuple[int, int, int, int]


def _coarse_project(g: Any) -> Tuple[List[Dict[str, Any]], List[int]]:
    """
    Coarse projection used by constants-bridge:
      - collapse nodes by k_coarse into representatives (id := k_coarse),
      - project scan_path ids to k_coarse ids and collapse consecutive repeats.
    """
    id_to_k: Dict[int, int] = {}
    rep_by_k: Dict[int, Dict[str, Any]] = {}
    for n in g.nodes:
        nid = int(n.id)
        k = int(n.k_coarse)
        id_to_k[nid] = k
        if k not in rep_by_k:
            rep_by_k[k] = {
                "id": int(k),
                "k_coarse": int(k),
                "u6": str(n.u6),
                "rep": str(n.rep_tex),
                "m": int(n.m),
            }
        else:
            # sanity: u6/rep should be consistent within one coarse cell
            if str(rep_by_k[k].get("u6", "")) and str(n.u6) and str(rep_by_k[k]["u6"]) != str(n.u6):
                raise RuntimeError(f"Inconsistent u6 within k_coarse={k}: {rep_by_k[k]['u6']} vs {n.u6}")
            if str(rep_by_k[k].get("rep", "")) and str(n.rep_tex) and str(rep_by_k[k]["rep"]) != str(n.rep_tex):
                raise RuntimeError(f"Inconsistent rep within k_coarse={k}: {rep_by_k[k]['rep']} vs {n.rep_tex}")

    scan_k: List[int] = []
    prev: int | None = None
    for nid in g.scan_path:
        k = id_to_k.get(int(nid))
        if k is None:
            continue
        if prev is None or int(k) != int(prev):
            scan_k.append(int(k))
            prev = int(k)
    coarse_nodes = [rep_by_k[k] for k in sorted(rep_by_k.keys())]
    return coarse_nodes, scan_k


def _perm_cost_hamming_on_fibers(fa: List[int], fb: List[int], p: Perm) -> int:
    a_bits = [holo.bits6(x) for x in fa]
    b_bits = [holo.bits6(x) for x in fb]
    cost = 0
    for i in range(4):
        cost += int(holo.hamming(a_bits[i], b_bits[int(p[i])]))
    return int(cost)


def _mu6_from_cross_m_scan_cost(nodes: List[Dict[str, Any]], scan_path_ids: List[int]) -> Dict[str, float]:
    """
    Cross-m scan-induced μ6 weighted by the minimal port-compatible matching cost.
    Mirrors exp_hilbert_sm_constants_bridge._mu6_from_cross_m_scan_cost.
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


def _w_y_eff_from_mu6(mu6: Dict[str, float], u_to_field: Dict[str, sml.SMField]) -> float:
    X6 = sml.all_x6()
    return 21.0 * sum(float(mu6.get(u, 0.0)) * _b_weight_for_u(u, u_to_field=u_to_field) for u in X6)


def _euclid(a: List[float] | Tuple[float, ...], b: List[float] | Tuple[float, ...]) -> float:
    return float(math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b))))


def _interface_metrics_from_scan_edges(g: Any) -> Dict[str, Any]:
    """
    Compute basic cross-m (m!=m') interface diagnostics on the scan edges:
      - n_cross: number of cross-m scan edges
      - len_{mean,max,sum}: Euclidean lengths (in the embedding used by CenterGraph)
      - pairs: counts by m->m' direction (e.g., "6->8")
      - n_direct_6_10: number of direct 6<->10 edges (both directions)
    """
    n_cross = 0
    lens: List[float] = []
    pairs: Dict[str, int] = {}

    for a_id, b_id in getattr(g, "scan_edges", []):
        a = g.nodes[int(a_id)]
        b = g.nodes[int(b_id)]
        ma = int(getattr(a, "m", 6))
        mb = int(getattr(b, "m", 6))
        if ma == mb:
            continue
        n_cross += 1
        pairs[f"{ma}->{mb}"] = int(pairs.get(f"{ma}->{mb}", 0)) + 1
        lens.append(_euclid(list(a.pt), list(b.pt)))

    n_direct_6_10 = int(pairs.get("6->10", 0)) + int(pairs.get("10->6", 0))

    if n_cross <= 0:
        return {
            "n_cross": 0,
            "len_mean": float("inf"),
            "len_max": float("inf"),
            "len_sum": float("inf"),
            "pairs": dict(sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))),
            "n_direct_6_10": n_direct_6_10,
        }

    return {
        "n_cross": int(n_cross),
        "len_mean": float(sum(lens) / len(lens)),
        "len_max": float(max(lens)),
        "len_sum": float(sum(lens)),
        "pairs": dict(sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))),
        "n_direct_6_10": int(n_direct_6_10),
    }


def _interface_score_from_metrics(
    met: Dict[str, Any],
    *,
    w_count: float,
    w_mean: float,
    w_max: float,
    w_sum: float,
    w_direct_6_10: float,
) -> float:
    """
    Lower is better.
    We reward more cross-m edges and penalize long/rare interfaces.
    """
    n_cross = int(met.get("n_cross", 0))
    len_mean = float(met.get("len_mean", float("inf")))
    len_max = float(met.get("len_max", float("inf")))
    len_sum = float(met.get("len_sum", float("inf")))
    n_610 = int(met.get("n_direct_6_10", 0))
    return float((-w_count * n_cross) + w_mean * len_mean + w_max * len_max + w_sum * len_sum + w_direct_6_10 * n_610)


def refined_ks(sched: Dict[int, int]) -> List[int]:
    return sorted([int(k) for k, m in sched.items() if int(m) > 6])


def sample_choice(rng: random.Random, ks: List[int], n_opts: int) -> Dict[int, int]:
    return {int(k): int(rng.randrange(int(n_opts))) for k in ks}


def _rep_distance(a: Dict[str, Dict[str, float]], b: Dict[str, Dict[str, float]]) -> float:
    """
    L1 distance across shared rep keys and angle bins.
    Missing reps are ignored (search-time robustness).
    """
    keys = sorted(set(a.keys()) & set(b.keys()))
    if not keys:
        return float("inf")
    dist = 0.0
    for k in keys:
        for ang in ("0", "90", "120", "180"):
            va = float(a[k].get(ang, float("nan")))
            vb = float(b[k].get(ang, float("nan")))
            if va != va or vb != vb:
                continue
            dist += abs(va - vb)
    return float(dist)

def _rep_distance_weighted(
    a: Dict[str, Dict[str, float]],
    b: Dict[str, Dict[str, float]],
    ca: Dict[str, int] | None = None,
    cb: Dict[str, int] | None = None,
) -> float:
    """
    Weighted distance emphasizing 120° and 180° bins (SU3/SU2 proxies),
    with optional per-rep sample-count weighting (use min(count_a, count_b)).
    """
    keys = sorted(set(a.keys()) & set(b.keys()))
    if not keys:
        return float("inf")
    w = {"120": 4.0, "180": 3.0, "90": 0.0, "0": 0.0}
    dist = 0.0
    wsum = 0.0
    for k in keys:
        wk = 1.0
        if ca is not None and cb is not None:
            wk = float(min(int(ca.get(k, 0)), int(cb.get(k, 0))))
            if wk <= 0.0:
                continue
        for ang in ("0", "90", "120", "180"):
            va = float(a[k].get(ang, float("nan")))
            vb = float(b[k].get(ang, float("nan")))
            if va != va or vb != vb:
                continue
            dist += wk * float(w[ang]) * abs(va - vb)
            wsum += wk * float(w[ang])
    if wsum <= 0.0:
        return float("inf")
    return float(dist / wsum)


def _colored_vs_colorless_separation(per_rep: Dict[str, Dict[str, float]]) -> float:
    """
    Simple SU(3) separation proxy:
      mean frac(120°) over colored reps (key starts with "(3,") minus mean over colorless "(1,".
    """
    col = []
    ncol = []
    for k, frac in per_rep.items():
        v = float(frac.get("120", float("nan")))
        if v != v:
            continue
        if k.startswith("(3,"):
            col.append(v)
        elif k.startswith("(1,"):
            ncol.append(v)
    if not col or not ncol:
        return float("nan")
    return float(sum(col) / len(col) - sum(ncol) / len(ncol))

def _parse_su_dims(rep_key: str) -> Tuple[int, int] | None:
    m = re.match(r"^\((\d+),(\d+)\)_", str(rep_key))
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def _doublet_vs_singlet_pi_separation(per_rep: Dict[str, Dict[str, float]]) -> float:
    """
    SU(2) separation proxy:
      mean frac(180°) over SU(2) doublets (su2_dim=2) minus mean over singlets (su2_dim=1).
    """
    dbl = []
    sng = []
    for k, frac in per_rep.items():
        dims = _parse_su_dims(k)
        if dims is None:
            continue
        _su3, su2 = dims
        v = float(frac.get("180", float("nan")))
        if v != v:
            continue
        if su2 == 2:
            dbl.append(v)
        elif su2 == 1:
            sng.append(v)
    if not dbl or not sng:
        return float("nan")
    return float(sum(dbl) / len(dbl) - sum(sng) / len(sng))


def main() -> None:
    out_root = figures_dir() / "adaptive" / "sm_hilbert_isomorphism"
    out_data = out_root / "data"
    out_data.mkdir(parents=True, exist_ok=True)

    u_to_field = _build_x6_to_field_map()

    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-start", type=int, default=0)
    ap.add_argument("--seed-count", type=int, default=20)
    ap.add_argument("--schedules-per-seed", type=int, default=20)
    ap.add_argument("--micro-per-schedule", type=int, default=30)
    ap.add_argument("--time-limit-s", type=float, default=570.0)
    ap.add_argument("--resume-best", action="store_true", help="Load existing report and keep the best score across runs.")
    ap.add_argument("--early-stop", action="store_true", help="Stop when a (rare) 'good enough' physics match is found.")
    ap.add_argument("--w-y-weight", type=float, default=2.0, help="Weight for coarse W_Y penalty in score.")
    ap.add_argument("--interface-scale", type=float, default=0.02, help="Scale factor for interface score term (0 disables).")
    ap.add_argument("--iface-w-count", type=float, default=2.0)
    ap.add_argument("--iface-w-mean", type=float, default=1.0)
    ap.add_argument("--iface-w-max", type=float, default=0.7)
    ap.add_argument("--iface-w-sum", type=float, default=0.02)
    ap.add_argument("--iface-w-direct-6-10", type=float, default=2.5)
    args = ap.parse_args()

    # Search config
    cons = BuildConstraints(enforce_edge_types=False, enforce_noncrossing_xy=False, forbid_passing_through_centers=False)
    seeds = list(range(int(args.seed_start), int(args.seed_start) + int(args.seed_count)))
    schedules_per_seed = int(args.schedules_per_seed)
    micro_per_schedule = int(args.micro_per_schedule)
    time_limit_s = float(args.time_limit_s)
    wy_weight = float(args.w_y_weight)
    iface_scale = float(args.interface_scale)
    iface_w_count = float(args.iface_w_count)
    iface_w_mean = float(args.iface_w_mean)
    iface_w_max = float(args.iface_w_max)
    iface_w_sum = float(args.iface_w_sum)
    iface_w_610 = float(args.iface_w_direct_6_10)
    # These targets are deliberately small; current holonomy proxies are sparse and quantized.
    target_su3_sep = 0.005
    target_su2_sep = 0.005
    target_wy = 10.0

    # When running under a wall-clock time limit, the % of the theoretical budget is misleading.
    # Use open-ended progress (i counter only) to indicate "how much data we actually produced".
    total: Optional[int] = None
    pe = ProgressEvery(label="exp_sm_hilbert_holonomy_gi_search", total=total, interval_s=60.0)
    pe.start()

    t0 = time.time()
    best: Optional[Dict[str, Any]] = None
    best_match: Optional[Dict[str, Any]] = None

    out_json = out_data / "sm_hilbert_holonomy_gi_search_report.json"
    prev_completed = 0
    if bool(args.resume_best) and out_json.exists():
        try:
            prev = json.loads(out_json.read_text(encoding="utf-8"))
            if isinstance(prev, dict):
                prev_completed = int(prev.get("completed_jobs", 0) or 0)
                pb = prev.get("best")
                if isinstance(pb, dict) and "score" in pb:
                    # Only resume if the stored best matches the current objective schema.
                    if "w_y_eff_coarse_cross_m_cost_2d" in pb:
                        best = pb
                if bool(args.early_stop):
                    pm = prev.get("best_match")
                    if isinstance(pm, dict) and "score" in pm:
                        best_match = pm
        except Exception:
            pass

    i = 0
    for seed in seeds:
        rng = random.Random(int(seed))
        for si in range(schedules_per_seed):
            if (time.time() - t0) > time_limit_s:
                break
            sched = sample_richer_schedule(rng, k_lo=18, k_hi=52)
            ks = refined_ks(sched)
            sst = schedule_stats(sched, k_min=18, k_max=52)
            for _ in range(micro_per_schedule):
                if (time.time() - t0) > time_limit_s:
                    break
                pe.maybe(i, extra=f"seed={seed} sch={si} chg={sst.n_changed} sw={sst.n_switches} maxm={sst.max_m}")
                i += 1

                choice2 = sample_choice(rng, ks, n_opts=16)
                choice3 = sample_choice(rng, ks, n_opts=48)
                try:
                    g2 = build_center_graph_fixed(dim=2, m_by_k=sched, chosen_micro_option=choice2, max_micro_orders=16, constraints=cons)
                    g3 = build_center_graph_fixed(dim=3, m_by_k=sched, chosen_micro_option=choice3, max_micro_orders=48, constraints=cons)
                except Exception:
                    continue

                type2 = canonical_signature_type_transition_graph(g2)
                type3 = canonical_signature_type_transition_graph(g3)
                if type2 != type3:
                    continue

                # Holonomy on *spatial type graph* induced by center-node axis adjacency.
                # This carrier produces many short cycles and is a better proxy for gauge holonomy.
                n2 = [{"id": n.id, "pt": [n.pt[0], n.pt[1]], "u6": n.u6, "rep": n.rep_tex} for n in g2.nodes]
                n3 = [{"id": n.id, "pt": [n.pt[0], n.pt[1], n.pt[2]], "u6": n.u6, "rep": n.rep_tex} for n in g3.nodes]
                h2 = holonomy_summary_from_spatial_type_graph_2d(nodes=n2, max_cycle_len=6)
                h3 = holonomy_summary_from_spatial_type_graph_3d(nodes=n3, max_cycle_len=6)

                d_rep = _rep_distance_weighted(h2.per_rep_angle_frac, h3.per_rep_angle_frac, h2.per_rep_count, h3.per_rep_count)
                sep2 = _colored_vs_colorless_separation(h2.per_rep_angle_frac)
                sep3 = _colored_vs_colorless_separation(h3.per_rep_angle_frac)
                sep_pen = 0.0
                if sep2 == sep2 and sep3 == sep3:
                    # Prefer both to be positive, above target, and similar.
                    sep_pen = abs(sep2 - sep3)
                    sep_pen += max(0.0, float(target_su3_sep) - float(sep2))
                    sep_pen += max(0.0, float(target_su3_sep) - float(sep3))
                else:
                    sep_pen = 10.0

                pi2 = _doublet_vs_singlet_pi_separation(h2.per_rep_angle_frac)
                pi3 = _doublet_vs_singlet_pi_separation(h3.per_rep_angle_frac)
                pi_pen = 0.0
                if pi2 == pi2 and pi3 == pi3:
                    pi_pen = abs(pi2 - pi3)
                    pi_pen += max(0.0, float(target_su2_sep) - float(pi2))
                    pi_pen += max(0.0, float(target_su2_sep) - float(pi3))
                else:
                    pi_pen = 10.0

                # Type-layer electroweak weight induced by *coarse cross-m cost* (wiring dependent): should be close to 10.
                c2_nodes, c2_scan = _coarse_project(g2)
                c3_nodes, c3_scan = _coarse_project(g3)
                mu2 = _mu6_from_cross_m_scan_cost(c2_nodes, c2_scan)
                mu3 = _mu6_from_cross_m_scan_cost(c3_nodes, c3_scan)
                wy2 = float(_w_y_eff_from_mu6(mu2, u_to_field=u_to_field))
                wy3 = float(_w_y_eff_from_mu6(mu3, u_to_field=u_to_field))
                wy_pen = 0.0
                if wy2 == wy2 and wy3 == wy3:
                    wy_pen = abs(wy2 - float(target_wy)) + abs(wy3 - float(target_wy)) + 0.5 * abs(wy2 - wy3)
                else:
                    wy_pen = 10.0

                # Cross-m interface diagnostics on the *actual scan edges* (not coarse collapsed).
                iface2 = _interface_metrics_from_scan_edges(g2)
                iface3 = _interface_metrics_from_scan_edges(g3)
                iface_score2 = _interface_score_from_metrics(
                    iface2,
                    w_count=iface_w_count,
                    w_mean=iface_w_mean,
                    w_max=iface_w_max,
                    w_sum=iface_w_sum,
                    w_direct_6_10=iface_w_610,
                )
                iface_score3 = _interface_score_from_metrics(
                    iface3,
                    w_count=iface_w_count,
                    w_mean=iface_w_mean,
                    w_max=iface_w_max,
                    w_sum=iface_w_sum,
                    w_direct_6_10=iface_w_610,
                )
                iface_score = 0.5 * float(iface_score2 + iface_score3)

                score = float(d_rep + 4.0 * sep_pen + 3.0 * pi_pen + float(wy_weight) * wy_pen + float(iface_scale) * iface_score)
                cand = {
                    "score": score,
                    "rep_distance_L1": d_rep,
                    "sep2_col_minus_ncol_120": sep2,
                    "sep3_col_minus_ncol_120": sep3,
                    "pi2_doublet_minus_singlet_180": pi2,
                    "pi3_doublet_minus_singlet_180": pi3,
                    "w_y_eff_coarse_cross_m_cost_2d": wy2,
                    "w_y_eff_coarse_cross_m_cost_3d": wy3,
                    "w_y_eff_target": float(target_wy),
                    "w_y_pen": wy_pen,
                    "iface_scale": float(iface_scale),
                    "iface_weights": {
                        "w_count": float(iface_w_count),
                        "w_mean": float(iface_w_mean),
                        "w_max": float(iface_w_max),
                        "w_sum": float(iface_w_sum),
                        "w_direct_6_10": float(iface_w_610),
                    },
                    "iface_score_2d": float(iface_score2),
                    "iface_score_3d": float(iface_score3),
                    "iface_score": float(iface_score),
                    "iface_2d": iface2,
                    "iface_3d": iface3,
                    "constraints": asdict(cons),
                    "m_schedule_by_k": {str(k): int(v) for k, v in sorted(sched.items())},
                    "schedule_stats_18_52": asdict(sst),
                    "choice2": {str(k): int(v) for k, v in sorted(choice2.items())},
                    "choice3": {str(k): int(v) for k, v in sorted(choice3.items())},
                    "type_sig": type2,
                    "holonomy": {
                        "2d": {"angle_frac": h2.angle_frac, "cycle_type_hist": h2.cycle_type_hist, "n_cycles": h2.n_cycles, "cycle_len_hist": h2.cycle_len_hist},
                        "3d": {"angle_frac": h3.angle_frac, "cycle_type_hist": h3.cycle_type_hist, "n_cycles": h3.n_cycles, "cycle_len_hist": h3.cycle_len_hist},
                    },
                }

                if best is None or score < float(best["score"]):
                    best = cand

                # Optional early stop for a "good enough" physics match.
                if bool(args.early_stop):
                    if d_rep < 0.05 and sep_pen < 0.002 and pi_pen < 0.002 and wy_pen < 0.25:
                        best_match = cand
                        break
            if best_match is not None:
                break
        if best_match is not None:
            break

    out = {
        "search_budget": {"seeds": seeds, "schedules_per_seed": schedules_per_seed, "micro_per_schedule": micro_per_schedule, "time_limit_s": time_limit_s},
        "completed_jobs": int(prev_completed) + int(i),
        "completed_jobs_this_run": int(i),
        "wall_clock_seconds": time.time() - t0,
        "best": best,
        "best_match": best_match,
    }

    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    pe.done(extra=f"wrote {out_json}")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()

