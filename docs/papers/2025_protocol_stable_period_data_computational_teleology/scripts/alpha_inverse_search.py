#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experiment 3: exhaustive search for alpha^{-1}(0) in the bounded ansatz
  v(a,b,c)=a*pi^3 + b*pi^2 + c*pi,
with a,b,c >= 0 and a+b+c <= BUDGET.

This script writes a LaTeX row file into:
  sections/generated/alpha_inverse_rows.tex

No third-party dependencies.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple


def fmt_sci_signed(x: float, sig: int = 3) -> str:
    if x == 0.0:
        return "$+0$"
    sign = "+" if x > 0 else "-"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = ax / (10.0**exp)
    mant = round(mant, max(sig - 1, 0))
    if mant >= 10.0:
        mant /= 10.0
        exp += 1
    mant_str = f"{mant:.{max(sig - 1, 0)}f}".rstrip("0").rstrip(".")
    return f"${sign}{mant_str}\\times 10^{{{exp}}}$"


def fmt_sci_unsigned(x: float, sig: int = 2) -> str:
    if x <= 0.0:
        return "$0$"
    exp = int(math.floor(math.log10(x)))
    mant = x / (10.0**exp)
    mant = round(mant, max(sig - 1, 0))
    if mant >= 10.0:
        mant /= 10.0
        exp += 1
    mant_str = f"{mant:.{max(sig - 1, 0)}f}".rstrip("0").rstrip(".")
    return f"${mant_str}\\times 10^{{{exp}}}$"


def write_rows(path: Path, lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = list(lines)
    if out:
        last = out[-1].rstrip()
        if last.endswith("\\\\"):
            last = last[:-2].rstrip()
        out[-1] = last
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def fmt_tex_sci_unsigned(x: float, sig: int = 3) -> str:
    """TeX scientific notation without surrounding $...$."""
    if x <= 0.0:
        return "0"
    exp = int(math.floor(math.log10(x)))
    mant = x / (10.0**exp)
    mant = round(mant, max(sig - 1, 0))
    if mant >= 10.0:
        mant /= 10.0
        exp += 1
    mant_str = f"{mant:.{max(sig - 1, 0)}f}".rstrip("0").rstrip(".")
    return f"{mant_str}\\times 10^{{{exp}}}"


def fmt_latex_int(n: int) -> str:
    """Format an integer with thousands separators as LaTeX-friendly '{,}'."""
    return f"{n:,}".replace(",", "{,}")


def log_phi(n: int) -> float:
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    return math.log(float(n)) / math.log(phi)


def main() -> None:
    TARGET = 137.035999177  # CODATA 2022 central value used in the manuscript
    BUDGET = 10

    rows: List[Tuple[float, int, int, int, float]] = []

    for a in range(BUDGET + 1):
        for b in range(BUDGET + 1 - a):
            for c in range(BUDGET + 1 - a - b):
                if a == 0 and b == 0 and c == 0:
                    continue
                v = a * (math.pi**3) + b * (math.pi**2) + c * math.pi
                err = abs(v - TARGET)
                rows.append((err, a, b, c, v))

    rows.sort(key=lambda t: t[0])
    best = rows[0]
    second = rows[1]

    print("Best:", best)
    print("Second:", second)
    print("Relative error best:", best[0] / TARGET)
    print("Relative error second:", second[0] / TARGET)
    print("Gap ratio (second/best):", second[0] / best[0])

    # Best-vs-second-best margin in absolute error, for robustness/uniqueness certificates.
    margin = float(second[0]) - float(best[0])

    # A closed sufficient horizon N guaranteeing uniqueness stability under a pi-certificate
    # via Corollary (uniqueness threshold) in the paper:
    #   57*B*4*(2+log_phi N)/N < margin/2.
    def lhs(n: int) -> float:
        return (57.0 * float(BUDGET) * 4.0 * (2.0 + log_phi(n))) / float(n)

    rhs = 0.5 * margin
    n_hi = 1
    while lhs(n_hi) >= rhs:
        n_hi *= 2
    n_lo = n_hi // 2
    while n_lo + 1 < n_hi:
        n_mid = (n_lo + n_hi) // 2
        if lhs(n_mid) < rhs:
            n_hi = n_mid
        else:
            n_lo = n_mid
    n_threshold = n_hi

    eps_pi_max = margin / (2.0 * 57.0 * float(BUDGET))

    topn = 10
    latex_lines: List[str] = []
    for err, a, b, c, v in rows[:topn]:
        delta = v - TARGET
        rel = abs(delta) / TARGET
        latex_lines.append(
            f"$({a},{b},{c})$ & {a+b+c} & {v:.10f} & {fmt_sci_signed(delta)} & {fmt_sci_unsigned(rel)} \\\\"
        )

    root = Path(__file__).resolve().parent.parent
    gen = root / "sections" / "generated"
    write_rows(gen / "alpha_inverse_rows.tex", latex_lines)

    # Additional auditable snippets for the manuscript text
    write_rows(gen / "alpha_gap_margin.tex", [fmt_tex_sci_unsigned(margin, sig=3)])
    write_rows(gen / "alpha_gap_best_abs.tex", [fmt_tex_sci_unsigned(float(best[0]), sig=3)])
    write_rows(gen / "alpha_gap_second_abs.tex", [fmt_tex_sci_unsigned(float(second[0]), sig=3)])
    write_rows(gen / "alpha_uniqueness_N.tex", [fmt_latex_int(int(n_threshold))])
    write_rows(gen / "alpha_eps_pi_max.tex", [fmt_tex_sci_unsigned(float(eps_pi_max), sig=3)])

    print(f"\nWrote LaTeX rows into: {gen}")
    print("File: alpha_inverse_rows.tex")
    print("Snippets: alpha_gap_margin.tex, alpha_uniqueness_N.tex, alpha_eps_pi_max.tex")

    print("\nTop 10 candidates:")
    for err, a, b, c, v in rows[:topn]:
        print(
            f"(a,b,c)=({a},{b},{c}) sum={a+b+c} v={v:.10f} err={v-TARGET:+.3e} rel={err/TARGET:.3e}"
        )

    print("\nMargin m (second-best abs error minus best abs error):", margin)
    print("Certified uniqueness N-threshold (sufficient):", n_threshold)
    print("Max pi-certificate error eps_pi_max (sufficient):", eps_pi_max)


if __name__ == "__main__":
    main()


