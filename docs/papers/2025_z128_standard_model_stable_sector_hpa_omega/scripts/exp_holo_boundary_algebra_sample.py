# -*- coding: utf-8 -*-
"""
Boundary algebra sample (deterministic, standard-library only).

This is an audit artifact: it instantiates a tiny screen-region family and
records monotonicity-compatible summaries (site count and protocol capacity),
serving as a reproducible companion to the isotony statement in Appendix 10f.

Outputs (LaTeX fragments):
  - sections/generated/holo_boundary_algebra_sample_rows.tex
  - sections/generated/holo_boundary_algebra_sample_summary.tex
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines


@dataclass(frozen=True)
class RegionRow:
    name: str
    sites: int
    i_prot_bits: int
    included_in: str


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "holo_boundary_algebra_sample_rows.tex"
    sum_path = out_dir / "holo_boundary_algebra_sample_summary.tex"

    # Deterministic anchor conventions.
    m = 6
    n = 3

    # Region chain by site counts; inclusion is by construction (R1 ⊂ R2 ⊂ R3 ⊂ R4).
    chain: List[Tuple[str, int]] = [("R_1", 1), ("R_2", 4), ("R_3", 16), ("R_4", 64)]

    rows: List[str] = []
    prev_name = "-"
    for name, sites in chain:
        i_prot = int(m) * int(sites)
        rows.append(
            " & ".join([name, str(int(sites)), str(int(i_prot)), prev_name]) + r" \\"
        )
        prev_name = name
    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])

    summary = [
        r"\paragraph{Boundary-region sample (audit).} \AuditTag "
        + r"This fragment instantiates a nested region chain by site counts (R$_1\subset$R$_2\subset$R$_3\subset$R$_4$) "
        + r"at anchor (m,n)=("
        + str(m)
        + ","
        + str(n)
        + r"). The protocol capacity $I_{\mathrm{prot}}(m,n;R)=m|R|$ is monotone along the chain, "
        + r"consistent with isotony of the associated boundary algebras (Appendix~\ref{app:holo_boundary_algebra_from_screens}).",
    ]
    write_lines(sum_path, summary)


if __name__ == "__main__":
    main()

