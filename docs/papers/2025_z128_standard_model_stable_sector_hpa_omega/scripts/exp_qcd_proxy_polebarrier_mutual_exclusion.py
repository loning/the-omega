#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proxy <-> pole-barrier consistency loop (audit-only).

Reads existing generated outputs:
  - sections/generated/qcd_confinement_proxy_summary.tex
  - sections/generated/qcd_confinement_pade_pole_rows.tex

Writes:
  - sections/generated/qcd_proxy_polebarrier_failure_rows.tex
  - sections/generated/qcd_proxy_polebarrier_failure_summary.tex

This is an audit-facing classifier that makes the "consistency bridge" explicit.
It does not upgrade confinement/mass-gap status.

Only the Python standard library is used.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

from common_tex import write_lines


def _parse_proxy_sigma_mu(summary_tex: str) -> Tuple[Optional[float], Optional[float]]:
    # Expect fragments like: \widehat\sigma=0, \widehat\mu=0.384615
    m1 = re.search(r"\\widehat\\sigma=([0-9eE+\-\.]+)", summary_tex)
    m2 = re.search(r"\\widehat\\mu=([0-9eE+\-\.]+)", summary_tex)
    sigma = float(m1.group(1)) if m1 else None
    mu = float(m2.group(1)) if m2 else None
    return sigma, mu


def _parse_pade_rows(rows_tex: str) -> Tuple[Optional[float], bool, int]:
    """
    Return (min_abs_root_over_rows, any_inside, total_inside_count).
    Skips rows with $-$.
    """
    min_abs: Optional[float] = None
    any_inside = False
    total_inside = 0
    for raw in rows_tex.splitlines():
        line = raw.strip()
        if not line or line.startswith("%") or "bottomrule" in line:
            continue
        if "&" not in line:
            continue
        parts = [p.strip() for p in line.split("&")]
        if len(parts) < 4:
            continue
        min_abs_s = parts[2].strip()
        inside_s = parts[3].replace("\\\\", "").strip()
        if "$-$" in min_abs_s or "-" == min_abs_s:
            continue
        try:
            v = float(min_abs_s)
            inside = int(inside_s.strip("$"))
        except Exception:
            continue
        if min_abs is None or v < min_abs:
            min_abs = v
        if inside > 0:
            any_inside = True
            total_inside += inside
    return min_abs, any_inside, total_inside


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    gen = root / "sections" / "generated"

    proxy_sum_p = gen / "qcd_confinement_proxy_summary.tex"
    pade_rows_p = gen / "qcd_confinement_pade_pole_rows.tex"
    if not proxy_sum_p.is_file() or not pade_rows_p.is_file():
        raise FileNotFoundError("Missing required generated inputs for QCD proxy<->pole loop.")

    sigma, mu = _parse_proxy_sigma_mu(proxy_sum_p.read_text(encoding="utf-8"))
    min_abs, any_inside, total_inside = _parse_pade_rows(pade_rows_p.read_text(encoding="utf-8"))

    # Bounded boolean gates (audit-facing, not theorem-level).
    area_signal = (sigma is not None) and (sigma > 0.0)
    pole_barrier_pass = (not any_inside)

    verdict = "undetermined"
    if area_signal and any_inside:
        verdict = "conflict(area_signal_vs_interior_poles)"
    elif area_signal and pole_barrier_pass:
        verdict = "gate_pass(area_signal_and_no_interior_poles)"
    elif (not area_signal) and any_inside:
        verdict = "nonconfining_proxy_but_interior_poles_present"
    elif (not area_signal) and pole_barrier_pass:
        verdict = "nonconfining_proxy_and_no_interior_poles"

    rows: List[str] = []
    rows.append(
        " & ".join(
            [
                f"{sigma if sigma is not None else 'nan'}",
                f"{mu if mu is not None else 'nan'}",
                ("yes" if area_signal else "no"),
                (f"{min_abs:.6g}" if min_abs is not None else "$-$"),
                ("yes" if any_inside else "no"),
                str(int(total_inside)),
                verdict.replace("_", r"\_"),
            ]
        )
        + r" \\"
    )

    write_lines(gen / "qcd_proxy_polebarrier_failure_rows.tex", rows)
    write_lines(
        gen / "qcd_proxy_polebarrier_failure_summary.tex",
        [
            r"\paragraph{Audit summary (proxy $\leftrightarrow$ pole-barrier consistency loop).} \AuditTag "
            + r"We compute two bounded diagnostics on the same finite Wilson-loop magnitudes: "
            + r"(i) an area/perimeter proxy fit with selected $(\widehat\sigma,\widehat\mu)$, and "
            + r"(ii) a Pad\'e pole-barrier sweep counting interior-unit-disk denominator roots. "
            + r"We report a boolean gate summary and a conflict/consistency label without upgrading confinement or mass-gap status.",
        ],
    )

    print("Wrote sections/generated/qcd_proxy_polebarrier_failure_rows.tex")
    print("Wrote sections/generated/qcd_proxy_polebarrier_failure_summary.tex")


if __name__ == "__main__":
    main()

