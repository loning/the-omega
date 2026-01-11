# -*- coding: utf-8 -*-
"""
Deterministic generator: budget-triggered chi-horizon occupancy (capacity-only table).

Purpose:
  Provide a reproducible, protocol-native summary of the minimal cloud occupancy
  required to trigger a budget-defined chi-horizon at resolution (m,n).

This is intentionally capacity-only:
  - It does NOT assume a concrete distribution of chi(x).
  - It reports the minimal required number of cloud sites |R_*| to satisfy
        I_chi = m * |R_*| >= c * I_obs
    together with the implied occupancy fraction |R_*| / 4^n.

Outputs (LaTeX fragments):
  - sections/generated/chi_horizon_budget_occupancy_rows.tex
  - sections/generated/chi_horizon_budget_occupancy_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from common_paths import generated_dir
from common_tex import write_lines


@dataclass(frozen=True)
class Case:
    m: int
    n: int
    i_obs_bits: int
    c: int


def _ceil_div(a: int, b: int) -> int:
    if b <= 0:
        raise ValueError("b must be positive")
    return (a + b - 1) // b


def _fmt_frac(x: float) -> str:
    # Keep it compact; this is an audit table, not a high-precision numeric target.
    if x >= 1.0:
        return "1"
    if x <= 0.0:
        return "0"
    return f"{x:.6f}"


def _cases() -> List[Case]:
    # Keep it small and auditable: same bounded candidate family style as other tables.
    mn_family: List[Tuple[int, int]] = [(6, 3), (8, 4), (10, 5), (12, 6)]
    budgets: List[int] = [64, 1024, 1_000_000]
    margins: List[int] = [16]
    out: List[Case] = []
    for (m, n) in mn_family:
        for i_obs in budgets:
            for c in margins:
                out.append(Case(m=m, n=n, i_obs_bits=i_obs, c=c))
    return out


def main() -> None:
    rows: List[str] = []
    for cs in _cases():
        total_sites = 4 ** cs.n
        required_sites = _ceil_div(cs.c * cs.i_obs_bits, cs.m)
        required_sites_capped = min(required_sites, total_sites)
        i_chi = cs.m * required_sites_capped
        frac = float(required_sites_capped) / float(total_sites)
        feasible = "yes" if required_sites <= total_sites else "no"

        rows.append(
            f"{cs.m} & {cs.n} & {total_sites} & {cs.i_obs_bits} & {cs.c} & "
            f"{required_sites} & {required_sites_capped} & {i_chi} & {feasible} & {_fmt_frac(frac)} \\\\"
        )

    rows.append("\\bottomrule")

    write_lines(generated_dir() / "chi_horizon_budget_occupancy_rows.tex", rows)

    summary = (
        "\\paragraph{Audit summary (budget-triggered cloud occupancy).} "
        "\\AuditTag This table is capacity-only and deterministic. "
        "For each $(m,n)$ and observer budget $I_{\\mathrm{obs}}$ (bits), "
        "it reports the minimal required cloud-site count $|\\mathcal R_\\star|$ such that "
        "$I_{\\chi}=m|\\mathcal R_\\star|\\ge c\\,I_{\\mathrm{obs}}$, "
        "together with the implied occupancy fraction $|\\mathcal R_\\star|/4^n$. "
        "If the required site count exceeds $4^n$, the budget-trigger criterion is infeasible at that resolution."
    )
    write_lines(generated_dir() / "chi_horizon_budget_occupancy_summary.tex", [summary])

    print("Wrote sections/generated/chi_horizon_budget_occupancy_rows.tex")
    print("Wrote sections/generated/chi_horizon_budget_occupancy_summary.tex")


if __name__ == "__main__":
    main()

