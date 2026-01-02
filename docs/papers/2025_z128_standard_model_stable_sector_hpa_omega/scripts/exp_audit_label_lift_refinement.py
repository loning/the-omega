# -*- coding: utf-8 -*-
"""
Audit checks for the functorial lift refinement index (suffix Zeckendorf index).

We audit two structural claims for the free suffix index rho introduced in
Appendix~\\ref{app:functorial_refinement}:
  (i) rho enumerates the admissible free suffix set contiguously (0..|Theta|-1),
 (ii) the subset of free suffixes ending in 1 occupies the top Fibonacci block
      of indices {F_{l+1}, ..., F_{l+2}-1}.

Here l denotes the free suffix length:
  - if u_6 = 0:  l = m-6
  - if u_6 = 1:  l = m-7  (drop the forced leading 0 after a trailing-1 prefix bit)

Outputs (LaTeX fragment):
  - sections/generated/audit_label_lift_refinement_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import exp_xm_enumeration as xm
from common_tex import write_lines


def fib(n: int) -> int:
    # Fibonacci numbers with F1=F2=1.
    if n <= 0:
        raise ValueError("n must be positive.")
    if n in (1, 2):
        return 1
    a, b = 1, 1
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b


def fib_weights(L: int) -> List[int]:
    # Weights [F2, F3, ..., F_{L+1}] with F1=F2=1.
    if L < 0:
        raise ValueError("L must be nonnegative.")
    if L == 0:
        return []
    if L == 1:
        return [1]
    w = [1, 2]
    while len(w) < L:
        w.append(w[-1] + w[-2])
    return w


def zeckendorf_value_word(word: str) -> int:
    wts = fib_weights(len(word))
    return sum(int(bit) * wts[i] for i, bit in enumerate(word))


def _set_tex(xs: List[int]) -> str:
    if not xs:
        return r"$\varnothing$"
    inner = ", ".join(str(x) for x in xs)
    return rf"$\{{{inner}\}}$"


def _fmt_status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def audit_rows(m_list: List[int]) -> List[str]:
    rows: List[str] = []
    for m in m_list:
        for u6 in (0, 1):
            # Determine free suffix length and enumerate free suffix set Theta.
            if u6 == 0:
                l_free = m - 6
            else:
                l_free = m - 7
            if l_free < 0:
                raise AssertionError("Invalid free length; expected m>=6.")

            theta = xm.all_xm(l_free) if l_free > 0 else [""]
            rhos = sorted(zeckendorf_value_word(t) for t in theta)
            contig_ok = rhos == list(range(len(theta)))

            # Boundary subset: free suffix ending with 1 (empty when l_free=0).
            bdry = [zeckendorf_value_word(t) for t in theta if t.endswith("1")]
            bdry = sorted(set(bdry))

            # Expected sizes and expected boundary block in index space.
            exp_size = fib(l_free + 2) if l_free >= 0 else 0
            size_ok = len(theta) == exp_size

            # The "ending in 1" subset occupies the top Fibonacci block:
            # indices {F_{l+1}, ..., F_{l+2}-1}, with empty set when l=0.
            start = fib(l_free + 1) if l_free >= 0 else 0
            exp_bdry = list(range(start, exp_size)) if l_free > 0 else []
            bdry_ok = bdry == exp_bdry

            ok = size_ok and contig_ok and bdry_ok
            rho_range = f"$0\\dots {exp_size - 1}$" if exp_size > 0 else "$0$"
            rows.append(
                f"{m} & {u6} & {l_free} & {len(theta)} & {rho_range} & {_set_tex(bdry)} & {_fmt_status(ok)} \\\\"
            )
    rows.append("\\bottomrule")
    return rows


def main() -> None:
    m_list = [8, 10, 12, 14, 16]
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "audit_label_lift_refinement_rows.tex", audit_rows(m_list))
    print("Wrote sections/generated/audit_label_lift_refinement_rows.tex")


if __name__ == "__main__":
    main()


