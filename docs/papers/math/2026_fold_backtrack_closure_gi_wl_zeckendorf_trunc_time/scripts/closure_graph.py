#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Closure graph: micro X_m plus macro Y_m with fold edges."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from common_zeckendorf import FoldResult, build_fold_domain, fold_f_m


@dataclass(frozen=True)
class ClosureGraph:
    m: int
    n_micro: int
    n_macro: int
    n_total: int
    micro_range: range
    macro_range: range
    # Macro node id = n_micro + macro_idx
    micro_to_macro_node: List[int]
    macro_to_micros: List[List[int]]
    micro_adj: List[List[int]]

    def neighbors(self, v: int) -> List[int]:
        if v < self.n_micro:
            return [*self.micro_adj[v], self.micro_to_macro_node[v]]
        midx = v - self.n_micro
        return self.macro_to_micros[midx]


def build_closure_graph(m: int, micro_adj: List[List[int]]) -> ClosureGraph:
    fold: FoldResult = build_fold_domain(m)
    n_micro = fold.n_micro
    n_macro = len(fold.macro_words)
    n_total = n_micro + n_macro
    micro_range = range(n_micro)
    macro_range = range(n_micro, n_total)

    micro_to_macro_node: List[int] = [0] * n_micro
    macro_to_micros: List[List[int]] = [[] for _ in range(n_macro)]

    for x in range(n_micro):
        w = fold_f_m(x, m=m)
        midx = fold.macro_index[w]
        macro_node = n_micro + midx
        micro_to_macro_node[x] = macro_node
        macro_to_micros[midx].append(x)

    return ClosureGraph(
        m=m,
        n_micro=n_micro,
        n_macro=n_macro,
        n_total=n_total,
        micro_range=micro_range,
        macro_range=macro_range,
        micro_to_macro_node=micro_to_macro_node,
        macro_to_micros=macro_to_micros,
        micro_adj=micro_adj,
    )

