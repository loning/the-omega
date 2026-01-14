# -*- coding: utf-8 -*-
"""
Holographic reconstruction audit (deterministic, standard-library only).

This script does not attempt to compute QEC thresholds; it emits an audit-facing summary
that ties the manuscript's PT carrier (erasure-QEC in a tensor-product subclass) to the
declared failure points H0*/H4*.

Outputs (LaTeX fragments):
  - sections/generated/holo_reconstruction_surrogate_rows.tex
  - sections/generated/holo_reconstruction_surrogate_summary.tex
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from common_paths import generated_dir
from common_tex import write_lines


@dataclass(frozen=True)
class Row:
    item: str
    status: str
    pointer: str


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "holo_reconstruction_surrogate_rows.tex"
    sum_path = out_dir / "holo_reconstruction_surrogate_summary.tex"

    rows_data: List[Row] = [
        Row(
            item="Boundary algebra carrier (screen-induced net)",
            status="PT (construction + isotony)",
            pointer=r"Appendix~\ref{app:holo_boundary_algebra_from_screens}",
        ),
        Row(
            item="Tensor-product locality subclass",
            status="PT (microcausality by construction)",
            pointer=r"Appendix~\ref{app:protocol_subclass_tensor_net}",
        ),
        Row(
            item="Reconstruction as erasure-QEC (exact carrier)",
            status="PT (finite-dimensional theorem)",
            pointer=r"Appendix~\ref{app:holo_reconstruction_surrogate}",
        ),
        Row(
            item="Approximate reconstruction reporting",
            status="Iface/Audit (epsilon_N budget required)",
            pointer=r"Appendix~\ref{app:holo_scope_contract}",
        ),
        Row(
            item="Failure points for holography",
            status="Audit gatekeeping",
            pointer=r"Appendix~\ref{app:minimal_failure_point_templates} (H0a/H0b/H0c/H4a/H4b)",
        ),
    ]

    def escape_cell_text(s: str) -> str:
        return s.replace("_", r"\_")

    lines: List[str] = []
    for r in rows_data:
        lines.append(
            " & ".join(
                [
                    escape_cell_text(r.item),
                    escape_cell_text(r.status),
                    r.pointer,
                ]
            )
            + r" \\"
        )
    lines.append(r"\bottomrule")
    write_lines(rows_path, lines if lines else ["% (no rows)"])

    summary = [
        r"\paragraph{Holographic reconstruction carrier (audit).} \AuditTag "
        + r"The manuscript's theorem-facing reconstruction carrier is finite-dimensional erasure-QEC in the "
        + r"tensor-product locality subclass; any extension beyond this controlled subclass must be reported "
        + r"in the windowed error-budget format and is subject to the H0*/H4* failure-point gates.",
    ]
    write_lines(sum_path, summary)


if __name__ == "__main__":
    main()
