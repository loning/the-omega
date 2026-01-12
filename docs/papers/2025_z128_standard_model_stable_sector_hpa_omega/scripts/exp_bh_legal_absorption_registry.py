# -*- coding: utf-8 -*-
"""
BH4 auxiliary audit: registry of self-consistent 'legal absorption' mechanism candidates.

Goal:
  Record multiple internally consistent routes that justify a restricted absorption subalphabet
  (e.g. cyclic-only or avoid_delim/esc) in the protocol language, without choosing among them.
  Selection is deferred to rigidity certificates (RB-A/B/C/D) elsewhere in the paper.

Outputs:
  - sections/generated/bh_legal_absorption_registry_rows.tex
  - sections/generated/bh_legal_absorption_registry_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from typing import List

from common_paths import generated_dir
from common_tex import write_lines


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
    # Deterministic registry (text-only; no hidden parameters).
    rows: List[str] = []

    # Columns:
    #  id | legal set (Iface) | mechanism hook | where in paper | falsifiable failure point
    rows.append(
        " & ".join(
            [
                _escape_tex("BH-LA1"),
                _escape_tex("cyclic-only (trap types absorb; boundary types are exits)"),
                _escape_tex("leakage-kernel trap/exit channelization"),
                _escape_tex("app:leakage_kernel (m=6: 18 trap + 3 exit)"),
                _escape_tex("if boundary types must be absorbable in the same protocol class"),
            ]
        )
        + r" \\"
    )
    rows.append(
        " & ".join(
            [
                _escape_tex("BH-LA2"),
                _escape_tex(r"avoid\{delim,esc\} (reserve rare labels for framing)"),
                _escape_tex("self-delimiting record design (protocol framing)"),
                _escape_tex("app:bh_page_surrogate (legal absorption subalphabet)"),
                _escape_tex("if framing labels appear frequently in empirical record without any pullback"),
            ]
        )
        + r" \\"
    )
    rows.append(
        " & ".join(
            [
                _escape_tex("BH-LA3"),
                _escape_tex("cyclic-only (emergent)"),
                _escape_tex("delay/overhead threshold: only high-delay traps effectively capture"),
                _escape_tex("app:protocol_horizon_tick_trap + app:leakage_kernel"),
                _escape_tex("if low-delay/boundary-like channels exhibit comparable capture cross-section"),
            ]
        )
        + r" \\"
    )
    rows.append(
        " & ".join(
            [
                _escape_tex("BH-LA4"),
                _escape_tex("kernel-weighted selection (K-dependent absorbability)"),
                _escape_tex("kernel family K filters which outcomes become stable in readout"),
                _escape_tex("app:kernel_family_cap_closure + app:cap_audit_template"),
                _escape_tex("if claimed K-robust while absorbability strongly varies across admissible K"),
            ]
        )
        + r" \\"
    )
    rows.append(r"\bottomrule")

    write_lines(generated_dir() / "bh_legal_absorption_registry_rows.tex", rows)

    summary = [
        r"\paragraph{Legal absorption registry (audit; no selection).} \AuditTag "
        r"This fragment records multiple self-consistent candidates that justify a restricted absorption subalphabet "
        r"in the protocol language (e.g.\ cyclic-only absorption or reserved-label avoidance for framing). "
        r"No choice is made here; candidate selection is deferred to rigidity certificates (RB-A/B/C/D) and to "
        r"explicit failure-point audits.",
    ]
    write_lines(generated_dir() / "bh_legal_absorption_registry_summary.tex", summary)

    print("Wrote sections/generated/bh_legal_absorption_registry_rows.tex")
    print("Wrote sections/generated/bh_legal_absorption_registry_summary.tex")


if __name__ == "__main__":
    main()

