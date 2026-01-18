# -*- coding: utf-8 -*-
"""
Leakage-kernel demo (audit generator).

Outputs (LaTeX fragments):
  - sections/generated/leakage_kernel_demo_rows.tex

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
class DemoFamily:
    family_id: str
    gamma: float  # rate proxy (1/time)
    note: str


def _candidate_families() -> Sequence[DemoFamily]:
    # Declared finite family for illustration.
    return [
        DemoFamily("exp_fast", 1.0, "exponential; high leakage"),
        DemoFamily("exp_mid", 0.1, "exponential; mid leakage"),
        DemoFamily("exp_slow", 0.01, "exponential; low leakage"),
    ]


def _cap_select(fams: Sequence[DemoFamily]) -> DemoFamily:
    # Deterministic CAP-like rule for the demo:
    #   minimize (gamma, description_length, family_id)
    best = None
    for f in fams:
        key = (float(f.gamma), int(len(f.note)), f.family_id)
        if best is None or key < best[0]:
            best = (key, f)
    assert best is not None
    return best[1]


def _fmt(x: float, digits: int = 6) -> str:
    return f"{float(x):.{int(digits)}f}"


def main() -> None:
    fams = list(_candidate_families())
    chosen = _cap_select(fams)

    lines: List[str] = []
    for f in fams:
        family_id_tex = f.family_id.replace("_", r"\_")
        gamma = float(f.gamma)
        tau = 1.0 / gamma if gamma > 0.0 else float("inf")
        note = f.note
        if f.family_id == chosen.family_id:
            note = note + "; CAP-selected"
        lines.append(
            " & ".join([family_id_tex, _fmt(gamma, 6), _fmt(tau, 6), note]) + r" \\"
        )

    write_lines(
        generated_dir() / "leakage_kernel_demo_rows.tex", lines if lines else ["% (no rows)"]
    )


if __name__ == "__main__":
    main()

