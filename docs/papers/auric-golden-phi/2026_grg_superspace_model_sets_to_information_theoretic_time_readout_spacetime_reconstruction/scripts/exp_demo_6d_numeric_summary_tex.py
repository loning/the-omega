#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a small LaTeX numeric summary for the 6D worked example.

This script is intentionally minimal and dependency-free. It reads the JSON
artifact produced by demo_6d_icosa_fingerprints.py and writes a LaTeX snippet
that can be \\input into the paper.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def _fmt(x: Any, nd: int = 4) -> str:
    try:
        xf = float(x)
    except Exception:
        return str(x)
    if abs(xf) >= 1000:
        return f"{xf:.0f}"
    if abs(xf) >= 10:
        return f"{xf:.2f}"
    return f"{xf:.{nd}f}"


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--in-json", type=str, required=True)
    ap.add_argument("--out-tex", type=str, required=True)
    ap.add_argument("--eps-ref", type=str, default="0.05")
    args = ap.parse_args()

    jpath = Path(args.in_json)
    payload: Dict[str, Any] = json.loads(jpath.read_text(encoding="utf-8"))

    eps_ref = str(args.eps_ref)
    by_eps = payload["symbolic"]["by_eps"]
    if eps_ref not in by_eps:
        # Fall back to the middle epsilon key.
        keys = sorted(by_eps.keys(), key=lambda s: float(s))
        eps_ref = keys[len(keys) // 2] if keys else eps_ref

    S = by_eps[eps_ref]
    summ = S["summary"]
    mis = S.get("mismatch", {})
    corr = S.get("raw_bits_correlated", {})
    raw = S.get("raw_bits", {})
    tau_mk = raw.get("tau_sequential_markov", {})

    one = payload.get("one_dim_factor", {})
    approx = one.get("rational_approx_deviation", [])
    approx0 = approx[0] if approx else {}

    lines = []
    lines.append(r"\begin{center}")
    lines.append(r"\begin{tabular}{ll}")
    lines.append(r"\hline")
    lines.append(r"\textbf{Quantity} & \textbf{Value} \\")
    lines.append(r"\hline")
    lines.append(r"$\epsilon$ (resolution parameter) & " + _fmt(eps_ref, 4) + r" \\")
    lines.append(r"$\widehat h$ (block-entropy proxy) & " + _fmt(summ.get("h_proxy"), 4) + r" \\")
    lines.append(r"$h_{\mathrm{theory}}=\mathbb{E}[H_b(\kappa_\epsilon)]$ & " + _fmt(summ.get("h_theory"), 4) + r" \\")
    lines.append(r"$\widehat h_{\mathrm{Markov}}$ (sequential log-loss) & " + _fmt(summ.get("h_proxy_markov"), 4) + r" \\")
    lines.append(r"$\widehat\tau(t)$ Markov length $T_0$ & " + _fmt(tau_mk.get("T"), 0) + r" \\")
    lines.append(r"$\varepsilon$ (eps vs eps2 mismatch) & " + _fmt(mis.get("epsilon_eps_vs_eps2"), 4) + r" \\")
    lines.append(r"$\epsilon_2$ (used for mismatch) & " + _fmt(mis.get("eps2"), 4) + r" \\")
    lines.append(r"$\varepsilon$ (iid vs correlated mismatch) & " + _fmt(mis.get("epsilon_iid_vs_correlated"), 4) + r" \\")
    lines.append(r"correlated noise $\rho$ & " + _fmt(corr.get("rho"), 3) + r" \\")
    lines.append(r"lag-1 autocorr(bits) & " + _fmt(corr.get("lag1_autocorr"), 3) + r" \\")
    if approx0:
        lines.append(r"\hline")
        lines.append(r"$\alpha$ (1D factor slope) & " + _fmt(one.get("alpha"), 6) + r" \\")
        lines.append(r"$p/q$ (convergent) & " + f"{approx0.get('p', '?')}/{approx0.get('q', '?')}" + r" \\")
        lines.append(r"$|\alpha-p/q|$ & " + _fmt(approx0.get("abs_alpha_minus_p_over_q"), 6) + r" \\")
        lines.append(r"max phase error (over $N$) & " + _fmt(approx0.get("max_phase_error_over_N"), 6) + r" \\")
        lines.append(r"Hamming mismatch (bits, over $N$) & " + _fmt(approx0.get("hamming_mismatch_bits_over_N"), 4) + r" \\")
        lines.append(r"periodicity error (alpha at $q$) & " + _fmt(approx0.get("periodicity_error_alpha_at_q"), 4) + r" \\")
        lines.append(r"periodicity error ($p/q$ at $q$) & " + _fmt(approx0.get("periodicity_error_p_over_q_at_q"), 4) + r" \\")
    lines.append(r"\hline")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{center}")
    lines.append("")

    out = Path(args.out_tex)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[exp_demo_6d] wrote: {out}", flush=True)


if __name__ == "__main__":
    main()

