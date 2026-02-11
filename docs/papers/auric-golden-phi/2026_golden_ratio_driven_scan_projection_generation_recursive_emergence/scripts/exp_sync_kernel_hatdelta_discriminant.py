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
  - sections/generated/tab_sync_kernel_hatdelta_nearest_complex_branch_point.tex

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


@dataclass(frozen=True)
class NearestComplexBranchPoint:
    x_re: str
    x_im_abs: str
    s_re: str
    s_im_abs: str
    theta_re: str
    theta_im_abs: str
    theta_abs: str
    re_s_minus_sqrt3: str


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


def _mp_nstr(x, nd_sig: int = 16) -> str:
    # mpmath number -> stable decimal string with ~nd_sig significant digits.
    import mpmath as mp

    return mp.nstr(x, nd_sig)


def _disc_even_poly_in_x(Ps: sp.Poly, s: sp.Symbol, x: sp.Symbol) -> sp.Poly:
    """
    Given an even polynomial Ps(s) (only even powers), return Q(x) with x=s^2 such that Ps(s)=Q(s^2).
    """
    expr_x = 0
    for (deg,), coeff in Ps.terms():
        if deg % 2 != 0:
            raise ValueError("Polynomial is not even in s; found an odd-degree term.")
        expr_x += coeff * x ** (deg // 2)
    return sp.Poly(sp.expand(expr_x), x, domain=sp.ZZ)


def _nearest_theta_branch_point_from_x_roots(roots_x, dps: int) -> tuple:
    """
    Given roots in x=s^2, search over s=±sqrt(x) and return the candidate with smallest |theta|,
    where theta=2*acos(s/2) (principal branch). Uses mpmath for complex acos/sqrt.
    Returns (abs_theta, theta, s, x) as mpmath complex numbers.
    """
    import mpmath as mp

    mp.mp.dps = int(dps)

    def _mp_c(z: sp.Expr) -> mp.mpc:
        return mp.mpc(str(sp.re(z)), str(sp.im(z)))

    best = None
    for xr in roots_x:
        x_mp = _mp_c(xr)
        for sign in (1, -1):
            s_mp = sign * mp.sqrt(x_mp)
            theta_mp = 2 * mp.acos(s_mp / 2)
            a = abs(theta_mp)
            if best is None or a < best[0]:
                best = (a, theta_mp, s_mp, x_mp)
    if best is None:
        raise RuntimeError("No candidate branch points found from x-roots.")
    return best


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
    parser.add_argument(
        "--tex-tab-complex-out",
        type=str,
        default=str(generated_dir() / "tab_sync_kernel_hatdelta_nearest_complex_branch_point.tex"),
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

    # Reduce to x=s^2 (degree-10) and locate the nearest complex branch point in the theta-plane.
    print("[hatdelta-disc] reducing to x=s^2 and finding nearest complex branch point...", flush=True)
    x_sym = sp.Symbol("x")
    Q = _disc_even_poly_in_x(P, s, x_sym)
    roots_x = sp.nroots(Q, n=int(args.dps), maxsteps=200)
    abs_theta, theta_mp, s_mp, x_mp = _nearest_theta_branch_point_from_x_roots(roots_x, int(args.dps))

    # Format as a ± b i blocks (we store magnitudes and use \pm/\mp in TeX).
    import mpmath as mp

    x_re = mp.re(x_mp)
    x_im_abs = abs(mp.im(x_mp))
    s_re = mp.re(s_mp)
    s_im_abs = abs(mp.im(s_mp))
    theta_re = mp.re(theta_mp)
    theta_im_abs = abs(mp.im(theta_mp))
    theta_abs = abs_theta
    re_s_minus_sqrt3 = x_re * 0  # placeholder to keep mp types
    try:
        re_s_minus_sqrt3 = mp.re(s_mp) - mp.sqrt(3)
    except Exception:
        re_s_minus_sqrt3 = mp.re(s_mp) - mp.sqrt(mp.mpf(3))

    nearest = NearestComplexBranchPoint(
        x_re=_mp_nstr(x_re, 16),
        x_im_abs=_mp_nstr(x_im_abs, 16),
        s_re=_mp_nstr(s_re, 16),
        s_im_abs=_mp_nstr(s_im_abs, 16),
        theta_re=_mp_nstr(theta_re, 16),
        theta_im_abs=_mp_nstr(theta_im_abs, 16),
        theta_abs=_mp_nstr(theta_abs, 16),
        re_s_minus_sqrt3=_mp_nstr(re_s_minus_sqrt3, 16),
    )

    # Threshold modulus for strict convergence of local Taylor series in the angle variable.
    # If theta_m = 2*pi/m, then theta_m < R_theta is guaranteed for m >= floor(2*pi/R_theta)+1.
    R_theta = float(theta_abs)
    m_min_convergent = int(math.floor((2.0 * math.pi) / R_theta) + 1)

    payload = {
        "disc_s": str(disc_norm),
        "disc_s_latex": sp.latex(disc_norm),
        "disc_x": str(Q.as_expr()),
        "disc_x_latex": sp.latex(Q.as_expr()),
        "roots_real_in_minus2_2": [str(r) for r in uniq],
        "roots_x_all": [str(r) for r in roots_x],
        "branch_points_positive": [asdict(bp) for bp in bps],
        "nearest_complex_branch_point": asdict(nearest),
        "theta_radius": str(theta_abs),
        "m_min_convergent_for_theta_2pi_over_m": m_min_convergent,
    }

    jout = Path(args.json_out)
    jout.parent.mkdir(parents=True, exist_ok=True)
    jout.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[hatdelta-disc] wrote {jout}", flush=True)

    # LaTeX equation block.
    eq = Path(args.tex_eq_out)
    eq.parent.mkdir(parents=True, exist_ok=True)

    def _poly_multiline_tex(expr: sp.Expr, var: sp.Symbol, *, max_line_len: int = 110) -> List[str]:
        """Format a univariate integer polynomial as multiple TeX lines.

        Output lines are meant to be used inside an amsmath aligned environment.
        """
        P1 = sp.Poly(sp.expand(expr), var, domain=sp.ZZ)
        terms = []
        for (e,), coeff in sorted(P1.as_dict().items(), key=lambda kv: -int(kv[0][0])):
            coeff = sp.Integer(coeff)
            if coeff == 0:
                continue
            if e == 0:
                terms.append(coeff)
            else:
                terms.append(coeff * (var ** int(e)))

        if not terms:
            return ["0"]

        parts: List[str] = []
        for idx, t in enumerate(terms):
            t = sp.expand(t)
            sign = -1 if t.could_extract_minus_sign() else 1
            t_abs = -t if sign < 0 else t
            tex = sp.latex(t_abs)
            if idx == 0:
                parts.append(("- " + tex) if sign < 0 else tex)
            else:
                parts.append(("- " + tex) if sign < 0 else ("+ " + tex))

        lines_out: List[str] = []
        cur = parts[0]
        for p in parts[1:]:
            if len(cur) + 1 + len(p) > max_line_len:
                lines_out.append(cur)
                cur = p
            else:
                cur = cur + " " + p
        lines_out.append(cur)
        return lines_out

    disc_lines = _poly_multiline_tex(disc_norm, s, max_line_len=95)
    eq_lines: List[str] = []
    eq_lines.append("% Auto-generated; do not edit by hand.")
    eq_lines.append("\\begin{equation}\\label{eq:sync_kernel_hatdelta_discriminant}")
    eq_lines.append("\\boxed{")
    eq_lines.append("\\begin{aligned}")
    if len(disc_lines) == 1:
        eq_lines.append("\\mathrm{Disc}_w\\bigl(\\widehat\\Delta(w,s)\\bigr)&=" + disc_lines[0])
    else:
        eq_lines.append("\\mathrm{Disc}_w\\bigl(\\widehat\\Delta(w,s)\\bigr)&=" + disc_lines[0] + "\\\\")
        for ln in disc_lines[1:-1]:
            eq_lines.append("&" + ln + "\\\\")
        eq_lines.append("&" + disc_lines[-1])
    eq_lines.append("\\end{aligned}")
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

    # LaTeX table: nearest complex branch point (controls true analytic radius around theta=0).
    tab2 = Path(args.tex_tab_complex_out)
    tab2.parent.mkdir(parents=True, exist_ok=True)
    t2: List[str] = []
    t2.append("\\begin{table}[H]")
    t2.append("\\centering")
    t2.append("\\scriptsize")
    t2.append("\\setlength{\\tabcolsep}{6pt}")
    t2.append(
        "\\caption{Nearest complex discriminant root in the $x=s^2$ reduction and its image in the angle plane "
        "$\\theta=2\\arccos(s/2)$ (principal branch). This pair controls the true analytic radius around $\\theta=0$ "
        "for local expansions on the unit-circle twist locus.}"
    )
    t2.append("\\label{tab:sync_kernel_hatdelta_nearest_complex_branch_point}")
    t2.append("\\begin{tabular}{r r r r r}")
    t2.append("\\toprule")
    t2.append("$x_\\star$ & $s_\\star$ & $\\theta_\\star$ & $|\\theta_\\star|$ & $\\Re(s_\\star)-\\sqrt3$\\\\")
    t2.append("\\midrule")
    t2.append(
        f"${nearest.x_re} \\mp {nearest.x_im_abs}\\,i$ & "
        f"${nearest.s_re} \\mp {nearest.s_im_abs}\\,i$ & "
        f"${nearest.theta_re} \\pm {nearest.theta_im_abs}\\,i$ & "
        f"${nearest.theta_abs}$ & "
        f"${nearest.re_s_minus_sqrt3}$\\\\"
    )
    t2.append("\\bottomrule")
    t2.append("\\end{tabular}")
    t2.append("\\end{table}")
    tab2.write_text("\n".join(t2) + "\n", encoding="utf-8")
    print(f"[hatdelta-disc] wrote {tab2}", flush=True)
    print("[hatdelta-disc] done", flush=True)


if __name__ == "__main__":
    main()

