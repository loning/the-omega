#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Independent search experiment:
  Find wiring candidates with a "better" cross-m (m!=m') interface structure.

Motivation:
  Current best holonomy-GI wiring has few and very long cross-m edges, which makes U(1)/alpha
  interface audits sparse and unstable. Here we directly optimize cross-m interface statistics.

This script is self-contained as a *search*: it does not read any prior search report.
It produces:
  - a report JSON (best candidate + metrics),
  - a concrete wiring_geometry.json (2D+3D) for the best candidate,
  - annotated 3D PNG visualizations emphasizing cross-m edges and their endpoints.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common_paths import figures_dir
from common_progress import ProgressEvery
from hilbert_sm_center_graph import BuildConstraints, CenterGraph, build_center_graph_fixed
from hilbert_sm_canonical import canonical_signature_type_transition_graph
from hilbert_sm_schedule_search import sample_richer_schedule, schedule_stats


Pt3 = Tuple[float, float, float]


def _extract_segments(points: List[Tuple[float, ...]]) -> List[Tuple[Tuple[float, ...], Tuple[float, ...]]]:
    segs: List[Tuple[Tuple[float, ...], Tuple[float, ...]]] = []
    for a, b in zip(points[:-1], points[1:]):
        segs.append((tuple(float(x) for x in a), tuple(float(x) for x in b)))
    return segs


def _euclid(a: Sequence[float], b: Sequence[float]) -> float:
    return float(math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b))))


def _pt_key(pt: Sequence[float], ndigits: int = 6) -> Tuple[float, float, float]:
    return (round(float(pt[0]), ndigits), round(float(pt[1]), ndigits), round(float(pt[2]), ndigits))


def _cross_m_edges(g: CenterGraph) -> List[Dict[str, Any]]:
    """
    Return cross-m scan edges as a list of records with endpoints and length.
    """
    out: List[Dict[str, Any]] = []
    for a_id, b_id in g.scan_edges:
        a = g.nodes[int(a_id)]
        b = g.nodes[int(b_id)]
        if int(a.m) == int(b.m):
            continue
        length = _euclid(a.pt, b.pt)
        out.append(
            {
                "a": {
                    "id": int(a.id),
                    "k_coarse": int(a.k_coarse),
                    "m": int(a.m),
                    "pt": [float(a.pt[0]), float(a.pt[1]), float(a.pt[2])],
                    "u6": str(a.u6),
                    "label": str(a.label_tex),
                    "rep": str(a.rep_tex),
                },
                "b": {
                    "id": int(b.id),
                    "k_coarse": int(b.k_coarse),
                    "m": int(b.m),
                    "pt": [float(b.pt[0]), float(b.pt[1]), float(b.pt[2])],
                    "u6": str(b.u6),
                    "label": str(b.label_tex),
                    "rep": str(b.rep_tex),
                },
                "length": float(length),
                "pair": f"{int(a.m)}->{int(b.m)}",
            }
        )
    out.sort(key=lambda r: (-float(r["length"]), r["pair"]))
    return out


def _interface_metrics(cross_edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = int(len(cross_edges))
    if n <= 0:
        return {
            "n_cross": 0,
            "len_mean": float("inf"),
            "len_max": float("inf"),
            "len_sum": float("inf"),
            "pairs": {},
        }
    lens = [float(e["length"]) for e in cross_edges]
    pairs: Dict[str, int] = {}
    for e in cross_edges:
        pairs[str(e.get("pair", "?"))] = int(pairs.get(str(e.get("pair", "?")), 0)) + 1
    return {
        "n_cross": n,
        "len_mean": float(sum(lens) / len(lens)),
        "len_max": float(max(lens)),
        "len_sum": float(sum(lens)),
        "pairs": dict(sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def _score_interface(
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
    """
    n_cross = int(met.get("n_cross", 0))
    len_mean = float(met.get("len_mean", float("inf")))
    len_max = float(met.get("len_max", float("inf")))
    len_sum = float(met.get("len_sum", float("inf")))
    pairs = met.get("pairs", {}) or {}
    n_6_10 = int(pairs.get("6->10", 0)) + int(pairs.get("10->6", 0))
    return float((-w_count * n_cross) + w_mean * len_mean + w_max * len_max + w_sum * len_sum + w_direct_6_10 * n_6_10)


def _set_equal_3d_limits(ax, xs, ys, zs, pad: float = 0.6):
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)
    cx = 0.5 * (xmin + xmax)
    cy = 0.5 * (ymin + ymax)
    cz = 0.5 * (zmin + zmax)
    rx = (xmax - xmin) * 0.5
    ry = (ymax - ymin) * 0.5
    rz = (zmax - zmin) * 0.5
    r = max(rx, ry, rz, 1e-9) + pad
    ax.set_xlim(cx - r, cx + r)
    ax.set_ylim(cy - r, cy + r)
    ax.set_zlim(cz - r, cz + r)
    try:
        ax.set_box_aspect((1, 1, 1))
    except Exception:
        pass


def _render_3d_interface_png(
    *,
    out_png: Path,
    g3: CenterGraph,
    cross_edges: List[Dict[str, Any]],
    title: str,
    elev: float,
    azim: float,
    label_top_edges: int,
) -> None:
    pts3 = [g3.nodes[int(nid)].pt for nid in g3.scan_path]
    xs = [float(p[0]) for p in pts3]
    ys = [float(p[1]) for p in pts3]
    zs = [float(p[2]) for p in pts3]

    fig = plt.figure(figsize=(10.5, 8.2), dpi=300)
    ax = fig.add_subplot(111, projection="3d")

    # Material-ish palette
    m_node_color = {6: "#1565C0", 8: "#FB8C00", 10: "#2E7D32"}
    edge_default = "#263238"
    edge_cross = "#C62828"

    # Fast lookup for cross edges by endpoint ids
    cross_pairs = set()
    for e in cross_edges:
        a = (e.get("a") or {}).get("id")
        b = (e.get("b") or {}).get("id")
        if isinstance(a, int) and isinstance(b, int):
            cross_pairs.add((int(a), int(b)))

    # Draw scan edges
    for a_id, b_id in g3.scan_edges:
        a = g3.nodes[int(a_id)]
        b = g3.nodes[int(b_id)]
        col = edge_default
        if int(a.m) != int(b.m):
            col = edge_cross
        ax.plot([a.pt[0], b.pt[0]], [a.pt[1], b.pt[1]], [a.pt[2], b.pt[2]], color=col, lw=1.2, alpha=0.9)

    # Scatter nodes by m
    buckets = {6: ([], [], []), 8: ([], [], []), 10: ([], [], [])}
    other = ([], [], [])
    for n in g3.nodes:
        pt = n.pt
        if int(n.m) in buckets:
            bx, by, bz = buckets[int(n.m)]
            bx.append(float(pt[0]))
            by.append(float(pt[1]))
            bz.append(float(pt[2]))
        else:
            ox, oy, oz = other
            ox.append(float(pt[0]))
            oy.append(float(pt[1]))
            oz.append(float(pt[2]))
    for m in (6, 8, 10):
        bx, by, bz = buckets[m]
        if bx:
            ax.scatter(bx, by, bz, s=10, c=m_node_color[m], alpha=0.95, depthshade=False, label=f"m={m}")
    if other[0]:
        ax.scatter(other[0], other[1], other[2], s=10, c="#6D4C41", alpha=0.95, depthshade=False, label="m=other")

    # Label endpoints of the longest cross-m edges
    for e in cross_edges[: int(max(0, label_top_edges))]:
        a = e["a"]
        b = e["b"]
        la = f"k={int(a['k_coarse'])} m={int(a['m'])}"
        lb = f"k={int(b['k_coarse'])} m={int(b['m'])}"
        xa, ya, za = a["pt"]
        xb, yb, zb = b["pt"]
        ax.text(float(xa), float(ya), float(za) + 0.18, la, fontsize=10, color="#111111")
        ax.text(float(xb), float(yb), float(zb) + 0.18, lb, fontsize=10, color="#111111")
        # Put length label at midpoint
        xm = 0.5 * (float(xa) + float(xb))
        ym = 0.5 * (float(ya) + float(yb))
        zm = 0.5 * (float(za) + float(zb))
        ax.text(xm, ym, zm + 0.22, f"{float(e['length']):.2f}", fontsize=10, color=edge_cross)

    _set_equal_3d_limits(ax, xs, ys, zs)
    ax.view_init(elev=float(elev), azim=float(azim))
    ax.set_axis_off()
    ax.legend(loc="upper left", frameon=False, fontsize=12)
    ax.set_title(title)
    fig.tight_layout(pad=0.0)
    fig.savefig(out_png, facecolor="white", transparent=False)
    plt.close(fig)


def _as_int_dict(d: Dict[int, int] | Dict[str, Any]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for k, v in (d or {}).items():
        out[int(k)] = int(v)
    return out


def refined_ks(sched: Dict[int, int]) -> List[int]:
    return sorted([int(k) for k, m in sched.items() if int(m) > 6])


def sample_choice(rng: random.Random, ks: List[int], n_opts: int) -> Dict[int, int]:
    return {int(k): int(rng.randrange(int(n_opts))) for k in ks}


def _load_prev_best(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            b = obj.get("best")
            if isinstance(b, dict) and "score" in b:
                return b
    except Exception:
        return None
    return None


def _write_best_artifacts(
    *,
    out_dir: Path,
    out_data: Path,
    out_report: Path,
    report_obj: Dict[str, Any],
    best: Dict[str, Any],
    best_g2: CenterGraph,
    best_g3: CenterGraph,
    best_cross3: List[Dict[str, Any]],
    elev: float,
    azim: float,
    label_top_edges: int,
    latest: bool,
) -> None:
    """
    Write:
      - report JSON
      - wiring_geometry(_latest).json
      - cross_m_edges_ranked(_latest).json
      - wiring_3d_interface(_latest).png
      - wiring_3d_interface_annotated(_latest).png
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_data.mkdir(parents=True, exist_ok=True)

    # Report
    out_report.write_text(json.dumps(report_obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    suf = "_latest" if latest else ""

    # wiring_geometry.json (schema compatible with existing figure scripts)
    pts2 = [best_g2.nodes[int(nid)].pt for nid in best_g2.scan_path]
    pts3 = [best_g3.nodes[int(nid)].pt for nid in best_g3.scan_path]
    geo = {
        "source": {"report": str(out_report.name), "picked": "best", "score": float(best["score"])},
        "constraints": dict(best.get("constraints", {})),
        "m_schedule_by_k": dict(best.get("m_schedule_by_k", {})),
        "choice2": dict(best.get("choice2", {})),
        "choice3": dict(best.get("choice3", {})),
        "graph2d": {
            "n_nodes": len(best_g2.nodes),
            "scan_path_node_ids": [int(x) for x in best_g2.scan_path],
            "segments": [([a[0], a[1]], [b[0], b[1]]) for a, b in _extract_segments(pts2)],
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
                for n in best_g2.nodes
            ],
        },
        "graph3d": {
            "n_nodes": len(best_g3.nodes),
            "scan_path_node_ids": [int(x) for x in best_g3.scan_path],
            "segments": [([a[0], a[1], a[2]], [b[0], b[1], b[2]]) for a, b in _extract_segments(pts3)],
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
                for n in best_g3.nodes
            ],
        },
    }
    (out_dir / f"wiring_geometry{suf}.json").write_text(
        json.dumps(geo, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )

    # cross-m ranking
    (out_dir / f"cross_m_edges_ranked{suf}.json").write_text(
        json.dumps({"edges": best_cross3, "metrics": _interface_metrics(best_cross3)}, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # PNGs
    _render_3d_interface_png(
        out_png=out_dir / f"wiring_3d_interface{suf}.png",
        g3=best_g3,
        cross_edges=[],
        title="3D wiring (interface-optimized candidate)",
        elev=float(elev),
        azim=float(azim),
        label_top_edges=0,
    )
    _render_3d_interface_png(
        out_png=out_dir / f"wiring_3d_interface_annotated{suf}.png",
        g3=best_g3,
        cross_edges=best_cross3,
        title="3D wiring (interface-optimized candidate): cross-m edges highlighted",
        elev=float(elev),
        azim=float(azim),
        label_top_edges=int(label_top_edges),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-start", type=int, default=900)
    ap.add_argument("--seed-count", type=int, default=20)
    ap.add_argument("--schedules-per-seed", type=int, default=25)
    ap.add_argument("--micro-per-schedule", type=int, default=40)
    ap.add_argument("--time-limit-s", type=float, default=600.0)
    ap.add_argument("--k-lo", type=int, default=18)
    ap.add_argument("--k-hi", type=int, default=52)
    ap.add_argument("--require-type-sig-match", action="store_true")
    ap.add_argument("--enforce-edge-types", action="store_true")
    ap.add_argument("--enforce-noncrossing-xy", action="store_true")
    ap.add_argument("--forbid-pass-through-centers", action="store_true")
    ap.add_argument("--w-count", type=float, default=2.0, help="Reward for n_cross (higher => more cross-m edges).")
    ap.add_argument("--w-mean", type=float, default=1.0, help="Penalty for mean cross-m length.")
    ap.add_argument("--w-max", type=float, default=0.7, help="Penalty for max cross-m length.")
    ap.add_argument("--w-sum", type=float, default=0.02, help="Penalty for sum cross-m length.")
    ap.add_argument("--w-direct-6-10", type=float, default=2.5, help="Penalty for direct 6<->10 edges.")
    ap.add_argument("--label-top-edges", type=int, default=8, help="Label endpoints of top-N longest cross edges.")
    ap.add_argument("--elev", type=float, default=22.0)
    ap.add_argument("--azim", type=float, default=-52.0)
    ap.add_argument("--checkpoint-s", type=float, default=60.0, help="Write *_latest artifacts every N seconds (0 disables).")
    ap.add_argument("--resume-best", action="store_true", help="Resume best score from existing report, if present.")
    args = ap.parse_args()

    out_root = figures_dir() / "adaptive" / "sm_hilbert_isomorphism"
    out_data = out_root / "data"
    out_data.mkdir(parents=True, exist_ok=True)

    out_dir = out_root / "wiring_fold_geometry_cross_m_interface"
    out_dir.mkdir(parents=True, exist_ok=True)

    cons = BuildConstraints(
        enforce_edge_types=bool(args.enforce_edge_types),
        enforce_noncrossing_xy=bool(args.enforce_noncrossing_xy),
        forbid_passing_through_centers=bool(args.forbid_pass_through_centers),
    )

    seeds = list(range(int(args.seed_start), int(args.seed_start) + int(args.seed_count)))
    schedules_per_seed = int(args.schedules_per_seed)
    micro_per_schedule = int(args.micro_per_schedule)
    time_limit_s = float(args.time_limit_s)
    k_lo = int(args.k_lo)
    k_hi = int(args.k_hi)

    w_count = float(args.w_count)
    w_mean = float(args.w_mean)
    w_max = float(args.w_max)
    w_sum = float(args.w_sum)
    w_610 = float(args.w_direct_6_10)

    total = len(seeds) * schedules_per_seed * micro_per_schedule
    pe = ProgressEvery(label="exp_sm_hilbert_cross_m_interface_search", total=total, interval_s=60.0)
    pe.start()
    t0 = time.time()
    last_ckpt = float(t0)

    best: Optional[Dict[str, Any]] = None
    best_g2: Optional[CenterGraph] = None
    best_g3: Optional[CenterGraph] = None
    best_cross3: Optional[List[Dict[str, Any]]] = None

    out_report = out_data / "sm_hilbert_cross_m_interface_search_report.json"
    if bool(args.resume_best):
        prev_best = _load_prev_best(out_report)
        if isinstance(prev_best, dict) and "score" in prev_best:
            best = prev_best

    i = 0
    for seed in seeds:
        rng = random.Random(int(seed))
        for si in range(schedules_per_seed):
            if (time.time() - t0) > time_limit_s:
                break
            sched = sample_richer_schedule(rng, k_lo=k_lo, k_hi=k_hi)
            ks = refined_ks(sched)
            sst = schedule_stats(sched, k_min=k_lo, k_max=k_hi)
            for _ in range(micro_per_schedule):
                if (time.time() - t0) > time_limit_s:
                    break
                extra = f"seed={seed} sch={si} chg={sst.n_changed} sw={sst.n_switches} maxm={sst.max_m}"
                if isinstance(best, dict):
                    bm = (best.get("metrics_3d") or {}) if isinstance(best.get("metrics_3d"), dict) else {}
                    extra += f" best_score={float(best.get('score', float('nan'))):.3f} best_cross={int(bm.get('n_cross', 0))} best_max={float(bm.get('len_max', float('nan'))):.2f}"
                pe.maybe(i, extra=extra)
                i += 1

                # Fixed micro-option families: 16 (2D) and 48 (3D), matching existing figures/scripts.
                choice2 = sample_choice(rng, ks, n_opts=16)
                choice3 = sample_choice(rng, ks, n_opts=48)
                try:
                    g2 = build_center_graph_fixed(dim=2, m_by_k=sched, chosen_micro_option=choice2, max_micro_orders=16, constraints=cons)
                    g3 = build_center_graph_fixed(dim=3, m_by_k=sched, chosen_micro_option=choice3, max_micro_orders=48, constraints=cons)
                except Exception:
                    continue

                if bool(args.require_type_sig_match):
                    try:
                        if canonical_signature_type_transition_graph(g2) != canonical_signature_type_transition_graph(g3):
                            continue
                    except Exception:
                        continue

                cross3 = _cross_m_edges(g3)
                met3 = _interface_metrics(cross3)
                score = _score_interface(met3, w_count=w_count, w_mean=w_mean, w_max=w_max, w_sum=w_sum, w_direct_6_10=w_610)

                cand: Dict[str, Any] = {
                    "score": float(score),
                    "metrics_3d": met3,
                    "constraints": asdict(cons),
                    "seed": int(seed),
                    "schedule_stats_klo_khi": asdict(sst),
                    "k_lo": int(k_lo),
                    "k_hi": int(k_hi),
                    "m_schedule_by_k": {str(k): int(v) for k, v in sorted(sched.items())},
                    "choice2": {str(k): int(v) for k, v in sorted(choice2.items())},
                    "choice3": {str(k): int(v) for k, v in sorted(choice3.items())},
                }

                if best is None or float(score) < float(best["score"]):
                    best = cand
                    best_g2 = g2
                    best_g3 = g3
                    best_cross3 = cross3

                # Periodic checkpoint
                ckpt_s = float(args.checkpoint_s)
                if ckpt_s > 0.0 and best is not None and best_g2 is not None and best_g3 is not None and best_cross3 is not None:
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
                            "objective": {
                                "require_type_sig_match": bool(args.require_type_sig_match),
                                "w_count": w_count,
                                "w_mean": w_mean,
                                "w_max": w_max,
                                "w_sum": w_sum,
                                "w_direct_6_10": w_610,
                            },
                            "completed_jobs": i,
                            "wall_clock_seconds": now - t0,
                            "best": best,
                        }
                        _write_best_artifacts(
                            out_dir=out_dir,
                            out_data=out_data,
                            out_report=out_report,
                            report_obj=report_obj,
                            best=best,
                            best_g2=best_g2,
                            best_g3=best_g3,
                            best_cross3=best_cross3,
                            elev=float(args.elev),
                            azim=float(args.azim),
                            label_top_edges=int(args.label_top_edges),
                            latest=True,
                        )
                        last_ckpt = float(now)

        if (time.time() - t0) > time_limit_s:
            break

    if best is None or best_g2 is None or best_g3 is None or best_cross3 is None:
        raise RuntimeError("No feasible candidate found under the requested constraints/budget.")

    report_obj = {
        "search_budget": {
            "seeds": seeds,
            "schedules_per_seed": schedules_per_seed,
            "micro_per_schedule": micro_per_schedule,
            "time_limit_s": time_limit_s,
            "k_lo": k_lo,
            "k_hi": k_hi,
        },
        "objective": {
            "require_type_sig_match": bool(args.require_type_sig_match),
            "w_count": w_count,
            "w_mean": w_mean,
            "w_max": w_max,
            "w_sum": w_sum,
            "w_direct_6_10": w_610,
        },
        "completed_jobs": i,
        "wall_clock_seconds": time.time() - t0,
        "best": best,
    }

    _write_best_artifacts(
        out_dir=out_dir,
        out_data=out_data,
        out_report=out_report,
        report_obj=report_obj,
        best=best,
        best_g2=best_g2,
        best_g3=best_g3,
        best_cross3=best_cross3,
        elev=float(args.elev),
        azim=float(args.azim),
        label_top_edges=int(args.label_top_edges),
        latest=False,
    )
    pe.done(extra=f"wrote {out_report}")
    print(f"Wrote {out_report}")
    print(f"Wrote {out_dir / 'wiring_geometry.json'}")
    print(f"Wrote {out_dir / 'cross_m_edges_ranked.json'}")
    print(f"Wrote {out_dir / 'wiring_3d_interface.png'}")
    print(f"Wrote {out_dir / 'wiring_3d_interface_annotated.png'}")


if __name__ == "__main__":
    main()

