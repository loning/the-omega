#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export completed primitive polynomials \\hat p_n(s) for the weighted sync-kernel.

We use the completion variables:
  u = r^2,  s = r + r^{-1},
and define the completed primitive polynomial
  \\hat p_n(s) := r^{-n} p_n(r^2),
which is invariant under r -> 1/r and thus lies in Z[s].

This script outputs:
  - sections/generated/tab_sync_kernel_weighted_primitive_completed.tex

All output is English-only by repository convention.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

import sympy as sp

from common_paths import generated_dir


def chebyshev_C(k: int, s: sp.Symbol) -> sp.Expr:
    """C_k(s) = r^k + r^{-k} with s = r + r^{-1} (integer polynomial)."""
    if k == 0:
        return sp.Integer(2)
    if k == 1:
        return s
    c0, c1 = sp.Integer(2), s
    for _ in range(2, k + 1):
        c0, c1 = c1, sp.expand(s * c1 - c0)
    return c1


def completed_poly_from_pn(n: int, pn_u: sp.Expr) -> sp.Expr:
    r = sp.Symbol("r")
    s = sp.Symbol("s")
    u = sp.Symbol("u")

    expr = sp.expand(r ** (-n) * pn_u.subs(u, r**2))
    coeffs: Dict[int, sp.Expr] = {}
    for term in sp.Add.make_args(expr):
        c, e = term.as_coeff_exponent(r)
        if not e.is_Integer:
            raise ValueError(f"Non-integer exponent in term: {term}")
        ei = int(e)
        coeffs[ei] = coeffs.get(ei, 0) + c

    poly_s = sp.Integer(0)
    used = set()
    for e in sorted(coeffs.keys(), key=lambda x: abs(x)):
        if e in used:
            continue
        if e == 0:
            poly_s += coeffs[e]
            used.add(0)
            continue
        if sp.simplify(coeffs.get(e, 0) - coeffs.get(-e, 0)) != 0:
            raise ValueError(f"Not symmetric under r->1/r at n={n}, exponent={e}")
        poly_s += coeffs[e] * chebyshev_C(abs(e), s)
        used.add(e)
        used.add(-e)
    return sp.expand(poly_s)


def write_table_tex(path: Path, polys: Dict[int, sp.Expr]) -> None:
    lines: list[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append(
        "\\caption{Completed primitive polynomials for the weighted sync-kernel. "
        "We define $u=r^2$, $s=r+r^{-1}$ and $\\widehat p_n(s):=r^{-n}p_n(r^2)\\in\\mathbb Z[s]$.}"
    )
    lines.append("\\label{tab:sync_kernel_weighted_primitive_completed}")
    lines.append("\\begin{tabular}{r l}")
    lines.append("\\toprule")
    lines.append("$n$ & $\\widehat p_n(s)$\\\\")
    lines.append("\\midrule")
    for n in sorted(polys.keys()):
        p = sp.expand(polys[n])
        lines.append(f"{n} & ${sp.latex(p)}$\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export completed primitive polynomials hat{p}_n(s).")
    parser.add_argument(
        "--tex-out",
        type=str,
        default=str(generated_dir() / "tab_sync_kernel_weighted_primitive_completed.tex"),
        help="Output LaTeX table path.",
    )
    args = parser.parse_args()

    u = sp.Symbol("u")
    # p_n(u) from appendix `90_appendix_sync_kernel_weighted.tex` (n=2..10)
    p: Dict[int, sp.Expr] = {
        2: 6 * u,
        3: 3 * u + 3 * u**2,
        4: 2 * u + 16 * u**2 + 2 * u**3,
        5: 3 * u + 19 * u**2 + 19 * u**3 + 3 * u**4,
        6: 3 * u + 26 * u**2 + 65 * u**3 + 26 * u**4 + 3 * u**5,
        7: 9 * u + 66 * u**2 + 276 * u**3 + 276 * u**4 + 66 * u**5 + 9 * u**6,
        8: 30 * u + 207 * u**2 + 861 * u**3 + 1925 * u**4 + 861 * u**5 + 207 * u**6 + 30 * u**7,
        9: 103 * u
        + 840 * u**2
        + 4062 * u**3
        + 9194 * u**4
        + 9194 * u**5
        + 4062 * u**6
        + 840 * u**7
        + 103 * u**8,
        10: 340 * u
        + 3330 * u**2
        + 18437 * u**3
        + 51822 * u**4
        + 74757 * u**5
        + 51822 * u**6
        + 18437 * u**7
        + 3330 * u**8
        + 340 * u**9,
    }

    polys: Dict[int, sp.Expr] = {n: completed_poly_from_pn(n, p[n]) for n in range(2, 11)}
    write_table_tex(Path(args.tex_out), polys)
    print(f"[primitive-completed] wrote {args.tex_out}", flush=True)


if __name__ == "__main__":
    main()

