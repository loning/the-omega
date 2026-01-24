#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Observer-centric cost scan: fixed Hilbert geometry vs adaptive switching.

We reuse the closure-graph + WL1 refinement machinery from:
  docs/papers/math/2026_fold_backtrack_closure_gi_wl_zeckendorf_trunc_time/scripts/

Interpretation (paper-local):
  - Ontic constraint: closure graph (micro geometry edges + fold edges).
  - Observer algorithm: deterministic WL1 refinement (color refinement).
  - Observer time: resolve_t (iterations until micro nodes are uniquely colored).
  - Hilbert measure: choice of micro geometry (1D/2D/3D Hilbert-lattice neighbors),
    and an adaptive schedule that switches geometry when refinement stabilizes.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_hash import sha256_file
from common_paths import export_dir, generated_dir, paper_root
from common_tex_pylatex import write_lines_as_fragment, write_tabular_fragment


def _import_external_closure_tooling() -> Tuple[object, object, object]:
    """Import closure_graph/micro_models/wl1 from the fold_backtrack_closure paper.

    We load these modules from the other paper's scripts directory to avoid code
    duplication, and include their file hashes in our experiment fingerprint.
    """

    import sys

    this_root = Path(__file__).resolve().parents[1]
    math_root = this_root.parent
    ext_scripts = math_root / "2026_fold_backtrack_closure_gi_wl_zeckendorf_trunc_time" / "scripts"
    if not ext_scripts.is_dir():
        raise RuntimeError(f"Missing external scripts dir: {ext_scripts}")

    # Ensure the external paper's local modules (common_zeckendorf, etc.) resolve.
    if str(ext_scripts) not in sys.path:
        sys.path.insert(0, str(ext_scripts))

    import closure_graph  # type: ignore
    import micro_models  # type: ignore
    import wl1  # type: ignore

    return closure_graph, micro_models, wl1


@dataclass(frozen=True)
class FixedResult:
    m: int
    geom: str
    avg_deg: float
    min_deg: int
    max_deg: int
    stable_t: int
    resolve_t: Optional[int]
    unresolved_micro_final: int
    max_micro_class_size_final: int


def _is_micro_resolved(colors: List[int], micro_nodes: range) -> bool:
    seen = set()
    for v in micro_nodes:
        c = colors[v]
        if c in seen:
            return False
        seen.add(c)
    return True


def _hilbert_adj(micro_models: object, m: int, d: int, torus: bool) -> Optional[List[List[int]]]:
    # Need n = 2^m = 2^(power*d) => power = m/d must be integer.
    if m % d != 0:
        return None
    power = m // d
    emb = micro_models.hilbert_embedding(power=power, ndim=d)  # type: ignore[attr-defined]
    adj = micro_models.hilbert_neighbors(emb, torus=torus)  # type: ignore[attr-defined]
    return adj


def _run_wl1_once(
    wl1: object,
    clo: object,
    init_colors: List[int],
    max_iter: int,
    progress_every: int,
) -> object:
    return wl1.wl1_refine(  # type: ignore[attr-defined]
        n_nodes=clo.n_total,
        neighbors=clo.neighbors,
        init_colors=init_colors,
        micro_nodes=clo.micro_range,
        max_iter=max_iter,
        progress_every=progress_every,
    )


def _analyze_fixed(
    closure_graph: object,
    micro_models: object,
    wl1: object,
    m: int,
    d: int,
    torus: bool,
    max_iter: int,
    progress_every: int,
) -> FixedResult:
    n = 1 << m
    adj = _hilbert_adj(micro_models, m=m, d=d, torus=torus)
    if adj is None:
        raise ValueError("invalid hilbert params")

    avg_deg, min_deg, max_deg = micro_models.degree_stats(adj)  # type: ignore[attr-defined]
    clo = closure_graph.build_closure_graph(m=m, micro_adj=adj)  # type: ignore[attr-defined]

    init = [0] * clo.n_total
    for v in clo.macro_range:
        init[v] = 1

    stats = _run_wl1_once(wl1, clo=clo, init_colors=init, max_iter=max_iter, progress_every=progress_every)
    pstats = wl1.micro_partition_stats(stats.colors, clo.micro_range)  # type: ignore[attr-defined]
    return FixedResult(
        m=m,
        geom=f"hilbert{d}d",
        avg_deg=float(avg_deg),
        min_deg=int(min_deg),
        max_deg=int(max_deg),
        stable_t=int(stats.stable_t),
        resolve_t=None if stats.resolve_t is None else int(stats.resolve_t),
        unresolved_micro_final=int(pstats.unresolved_micro_final),
        max_micro_class_size_final=int(pstats.max_micro_class_size_final),
    )


def _analyze_adaptive(
    closure_graph: object,
    micro_models: object,
    wl1: object,
    m: int,
    schedule: Sequence[int],
    torus: bool,
    stage_max_iter: int,
    stage_progress_every: int,
    max_stages: int,
) -> FixedResult:
    # Start from the canonical init partition.
    n = 1 << m

    # Build the first graph to size init_colors.
    first_adj = _hilbert_adj(micro_models, m=m, d=schedule[0], torus=torus)
    if first_adj is None:
        raise ValueError("invalid schedule[0] for this m")
    clo0 = closure_graph.build_closure_graph(m=m, micro_adj=first_adj)  # type: ignore[attr-defined]

    colors = [0] * clo0.n_total
    for v in clo0.macro_range:
        colors[v] = 1

    total_updates = 0
    resolved_at: Optional[int] = 0 if _is_micro_resolved(colors, clo0.micro_range) else None

    last_pstats = wl1.micro_partition_stats(colors, clo0.micro_range)  # type: ignore[attr-defined]
    last_deg = micro_models.degree_stats(first_adj)  # type: ignore[attr-defined]

    for stage in range(max_stages):
        if resolved_at is not None:
            break

        d = int(schedule[stage % len(schedule)])
        adj = _hilbert_adj(micro_models, m=m, d=d, torus=torus)
        if adj is None:
            continue

        avg_deg, min_deg, max_deg = micro_models.degree_stats(adj)  # type: ignore[attr-defined]
        clo = closure_graph.build_closure_graph(m=m, micro_adj=adj)  # type: ignore[attr-defined]

        if clo.n_total != len(colors):
            raise RuntimeError("unexpected node count change")

        stats = _run_wl1_once(wl1, clo=clo, init_colors=colors, max_iter=stage_max_iter, progress_every=stage_progress_every)

        # Account updates (stable_t is number of effective refinement updates in this call).
        total_updates += int(stats.stable_t)
        colors = list(stats.colors)

        if stats.resolve_t is not None:
            resolved_at = total_updates - int(stats.stable_t) + int(stats.resolve_t)
        elif _is_micro_resolved(colors, clo.micro_range):
            resolved_at = total_updates

        last_pstats = wl1.micro_partition_stats(colors, clo.micro_range)  # type: ignore[attr-defined]
        last_deg = (avg_deg, min_deg, max_deg)

        # If a stage did nothing (stable_t == 0), switching geometry is the only way forward.
        # The loop continues until max_stages.

    avg_deg, min_deg, max_deg = last_deg
    return FixedResult(
        m=m,
        geom="adaptive_cycle",
        avg_deg=float(avg_deg),
        min_deg=int(min_deg),
        max_deg=int(max_deg),
        stable_t=int(total_updates),
        resolve_t=None if resolved_at is None else int(resolved_at),
        unresolved_micro_final=int(last_pstats.unresolved_micro_final),
        max_micro_class_size_final=int(last_pstats.max_micro_class_size_final),
    )


def _analyze_adaptive_greedy(
    closure_graph: object,
    micro_models: object,
    wl1: object,
    m: int,
    candidates: Sequence[int],
    torus: bool,
    stage_max_iter: int,
    probe_iter: int,
    max_stages: int,
) -> FixedResult:
    """Greedy adaptive observer.

    At each stage, try each candidate geometry for `probe_iter` refinement steps
    and pick the one that yields the best immediate improvement (deterministic
    tie-break). Then commit to that geometry for up to `stage_max_iter` steps.
    """

    first_d = int(sorted(candidates)[0])
    first_adj = _hilbert_adj(micro_models, m=m, d=first_d, torus=torus)
    if first_adj is None:
        raise ValueError("invalid candidates for this m")
    clo0 = closure_graph.build_closure_graph(m=m, micro_adj=first_adj)  # type: ignore[attr-defined]

    colors = [0] * clo0.n_total
    for v in clo0.macro_range:
        colors[v] = 1

    total_updates = 0
    resolved_at: Optional[int] = 0 if _is_micro_resolved(colors, clo0.micro_range) else None

    last_pstats = wl1.micro_partition_stats(colors, clo0.micro_range)  # type: ignore[attr-defined]
    last_deg = micro_models.degree_stats(first_adj)  # type: ignore[attr-defined]

    cand = sorted(int(d) for d in candidates)
    for _stage in range(int(max_stages)):
        if resolved_at is not None:
            break

        # Greedy selection by short probe.
        best_d: Optional[int] = None
        best_key: Optional[Tuple[int, int, int]] = None
        best_probe_colors: Optional[List[int]] = None
        best_probe_deg: Optional[Tuple[float, int, int]] = None

        for d in cand:
            adj = _hilbert_adj(micro_models, m=m, d=d, torus=torus)
            if adj is None:
                continue
            clo = closure_graph.build_closure_graph(m=m, micro_adj=adj)  # type: ignore[attr-defined]
            stats_probe = _run_wl1_once(
                wl1,
                clo=clo,
                init_colors=colors,
                max_iter=int(max(1, probe_iter)),
                progress_every=0,
            )
            pstats_probe = wl1.micro_partition_stats(stats_probe.colors, clo.micro_range)  # type: ignore[attr-defined]

            # Key: prefer resolved; then smaller unresolved; then smaller max class; deterministic by d.
            resolved_flag = 0 if (_is_micro_resolved(list(stats_probe.colors), clo.micro_range) or stats_probe.resolve_t is not None) else 1
            key = (resolved_flag, int(pstats_probe.unresolved_micro_final), int(pstats_probe.max_micro_class_size_final))
            if best_key is None or key < best_key:
                best_key = key
                best_d = d
                best_probe_colors = list(stats_probe.colors)
                best_probe_deg = micro_models.degree_stats(adj)  # type: ignore[attr-defined]

        if best_d is None or best_probe_colors is None or best_probe_deg is None:
            break

        # Commit on chosen geometry for stage_max_iter steps, starting from current colors.
        adj = _hilbert_adj(micro_models, m=m, d=best_d, torus=torus)
        if adj is None:
            break
        clo = closure_graph.build_closure_graph(m=m, micro_adj=adj)  # type: ignore[attr-defined]
        stats = _run_wl1_once(
            wl1,
            clo=clo,
            init_colors=colors,
            max_iter=int(stage_max_iter),
            progress_every=0,
        )
        total_updates += int(stats.stable_t)
        colors = list(stats.colors)

        if stats.resolve_t is not None:
            resolved_at = total_updates - int(stats.stable_t) + int(stats.resolve_t)
        elif _is_micro_resolved(colors, clo.micro_range):
            resolved_at = total_updates

        last_pstats = wl1.micro_partition_stats(colors, clo.micro_range)  # type: ignore[attr-defined]
        last_deg = micro_models.degree_stats(adj)  # type: ignore[attr-defined]

    avg_deg, min_deg, max_deg = last_deg
    return FixedResult(
        m=m,
        geom="adaptive_greedy",
        avg_deg=float(avg_deg),
        min_deg=int(min_deg),
        max_deg=int(max_deg),
        stable_t=int(total_updates),
        resolve_t=None if resolved_at is None else int(resolved_at),
        unresolved_micro_final=int(last_pstats.unresolved_micro_final),
        max_micro_class_size_final=int(last_pstats.max_micro_class_size_final),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", type=str, default="6,9,12,15")
    ap.add_argument("--torus", action="store_true")
    ap.add_argument("--max_iter", type=int, default=120)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--stage_max_iter", type=int, default=30)
    ap.add_argument("--greedy_probe_iter", type=int, default=6)
    ap.add_argument("--max_stages", type=int, default=12)
    args = ap.parse_args()

    ms = [int(x.strip()) for x in args.ms.split(",") if x.strip()]
    if not ms:
        raise SystemExit("No m provided")

    closure_graph, micro_models, wl1 = _import_external_closure_tooling()

    # Fingerprint external dependencies so cache invalidates if they change.
    ext_dir = Path(closure_graph.__file__).resolve().parent  # type: ignore[attr-defined]
    ext_files = ["closure_graph.py", "micro_models.py", "wl1.py", "common_zeckendorf.py"]
    extra = {nm: sha256_file(ext_dir / nm) for nm in ext_files if (ext_dir / nm).is_file()}

    out_tab = "tab_observer_hilbert_compare.tex"
    out_sum = "observer_hilbert_summary.tex"
    out_csv = "observer_hilbert_compare.csv"
    out_png_resolve = "observer_resolve_t_vs_dimension.png"
    out_fig_resolve = "fig_observer_resolve_t_vs_dimension.tex"

    script_path = Path(__file__).resolve()
    params = {
        "ms": ms,
        "torus": bool(args.torus),
        "max_iter": int(args.max_iter),
        "stage_max_iter": int(args.stage_max_iter),
        "greedy_probe_iter": int(args.greedy_probe_iter),
        "max_stages": int(args.max_stages),
        "schedule": [1, 2, 3],
    }

    run = prepare_run(
        experiment="observer_hilbert_cost_scan",
        params=params,
        script_path=script_path,
        required_files=[out_tab, out_sum, out_csv, out_png_resolve, out_fig_resolve],
        force=bool(args.force),
        extra_fingerprint={"external": extra},
    )

    if run.cached:
        print(f"[exp_observer_hilbert_cost_scan] cached: {run.run_dir.name}", flush=True)
        copy_atomic(run.run_dir / out_tab, generated_dir() / out_tab)
        copy_atomic(run.run_dir / out_sum, generated_dir() / out_sum)
        copy_atomic(run.run_dir / out_fig_resolve, generated_dir() / out_fig_resolve)
        copy_atomic(run.run_dir / out_csv, export_dir() / out_csv)
        copy_atomic(run.run_dir / out_png_resolve, export_dir() / out_png_resolve)
        return

    rows: List[FixedResult] = []
    for m in ms:
        print(f"[exp_observer_hilbert_cost_scan] m={m}", flush=True)
        for d in (1, 2, 3):
            if m % d != 0:
                continue
            r = _analyze_fixed(
                closure_graph=closure_graph,
                micro_models=micro_models,
                wl1=wl1,
                m=m,
                d=d,
                torus=bool(args.torus),
                max_iter=int(args.max_iter),
                progress_every=2 if m >= 12 else 1,
            )
            rows.append(r)

        # Adaptive observer: cycle through available d in [1,2,3] (skipping incompatible d).
        avail = [d for d in (1, 2, 3) if (m % d == 0)]
        if avail:
            r_ad = _analyze_adaptive(
                closure_graph=closure_graph,
                micro_models=micro_models,
                wl1=wl1,
                m=m,
                schedule=avail,
                torus=bool(args.torus),
                stage_max_iter=int(args.stage_max_iter),
                stage_progress_every=2 if m >= 12 else 1,
                max_stages=int(args.max_stages),
            )
            rows.append(r_ad)
            r_greedy = _analyze_adaptive_greedy(
                closure_graph=closure_graph,
                micro_models=micro_models,
                wl1=wl1,
                m=m,
                candidates=avail,
                torus=bool(args.torus),
                stage_max_iter=int(args.stage_max_iter),
                probe_iter=int(args.greedy_probe_iter),
                max_stages=int(args.max_stages),
            )
            rows.append(r_greedy)

    # Plot resolve_t vs dimension for each m (fixed geometries only).
    series: Dict[int, List[Tuple[int, Optional[int]]]] = {}
    for r in rows:
        if not r.geom.startswith("hilbert"):
            continue
        d = int(r.geom.replace("hilbert", "").replace("d", ""))
        series.setdefault(r.m, []).append((d, r.resolve_t))
    for m, pts in series.items():
        pts.sort(key=lambda x: x[0])

    out_png_path = run.run_dir / out_png_resolve
    out_png_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(7.2, 3.4))
    for m, pts in sorted(series.items()):
        xs = [d for d, _ in pts]
        ys = [float(v) if v is not None else float("nan") for _, v in pts]
        plt.plot(xs, ys, marker="o", linewidth=1.6, label=f"m={m}")
    plt.xlabel("d (Hilbert dimension)")
    plt.ylabel("resolve_t (WL1)")
    plt.title("Observer resolve_t vs Hilbert dimension (fixed geometry)")
    plt.grid(True, alpha=0.3)
    plt.legend(ncol=2, fontsize=9)
    plt.tight_layout()
    plt.savefig(out_png_path, dpi=170)
    plt.close()

    out_fig_path = run.run_dir / out_fig_resolve
    write_lines_as_fragment(
        out_fig_path,
        [
            r"\begin{figure}[H]",
            r"\centering",
            rf"\includegraphics[width=0.85\linewidth]{{artifacts/export/{out_png_resolve}}}",
            r"\caption{固定几何下，观察者时间指标 resolve\_t 随 Hilbert 维度的变化。缺失点表示在给定最大迭代轮数内未解析。}",
            r"\label{fig:observer_resolve_vs_dim}",
            r"\end{figure}",
        ],
    )

    # Write a compact LaTeX table.
    header = [
        r"$m$",
        r"geometry",
        r"$\overline{\deg}$",
        r"$\deg_{\min}$",
        r"$\deg_{\max}$",
        r"stable\_t",
        r"resolve\_t",
        r"unresolved\_micro",
        r"max\_class",
    ]
    tex_rows: List[List[str]] = []
    for r in rows:
        geom_tex = r"\texttt{" + str(r.geom).replace("_", r"\_") + "}"
        tex_rows.append(
            [
                str(r.m),
                geom_tex,
                f"{r.avg_deg:.2f}",
                str(r.min_deg),
                str(r.max_deg),
                str(r.stable_t),
                "" if r.resolve_t is None else str(r.resolve_t),
                str(r.unresolved_micro_final),
                str(r.max_micro_class_size_final),
            ]
        )

    out_tab_path = run.run_dir / out_tab
    write_tabular_fragment(out_tab_path, column_spec="r l r r r r r r r", header=header, rows=tex_rows, booktabs=True)

    # Minimal summary fragment (paragraphs).
    best_by_m: Dict[int, FixedResult] = {}
    for r in rows:
        cur = best_by_m.get(r.m)
        if cur is None:
            best_by_m[r.m] = r
            continue
        # Prefer resolved; then smaller resolve_t; else smaller unresolved.
        def key(x: FixedResult) -> Tuple[int, int, int]:
            return (0 if x.resolve_t is not None else 1, x.resolve_t or 10**9, x.unresolved_micro_final)

        if key(r) < key(cur):
            best_by_m[r.m] = r

    lines: List[str] = []
    lines.append(r"\paragraph{摘要（自动生成）}")
    for m, r in sorted(best_by_m.items()):
        rt = "NA" if r.resolve_t is None else str(r.resolve_t)
        geom_tex = str(r.geom).replace("_", r"\_")
        lines.append(
            rf"对 $m={m}$，在本实验设置下最优几何为 \texttt{{{geom_tex}}}，其 resolve\_t={rt}，unresolved\_micro={r.unresolved_micro_final}。"
        )
    lines.append(r"\paragraph{说明}")
    lines.append(r"本节把 WL1 细化迭代次数（解析微观唯一着色所需步数）作为一个可审计的观察者时间指标；Hilbert 维度与切换策略仅改变微观几何边，从而改变约束传播形态。")

    out_sum_path = run.run_dir / out_sum
    write_lines_as_fragment(out_sum_path, lines)

    # Also write a stable CSV export for manual inspection.
    out_csv_path = run.run_dir / out_csv
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    import csv

    with out_csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "m",
                "geometry",
                "avg_deg",
                "min_deg",
                "max_deg",
                "stable_t",
                "resolve_t",
                "unresolved_micro_final",
                "max_micro_class_size_final",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.m,
                    r.geom,
                    f"{r.avg_deg:.6f}",
                    r.min_deg,
                    r.max_deg,
                    r.stable_t,
                    "" if r.resolve_t is None else r.resolve_t,
                    r.unresolved_micro_final,
                    r.max_micro_class_size_final,
                ]
            )

    manifest = build_base_manifest("observer_hilbert_cost_scan", run.run_id, params, script_path)
    manifest = add_output_hashes(manifest, run.run_dir, [out_tab, out_sum, out_csv, out_png_resolve, out_fig_resolve])
    write_manifest(run.run_dir, manifest)

    copy_atomic(out_tab_path, generated_dir() / out_tab)
    copy_atomic(out_sum_path, generated_dir() / out_sum)
    copy_atomic(out_fig_path, generated_dir() / out_fig_resolve)
    copy_atomic(out_csv_path, export_dir() / out_csv)
    copy_atomic(out_png_path, export_dir() / out_png_resolve)
    print("[exp_observer_hilbert_cost_scan] done", flush=True)


if __name__ == "__main__":
    main()

