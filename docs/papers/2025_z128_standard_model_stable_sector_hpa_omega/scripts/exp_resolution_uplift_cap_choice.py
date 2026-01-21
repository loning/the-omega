# -*- coding: utf-8 -*-
"""
Deterministic generator: capacity-driven uplift choice under explicit (m,n) constraints.

Purpose:
  Provide a small, auditable table that instantiates the CAP key of
  Appendix `app:resolution_uplift_fusion_horizon_unification` on bounded families.

Outputs (LaTeX fragments):
  - sections/generated/resolution_uplift_cap_choice_rows.tex
  - sections/generated/resolution_uplift_cap_choice_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from common_paths import generated_dir
from common_tex import write_lines


@dataclass(frozen=True)
class Scenario:
    name: str
    m_family: Tuple[int, ...]
    n_family: Tuple[int, ...]


def _i_prot(m: int, n: int) -> int:
    if m <= 0 or n < 0:
        raise ValueError("m must be positive and n must be nonnegative")
    return m * (4**n)


def _cap_minimizer(m_family: Iterable[int], n_family: Iterable[int], i_tar: int) -> Tuple[int, int]:
    if i_tar <= 0:
        raise ValueError("i_tar must be positive")
    best = None
    for n in sorted(set(n_family)):
        for m in sorted(set(m_family)):
            feasible = _i_prot(m, n) >= i_tar
            key = (0 if feasible else 1, n, m)  # feasibility-first, then minimize (n,m)
            if best is None or key < best[0]:
                best = (key, (m, n))
    assert best is not None
    return best[1]


def _fmt_float(x: float) -> str:
    if math.isfinite(x):
        return f"{x:.6f}"
    return "nan"


def _tex_escape(s: str) -> str:
    # Minimal escape for LaTeX fragments used in tabular rows.
    return s.replace("_", r"\_")


def _scenarios() -> List[Scenario]:
    # Keep families aligned with other uplift/strong-field audit modules.
    base_m = (6, 8, 10, 12, 14, 16)
    base_n = (3, 4, 5, 6)
    return [
        Scenario(name="full", m_family=base_m, n_family=base_n),
        Scenario(name="n_blocked_3", m_family=base_m, n_family=(3,)),
        Scenario(name="m_blocked_6", m_family=(6,), n_family=base_n),
    ]


def _targets_bits() -> List[int]:
    # Use a small dyadic ladder relative to the anchor capacity I_prot(6,3)=384.
    i0 = _i_prot(6, 3)
    mult = [1, 2, 4, 8, 16, 32, 64, 128]
    return [i0 * k for k in mult]


def main() -> None:
    rows: List[str] = []
    for sc in _scenarios():
        for i_tar in _targets_bits():
            m_star, n_star = _cap_minimizer(sc.m_family, sc.n_family, i_tar=i_tar)
            i_star = _i_prot(m_star, n_star)
            feasible = "yes" if i_star >= i_tar else "no"
            delta = abs(math.log(i_star / i_tar)) if (i_tar > 0 and i_star > 0) else float("nan")
            rows.append(
                f"{_tex_escape(sc.name)} & {i_tar} & {m_star} & {n_star} & {i_star} & {feasible} & {_fmt_float(delta)} \\\\"
            )

    rows.append("\\bottomrule")
    write_lines(generated_dir() / "resolution_uplift_cap_choice_rows.tex", rows)

    summary = (
        "\\paragraph{Audit summary (capacity-driven uplift choice).} "
        "\\AuditTag For each declared constraint scenario and each target information demand "
        "$I_{\\mathrm{tar}}$ (bits), we apply the feasibility-first CAP key "
        "$K_{\\mathrm{cap}}=(1-f, n, m)$ over a bounded $(m,n)$ family "
        "(Appendix~\\ref{app:resolution_uplift_fusion_horizon_unification}) and report the selected minimizer "
        "$(m^\\ast,n^\\ast)$ and the achieved capacity $I_{\\mathrm{prot}}(m^\\ast,n^\\ast)$. "
        "The scenarios illustrate the discrete staging rule, including the regime "
        "\"$n$ blocked $\\Rightarrow$ $m$ expands\"."
    )
    write_lines(generated_dir() / "resolution_uplift_cap_choice_summary.tex", [summary])

    print("Wrote sections/generated/resolution_uplift_cap_choice_rows.tex")
    print("Wrote sections/generated/resolution_uplift_cap_choice_summary.tex")


if __name__ == "__main__":
    main()

