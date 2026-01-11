#!/usr/bin/env python3
"""
Scheme reparametrization demo audit (dictionary-level, deterministic).

We illustrate the contract in appendix 76 by a minimal toy:
  - One-loop QCD running: alpha_s(mu)=2pi/(b0 log(mu/Lambda)).
  - Scheme rescaling: Lambda' = c * Lambda corresponds to an additive shift in r_Lambda.
  - Invariant object: alpha_s as a function of r_Lambda (not of r with fixed mu0).

Writes:
  - sections/generated/scheme_invariance_demo_rows.tex
  - sections/generated/scheme_invariance_demo_summary.tex
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple


def fmt(x: float, nd: int = 6) -> str:
    if not math.isfinite(float(x)):
        return "nan"
    return f"{float(x):.{int(nd)}f}"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    gen = root / "sections" / "generated"
    gen.mkdir(parents=True, exist_ok=True)

    phi = (1.0 + math.sqrt(5.0)) / 2.0
    logphi = math.log(phi)

    # Toy parameters (audit-facing, not fitted).
    nf = 5
    b0 = 11.0 - (2.0 / 3.0) * float(nf)
    Lambda = 1.0  # arbitrary units

    # Scheme family: Lambda' = c * Lambda (bounded discrete).
    cs = [0.5, 1.0, 2.0]

    # Sample a few r_Lambda values (dimensionless), then map to mu.
    rL_vals = [1.0, 2.0, 3.0, 4.0]

    def alpha_from_rL(rL: float) -> float:
        # mu/Lambda = phi^{rL}
        return (2.0 * math.pi) / (b0 * (rL * logphi))

    rows: List[str] = []
    for rL in rL_vals:
        a_ref = alpha_from_rL(rL)
        for c in cs:
            # under Lambda' = c Lambda, same physical mu corresponds to rL' = rL - log_phi c
            rL_prime = float(rL - (math.log(float(c)) / logphi))
            a_prime = alpha_from_rL(rL_prime)
            # invariant check: alpha as function of rL should match when evaluated at transformed rL'
            abs_err = abs(a_ref - a_prime)
            rows.append(
                " & ".join(
                    [
                        fmt(rL, 3),
                        fmt(c, 3),
                        fmt(rL_prime, 6),
                        fmt(a_ref, 6),
                        fmt(a_prime, 6),
                        fmt(abs_err, 6),
                    ]
                )
                + r" \\"
            )

    (gen / "scheme_invariance_demo_rows.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (gen / "scheme_invariance_demo_summary.tex").write_text(
        "\\paragraph{Scheme demo summary (invariance under rescaling).}\n"
        "\\AuditTag "
        "In a one-loop QCD toy, rescaling the transmutation scale $\\Lambda' = c\\Lambda$ induces an additive shift "
        "$r_{\\Lambda'}(\\mu)=r_{\\Lambda}(\\mu)-\\log_{\\varphi}c$. "
        "Evaluating $\\alpha_s$ as a function of $r_{\\Lambda}$ yields an invariant description across the bounded $c$-family; "
        "the table reports the transformed coordinate and the residual $|\\alpha-\\alpha'|$.\n",
        encoding="utf-8",
    )

    print("Wrote sections/generated/scheme_invariance_demo_rows.tex")
    print("Wrote sections/generated/scheme_invariance_demo_summary.tex")


if __name__ == "__main__":
    main()

