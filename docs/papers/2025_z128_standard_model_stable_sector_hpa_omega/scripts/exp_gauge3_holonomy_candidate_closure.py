# -*- coding: utf-8 -*-
"""
Holonomy-driven candidate-family closure for M_gauge3 (bounded audit).

This script supports Appendix "Holonomy-driven candidate-family closure for the three-factor gauge identification".
It produces an explicit, reproducible certificate for the non-abelian factor choices used in the
channel-to-gauge interface closure:

  - A minimal non-abelian rotation-skeleton factor (H2 proxy): minimize dim(g).
  - A minimal genuinely complex 3x3 unitary factor (H3 proxy): minimize d_min (minimal faithful complex rep dim),
    excluding the SU(2) isomorphism class.

The bounded enumeration of compact simple factors is reused from exp_gauge_complexity_sensitivity.py.

Outputs:
  - sections/generated/gauge3_holonomy_candidate_closure_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from common_paths import generated_dir
from common_tex import write_lines

import exp_gauge_complexity_sensitivity as gcs


def main() -> None:
    max_dim = 80
    factors = gcs.enumerate_factors(max_dim=max_dim)
    if not factors:
        raise RuntimeError("Empty factor list.")

    # (H2 proxy) Minimal non-abelian rotation skeleton: minimize dim(g), tie-break by (rank, name).
    g_rot = min(factors, key=lambda g: (g.dim, g.rank, g.name))

    # (H3 proxy) Minimal genuinely complex 3x3 unitary sector:
    # minimize d_min among factors not isomorphic to the rotation-skeleton minimizer.
    others = [g for g in factors if g.iso_id != g_rot.iso_id]
    if not others:
        raise RuntimeError("No admissible second-factor candidates.")
    g_mix = min(others, key=lambda g: (g.mfd, g.dim, g.rank, g.name))

    rows: list[str] = []

    # (H1) U(1) is forced by local rephasing; no search.
    rows.append(r"(H1) abelian rephasing sector & standard dictionary (no search) & forced & $U(1)$ \\")

    # (H2) Rotation skeleton from nontrivial 3/4-cycle holonomy.
    rows.append(
        rf"(H2) rotation skeleton ($3/4$-cycle support) & compact simple ($\dim\le {max_dim}$) & $\min\,\dim(\mathfrak{{g}})$ & ${g_rot.name}$ \\"
    )

    # (H3) Genuinely complex 3x3 unitary sector with CP-odd support.
    rows.append(
        rf"(H3) CP-odd $3\times 3$ unitary sector ($J\neq 0$) & compact simple ($\dim\le {max_dim}$), $\mathfrak{{g}}\not\cong \mathfrak{{su}}(2)$ & $\min\, d_{{\min}}$ & ${g_mix.name}$ \\"
    )

    rows.append(r"\bottomrule")

    out_path = generated_dir() / "gauge3_holonomy_candidate_closure_rows.tex"
    write_lines(out_path, rows)
    print(f"Wrote {out_path} (max_dim={max_dim}, n_factors={len(factors)})")


if __name__ == "__main__":
    main()

