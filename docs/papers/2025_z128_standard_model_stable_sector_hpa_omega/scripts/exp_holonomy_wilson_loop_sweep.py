# -*- coding: utf-8 -*-
"""
Wilson-loop style diagnostics for loop-scale phase-lifted holonomies (toy).

For each k×k square loop on the n=3 (8×8) grid (k=1..7), we compute the phase-lifted
4×4 unitary holonomy around the loop (denom=64), project to the 3D sum-zero subspace,
renormalize to an effective 3×3 unitary Q, and evaluate Wilson-loop style scalars:

  W := Re(tr(Q))/3,
  A := 1 - W.

We summarize these quantities over the nontrivial 3/4-cycle subset, per k.

Outputs (LaTeX fragment):
  - sections/generated/holonomy_wilson_loop_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import exp_holonomy_loops as holo
import exp_holonomy_loop_scale_sweep as ls
import exp_holonomy_phase_lift_cp_invariant as ph
from common_tex import write_lines


def mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else float("nan")


def main() -> None:
    ks = list(range(1, 8))
    denom = 64

    labels = holo.grid_labels(n_bits=3)
    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)
    B = ph.basis_B()

    rows: List[str] = []
    for k in ks:
        Ws: List[float] = []
        As: List[float] = []
        cnt = 0
        max_xy = 8 - k - 1
        for x in range(max_xy + 1):
            for y in range(max_xy + 1):
                # Build holonomy permutation to filter to 3/4 cycles.
                hol_p = (0, 1, 2, 3)
                H = [[1.0 + 0j if i == j else 0j for j in range(4)] for i in range(4)]
                for a, b in ls.loop_edges_square(x, y, k=k):
                    p_ab = edge_p[(a, b)]
                    hol_p = holo.compose(p_ab, hol_p)
                    U_ab = ph.edge_unitary_with_denom(a, b, labels, pre, edge_p, denom=denom, map_name="id", bits=6)
                    H = ph.matmul(U_ab, H)
                ct = holo.cycle_type(hol_p)
                if ct not in ("3", "4"):
                    continue

                M3 = ph.project_3x3(H, B=B)
                Q = ph.gram_schmidt_unitary(M3)
                if Q is None:
                    continue
                tr = (Q[0][0] + Q[1][1] + Q[2][2]).real
                W = tr / 3.0
                A = 1.0 - W
                Ws.append(W)
                As.append(A)
                cnt += 1

        if cnt == 0:
            rows.append(f"{k} & 0 & $-$ & $-$ & $-$ & $-$ \\\\")
        else:
            rows.append(f"{k} & {cnt} & {mean(Ws):.6g} & {min(Ws):.6g} & {max(Ws):.6g} & {mean(As):.6g} \\\\")

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_wilson_loop_rows.tex", rows)
    print("Wrote sections/generated/holonomy_wilson_loop_rows.tex")


if __name__ == "__main__":
    main()


