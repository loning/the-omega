#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostics: "gradient-like" landscape for the strong numeric search (discrete setting).

We produce auditable local-sensitivity plots around a given best candidate:
  - Schedule 1-step perturbations: change m(k) in {6,8,10} and record Δscore / ΔEW / ΔU1.
  - Micro-choice perturbations: vary choice2/choice3 for refined k and record Δscore.
  - U(1) joint-all landscape: heatmap of joint e_inf over (candidate, scale) family.

English-only output.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

from common_paths import figures_dir
from hilbert_sm_center_graph import BuildConstraints

import exp_hilbert_sm_numeric_match_strong_search as search


def _read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _parse_best(report: Dict[str, Any]) -> Dict[str, Any]:
    best = report.get("best")
    if not isinstance(best, dict):
        raise RuntimeError("Report missing 'best' dict.")
    return best


def _sched_from_best(best: Dict[str, Any]) -> Dict[int, int]:
    ms = best.get("m_schedule_by_k", {})
    if not isinstance(ms, dict):
        return {}
    return {int(k): int(v) for k, v in ms.items()}


def _choice_from_best(best: Dict[str, Any], key: str) -> Dict[int, int]:
    d = best.get(key, {})
    if not isinstance(d, dict):
        return {}
    return {int(k): int(v) for k, v in d.items()}


def _allowed_m_values() -> List[int]:
    return [6, 8, 10]


def _neighbor_ms(m: int) -> List[int]:
    vals = [x for x in _allowed_m_values() if int(x) != int(m)]
    return vals


def _sched_get(s: Dict[int, int], k: int) -> int:
    return int(s.get(int(k), 6))


def _sched_set(s: Dict[int, int], k: int, m: int) -> Dict[int, int]:
    out = dict((int(kk), int(vv)) for kk, vv in s.items())
    if int(m) == 6:
        out.pop(int(k), None)
    else:
        out[int(k)] = int(m)
    return out


def _choice_adjust_for_sched(
    sched: Dict[int, int],
    choice: Dict[int, int],
    *,
    default_value: int = 0,
) -> Dict[int, int]:
    """
    Ensure choice dict contains entries for refined ks and removes entries for m=6 cells.
    """
    out = dict((int(k), int(v)) for k, v in choice.items())
    for k in range(64):
        m = int(sched.get(int(k), 6))
        if m <= 6:
            out.pop(int(k), None)
        else:
            out.setdefault(int(k), int(default_value))
    # Keep only refined ks in the target window for clarity (still valid if extra keys exist).
    return out


def _score(
    *,
    sched: Dict[int, int],
    choice2: Dict[int, int],
    choice3: Dict[int, int],
    gi_level: str,
    ew_mode: str,
    ew_node_w: float,
    ew_coarse_w: float,
    min_cross_micro: int,
    min_cross_coarse: int,
) -> Dict[str, Any] | None:
    u_to_field = search._build_x6_to_field_map()
    cons = BuildConstraints(enforce_edge_types=False, enforce_noncrossing_xy=False, forbid_passing_through_centers=False)
    return search._score_one_candidate(
        u_to_field=u_to_field,
        cons=cons,
        sched=sched,
        choice2=choice2,
        choice3=choice3,
        w_ew=1.0,
        w_u1=1.0,
        k_lo=18,
        k_hi=52,
        gi_level=str(gi_level),
        ew_mode=str(ew_mode),
        ew_blend_node_weight=float(ew_node_w),
        ew_blend_coarse_weight=float(ew_coarse_w),
        min_cross_m_edges_micro=int(min_cross_micro),
        min_cross_m_edges_coarse=int(min_cross_coarse),
    )


def _extract_metrics(cand: Dict[str, Any]) -> Dict[str, float]:
    jb = (cand.get("u1") or {}).get("joint_best") or {}
    return {
        "score": float(cand.get("score", float("nan"))),
        "ew": float(cand.get("ew_score", float("nan"))),
        "ew_node": float(cand.get("ew_score_node", float("nan"))),
        "ew_coarse": float(cand.get("ew_score_coarse_cell", float("nan"))),
        "u1": float(cand.get("u1_score", float("nan"))),
        "u1_einf": float(jb.get("e_inf", float("nan"))),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=str, required=True, help="Path to sm_hilbert_numeric_match_strong_search_report.json")
    ap.add_argument("--out-dir", type=str, default="", help="Output directory (default under figures/adaptive/.../diagnostics).")
    ap.add_argument("--gi-level", type=str, default="", choices=["", "off", "type", "full"], help="Override GI level (default from report.best.gi.level).")
    ap.add_argument("--ew-mode", type=str, default="", choices=["", "node", "coarse_cell", "blend"], help="Override EW mode (default from report.best.ew_mode or blend).")
    ap.add_argument("--ew-blend-node-weight", type=float, default=0.25)
    ap.add_argument("--ew-blend-coarse-weight", type=float, default=1.0)
    ap.add_argument("--min-cross-m-edges-micro", type=int, default=0)
    ap.add_argument("--min-cross-m-edges-coarse", type=int, default=0)
    ap.add_argument("--micro-choice-tries-2d", type=int, default=6, help="How many alternative 2D micro options to try per refined k.")
    ap.add_argument("--micro-choice-tries-3d", type=int, default=6, help="How many alternative 3D micro options to try per refined k.")
    args = ap.parse_args()

    report = _read_json(Path(str(args.report)))
    best = _parse_best(report)

    # Match the U(1) scale-family mode used during the search run (if recorded).
    sb = report.get("search_budget") or {}
    u1sf = (sb.get("u1_scale_family") or {}) if isinstance(sb, dict) else {}
    mode = u1sf.get("mode") if isinstance(u1sf, dict) else None
    if mode:
        search.U1_SCALE_MODE = str(mode)

    sched0 = _sched_from_best(best)
    choice2_0 = _choice_from_best(best, "choice2")
    choice3_0 = _choice_from_best(best, "choice3")

    gi_level = str(args.gi_level) if str(args.gi_level) else str((best.get("gi") or {}).get("level", "type"))
    ew_mode = str(args.ew_mode) if str(args.ew_mode) else str(best.get("ew_mode") or "blend")
    ew_node_w = float(args.ew_blend_node_weight)
    ew_coarse_w = float(args.ew_blend_coarse_weight)
    min_cross_micro = int(args.min_cross_m_edges_micro)
    min_cross_coarse = int(args.min_cross_m_edges_coarse)

    base = _score(
        sched=sched0,
        choice2=_choice_adjust_for_sched(sched0, choice2_0),
        choice3=_choice_adjust_for_sched(sched0, choice3_0),
        gi_level=gi_level,
        ew_mode=ew_mode,
        ew_node_w=ew_node_w,
        ew_coarse_w=ew_coarse_w,
        min_cross_micro=min_cross_micro,
        min_cross_coarse=min_cross_coarse,
    )
    if base is None:
        raise RuntimeError("Baseline candidate is invalid under the requested gates.")
    base_m = _extract_metrics(base)

    if args.out_dir:
        out_dir = Path(str(args.out_dir))
    else:
        out_dir = figures_dir() / "adaptive" / "sm_hilbert_isomorphism" / "diagnostics" / "numeric_match_strong"
    _ensure_dir(out_dir)

    # 1) Schedule sensitivity (k in [18,52])
    ks = list(range(18, 53))
    delta_best: Dict[int, float] = {}
    grid = []  # records for jsonl-like export
    for k in ks:
        m0 = _sched_get(sched0, k)
        best_delta = float("inf")
        for m1 in _neighbor_ms(m0):
            sched1 = _sched_set(sched0, k, m1)
            c2 = _choice_adjust_for_sched(sched1, choice2_0)
            c3 = _choice_adjust_for_sched(sched1, choice3_0)
            cand = _score(
                sched=sched1,
                choice2=c2,
                choice3=c3,
                gi_level=gi_level,
                ew_mode=ew_mode,
                ew_node_w=ew_node_w,
                ew_coarse_w=ew_coarse_w,
                min_cross_micro=min_cross_micro,
                min_cross_coarse=min_cross_coarse,
            )
            if cand is None:
                grid.append({"kind": "schedule", "k": int(k), "m0": int(m0), "m1": int(m1), "ok": False})
                continue
            met = _extract_metrics(cand)
            d = float(met["score"] - base_m["score"])
            best_delta = min(best_delta, d)
            grid.append(
                {
                    "kind": "schedule",
                    "k": int(k),
                    "m0": int(m0),
                    "m1": int(m1),
                    "ok": True,
                    "delta_score": float(d),
                    "delta_ew": float(met["ew"] - base_m["ew"]),
                    "delta_u1": float(met["u1"] - base_m["u1"]),
                    "delta_u1_einf": float(met["u1_einf"] - base_m["u1_einf"]),
                }
            )
        delta_best[int(k)] = float(best_delta if math.isfinite(best_delta) else float("nan"))

    # Plot schedule best-improvement bar
    xs = np.array(ks, dtype=int)
    ys = np.array([delta_best[int(k)] for k in ks], dtype=float)
    plt.figure(figsize=(14, 4))
    plt.axhline(0.0, color="black", linewidth=1)
    plt.bar(xs, ys, color=["#d62728" if y < 0 else "#1f77b4" for y in ys])
    plt.title("Schedule 1-step sensitivity: best Δscore per k (negative=improves)")
    plt.xlabel("k")
    plt.ylabel("Δscore")
    plt.tight_layout()
    plt.savefig(out_dir / "schedule_sensitivity_best_delta.png", dpi=200)
    plt.close()

    # 2) Micro-choice sensitivity
    refined = sorted([k for k, m in sched0.items() if int(m) > 6])
    micro_rows = []
    for k in refined:
        # 2D choices (16)
        cur2 = int(choice2_0.get(int(k), 0))
        for t in range(1, int(args.micro_choice_tries_2d) + 1):
            v2 = int((cur2 + t) % 16)
            c2 = dict(choice2_0)
            c2[int(k)] = int(v2)
            c2 = _choice_adjust_for_sched(sched0, c2)
            c3 = _choice_adjust_for_sched(sched0, choice3_0)
            cand = _score(
                sched=sched0,
                choice2=c2,
                choice3=c3,
                gi_level=gi_level,
                ew_mode=ew_mode,
                ew_node_w=ew_node_w,
                ew_coarse_w=ew_coarse_w,
                min_cross_micro=min_cross_micro,
                min_cross_coarse=min_cross_coarse,
            )
            if cand is None:
                micro_rows.append({"kind": "micro2d", "k": int(k), "from": int(cur2), "to": int(v2), "ok": False})
                continue
            met = _extract_metrics(cand)
            micro_rows.append({"kind": "micro2d", "k": int(k), "from": int(cur2), "to": int(v2), "ok": True, "delta_score": float(met["score"] - base_m["score"])})

        # 3D choices (48)
        cur3 = int(choice3_0.get(int(k), 0))
        for t in range(1, int(args.micro_choice_tries_3d) + 1):
            v3 = int((cur3 + t) % 48)
            c3 = dict(choice3_0)
            c3[int(k)] = int(v3)
            c2 = _choice_adjust_for_sched(sched0, choice2_0)
            c3 = _choice_adjust_for_sched(sched0, c3)
            cand = _score(
                sched=sched0,
                choice2=c2,
                choice3=c3,
                gi_level=gi_level,
                ew_mode=ew_mode,
                ew_node_w=ew_node_w,
                ew_coarse_w=ew_coarse_w,
                min_cross_micro=min_cross_micro,
                min_cross_coarse=min_cross_coarse,
            )
            if cand is None:
                micro_rows.append({"kind": "micro3d", "k": int(k), "from": int(cur3), "to": int(v3), "ok": False})
                continue
            met = _extract_metrics(cand)
            micro_rows.append({"kind": "micro3d", "k": int(k), "from": int(cur3), "to": int(v3), "ok": True, "delta_score": float(met["score"] - base_m["score"])})

    # Summarize best micro delta per k
    best2 = {int(k): float("inf") for k in refined}
    best3 = {int(k): float("inf") for k in refined}
    for r in micro_rows:
        if not r.get("ok"):
            continue
        k = int(r["k"])
        d = float(r["delta_score"])
        if r["kind"] == "micro2d":
            best2[k] = min(best2[k], d)
        else:
            best3[k] = min(best3[k], d)
    plt.figure(figsize=(14, 4))
    xs2 = np.array(refined, dtype=int)
    y2 = np.array([best2[k] if math.isfinite(best2[k]) else np.nan for k in refined], dtype=float)
    y3 = np.array([best3[k] if math.isfinite(best3[k]) else np.nan for k in refined], dtype=float)
    plt.axhline(0.0, color="black", linewidth=1)
    plt.plot(xs2, y2, marker="o", label="2D micro (best Δscore)")
    plt.plot(xs2, y3, marker="o", label="3D micro (best Δscore)")
    plt.title("Micro-choice sensitivity: best Δscore per refined k")
    plt.xlabel("k (refined)")
    plt.ylabel("Δscore")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "micro_choice_sensitivity_best_delta.png", dpi=200)
    plt.close()

    # 3) U(1) joint-all landscape heatmap
    # Recompute groups from baseline geo.
    geo = base.get("geo") or {}
    groups: Dict[str, List[float]] = {}
    for gkey in ("graph2d", "graph3d"):
        g = geo.get(gkey, {})
        nodes = list(g.get("nodes", []))
        scan_ids = [int(x) for x in g.get("scan_path_node_ids", [])]
        coarse_nodes, coarse_scan = search._coarse_project(nodes, scan_ids)
        groups[f"{gkey}:micro"] = search._edges_strengths_flow_plus_mis(nodes, scan_ids)
        groups[f"{gkey}:coarse"] = search._edges_strengths_flow_plus_mis(coarse_nodes, coarse_scan)

    cand_list = search._candidates()
    scales = search._scale_family()
    alpha_low = float(search.ALPHA_INV_CODATA_2022)
    alpha_z = float(search.ALPHAZ_INV_PDG)

    def joint_einf_for(agg_id: str, kk: int, s: float) -> float:
        worst = 0.0
        for _name, xs in groups.items():
            basev = search._aggregate(xs, agg_id=agg_id, k=int(kk))
            if not (math.isfinite(basev) and basev > 0.0):
                return float("inf")
            pred = float(s) * float(basev)
            if pred <= 0.0 or not math.isfinite(pred):
                return float("inf")
            e_low = abs(math.log(pred / alpha_low))
            e_z = abs(math.log(pred / alpha_z))
            worst = max(worst, max(e_low, e_z))
        return float(worst)

    H = np.zeros((len(cand_list), len(scales)), dtype=float)
    for i, (agg_id, kk) in enumerate(cand_list):
        for j, s in enumerate(scales):
            H[i, j] = joint_einf_for(agg_id, kk, s)

    plt.figure(figsize=(12, 6))
    im = plt.imshow(H, aspect="auto", interpolation="nearest")
    plt.colorbar(im, label="joint e_inf")
    plt.yticks(
        ticks=list(range(len(cand_list))),
        labels=[f"{agg}(k={kk})" for (agg, kk) in cand_list],
        fontsize=8,
    )
    # With an extended scale family, labeling every tick becomes unreadable.
    step = max(1, int(len(scales) // 16))
    xt = list(range(0, len(scales), step))
    plt.xticks(
        ticks=xt,
        labels=[f"{math.log10(float(scales[i])):+.2f}" for i in xt],
        rotation=90,
        fontsize=8,
    )
    plt.xlabel("log10(scale) (subset ticks)")
    plt.ylabel("candidate")
    plt.title("U(1) joint-all landscape: e_inf over candidate × scale")
    plt.tight_layout()
    plt.savefig(out_dir / "u1_joint_landscape_einf.png", dpi=200)
    plt.close()

    # Write json diagnostics
    diag = {
        "baseline": {"gi_level": gi_level, "ew_mode": ew_mode, "metrics": base_m, "schedule": sched0, "choice2": choice2_0, "choice3": choice3_0},
        "schedule_best_delta": {str(k): float(delta_best[k]) for k in ks},
        "records": grid,
        "micro_records": micro_rows,
        "u1_candidates": [f"{agg}(k={kk})" for (agg, kk) in cand_list],
        "u1_scales": [float(s) for s in scales],
        "u1_landscape_einf": H.tolist(),
    }
    (out_dir / "diagnostics.json").write_text(json.dumps(diag, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out_dir / 'diagnostics.json'}")
    print(f"Wrote {out_dir / 'schedule_sensitivity_best_delta.png'}")
    print(f"Wrote {out_dir / 'micro_choice_sensitivity_best_delta.png'}")
    print(f"Wrote {out_dir / 'u1_joint_landscape_einf.png'}")


if __name__ == "__main__":
    main()

