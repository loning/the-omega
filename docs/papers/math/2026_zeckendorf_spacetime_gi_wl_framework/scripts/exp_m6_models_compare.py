#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""m=6 micro-geometry comparison table (Zeckendorf-only)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Dict, List, Tuple

from common_paths import export_dir, generated_dir
from common_zeckendorf import build_fold_domain, fold_f_m, tail_shift_word, tail_word_of_N
from micro_models import bitsplit_neighbors, hilbert_neighbors, hypercube_neighbors
from wl1 import micro_partition_stats, wl1_refine


def _add_undirected(adj: List[List[int]], a: int, b: int) -> None:
    if b not in adj[a]:
        adj[a].append(b)
    if a not in adj[b]:
        adj[b].append(a)


def build_zeckendorf_graph(m: int, micro_adj: List[List[int]]) -> Tuple[List[List[int]], List[int], range, Dict[int, int]]:
    domain = build_fold_domain(m)
    n_micro = domain.n_micro
    n_macro = len(domain.macro_words)
    n_tail = len(domain.tail_words)
    micro_off = 0
    macro_off = micro_off + n_micro
    tail_off = macro_off + n_macro
    n_total = tail_off + n_tail

    adj = [[] for _ in range(n_total)]

    # micro edges
    for x in range(n_micro):
        for y in micro_adj[x]:
            _add_undirected(adj, micro_off + x, micro_off + y)

    # fold + tail pointer edges
    fiber_sizes: Dict[int, int] = {w: 0 for w in domain.macro_words}
    for x in range(n_micro):
        w = fold_f_m(x, m)
        fiber_sizes[w] += 1
        _add_undirected(adj, micro_off + x, macro_off + domain.macro_index[w])
        if n_tail > 0:
            t = tail_word_of_N(x, m)
            _add_undirected(adj, micro_off + x, tail_off + domain.tail_index[t])

    # tail time edges
    if n_tail > 0:
        for t in domain.tail_words:
            t2 = tail_shift_word(t)
            _add_undirected(adj, tail_off + domain.tail_index[t], tail_off + domain.tail_index[t2])

    # colors: micro 0; tail 1; macro unique 2+
    colors = [0] * n_total
    if n_tail > 0:
        for i in range(n_tail):
            colors[tail_off + i] = 1
    for i in range(n_macro):
        colors[macro_off + i] = 2 + i

    micro_nodes = range(micro_off, micro_off + n_micro)
    return adj, colors, micro_nodes, fiber_sizes


def degree_stats(adj: List[List[int]]) -> Tuple[float, int, int]:
    degs = [len(x) for x in adj]
    return (sum(degs) / len(degs), min(degs), max(degs))


@dataclass(frozen=True)
class Row:
    model: str
    avg_deg: float
    min_deg: int
    max_deg: int
    stable_t: int
    resolve_t: int
    unresolved: int
    max_cls: int
    max_fiber: int
    avg_fiber: float


def main() -> None:
    m = 6
    domain = build_fold_domain(m)

    models: List[Tuple[str, List[List[int]]]] = []
    models.append(("hypercube", hypercube_neighbors(m)))
    models.append(("bitsplit_d2_open", bitsplit_neighbors(m=m, d=2, torus=False)))
    models.append(("bitsplit_d3_open", bitsplit_neighbors(m=m, d=3, torus=False)))
    # 2D Hilbert: power=3, ndim=2 => 2^(3*2)=64
    models.append(("hilbert_2d_open", hilbert_neighbors(power=3, ndim=2, torus=False)))
    # 3D Hilbert: power=2, ndim=3 => 2^(2*3)=64
    models.append(("hilbert_3d_open", hilbert_neighbors(power=2, ndim=3, torus=False)))

    rows: List[Row] = []
    for name, micro_adj in models:
        if len(micro_adj) != (1 << m):
            raise ValueError(f"model {name} has wrong size: {len(micro_adj)}")
        print(f"[m6_compare] model={name}", flush=True)

        adj, colors, micro_nodes, fiber_sizes = build_zeckendorf_graph(m, micro_adj)
        stats = wl1_refine(len(adj), lambda v: adj[v], colors, micro_nodes=micro_nodes, progress_every=20)
        pstats = micro_partition_stats(stats.colors, micro_nodes)

        avg_deg, min_deg, max_deg = degree_stats(micro_adj)
        max_fiber = max(fiber_sizes.values()) if fiber_sizes else 0
        avg_fiber = float(sum(fiber_sizes.values()) / len(fiber_sizes)) if fiber_sizes else 0.0

        rows.append(
            Row(
                model=name,
                avg_deg=avg_deg,
                min_deg=min_deg,
                max_deg=max_deg,
                stable_t=stats.stable_t,
                resolve_t=stats.resolve_t or 0,
                unresolved=pstats.unresolved_micro_final,
                max_cls=pstats.max_micro_class_size_final,
                max_fiber=max_fiber,
                avg_fiber=avg_fiber,
            )
        )

    # CSV export
    out_csv = export_dir() / "m6_models_compare.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "model",
                "avg_deg",
                "min_deg",
                "max_deg",
                "stable_t",
                "resolve_t",
                "unresolved_micro_final",
                "max_micro_class_size_final",
                "max_fiber_size",
                "avg_fiber_size",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.model,
                    f"{r.avg_deg:.3f}",
                    r.min_deg,
                    r.max_deg,
                    r.stable_t,
                    r.resolve_t,
                    r.unresolved,
                    r.max_cls,
                    r.max_fiber,
                    f"{r.avg_fiber:.3f}",
                ]
            )
    print(f"[m6_compare] wrote {out_csv}", flush=True)

    # LaTeX table fragment
    tex_lines: List[str] = []
    tex_lines.append("\\begin{table}[H]")
    tex_lines.append("\\centering")
    tex_lines.append("\\caption{$m=6$ 的微观几何邻接对照（Zeckendorf，\\WL{}-1，含时间结构）。}")
    tex_lines.append("\\label{tab:m6_models_compare}")
    tex_lines.append("\\begin{tabular}{lrrr|rr|rr|rr}")
    tex_lines.append("\\toprule")
    tex_lines.append(
        "model & avg\\_deg & min\\_deg & max\\_deg & stable\\_t & resolve\\_t & unresolved & max\\_cls & max\\_fiber & avg\\_fiber\\\\"
    )
    tex_lines.append("\\midrule")
    for r in rows:
        tex_lines.append(
            f"{r.model.replace('_','\\_')} & {r.avg_deg:.3f} & {r.min_deg} & {r.max_deg} & {r.stable_t} & {r.resolve_t} & {r.unresolved} & {r.max_cls} & {r.max_fiber} & {r.avg_fiber:.3f}\\\\"
        )
    tex_lines.append("\\bottomrule")
    tex_lines.append("\\end{tabular}")
    tex_lines.append("\\end{table}")

    out_tex = generated_dir() / "tab_m6_models_compare.tex"
    out_tex.parent.mkdir(parents=True, exist_ok=True)
    out_tex.write_text("\n".join(tex_lines) + "\n", encoding="utf-8")
    print(f"[m6_compare] wrote {out_tex}", flush=True)
    print("[m6_compare] OK", flush=True)


if __name__ == "__main__":
    main()

