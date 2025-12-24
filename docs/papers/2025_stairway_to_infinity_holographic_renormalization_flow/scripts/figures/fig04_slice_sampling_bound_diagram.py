from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import math

    import numpy as np
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.2))
    fig.suptitle("Finite-$N$ control (schematic): variation × discrepancy", fontsize=12)

    # A schematic height-slice integrand and samples (left).
    phi = (1.0 + 5.0**0.5) / 2.0
    alpha = 1.0 / phi
    N = 48
    xs = (alpha * np.arange(N)) % 1.0
    xgrid = np.linspace(0.0, 1.0, 800, endpoint=False)
    y0 = 0.55
    n_mode = 2

    F = np.cos(2.0 * math.pi * xgrid) * math.exp(-2.0 * math.pi * y0) + 0.45 * np.cos(4.0 * math.pi * xgrid + 0.4) * math.exp(
        -4.0 * math.pi * y0
    )
    # Real part of g_{n,y}(x)=F_y(x)e^{-2π i n x}.
    g = F * np.cos(2.0 * math.pi * n_mode * xgrid)

    ax1.plot(xgrid, g, color="black", lw=1.3)
    Fs = np.cos(2.0 * math.pi * xs) * math.exp(-2.0 * math.pi * y0) + 0.45 * np.cos(4.0 * math.pi * xs + 0.4) * math.exp(
        -4.0 * math.pi * y0
    )
    gs = Fs * np.cos(2.0 * math.pi * n_mode * xs)
    ax1.plot(xs, gs, "o", ms=3.0, color="#1e88e5", alpha=0.85)
    ax1.set_xlim(0.0, 1.0)
    ax1.set_xlabel(r"$x$")
    ax1.set_title(r"oscillatory integrand $g_{n,y}(x)$ + samples", fontsize=10.5)
    ax1.grid(alpha=0.18)

    # Discrepancy as a CDF gap (right).
    xs_sorted = np.sort(xs)
    Fn = np.arange(1, len(xs_sorted) + 1) / len(xs_sorted)
    ax2.step(xs_sorted, Fn, where="post", color="black", lw=1.3, label=r"empirical $F_N(x)$")
    ax2.plot([0.0, 1.0], [0.0, 1.0], color="#1e88e5", lw=1.2, label=r"uniform $x$")
    ax2.set_xlim(0.0, 1.0)
    ax2.set_ylim(0.0, 1.02)
    ax2.set_xlabel(r"$x$")
    ax2.set_title(r"star discrepancy $D_N^\ast=\sup_x|F_N(x)-x|$", fontsize=10.5)
    ax2.grid(alpha=0.18)
    ax2.legend(frameon=False, fontsize=9, loc="lower right")

    fig.text(
        0.02,
        0.02,
        r"$|\widehat a_{n,N}(y)-a_n|\ \leq\ \mathrm{e}^{2\pi n y}\,\mathrm{Var}(g_{n,y})\,D_N^\ast(P_N)"
        r"\qquad (g_{n,y}(x)=F_y(x)\mathrm{e}^{-2\pi i n x})$",
        fontsize=9.5,
    )

    fig.tight_layout(rect=(0.0, 0.08, 1.0, 0.90))

    out_pdf = out_dir / "fig04_slice_sampling_bound_diagram.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig04_slice_sampling_bound_diagram.png", bbox_inches="tight")
    plt.close(fig)


