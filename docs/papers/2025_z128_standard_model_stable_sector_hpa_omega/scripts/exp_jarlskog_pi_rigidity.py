#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rigidity enumeration for the Jarlskog invariant in a simple pi-ansatz family.

We consider:
  J(a,n) = 1 / (a * pi^n)
over the bounded domain 1 <= a <= A, 1 <= n <= N.

We minimize the audit-norm absolute log mismatch
  e := |log(J / J_ref)|
to the PDG reference central value and report the top candidates (together with
the best/second-best gap).

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from common_constants import JARLSKOG_PDG_CENTRAL, JARLSKOG_PDG_SIGMA
from common_paths import generated_dir


@dataclass(frozen=True)
class Candidate:
    a: int
    n: int
    value: float
    abs_err: float
    rel_err: float
    sigma_err: float
    log_mismatch: float


def main() -> None:
    A = 50
    N = 20
    pi = math.pi
    target = float(JARLSKOG_PDG_CENTRAL)
    sigma = float(JARLSKOG_PDG_SIGMA)

    cands: List[Candidate] = []
    for a in range(1, A + 1):
        for n in range(1, N + 1):
            val = 1.0 / (a * (pi**n))
            abs_err = abs(val - target)
            rel_err = abs_err / target
            sigma_err = abs_err / sigma if sigma > 0.0 else float("inf")
            log_mismatch = abs(math.log(val / target))
            cands.append(
                Candidate(
                    a=a,
                    n=n,
                    value=val,
                    abs_err=abs_err,
                    rel_err=rel_err,
                    sigma_err=sigma_err,
                    log_mismatch=log_mismatch,
                )
            )

    # Deterministic sort: minimize log mismatch, then (a+n), then (a,n).
    cands_sorted = sorted(cands, key=lambda x: (x.log_mismatch, x.a + x.n, x.a, x.n))
    top = cands_sorted[:10]
    gap = cands_sorted[1].log_mismatch - cands_sorted[0].log_mismatch

    rows: List[str] = []
    for i, cand in enumerate(top, start=1):
        rows.append(
            rf"{i} & $({cand.a},{cand.n})$ & {cand.value:.10e} & {cand.abs_err:.3e} & {cand.rel_err:.3e} & {cand.sigma_err:.3e} & {cand.log_mismatch:.3e} \\"
        )
    rows.append(r"\addlinespace")
    rows.append(rf"\multicolumn{{7}}{{l}}{{domain $|\Theta|={len(cands)}$;\ \ best/second gap $\Delta e={gap:.3e}$}} \\")
    rows.append(r"\bottomrule")

    out_dir = generated_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "jarlskog_pi_rigidity_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/jarlskog_pi_rigidity_rows.tex")


if __name__ == "__main__":
    main()


