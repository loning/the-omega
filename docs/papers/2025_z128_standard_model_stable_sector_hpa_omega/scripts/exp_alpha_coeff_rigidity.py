#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rigidity enumeration for alpha^{-1} in a bounded nonnegative coefficient simplex.

We consider the finite family:
  x(a,b,c) = a*pi^3 + b*pi^2 + c*pi
with a,b,c in Z_{\\ge 0} and a+b+c <= S.

We minimize the audit-norm absolute log mismatch
  e := |log(x / alpha^{-1}_{ref})|
to the CODATA reference alpha^{-1} and report the best candidates, together
with the best/second-best gap.

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

from common_constants import ALPHA_INV_CODATA_2022
from common_paths import generated_dir


@dataclass(frozen=True)
class Candidate:
    a: int
    b: int
    c: int
    value: float
    abs_err: float
    rel_err: float
    log_mismatch: float
    coeff_sum: int


def expr_tex(a: int, b: int, c: int) -> str:
    parts: List[str] = []

    def add(coeff: int, term: str) -> None:
        if coeff == 0:
            return
        if coeff == 1:
            parts.append(f"+{term}")
        else:
            parts.append(f"+{coeff}{term}")

    add(a, r"\pi^3")
    add(b, r"\pi^2")
    add(c, r"\pi")

    if not parts:
        return "0"
    s = "".join(parts)
    if s.startswith("+"):
        s = s[1:]
    return s


def enumerate_simplex(S: int) -> List[Candidate]:
    pi = math.pi
    target = float(ALPHA_INV_CODATA_2022)
    out: List[Candidate] = []
    for a in range(S + 1):
        for b in range(S + 1 - a):
            for c in range(S + 1 - a - b):
                if a == 0 and b == 0 and c == 0:
                    continue
                val = a * (pi**3) + b * (pi**2) + c * pi
                abs_err = abs(val - target)
                rel_err = abs_err / target
                log_mismatch = abs(math.log(val / target)) if val > 0.0 else float("inf")
                out.append(
                    Candidate(
                        a=a,
                        b=b,
                        c=c,
                        value=val,
                        abs_err=abs_err,
                        rel_err=rel_err,
                        log_mismatch=log_mismatch,
                        coeff_sum=a + b + c,
                    )
                )
    return out


def main() -> None:
    S = 10
    cands = enumerate_simplex(S=S)

    # Deterministic sort in the audit norm: minimize log mismatch, then (a+b+c), then (a,b,c).
    cands_sorted = sorted(cands, key=lambda x: (x.log_mismatch, x.coeff_sum, x.a, x.b, x.c))
    top = cands_sorted[:10]
    best = cands_sorted[0]
    second = cands_sorted[1]
    gap = second.log_mismatch - best.log_mismatch

    rows: List[str] = []
    for i, cand in enumerate(top, start=1):
        rows.append(
            rf"{i} & $({cand.a},{cand.b},{cand.c})$ & ${expr_tex(cand.a, cand.b, cand.c)}$ & {cand.value:.10f} & {cand.abs_err:.3e} & {cand.rel_err:.3e} & {cand.log_mismatch:.3e} \\"
        )
    rows.append(r"\addlinespace")
    rows.append(rf"\multicolumn{{7}}{{l}}{{domain $|\Theta|={len(cands)}$;\ \ best/second gap $\Delta e={gap:.3e}$}} \\")
    rows.append(r"\bottomrule")

    out_dir = generated_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "alpha_coeff_rigidity_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/alpha_coeff_rigidity_rows.tex")


if __name__ == "__main__":
    main()


