#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Horizon spectral measure: endpoint window mass asymptotic (audit script).

Outputs:
- artifacts/export/horizon_mu_endpoint_window_asymptotic.json
- sections/generated/tab_horizon_mu_endpoint_window_asymptotic.tex

This script performs a small numerical audit of the endpoint-window mass law for the
horizon spectral measure μ_ζ on the unit circle, as described in
Theorem (endpoint-window asymptotic) in the appendix.

Under RH, the spectral measure admits an atomic representation supported on Cayley
images of critical-line zeros, with weights (1+γ^2)^{-1}. For an endpoint angular
window I_ε around ξ=-1, this yields

  μ_ζ(I_ε) = 2 * Σ_{γ >= cot(ε/2)} (1+γ^2)^{-1},

and the first-order asymptotic prediction is

  μ_ζ(I_ε) ~ (ε/(2π)) * (log(1/(π ε)) + 1),  ε↓0.

We approximate the sum using mpmath.zetazero(k) up to a cutoff γ_cut, and add a
small tail correction based on the Riemann–von Mangoldt main term.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from typing import Dict, List, Sequence

import mpmath as mp

from common_paths import export_dir, generated_dir


@dataclass(frozen=True)
class Row:
    eps: mp.mpf
    T_eps: mp.mpf
    k_tail: int
    mu_trunc: mp.mpf
    mu_tail_est: mp.mpf
    mu_est: mp.mpf
    mu_asymp: mp.mpf


def _asymp_mu_eps(eps: mp.mpf) -> mp.mpf:
    # μ_ζ(I_ε) ~ (ε/(2π)) * (log(1/(π ε)) + 1)
    return (eps / (2 * mp.pi)) * (mp.log(1 / (mp.pi * eps)) + 1)


def _tail_estimate(gamma_cut: mp.mpf) -> mp.mpf:
    # Tail from γ_cut to ∞ using the first-order RVM-based approximation:
    # 2 ∫_{γ_cut}^∞ (1/(1+t^2)) dN(t) ~ (1/π) (log(γ_cut/(2π)) + 1)/γ_cut.
    return (1 / mp.pi) * (mp.log(gamma_cut / (2 * mp.pi)) + 1) / gamma_cut


def _compute_zeros_upto(gamma_max: mp.mpf, *, max_zeros: int) -> List[mp.mpf]:
    gammas: List[mp.mpf] = []
    t0 = time.time()
    for k in range(1, max_zeros + 1):
        z = mp.zetazero(k)
        gamma = abs(mp.im(z))
        if gamma > gamma_max:
            break
        gammas.append(gamma)
        if k % 200 == 0:
            dt = time.time() - t0
            print(
                f"[exp_horizon_mu_endpoint_window_asymptotic] zeros={k} gamma~{float(gamma):.3f} elapsed_s={dt:.2f}",
                flush=True,
            )
    if not gammas:
        raise RuntimeError("no zeros collected (gamma_max too small?)")
    return gammas


def _suffix_sums(weights: Sequence[mp.mpf]) -> List[mp.mpf]:
    out: List[mp.mpf] = [mp.mpf("0")] * (len(weights) + 1)
    s = mp.mpf("0")
    for i in range(len(weights) - 1, -1, -1):
        s += weights[i]
        out[i] = s
    out[len(weights)] = mp.mpf("0")
    return out


def _bisect_left_mpf(xs: Sequence[mp.mpf], x: mp.mpf) -> int:
    lo, hi = 0, len(xs)
    while lo < hi:
        mid = (lo + hi) // 2
        if xs[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def _write_table(rows: List[Row], gamma_cut: mp.mpf, n_zeros: int) -> None:
    lines: List[str] = []
    lines.append("\\begin{table}[H]\n")
    lines.append("\\centering\n")
    lines.append("\\small\n")
    lines.append("\\begin{tabular}{rrrrrr}\n")
    lines.append("\\toprule\n")
    lines.append(
        "$\\varepsilon$ & $T_{\\varepsilon}$ & $K$ & $\\widehat\\mu_{\\zeta}(I_{\\varepsilon})$ & asymp & ratio\\\\\n"
    )
    lines.append("\\midrule\n")
    for r in rows:
        eps = float(r.eps)
        T = float(r.T_eps)
        K = int(r.k_tail)
        mu_est = float(r.mu_est)
        mu_asymp = float(r.mu_asymp)
        ratio = float(r.mu_est / r.mu_asymp) if r.mu_asymp != 0 else float("nan")
        lines.append(
            f"{eps:.4g} & {T:.4g} & {K:d} & {mu_est:.6g} & {mu_asymp:.6g} & {ratio:.4g}\\\\\n"
        )
    lines.append("\\bottomrule\n")
    lines.append("\\end{tabular}\n")
    lines.append(
        "\\caption{端点角窗质量的数值审计：以临界线零点的 Cayley 原子化近似 $\\mu_{\\zeta}(I_{\\varepsilon})$，并与一阶渐近 $\\frac{\\varepsilon}{2\\pi}(\\log\\frac{1}{\\pi\\varepsilon}+1)$ 比较。表中 $K$ 为纳入求和的零点个数（满足 $\\gamma\\ge T_{\\varepsilon}$ 且 $\\gamma\\le \\gamma_{\\mathrm{cut}}$）。本表使用零点至截止 $\\gamma_{\\mathrm{cut}}\\approx "
        f"{float(gamma_cut):.6g}"
        "$（共 "
        f"{n_zeros}"
        " 个），并对 $\\gamma>\\gamma_{\\mathrm{cut}}$ 的尾项加入基于 Riemann--von Mangoldt 主项的一阶估计。}\n"
    )
    lines.append("\\label{tab:horizon-mu-endpoint-window-asymptotic}\n")
    lines.append("\\end{table}\n")

    p = generated_dir() / "tab_horizon_mu_endpoint_window_asymptotic.tex"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Audit endpoint window mass asymptotic for horizon spectral measure."
    )
    ap.add_argument("--dps", type=int, default=80, help="mpmath decimal precision.")
    ap.add_argument(
        "--gamma-max",
        type=float,
        default=1500.0,
        help="Collect zeros up to this gamma cutoff (positive imaginary part).",
    )
    ap.add_argument(
        "--max-zeros",
        type=int,
        default=4000,
        help="Safety cap on number of zeros to query.",
    )
    ap.add_argument(
        "--eps",
        type=float,
        nargs="*",
        default=[0.25, 0.2, 0.15, 0.12, 0.1, 0.08, 0.06, 0.05],
        help="List of endpoint window half-widths ε (radians).",
    )
    args = ap.parse_args()

    mp.mp.dps = int(args.dps)
    gamma_max = mp.mpf(str(args.gamma_max))

    t0 = time.time()
    gammas = _compute_zeros_upto(gamma_max, max_zeros=int(args.max_zeros))
    gamma_cut = gammas[-1]
    n_zeros = len(gammas)
    weights = [mp.mpf("1") / (mp.mpf("1") + g * g) for g in gammas]
    suff = _suffix_sums(weights)
    tail = _tail_estimate(gamma_cut)

    rows: List[Row] = []
    for eps_f in list(args.eps):
        eps = mp.mpf(str(eps_f))
        if eps <= 0 or eps >= mp.pi:
            raise ValueError("eps must satisfy 0 < eps < pi")
        T_eps = mp.mpf("1") / mp.tan(eps / 2)
        i0 = _bisect_left_mpf(gammas, T_eps)
        k_tail = max(0, n_zeros - i0)
        mu_trunc = mp.mpf("2") * suff[i0]
        mu_est = mu_trunc + tail
        mu_asymp = _asymp_mu_eps(eps)
        rows.append(
            Row(
                eps=eps,
                T_eps=T_eps,
                k_tail=k_tail,
                mu_trunc=mu_trunc,
                mu_tail_est=tail,
                mu_est=mu_est,
                mu_asymp=mu_asymp,
            )
        )

    # Write JSON audit.
    out_json = export_dir() / "horizon_mu_endpoint_window_asymptotic.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, object] = {
        "mp_dps": int(args.dps),
        "gamma_max_requested": float(args.gamma_max),
        "gamma_cut": float(gamma_cut),
        "n_zeros": int(n_zeros),
        "tail_estimate": float(tail),
        "rows": [
            {
                "eps": float(r.eps),
                "T_eps": float(r.T_eps),
                "K": int(r.k_tail),
                "mu_trunc": float(r.mu_trunc),
                "mu_tail_est": float(r.mu_tail_est),
                "mu_est": float(r.mu_est),
                "mu_asymp": float(r.mu_asymp),
                "ratio": float(r.mu_est / r.mu_asymp) if r.mu_asymp != 0 else None,
            }
            for r in rows
        ],
        "elapsed_s": float(time.time() - t0),
    }
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Write TeX table.
    _write_table(rows, gamma_cut=gamma_cut, n_zeros=n_zeros)

    dt = time.time() - t0
    print(
        f"[exp_horizon_mu_endpoint_window_asymptotic] done zeros={n_zeros} gamma_cut={float(gamma_cut):.6g} elapsed_s={dt:.2f}",
        flush=True,
    )


if __name__ == "__main__":
    main()

