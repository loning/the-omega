#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zeckendorf-only scan under unified WL-1 metrics."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Dict, List, Tuple

from common_paths import export_dir
from common_zeckendorf import (
    FoldDomain,
    build_fold_domain,
    fold_f_m,
    tail_shift_word,
    tail_word_of_N,
)
from micro_models import hypercube_neighbors
from wl1 import micro_partition_stats, wl1_refine


@dataclass(frozen=True)
class WLRow:
    m: int
    n_micro: int
    n_total: int
    stable_t: int
    resolve_t: int
    unresolved_micro_final: int
    max_micro_class_size_final: int
    max_fiber_size: int
    avg_fiber_size: float


def _make_adj(n: int) -> List[List[int]]:
    return [[] for _ in range(n)]


def _add_undirected(adj: List[List[int]], a: int, b: int) -> None:
    if b not in adj[a]:
        adj[a].append(b)
    if a not in adj[b]:
        adj[b].append(a)


def build_graph_zeckendorf(domain: FoldDomain, include_time: bool = True) -> Tuple[List[List[int]], List[int], range, Dict[int, int]]:
    m = domain.m
    n_micro = domain.n_micro
    n_macro = len(domain.macro_words)
    n_tail = len(domain.tail_words)
    micro_off = 0
    macro_off = micro_off + n_micro
    tail_off = macro_off + n_macro
    n_total = tail_off + n_tail

    adj = _make_adj(n_total)

    # Micro adjacency: hypercube
    micro_nb = hypercube_neighbors(m)
    for x in range(n_micro):
        for y in micro_nb[x]:
            _add_undirected(adj, micro_off + x, micro_off + y)

    # Fold edges + tail pointer edges
    fiber_sizes: Dict[int, int] = {w: 0 for w in domain.macro_words}
    for x in range(n_micro):
        w = fold_f_m(x, m)
        fiber_sizes[w] += 1
        _add_undirected(adj, micro_off + x, macro_off + domain.macro_index[w])

        if include_time and n_tail > 0:
            t = tail_word_of_N(x, m)
            _add_undirected(adj, micro_off + x, tail_off + domain.tail_index[t])

    # Tail time edges (shift)
    if include_time and n_tail > 0:
        for t in domain.tail_words:
            t2 = tail_shift_word(t)
            if t2 in domain.tail_index:
                _add_undirected(adj, tail_off + domain.tail_index[t], tail_off + domain.tail_index[t2])

    # Colors: micro 0; tail 1; macro unique 2+
    colors = [0] * n_total
    if n_tail > 0:
        for i in range(n_tail):
            colors[tail_off + i] = 1
    for i in range(n_macro):
        colors[macro_off + i] = 2 + i

    max_fiber = max(fiber_sizes.values()) if fiber_sizes else 0
    avg_fiber = float(sum(fiber_sizes.values()) / len(fiber_sizes)) if fiber_sizes else 0.0
    micro_range = range(micro_off, micro_off + n_micro)
    return adj, colors, micro_range, fiber_sizes


def run_scan(ms: List[int]) -> List[WLRow]:
    rows: List[WLRow] = []
    for m in ms:
        print(f"[scan] m={m}", flush=True)

        domain = build_fold_domain(m)
        adj, colors, micro_nodes, fiber_sizes = build_graph_zeckendorf(domain, include_time=True)
        stats = wl1_refine(len(adj), lambda v: adj[v], colors, micro_nodes=micro_nodes, progress_every=10)
        pstats = micro_partition_stats(stats.colors, micro_nodes)
        rows.append(
            WLRow(
                m=m,
                n_micro=domain.n_micro,
                n_total=len(adj),
                stable_t=stats.stable_t,
                resolve_t=stats.resolve_t or 0,
                unresolved_micro_final=pstats.unresolved_micro_final,
                max_micro_class_size_final=pstats.max_micro_class_size_final,
                max_fiber_size=max(fiber_sizes.values()) if fiber_sizes else 0,
                avg_fiber_size=float(sum(fiber_sizes.values()) / len(fiber_sizes)) if fiber_sizes else 0.0,
            )
        )

    return rows


def write_csv(rows: List[WLRow], out_csv: str) -> None:
    path = export_dir() / out_csv
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "m",
                "n_micro",
                "n_total",
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
                    r.m,
                    r.n_micro,
                    r.n_total,
                    r.stable_t,
                    r.resolve_t,
                    r.unresolved_micro_final,
                    r.max_micro_class_size_final,
                    r.max_fiber_size,
                    f"{r.avg_fiber_size:.6f}",
                ]
            )
    print(f"[scan] wrote {path}", flush=True)


def main() -> None:
    ms = list(range(3, 19))
    rows = run_scan(ms)
    write_csv(rows, "zeckendorf_scan_m3_to_m18.csv")


if __name__ == "__main__":
    main()

