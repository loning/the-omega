from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import math

    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Wedge

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(9.4, 3.1))
    fig.suptitle("Stairway method (schematic): scan points → slice values → Fourier modes", fontsize=12)

    # Panel 1: scan orbit on R/Z.
    ax1.set_aspect("equal")
    ax1.set_axis_off()
    ax1.add_patch(Circle((0.0, 0.0), 1.0, fill=False, lw=1.2, ec="black"))
    phi = (1.0 + 5.0**0.5) / 2.0
    alpha = 1.0 / phi
    N = 32
    xs = (alpha * np.arange(N)) % 1.0
    angles = 2.0 * math.pi * xs
    ax1.plot(np.cos(angles), np.sin(angles), "o", ms=3.6, color="black")
    ax1.add_patch(Wedge((0.0, 0.0), 1.0, 0.0, 360.0 * (1.0 - alpha), width=0.18, fc="#90caf9", ec="none"))
    ax1.text(0.0, 1.25, r"scan on $\mathbb{R}/\mathbb{Z}$", ha="center", fontsize=10)
    ax1.text(0.0, 1.08, r"$x_t=x_0+t\alpha\ (\mathrm{mod}\,1)$", ha="center", fontsize=9)

    # Panel 2: a height slice F_y(x) with sample points.
    xgrid = np.linspace(0.0, 1.0, 600, endpoint=False)
    y0 = 0.55
    # A schematic periodic slice (not data): a few Fourier modes damped by height.
    F = np.cos(2.0 * math.pi * xgrid) * math.exp(-2.0 * math.pi * y0) + 0.45 * np.cos(4.0 * math.pi * xgrid + 0.4) * math.exp(
        -4.0 * math.pi * y0
    )
    ax2.plot(xgrid, F, color="black", lw=1.3)
    Fs = np.cos(2.0 * math.pi * xs) * math.exp(-2.0 * math.pi * y0) + 0.45 * np.cos(4.0 * math.pi * xs + 0.4) * math.exp(
        -4.0 * math.pi * y0
    )
    ax2.plot(xs, Fs, "o", ms=3.2, color="#1e88e5")
    ax2.set_xlim(0.0, 1.0)
    ax2.set_xlabel(r"$x\in[0,1)$")
    ax2.set_title(r"height slice $F_y(x)=f(x+iy)$", fontsize=10.5)
    ax2.grid(alpha=0.18)

    # Panel 3: Fourier magnitudes (schematic).
    nmax = 7
    # Use a dense grid as a "reference" for visualization of mode weights.
    fft = np.fft.rfft(F) / len(F)
    mags = np.abs(fft[:nmax])
    ns = np.arange(nmax)
    ax3.bar(ns, mags, color="#c8e6c9", edgecolor="black", linewidth=0.7)
    ax3.set_xlabel(r"mode index $n$")
    ax3.set_title(r"modes in $q$-expansion", fontsize=10.5)
    ax3.set_xticks(ns)
    ax3.set_ylim(0.0, max(1e-6, float(mags.max())) * 1.25)
    ax3.grid(axis="y", alpha=0.18)
    ax3.text(0.02, 0.90, r"$a_n=\int_0^1 F_y(x)e^{-2\pi i n x}\,dx$", transform=ax3.transAxes, fontsize=9)

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))

    out_pdf = out_dir / "fig02_stairway_pipeline.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig02_stairway_pipeline.png", bbox_inches="tight")
    plt.close(fig)


