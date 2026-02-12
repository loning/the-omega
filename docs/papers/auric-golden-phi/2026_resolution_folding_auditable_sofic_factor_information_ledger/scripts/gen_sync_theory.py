#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate synchronization / ambiguity-shell certificates for Y_m.

Outputs:
- artifacts/export/sync_theory.csv
- sections/generated/tab_sync_theory.tex

The generated LaTeX fragment is write-only and should be included via \\input.
"""

from __future__ import annotations

import argparse
import csv
import math
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from common_paths import export_dir, generated_dir


@dataclass
class Progress:
    interval_s: float = 20.0
    t0: float = time.time()
    t_last: float = 0.0

    def log(self, msg: str) -> None:
        now = time.time()
        if (now - self.t_last) >= self.interval_s:
            dt = now - self.t0
            print(f"[progress] t={dt:.1f}s {msg}", flush=True)
            self.t_last = now


def fib_list(n: int) -> List[int]:
    """Return Fibonacci numbers F[0..n] with F_1=F_2=1 convention (F[0]=0)."""
    if n < 0:
        return []
    F = [0] * (n + 1)
    if n >= 1:
        F[1] = 1
    if n >= 2:
        F[2] = 1
    for k in range(3, n + 1):
        F[k] = F[k - 1] + F[k - 2]
    return F


def zeckendorf_digits_prefix(N: int, m: int, F: List[int]) -> int:
    """Return Fold_m of value N as an m-bit mask (c_k stored at bit k-1)."""
    if N < 0:
        raise ValueError("N must be nonnegative")
    if m <= 0:
        return 0

    # Find maximal k with F[k+1] <= N.
    k = 1
    while (k + 1) < len(F) and F[k + 1] <= N:
        k += 1
    if k > m + 4:
        k = m + 4

    digits: Dict[int, int] = {}
    kk = k
    n = N
    while n > 0 and kk >= 1:
        w = F[kk + 1]
        if w <= n:
            digits[kk] = 1
            n -= w
            kk -= 2
        else:
            kk -= 1

    mask = 0
    for pos in range(1, m + 1):
        if digits.get(pos, 0):
            mask |= 1 << (pos - 1)
    return mask


def fold_m_mask(word: int, m: int, weights: List[int], F: List[int]) -> int:
    """Compute Fold_m for a binary word encoded as bits (bit k-1 is ω_k)."""
    N = 0
    w = word
    for k in range(1, m + 1):
        if w & 1:
            N += weights[k]
        w >>= 1
    return zeckendorf_digits_prefix(N, m, F)


def build_Gm_edges(m: int) -> Tuple[List[int], List[int], List[int], List[int]]:
    """Return (succ0, succ1, lab0, lab1) for vertices v in V_m={0,1}^{m-1}.

We encode v=v1..v_{m-1} as an (m-1)-bit integer with v_k at bit (k-1).
For b in {0,1}, the edge (v,b) goes to v' = v2..v_{m-1}b, encoded as:
v' = (v >> 1) | (b << (m-2)).
The label is Fold_m(v1..v_{m-1}b), encoded as an m-bit mask.
"""
    if m < 2:
        raise ValueError("m must be >= 2")
    V = 1 << (m - 1)
    top_bit = 1 << (m - 2)

    F = fib_list(m + 8)
    weights = [0] * (m + 1)
    for k in range(1, m + 1):
        weights[k] = F[k + 1]

    succ0 = [0] * V
    succ1 = [0] * V
    lab0 = [0] * V
    lab1 = [0] * V

    for v in range(V):
        v_drop = v >> 1  # drop v1
        # b=0
        succ0[v] = v_drop
        w0 = v  # append 0 as m-th bit
        lab0[v] = fold_m_mask(w0, m, weights, F)
        # b=1
        succ1[v] = v_drop | top_bit
        w1 = v | (1 << (m - 1))
        lab1[v] = fold_m_mask(w1, m, weights, F)

    return succ0, succ1, lab0, lab1


def determinize(
    m: int,
    succ0: List[int],
    succ1: List[int],
    lab0: List[int],
    lab1: List[int],
    prog: Progress,
) -> Tuple[List[int], List[Dict[int, int]]]:
    """Determinize G_m by subset construction.

Returns:
- masks_by_id: list of subset bitmasks in BFS order
- trans_by_id: list of dict label->next_id
"""
    V = 1 << (m - 1)
    full = (1 << V) - 1

    masks_by_id: List[int] = []
    trans_by_id: List[Dict[int, int]] = []
    id_of: Dict[int, int] = {full: 0}
    q: deque[int] = deque([full])

    while q:
        S = q.popleft()
        sid = id_of[S]
        if sid == len(masks_by_id):
            masks_by_id.append(S)
            trans_by_id.append({})

        next_mask_by_label: Dict[int, int] = {}
        tmp = S
        while tmp:
            lsb = tmp & -tmp
            v = lsb.bit_length() - 1
            tmp -= lsb
            # b=0
            L0 = lab0[v]
            t0 = succ0[v]
            next_mask_by_label[L0] = next_mask_by_label.get(L0, 0) | (1 << t0)
            # b=1
            L1 = lab1[v]
            t1 = succ1[v]
            next_mask_by_label[L1] = next_mask_by_label.get(L1, 0) | (1 << t1)

        trans: Dict[int, int] = {}
        for L, Smask in next_mask_by_label.items():
            nid = id_of.get(Smask)
            if nid is None:
                nid = len(id_of)
                id_of[Smask] = nid
                q.append(Smask)
            trans[L] = nid
        trans_by_id[sid] = trans

        if (len(masks_by_id) & 0x3FF) == 0:
            prog.log(f"m={m} det_states={len(masks_by_id)} queue={len(q)}")

    return masks_by_id, trans_by_id


def build_amb_graph(
    masks_by_id: List[int],
    trans_by_id: List[Dict[int, int]],
) -> Tuple[List[int], List[Dict[int, int]], int]:
    """Restrict the determinized automaton to ambiguous states |S|>1.

Returns:
- amb_ids: list of global state ids that are ambiguous
- amb_adj: adjacency list on amb-indexed nodes, with edge weights = number of labels
- start_amb_idx: amb-index of the start state (0) if ambiguous, else -1
"""
    amb_ids: List[int] = [i for i, S in enumerate(masks_by_id) if S.bit_count() > 1]
    amb_index: Dict[int, int] = {sid: j for j, sid in enumerate(amb_ids)}
    n = len(amb_ids)

    amb_adj: List[Dict[int, int]] = [dict() for _ in range(n)]
    for sid in amb_ids:
        i = amb_index[sid]
        for _, nxt in trans_by_id[sid].items():
            j = amb_index.get(nxt)
            if j is None:
                continue
            amb_adj[i][j] = amb_adj[i].get(j, 0) + 1

    start_amb_idx = amb_index.get(0, -1)
    return amb_ids, amb_adj, start_amb_idx


def topological_order_or_cycle(adj: List[Dict[int, int]]) -> Tuple[bool, List[int]]:
    """Return (has_cycle, topo_order) for the directed graph underlying adj."""
    n = len(adj)
    indeg = [0] * n
    for i in range(n):
        for j in adj[i].keys():
            indeg[j] += 1
    dq: deque[int] = deque([i for i in range(n) if indeg[i] == 0])
    topo: List[int] = []
    while dq:
        i = dq.popleft()
        topo.append(i)
        for j in adj[i].keys():
            indeg[j] -= 1
            if indeg[j] == 0:
                dq.append(j)
    has_cycle = len(topo) != n
    return has_cycle, topo


def longest_path_dag(adj: List[Dict[int, int]], topo: List[int], start: int) -> int:
    """Longest path length (number of edges) from start in a DAG."""
    n = len(adj)
    neg_inf = -10**18
    dp = [neg_inf] * n
    if start < 0:
        return 0
    dp[start] = 0
    for i in topo:
        if dp[i] == neg_inf:
            continue
        di = dp[i]
        for j in adj[i].keys():
            if di + 1 > dp[j]:
                dp[j] = di + 1
    return int(max(0, max(dp)))


def spectral_radius_power_iteration(adj: List[Dict[int, int]], iters: int = 60) -> float:
    """Estimate PF spectral radius of a nonnegative matrix given as sparse adjacency.

The matrix acts on column vectors: (Ax)_j = sum_i x_i * w_{i->j}.
"""
    n = len(adj)
    if n == 0:
        return 0.0
    x = [1.0] * n
    lam = 0.0
    for _ in range(iters):
        y = [0.0] * n
        for i in range(n):
            xi = x[i]
            if xi == 0.0:
                continue
            for j, w in adj[i].items():
                y[j] += xi * float(w)
        norm = max(y)
        if norm <= 0.0:
            return 0.0
        x = [v / norm for v in y]
        lam = norm
    return float(lam)


def write_csv(rows: List[Dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else ["m"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_latex_table(rows: List[Dict[str, object]], path: Path) -> None:
    """Generate a small LaTeX table fragment via pylatex."""
    from pylatex import Tabular, NoEscape  # type: ignore

    tab = Tabular("r|r r r r r r")
    tab.add_hline()
    tab.add_row(
        [
            NoEscape("$m$"),
            NoEscape("$|V_m|$"),
            NoEscape("$|\\mathcal{S}_m^{\\mathrm{det}}|$"),
            NoEscape("$|\\mathcal{S}_m^{\\mathrm{amb}}|$"),
            NoEscape("cycle?"),
            NoEscape("$D_{\\mathrm{sync}}(m)$"),
            NoEscape("$h_{\\mathrm{top}}(Y_m^{\\mathrm{amb}})$"),
        ]
    )
    tab.add_hline()
    for r in rows:
        h_amb = float(r["h_amb"])
        D = r["D_sync"]
        if isinstance(D, str) and D.startswith("\\"):
            D_cell = NoEscape(f"${D}$")
        else:
            D_cell = str(D)
        tab.add_row(
            [
                str(int(r["m"])),
                str(int(r["V"])),
                str(int(r["det_states"])),
                str(int(r["amb_states"])),
                "yes" if bool(r["amb_cycle"]) else "no",
                D_cell,
                f"{h_amb:.6f}" if h_amb >= 0.0 else NoEscape("$-\\infty$"),
            ]
        )
    tab.add_hline()

    path.parent.mkdir(parents=True, exist_ok=True)
    tex = tab.dumps()
    frag = "\n".join(
        [
            "% auto-generated by scripts/gen_sync_theory.py",
            "\\begin{table}[t]",
            "\\centering",
            "\\caption{Determinized ambiguity-shell certificates for $Y_m$: size of the reachable subset construction and the induced non-singleton subgraph. When the non-singleton subgraph is acyclic, the worst-case synchronization delay $D_{\\mathrm{sync}}(m)$ is finite and computable by longest-path DP.}",
            "\\label{tab:sync-theory}",
            tex,
            "\\end{table}",
            "",
        ]
    )
    path.write_text(frag, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m-min", type=int, default=2)
    ap.add_argument("--m-max", type=int, default=10)
    args = ap.parse_args()

    m_min = int(args.m_min)
    m_max = int(args.m_max)
    if m_min < 2 or m_max < m_min:
        raise SystemExit("Invalid m range (require m>=2)")

    prog = Progress()
    rows: List[Dict[str, object]] = []

    for m in range(m_min, m_max + 1):
        prog.log(f"start m={m}")
        succ0, succ1, lab0, lab1 = build_Gm_edges(m)
        masks_by_id, trans_by_id = determinize(m, succ0, succ1, lab0, lab1, prog)
        amb_ids, amb_adj, start_amb = build_amb_graph(masks_by_id, trans_by_id)
        has_cycle, topo = topological_order_or_cycle(amb_adj)

        if has_cycle or start_amb < 0:
            D_sync: object = "\\infty"
            rho = spectral_radius_power_iteration(amb_adj)
            h_amb = math.log(rho) if rho > 0.0 else float("-inf")
        else:
            D_sync = longest_path_dag(amb_adj, topo, start_amb)
            h_amb = float("-inf")

        V = 1 << (m - 1)
        rows.append(
            {
                "m": m,
                "V": V,
                "det_states": len(masks_by_id),
                "amb_states": len(amb_ids),
                "amb_cycle": bool(has_cycle),
                "D_sync": D_sync,
                "h_amb": (h_amb if math.isfinite(h_amb) else -1.0),
            }
        )

    csv_path = export_dir() / "sync_theory.csv"
    tex_path = generated_dir() / "tab_sync_theory.tex"
    write_csv(rows, csv_path)
    write_latex_table(rows, tex_path)
    print(f"[done] wrote {csv_path} and {tex_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

