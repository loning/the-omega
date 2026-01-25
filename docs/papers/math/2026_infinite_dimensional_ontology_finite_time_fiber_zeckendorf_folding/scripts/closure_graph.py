#!/usr/bin/env python3
"""
Closure graph for (micro adjacency + Fold_m edges).

Vertices:
  - micro nodes: all b in Omega_m, indexed by integer 0..2^m-1
  - macro nodes: all x in X_m (no-adjacent-1 words), indexed by macro_index

Edges:
  - micro adjacency edges from a chosen display (graph on Omega_m)
  - fold edges (b -- Fold_m(b))
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from common_zeckendorf import FoldDomain, build_fold_domain, fold_window_bits_to_macro_word


@dataclass(frozen=True)
class ClosureGraph:
    m: int
    n_micro: int
    n_macro: int
    n_total: int
    micro_range: range
    macro_range: range
    neighbors: List[List[int]]
    fold_domain: FoldDomain


def build_closure_graph(m: int, micro_adj: Sequence[Sequence[int]]) -> ClosureGraph:
    n_micro = 1 << int(m)
    if len(micro_adj) != n_micro:
        raise ValueError("micro_adj length mismatch")

    dom = build_fold_domain(m)
    n_macro = len(dom.macro_words)
    n_total = n_micro + n_macro

    neighbors: List[List[int]] = [[] for _ in range(n_total)]

    # micro adjacency edges (undirected)
    for u in range(n_micro):
        for v in micro_adj[u]:
            neighbors[u].append(int(v))

    # fold edges (undirected)
    for b in range(n_micro):
        x = fold_window_bits_to_macro_word(b, m=m)
        mi = dom.macro_index[x]
        macro_node = n_micro + mi
        neighbors[b].append(macro_node)
        neighbors[macro_node].append(b)

    return ClosureGraph(
        m=int(m),
        n_micro=int(n_micro),
        n_macro=int(n_macro),
        n_total=int(n_total),
        micro_range=range(0, n_micro),
        macro_range=range(n_micro, n_total),
        neighbors=neighbors,
        fold_domain=dom,
    )

