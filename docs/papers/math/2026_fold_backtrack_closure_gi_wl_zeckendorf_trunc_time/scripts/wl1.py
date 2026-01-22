#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic 1-WL (color refinement) for closure graphs with micro+macro."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple


NeighborFn = Callable[[int], Sequence[int]]


@dataclass(frozen=True)
class WLStats:
    stable_t: int
    resolve_t: Optional[int]
    colors: List[int]  # final colors


def _compress_colors(signatures: List[Tuple]) -> List[int]:
    # Deterministic: assign IDs in order of first appearance.
    mp: Dict[Tuple, int] = {}
    out = [0] * len(signatures)
    nxt = 0
    for i, sig in enumerate(signatures):
        v = mp.get(sig)
        if v is None:
            v = nxt
            mp[sig] = v
            nxt += 1
        out[i] = v
    return out


def wl1_refine(
    n_nodes: int,
    neighbors: NeighborFn,
    init_colors: List[int],
    micro_nodes: range,
    max_iter: int = 100,
    progress_every: int = 1,
) -> WLStats:
    if len(init_colors) != n_nodes:
        raise ValueError("init_colors length mismatch")

    colors = list(init_colors)
    resolve_t: Optional[int] = None

    for t in range(1, max_iter + 1):
        if progress_every > 0 and (t == 1 or t % progress_every == 0):
            print(f"[wl1] iter={t}", flush=True)

        sigs: List[Tuple] = [None] * n_nodes  # type: ignore[assignment]
        for v in range(n_nodes):
            nb_cols = [colors[u] for u in neighbors(v)]
            nb_cols.sort()
            sigs[v] = (colors[v], tuple(nb_cols))

        new_colors = _compress_colors(sigs)

        if resolve_t is None:
            # micro resolved if each micro node has unique color among micros
            seen = set()
            ok = True
            for v in micro_nodes:
                c = new_colors[v]
                if c in seen:
                    ok = False
                    break
                seen.add(c)
            if ok:
                resolve_t = t

        if new_colors == colors:
            # stable_t counts *refinement updates* (exclude the final no-op check)
            return WLStats(stable_t=t - 1, resolve_t=resolve_t, colors=colors)
        colors = new_colors

    return WLStats(stable_t=max_iter, resolve_t=resolve_t, colors=colors)


@dataclass(frozen=True)
class PartitionStats:
    unresolved_micro_final: int
    non_single_micro_classes_final: int
    max_micro_class_size_final: int


def micro_partition_stats(colors: List[int], micro_nodes: range) -> PartitionStats:
    cls: Dict[int, int] = defaultdict(int)
    for v in micro_nodes:
        cls[colors[v]] += 1
    non_single = [sz for sz in cls.values() if sz > 1]
    unresolved = sum(sz for sz in non_single)
    max_sz = max(non_single) if non_single else 1
    return PartitionStats(
        unresolved_micro_final=unresolved,
        non_single_micro_classes_final=len(non_single),
        max_micro_class_size_final=max_sz,
    )


def micro_ambiguous_pairs(colors: List[int], micro_nodes: range) -> List[Tuple[int, int]]:
    buckets: Dict[int, List[int]] = defaultdict(list)
    for v in micro_nodes:
        buckets[colors[v]].append(v)
    pairs: List[Tuple[int, int]] = []
    for nodes in buckets.values():
        if len(nodes) == 2:
            a, b = sorted(nodes)
            pairs.append((a, b))
    pairs.sort()
    return pairs

