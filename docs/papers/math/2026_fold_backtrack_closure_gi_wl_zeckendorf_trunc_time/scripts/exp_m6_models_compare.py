#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare micro geometries at m=6 (WL1 stats + simple Hilbert visualizations)."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt

from closure_graph import build_closure_graph
from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import export_dir, paper_root
from micro_models import (
    balanced_splits,
    bitsplit_neighbors,
    degree_stats,
    hilbert_embedding,
    hilbert_neighbors,
    hypercube_neighbors,
)
from wl1 import micro_partition_stats, wl1_refine


def _write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "model",
                "micro_degree_avg",
                "micro_degree_min",
                "micro_degree_max",
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


def _wl1_on_model(m: int, adj: List[List[int]]) -> Tuple[int, int | None, int, int, int]:
    clo = build_closure_graph(m=m, micro_adj=adj)
    init_colors = [0] * clo.n_total
    for v in clo.macro_range:
        init_colors[v] = 1
    stats = wl1_refine(
        n_nodes=clo.n_total,
        neighbors=clo.neighbors,
        init_colors=init_colors,
        micro_nodes=clo.micro_range,
        max_iter=200,
        progress_every=1,
    )
    pstats = micro_partition_stats(stats.colors, clo.micro_range)
    return (
        stats.stable_t,
        stats.resolve_t,
        pstats.unresolved_micro_final,
        pstats.max_micro_class_size_final,
        pstats.non_single_micro_classes_final,
    )


def _plot_hilbert2d(path: Path, coords: List[Tuple[int, int]], L: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = [[0 for _ in range(L)] for _ in range(L)]
    for idx, (x, y) in enumerate(coords):
        img[y][x] = idx
    plt.figure(figsize=(4, 4))
    plt.imshow(img, origin="lower", cmap="viridis")
    plt.axis("off")
    plt.title("m=6 Hilbert 2D (8x8) index embedding", fontsize=10)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_hilbert3d_layers(path: Path, coords: List[Tuple[int, int, int]], L: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    layers = [[[0 for _ in range(L)] for _ in range(L)] for _ in range(L)]
    for idx, (x, y, z) in enumerate(coords):
        layers[z][y][x] = idx

    fig, axes = plt.subplots(2, 2, figsize=(6, 6))
    for z, ax in enumerate(axes.flat):
        ax.imshow(layers[z], origin="lower", cmap="viridis")
        ax.set_title(f"z={z}", fontsize=10)
        ax.axis("off")
    fig.suptitle("m=6 Hilbert 3D (4x4x4) layers", fontsize=11)
    fig.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    m = 6
    out_csv_name = "m6_wl1_hilbert_vs_bitsplit_vs_hypercube.csv"
    out_h2 = "m6_2d_hilbert_grid.png"
    out_h3 = "m6_3d_hilbert_layers.png"

    script_path = Path(__file__).resolve()
    params = {"m": m}
    run = prepare_run(
        experiment="m6_models_compare",
        params=params,
        script_path=script_path,
        required_files=[out_csv_name, out_h2, out_h3],
        force=args.force,
    )

    if run.cached:
        print(f"[exp_m6_models_compare] cached: {run.run_dir.name}", flush=True)
        for nm in [out_csv_name, out_h2, out_h3]:
            copy_atomic(run.run_dir / nm, export_dir() / nm)
        return

    rows: List[Dict[str, object]] = []

    # bitsplit 3d split 2-2-2
    splits_3d = [2, 2, 2]
    adj = bitsplit_neighbors(n=1 << m, splits=splits_3d, torus=False)
    deg_avg, deg_min, deg_max = degree_stats(adj)
    stable_t, resolve_t, u, smax, non_single = _wl1_on_model(m, adj)
    rows.append(
        {
            "model": "bitsplit_3d_open",
            "micro_degree_avg": round(deg_avg, 3),
            "micro_degree_min": deg_min,
            "micro_degree_max": deg_max,
            "stable_t": stable_t,
            "resolve_t": "" if resolve_t is None else float(resolve_t),
            "unresolved_micro_final": u,
            "max_micro_class_size_final": smax,
            "non_single_micro_classes_final": non_single,
        }
    )

    adj = bitsplit_neighbors(n=1 << m, splits=splits_3d, torus=True)
    deg_avg, deg_min, deg_max = degree_stats(adj)
    stable_t, resolve_t, u, smax, non_single = _wl1_on_model(m, adj)
    rows.append(
        {
            "model": "bitsplit_3d_torus",
            "micro_degree_avg": round(deg_avg, 3),
            "micro_degree_min": deg_min,
            "micro_degree_max": deg_max,
            "stable_t": stable_t,
            "resolve_t": "" if resolve_t is None else float(resolve_t),
            "unresolved_micro_final": u,
            "max_micro_class_size_final": smax,
            "non_single_micro_classes_final": non_single,
        }
    )

    splits_2d = [3, 3]
    adj = bitsplit_neighbors(n=1 << m, splits=splits_2d, torus=False)
    deg_avg, deg_min, deg_max = degree_stats(adj)
    stable_t, resolve_t, u, smax, non_single = _wl1_on_model(m, adj)
    rows.append(
        {
            "model": "bitsplit_2d_open",
            "micro_degree_avg": round(deg_avg, 3),
            "micro_degree_min": deg_min,
            "micro_degree_max": deg_max,
            "stable_t": stable_t,
            "resolve_t": "" if resolve_t is None else float(resolve_t),
            "unresolved_micro_final": u,
            "max_micro_class_size_final": smax,
            "non_single_micro_classes_final": non_single,
        }
    )

    # hilbert 3d: 4x4x4 => power=2 ndim=3
    emb3 = hilbert_embedding(power=2, ndim=3)
    adj = hilbert_neighbors(emb3, torus=False)
    deg_avg, deg_min, deg_max = degree_stats(adj)
    stable_t, resolve_t, u, smax, non_single = _wl1_on_model(m, adj)
    rows.append(
        {
            "model": "hilbert_3d_open",
            "micro_degree_avg": round(deg_avg, 3),
            "micro_degree_min": deg_min,
            "micro_degree_max": deg_max,
            "stable_t": stable_t,
            "resolve_t": "" if resolve_t is None else float(resolve_t),
            "unresolved_micro_final": u,
            "max_micro_class_size_final": smax,
            "non_single_micro_classes_final": non_single,
        }
    )

    adj = bitsplit_neighbors(n=1 << m, splits=splits_2d, torus=True)
    deg_avg, deg_min, deg_max = degree_stats(adj)
    stable_t, resolve_t, u, smax, non_single = _wl1_on_model(m, adj)
    rows.append(
        {
            "model": "bitsplit_2d_torus",
            "micro_degree_avg": round(deg_avg, 3),
            "micro_degree_min": deg_min,
            "micro_degree_max": deg_max,
            "stable_t": stable_t,
            "resolve_t": "" if resolve_t is None else float(resolve_t),
            "unresolved_micro_final": u,
            "max_micro_class_size_final": smax,
            "non_single_micro_classes_final": non_single,
        }
    )

    # hilbert 2d: 8x8 => power=3 ndim=2
    emb2 = hilbert_embedding(power=3, ndim=2)
    adj = hilbert_neighbors(emb2, torus=False)
    deg_avg, deg_min, deg_max = degree_stats(adj)
    stable_t, resolve_t, u, smax, non_single = _wl1_on_model(m, adj)
    rows.append(
        {
            "model": "hilbert_2d_open",
            "micro_degree_avg": round(deg_avg, 3),
            "micro_degree_min": deg_min,
            "micro_degree_max": deg_max,
            "stable_t": stable_t,
            "resolve_t": "" if resolve_t is None else float(resolve_t),
            "unresolved_micro_final": u,
            "max_micro_class_size_final": smax,
            "non_single_micro_classes_final": non_single,
        }
    )

    adj = hypercube_neighbors(n=1 << m, m=m)
    deg_avg, deg_min, deg_max = degree_stats(adj)
    stable_t, resolve_t, u, smax, non_single = _wl1_on_model(m, adj)
    rows.append(
        {
            "model": "hypercube",
            "micro_degree_avg": round(deg_avg, 3),
            "micro_degree_min": deg_min,
            "micro_degree_max": deg_max,
            "stable_t": stable_t,
            "resolve_t": "" if resolve_t is None else float(resolve_t),
            "unresolved_micro_final": u,
            "max_micro_class_size_final": smax,
            "non_single_micro_classes_final": non_single,
        }
    )

    out_csv = run.run_dir / out_csv_name
    out2 = run.run_dir / out_h2
    out3 = run.run_dir / out_h3
    _write_csv(out_csv, rows)
    _plot_hilbert2d(out2, coords=[(int(x), int(y)) for (x, y) in emb2.coords], L=8)
    _plot_hilbert3d_layers(out3, coords=[(int(x), int(y), int(z)) for (x, y, z) in emb3.coords], L=4)

    manifest = build_base_manifest("m6_models_compare", run.run_id, params, script_path)
    manifest = add_output_hashes(manifest, run.run_dir, [out_csv_name, out_h2, out_h3])
    write_manifest(run.run_dir, manifest)

    for nm in [out_csv_name, out_h2, out_h3]:
        copy_atomic(run.run_dir / nm, export_dir() / nm)
    print("[exp_m6_models_compare] done", flush=True)


if __name__ == "__main__":
    main()

