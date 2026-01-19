#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Numeric-first search experiment:
  Match electroweak numeric targets (alpha^{-1}(m_Z), sin^2 theta_W) as early as possible.

Key point:
  The manuscript's "node-count" pushforward measure μ6 (count center nodes by stable type u6)
  depends primarily on the m-schedule (m=6/8/10) because refinement multiplies the number of
  center nodes per coarse cell deterministically (m=8 -> 4 nodes; m=10 -> 16 nodes) in both 2D and 3D.

Therefore, we can search schedules cheaply by scoring W_Y_eff implied by μ6_node, then only
materialize a concrete wiring geometry (wiring_geometry.json + 3D PNG) for the current best.

Outputs:
  figures/adaptive/sm_hilbert_isomorphism/data/sm_hilbert_numeric_match_search_report.json
  figures/adaptive/sm_hilbert_isomorphism/wiring_fold_geometry_numeric_match/
    - wiring_geometry.json
    - wiring_3d_perspective.png
    - wiring_3d_perspective_annotated.png (optional if you use fig_hilbert_sm_wiring_geometry_3d_png.py)

English-only output.
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

from common_constants import ALPHAZ_INV_PDG, SIN2_THETAW_PDG
from common_paths import figures_dir
from common_progress import ProgressEvery

import exp_sm_labeling_solver as sml
from hilbert_sm_center_graph import BuildConstraints, build_center_graph_fixed
from hilbert_sm_schedule_search import sample_richer_schedule, schedule_stats


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


def _node_multiplier_for_m(m: int) -> int:
    """
    Deterministic node-count multiplier per coarse cell for m in {6,8,10}.
    - m=6  -> 1 center
    - m=8  -> 4 centers
    - m=10 -> 16 centers
    """
    m = int(m)
    if m <= 6:
        return 1
    if m == 8:
        return 4
    if m == 10:
        return 16
    # For completeness, approximate with 2^(m-6) capped at 16 for this paper's standard experiments.
    return int(min(16, 2 ** int(m - 6)))


def _mu6_node_from_schedule(m_by_k: Dict[int, int]) -> Dict[str, float]:
    """
    μ6_node induced by schedule alone, under the deterministic refinement multiplicities.
    """
    X6 = sml.all_x6()
    counts: Dict[str, int] = {u: 0 for u in X6}
    for k in range(64):
        u = str(sml.fold6(int(k)))
        m = int(m_by_k.get(int(k), 6))
        counts[u] += int(_node_multiplier_for_m(m))
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
    }


def refined_ks(sched: Dict[int, int]) -> List[int]:
    return sorted([int(k) for k, m in sched.items() if int(m) > 6])


def sample_choice(rng: random.Random, ks: List[int], n_opts: int) -> Dict[int, int]:
    return {int(k): int(rng.randrange(int(n_opts))) for k in ks}


def _write_wiring_geometry(out_dir: Path, *, m_sched: Dict[int, int], choice2: Dict[int, int], choice3: Dict[int, int]) -> None:
    cons = BuildConstraints(enforce_edge_types=False, enforce_noncrossing_xy=False, forbid_passing_through_centers=False)
    g2 = build_center_graph_fixed(dim=2, m_by_k=m_sched, chosen_micro_option=choice2, max_micro_orders=16, constraints=cons)
    g3 = build_center_graph_fixed(dim=3, m_by_k=m_sched, chosen_micro_option=choice3, max_micro_orders=48, constraints=cons)

    pts2 = [g2.nodes[int(nid)].pt for nid in g2.scan_path]
    pts3 = [g3.nodes[int(nid)].pt for nid in g3.scan_path]

    def extract_segments(points: List[Tuple[float, ...]]):
        segs = []
        for a, b in zip(points[:-1], points[1:]):
            segs.append((tuple(float(x) for x in a), tuple(float(x) for x in b)))
        return segs

    geo = {
        "constraints": asdict(cons),
        "m_schedule_by_k": {str(k): int(v) for k, v in sorted(m_sched.items())},
        "choice2": {str(k): int(v) for k, v in sorted(choice2.items())},
        "choice3": {str(k): int(v) for k, v in sorted(choice3.items())},
        "graph2d": {
            "n_nodes": len(g2.nodes),
            "scan_path_node_ids": [int(x) for x in g2.scan_path],
            "segments": [([a[0], a[1]], [b[0], b[1]]) for a, b in extract_segments(pts2)],
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
            "segments": [([a[0], a[1], a[2]], [b[0], b[1], b[2]]) for a, b in extract_segments(pts3)],
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


def main() -> None:
    out_root = figures_dir() / "adaptive" / "sm_hilbert_isomorphism"
    out_data = out_root / "data"
    out_data.mkdir(parents=True, exist_ok=True)
    out_dir = out_root / "wiring_fold_geometry_numeric_match"
    out_dir.mkdir(parents=True, exist_ok=True)

    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-start", type=int, default=3000)
    ap.add_argument("--seed-count", type=int, default=40)
    ap.add_argument("--schedules-per-seed", type=int, default=80)
    ap.add_argument("--micro-per-schedule", type=int, default=1, help="Micro choices are irrelevant for node-count μ6; keep small.")
    ap.add_argument("--time-limit-s", type=float, default=600.0)
    ap.add_argument("--k-lo", type=int, default=18)
    ap.add_argument("--k-hi", type=int, default=52)
    ap.add_argument("--checkpoint-s", type=float, default=60.0)
    ap.add_argument("--resume-best", action="store_true")
    args = ap.parse_args()

    u_to_field = _build_x6_to_field_map()

    seeds = list(range(int(args.seed_start), int(args.seed_start) + int(args.seed_count)))
    schedules_per_seed = int(args.schedules_per_seed)
    micro_per_schedule = int(args.micro_per_schedule)
    time_limit_s = float(args.time_limit_s)
    k_lo = int(args.k_lo)
    k_hi = int(args.k_hi)
    ckpt_s = float(args.checkpoint_s)

    out_report = out_data / "sm_hilbert_numeric_match_search_report.json"

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

    total = len(seeds) * schedules_per_seed * micro_per_schedule
    pe = ProgressEvery(label="exp_sm_hilbert_numeric_match_search", total=total, interval_s=60.0)
    pe.start()
    t0 = time.time()
    last_ckpt = float(t0)
    i = 0

    for seed in seeds:
        rng = random.Random(int(seed))
        for si in range(schedules_per_seed):
            if (time.time() - t0) > time_limit_s:
                break
            sched = sample_richer_schedule(rng, k_lo=k_lo, k_hi=k_hi)
            sst = schedule_stats(sched, k_min=k_lo, k_max=k_hi)
            for _ in range(micro_per_schedule):
                if (time.time() - t0) > time_limit_s:
                    break
                extra = f"seed={seed} sch={si} chg={sst.n_changed} sw={sst.n_switches} maxm={sst.max_m}"
                if isinstance(best, dict):
                    extra += f" best_score={float(best.get('score', float('nan'))):.4g} best_e={float(best.get('e_sum', float('nan'))):.4g}"
                pe.maybe(i, extra=extra)
                i += 1

                mu6 = _mu6_node_from_schedule(sched)
                wy = _w_y_eff_from_mu6(mu6, u_to_field=u_to_field)
                ew = _ew_from_wy(wy)
                # score: numeric mismatch only (sum), plus small penalty if 2D/3D mismatch were to occur (here identical).
                score = float(ew["e_alpha"] + ew["e_sin2"])

                cand = {
                    "score": float(score),
                    "e_alpha": float(ew["e_alpha"]),
                    "e_sin2": float(ew["e_sin2"]),
                    "e_sum": float(score),
                    "w_y_eff": float(ew["w_y_eff"]),
                    "alpha_inv": float(ew["alpha_inv"]),
                    "sin2": float(ew["sin2"]),
                    "seed": int(seed),
                    "k_lo": int(k_lo),
                    "k_hi": int(k_hi),
                    "schedule_stats_klo_khi": asdict(sst),
                    "m_schedule_by_k": {str(k): int(v) for k, v in sorted(sched.items())},
                }

                if best is None or float(score) < float(best["score"]):
                    best = cand

                    # Materialize a concrete wiring only when improved.
                    ks = refined_ks(sched)
                    choice2 = sample_choice(rng, ks, n_opts=16)
                    choice3 = sample_choice(rng, ks, n_opts=48)
                    _write_wiring_geometry(out_dir, m_sched=sched, choice2=choice2, choice3=choice3)

                # checkpoint
                if ckpt_s > 0.0 and best is not None:
                    now = time.time()
                    if (now - last_ckpt) >= ckpt_s:
                        report_obj = {
                            "search_budget": {
                                "seeds": seeds,
                                "schedules_per_seed": schedules_per_seed,
                                "micro_per_schedule": micro_per_schedule,
                                "time_limit_s": time_limit_s,
                                "k_lo": k_lo,
                                "k_hi": k_hi,
                            },
                            "completed_jobs": i,
                            "wall_clock_seconds": now - t0,
                            "best": best,
                        }
                        out_report.write_text(json.dumps(report_obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
                        last_ckpt = float(now)

        if (time.time() - t0) > time_limit_s:
            break

    if best is None:
        raise RuntimeError("No candidate schedule scored.")

    report_obj = {
        "search_budget": {
            "seeds": seeds,
            "schedules_per_seed": schedules_per_seed,
            "micro_per_schedule": micro_per_schedule,
            "time_limit_s": time_limit_s,
            "k_lo": k_lo,
            "k_hi": k_hi,
        },
        "completed_jobs": i,
        "wall_clock_seconds": time.time() - t0,
        "best": best,
    }
    out_report.write_text(json.dumps(report_obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    pe.done(extra=f"wrote {out_report}")
    print(f"Wrote {out_report}")
    print(f"Wrote {out_dir / 'wiring_geometry.json'} (for current best)")


if __name__ == "__main__":
    main()

