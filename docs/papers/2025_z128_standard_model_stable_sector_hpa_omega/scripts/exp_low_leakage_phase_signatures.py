# -*- coding: utf-8 -*-
"""
Protected low-leakage phase signature rows (audit generator).

Outputs (LaTeX fragments):
  - sections/generated/low_leakage_phase_rows.tex
  - sections/generated/low_leakage_phase_summary.tex

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from common_paths import generated_dir
from common_tex import write_lines


@dataclass(frozen=True)
class SigRow:
    obj: str
    tau_ws: float
    gamma: float


def _fmt(x: float, digits: int = 6) -> str:
    return f"{float(x):.{int(digits)}f}"


def _rows() -> Sequence[SigRow]:
    # Declared finite comparison family (illustration; not a premise).
    return [
        SigRow("Higgs-like", tau_ws=1.0, gamma=1.0e6),
        SigRow("Proton-like", tau_ws=1.0e6, gamma=1.0e-6),
        SigRow("BH-like", tau_ws=1.0e9, gamma=1.0e-12),
    ]


def main() -> None:
    rows = list(_rows())
    gamma_ref = 1.0e-3

    lines: List[str] = []
    for r in rows:
        verdict = "low-leakage" if float(r.gamma) < gamma_ref else "not-low-leakage"
        lines.append(
            " & ".join([r.obj, _fmt(r.tau_ws, 3), _fmt(r.gamma, 6), verdict]) + r" \\"
        )

    write_lines(
        generated_dir() / "low_leakage_phase_rows.tex", lines if lines else ["% (no rows)"]
    )

    summary = [
        r"\paragraph{Audit summary (low-leakage phase signatures).} \AuditTag "
        r"Rows are a deterministic illustration in a finite comparison family. "
        rf"The reference threshold is set to $\Gamma_{{\mathrm{{ref}}}}={_fmt(gamma_ref, 6)}$ (proxy units). "
        r"A row is tagged \texttt{low-leakage} iff $\Gamma<\Gamma_{\mathrm{ref}}$.",
    ]
    write_lines(generated_dir() / "low_leakage_phase_summary.tex", summary)


if __name__ == "__main__":
    main()

