#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAP display-dimension scan (WL1 closure graph).

Goal:
  Provide an auditable, deterministic proxy for "observer evolution time" as a
  function of display dimension d, using:
    - micro adjacency: bit-split lattice in d dimensions
    - fold edges: the truncation's space projection (default: paper's Fold_m)
    - observer algorithm: deterministic 1-WL (color refinement) on the closure graph

Outputs (LaTeX-consumed):
  - sections/generated/cap_display_dim_scan_table_<trunc>.tex
  - sections/generated/cap_display_dim_scan_summary_<trunc>.tex
  - sections/generated/fig_cap_display_resolve_vs_dim_<trunc>.tex
  - sections/generated/assets/cap_display_resolve_vs_dim_<trunc>.png
  - sections/generated/assets/cap_display_unresolved_vs_dim_<trunc>.png
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt

from closure_graph import build_closure_graph
from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import export_dir, generated_assets_dir, generated_dir
from common_pylatex import NoEscape, booktabs_tabular, figure_includegraphics, write_tex_fragment
from micro_models import bitsplit_neighbors, degree_stats
from wl1 import micro_partition_stats, wl1_refine
from truncations import available_truncations


@dataclass(frozen=True)
class Row:
    m: int
    d: int
    torus: bool
    avg_deg: float
    stable_t: int
    resolve_t: Optional[int]
    unresolved_micro_final: int
    max_micro_class_size_final: int


def _quantile(values: List[float], p: float) -> float:
    """
    Deterministic quantile for a finite list (linear interpolation, sorted).
    values must be non-empty.
    """
    if not values:
        raise ValueError("values must be non-empty")
    if p <= 0.0:
        return float(min(values))
    if p >= 1.0:
        return float(max(values))
    xs = sorted(float(x) for x in values)
    n = len(xs)
    # position in [0, n-1]
    pos = p * (n - 1)
    i = int(pos)
    j = min(i + 1, n - 1)
    w = pos - float(i)
    return (1.0 - w) * xs[i] + w * xs[j]


def _run_once(m: int, d: int, torus: bool, max_iter: int, truncation: str) -> Row:
    adj = bitsplit_neighbors(m=m, d=d, torus=torus)
    avg_deg, _min_deg, _max_deg = degree_stats(adj)
    clo = build_closure_graph(m=m, micro_adj=adj, truncation=truncation)

    init = [0] * clo.n_total
    # Macro nodes uniquely colored.
    for i, v in enumerate(clo.macro_range):
        init[v] = 1 + i

    stats = wl1_refine(
        n_nodes=clo.n_total,
        neighbors=clo.neighbors,
        init_colors=init,
        micro_nodes=clo.micro_range,
        max_iter=max_iter,
        progress_every_seconds=15.0,
    )
    pstats = micro_partition_stats(stats.colors, clo.micro_range)
    return Row(
        m=int(m),
        d=int(d),
        torus=bool(torus),
        avg_deg=float(avg_deg),
        stable_t=int(stats.stable_t),
        resolve_t=None if stats.resolve_t is None else int(stats.resolve_t),
        unresolved_micro_final=int(pstats.unresolved_micro_final),
        max_micro_class_size_final=int(pstats.max_micro_class_size_final),
    )


def _plot_series(
    series: Dict[int, List[Tuple[int, Optional[int]]]],
    out_png: Path,
    title: str,
    ylabel: str,
) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.6, 3.6))
    for m, pts in sorted(series.items()):
        pts.sort(key=lambda x: x[0])
        xs = [d for d, _ in pts]
        ys = [float(v) if v is not None else float("nan") for _, v in pts]
        plt.plot(xs, ys, marker="o", linewidth=1.6, label=f"m={m}")
    plt.xlabel("d (display dimension)")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend(ncol=2, fontsize=9)
    plt.tight_layout()
    plt.savefig(out_png, dpi=170)
    plt.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", type=str, default="6,9,12,15")
    ap.add_argument("--d-max", type=int, default=4)
    ap.add_argument("--torus", action="store_true")
    ap.add_argument("--max-iter", type=int, default=200)
    ap.add_argument("--q", type=float, default=0.95, help="Quantile level for CAP key aggregation over m.")
    ap.add_argument("--truncation", type=str, default="zeck_window", choices=list(available_truncations()))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    ms = [int(x.strip()) for x in args.ms.split(",") if x.strip()]
    d_max = int(args.d_max)
    torus = bool(args.torus)
    max_iter = int(args.max_iter)
    q = float(args.q)
    truncation = str(args.truncation)
    trunc_tex = truncation.replace("_", r"\_")

    suf = truncation
    out_tab = f"cap_display_dim_scan_table_{suf}.tex"
    out_sum = f"cap_display_dim_scan_summary_{suf}.tex"
    out_csv = f"cap_display_dim_scan_{suf}.csv"
    out_png_resolve = f"cap_display_resolve_vs_dim_{suf}.png"
    out_png_unresolved = f"cap_display_unresolved_vs_dim_{suf}.png"
    out_fig_resolve = f"fig_cap_display_resolve_vs_dim_{suf}.tex"
    out_fig_unresolved = f"fig_cap_display_unresolved_vs_dim_{suf}.tex"
    out_key_tab = f"cap_display_dim_key_table_{suf}.tex"

    script_path = Path(__file__).resolve()
    params = {"ms": ms, "d_max": d_max, "torus": torus, "max_iter": max_iter, "truncation": truncation}

    run = prepare_run(
        experiment="cap_display_dim_scan",
        params=params,
        script_path=script_path,
        required_files=[out_tab, out_sum, out_csv, out_png_resolve, out_png_unresolved, out_fig_resolve, out_fig_unresolved, out_key_tab],
        force=bool(args.force),
        extra_fingerprint={},
    )

    if run.cached:
        print(f"[exp_cap_display_dim_scan] cached: {run.run_dir.name}", flush=True)
        copy_atomic(run.run_dir / out_tab, generated_dir() / out_tab)
        copy_atomic(run.run_dir / out_sum, generated_dir() / out_sum)
        copy_atomic(run.run_dir / out_fig_resolve, generated_dir() / out_fig_resolve)
        copy_atomic(run.run_dir / out_fig_unresolved, generated_dir() / out_fig_unresolved)
        copy_atomic(run.run_dir / out_key_tab, generated_dir() / out_key_tab)
        copy_atomic(run.run_dir / out_csv, export_dir() / out_csv)
        copy_atomic(run.run_dir / out_png_resolve, generated_assets_dir() / out_png_resolve)
        copy_atomic(run.run_dir / out_png_unresolved, generated_assets_dir() / out_png_unresolved)
        return

    rows: List[Row] = []
    for m in ms:
        print(f"[exp_cap_display_dim_scan] truncation={truncation} m={m}", flush=True)
        for d in range(1, d_max + 1):
            if m % d != 0:
                # keep shapes balanced/power-of-two in each dimension
                continue
            r = _run_once(m=m, d=d, torus=torus, max_iter=max_iter, truncation=truncation)
            rows.append(r)

    # CSV export
    out_csv_path = run.run_dir / out_csv
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with out_csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["m", "d", "torus", "avg_deg", "stable_t", "resolve_t", "unresolved_micro_final", "max_micro_class_size_final"])
        for r in rows:
            w.writerow([r.m, r.d, int(r.torus), f"{r.avg_deg:.6f}", r.stable_t, "" if r.resolve_t is None else r.resolve_t, r.unresolved_micro_final, r.max_micro_class_size_final])

    # Plots (resolve_t and unresolved_micro_final)
    series_resolve: Dict[int, List[Tuple[int, Optional[int]]]] = {}
    series_unres: Dict[int, List[Tuple[int, Optional[int]]]] = {}
    for r in rows:
        series_resolve.setdefault(r.m, []).append((r.d, r.resolve_t))
        series_unres.setdefault(r.m, []).append((r.d, r.unresolved_micro_final))

    out_png_resolve_path = run.run_dir / out_png_resolve
    _plot_series(
        series_resolve,
        out_png=out_png_resolve_path,
        title="CAP display scan: resolve_t vs dimension (WL1 closure graph)",
        ylabel="resolve_t (WL1 iterations)",
    )

    out_png_unres_path = run.run_dir / out_png_unresolved
    # unresolved is always defined (int), but keep the same signature.
    series_unres2: Dict[int, List[Tuple[int, Optional[int]]]] = {m: [(d, int(v) if v is not None else None) for d, v in pts] for m, pts in series_unres.items()}
    _plot_series(
        series_unres2,
        out_png=out_png_unres_path,
        title="CAP display scan: unresolved_micro vs dimension (WL1 closure graph)",
        ylabel="unresolved_micro_final",
    )

    # LaTeX figure fragments.
    out_fig_resolve_path = run.run_dir / out_fig_resolve
    fig_resolve = figure_includegraphics(
        rel_graphics_path=f"sections/generated/assets/{out_png_resolve}",
        caption_tex=rf"显示维数扫描（\texttt{{{trunc_tex}}}）：基于闭包图的 WL1 解析时间（resolve\_t）随显示维数 $d$ 的变化。缺失点表示在给定迭代上限内未完全解析。",
        label=f"fig:cap_display_resolve_vs_dim_{truncation}",
        width_tex=r"0.90\linewidth",
        position="H",
    )
    write_tex_fragment(out_fig_resolve_path, fig_resolve, comment="Auto-generated by scripts/exp_cap_display_dim_scan.py")

    out_fig_unres_path = run.run_dir / out_fig_unresolved
    fig_unres = figure_includegraphics(
        rel_graphics_path=f"sections/generated/assets/{out_png_unresolved}",
        caption_tex=rf"显示维数扫描（\texttt{{{trunc_tex}}}）：稳定后仍未分解的微观点总数（unresolved\_micro\_final）随显示维数 $d$ 的变化。",
        label=f"fig:cap_display_unresolved_vs_dim_{truncation}",
        width_tex=r"0.90\linewidth",
        position="H",
    )
    write_tex_fragment(out_fig_unres_path, fig_unres, comment="Auto-generated by scripts/exp_cap_display_dim_scan.py")

    # Compact LaTeX table.
    out_tab_path = run.run_dir / out_tab
    tab = booktabs_tabular(
        col_spec="r r r r r r",
        header=[
            NoEscape(r"$m$"),
            NoEscape(r"$d$"),
            NoEscape(r"$\overline{\deg}$"),
            NoEscape(r"stable\_t"),
            NoEscape(r"resolve\_t"),
            NoEscape(r"unresolved\_micro"),
        ],
        rows=[
            [
                str(r.m),
                str(r.d),
                f"{r.avg_deg:.2f}",
                str(r.stable_t),
                "" if r.resolve_t is None else str(r.resolve_t),
                str(r.unresolved_micro_final),
            ]
            for r in sorted(rows, key=lambda x: (x.m, x.d))
        ],
    )
    write_tex_fragment(out_tab_path, tab, comment="Auto-generated by scripts/exp_cap_display_dim_scan.py")

    # Summary fragment.
    out_sum_path = run.run_dir / out_sum
    sum_lines: List[str] = []
    sum_lines.append(r"\paragraph{显示维数扫描摘要（自动生成）}")
    sum_lines.append(
        r"\AuditTag 本片段由 \texttt{scripts/exp\_cap\_display\_dim\_scan.py} 生成。截断族为 "
        + rf"\texttt{{{trunc_tex}}}"
        + r"。闭包图由微观显示邻接与折叠边（空间投影）组成，观察者算法为确定性 $1\text{-}\mathrm{WL}$ 颜色细化；指标 stable\_t 与 resolve\_t 的定义见正文。"
    )
    # Best d per m (prefer resolved; then smaller resolve_t; then smaller d).
    best: Dict[int, Row] = {}
    for r in rows:
        cur = best.get(r.m)
        if cur is None:
            best[r.m] = r
            continue
        def key(x: Row) -> Tuple[int, int, int]:
            return (0 if x.resolve_t is not None else 1, x.resolve_t or 10**9, x.d)
        if key(r) < key(cur):
            best[r.m] = r
    for m in sorted(best.keys()):
        r = best[m]
        rt = "NA" if r.resolve_t is None else str(r.resolve_t)
        sum_lines.append(rf"对 $m={m}$，本扫描下的最优维数为 $d={r.d}$，resolve\_t={rt}，unresolved\_micro={r.unresolved_micro_final}。")
    write_tex_fragment(
        out_sum_path,
        "\n".join(sum_lines) + "\n",
        comment="Auto-generated by scripts/exp_cap_display_dim_scan.py",
    )

    # CAP key table aggregated over m (by dimension).
    # Treat unresolved resolve_t as +inf in aggregation.
    key_rows: List[List[str]] = []
    for d in sorted({r.d for r in rows}):
        rs = [r for r in rows if r.d == d]
        if not rs:
            continue
        resolves = [float("inf") if r.resolve_t is None else float(r.resolve_t) for r in rs]
        stables = [float(r.stable_t) for r in rs]
        unresolved = sum(1 for r in rs if r.resolve_t is None)
        k2 = _quantile(resolves, p=q)
        k3 = _quantile(stables, p=q)
        # Present inf as NA.
        k2s = "NA" if k2 == float("inf") else f"{k2:.2f}"
        key_rows.append([str(d), str(len(rs)), str(unresolved), k2s, f"{k3:.2f}", f"{sum(stables)/float(len(stables)):.2f}"])

    key_tab = booktabs_tabular(
        col_spec="r r r r r r",
        header=[
            NoEscape(r"$d$"),
            NoEscape(r"$|\mathcal M_d|$"),
            NoEscape(r"unresolved"),
            NoEscape(rf"$\mathrm{{Q}}_{{{q:.2f}}}(t_{{\mathrm{{resolve}}}})$"),
            NoEscape(rf"$\mathrm{{Q}}_{{{q:.2f}}}(t_{{\mathrm{{stable}}}})$"),
            NoEscape(r"$\mathrm{mean}(t_{\mathrm{stable}})$"),
        ],
        rows=[[NoEscape(x) if x.startswith("$") else x for x in row] for row in key_rows],
    )
    out_key_tab_path = run.run_dir / out_key_tab
    write_tex_fragment(out_key_tab_path, key_tab, comment="Auto-generated by scripts/exp_cap_display_dim_scan.py")

    # Manifest + copy outputs into paper locations.
    manifest = build_base_manifest("cap_display_dim_scan", run.run_id, params, script_path)
    manifest = add_output_hashes(
        manifest,
        run.run_dir,
        [out_tab, out_sum, out_csv, out_png_resolve, out_png_unresolved, out_fig_resolve, out_fig_unresolved, out_key_tab],
    )
    write_manifest(run.run_dir, manifest)

    copy_atomic(out_tab_path, generated_dir() / out_tab)
    copy_atomic(out_sum_path, generated_dir() / out_sum)
    copy_atomic(out_fig_resolve_path, generated_dir() / out_fig_resolve)
    copy_atomic(out_fig_unres_path, generated_dir() / out_fig_unresolved)
    copy_atomic(out_key_tab_path, generated_dir() / out_key_tab)
    copy_atomic(out_csv_path, export_dir() / out_csv)
    copy_atomic(out_png_resolve_path, generated_assets_dir() / out_png_resolve)
    copy_atomic(out_png_unres_path, generated_assets_dir() / out_png_unresolved)

    print("[exp_cap_display_dim_scan] done", flush=True)


if __name__ == "__main__":
    main()

