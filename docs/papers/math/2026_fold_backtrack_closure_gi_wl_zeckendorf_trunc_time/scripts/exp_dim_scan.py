#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bit-split dimension scan (open boundary), plus summary plots."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib.pyplot as plt

from closure_graph import build_closure_graph
from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import export_dir, paper_root
from micro_models import balanced_splits, bitsplit_neighbors
from wl1 import micro_partition_stats, wl1_refine


def _splits_str(splits: Sequence[int]) -> str:
    return "-".join(str(x) for x in splits)


def _write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "m",
                "d",
                "splits",
                "stable_t",
                "resolve_t",
                "unresolved_micro_final",
                "max_micro_class_size_final",
                "non_single_micro_classes_final",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _plot_resolve_vs_d(path: Path, series: Dict[int, List[Tuple[int, float]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 3.6))
    for m, pts in sorted(series.items()):
        xs = [d for d, _ in pts]
        ys = [v for _, v in pts]
        plt.plot(xs, ys, marker="o", linewidth=1.5, label=f"m={m}")
    plt.xlabel("d (dimension)")
    plt.ylabel("resolve_t (WL1)")
    plt.title("Resolve time vs dimension (bit-split open)")
    plt.grid(True, alpha=0.3)
    plt.legend(ncol=2, fontsize=9)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_unresolved_vs_d(path: Path, series: Dict[int, List[Tuple[int, int]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 3.6))
    for m, pts in sorted(series.items()):
        xs = [d for d, _ in pts]
        ys = [v for _, v in pts]
        plt.plot(xs, ys, marker="o", linewidth=1.5, label=f"m={m}")
    plt.xlabel("d (dimension)")
    plt.ylabel("unresolved_micro_final (WL1)")
    plt.title("Unresolved micro vs dimension (bit-split open)")
    plt.grid(True, alpha=0.3)
    plt.legend(ncol=2, fontsize=9)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", type=str, default="6,9,12,15")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    ms = [int(x.strip()) for x in args.ms.split(",") if x.strip()]

    out_csv_name = "dim_scan_m6_m9_m12_m15.csv"
    out_png_resolve = "resolve_time_vs_dimension_m6_m9_m12_m15.png"
    out_png_unresolved = "unresolved_vs_dimension_m6_m9_m12_m15.png"

    script_path = Path(__file__).resolve()
    params = {"ms": ms, "boundary": "open", "model": "bitsplit"}
    run = prepare_run(
        experiment="dim_scan_bitsplit_open",
        params=params,
        script_path=script_path,
        required_files=[out_csv_name, out_png_resolve, out_png_unresolved],
        force=args.force,
    )

    if run.cached:
        print(f"[exp_dim_scan] cached: {run.run_dir.name}", flush=True)
        for nm in [out_csv_name, out_png_resolve, out_png_unresolved]:
            copy_atomic(run.run_dir / nm, export_dir() / nm)
        return

    rows: List[Dict[str, object]] = []
    resolve_series: Dict[int, List[Tuple[int, float]]] = {}
    unresolved_series: Dict[int, List[Tuple[int, int]]] = {}

    for m in ms:
        print(f"[exp_dim_scan] m={m}", flush=True)
        n = 1 << m
        resolve_pts: List[Tuple[int, float]] = []
        unresolved_pts: List[Tuple[int, int]] = []
        for d in range(1, m + 1):
            splits = balanced_splits(m, d)
            adj = bitsplit_neighbors(n=n, splits=splits, torus=False)
            clo = build_closure_graph(m=m, micro_adj=adj)

            # initial colors:
            # - micro vertices share one color (0)
            # - each macro vertex gets a unique color (1 + macro_idx)
            init_colors = [0] * clo.n_total
            for v in clo.macro_range:
                init_colors[v] = 1 + (v - clo.n_micro)

            stats = wl1_refine(
                n_nodes=clo.n_total,
                neighbors=clo.neighbors,
                init_colors=init_colors,
                micro_nodes=clo.micro_range,
                max_iter=200,
                progress_every=2 if (m >= 12 and d <= 2) else 5 if (m >= 12) else 1,
            )
            pstats = micro_partition_stats(stats.colors, clo.micro_range)
            resolve_t = "" if stats.resolve_t is None else float(stats.resolve_t)

            rows.append(
                {
                    "m": m,
                    "d": d,
                    "splits": _splits_str(splits),
                    "stable_t": stats.stable_t,
                    "resolve_t": resolve_t,
                    "unresolved_micro_final": pstats.unresolved_micro_final,
                    "max_micro_class_size_final": pstats.max_micro_class_size_final,
                    "non_single_micro_classes_final": pstats.non_single_micro_classes_final,
                }
            )

            if stats.resolve_t is not None:
                resolve_pts.append((d, float(stats.resolve_t)))
            unresolved_pts.append((d, pstats.unresolved_micro_final))

        resolve_series[m] = resolve_pts
        unresolved_series[m] = unresolved_pts

    out_csv = run.run_dir / out_csv_name
    out_png1 = run.run_dir / out_png_resolve
    out_png2 = run.run_dir / out_png_unresolved
    _write_csv(out_csv, rows)
    _plot_resolve_vs_d(out_png1, resolve_series)
    _plot_unresolved_vs_d(out_png2, unresolved_series)

    manifest = build_base_manifest("dim_scan_bitsplit_open", run.run_id, params, script_path)
    manifest = add_output_hashes(manifest, run.run_dir, [out_csv_name, out_png_resolve, out_png_unresolved])
    write_manifest(run.run_dir, manifest)

    for nm in [out_csv_name, out_png_resolve, out_png_unresolved]:
        copy_atomic(run.run_dir / nm, export_dir() / nm)
    print("[exp_dim_scan] done", flush=True)


if __name__ == "__main__":
    main()

