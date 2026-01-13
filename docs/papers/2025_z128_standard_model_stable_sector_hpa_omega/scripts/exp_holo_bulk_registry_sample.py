# -*- coding: utf-8 -*-
"""
Bulk reportables registry sample (deterministic, standard-library only).

This script emits a compact, reproducible table that mirrors Appendix 10g's
bulk registry list as an auditable artifact.

Outputs (LaTeX fragments):
  - sections/generated/holo_bulk_registry_sample_rows.tex
  - sections/generated/holo_bulk_registry_sample_summary.tex
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from common_paths import generated_dir
from common_tex import write_lines


@dataclass(frozen=True)
class Item:
    name: str
    pointer: str
    layer: str


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "holo_bulk_registry_sample_rows.tex"
    sum_path = out_dir / "holo_bulk_registry_sample_summary.tex"

    items: List[Item] = [
        Item(
            name=r"Weak-field proxies from $\chi$ (including $\widehat G_{00,h}$)",
            pointer=r"Appendices~\ref{app:overhead_to_gravity_closure}, \ref{app:weak_field_curvature_from_chi}",
            layer="PT/Iface",
        ),
        Item(
            name=r"Determinant/trace/pressure certificates (pole barrier, pressure)",
            pointer=r"Section~\ref{sec:rigidity_bridge_spine}; Appendix~\ref{app:operator_mother_space}",
            layer="Audit/Iface",
        ),
        Item(
            name=r"Protocol capacity $I_{\mathrm{prot}}(m,n)=m4^n$ and uplift staging",
            pointer=r"Appendix~\ref{app:resolution_uplift_fusion_horizon_unification}",
            layer="CAP/Iface",
        ),
        Item(
            name=r"BH boundary capacity calibration hook (optional matching)",
            pointer=r"Appendix~\ref{app:bh_planck_capacity_calibration}",
            layer="Match/Audit",
        ),
        Item(
            name=r"Record-algebra recovery surrogates (Page/island toys)",
            pointer=r"Appendices~\ref{app:bh_page_surrogate}, \ref{app:bh_island_equiv}",
            layer="Audit",
        ),
    ]

    rows: List[str] = []
    for it in items:
        rows.append(
            " & ".join(
                [
                    it.name.replace("_", r"\_"),
                    it.layer.replace("_", r"\_"),
                    it.pointer.replace("_", r"\_"),
                ]
            )
            + r" \\"
        )
    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])

    summary = [
        r"\paragraph{Bulk reportables registry sample (audit).} \AuditTag "
        + r"This table is a deterministic, compact mirror of the bulk reportables registry used by the holographic dictionary "
        + r"(Appendix~\ref{app:holo_bulk_observables_registry}). It is not a complete ontology; it is a reportables list with evidence pointers.",
    ]
    write_lines(sum_path, summary)


if __name__ == "__main__":
    main()

