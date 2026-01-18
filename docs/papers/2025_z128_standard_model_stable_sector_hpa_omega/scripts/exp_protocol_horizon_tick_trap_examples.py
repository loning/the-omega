# -*- coding: utf-8 -*-
"""
Protocol horizon / relative black-hole criterion (audit illustration).

Outputs (LaTeX fragments):
  - sections/generated/protocol_horizon_examples_rows.tex
  - sections/generated/protocol_horizon_examples_summary.tex

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

from common_paths import generated_dir
from common_tex import write_lines


def _i_prot_bits(m: int, n: int) -> int:
    return int(m) * (4 ** int(n))


@dataclass(frozen=True)
class ExampleRow:
    obj: str
    i_obs: int
    i_prot: int
    verdict: str


def _verdict(i_obs: int, m: int, n: int) -> str:
    ip = _i_prot_bits(m, n)
    # Audit convention for this illustration:
    # if internal capacity exceeds observer budget by a wide margin, treat as horizon-like.
    if ip >= 16 * int(i_obs):
        return rf"black-hole-like; $(m,n)=({m},{n})$"
    if ip <= int(i_obs) // 2:
        return rf"resolvable; $(m,n)=({m},{n})$"
    return rf"marginal; $(m,n)=({m},{n})$"


def _examples() -> List[ExampleRow]:
    # Declared finite comparison family.
    objects: Sequence[Tuple[str, Tuple[int, int]]] = [
        ("Higgs-like", (6, 3)),
        ("Proton-like", (10, 4)),
        ("BH-like", (16, 6)),
    ]
    budgets: Sequence[int] = [
        64,
        1_024,
        1_000_000,
    ]
    rows: List[ExampleRow] = []
    for obj, (m, n) in objects:
        ip = _i_prot_bits(m, n)
        for i_obs in budgets:
            rows.append(
                ExampleRow(
                    obj=obj,
                    i_obs=int(i_obs),
                    i_prot=int(ip),
                    verdict=_verdict(int(i_obs), int(m), int(n)),
                )
            )
    return rows


def _write_rows(rows: Sequence[ExampleRow]) -> None:
    lines: List[str] = []
    for r in rows:
        lines.append(
            " & ".join([r.obj, str(int(r.i_obs)), str(int(r.i_prot)), r.verdict]) + r" \\"
        )
    write_lines(
        generated_dir() / "protocol_horizon_examples_rows.tex",
        lines if lines else ["% (no rows)"],
    )


def _write_summary() -> None:
    budgets = "64, 1024, 1000000"
    lines = [
        r"\paragraph{Audit summary (protocol horizon illustration).} \AuditTag "
        r"Rows are a deterministic illustration only. "
        rf"Comparison family: budgets $I_{{\mathrm{{obs}}}}\in\{{{budgets}\}}$ (bits) "
        r"and objects mapped to fixed protocol resolutions. "
        r"The verdict uses a declared margin rule: "
        r"\texttt{black-hole-like} iff $I_{\mathrm{prot}}(m,n)\ge 16\,I_{\mathrm{obs}}$, "
        r"\texttt{resolvable} iff $I_{\mathrm{prot}}(m,n)\le I_{\mathrm{obs}}/2$, "
        r"otherwise \texttt{marginal}.",
    ]
    write_lines(generated_dir() / "protocol_horizon_examples_summary.tex", lines)


def main() -> None:
    rows = _examples()
    _write_rows(rows)
    _write_summary()


if __name__ == "__main__":
    main()

