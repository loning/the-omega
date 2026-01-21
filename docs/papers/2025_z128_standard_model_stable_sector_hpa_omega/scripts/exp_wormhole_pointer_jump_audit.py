# -*- coding: utf-8 -*-
"""
Wormhole-like pointer jump audit (protocol-only).

Goal:
  Quantify how an explicit finite set of nonlocal pointer edges reduces scan
  distance on the Hilbert-indexed screen at fixed n.

Design goals:
  - Deterministic (no randomness, no timestamps).
  - Standard-library only.
  - Output small LaTeX fragments for Appendix 10.

Outputs (LaTeX fragments):
  - sections/generated/wormhole_pointer_jump_rows.tex
  - sections/generated/wormhole_pointer_jump_summary.tex
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from common_paths import generated_dir
from common_tex import write_lines


@dataclass(frozen=True)
class PairStat:
    i: int
    j: int
    d0: int
    d1: int


def _default_pointer_edges(N: int) -> List[Tuple[int, int]]:
    """
    A deterministic pointer candidate pool. Edges are undirected in this audit.
    A caller may take the first k edges to form a bounded pointer family of size k.
    """
    if N <= 1:
        return []
    edges: List[Tuple[int, int]] = []
    edges.append((0, N - 1))
    edges.append((N // 4, (3 * N) // 4))
    edges.append((N // 8, (N // 2) + (N // 8)))
    edges.append((N // 16, (15 * N) // 16))
    edges.append((N // 2, N - 1))
    edges.append((0, N // 2))
    edges.append((N // 3, (2 * N) // 3))
    edges.append((N // 5, (4 * N) // 5))
    edges.append((N // 7, (6 * N) // 7))
    # Ensure uniqueness and bounds.
    out: List[Tuple[int, int]] = []
    seen = set()
    for a, b in edges:
        a = int(max(0, min(N - 1, a)))
        b = int(max(0, min(N - 1, b)))
        if a == b:
            continue
        key = (a, b) if a < b else (b, a)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _eval_pairs(N: int) -> List[Tuple[int, int]]:
    """
    A small deterministic evaluation set of index pairs.
    """
    if N <= 1:
        return []
    pairs: List[Tuple[int, int]] = []
    anchors = [
        (0, N - 1),
        (0, N // 2),
        (N // 4, (3 * N) // 4),
        (N // 8, (N // 2) + (N // 8)),
    ]
    for a, b in anchors:
        a = int(max(0, min(N - 1, a)))
        b = int(max(0, min(N - 1, b)))
        if a != b:
            pairs.append((a, b))

    # Add a deterministic sweep of pairs.
    for t in range(1, 9):
        a = (t * 137) % N
        b = (a + (N // 2) + (t * 17)) % N
        if a == b:
            b = (b + 1) % N
        pairs.append((int(a), int(b)))

    # Deduplicate
    out: List[Tuple[int, int]] = []
    seen = set()
    for a, b in pairs:
        key = (a, b)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _build_ptr_map(edges: Iterable[Tuple[int, int]]) -> Dict[int, List[int]]:
    m: Dict[int, List[int]] = {}
    for a, b in edges:
        m.setdefault(int(a), []).append(int(b))
        m.setdefault(int(b), []).append(int(a))
    return m


def _shortest_distance_path_with_ptr(N: int, ptr_map: Dict[int, List[int]], src: int, dst: int) -> int:
    """
    Graph distance on the scan path (0-1-2-...-(N-1)) plus undirected pointer edges.
    Unit cost per edge.
    """
    if src == dst:
        return 0
    src = int(src)
    dst = int(dst)
    q: deque[int] = deque([src])
    dist = {src: 0}
    while q:
        u = q.popleft()
        du = dist[u]
        # Scan neighbors
        if u - 1 >= 0 and (u - 1) not in dist:
            dist[u - 1] = du + 1
            if (u - 1) == dst:
                return du + 1
            q.append(u - 1)
        if u + 1 < N and (u + 1) not in dist:
            dist[u + 1] = du + 1
            if (u + 1) == dst:
                return du + 1
            q.append(u + 1)
        # Pointer neighbors
        for v in ptr_map.get(u, []):
            if v in dist:
                continue
            dist[v] = du + 1
            if v == dst:
                return du + 1
            q.append(v)
    # Should not happen on a connected path graph.
    return abs(src - dst)


def main() -> None:
    out = generated_dir()
    rows_path = out / "wormhole_pointer_jump_rows.tex"
    sum_path = out / "wormhole_pointer_jump_summary.tex"

    rows: List[str] = []
    notes: List[str] = []

    # Keep the audit small and deterministic: run a finite grid over n and pointer counts.
    n_list = [3, 4, 5, 6]
    ptr_k_list = [0, 1, 2, 3, 4, 8]

    for n in n_list:
        N = int(4**int(n))
        pool = _default_pointer_edges(N)
        pairs = _eval_pairs(N)

        for k_ptr in ptr_k_list:
            k_ptr = int(k_ptr)
            ptr_edges = list(pool[:k_ptr]) if k_ptr > 0 else []
            ptr_map = _build_ptr_map(ptr_edges)

            stats: List[PairStat] = []
            for i, j in pairs:
                d0 = int(abs(int(i) - int(j)))
                if d0 <= 0:
                    continue
                d1 = int(_shortest_distance_path_with_ptr(N, ptr_map, int(i), int(j)))
                stats.append(PairStat(i=int(i), j=int(j), d0=d0, d1=d1))

            if not stats:
                continue

            ratios = [s.d1 / float(s.d0) for s in stats if s.d0 > 0]
            mean_ratio = sum(ratios) / float(len(ratios))
            min_ratio = min(ratios)
            best = max(stats, key=lambda s: (s.d0 - s.d1, s.d0, -s.d1))
            max_delta = int(best.d0 - best.d1)
            exemplar = f"{best.i}->{best.j} (d0-d1={max_delta})"

            rows.append(
                " & ".join(
                    [
                        str(int(n)),
                        str(int(N)),
                        str(int(len(ptr_edges))),
                        f"{mean_ratio:.6f}",
                        f"{min_ratio:.6f}",
                        str(int(max_delta)),
                        exemplar.replace("_", r"\_"),
                    ]
                )
                + r" \\"
            )

            notes.append(
                rf"For $n={int(n)}$ (screen size $4^n={int(N)}$) and \#ptr={len(ptr_edges)}, the audit reports ratios over {len(stats)} fixed index pairs."
            )

    if not rows:
        write_lines(rows_path, ["% (no pointer-jump rows available)"])
        write_lines(
            sum_path,
            [
                r"\paragraph{Pointer-jump audit summary.} \AuditTag "
                + r"No rows were generated (unexpected).",
            ],
        )
        return

    write_lines(rows_path, rows)
    write_lines(
        sum_path,
        [
            r"\paragraph{Pointer-jump audit summary.} \AuditTag "
            + r"We model the Hilbert-indexed screen as a unit-cost scan path on indices $0,1,\dots,4^n-1$ augmented by a finite set of explicit undirected pointer edges. "
            + r"For a fixed finite set of index pairs we report the baseline scan distance $d_0=|i-j|$ and the shortest-path distance $d_1$ in the augmented graph, summarized by the ratio $d_1/d_0$ and the maximal absolute reduction $\Delta=d_0-d_1$. "
            + r"This is a protocol-only audit of readout shortcut geometry (Definition~\ref{def:wormhole_pointer_jump}).",
        ]
        + [r"\noindent\AuditTag " + n for n in notes],
    )


if __name__ == "__main__":
    main()

