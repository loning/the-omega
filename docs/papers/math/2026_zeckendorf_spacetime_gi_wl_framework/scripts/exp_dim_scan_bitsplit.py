#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bit-split dimension scan (Zeckendorf-only, open boundary)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt

from common_paths import export_dir
from common_zeckendorf import build_fold_domain, fold_f_m, tail_shift_word, tail_word_of_N
from micro_models import balanced_splits, bitsplit_index, bitsplit_coords
from wl1 import micro_partition_stats, wl1_refine


def _add_undirected(adj: List[List[int]], a: int, b: int) -> None:
    if b not in adj[a]:
        adj[a].append(b)
    if a not in adj[b]:
        adj[b].append(a)


def build_graph_zeckendorf_from_micro_adj(m: int, micro_adj: List[List[int]]) -> Tuple[List[List[int]], List[int], range]:
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
    for x in range(n_micro):
        w = fold_f_m(x, m)
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
    return adj, colors, micro_nodes


def bitsplit_neighbors_open(m: int, d: int) -> List[List[int]]:
    """Bit-split open-boundary adjacency for {0,1}^m as index 0..2^m-1."""
    splits = balanced_splits(m, d)
    dims = [1 << s for s in splits]
    n = 1 << m
    out: List[List[int]] = [[] for _ in range(n)]
    for x in range(n):
        c = list(bitsplit_coords(x, splits))
        nb: List[int] = []
        for j, L in enumerate(dims):
            for delta in (-1, 1):
                v = c[j] + delta
                if 0 <= v < L:
                    c2 = c.copy()
                    c2[j] = v
                    nb.append(bitsplit_index(c2, splits))
        out[x] = nb
    return out


@dataclass(frozen=True)
class Row:
    m: int
    d: int
    stable_t: int
    resolve_t: int
    unresolved: int


def main() -> None:
    ms = [6, 9, 12, 15]
    rows: List[Row] = []
    series_resolve: Dict[int, List[Tuple[int, int]]] = {m: [] for m in ms}
    series_unres: Dict[int, List[Tuple[int, int]]] = {m: [] for m in ms}

    for m in ms:
        print(f"[exp_dim_scan] m={m}", flush=True)
        for d in range(1, m + 1):
            micro_adj = bitsplit_neighbors_open(m, d)
            adj, colors, micro_nodes = build_graph_zeckendorf_from_micro_adj(m, micro_adj)
            stats = wl1_refine(len(adj), lambda v: adj[v], colors, micro_nodes=micro_nodes, progress_every=20)
            pstats = micro_partition_stats(stats.colors, micro_nodes)
            resolve_t = stats.resolve_t or 0
            rows.append(Row(m=m, d=d, stable_t=stats.stable_t, resolve_t=resolve_t, unresolved=pstats.unresolved_micro_final))
            series_resolve[m].append((d, resolve_t))
            series_unres[m].append((d, pstats.unresolved_micro_final))

    out_csv = export_dir() / "dim_scan_bitsplit_open_m6_m9_m12_m15.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["m", "d", "stable_t", "resolve_t", "unresolved_micro_final"])
        for r in rows:
            w.writerow([r.m, r.d, r.stable_t, r.resolve_t, r.unresolved])
    print(f"[exp_dim_scan] wrote {out_csv}", flush=True)

    # plots
    out1 = export_dir() / "resolve_time_vs_dimension_m6_m9_m12_m15.png"
    out2 = export_dir() / "unresolved_vs_dimension_m6_m9_m12_m15.png"

    plt.figure(figsize=(8, 3.6))
    for m in ms:
        xs = [d for d, _ in series_resolve[m]]
        ys = [v for _, v in series_resolve[m]]
        plt.plot(xs, ys, marker="o", linewidth=1.5, label=f"m={m}")
    plt.xlabel("d (dimension)")
    plt.ylabel("resolve_t (WL-1; 0 means not resolved)")
    plt.title("Resolve time vs dimension (bit-split open, Zeckendorf)")
    plt.grid(True, alpha=0.3)
    plt.legend(ncol=2, fontsize=9)
    plt.tight_layout()
    plt.savefig(out1, dpi=160)
    plt.close()

    plt.figure(figsize=(8, 3.6))
    for m in ms:
        xs = [d for d, _ in series_unres[m]]
        ys = [v for _, v in series_unres[m]]
        plt.plot(xs, ys, marker="o", linewidth=1.5, label=f"m={m}")
    plt.xlabel("d (dimension)")
    plt.ylabel("unresolved_micro_final (WL-1)")
    plt.title("Unresolved micro vs dimension (bit-split open, Zeckendorf)")
    plt.grid(True, alpha=0.3)
    plt.legend(ncol=2, fontsize=9)
    plt.tight_layout()
    plt.savefig(out2, dpi=160)
    plt.close()

    print("[exp_dim_scan] OK", flush=True)


if __name__ == "__main__":
    main()

