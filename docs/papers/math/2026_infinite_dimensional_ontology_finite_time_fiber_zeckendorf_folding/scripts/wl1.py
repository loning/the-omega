#!/usr/bin/env python3
"""
Deterministic 1-WL (color refinement) used by this paper.

We use 1-WL as an "observer-time" proxy on a finite closure graph:
  - stable_t: iterations until colors stabilize
  - resolve_t: iterations until all micro nodes are uniquely colored
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from common_progress import Progress


@dataclass(frozen=True)
class WLStats:
    stable_t: int
    resolve_t: Optional[int]
    colors: List[int]


@dataclass(frozen=True)
class MicroPartitionStats:
    unresolved_micro_final: int
    max_micro_class_size_final: int


def _is_micro_resolved(colors: Sequence[int], micro_nodes: range) -> bool:
    seen: set[int] = set()
    for v in micro_nodes:
        c = int(colors[v])
        if c in seen:
            return False
        seen.add(c)
    return True


def micro_partition_stats(colors: Sequence[int], micro_nodes: range) -> MicroPartitionStats:
    # Count class sizes on micro nodes only.
    counts: Dict[int, int] = {}
    for v in micro_nodes:
        c = int(colors[v])
        counts[c] = counts.get(c, 0) + 1
    unresolved = sum(sz for sz in counts.values() if sz > 1)
    max_cls = max(counts.values()) if counts else 0
    return MicroPartitionStats(unresolved_micro_final=int(unresolved), max_micro_class_size_final=int(max_cls))


def wl1_refine(
    n_nodes: int,
    neighbors: Sequence[Sequence[int]],
    init_colors: Sequence[int],
    micro_nodes: range,
    max_iter: int = 200,
    progress_every_seconds: float = 15.0,
) -> WLStats:
    """
    Run 1-WL refinement on an undirected graph.

    Color update rule:
      new_color(v) = Hash( color(v), multiset{ color(u) : u in N(v) } )

    Hash is implemented by a deterministic re-indexing of signatures.
    """
    if n_nodes <= 0:
        return WLStats(stable_t=0, resolve_t=0, colors=[])
    if len(neighbors) != n_nodes:
        raise ValueError("neighbors length mismatch")
    if len(init_colors) != n_nodes:
        raise ValueError("init_colors length mismatch")

    prog = Progress(every_seconds=progress_every_seconds)

    colors = [int(c) for c in init_colors]
    resolve_t: Optional[int] = 0 if _is_micro_resolved(colors, micro_nodes) else None

    for t in range(1, int(max_iter) + 1):
        prog.maybe(f"wl1 t={t}/{max_iter}")

        # Compute signatures.
        sigs: List[Tuple[int, Tuple[int, ...]]] = []
        sigs_extend = sigs.append
        for v in range(n_nodes):
            neigh_cols = [colors[u] for u in neighbors[v]]
            neigh_cols.sort()
            sigs_extend((colors[v], tuple(neigh_cols)))

        # Relabel signatures deterministically (stable order by (old_color, neighbor tuple)).
        uniq = sorted(set(sigs))
        sig_to_new: Dict[Tuple[int, Tuple[int, ...]], int] = {s: i for i, s in enumerate(uniq)}
        new_colors = [sig_to_new[s] for s in sigs]

        if resolve_t is None and _is_micro_resolved(new_colors, micro_nodes):
            resolve_t = int(t)

        if new_colors == colors:
            prog.done(f"wl1 stable at t={t-1}")
            return WLStats(stable_t=int(t - 1), resolve_t=resolve_t, colors=new_colors)

        colors = new_colors

    prog.done(f"wl1 reached max_iter={max_iter}")
    return WLStats(stable_t=int(max_iter), resolve_t=resolve_t, colors=colors)

