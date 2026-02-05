#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chebyshev–Dwork congruence chain in the invariant coordinate t=u+u^{-1}.

We work with the weighted sync-kernel trace polynomials:
  a_n(u) = Tr(B(u)^n) in Z[u],
which satisfy the palindromic relation a_n(u)=u^n a_n(1/u).

For even n, define the invariant polynomial A_n(t) in Z[t] by:
  a_n(u) = u^{n/2} A_n(u+u^{-1}).

For p=2 and k>=2, the Dwork congruence implies the closed recursion in Z[t]:
  A_{2^k}(t) ≡ A_{2^{k-1}}(t^2-2) (mod 2^k).

This script computes A_{2^k}(t) for small k and verifies the congruence
coefficientwise, producing an auditable table.

Outputs:
  - artifacts/export/sync_kernel_weighted_chebyshev_dwork_chain.json
  - sections/generated/tab_sync_kernel_weighted_chebyshev_dwork_chain.tex

All output is English-only by repository convention.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

import sympy as sp

from common_paths import export_dir, generated_dir
from common_phi_fold import Progress
from exp_sync_kernel_weighted_pressure import STATES, build_edges


def _build_B_u(u: sp.Symbol) -> sp.Matrix:
    idx = {s: i for i, s in enumerate(STATES)}
    n = len(STATES)
    B = sp.zeros(n, n)
    for e in build_edges():
        i = idx[e.src]
        j = idx[e.dst]
        B[i, j] += sp.Integer(1) if e.e == 0 else u
    return B


def _chebyshev_C(k: int, t: sp.Symbol) -> sp.Expr:
    """C_k(t) = u^k + u^{-k} as a polynomial in t=u+u^{-1}."""
    if k < 0:
        raise ValueError("k must be >= 0")
    if k == 0:
        return sp.Integer(2)
    if k == 1:
        return t
    c0, c1 = sp.Integer(2), t
    for _ in range(2, k + 1):
        c0, c1 = c1, sp.expand(t * c1 - c0)
    return c1


def _A_from_palindromic_trace(a_u: sp.Expr, n: int, u: sp.Symbol, t: sp.Symbol) -> sp.Expr:
    """Return A_n(t) such that a_n(u)=u^{n/2}A_n(u+u^{-1}) for even n."""
    if n % 2 != 0:
        raise ValueError("Require even n.")
    expr = sp.expand(u ** (-n // 2) * a_u)  # invariant Laurent polynomial

    # Collect coefficients by u-exponent.
    coeffs: Dict[int, sp.Expr] = {}
    for term in sp.Add.make_args(expr):
        c, e = term.as_coeff_exponent(u)
        if not e.is_Integer:
            raise ValueError(f"Non-integer exponent in term: {term}")
        ei = int(e)
        coeffs[ei] = coeffs.get(ei, 0) + c

    # Convert symmetric Laurent polynomial to Z[t] via C_k(t).
    used = set()
    poly_t = sp.Integer(0)
    for e in sorted(coeffs.keys(), key=lambda x: abs(x)):
        if e in used:
            continue
        if e == 0:
            poly_t += coeffs[e]
            used.add(0)
            continue
        if sp.simplify(coeffs.get(e, 0) - coeffs.get(-e, 0)) != 0:
            raise ValueError(f"Not invariant under u->1/u at n={n}, exponent={e}")
        poly_t += coeffs[e] * _chebyshev_C(abs(e), t)
        used.add(e)
        used.add(-e)

    poly_t = sp.expand(poly_t)
    P = sp.Poly(poly_t, t, domain=sp.ZZ)
    if any(c.q != 1 for c in P.all_coeffs()):
        raise ValueError(f"Non-integer coefficients in A_{n}(t): {poly_t}")
    return poly_t


def _coeffs_all_divisible(expr: sp.Expr, t: sp.Symbol, mod: int) -> bool:
    P = sp.Poly(sp.expand(expr), t, domain=sp.ZZ)
    return all(int(c) % mod == 0 for c in P.all_coeffs())


@dataclass(frozen=True)
class Row:
    k: int
    n: int
    deg_A: int
    congruence_mod_2_pow_k_holds: bool


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Chebyshev–Dwork congruence chain for the weighted sync-kernel.")
    parser.add_argument("--k-max", type=int, default=5, help="Compute n=2^k up to k-max (k>=2 checked).")
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "sync_kernel_weighted_chebyshev_dwork_chain.json"),
    )
    parser.add_argument(
        "--tex-out",
        type=str,
        default=str(generated_dir() / "tab_sync_kernel_weighted_chebyshev_dwork_chain.tex"),
    )
    args = parser.parse_args()

    k_max = int(args.k_max)
    if k_max < 2:
        raise SystemExit("Require --k-max >= 2.")

    prog = Progress("sync-kernel-chebyshev-dwork", every_seconds=20.0)
    u = sp.Symbol("u")
    t = sp.Symbol("t")

    Bu = _build_B_u(u)
    # Compute B(u)^(2^k) iteratively by squaring.
    M = Bu
    a_pow: Dict[int, sp.Expr] = {1: sp.expand(sp.trace(M))}
    for k in range(1, k_max + 1):
        M = sp.expand(M * M)
        n = 2**k
        a_pow[n] = sp.expand(sp.trace(M))
        prog.tick(f"trace n=2^{k}={n}")

    # Build A_{2^k}(t) for k>=1 (n even).
    A: Dict[int, sp.Expr] = {}
    for k in range(1, k_max + 1):
        n = 2**k
        A[n] = _A_from_palindromic_trace(a_pow[n], n=n, u=u, t=t)
        prog.tick(f"A_n n={n}")

    # Verify the congruence chain for k>=2.
    rows: List[Row] = []
    for k in range(2, k_max + 1):
        n = 2**k
        n_prev = 2 ** (k - 1)
        lhs = A[n]
        rhs = sp.expand(A[n_prev].subs(t, t**2 - 2))
        diff = sp.expand(lhs - rhs)
        ok = _coeffs_all_divisible(diff, t=t, mod=2**k)
        deg_A = int(sp.Poly(A[n], t, domain=sp.ZZ).degree())
        rows.append(Row(k=k, n=n, deg_A=deg_A, congruence_mod_2_pow_k_holds=bool(ok)))
        prog.tick(f"check k={k} mod=2^{k}")

    payload = {
        "k_max": k_max,
        "rows": [asdict(r) for r in rows],
        "note": "Check is coefficientwise in Z[t].",
    }
    jout = Path(args.json_out)
    jout.parent.mkdir(parents=True, exist_ok=True)
    jout.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[chebyshev-dwork] wrote {jout}", flush=True)

    # TeX table.
    tout = Path(args.tex_out)
    tout.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append(
        "\\caption{Chebyshev--Dwork congruence chain audit in $\\mathbb{Z}[t]$ for the weighted sync-kernel. "
        "We compute $A_{2^k}(t)$ from $a_{2^k}(u)=\\mathrm{Tr}(B(u)^{2^k})$ via "
        "$a_{2^k}(u)=u^{2^{k-1}}A_{2^k}(u+u^{-1})$, and verify "
        "$A_{2^k}(t)\\equiv A_{2^{k-1}}(t^2-2)\\ (\\mathrm{mod}\\ 2^k)$ coefficientwise.}"
    )
    lines.append("\\label{tab:sync_kernel_weighted_chebyshev_dwork_chain}")
    lines.append("\\begin{tabular}{r r r l}")
    lines.append("\\toprule")
    lines.append("$k$ & $2^k$ & $\\deg A_{2^k}$ & check in $\\mathbb{Z}[t]$\\\\")
    lines.append("\\midrule")
    for r in rows:
        verdict = "PASS" if r.congruence_mod_2_pow_k_holds else "FAIL"
        lines.append(f"{r.k} & {r.n} & {r.deg_A} & {verdict}\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    tout.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[chebyshev-dwork] wrote {tout}", flush=True)
    print("[chebyshev-dwork] done", flush=True)


if __name__ == "__main__":
    main()

