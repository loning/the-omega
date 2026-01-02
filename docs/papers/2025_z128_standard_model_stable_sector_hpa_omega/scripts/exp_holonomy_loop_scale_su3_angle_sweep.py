# -*- coding: utf-8 -*-
"""
Loop-scale sweep of SO(3)⊂SU(3) rotation angles for finite holonomy (k×k loops).

We reuse the deterministic S4 edge transport on the n=3 (8×8) Hilbert grid and
compute S4 holonomy permutations around k×k square loops for k=1..7.

Each holonomy permutation p∈S4 is mapped to a real 3×3 SO(3) matrix via the
sign-twisted standard representation (sum-zero subspace of R^4), as in
exp_holonomy_su3_representation.py. We then compute the associated rotation angle.

We summarize angles on the nontrivial 3/4-cycle subset, per loop size k.

Outputs (LaTeX fragment):
  - sections/generated/holonomy_loop_scale_su3_angle_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import exp_holonomy_loops as holo
import exp_holonomy_loop_scale_sweep as ls
import exp_holonomy_su3_representation as su3
from common_tex import write_lines


def mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else float("nan")


def main() -> None:
    ks = list(range(1, 8))

    labels = holo.grid_labels(n_bits=3)
    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)

    B = su3.basis_B()

    rows: List[str] = []
    for k in ks:
        angles: List[float] = []
        max_xy = 8 - k - 1
        for x in range(max_xy + 1):
            for y in range(max_xy + 1):
                hol_p = (0, 1, 2, 3)
                for a, b in ls.loop_edges_square(x, y, k=k):
                    p_ab = edge_p[(a, b)]
                    hol_p = holo.compose(p_ab, hol_p)
                ct = holo.cycle_type(hol_p)
                if ct not in ("3", "4"):
                    continue
                R = su3.su3_rep(hol_p, B=B)
                angles.append(su3.rotation_angle_deg(R))

        cnt = len(angles)
        if cnt == 0:
            rows.append(f"{k} & 0 & $-$ & $-$ & $-$ \\\\")
        else:
            rows.append(f"{k} & {cnt} & {mean(angles):.3f} & {min(angles):.3f} & {max(angles):.3f} \\\\")

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_loop_scale_su3_angle_rows.tex", rows)
    print("Wrote sections/generated/holonomy_loop_scale_su3_angle_rows.tex")


if __name__ == "__main__":
    main()


