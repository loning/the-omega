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


def main() -> None:
    # Deterministic registry (text-only; no hidden parameters).
    rows: List[str] = []

    # Columns:
    #  id | legal set (Iface) | mechanism hook | where in paper | falsifiable failure point
    rows.append(
        "BH-LA1"
        " & cyclic-only (trap types absorb; boundary types are exits)"
        " & leakage-kernel trap/exit channelization"
        " & app:leakage_kernel (m=6: 18 trap + 3 exit)"
        " & if boundary types must be absorbable in the same protocol class"
        r" \\"
    )
    rows.append(
        "BH-LA2"
        " & avoid\\\\{delim,esc\\\\} (reserve rare labels for framing)"
        " & self-delimiting record design (protocol framing)"
        " & app:bh_page_surrogate (legal absorption subalphabet)"
        " & if framing labels appear frequently in empirical record without any pullback"
        r" \\"
    )
    rows.append(
        "BH-LA3"
        " & cyclic-only (emergent)"
        " & delay/overhead threshold: only high-delay traps effectively capture"
        " & app:protocol_horizon_tick_trap + app:leakage_kernel"
        " & if low-delay/boundary-like channels exhibit comparable capture cross-section"
        r" \\"
    )
    rows.append(
        "BH-LA4"
        " & kernel-weighted selection (K-dependent absorbability)"
        " & kernel family K filters which outcomes become stable in readout"
        " & app:kernel_family_cap_closure + app:cap_audit_template"
        " & if claimed K-robust while absorbability strongly varies across admissible K"
        r" \\"
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

