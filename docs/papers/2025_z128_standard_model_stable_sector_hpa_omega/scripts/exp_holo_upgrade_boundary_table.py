# -*- coding: utf-8 -*-
"""
Toy evidence upgrade boundary table (deterministic, standard-library only).

This table enforces a manuscript-wide discipline:
  - Toy/audit artifacts are never premises for theorem-level claims.
  - PT carriers are explicitly limited to controlled subclasses.
  - CP/interface claims must carry explicit failure points and fallbacks.

Outputs (LaTeX fragments):
  - sections/generated/holo_upgrade_boundary_rows.tex
  - sections/generated/holo_upgrade_boundary_summary.tex
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from common_paths import generated_dir
from common_tex import write_lines


@dataclass(frozen=True)
class Row:
    evidence: str
    allowed_use: str
    forbidden_upgrade: str
    gates: str
    pointer: str


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "holo_upgrade_boundary_rows.tex"
    sum_path = out_dir / "holo_upgrade_boundary_summary.tex"

    rows: List[Row] = [
        Row(
            evidence="Toy record/queue audits (scattering vs BH saturation, Page surrogates)",
            allowed_use="Audit narrative alignment; reproducible artifacts; interface intuition only",
            forbidden_upgrade="Not a premise for holographic reconstruction theorems or physical duality claims",
            gates="S1; H0a/H0b/H0c; H4a/H4b",
            pointer=r"Appendix~\ref{app:scattering_bh_toy_equivalence_audits}",
        ),
        Row(
            evidence="Finite-dimensional PT carriers (net/isotony; tensor-product locality; erasure-QEC)",
            allowed_use="Theorem-facing claims inside the controlled subclass only",
            forbidden_upgrade="No claim of unrestricted bulk geometry duality or nonperturbative 4D S-matrix derivation",
            gates="R3; S1--S3; W1--W3",
            pointer=r"Appendices~\ref{app:holo_boundary_algebra_from_screens}, \ref{app:holo_reconstruction_surrogate}",
        ),
        Row(
            evidence="Matching-layer / CP interface dictionaries (units, schemes, thresholds, PBH hooks)",
            allowed_use="Windowed comparability statements with explicit envelopes and budgets",
            forbidden_upgrade="No promotion to PT without discharging the stated gates and budgets",
            gates="R1/R2; H0b",
            pointer=r"Appendices~\ref{app:scheme_invariance_audit_contract}, \ref{app:matching_envelope_theoremization}",
        ),
    ]

    def escape_cell_text(s: str) -> str:
        return s.replace("_", r"\_")

    tex_lines: List[str] = []
    for r in rows:
        tex_lines.append(
            " & ".join(
                [
                    escape_cell_text(r.evidence),
                    escape_cell_text(r.allowed_use),
                    escape_cell_text(r.forbidden_upgrade),
                    escape_cell_text(r.gates),
                    r.pointer,
                ]
            )
            + r" \\"
        )
    tex_lines.append(r"\bottomrule")

    write_lines(rows_path, tex_lines if tex_lines else ["% (no rows)"])

    summary = [
        r"\paragraph{Upgrade boundary (audit).} \AuditTag "
        + r"This registry fixes the rule: toy/audit artifacts support narrative alignment and falsifiability hooks, "
        + r"but are never premises for theorem-level holographic claims. PT statements must remain inside declared carriers; "
        + r"CP/interface statements must carry explicit failure-point gates and fallbacks.",
    ]
    write_lines(sum_path, summary)


if __name__ == "__main__":
    main()
