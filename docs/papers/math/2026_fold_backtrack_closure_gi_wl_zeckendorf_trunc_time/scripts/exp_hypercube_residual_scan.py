#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hypercube WL1 residual scan for m=3..18."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt

from closure_graph import build_closure_graph
from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import export_dir, paper_root
from micro_models import hypercube_neighbors
from wl1 import micro_partition_stats, wl1_refine


def _write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "m",
                "resolve_t",
                "stable_t",
                "unresolved_micro_final",
                "non_single_micro_classes_final",
                "max_micro_class_size_final",
                "total_nodes",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _plot_unresolved(path: Path, ms: List[int], unresolved: List[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 3.5))
    plt.plot(ms, unresolved, marker="o", linewidth=1.5)
    plt.xlabel("m")
    plt.ylabel("unresolved_micro_final (WL1)")
    plt.title("Hypercube residual ambiguity under WL1 (closure graph)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m_min", type=int, default=3)
    ap.add_argument("--m_max", type=int, default=18)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    out_csv_name = "hypercube_residual_scan_m3_to_m18.csv"
    out_png_name = "hypercube_residual_ambiguity_m3_to_m18.png"

    script_path = Path(__file__).resolve()
    params = {"m_min": args.m_min, "m_max": args.m_max}
    run = prepare_run(
        experiment="hypercube_residual_scan",
        params=params,
        script_path=script_path,
        required_files=[out_csv_name, out_png_name],
        force=args.force,
    )

    if run.cached:
        print(f"[exp_hypercube_residual_scan] cached: {run.run_dir.name}", flush=True)
        copy_atomic(run.run_dir / out_csv_name, export_dir() / out_csv_name)
        copy_atomic(run.run_dir / out_png_name, export_dir() / out_png_name)
        return

    rows: List[Dict[str, object]] = []
    ms: List[int] = []
    unresolved_vals: List[int] = []

    for m in range(args.m_min, args.m_max + 1):
        print(f"[exp_hypercube_residual_scan] m={m}", flush=True)
        n = 1 << m
        adj = hypercube_neighbors(n=n, m=m)
        clo = build_closure_graph(m=m, micro_adj=adj)

        # initial colors: micro all 0, macro all 1 (unlabeled macro vertices)
        init_colors = [0] * clo.n_total
        for v in clo.macro_range:
            init_colors[v] = 1

        stats = wl1_refine(
            n_nodes=clo.n_total,
            neighbors=clo.neighbors,
            init_colors=init_colors,
            micro_nodes=clo.micro_range,
            max_iter=200,
            progress_every=1 if m <= 10 else 2,
        )
        pstats = micro_partition_stats(stats.colors, clo.micro_range)

        resolve_t = "" if stats.resolve_t is None else float(stats.resolve_t)
        row = {
            "m": m,
            "resolve_t": resolve_t,
            "stable_t": stats.stable_t,
            "unresolved_micro_final": pstats.unresolved_micro_final,
            "non_single_micro_classes_final": pstats.non_single_micro_classes_final,
            "max_micro_class_size_final": pstats.max_micro_class_size_final,
            "total_nodes": clo.n_total,
        }
        rows.append(row)
        ms.append(m)
        unresolved_vals.append(pstats.unresolved_micro_final)

    out_csv = run.run_dir / out_csv_name
    out_png = run.run_dir / out_png_name
    _write_csv(out_csv, rows)
    _plot_unresolved(out_png, ms=ms, unresolved=unresolved_vals)

    manifest = build_base_manifest("hypercube_residual_scan", run.run_id, params, script_path)
    manifest = add_output_hashes(manifest, run.run_dir, [out_csv_name, out_png_name])
    write_manifest(run.run_dir, manifest)

    copy_atomic(out_csv, export_dir() / out_csv_name)
    copy_atomic(out_png, export_dir() / out_png_name)
    print("[exp_hypercube_residual_scan] done", flush=True)


if __name__ == "__main__":
    main()

