from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import math

    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Wedge

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(9.2, 3.2))
    fig.suptitle("Three interfaces: scan orbit, cusp parameter, and discrete modes", fontsize=12)

    # Panel 1: scan orbit on a circle with a readout window.
    ax1.set_aspect("equal")
    ax1.set_axis_off()
    ax1.add_patch(Circle((0.0, 0.0), 1.0, fill=False, lw=1.2, ec="black"))
    phi = (1.0 + 5.0**0.5) / 2.0
    alpha = 1.0 / phi
    N = 16
    xs = (alpha * np.arange(N)) % 1.0
    angles = 2.0 * math.pi * xs
    ax1.plot(np.cos(angles), np.sin(angles), "o", ms=4.0, color="black")
    # Canonical window W=[0,1-alpha) as an arc.
    theta1 = 0.0
    theta2 = 360.0 * (1.0 - alpha)
    ax1.add_patch(Wedge((0.0, 0.0), 1.0, theta1, theta2, width=0.18, facecolor="#90caf9", edgecolor="none"))
    ax1.text(0.0, -1.35, r"$x_t=x_0+t\alpha\ (\mathrm{mod}\,1)$", ha="center", fontsize=9)
    ax1.text(0.0, -1.55, r"window $W\subset\mathbb{R}/\mathbb{Z}$", ha="center", fontsize=9)
    ax1.set_title("Scan on $\\mathbb{R}/\\mathbb{Z}$", fontsize=10.5)

    # Panel 2: cusp parameter magnitude |q| = exp(-2*pi*y).
    ys = np.linspace(0.0, 2.2, 400)
    qabs = np.exp(-2.0 * math.pi * ys)
    ax2.plot(ys, qabs, color="black", lw=1.4)
    ax2.set_ylim(0.0, 1.05)
    ax2.set_xlim(0.0, 2.2)
    ax2.set_xlabel(r"height $y=\Im\tau$")
    ax2.set_ylabel(r"$|q|$")
    ax2.set_title(r"Cusp coordinate $q=\mathrm{e}^{2\pi i\tau}$", fontsize=10.5)
    ax2.text(0.10, 0.18, r"$|q|=\mathrm{e}^{-2\pi y}$", fontsize=9)

    # Panel 3: discrete integer-indexed modes (schematic spectrum).
    ns = np.arange(0, 10)
    heights = np.exp(-0.25 * ns)  # schematic decay
    ax3.vlines(ns, 0.0, heights, color="black", lw=1.6)
    ax3.plot(ns, heights, "o", ms=4.0, color="black")
    ax3.set_xlim(-0.5, 9.5)
    ax3.set_ylim(0.0, 1.05)
    ax3.set_xlabel(r"mode index $n\in\mathbb{Z}_{\geq 0}$")
    ax3.set_ylabel(r"mode weight (schematic)")
    ax3.set_title(r"Discrete $q$-modes $q^n$", fontsize=10.5)
    ax3.text(0.2, 0.15, r"$f(\tau)=\sum_{n\geq 0} a_n q^n$", fontsize=9)

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))

    out_pdf = out_dir / "fig03_constitution_chain.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig03_constitution_chain.png", bbox_inches="tight")
    plt.close(fig)


