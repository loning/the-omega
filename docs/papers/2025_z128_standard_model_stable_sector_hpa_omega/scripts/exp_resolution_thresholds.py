# -*- coding: utf-8 -*-
"""
Resolution-threshold table for the Fibonacci-stable sector counts |X_m|.

We connect the continuous resolution coordinate
  r(mu) = log(mu/m_e) / log(phi) = log_phi(mu/m_e)
to a discrete window-length uplift m -> m+1 via a simple calibration:
  r_step := 2*pi
  threshold depth for window length m is r_th(m) = (m-6) * r_step
  threshold energy is mu_th(m) = m_e * phi^{r_th(m)}.

This yields a concrete, auditable staircase template for where Fibonacci-structured
stable-type count uplifts may occur if effective window length changes with energy.

Outputs:
  - sections/generated/resolution_thresholds_rows.tex
  - figures/resolution_thresholds_staircase.{pdf,png} (optional; requires matplotlib)

Only the Python standard library is required for the table fragment. Plotting is optional.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

from common_constants import M_E_GEV, PHI


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


def xm_counts(m: int) -> Tuple[int, int, int]:
    # |X_m| = F_{m+2}. Boundary count is F_{m-2} for m>=4; cyclic is the remainder.
    total = fib(m + 2)
    bdry = fib(m - 2) if m >= 4 else 0
    cyc = total - bdry
    return total, cyc, bdry


def mu_threshold(m: int, r_step: float) -> Tuple[float, float]:
    r_th = float(m - 6) * r_step
    mu = M_E_GEV * (PHI ** r_th)
    return r_th, mu


def fmt_mu(mu: float) -> str:
    if mu == 0.0:
        return "0"
    if mu < 1.0e-3 or mu >= 1.0e4:
        exp = int(math.floor(math.log10(abs(mu))))
        mant = mu / (10.0**exp)
        return f"{mant:.6g}\\times 10^{{{exp}}}"
    return f"{mu:.6g}"


def try_plot(thresholds: List[Tuple[int, float, float]]) -> None:
    # Optional plotting: requires matplotlib.
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return

    # Step plot in log10(mu/GeV).
    xs: List[float] = []
    ys: List[float] = []
    for m, _r, mu in thresholds:
        xs.append(math.log10(mu))
        ys.append(float(m))

    fig = plt.figure(figsize=(6.5, 3.2))
    ax = fig.add_subplot(1, 1, 1)
    ax.step(xs, ys, where="post", linewidth=2.0)
    ax.set_xlabel("log10(threshold energy [GeV])")
    ax.set_ylabel("effective window length m")
    ax.set_title("Resolution-uplift staircase (r_step = 2*pi)")
    ax.grid(True, alpha=0.25)

    # Key physical anchors (labels are narrative only; values are from the same calibration).
    x_of_m: dict[int, float] = {m: math.log10(mu) for m, _r, mu in thresholds}
    anchors = [
        (6, "m=6: electron anchor"),
        (8, "m=8: QCD (~0.2 GeV)"),
        (10, "m=10: electroweak (Z pole / Higgs sector)"),
    ]
    for m, label in anchors:
        if m not in x_of_m:
            continue
        x = x_of_m[m]
        y = float(m)
        ax.scatter([x], [y], s=28)
        ax.annotate(
            label,
            xy=(x, y),
            xytext=(8, 8),
            textcoords="offset points",
            fontsize=8,
            ha="left",
            va="bottom",
            arrowprops={"arrowstyle": "->", "linewidth": 0.8},
        )

    root = Path(__file__).resolve().parent.parent
    fig_dir = root / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig_path_pdf = fig_dir / "resolution_thresholds_staircase.pdf"
    fig_path_png = fig_dir / "resolution_thresholds_staircase.png"
    fig.tight_layout()
    fig.savefig(fig_path_pdf)
    fig.savefig(fig_path_png, dpi=200)
    plt.close(fig)


def main() -> None:
    r_step = 2.0 * math.pi
    m_list = list(range(6, 17))  # 6..16 (electron to ultra-high energies in this calibration)

    rows: List[str] = []
    thresholds: List[Tuple[int, float, float]] = []

    prev_total = None
    for m in m_list:
        total, cyc, bdry = xm_counts(m)
        d_total = 0 if prev_total is None else (total - prev_total)
        prev_total = total

        r_th, mu = mu_threshold(m, r_step=r_step)
        thresholds.append((m, r_th, mu))
        rows.append(
            f"{m} & {r_th:.3f} & ${fmt_mu(mu)}$ & {total} & {cyc} & {bdry} & {d_total} \\\\"
        )

    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "resolution_thresholds_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/resolution_thresholds_rows.tex")

    try_plot(thresholds)


if __name__ == "__main__":
    main()


