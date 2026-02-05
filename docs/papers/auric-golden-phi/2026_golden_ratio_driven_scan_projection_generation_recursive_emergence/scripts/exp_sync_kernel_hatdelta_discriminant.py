#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discriminant of the completed determinant hat{Delta}(w,s) for the weighted sync-kernel.

We use the explicit completed polynomial from the paper:
  hatDelta(w,s) = 1 - s w - 5 w^2 + 3 s w^3 + (5 - s^2) w^4 + (s^3 - 6 s) w^5 + (s^2 - 1) w^6.

We compute:
  Disc_w(hatDelta)(s) in Z[s],
and numerically locate its real roots in [-2,2], which correspond to spectral branch points
on the unit-circle twist locus s = 2 cos(t/2).

Outputs:
  - artifacts/export/sync_kernel_hatdelta_discriminant.json
  - sections/generated/eq_sync_kernel_hatdelta_discriminant.tex
  - sections/generated/tab_sync_kernel_hatdelta_branch_points.tex

All output is English-only by repository convention.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

import sympy as sp

from common_paths import export_dir, generated_dir


@dataclass(frozen=True)
class BranchPoint:
    s: str
    theta: str  # theta = 2 arccos(s/2) in radians, principal in [0, 2pi]


def _hat_delta(w: sp.Symbol, s: sp.Symbol) -> sp.Expr:
    return sp.expand(
        1
        - s * w
        - 5 * w**2
        + 3 * s * w**3
        + (5 - s**2) * w**4
        + (s**3 - 6 * s) * w**5
        + (s**2 - 1) * w**6
    )


def _nstr(x: sp.Expr, nd: int) -> str:
    return str(sp.N(x, nd))


def main() -> None:
    parser = argparse.ArgumentParser(description="Discriminant and branch points for hatDelta(w,s).")
    parser.add_argument("--dps", type=int, default=80, help="Decimal digits for root finding.")
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "sync_kernel_hatdelta_discriminant.json"),
    )
    parser.add_argument(
        "--tex-eq-out",
        type=str,
        default=str(generated_dir() / "eq_sync_kernel_hatdelta_discriminant.tex"),
    )
    parser.add_argument(
        "--tex-tab-out",
        type=str,
        default=str(generated_dir() / "tab_sync_kernel_hatdelta_branch_points.tex"),
    )
    args = parser.parse_args()

    # SymPy uses mpmath for numerical evaluation; set mpmath precision explicitly.
    import mpmath as mp
    mp.mp.dps = int(args.dps)
    w, s = sp.symbols("w s")
    hd = _hat_delta(w, s)

    print("[hatdelta-disc] computing Disc_w(hatDelta)...", flush=True)
    disc = sp.discriminant(sp.Poly(hd, w), w)
    disc = sp.expand(disc)

    # Normalize: primitive integer polynomial with positive leading coefficient.
    P = sp.Poly(disc, s, domain=sp.ZZ)
    if P.LC() < 0:
        P = sp.Poly(-P.as_expr(), s, domain=sp.ZZ)
    disc_norm = sp.expand(P.as_expr())

    # Find real roots in [-2,2].
    print("[hatdelta-disc] finding real roots in [-2,2]...", flush=True)
    roots = sp.nroots(P, n=int(args.dps), maxsteps=200)
    real_roots: List[sp.Float] = []
    for r in roots:
        rr = sp.N(sp.re(r), int(args.dps))
        ii = sp.N(sp.im(r), int(args.dps))
        if abs(float(ii)) < 1e-30:
            rrf = sp.Float(rr)
            if -2.0 - 1e-12 <= float(rrf) <= 2.0 + 1e-12:
                real_roots.append(rrf)
    real_roots = sorted(real_roots, key=lambda x: float(x))

    # Keep unique roots (nroots can duplicate very close).
    uniq: List[sp.Float] = []
    for r in real_roots:
        if not uniq or abs(float(r - uniq[-1])) > 1e-10:
            uniq.append(r)

    # Positive roots as branch-point representatives; map to theta in [0,pi] via s=2cos(theta/2).
    bps: List[BranchPoint] = []
    for r in uniq:
        if float(r) <= 0:
            continue
        # theta = 2 arccos(s/2)
        x = float(r) / 2.0
        x = max(-1.0, min(1.0, x))
        theta = 2.0 * math.acos(x)
        bps.append(
            BranchPoint(
                s=_nstr(r, 20),
                theta=f"{theta:.12f}",
            )
        )

    payload = {
        "disc_s": str(disc_norm),
        "disc_s_latex": sp.latex(disc_norm),
        "roots_real_in_minus2_2": [str(r) for r in uniq],
        "branch_points_positive": [asdict(bp) for bp in bps],
    }

    jout = Path(args.json_out)
    jout.parent.mkdir(parents=True, exist_ok=True)
    jout.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[hatdelta-disc] wrote {jout}", flush=True)

    # LaTeX equation block.
    eq = Path(args.tex_eq_out)
    eq.parent.mkdir(parents=True, exist_ok=True)
    eq_lines: List[str] = []
    eq_lines.append("% Auto-generated; do not edit by hand.")
    eq_lines.append("\\begin{equation}\\label{eq:sync_kernel_hatdelta_discriminant}")
    eq_lines.append("\\boxed{")
    eq_lines.append("\\mathrm{Disc}_w\\bigl(\\widehat\\Delta(w,s)\\bigr)=" + sp.latex(disc_norm))
    eq_lines.append("}")
    eq_lines.append("\\end{equation}")
    eq.write_text("\n".join(eq_lines) + "\n", encoding="utf-8")
    print(f"[hatdelta-disc] wrote {eq}", flush=True)

    # LaTeX table.
    tab = Path(args.tex_tab_out)
    tab.parent.mkdir(parents=True, exist_ok=True)
    tlines: List[str] = []
    tlines.append("\\begin{table}[H]")
    tlines.append("\\centering")
    tlines.append("\\scriptsize")
    tlines.append("\\setlength{\\tabcolsep}{6pt}")
    tlines.append(
        "\\caption{Spectral branch points on the unit-circle twist locus for the completed determinant "
        "$\\widehat\\Delta(w,s)$. We list the positive real roots $s_\\star\\in(0,2]$ of "
        "$\\mathrm{Disc}_w(\\widehat\\Delta)(s)=0$ and the corresponding angles "
        "$\\theta=2\\arccos(s_\\star/2)\\in(0,\\pi]$ (so that $s=2\\cos(\\theta/2)$).}"
    )
    tlines.append("\\label{tab:sync_kernel_hatdelta_branch_points}")
    tlines.append("\\begin{tabular}{r r}")
    tlines.append("\\toprule")
    tlines.append("$s_\\star$ & $\\theta$ (rad)\\\\")
    tlines.append("\\midrule")
    if not bps:
        tlines.append("$0$ & $0$\\\\")
    else:
        for bp in bps:
            tlines.append(f"${bp.s}$ & ${bp.theta}$\\\\")
    tlines.append("\\bottomrule")
    tlines.append("\\end{tabular}")
    tlines.append("\\end{table}")
    tab.write_text("\n".join(tlines) + "\n", encoding="utf-8")
    print(f"[hatdelta-disc] wrote {tab}", flush=True)
    print("[hatdelta-disc] done", flush=True)


if __name__ == "__main__":
    main()

