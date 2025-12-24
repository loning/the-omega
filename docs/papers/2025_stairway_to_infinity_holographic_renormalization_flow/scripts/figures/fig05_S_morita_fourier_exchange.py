from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(9.4, 3.1))
    fig.suptitle(r"$S$-inversion as a scale exchange (schematic)", fontsize=12)

    # Panel 1: cusp depth exchange (x=0 slice of Im(-1/τ)=y/(x^2+y^2)).
    y = np.logspace(-1, 1, 300)
    y_inv = 1.0 / y
    ax1.plot(y, y_inv, color="black", lw=1.3)
    ax1.plot(y, y, color="#1e88e5", lw=1.0, alpha=0.6)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel(r"$y=\Im\tau$")
    ax1.set_ylabel(r"$\Im(-1/\tau)$ (at $x=0$)")
    ax1.set_title(r"modular $S:\ \tau\mapsto -1/\tau$", fontsize=10.5)
    ax1.grid(alpha=0.18)
    ax1.text(0.05, 0.92, r"deep cusp $\leftrightarrow$ shallow cusp", transform=ax1.transAxes, fontsize=9, va="top")

    # Panel 2: Morita exchange of the noncommutative torus parameter (schematic α↔1/α).
    a = np.logspace(-1, 1, 300)
    a_inv = 1.0 / a
    ax2.plot(a, a_inv, color="black", lw=1.3)
    ax2.plot(a, a, color="#1e88e5", lw=1.0, alpha=0.6)
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel(r"$\alpha$")
    ax2.set_ylabel(r"$\alpha'$")
    ax2.set_title(r"Morita: $A_\alpha \sim A_{\alpha'}$,  $\alpha'=\alpha^{-1}$", fontsize=10.2)
    ax2.grid(alpha=0.18)

    # Panel 3: Fourier swap for the Weyl pair (visual mnemonic).
    ax3.set_axis_off()
    ax3.set_title(r"Fourier swap (Weyl pair)", fontsize=10.5)

    # Unit circle phases e^{2π i k α} for a few modes k.
    cx, cy, rad = 0.34, 0.60, 0.18
    ax3.add_patch(Circle((cx, cy), rad, transform=ax3.transAxes, fill=False, lw=1.1, ec="black"))
    alpha0 = (np.sqrt(5.0) - 1.0) / 2.0
    ks = np.arange(0, 6)
    for k in ks:
        ang = 2.0 * np.pi * k * alpha0
        x = cx + rad * np.cos(ang)
        y0 = cy + rad * np.sin(ang)
        ax3.plot([x], [y0], "o", ms=3.6, color="#1e88e5", transform=ax3.transAxes)
        ax3.text(x, y0, f"{k}", transform=ax3.transAxes, fontsize=8.5, va="center", ha="center")
    ax3.text(0.06, 0.93, r"$U$ shifts $x$", transform=ax3.transAxes, fontsize=9)
    ax3.text(0.06, 0.86, r"$\Rightarrow$ phases in $k$", transform=ax3.transAxes, fontsize=9)
    ax3.text(0.58, 0.72, r"$\widehat U:\ c_k\mapsto e^{2\pi i k\alpha}c_k$", transform=ax3.transAxes, fontsize=9)

    # Index shift for V (multiplication by e^{2π i x}).
    xs = np.linspace(0.12, 0.48, 6)
    for j, x in enumerate(xs):
        ax3.plot([x], [0.14], "o", ms=3.4, color="black", transform=ax3.transAxes)
        ax3.text(x, 0.08, f"{j}", transform=ax3.transAxes, fontsize=8, ha="center")
    ax3.annotate(
        "",
        xy=(0.48, 0.14),
        xytext=(0.12, 0.14),
        xycoords=ax3.transAxes,
        textcoords=ax3.transAxes,
        arrowprops={"arrowstyle": "->", "lw": 1.1, "mutation_scale": 12},
    )
    ax3.text(0.06, 0.36, r"$V$ multiplies by $e^{2\pi i x}$", transform=ax3.transAxes, fontsize=9)
    ax3.text(0.06, 0.28, r"$\Rightarrow$ index shift in $k$", transform=ax3.transAxes, fontsize=9)
    ax3.text(0.58, 0.20, r"$\widehat V:\ c_k\mapsto c_{k-1}$", transform=ax3.transAxes, fontsize=9)

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))

    out_pdf = out_dir / "fig05_S_morita_fourier_exchange.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig05_S_morita_fourier_exchange.png", bbox_inches="tight")
    plt.close(fig)


