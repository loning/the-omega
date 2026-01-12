# -*- coding: utf-8 -*-
"""
Generate a compact failure-point registry table as a LaTeX fragment.

This script is deterministic and uses only the Python standard library.
"""

from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class FailurePoint:
    code: str
    trigger: str
    check: str
    impact: str
    fallback: str


def main() -> None:
    fps = [
        FailurePoint(
            code="W1",
            trigger="No common invariant domain for unbounded generators",
            check="Verify existence/stability of a dense domain D for declared operators",
            impact="Wightman<->net maps ill-defined at stated regularity",
            fallback="Remain in bounded-algebra net/state bookkeeping",
        ),
        FailurePoint(
            code="W2",
            trigger="No generating fields in declared class",
            check="Audit generator existence + energy/regularity bounds",
            impact="net→field reconstruction not usable theorem-level",
            fallback="Treat field statements as interface/matching only",
        ),
        FailurePoint(
            code="W3",
            trigger="Locality notion mismatch (graded/braided vs commutative)",
            check="Declare correct locality variant and encode consistently",
            impact="Microcausality identification must be re-ledgered",
            fallback="Keep locality as explicit interface pack",
        ),
        FailurePoint(
            code="S1",
            trigger="S(omega) not (approximately) unitary on declared band",
            check="Calibrate losses/instability; audit unitarity window",
            impact="Wigner-Smith delay becomes proxy with loss error",
            fallback="Use operational delay dictionary only",
        ),
        FailurePoint(
            code="S2",
            trigger="No isolated stable one-particle sector / mass gap",
            check="Audit spectral isolation vs thresholds in window",
            impact="Haag-Ruelle/LSZ interpretation fails",
            fallback="No particle-channel claims; keep AQFT bookkeeping",
        ),
        FailurePoint(
            code="S3",
            trigger="Asymptotic completeness unknown/false",
            check="Declare as hypothesis or restrict to gapped subsector",
            impact="S not a complete channel map",
            fallback="Treat S as effective interface object",
        ),
        FailurePoint(
            code="R1",
            trigger="Scheme dependence shifts numerical parameters",
            check="Use bounded scheme family; report sensitivity envelope",
            impact="Numeric matching becomes scheme-family dependent",
            fallback="Restrict to scheme-invariant relations/envelopes",
        ),
        FailurePoint(
            code="R2",
            trigger="Threshold conventions alter effective content",
            check="Declare finite threshold family; audit variations",
            impact="Running/beta-based claims become family-dependent",
            fallback="Keep only family-invariant comparisons",
        ),
        FailurePoint(
            code="R3",
            trigger="Nonperturbative control required (4D existence, mass gap, etc.)",
            check="Mark as open/conditional; provide falsifiability hooks",
            impact="Strong-closure claim cannot be asserted",
            fallback="Revert to proxy/audit-level statements",
        ),
        FailurePoint(
            code="CL1",
            trigger="Refinement incompatibility across scales (no directed family)",
            check="Declare refinement maps and verify/bound compatibility on chain",
            impact="No theorem-level continuum limit object can be claimed",
            fallback="Keep holonomy outputs as finite diagnostics only",
        ),
        FailurePoint(
            code="CL2",
            trigger="No stable loop-scale→length map (a) for small-loop expansions",
            check="Declare bounded scale-map family and audit sensitivity",
            impact="Wilson small-plaquette expansion not usable for identification",
            fallback="Restrict to dimensionless loop diagnostics / representative only",
        ),
        FailurePoint(
            code="CL3",
            trigger="Insufficient regularity/energy bounds for small-loop expansion",
            check="Verify regularity/energy-bound bundle or restrict to smooth subsector",
            impact="Curvature/action-density proxy identification fails theorem-level",
            fallback="Downgrade to proxy-level semantics with explicit budgets",
        ),
        FailurePoint(
            code="CL4",
            trigger="No variational convergence (Gamma-limit) connecting discrete to continuum action",
            check="Provide Gamma-convergence (or equivalent) theorem under stated conditions",
            impact="Continuum Euler–Lagrange cannot be claimed as limit of discrete minimizers",
            fallback="Keep continuum YM as CAP-selected representative only",
        ),
        FailurePoint(
            code="WBR1",
            trigger="Regulator/scheme breaks BRST",
            check="Restore ST by admissible counterterms to declared order",
            impact="Ward/BRST not theorem-usable unless restored",
            fallback="Treat BRST as interface assumption + explicit budget",
        ),
        FailurePoint(
            code="WBR2",
            trigger="Gauge anomaly coefficients nonzero",
            check="Apply anomaly filters + cohomology obstruction test",
            impact="ST cannot be restored by local counterterms",
            fallback="Modify registry/scope; otherwise no strong gauge claim",
        ),
        FailurePoint(
            code="WBR3",
            trigger="Truncation leaves higher-order breaking",
            check="Encode remainder as explicit truncation budget term",
            impact="Ward/BRST holds only to stated order",
            fallback="Enlarge truncation or weaken identity scope",
        ),
    ]

    rows = []
    for fp in fps:
        rows.append(
            " & ".join(
                [
                    _escape_tex(fp.code),
                    _escape_tex(fp.trigger),
                    _escape_tex(fp.check),
                    _escape_tex(fp.fallback),
                ]
            )
            + r" \\"
        )

    out = generated_dir() / "failure_point_registry_rows.tex"
    write_lines(out, rows)


if __name__ == "__main__":
    main()

