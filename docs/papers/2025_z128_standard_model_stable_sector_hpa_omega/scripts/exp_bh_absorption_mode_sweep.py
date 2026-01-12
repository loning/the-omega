# -*- coding: utf-8 -*-
"""
BH5/BH4 auxiliary audit: absorption-mode sweep for the black-hole-equivalent queue model.

We compare several protocol-level "legal absorption" modes at fixed m:
  - unrestricted
  - avoid_delim_esc
  - cyclic_only   (preferred BH-like analogue: trap states absorb; boundary states serve as exits)
  - boundary_only

We report:
  - whether decoding succeeds (unitarity in the CS model)
  - escaping overhead (framing cost) and record length

Outputs:
  - sections/generated/bh_absorption_mode_sweep_rows.tex
  - sections/generated/bh_absorption_mode_sweep_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from typing import List

from common_paths import generated_dir
from common_tex import write_lines

import exp_black_hole_queue_equivalence as bhq


def _escape_tex(s: str) -> str:
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("#", "\\#")
        .replace("_", "\\_")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("^", "\\^{}")
        .replace("~", "\\~{}")
    )


def main() -> None:
    m = 6
    base_vacuum_mass = 64
    msg_text = "TICK-INFORMATION"

    modes = ["unrestricted", "avoid_delim_esc", "cyclic_only", "boundary_only"]

    rows: List[str] = []
    for mode in modes:
        r = bhq._run_case(m=m, base_vacuum_mass=base_vacuum_mass, msg_text=msg_text, mode=mode)
        rows.append(
            " & ".join(
                [
                    _escape_tex(r["mode"]),
                    r["allowed_card"],
                    r["t"],
                    r["digit_base"],
                    r["needs_escape"],
                    r["escape_extra"],
                    r["radiation_ticks"],
                    r["ok"],
                ]
            )
            + r" \\"
        )
    rows.append(r"\bottomrule")
    write_lines(generated_dir() / "bh_absorption_mode_sweep_rows.tex", rows)

    summary = [
        r"\paragraph{Absorption-mode sweep (audit).} \AuditTag "
        r"This fragment compares several protocol-level absorption modes for the black-hole-equivalent queue model "
        r"at the anchor $m=6$. "
        r"The preferred BH-like analogue is \texttt{cyclic\_only}: only cyclic/trap types are absorbable, while "
        r"boundary types serve as distinguished exit-channel symbols. "
        r"The table reports whether exact recovery succeeds, along with framing (escaping) overhead and record length.",
    ]
    write_lines(generated_dir() / "bh_absorption_mode_sweep_summary.tex", summary)

    print("Wrote sections/generated/bh_absorption_mode_sweep_rows.tex")
    print("Wrote sections/generated/bh_absorption_mode_sweep_summary.tex")


if __name__ == "__main__":
    main()

