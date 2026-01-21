#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Autosweep driver for cross-m interface search.

Goal:
  Continuously explore *search parameters* (objective weights + constraint toggles + RNG ranges),
  keep an archive of runs, and track a global best under a *weight-independent* key:
    maximize n_cross, then minimize len_max, len_mean, len_sum, and direct 6<->10 edges.

This script calls:
  exp_hilbert_sm_cross_m_interface_search.py

Outputs:
  figures/adaptive/sm_hilbert_isomorphism/
    wiring_fold_geometry_cross_m_interface_sweep/runs/<run_id>/... (archived artifacts)
    wiring_fold_geometry_cross_m_interface_global_best/... (copy of best-by-key)
  figures/adaptive/sm_hilbert_isomorphism/data/
    sm_hilbert_cross_m_interface_autosweep_state.json
    sm_hilbert_cross_m_interface_autosweep_runs.jsonl

Notes:
  - English-only output (filenames, keys).
  - Uses only stdlib + existing local scripts.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from common_paths import figures_dir


def _now_tag() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _best_key_from_report(report: Dict[str, Any]) -> Optional[Tuple[int, float, float, float, int]]:
    best = report.get("best")
    if not isinstance(best, dict):
        return None
    met = best.get("metrics_3d")
    if not isinstance(met, dict):
        return None
    n_cross = int(met.get("n_cross", 0))
    len_max = float(met.get("len_max", float("inf")))
    len_mean = float(met.get("len_mean", float("inf")))
    len_sum = float(met.get("len_sum", float("inf")))
    pairs = met.get("pairs") if isinstance(met.get("pairs"), dict) else {}
    n_6_10 = int(pairs.get("6->10", 0)) + int(pairs.get("10->6", 0))
    # Key: maximize n_cross => minimize (-n_cross, len_max, len_mean, len_sum, n_6_10)
    return (n_cross, len_max, len_mean, len_sum, n_6_10)


def _is_better(a: Tuple[int, float, float, float, int], b: Tuple[int, float, float, float, int]) -> bool:
    """
    Return True if a is better than b.
    """
    # Higher n_cross is better; the rest lower is better.
    if a[0] != b[0]:
        return a[0] > b[0]
    if a[1] != b[1]:
        return a[1] < b[1]
    if a[2] != b[2]:
        return a[2] < b[2]
    if a[3] != b[3]:
        return a[3] < b[3]
    return a[4] < b[4]


def _sample_weights(rng: random.Random) -> Dict[str, float]:
    # Keep weights in sane ranges; search will self-stabilize.
    return {
        "w_count": float(rng.uniform(1.0, 5.0)),
        "w_mean": float(rng.uniform(0.3, 2.5)),
        "w_max": float(rng.uniform(0.2, 2.0)),
        "w_sum": float(rng.uniform(0.0, 0.08)),
        "w_direct_6_10": float(rng.uniform(1.0, 6.0)),
    }


def _sample_constraints(rng: random.Random, phase: int) -> Dict[str, bool]:
    # Phase 0: keep it loose to explore.
    # Later phases occasionally tighten one knob at a time.
    if phase <= 0:
        return {"enforce_edge_types": False, "enforce_noncrossing_xy": False, "forbid_pass_through_centers": False}
    if phase == 1:
        return {
            "enforce_edge_types": rng.random() < 0.25,
            "enforce_noncrossing_xy": False,
            "forbid_pass_through_centers": rng.random() < 0.15,
        }
    # phase >= 2
    return {
        "enforce_edge_types": rng.random() < 0.4,
        "enforce_noncrossing_xy": rng.random() < 0.12,
        "forbid_pass_through_centers": rng.random() < 0.25,
    }


def _copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-seed", type=int, default=12345)
    ap.add_argument("--phase", type=int, default=0, help="0=loose, 1=semi-tight, 2+=tighter mix")
    ap.add_argument("--per-run-time-s", type=float, default=420.0)
    ap.add_argument("--per-run-seed-count", type=int, default=25)
    ap.add_argument("--per-run-schedules-per-seed", type=int, default=35)
    ap.add_argument("--per-run-micro-per-schedule", type=int, default=50)
    ap.add_argument("--checkpoint-s", type=float, default=60.0)
    ap.add_argument("--require-type-sig-prob", type=float, default=0.35)
    ap.add_argument("--label-top-edges", type=int, default=12)
    ap.add_argument("--elev", type=float, default=22.0)
    ap.add_argument("--azim", type=float, default=-52.0)
    args = ap.parse_args()

    rng = random.Random(int(args.run_seed))

    out_root = figures_dir() / "adaptive" / "sm_hilbert_isomorphism"
    out_data = out_root / "data"
    out_data.mkdir(parents=True, exist_ok=True)

    base_out_dir = out_root / "wiring_fold_geometry_cross_m_interface"
    sweep_dir = out_root / "wiring_fold_geometry_cross_m_interface_sweep" / "runs"
    best_dir = out_root / "wiring_fold_geometry_cross_m_interface_global_best"

    state_path = out_data / "sm_hilbert_cross_m_interface_autosweep_state.json"
    runs_path = out_data / "sm_hilbert_cross_m_interface_autosweep_runs.jsonl"

    # Load global best key if any.
    state = _read_json(state_path) or {}
    gb_key = None
    if isinstance(state.get("global_best_key"), list) and len(state["global_best_key"]) == 5:
        try:
            gb_key = (
                int(state["global_best_key"][0]),
                float(state["global_best_key"][1]),
                float(state["global_best_key"][2]),
                float(state["global_best_key"][3]),
                int(state["global_best_key"][4]),
            )
        except Exception:
            gb_key = None

    run_idx = int(state.get("run_idx", 0))

    script_dir = Path(__file__).resolve().parent
    search_script = script_dir / "exp_hilbert_sm_cross_m_interface_search.py"
    report_path = out_data / "sm_hilbert_cross_m_interface_search_report.json"

    while True:
        run_idx += 1
        run_id = f"{_now_tag()}_r{run_idx:06d}"

        weights = _sample_weights(rng)
        cons = _sample_constraints(rng, phase=int(args.phase))
        require_type = rng.random() < float(args.require_type_sig_prob)

        seed_start = int(rng.randrange(10_000, 10_000_000))

        cmd = [
            "python3",
            str(search_script),
            "--time-limit-s",
            str(float(args.per_run_time_s)),
            "--seed-start",
            str(seed_start),
            "--seed-count",
            str(int(args.per_run_seed_count)),
            "--schedules-per-seed",
            str(int(args.per_run_schedules_per_seed)),
            "--micro-per-schedule",
            str(int(args.per_run_micro_per_schedule)),
            "--checkpoint-s",
            str(float(args.checkpoint_s)),
            "--resume-best",
            "--label-top-edges",
            str(int(args.label_top_edges)),
            "--elev",
            str(float(args.elev)),
            "--azim",
            str(float(args.azim)),
            "--w-count",
            str(weights["w_count"]),
            "--w-mean",
            str(weights["w_mean"]),
            "--w-max",
            str(weights["w_max"]),
            "--w-sum",
            str(weights["w_sum"]),
            "--w-direct-6-10",
            str(weights["w_direct_6_10"]),
        ]
        if cons["enforce_edge_types"]:
            cmd.append("--enforce-edge-types")
        if cons["enforce_noncrossing_xy"]:
            cmd.append("--enforce-noncrossing-xy")
        if cons["forbid_pass_through_centers"]:
            cmd.append("--forbid-pass-through-centers")
        if require_type:
            cmd.append("--require-type-sig-match")

        t_run0 = time.time()
        try:
            subprocess.run(cmd, cwd=str(Path.cwd()), check=True)
        except Exception as e:
            # Write a failed-run entry and continue.
            rec = {
                "run_id": run_id,
                "run_idx": run_idx,
                "status": "failed",
                "error": str(e),
                "cmd": cmd,
                "elapsed_s": time.time() - t_run0,
                "weights": weights,
                "constraints": cons,
                "require_type_sig_match": bool(require_type),
                "seed_start": seed_start,
            }
            runs_path.parent.mkdir(parents=True, exist_ok=True)
            runs_path.write_text("", encoding="utf-8") if not runs_path.exists() else None
            with runs_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            # update state
            state = {"run_idx": run_idx, "global_best_key": list(gb_key) if gb_key else None, "last_run": rec}
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
            continue

        report = _read_json(report_path)
        key = _best_key_from_report(report or {})
        rec = {
            "run_id": run_id,
            "run_idx": run_idx,
            "status": "ok",
            "elapsed_s": time.time() - t_run0,
            "weights": weights,
            "constraints": cons,
            "require_type_sig_match": bool(require_type),
            "seed_start": seed_start,
            "best_key": list(key) if key else None,
            "best_metrics_3d": (report.get("best", {}) or {}).get("metrics_3d") if isinstance(report, dict) else None,
        }

        # Archive run artifacts by copying the whole base output directory.
        run_dst = sweep_dir / run_id
        try:
            _copy_tree(base_out_dir, run_dst)
        except Exception:
            # best effort; keep going
            pass

        # Update global best if improved.
        improved = False
        if key is not None and (gb_key is None or _is_better(key, gb_key)):
            gb_key = key
            improved = True
            try:
                _copy_tree(base_out_dir, best_dir)
            except Exception:
                pass

        rec["global_best_updated"] = bool(improved)
        rec["global_best_key"] = list(gb_key) if gb_key else None

        # Append run record.
        runs_path.parent.mkdir(parents=True, exist_ok=True)
        if not runs_path.exists():
            runs_path.write_text("", encoding="utf-8")
        with runs_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        # Update state.
        state = {"run_idx": run_idx, "global_best_key": list(gb_key) if gb_key else None, "last_run": rec}
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

        # Small pause to avoid tight loops if runs are extremely fast.
        time.sleep(float(rng.uniform(0.5, 2.0)))


if __name__ == "__main__":
    main()

