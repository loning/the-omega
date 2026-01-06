#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit null baselines over a broader low-complexity expression grammar.

We consider integer polynomials in pi of bounded degree and bounded coefficients:
  P(pi) = a3*pi^3 + a2*pi^2 + a1*pi + a0,
with ai in [-A, A] and degree <= 3.

For each target (CODATA alpha^{-1}), we compute the best achievable absolute
log-mismatch e = |log(P(pi)/x_ref)| over the full finite domain, and report:
  - domain size
  - best polynomial and its e
  - count of candidates with e <= e_best (ties) and with e <= eps

This is intended to provide explicit look-elsewhere context for a larger class
than the hand-picked single expression 4*pi^3 + pi^2 + pi used in the paper.

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

from common_constants import ALPHA_INV_CODATA_2022


@dataclass(frozen=True)
class Best:
    a3: int
    a2: int
    a1: int
    a0: int
    value: float
    e: float


def abs_log_ratio(x: float, x_ref: float) -> float:
    return abs(math.log(x / x_ref))


def iter_coeffs(A: int) -> Iterable[Tuple[int, int, int, int]]:
    rng = range(-A, A + 1)
    for a3 in rng:
        for a2 in rng:
            for a1 in rng:
                for a0 in rng:
                    yield a3, a2, a1, a0


def poly_value(pi: float, a3: int, a2: int, a1: int, a0: int) -> float:
    return ((a3 * pi + a2) * pi + a1) * pi + a0


def best_poly(A: int, x_ref: float) -> Tuple[Best, int, int, int]:
    pi = math.pi
    domain = 0
    best: Best | None = None
    ties_best = 0
    count_le_001 = 0
    count_le_005 = 0

    # First pass: determine best e and count quantiles.
    e_list: List[float] = []
    for a3, a2, a1, a0 in iter_coeffs(A):
        domain += 1
        val = poly_value(pi, a3, a2, a1, a0)
        if val <= 0.0 or not math.isfinite(val):
            continue
        e = abs_log_ratio(val, x_ref)
        e_list.append(e)
        if e <= 0.01:
            count_le_001 += 1
        if e <= 0.05:
            count_le_005 += 1
        if best is None or e < best.e:
            best = Best(a3=a3, a2=a2, a1=a1, a0=a0, value=val, e=e)

    if best is None:
        raise AssertionError("No positive finite candidates in domain.")

    # Second pass: count ties at best e (within exact float equality).
    for a3, a2, a1, a0 in iter_coeffs(A):
        val = poly_value(pi, a3, a2, a1, a0)
        if val <= 0.0 or not math.isfinite(val):
            continue
        e = abs_log_ratio(val, x_ref)
        if e == best.e:
            ties_best += 1

    return best, domain, ties_best, count_le_001, count_le_005


def poly_tex(a3: int, a2: int, a1: int, a0: int) -> str:
    # Render as TeX with suppressed zero terms.
    parts: List[str] = []

    def add_term(coeff: int, term: str) -> None:
        if coeff == 0:
            return
        if coeff == 1:
            parts.append(f"+{term}")
        elif coeff == -1:
            parts.append(f"-{term}")
        elif coeff > 0:
            parts.append(f"+{coeff}{term}")
        else:
            parts.append(f"{coeff}{term}")

    add_term(a3, r"\pi^3")
    add_term(a2, r"\pi^2")
    add_term(a1, r"\pi")
    if a0 != 0:
        parts.append(f"{a0:+d}")

    if not parts:
        return "0"
    s = "".join(parts)
    if s.startswith("+"):
        s = s[1:]
    return s


def main() -> None:
    x_ref = float(ALPHA_INV_CODATA_2022)
    # A is a bounded complexity knob; A=10 yields (2A+1)^4 = 194,481 candidates.
    A = 10
    best, domain, ties_best, n001, n005 = best_poly(A=A, x_ref=x_ref)

    rows: List[str] = []
    rows.append(
        rf"$\alpha_{{\mathrm{{em}}}}^{{-1}}$ (CODATA) & $\sum_{{j=0}}^3 a_j\pi^j,\ a_j\in[-{A},{A}]$ & {domain} & ${poly_tex(best.a3, best.a2, best.a1, best.a0)}$ & {best.e:.6g} & {ties_best} & {n001} & {n005} \\\\"
    )
    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit_pi_poly_null_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/audit_pi_poly_null_rows.tex")


if __name__ == "__main__":
    main()


