#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rigidity enumerations for electroweak Z-scale targets under bounded complexity.

We record two finite searches used in the paper:
  (1) alpha^{-1}(mu_Z) ~ n*pi^2 with 1 <= n <= N
  (2) sin^2(theta_W)(mu_Z) ~ p/q with 1 <= q <= Q and gcd(p,q)=1

We rank candidates by absolute error to the PDG reference targets, with
deterministic tie-break rules.

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

from common_constants import ALPHAZ_INV_PDG, SIN2_THETAW_PDG
from common_paths import generated_dir


@dataclass(frozen=True)
class Pi2Cand:
    n: int
    value: float
    abs_err: float
    rel_err: float


@dataclass(frozen=True)
class RatCand:
    p: int
    q: int
    value: float
    abs_err: float


def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a)


def main() -> None:
    out_dir = generated_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # (1) Integer pi^2 search
    N = 50
    pi2 = math.pi**2
    target_alpha = float(ALPHAZ_INV_PDG)
    pi2_cands: List[Pi2Cand] = []
    for n in range(1, N + 1):
        val = n * pi2
        abs_err = abs(val - target_alpha)
        rel_err = abs_err / target_alpha
        pi2_cands.append(Pi2Cand(n=n, value=val, abs_err=abs_err, rel_err=rel_err))
    pi2_cands_sorted = sorted(pi2_cands, key=lambda x: (x.abs_err, x.n))
    top_pi2 = pi2_cands_sorted[:10]

    rows_pi2: List[str] = []
    for i, cand in enumerate(top_pi2, start=1):
        rows_pi2.append(
            rf"{i} & {cand.n} & {cand.value:.10f} & {cand.abs_err:.3e} & {cand.rel_err:.3e} \\"
        )
    rows_pi2.append(r"\bottomrule")
    (out_dir / "ew_alpha_pi2_rigidity_rows.tex").write_text("\n".join(rows_pi2), encoding="utf-8")
    print("Wrote sections/generated/ew_alpha_pi2_rigidity_rows.tex")

    # (2) Rational sin^2 search
    Q = 50
    target_sin2 = float(SIN2_THETAW_PDG)
    rat_cands: List[RatCand] = []
    for q in range(1, Q + 1):
        for p in range(0, q + 1):
            if p == 0 or p == q:
                continue
            if gcd(p, q) != 1:
                continue
            val = p / q
            abs_err = abs(val - target_sin2)
            rat_cands.append(RatCand(p=p, q=q, value=val, abs_err=abs_err))
    rat_cands_sorted = sorted(rat_cands, key=lambda x: (x.abs_err, x.q, x.p))
    top_rat = rat_cands_sorted[:10]

    rows_rat: List[str] = []
    for i, cand in enumerate(top_rat, start=1):
        rows_rat.append(rf"{i} & ${cand.p}/{cand.q}$ & {cand.value:.10f} & {cand.abs_err:.3e} \\")
    rows_rat.append(r"\bottomrule")
    (out_dir / "ew_sin2_rational_rigidity_rows.tex").write_text("\n".join(rows_rat), encoding="utf-8")
    print("Wrote sections/generated/ew_sin2_rational_rigidity_rows.tex")


if __name__ == "__main__":
    main()


