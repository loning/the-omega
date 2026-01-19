#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Strong numeric-first search: electroweak constants + U(1) alpha-link audit.

We jointly optimize:
  - EW: alpha^{-1}(m_Z) and sin^2(theta_W) implied by W_Y_eff from node-count μ6(u),
        using log-mismatch to PDG targets.
  - U(1): cross-m interface strengths -> alpha link, using the same bounded-family aggregation +
        scale-family minimax log-mismatch as exp_hilbert_sm_u1_alpha_link_audit.py (mode=flow_plus_mis),
        matching BOTH alpha_em^{-1} (CODATA) and alpha^{-1}(m_Z) (PDG).

Outputs:
  figures/adaptive/sm_hilbert_isomorphism/data/sm_hilbert_numeric_match_strong_search_report.json
  figures/adaptive/sm_hilbert_isomorphism/wiring_fold_geometry_numeric_match_strong/
    - wiring_geometry.json
    - wiring_3d_perspective_annotated.png

English-only output.
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import random
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from common_constants import (
    ALPHA_INV_CODATA_2022,
    ALPHAZ_INV_PDG,
    SIN2_THETAW_PDG,
)
from common_paths import figures_dir
from common_progress import ProgressEvery

import alpha_running as arun
import exp_holonomy_loops as holo
import exp_sm_labeling_solver as sml
from hilbert_sm_center_graph import BuildConstraints, build_center_graph_fixed
from hilbert_sm_canonical import canonical_signature_center_graph, canonical_signature_type_transition_graph
from hilbert_sm_holonomy import _best_perm_with_ports, _port_label
from hilbert_sm_schedule_search import sample_hierarchical_schedule, sample_richer_schedule, sample_unimodal_schedule, schedule_stats


Perm = Tuple[int, int, int, int]


def _build_x6_to_field_map() -> Dict[str, sml.SMField]:
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
            continue
        counts[u] += 1
    denom = float(sum(counts.values()))
    if denom <= 0.0:
        return {u: float("nan") for u in counts}
    return {u: float(c) / denom for (u, c) in counts.items()}


def _mu6_from_coarse_cells(nodes: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Type-layer μ6 induced by coarse cells: each k_coarse counts once, regardless of m refinement.
    Mirrors exp_hilbert_sm_constants_bridge._mu6_from_coarse_cells.
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


def _w_y_eff_from_mu6(mu6: Dict[str, float], u_to_field: Dict[str, sml.SMField]) -> float:
    X6 = sml.all_x6()
    return 21.0 * sum(float(mu6.get(u, 0.0)) * _b_weight_for_u(u, u_to_field=u_to_field) for u in X6)


def _ew_from_wy(wy: float) -> Dict[str, float]:
    alpha_inv = (3.0 + float(wy)) * (math.pi**2)
    sin2 = 3.0 / (3.0 + float(wy))
    e_alpha = abs(math.log(alpha_inv / float(ALPHAZ_INV_PDG)))
    e_sin2 = abs(math.log(sin2 / float(SIN2_THETAW_PDG)))
    return {
        "w_y_eff": float(wy),
        "alpha_inv": float(alpha_inv),
        "sin2": float(sin2),
        "e_alpha": float(e_alpha),
        "e_sin2": float(e_sin2),
        "e_sum": float(e_alpha + e_sin2),
    }


def _ew_from_mu6(mu6: Dict[str, float], *, u_to_field: Dict[str, sml.SMField]) -> Dict[str, float]:
    wy = _w_y_eff_from_mu6(mu6, u_to_field=u_to_field)
    out = _ew_from_wy(wy)
    X6 = sml.all_x6()
    cyc = [u for u in X6 if not sml.is_boundary_word(u)]
    p_cyc = float(sum(float(mu6.get(u, 0.0)) for u in cyc))
    out["p_cyc"] = float(p_cyc)
    out["n_cyc_eff"] = float(21.0 * p_cyc)
    return out


def _ew_score_from_modes(
    ew2: Dict[str, float],
    ew3: Dict[str, float],
    *,
    w_dim_consistency: float = 1.0,
) -> float:
    """
    Unified audit-norm objective (lower is better).
      - average log-mismatch to PDG targets (already encoded in e_sum)
      - add a dimension-consistency penalty in the same log geometry on W_Y.
    """
    e_avg = 0.5 * (float(ew2.get("e_sum", float("inf"))) + float(ew3.get("e_sum", float("inf"))))
    wy2 = float(ew2.get("w_y_eff", float("nan")))
    wy3 = float(ew3.get("w_y_eff", float("nan")))
    if not (math.isfinite(wy2) and math.isfinite(wy3) and wy2 > 0.0 and wy3 > 0.0):
        e_dim = float("inf")
    else:
        e_dim = abs(math.log(wy2 / wy3))
    return float(e_avg + float(w_dim_consistency) * float(e_dim))


def refined_ks(sched: Dict[int, int]) -> List[int]:
    return sorted([int(k) for k, m in sched.items() if int(m) > 6])


def sample_choice(rng: random.Random, ks: List[int], n_opts: int) -> Dict[int, int]:
    return {int(k): int(rng.randrange(int(n_opts))) for k in ks}


def sample_schedule(rng: random.Random, *, schedule_family: str, k_lo: int, k_hi: int) -> Tuple[Dict[int, int], str]:
    """
    Finite schedule-family selector (auditable):
      - richer: sample_richer_schedule
      - hierarchical: sample_hierarchical_schedule
      - unimodal: sample_unimodal_schedule
      - mix: fixed mixture over the above families
    Returns (schedule, family_id).
    """
    fam = str(schedule_family)
    if fam == "richer":
        return sample_richer_schedule(rng, k_lo=k_lo, k_hi=k_hi), "richer"
    if fam == "hierarchical":
        return sample_hierarchical_schedule(rng, k_lo=k_lo, k_hi=k_hi), "hierarchical"
    if fam == "unimodal":
        return sample_unimodal_schedule(rng, k_lo=k_lo, k_hi=k_hi), "unimodal"
    if fam != "mix":
        raise ValueError(f"Unknown schedule_family={fam}")

    r = float(rng.random())
    if r < 0.55:
        return sample_richer_schedule(rng, k_lo=k_lo, k_hi=k_hi), "richer"
    if r < 0.80:
        return sample_unimodal_schedule(rng, k_lo=k_lo, k_hi=k_hi), "unimodal"
    return sample_hierarchical_schedule(rng, k_lo=k_lo, k_hi=k_hi), "hierarchical"


def _coarse_project(nodes: List[Dict[str, Any]], scan_ids: List[int]) -> Tuple[List[Dict[str, Any]], List[int]]:
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
    for nid in scan_ids:
        k = id_to_k.get(int(nid))
        if k is None:
            continue
        if prev is None or int(k) != int(prev):
            scan_k.append(int(k))
            prev = int(k)
    coarse_nodes = [rep_by_k[k] for k in sorted(rep_by_k.keys())]
    return coarse_nodes, scan_k


def _u1_alpha_link_best_joint(
    groups: Dict[str, Sequence[float]], *, alpha_low: float, alpha_z: float
) -> Dict[str, Any]:
    """
    Joint bounded-family audit:
      choose ONE (aggregation, scale) to minimize the worst-case minimax log-mismatch across:
        - targets {alpha_low, alpha_z}
        - all named groups in `groups`
    """
    # sanitize groups: require all groups to have at least one finite positive value
    clean: Dict[str, List[float]] = {}
    for name, values in groups.items():
        xs = [float(x) for x in values if math.isfinite(float(x))]
        if not xs or max(xs) <= 0.0:
            return {
                "e_inf": float("inf"),
                "candidate": None,
                "scale": float("nan"),
                "pred_by_group": {},
                "e_by_group": {},
                "groups": sorted(groups.keys()),
            }
        clean[str(name)] = xs

    best = None
    for agg_id, k in _candidates():
        bases: Dict[str, float] = {}
        ok = True
        for gname, xs in clean.items():
            base = _aggregate(xs, agg_id=agg_id, k=int(k))
            if not math.isfinite(base) or base <= 0.0:
                ok = False
                break
            bases[gname] = float(base)
        if not ok:
            continue

        local_best = None
        for s in _scale_family():
            pred0_by: Dict[str, float] = {gname: float(s) * float(b) for gname, b in bases.items()}
            predz_by: Dict[str, float] = {gname: arun.alpha_inv_mz_from_alpha0_inv(float(pred0)) for gname, pred0 in pred0_by.items()}
            e_by: Dict[str, Dict[str, float]] = {}
            worst = 0.0
            worst_sum = 0.0
            for gname in pred0_by.keys():
                pred0 = float(pred0_by[gname])
                predz = float(predz_by[gname])
                if not (math.isfinite(pred0) and pred0 > 0.0 and math.isfinite(predz) and predz > 0.0):
                    e_by[gname] = {"pred0": float(pred0), "predz": float(predz), "e_low": float("inf"), "e_z": float("inf"), "e_inf": float("inf")}
                    worst = float("inf")
                    worst_sum = float("inf")
                    continue
                e_low = abs(math.log(pred0 / float(alpha_low)))
                e_z = abs(math.log(predz / float(alpha_z)))
                e_inf = max(e_low, e_z)
                e_by[gname] = {"pred0": float(pred0), "predz": float(predz), "e_low": float(e_low), "e_z": float(e_z), "e_inf": float(e_inf)}
                worst = max(worst, float(e_inf))
                worst_sum = max(worst_sum, float(e_low + e_z))

            key = (float(worst), float(worst_sum), len(agg_id) + int(k), abs(math.log10(float(s))))
            if local_best is None or key < local_best[0]:
                local_best = (key, s, pred0_by, predz_by, e_by)
        assert local_best is not None
        key, s, pred0_by, predz_by, e_by = local_best
        rec = {
            "candidate": f"{agg_id}(k={k})",
            "scale": float(s),
            "e_inf": float(key[0]),
            "pred0_by_group": {k: float(v) for k, v in pred0_by.items()},
            "predz_by_group": {k: float(v) for k, v in predz_by.items()},
            "e_by_group": e_by,
            "running": {
                "model": "delta_alpha_decomposition",
                "delta_alpha": {
                    "lep": float(arun.delta_alpha_mz().lep),
                    "had5": float(arun.delta_alpha_mz().had5),
                    "top": float(arun.delta_alpha_mz().top),
                    "eff": float(arun.delta_alpha_mz().eff),
                    "total": float(arun.delta_alpha_mz().total),
                },
            },
        }
        if best is None or (float(rec["e_inf"]), float(key[1])) < (float(best["e_inf"]), float(best.get("_key2", float("inf")))):
            best = dict(rec)
            best["_key2"] = float(key[1])

    if best is None:
        return {
            "e_inf": float("inf"),
            "candidate": None,
            "scale": float("nan"),
            "pred_by_group": {},
            "e_by_group": {},
            "groups": sorted(groups.keys()),
        }
    best.pop("_key2", None)
    best["groups"] = sorted(clean.keys())
    return best


def _edges_strengths_flow_plus_mis(nodes: List[Dict[str, Any]], scan_ids: List[int]) -> List[float]:
    """
    Per-edge strength s := flow_u1 + mis_u1 on cross-m scan edges.
    """
    id_to_node: Dict[int, Dict[str, Any]] = {int(n.get("id")): n for n in nodes if "id" in n}
    pre = holo.preimages()
    xs: List[float] = []
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
        xs.append(float(flow_u1 + mis_u1))
    return xs


U1_SCALE_MODE = "extend_scale"  # or "pow10_only"
U1_SCALE_CS_EXTENDED = [1.0, 1.25, 1.5, 2.0, 2.5, 4.0, 5.0, 8.0]
U1_SCALE_E_MIN = -6
U1_SCALE_E_MAX = 6


def _scale_family() -> List[float]:
    """
    Coarse bounded scale family for U(1) alpha-linkage.

    - pow10_only: {10^e : e in [E_MIN..E_MAX]}
    - extend_scale: {c*10^e : c in CS_EXTENDED, e in [E_MIN..E_MAX]}
    """
    mode = str(U1_SCALE_MODE)
    cs = [1.0] if mode == "pow10_only" else list(U1_SCALE_CS_EXTENDED)
    scales = []
    for e in range(int(U1_SCALE_E_MIN), int(U1_SCALE_E_MAX) + 1):
        p = 10.0 ** int(e)
        for c in cs:
            scales.append(float(c) * float(p))
    return sorted(set(float(s) for s in scales))


def _u1_scale_family_spec() -> Dict[str, Any]:
    mode = str(U1_SCALE_MODE)
    cs = [1.0] if mode == "pow10_only" else list(U1_SCALE_CS_EXTENDED)
    return {
        "mode": mode,
        "kind": "c_times_pow10",
        "cs": [float(x) for x in cs],
        "e_min": int(U1_SCALE_E_MIN),
        "e_max": int(U1_SCALE_E_MAX),
        "n_scales": int(len(_scale_family())),
    }


def _safe_log(x: float) -> float:
    return math.log(max(1e-300, float(x)))


def _aggregate(values: Sequence[float], agg_id: str, k: int) -> float:
    xs = [float(x) for x in values]
    if not xs:
        return float("nan")
    if agg_id == "mean_s":
        return float(sum(xs) / len(xs))
    if agg_id == "sum_s":
        return float(sum(xs))
    if agg_id == "sum_log1p_s":
        return float(sum(math.log1p(max(0.0, x)) for x in xs))
    if agg_id == "mean_pow_s":
        return float(sum((max(0.0, x) ** int(k)) for x in xs) / len(xs))
    if agg_id == "mean_inv1p_s_pow":
        return float(sum((1.0 / (1.0 + max(0.0, x))) ** int(k) for x in xs) / len(xs))
    if agg_id == "sum_neg_log1p_s":
        return float(sum(-_safe_log(1.0 + max(0.0, x)) for x in xs))
    raise ValueError(agg_id)


def _candidates() -> List[Tuple[str, int]]:
    out: List[Tuple[str, int]] = [
        ("mean_s", 1),
        ("sum_s", 1),
        ("sum_log1p_s", 1),
        ("sum_neg_log1p_s", 1),
    ]
    for k in (1, 2, 3):
        out.append(("mean_pow_s", k))
        out.append(("mean_inv1p_s_pow", k))
    return out


def _u1_alpha_link_best(values: Sequence[float], *, alpha_low: float, alpha_z: float) -> Dict[str, Any]:
    """
    Deterministic bounded-family audit:
      choose (aggregation, scale) to minimize e_inf := max(|log(pred/alpha_low)|, |log(pred/alpha_z)|).
    """
    xs = [float(x) for x in values if math.isfinite(float(x))]
    if not xs or max(xs) <= 0.0:
        return {"e_inf": float("inf"), "e_low": float("inf"), "e_z": float("inf"), "pred": float("nan"), "candidate": None}

    best = None
    for agg_id, k in _candidates():
        base = _aggregate(xs, agg_id=agg_id, k=int(k))
        if not math.isfinite(base) or base <= 0.0:
            continue
        local_best = None
        for s in _scale_family():
            pred = float(s) * float(base)
            e_low = abs(math.log(pred / float(alpha_low)))
            e_z = abs(math.log(pred / float(alpha_z)))
            e_inf = max(e_low, e_z)
            key = (e_inf, e_low + e_z, len(agg_id) + int(k))
            if local_best is None or key < local_best[0]:
                local_best = (key, pred, e_low, e_z, agg_id, k, s)
        assert local_best is not None
        key, pred, e_low, e_z, agg_id, k, s = local_best
        rec = {
            "candidate": f"{agg_id}(k={k})",
            "scale": float(s),
            "pred": float(pred),
            "e_low": float(e_low),
            "e_z": float(e_z),
            "e_inf": float(key[0]),
        }
        if best is None or (float(rec["e_inf"]), float(rec["e_low"]) + float(rec["e_z"])) < (
            float(best["e_inf"]),
            float(best["e_low"]) + float(best["e_z"]),
        ):
            best = rec

    return best or {"e_inf": float("inf"), "e_low": float("inf"), "e_z": float("inf"), "pred": float("nan"), "candidate": None}


def _u1_score_strong(geo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strong U(1) score: worst-case minimax error across {graph2d, graph3d} x {micro, coarse}.
    """
    alpha_low = float(ALPHA_INV_CODATA_2022)
    alpha_z = float(ALPHAZ_INV_PDG)
    per: Dict[str, Any] = {}
    groups: Dict[str, Sequence[float]] = {}
    for gkey in ("graph2d", "graph3d"):
        g = geo.get(gkey, {})
        nodes = list(g.get("nodes", []))
        scan_ids = [int(x) for x in g.get("scan_path_node_ids", [])]
        coarse_nodes, coarse_scan = _coarse_project(nodes, scan_ids)

        xs_micro = _edges_strengths_flow_plus_mis(nodes, scan_ids)
        xs_coarse = _edges_strengths_flow_plus_mis(coarse_nodes, coarse_scan)
        per[gkey] = {
            "mode": "flow_plus_mis",
            "micro": {"n_edges": int(len(xs_micro))},
            "coarse": {"n_edges": int(len(xs_coarse))},
        }
        groups[f"{gkey}:micro"] = xs_micro
        groups[f"{gkey}:coarse"] = xs_coarse

    best_joint = _u1_alpha_link_best_joint(groups, alpha_low=alpha_low, alpha_z=alpha_z)
    # Attach per-group best stats for audit readability
    for gkey in ("graph2d", "graph3d"):
        for layer in ("micro", "coarse"):
            nm = f"{gkey}:{layer}"
            per[gkey][layer]["best_joint"] = best_joint.get("e_by_group", {}).get(nm)
    return {"score": float(best_joint["e_inf"]), "joint_best": best_joint, "per_graph": per}


def _choice_key(d: Dict[str, Any]) -> Tuple[Tuple[str, int], ...]:
    """
    Deterministic comparable key for choice dicts stored as {str(k): int(v)}.
    """
    items: List[Tuple[str, int]] = []
    for k, v in (d or {}).items():
        items.append((str(k), int(v)))
    return tuple(sorted(items, key=lambda kv: (int(kv[0]) if kv[0].isdigit() else kv[0], kv[1], kv[0])))


def _candidate_rank_key(cand: Dict[str, Any]) -> Tuple[
    float,
    float,
    float,
    int,
    str,
    float,
    int,
    int,
    int,
    Tuple[Tuple[str, int], ...],
    Tuple[Tuple[str, int], ...],
]:
    """
    CAP-style deterministic tie-break key: lower is better.
    """
    score = float(cand.get("score", float("inf")))
    u1 = float(cand.get("u1_score", float("inf")))
    ew = float(cand.get("ew_score", float("inf")))
    jb = (cand.get("u1") or {}).get("joint_best") or {}
    cand_name = str(jb.get("candidate") or "")
    scale = float(jb.get("scale", float("nan")))
    scale_mag = abs(math.log10(scale)) if (math.isfinite(scale) and scale > 0.0) else float("inf")
    sst = cand.get("schedule_stats_klo_khi") or {}
    n_sw = int(sst.get("n_switches", 10**9))
    n_chg = int(sst.get("n_changed", 10**9))
    max_m = int(sst.get("max_m", 10**9))
    c2 = _choice_key(cand.get("choice2") or {})
    c3 = _choice_key(cand.get("choice3") or {})
    return (score, u1, ew, len(cand_name), cand_name, scale_mag, n_sw, n_chg, max_m, c2, c3)


def _cross_m_edges_count_from_graph_nodes(nodes: List[Dict[str, Any]], scan_ids: List[int]) -> int:
    """
    Count scan edges where m changes (m(a)!=m(b)) on a schema-aligned geo nodes list.
    """
    id_to_node: Dict[int, Dict[str, Any]] = {int(n.get("id")): n for n in nodes if "id" in n}
    n_cross = 0
    for a, b in zip(scan_ids[:-1], scan_ids[1:]):
        na = id_to_node.get(int(a))
        nb = id_to_node.get(int(b))
        if na is None or nb is None:
            continue
        if int(na.get("m", 6)) != int(nb.get("m", 6)):
            n_cross += 1
    return int(n_cross)


def _score_one_candidate_with_reason(
    *,
    u_to_field: Dict[str, sml.SMField],
    cons: BuildConstraints,
    sched: Dict[int, int],
    choice2: Dict[int, int],
    choice3: Dict[int, int],
    w_ew: float,
    w_u1: float,
    k_lo: int,
    k_hi: int,
    gi_level: str,
    ew_mode: str,
    ew_blend_node_weight: float,
    ew_blend_coarse_weight: float,
    min_cross_m_edges_micro: int,
    min_cross_m_edges_coarse: int,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Return (candidate_or_None, reason) for auditable skip statistics.
    Reasons are coarse-grained by design (keep reporting stable).
    """
    try:
        cand = _score_one_candidate(
            u_to_field=u_to_field,
            cons=cons,
            sched=sched,
            choice2=choice2,
            choice3=choice3,
            w_ew=w_ew,
            w_u1=w_u1,
            k_lo=k_lo,
            k_hi=k_hi,
            gi_level=str(gi_level),
            ew_mode=str(ew_mode),
            ew_blend_node_weight=float(ew_blend_node_weight),
            ew_blend_coarse_weight=float(ew_blend_coarse_weight),
            min_cross_m_edges_micro=int(min_cross_m_edges_micro),
            min_cross_m_edges_coarse=int(min_cross_m_edges_coarse),
        )
    except Exception:
        return None, "build_or_score_error"
    if cand is None:
        return None, "filtered"
    return cand, "ok"


def _render_png(out_dir: Path) -> None:
    """
    Render a labeled 3D PNG for the current best wiring_geometry.json.
    """
    script_dir = Path(__file__).resolve().parent
    fig_script = script_dir / "fig_hilbert_sm_wiring_geometry_3d_png.py"
    in_json = out_dir / "wiring_geometry.json"
    out_png = out_dir / "wiring_3d_perspective_annotated.png"
    # Renderer expects graph3d.segments. If missing, add them from scan_path_node_ids.
    try:
        geo = json.loads(in_json.read_text(encoding="utf-8"))
        g3 = geo.get("graph3d", {})
        if isinstance(g3, dict) and "segments" not in g3:
            nodes = list(g3.get("nodes", []))
            scan_ids = [int(x) for x in g3.get("scan_path_node_ids", [])]
            id_to_pt: Dict[int, List[float]] = {int(n.get("id")): list(n.get("pt", [])) for n in nodes if "id" in n and "pt" in n}
            segs = []
            for a, b in zip(scan_ids[:-1], scan_ids[1:]):
                pa = id_to_pt.get(int(a))
                pb = id_to_pt.get(int(b))
                if not (isinstance(pa, list) and isinstance(pb, list) and len(pa) == 3 and len(pb) == 3):
                    continue
                segs.append(([float(pa[0]), float(pa[1]), float(pa[2])], [float(pb[0]), float(pb[1]), float(pb[2])]))
            g3["segments"] = segs
            geo["graph3d"] = g3
            in_json.write_text(json.dumps(geo, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        pass

    subprocess.run(
        [
            "python3",
            str(fig_script),
            "--input",
            str(in_json),
            "--output",
            str(out_png),
            "--dpi",
            "300",
            "--scatter-nodes",
            "--color-by-m",
            "--label-mode",
            "k",
            "--label-topk",
            "18",
            "--label-only-m",
            "-1",
        ],
        check=False,
    )


def _add_segments_inplace(geo: Dict[str, Any]) -> None:
    """
    Ensure graph2d.segments and graph3d.segments exist (for downstream rendering/inspection).
    Segments are derived from scan_path_node_ids and per-node pt.
    """

    def build_segments(nodes: List[Dict[str, Any]], scan_ids: List[int], dim: int) -> List[List[List[float]]]:
        id_to_pt: Dict[int, List[float]] = {int(n.get("id")): list(n.get("pt", [])) for n in nodes if "id" in n and "pt" in n}
        segs: List[List[List[float]]] = []
        for a, b in zip(scan_ids[:-1], scan_ids[1:]):
            pa = id_to_pt.get(int(a))
            pb = id_to_pt.get(int(b))
            if not (isinstance(pa, list) and isinstance(pb, list) and len(pa) == dim and len(pb) == dim):
                continue
            segs.append([list(float(x) for x in pa), list(float(x) for x in pb)])
        return segs

    for gkey, dim in (("graph2d", 2), ("graph3d", 3)):
        g = geo.get(gkey, {})
        if not isinstance(g, dict):
            continue
        if "segments" in g:
            continue
        nodes = list(g.get("nodes", []))
        scan_ids = [int(x) for x in g.get("scan_path_node_ids", [])]
        g["segments"] = build_segments(nodes, scan_ids, dim=dim)
        geo[gkey] = g


def _score_one_candidate(
    *,
    u_to_field: Dict[str, sml.SMField],
    cons: BuildConstraints,
    sched: Dict[int, int],
    choice2: Dict[int, int],
    choice3: Dict[int, int],
    w_ew: float,
    w_u1: float,
    k_lo: int,
    k_hi: int,
    gi_level: str,
    ew_mode: str,
    ew_blend_node_weight: float,
    ew_blend_coarse_weight: float,
    min_cross_m_edges_micro: int,
    min_cross_m_edges_coarse: int,
) -> Optional[Dict[str, Any]]:
    try:
        g2 = build_center_graph_fixed(dim=2, m_by_k=sched, chosen_micro_option=choice2, max_micro_orders=16, constraints=cons)
        g3 = build_center_graph_fixed(dim=3, m_by_k=sched, chosen_micro_option=choice3, max_micro_orders=48, constraints=cons)
    except Exception:
        return None

    gi_level = str(gi_level)
    sig_type_2 = canonical_signature_type_transition_graph(g2)
    sig_type_3 = canonical_signature_type_transition_graph(g3)
    if gi_level in ("type", "full") and sig_type_2 != sig_type_3:
        return None

    sig_full_2 = None
    sig_full_3 = None
    if gi_level == "full":
        sig_full_2, _wl2 = canonical_signature_center_graph(g2, include_scan_pos=False, include_dim=False)
        sig_full_3, _wl3 = canonical_signature_center_graph(g3, include_scan_pos=False, include_dim=False)
        if sig_full_2 != sig_full_3:
            return None

    geo = {
        "constraints": asdict(cons),
        "m_schedule_by_k": {str(k): int(v) for k, v in sorted(sched.items())},
        "choice2": {str(k): int(v) for k, v in sorted(choice2.items())},
        "choice3": {str(k): int(v) for k, v in sorted(choice3.items())},
        "graph2d": {
            "n_nodes": len(g2.nodes),
            "scan_path_node_ids": [int(x) for x in g2.scan_path],
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

    # U(1) signal pruning: require enough cross-m edges on micro/coarse layers.
    if int(min_cross_m_edges_micro) > 0 or int(min_cross_m_edges_coarse) > 0:
        try:
            n2_micro = _cross_m_edges_count_from_graph_nodes(list(geo["graph2d"]["nodes"]), list(geo["graph2d"]["scan_path_node_ids"]))
            n3_micro = _cross_m_edges_count_from_graph_nodes(list(geo["graph3d"]["nodes"]), list(geo["graph3d"]["scan_path_node_ids"]))
            coarse_nodes_2, coarse_scan_2 = _coarse_project(list(geo["graph2d"]["nodes"]), list(geo["graph2d"]["scan_path_node_ids"]))
            coarse_nodes_3, coarse_scan_3 = _coarse_project(list(geo["graph3d"]["nodes"]), list(geo["graph3d"]["scan_path_node_ids"]))
            n2_coarse = _cross_m_edges_count_from_graph_nodes(coarse_nodes_2, coarse_scan_2)
            n3_coarse = _cross_m_edges_count_from_graph_nodes(coarse_nodes_3, coarse_scan_3)
            if int(min_cross_m_edges_micro) > 0 and (int(n2_micro) < int(min_cross_m_edges_micro) or int(n3_micro) < int(min_cross_m_edges_micro)):
                return None
            if int(min_cross_m_edges_coarse) > 0 and (int(n2_coarse) < int(min_cross_m_edges_coarse) or int(n3_coarse) < int(min_cross_m_edges_coarse)):
                return None
        except Exception:
            return None

    # EW scores (audit-norm). Keep several modes for later reporting.
    mu2_node = _mu6_from_nodes(list(geo["graph2d"]["nodes"]))
    mu3_node = _mu6_from_nodes(list(geo["graph3d"]["nodes"]))
    ew2_node = _ew_from_mu6(mu2_node, u_to_field=u_to_field)
    ew3_node = _ew_from_mu6(mu3_node, u_to_field=u_to_field)
    ew_score_node = _ew_score_from_modes(ew2_node, ew3_node, w_dim_consistency=1.0)

    # Type-layer (coarse cell) EW audit (not used in the core score; recorded for consistency).
    mu2_coarse = _mu6_from_coarse_cells(list(geo["graph2d"]["nodes"]))
    mu3_coarse = _mu6_from_coarse_cells(list(geo["graph3d"]["nodes"]))
    ew2_coarse = _ew_from_mu6(mu2_coarse, u_to_field=u_to_field)
    ew3_coarse = _ew_from_mu6(mu3_coarse, u_to_field=u_to_field)
    ew_score_coarse = _ew_score_from_modes(ew2_coarse, ew3_coarse, w_dim_consistency=1.0)

    ew_mode = str(ew_mode)
    if ew_mode == "node":
        ew_score = float(ew_score_node)
    elif ew_mode == "coarse_cell":
        ew_score = float(ew_score_coarse)
    else:
        ew_score = float(float(ew_blend_node_weight) * float(ew_score_node) + float(ew_blend_coarse_weight) * float(ew_score_coarse))

    u1 = _u1_score_strong(geo)
    u1_score = float(u1["score"])

    score = float(w_ew * ew_score + w_u1 * u1_score)

    sst = schedule_stats(sched, k_min=k_lo, k_max=k_hi)

    # candidate (small) record; geometry will be written by coordinator when selected best.
    cand = {
        "score": float(score),
        "weights": {"ew": float(w_ew), "u1": float(w_u1)},
        "ew_score": float(ew_score),
        "ew_score_node": float(ew_score_node),
        "ew_score_coarse_cell": float(ew_score_coarse),
        "ew_mode": str(ew_mode),
        "ew_blend_weights": {"node": float(ew_blend_node_weight), "coarse_cell": float(ew_blend_coarse_weight)},
        "u1_score": float(u1_score),
        "ew": {
            "node": {"graph2d": ew2_node, "graph3d": ew3_node},
            "coarse_cell": {"graph2d": ew2_coarse, "graph3d": ew3_coarse},
        },
        "u1": u1,
        "gi": {"level": str(gi_level), "sig_type_2d": sig_type_2, "sig_type_3d": sig_type_3, "sig_full_2d": sig_full_2, "sig_full_3d": sig_full_3},
        "min_cross_m_edges": {"micro": int(min_cross_m_edges_micro), "coarse": int(min_cross_m_edges_coarse)},
        "k_lo": int(k_lo),
        "k_hi": int(k_hi),
        "schedule_stats_klo_khi": asdict(sst),
        "m_schedule_by_k": {str(k): int(v) for k, v in sorted(sched.items())},
        "choice2": {str(k): int(v) for k, v in sorted(choice2.items())},
        "choice3": {str(k): int(v) for k, v in sorted(choice3.items())},
        "geo": geo,
    }
    return cand


def _worker_loop(
    worker_id: int,
    queue_out: "mp.Queue[Dict[str, Any]]",
    *,
    seed_start: int,
    schedules_per_seed: int,
    micro_per_schedule: int,
    k_lo: int,
    k_hi: int,
    schedule_family: str,
    ew_proxy_th: float,
    w_ew: float,
    w_u1: float,
    time_limit_s: float,
    t0: float,
    gi_level: str,
    ew_mode: str,
    u1_scale_mode: str,
    ew_blend_node_weight: float,
    ew_blend_coarse_weight: float,
    min_cross_m_edges_micro: int,
    min_cross_m_edges_coarse: int,
) -> None:
    global U1_SCALE_MODE
    U1_SCALE_MODE = str(u1_scale_mode)
    u_to_field = _build_x6_to_field_map()
    cons = BuildConstraints(enforce_edge_types=False, enforce_noncrossing_xy=False, forbid_passing_through_centers=False)
    u6_by_k = [str(sml.fold6(k)) for k in range(64)]
    X6 = sml.all_x6()

    rng = random.Random(int(seed_start) + 1000003 * int(worker_id))
    best: Optional[Dict[str, Any]] = None
    skip_counts: Dict[str, int] = {}
    jobs = 0
    last_send = float(t0)

    while (time.time() - t0) < float(time_limit_s):
        seed = int(rng.randrange(0, 2**31 - 1))
        rr = random.Random(int(seed))
        for _si in range(int(schedules_per_seed)):
            if (time.time() - t0) >= float(time_limit_s):
                break
            sched, fam_id = sample_schedule(rr, schedule_family=str(schedule_family), k_lo=k_lo, k_hi=k_hi)
            ks = refined_ks(sched)

            # EW proxy prune (same as main).
            counts = {u: 0 for u in X6}
            for k in range(64):
                u = u6_by_k[int(k)]
                m = int(sched.get(int(k), 6))
                mult = 1 if m <= 6 else (4 if m == 8 else 16)
                counts[u] += int(mult)
            denom = float(sum(counts.values()))
            if denom <= 0.0:
                continue
            mu6_proxy = {u: float(c) / denom for (u, c) in counts.items()}
            wy_proxy = _w_y_eff_from_mu6(mu6_proxy, u_to_field=u_to_field)
            ew_proxy = _ew_from_wy(wy_proxy)
            if float(ew_proxy["e_sum"]) > float(ew_proxy_th):
                continue

            for _ in range(int(micro_per_schedule)):
                if (time.time() - t0) >= float(time_limit_s):
                    break
                choice2 = sample_choice(rr, ks, n_opts=16)
                choice3 = sample_choice(rr, ks, n_opts=48)
                cand = _score_one_candidate(
                    u_to_field=u_to_field,
                    cons=cons,
                    sched=sched,
                    choice2=choice2,
                    choice3=choice3,
                    w_ew=w_ew,
                    w_u1=w_u1,
                    k_lo=k_lo,
                    k_hi=k_hi,
                    gi_level=str(gi_level),
                    ew_mode=str(ew_mode),
                    ew_blend_node_weight=float(ew_blend_node_weight),
                    ew_blend_coarse_weight=float(ew_blend_coarse_weight),
                    min_cross_m_edges_micro=int(min_cross_m_edges_micro),
                    min_cross_m_edges_coarse=int(min_cross_m_edges_coarse),
                )
                jobs += 1
                if cand is None:
                    skip_counts["filtered"] = int(skip_counts.get("filtered", 0)) + 1
                    continue
                cand["schedule_family"] = str(fam_id)
                if best is None or _candidate_rank_key(cand) < _candidate_rank_key(best):
                    best = cand

                now = time.time()
                if (now - last_send) >= 2.0:
                    queue_out.put({"worker": int(worker_id), "jobs": int(jobs), "best": best, "skip_counts": skip_counts})
                    last_send = float(now)

    queue_out.put({"worker": int(worker_id), "jobs": int(jobs), "best": best, "skip_counts": skip_counts, "done": True})


def main() -> None:
    out_root = figures_dir() / "adaptive" / "sm_hilbert_isomorphism"
    out_data = out_root / "data"
    out_data.mkdir(parents=True, exist_ok=True)

    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", type=str, default="", help="Optional suffix for outputs (useful for ablations).")
    ap.add_argument("--seed-start", type=int, default=7000)
    ap.add_argument("--seed-count", type=int, default=60)
    ap.add_argument("--schedules-per-seed", type=int, default=60)
    ap.add_argument("--micro-per-schedule", type=int, default=30)
    ap.add_argument("--time-limit-s", type=float, default=600.0)
    ap.add_argument("--k-lo", type=int, default=18)
    ap.add_argument("--k-hi", type=int, default=52)
    ap.add_argument(
        "--schedule-family",
        type=str,
        default="mix",
        choices=["mix", "richer", "hierarchical", "unimodal"],
        help="Schedule sampling family (default: mix).",
    )
    ap.add_argument("--checkpoint-s", type=float, default=60.0)
    ap.add_argument("--resume-best", action="store_true")
    ap.add_argument("--ew-weight", type=float, default=1.0)
    ap.add_argument("--u1-weight", type=float, default=1.0)
    ap.add_argument("--u1-scale-mode", type=str, default="extend_scale", choices=["pow10_only", "extend_scale"], help="U(1) bounded scale-family mode.")
    ap.add_argument("--ew-proxy-threshold", type=float, default=0.02, help="Skip schedules with proxy EW mismatch above this.")
    ap.add_argument("--gi-level", type=str, default="type", choices=["off", "type", "full"], help="Graph-isomorphism gate level (default: type).")
    ap.add_argument("--ew-mode", type=str, default="blend", choices=["node", "coarse_cell", "blend"], help="EW score mode (default: blend).")
    ap.add_argument("--ew-blend-node-weight", type=float, default=0.25)
    ap.add_argument("--ew-blend-coarse-weight", type=float, default=1.0)
    ap.add_argument("--min-cross-m-edges-micro", type=int, default=0, help="Require >= this many cross-m scan edges in EACH of graph2d/graph3d (micro).")
    ap.add_argument("--min-cross-m-edges-coarse", type=int, default=0, help="Require >= this many cross-m scan edges in EACH of graph2d/graph3d (coarse).")
    ap.add_argument("--stage-a-schedules-per-seed", type=int, default=50, help="StageA schedule samples per seed (broad scan).")
    ap.add_argument("--stage-a-micro-per-schedule", type=int, default=4, help="StageA micro samples per schedule.")
    ap.add_argument("--stage-a-fraction", type=float, default=0.75, help="Fraction of time-limit spent in StageA (time-driven).")
    ap.add_argument("--stage-b-top-n-schedules", type=int, default=20, help="StageB: deep search only on top-N schedules from StageA.")
    ap.add_argument("--stage-b-micro-per-schedule", type=int, default=60, help="StageB micro samples per schedule.")
    ap.add_argument("--workers", type=int, default=0, help="CPU worker processes (0=auto).")
    ap.add_argument("--parallel", action="store_true", help="Enable multi-process search.")
    args = ap.parse_args()

    # Configure U(1) scale-family mode (global, used by _scale_family()).
    global U1_SCALE_MODE
    U1_SCALE_MODE = str(args.u1_scale_mode)

    # Optional output suffix for ablation comparisons.
    tag_raw = str(getattr(args, "tag", "") or "").strip()
    tag = "".join((ch if (ch.isalnum() or ch in "-_") else "_") for ch in tag_raw)
    tag = tag.strip("_-")
    suffix = f"_{tag}" if tag else ""

    out_dir = out_root / f"wiring_fold_geometry_numeric_match_strong{suffix}"
    out_dir.mkdir(parents=True, exist_ok=True)

    u_to_field = _build_x6_to_field_map()

    seeds = list(range(int(args.seed_start), int(args.seed_start) + int(args.seed_count)))
    schedules_per_seed = int(args.schedules_per_seed)
    micro_per_schedule = int(args.micro_per_schedule)
    time_limit_s = float(args.time_limit_s)
    k_lo = int(args.k_lo)
    k_hi = int(args.k_hi)
    schedule_family = str(args.schedule_family)
    ckpt_s = float(args.checkpoint_s)
    w_ew = float(args.ew_weight)
    w_u1 = float(args.u1_weight)
    ew_proxy_th = float(args.ew_proxy_threshold)
    gi_level = str(args.gi_level)
    ew_mode = str(args.ew_mode)
    ew_blend_node_weight = float(args.ew_blend_node_weight)
    ew_blend_coarse_weight = float(args.ew_blend_coarse_weight)
    min_cross_m_edges_micro = int(args.min_cross_m_edges_micro)
    min_cross_m_edges_coarse = int(args.min_cross_m_edges_coarse)
    stage_a_schedules_per_seed = int(args.stage_a_schedules_per_seed)
    stage_a_micro_per_schedule = int(args.stage_a_micro_per_schedule)
    stage_a_fraction = float(args.stage_a_fraction)
    stage_b_top_n_schedules = int(args.stage_b_top_n_schedules)
    stage_b_micro_per_schedule = int(args.stage_b_micro_per_schedule)
    n_workers = int(args.workers)
    if n_workers <= 0:
        n_workers = max(1, int(os.cpu_count() or 1) - 1)

    out_report = out_data / f"sm_hilbert_numeric_match_strong_search_report{suffix}.json"
    best: Optional[Dict[str, Any]] = None

    if bool(args.resume_best) and out_report.exists():
        try:
            prev = json.loads(out_report.read_text(encoding="utf-8"))
            if isinstance(prev, dict):
                pb = prev.get("best")
                if isinstance(pb, dict) and "score" in pb:
                    best = pb
        except Exception:
            pass

    t0 = time.time()
    last_ckpt = float(t0)
    i = 0

    # Keep geometry constraints loose; "strong" refers to numeric targets.
    cons = BuildConstraints(enforce_edge_types=False, enforce_noncrossing_xy=False, forbid_passing_through_centers=False)

    # Precompute u6 per k for proxy.
    u6_by_k = [str(sml.fold6(k)) for k in range(64)]
    X6 = sml.all_x6()

    if bool(args.parallel) and n_workers > 1:
        ctx = mp.get_context("spawn")
        q: "mp.Queue[Dict[str, Any]]" = ctx.Queue()
        procs = []
        for wid in range(n_workers):
            p = ctx.Process(
                target=_worker_loop,
                args=(wid, q),
                kwargs={
                    "seed_start": int(args.seed_start),
                    "schedules_per_seed": int(schedules_per_seed),
                    "micro_per_schedule": int(micro_per_schedule),
                    "k_lo": int(k_lo),
                    "k_hi": int(k_hi),
                    "schedule_family": str(schedule_family),
                    "ew_proxy_th": float(ew_proxy_th),
                    "w_ew": float(w_ew),
                    "w_u1": float(w_u1),
                    "time_limit_s": float(time_limit_s),
                    "t0": float(t0),
                    "gi_level": str(gi_level),
                    "ew_mode": str(ew_mode),
                    "u1_scale_mode": str(U1_SCALE_MODE),
                    "ew_blend_node_weight": float(ew_blend_node_weight),
                    "ew_blend_coarse_weight": float(ew_blend_coarse_weight),
                    "min_cross_m_edges_micro": int(min_cross_m_edges_micro),
                    "min_cross_m_edges_coarse": int(min_cross_m_edges_coarse),
                },
            )
            p.daemon = True
            p.start()
            procs.append(p)

        # Coordinator: merge best and write checkpoints.
        worker_jobs: Dict[int, int] = {}
        worker_skips: Dict[int, Dict[str, int]] = {}
        done_workers: set[int] = set()

        while (time.time() - t0) < float(time_limit_s) and len(done_workers) < n_workers:
            try:
                msg = q.get(timeout=1.0)
            except Exception:
                msg = None
            if isinstance(msg, dict):
                wid = int(msg.get("worker", -1))
                if wid >= 0:
                    worker_jobs[wid] = int(msg.get("jobs", worker_jobs.get(wid, 0)))
                    if isinstance(msg.get("skip_counts"), dict):
                        worker_skips[wid] = {str(k): int(v) for k, v in msg.get("skip_counts", {}).items()}
                    if bool(msg.get("done")):
                        done_workers.add(wid)
                cand = msg.get("best")
                if isinstance(cand, dict) and "score" in cand:
                    if best is None or _candidate_rank_key(cand) < _candidate_rank_key(best):
                        best = {k: v for k, v in cand.items() if k != "geo"}  # keep best record small
                        # write best geometry + render
                        geo = cand.get("geo")
                        if isinstance(geo, dict):
                            _add_segments_inplace(geo)
                            (out_dir / "wiring_geometry.json").write_text(
                                json.dumps(geo, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
                            )
                            _render_png(out_dir)

            i = int(sum(worker_jobs.values()))
            now = time.time()
            if ckpt_s > 0.0 and best is not None and (now - last_ckpt) >= ckpt_s:
                skip_counts: Dict[str, int] = {}
                for _wid, sc in worker_skips.items():
                    for k, v in sc.items():
                        skip_counts[k] = int(skip_counts.get(k, 0)) + int(v)
                report_obj = {
                    "search_budget": {
                        "seed_start": int(args.seed_start),
                        "workers": int(n_workers),
                        "schedules_per_worker_batch": int(schedules_per_seed),
                        "micro_per_schedule": int(micro_per_schedule),
                        "time_limit_s": float(time_limit_s),
                        "k_lo": int(k_lo),
                        "k_hi": int(k_hi),
                        "schedule_family": str(schedule_family),
                        "ew_proxy_threshold": float(ew_proxy_th),
                        "gi_level": str(gi_level),
                        "ew_mode": str(ew_mode),
                        "ew_blend": {"node": float(ew_blend_node_weight), "coarse_cell": float(ew_blend_coarse_weight)},
                        "u1_scale_family": _u1_scale_family_spec(),
                        "min_cross_m_edges": {"micro": int(min_cross_m_edges_micro), "coarse": int(min_cross_m_edges_coarse)},
                        "parallel_mode": True,
                    },
                    "completed_jobs": int(i),
                    "wall_clock_seconds": float(now - t0),
                    "best": best,
                    "skip_counts": skip_counts,
                }
                out_report.write_text(json.dumps(report_obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
                last_ckpt = float(now)

        for p in procs:
            try:
                p.join(timeout=1.0)
            except Exception:
                pass

        if best is None:
            raise RuntimeError("No candidate found within the budget.")

        skip_counts: Dict[str, int] = {}
        for _wid, sc in worker_skips.items():
            for k, v in sc.items():
                skip_counts[k] = int(skip_counts.get(k, 0)) + int(v)
        report_obj = {
            "search_budget": {
                "seed_start": int(args.seed_start),
                "workers": int(n_workers),
                "schedules_per_worker_batch": int(schedules_per_seed),
                "micro_per_schedule": int(micro_per_schedule),
                "time_limit_s": float(time_limit_s),
                "k_lo": int(k_lo),
                "k_hi": int(k_hi),
                "schedule_family": str(schedule_family),
                "ew_proxy_threshold": float(ew_proxy_th),
                "gi_level": str(gi_level),
                "ew_mode": str(ew_mode),
                "ew_blend": {"node": float(ew_blend_node_weight), "coarse_cell": float(ew_blend_coarse_weight)},
                "u1_scale_family": _u1_scale_family_spec(),
                "min_cross_m_edges": {"micro": int(min_cross_m_edges_micro), "coarse": int(min_cross_m_edges_coarse)},
                "parallel_mode": True,
            },
            "completed_jobs": int(i),
            "wall_clock_seconds": float(time.time() - t0),
            "best": best,
            "skip_counts": skip_counts,
        }
        out_report.write_text(json.dumps(report_obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Wrote {out_report}")
        print(f"Wrote {out_dir / 'wiring_geometry.json'}")
        print(f"Wrote {out_dir / 'wiring_3d_perspective_annotated.png'}")
        return

    # Two-stage search (short-run friendly).
    skip_counts: Dict[str, int] = {}
    best_trace: List[Dict[str, Any]] = []

    def record_best_trace(c: Dict[str, Any], job_i: int, *, stage: str) -> None:
        jb = (c.get("u1") or {}).get("joint_best") or {}
        best_trace.append(
            {
                "t": float(time.time() - t0),
                "stage": str(stage),
                "job": int(job_i),
                "score": float(c.get("score", float("nan"))),
                "ew_score": float(c.get("ew_score", float("nan"))),
                "ew_node": float(c.get("ew_score_node", float("nan"))),
                "ew_coarse_cell": float(c.get("ew_score_coarse_cell", float("nan"))),
                "u1_score": float(c.get("u1_score", float("nan"))),
                "u1_e_inf": float(jb.get("e_inf", float("nan"))),
                "u1_candidate": str(jb.get("candidate") or ""),
                "u1_scale": float(jb.get("scale", float("nan"))),
                "schedule_stats": c.get("schedule_stats_klo_khi"),
                "m_schedule_by_k": c.get("m_schedule_by_k"),
            }
        )

    def sched_key(s: Dict[int, int]) -> Tuple[Tuple[int, int], ...]:
        return tuple(sorted([(int(k), int(v)) for k, v in s.items()], key=lambda kv: kv[0]))

    schedule_best: Dict[Tuple[Tuple[int, int], ...], Dict[str, Any]] = {}

    def write_checkpoint() -> None:
        nonlocal last_ckpt
        now = time.time()
        if ckpt_s <= 0.0 or best is None:
            return
        if (now - last_ckpt) < float(ckpt_s):
            return
        leaderboard = [v for (_k, v) in sorted(list(schedule_best.items()), key=lambda kv: _candidate_rank_key(kv[1]))[: max(1, int(stage_b_top_n_schedules))]]
        report_obj = {
            "search_budget": {
                "seeds": seeds,
                "stage_a_schedules_per_seed": int(stage_a_schedules_per_seed),
                "stage_a_micro_per_schedule": int(stage_a_micro_per_schedule),
                "stage_a_fraction": float(stage_a_fraction),
                "stage_b_top_n_schedules": int(stage_b_top_n_schedules),
                "stage_b_micro_per_schedule": int(stage_b_micro_per_schedule),
                "time_limit_s": time_limit_s,
                "k_lo": k_lo,
                "k_hi": k_hi,
                "schedule_family": str(schedule_family),
                "ew_proxy_threshold": ew_proxy_th,
                "gi_level": str(gi_level),
                "ew_mode": str(ew_mode),
                "ew_blend": {"node": float(ew_blend_node_weight), "coarse_cell": float(ew_blend_coarse_weight)},
                "u1_scale_family": _u1_scale_family_spec(),
                "min_cross_m_edges": {"micro": int(min_cross_m_edges_micro), "coarse": int(min_cross_m_edges_coarse)},
                "parallel_mode": False,
            },
            "completed_jobs": int(job_i),
            "wall_clock_seconds": float(now - t0),
            "best": best,
            "skip_counts": skip_counts,
            "best_trace": best_trace,
            "schedule_leaderboard": leaderboard,
        }
        out_report.write_text(json.dumps(report_obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        last_ckpt = float(now)

    pe = ProgressEvery(label="exp_sm_hilbert_numeric_match_strong_search", total=None, interval_s=60.0)
    pe.start()

    job_i = 0
    # StageA: broad schedule scan (time-driven).
    stage_a_fraction = min(1.0, max(0.0, float(stage_a_fraction)))
    stage_a_deadline = float(t0) + float(time_limit_s) * float(stage_a_fraction)
    epoch = 0
    while True:
        now = time.time()
        if now >= stage_a_deadline or (now - t0) > time_limit_s:
            break
        for seed in seeds:
            now2 = time.time()
            if now2 >= stage_a_deadline or (now2 - t0) > time_limit_s:
                break

            # Epoch-mix the seed so we do not repeat the same deterministic stream.
            seed_eff = int(seed) + 1000003 * int(epoch)
            rng = random.Random(int(seed_eff))

            for si in range(int(stage_a_schedules_per_seed)):
                if time.time() >= stage_a_deadline or (time.time() - t0) > time_limit_s:
                    break
                sched, fam_id = sample_schedule(rng, schedule_family=str(schedule_family), k_lo=k_lo, k_hi=k_hi)
                sst = schedule_stats(sched, k_min=k_lo, k_max=k_hi)
                ks = refined_ks(sched)

                # Cheap EW proxy prune.
                counts = {u: 0 for u in X6}
                for k in range(64):
                    u = u6_by_k[int(k)]
                    m = int(sched.get(int(k), 6))
                    mult = 1 if m <= 6 else (4 if m == 8 else 16)
                    counts[u] += int(mult)
                denom = float(sum(counts.values()))
                if denom <= 0.0:
                    skip_counts["A:ew_proxy_denom"] = int(skip_counts.get("A:ew_proxy_denom", 0)) + 1
                    continue
                mu6_proxy = {u: float(c) / denom for (u, c) in counts.items()}
                wy_proxy = _w_y_eff_from_mu6(mu6_proxy, u_to_field=u_to_field)
                ew_proxy = _ew_from_wy(wy_proxy)
                if float(ew_proxy["e_sum"]) > ew_proxy_th:
                    skip_counts["A:ew_proxy"] = int(skip_counts.get("A:ew_proxy", 0)) + 1
                    continue

                for _ in range(int(stage_a_micro_per_schedule)):
                    if time.time() >= stage_a_deadline or (time.time() - t0) > time_limit_s:
                        break
                    extra = f"A epoch={epoch} seed={seed} fam={fam_id} sch={si} chg={sst.n_changed} sw={sst.n_switches} maxm={sst.max_m}"
                    if isinstance(best, dict):
                        extra += f" best={float(best.get('score', float('nan'))):.4g}"
                    pe.maybe(job_i, extra=extra)
                    job_i += 1

                    choice2 = sample_choice(rng, ks, n_opts=16)
                    choice3 = sample_choice(rng, ks, n_opts=48)
                    cand, reason = _score_one_candidate_with_reason(
                        u_to_field=u_to_field,
                        cons=cons,
                        sched=sched,
                        choice2=choice2,
                        choice3=choice3,
                        w_ew=w_ew,
                        w_u1=w_u1,
                        k_lo=k_lo,
                        k_hi=k_hi,
                        gi_level=str(gi_level),
                        ew_mode=str(ew_mode),
                        ew_blend_node_weight=float(ew_blend_node_weight),
                        ew_blend_coarse_weight=float(ew_blend_coarse_weight),
                        min_cross_m_edges_micro=int(min_cross_m_edges_micro),
                        min_cross_m_edges_coarse=int(min_cross_m_edges_coarse),
                    )
                    if cand is None:
                        skip_counts[f"A:{reason}"] = int(skip_counts.get(f"A:{reason}", 0)) + 1
                        continue
                    cand["seed"] = int(seed)
                    cand["seed_eff"] = int(seed_eff)
                    cand["epoch"] = int(epoch)
                    cand["schedule_family"] = str(fam_id)

                    if best is None or _candidate_rank_key(cand) < _candidate_rank_key(best):
                        best = {k: v for k, v in cand.items() if k != "geo"}
                        geo = cand.get("geo")
                        if isinstance(geo, dict):
                            (out_dir / "wiring_geometry.json").write_text(
                                json.dumps(geo, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
                            )
                            _render_png(out_dir)
                        record_best_trace(best, job_i, stage="A")

                    sk = sched_key(sched)
                    prev = schedule_best.get(sk)
                    if prev is None or _candidate_rank_key(cand) < _candidate_rank_key(prev):
                        schedule_best[sk] = {k: v for k, v in cand.items() if k != "geo"}
                    write_checkpoint()

        epoch += 1

    # StageB: deep micro on top schedules.
    top_scheds = sorted(list(schedule_best.items()), key=lambda kv: _candidate_rank_key(kv[1]))[: max(0, int(stage_b_top_n_schedules))]
    for idx, (sk, _prev_best) in enumerate(top_scheds, start=1):
        if (time.time() - t0) > time_limit_s:
            break
        sched = {int(k): int(v) for k, v in sk}
        ks = refined_ks(sched)
        rr2 = random.Random(int(args.seed_start) + 99991 * idx + 17)
        rr3 = random.Random(int(args.seed_start) + 99991 * idx + 7777)
        for j in range(int(stage_b_micro_per_schedule)):
            if (time.time() - t0) > time_limit_s:
                break
            extra = f"B {idx}/{len(top_scheds)} j={j} chg={len(sk)}"
            if isinstance(best, dict):
                extra += f" best={float(best.get('score', float('nan'))):.4g}"
            pe.maybe(job_i, extra=extra)
            job_i += 1

            choice2 = sample_choice(rr2, ks, n_opts=16)
            choice3 = sample_choice(rr3, ks, n_opts=48)
            cand, reason = _score_one_candidate_with_reason(
                u_to_field=u_to_field,
                cons=cons,
                sched=sched,
                choice2=choice2,
                choice3=choice3,
                w_ew=w_ew,
                w_u1=w_u1,
                k_lo=k_lo,
                k_hi=k_hi,
                gi_level=str(gi_level),
                ew_mode=str(ew_mode),
                ew_blend_node_weight=float(ew_blend_node_weight),
                ew_blend_coarse_weight=float(ew_blend_coarse_weight),
                min_cross_m_edges_micro=int(min_cross_m_edges_micro),
                min_cross_m_edges_coarse=int(min_cross_m_edges_coarse),
            )
            if cand is None:
                skip_counts[f"B:{reason}"] = int(skip_counts.get(f"B:{reason}", 0)) + 1
                continue
            cand["seed"] = int(args.seed_start)

            if best is None or _candidate_rank_key(cand) < _candidate_rank_key(best):
                best = {k: v for k, v in cand.items() if k != "geo"}
                geo = cand.get("geo")
                if isinstance(geo, dict):
                    (out_dir / "wiring_geometry.json").write_text(json.dumps(geo, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
                    _render_png(out_dir)
                record_best_trace(best, job_i, stage="B")
                write_checkpoint()

    if best is None:
        raise RuntimeError("No candidate found within the budget.")

    leaderboard = [v for (_k, v) in sorted(list(schedule_best.items()), key=lambda kv: _candidate_rank_key(kv[1]))[: max(1, int(stage_b_top_n_schedules))]]
    report_obj = {
        "search_budget": {
            "seeds": seeds,
            "stage_a_schedules_per_seed": int(stage_a_schedules_per_seed),
            "stage_a_micro_per_schedule": int(stage_a_micro_per_schedule),
            "stage_a_fraction": float(stage_a_fraction),
            "stage_b_top_n_schedules": int(stage_b_top_n_schedules),
            "stage_b_micro_per_schedule": int(stage_b_micro_per_schedule),
            "time_limit_s": time_limit_s,
            "k_lo": k_lo,
            "k_hi": k_hi,
            "schedule_family": str(schedule_family),
            "ew_proxy_threshold": ew_proxy_th,
            "gi_level": str(gi_level),
            "ew_mode": str(ew_mode),
            "ew_blend": {"node": float(ew_blend_node_weight), "coarse_cell": float(ew_blend_coarse_weight)},
            "u1_scale_family": _u1_scale_family_spec(),
            "min_cross_m_edges": {"micro": int(min_cross_m_edges_micro), "coarse": int(min_cross_m_edges_coarse)},
            "parallel_mode": False,
        },
        "completed_jobs": int(job_i),
        "wall_clock_seconds": float(time.time() - t0),
        "best": best,
        "skip_counts": skip_counts,
        "best_trace": best_trace,
        "schedule_leaderboard": leaderboard,
    }
    out_report.write_text(json.dumps(report_obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    pe.done(extra=f"wrote {out_report}")
    print(f"Wrote {out_report}")
    print(f"Wrote {out_dir / 'wiring_geometry.json'}")
    print(f"Wrote {out_dir / 'wiring_3d_perspective_annotated.png'}")


if __name__ == "__main__":
    main()

