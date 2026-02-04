#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eliminate lambda from the weighted sync-kernel pressure equation.

We have the sextic algebraic equation F(lambda,u)=0 for the Perron root lambda(u),
and the Legendre slope
  alpha(u) = u * lambda_u / lambda
with lambda_u = -F_u / F_lambda.

Hence alpha,lambda,u satisfy the polynomial system:
  F(lambda,u) = 0,
  G(alpha,lambda,u) := alpha*lambda*F_lambda(lambda,u) + u*F_u(lambda,u) = 0.

Eliminating lambda yields a nonzero polynomial R(alpha,u) in Z[alpha,u] such that
R(alpha(u),u)=0 for all u>0 on the Perron branch. This is an algebraic certificate
for the full-domain rate curve.

This script writes:
  - artifacts/export/sync_kernel_rate_curve_resultant.json
  - sections/generated/tab_sync_kernel_rate_curve_resultant_degree.tex

All output is English-only by repository convention.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

import sympy as sp

from common_paths import export_dir, generated_dir


@dataclass(frozen=True)
class ResultantSummary:
    deg_alpha: int
    deg_u: int
    n_terms: int
    content_gcd: str
    leading_monomial: str
    leading_coeff: str
    elapsed_sec: float


def _build_F(lam: sp.Symbol, u: sp.Symbol) -> sp.Expr:
    # Must match appendix `90_appendix_sync_kernel_weighted.tex` exactly.
    return (
        lam**6
        - (1 + u) * lam**5
        - 5 * u * lam**4
        + 3 * u * (1 + u) * lam**3
        - u * (u**2 - 3 * u + 1) * lam**2
        + u * (u**3 - 3 * u**2 - 3 * u + 1) * lam
        + u**2 * (u**2 + u + 1)
    )


def _tex_table(summary: ResultantSummary) -> str:
    lines: list[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append(
        "\\caption{Elimination certificate for the rate curve. "
        "We eliminate $\\lambda$ from $F(\\lambda,u)=0$ and "
        "$\\alpha\\lambda F_{\\lambda}(\\lambda,u)+uF_u(\\lambda,u)=0$ to obtain "
        "$R(\\alpha,u)\\in\\mathbb{Z}[\\alpha,u]$. "
        "This table records the degree/size of $R$ (see script).}"
    )
    lines.append("\\label{tab:sync_kernel_rate_curve_resultant_degree}")
    lines.append("\\begin{tabular}{l l}")
    lines.append("\\toprule")
    lines.append("$\\deg_{\\alpha} R$ & $%d$\\\\"
                 % summary.deg_alpha)
    lines.append("$\\deg_{u} R$ & $%d$\\\\"
                 % summary.deg_u)
    lines.append("\\#terms & $%d$\\\\"
                 % summary.n_terms)
    lines.append("$\\mathrm{content}(R)$ & $%s$\\\\"
                 % summary.content_gcd.replace("_", "\\_"))
    lines.append("leading monomial & $%s$\\\\"
                 % summary.leading_monomial.replace("_", "\\_"))
    lines.append("leading coeff & $%s$\\\\"
                 % summary.leading_coeff.replace("_", "\\_"))
    lines.append("elapsed (sec) & %.3f\\\\"
                 % summary.elapsed_sec)
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Eliminate lambda to get R(alpha,u).")
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "sync_kernel_rate_curve_resultant.json"),
    )
    parser.add_argument(
        "--tex-out",
        type=str,
        default=str(generated_dir() / "tab_sync_kernel_rate_curve_resultant_degree.tex"),
    )
    args = parser.parse_args()

    t0 = time.time()
    lam = sp.Symbol("lam")
    u = sp.Symbol("u")
    alpha = sp.Symbol("alpha")

    F = _build_F(lam, u)
    Fl = sp.diff(F, lam)
    Fu = sp.diff(F, u)
    G = sp.expand(alpha * lam * Fl + u * Fu)

    # Eliminate lam by resultant. This can take time; print a heartbeat.
    print("[elim] building resultant R(alpha,u) ...", flush=True)
    t1 = time.time()
    R = sp.resultant(F, G, lam)
    elapsed = time.time() - t1
    print(f"[elim] resultant computed in {elapsed:.3f}s", flush=True)

    PR = sp.Poly(R, alpha, u, domain="ZZ")
    deg_alpha = int(PR.degree(alpha))
    deg_u = int(PR.degree(u))
    n_terms = len(PR.terms())
    content = sp.Integer(sp.gcd_list(list(PR.coeffs()))) if PR.coeffs() else sp.Integer(0)

    # Leading term info under lex order (alpha > u).
    lt_monom, lt_coeff = PR.LT()
    leading_monomial = f"\\alpha^{{{lt_monom[0]}}}u^{{{lt_monom[1]}}}"
    leading_coeff = str(lt_coeff)

    summary = ResultantSummary(
        deg_alpha=deg_alpha,
        deg_u=deg_u,
        n_terms=n_terms,
        content_gcd=str(content),
        leading_monomial=leading_monomial,
        leading_coeff=leading_coeff,
        elapsed_sec=time.time() - t0,
    )

    jout = Path(args.json_out)
    jout.parent.mkdir(parents=True, exist_ok=True)
    jout.write_text(json.dumps(asdict(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[elim] wrote {jout}", flush=True)

    tout = Path(args.tex_out)
    tout.parent.mkdir(parents=True, exist_ok=True)
    tout.write_text(_tex_table(summary), encoding="utf-8")
    print(f"[elim] wrote {tout}", flush=True)


if __name__ == "__main__":
    main()

