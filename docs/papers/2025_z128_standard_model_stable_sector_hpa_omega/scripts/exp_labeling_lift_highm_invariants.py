# -*- coding: utf-8 -*-
"""
High-m invariants inside prefix lift fibers (beyond suffix enumeration).

The coarse functorial lift uses only the prefix projection pi_{m->6} and therefore
identifies all lifts w in Ext_m(u) with the same base label L_SM(u).

To expose nontrivial structure available at window length m, this script computes
simple intrinsic invariants on X_m and summarizes them *within each prefix fiber*:
  - the Fold_m degeneracy g_m(w) := |Fold_m^{-1}(w)| over N in {0,..,2^m-1},
  - the pi-channel boundary tag on X_m: w_1 = w_m = 1 (boundary vs cyclic),
  - the Zeckendorf value V_m(w) using Fibonacci weights [F2..F_{m+1}].

Outputs (LaTeX fragment):
  - sections/generated/label_lift_highm_invariants_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import exp_foldm_stats as foldm
import exp_sm_labeling_solver as sml
import exp_xm_enumeration as xm


def fib_weights(m: int) -> List[int]:
    # Fibonacci weights [F2, F3, ..., F_{m+1}] with F1=F2=1.
    if m < 0:
        raise ValueError("m must be nonnegative.")
    if m == 0:
        return []
    if m == 1:
        return [1]
    w = [1, 2]
    while len(w) < m:
        w.append(w[-1] + w[-2])
    return w


def zeckendorf_value_m(w: str) -> int:
    wts = fib_weights(len(w))
    return sum(int(bit) * wts[i] for i, bit in enumerate(w))


def is_boundary_word(w: str) -> bool:
    return w[0] == "1" and w[-1] == "1"


def hist_to_tex(hist: Counter[int]) -> str:
    parts = [f"{k}:{hist[k]}" for k in sorted(hist)]
    return "\\texttt{" + ", ".join(parts) + "}"


def parse_label_map_from_rows(rows: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in rows:
        cols = [c.strip() for c in line.split("&")]
        if len(cols) < 7:
            continue
        w_col = cols[0]
        if not w_col.startswith("\\texttt{") or "}" not in w_col:
            continue
        u = w_col[len("\\texttt{") : w_col.index("}")]
        label = cols[6].strip()
        out[u] = label
    if len(out) != 21:
        raise AssertionError(f"Expected 21 base labels, got {len(out)}.")
    return out


def main() -> None:
    m_list = [8, 10, 12, 14, 16]

    base_rows = sml.generate_rows()
    label_of = parse_label_map_from_rows(base_rows)
    X6 = sml.all_x6()
    if len(X6) != 21:
        raise AssertionError("Expected |X6|=21.")

    # Precompute X_m and g_m for each m.
    Xm_of: Dict[int, List[str]] = {}
    gm_of: Dict[int, Dict[str, int]] = {}
    for m in m_list:
        Xm = xm.all_xm(m)
        Xm_of[m] = Xm
        pre: Dict[str, List[int]] = defaultdict(list)
        for n in range(1 << m):
            w = foldm.foldm(n, m)
            pre[w].append(n)
        # Convert to degeneracy map.
        gm = {w: len(ns) for (w, ns) in pre.items()}
        if set(gm.keys()) != set(Xm):
            raise AssertionError(f"Fold_m image mismatch at m={m}.")
        gm_of[m] = gm

    # Emit rows: one row per (m,u) summarizing invariants inside Ext_m(u).
    def sort_key(u: str) -> Tuple[int, str]:
        return (sml.zeckendorf_value(u), u)

    out_rows: List[str] = []
    for m in m_list:
        Xm = Xm_of[m]
        gm = gm_of[m]
        for u in sorted(X6, key=sort_key):
            lab = label_of[u]
            lifts = [w for w in Xm if w.startswith(u)]
            cnt = len(lifts)
            bdry = sum(1 for w in lifts if is_boundary_word(w))
            cyc = cnt - bdry

            gs = [gm[w] for w in lifts]
            g_min = min(gs) if gs else 0
            g_max = max(gs) if gs else 0
            g_hist = Counter(gs)

            Vs = [zeckendorf_value_m(w) for w in lifts]
            V_min = min(Vs) if Vs else 0
            V_max = max(Vs) if Vs else 0
            V_range = f"\\texttt{{{V_min}..{V_max}}}"

            out_rows.append(
                f"{m} & \\texttt{{{u}}} & {lab} & {cnt} & {cyc} & {bdry} & {g_min} & {g_max} & {hist_to_tex(g_hist)} & {V_range} \\\\"
            )

    out_rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "label_lift_highm_invariants_rows.tex").write_text("\n".join(out_rows), encoding="utf-8")
    print("Wrote sections/generated/label_lift_highm_invariants_rows.tex")


if __name__ == "__main__":
    main()


