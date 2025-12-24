from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import math

    import matplotlib.pyplot as plt
    import numpy as np

    y_max = 2.6
    x_left, x_right = -0.5, 0.5

    xs = np.linspace(x_left, x_right, 400)
    ys_arc = np.sqrt(1.0 - xs**2)

    # Polygon for the fundamental domain (truncated at y_max).
    poly_x = np.concatenate([[x_left, x_left], xs, [x_right, x_right]])
    poly_y = np.concatenate([[ys_arc[0], y_max], ys_arc, [y_max, ys_arc[-1]]])

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.fill(poly_x, poly_y, alpha=0.18, edgecolor="none")

    # Boundary: vertical lines and unit-circle arc.
    ax.plot([x_left, x_left], [ys_arc[0], y_max], color="black", lw=1.3)
    ax.plot([x_right, x_right], [ys_arc[-1], y_max], color="black", lw=1.3)
    ax.plot(xs, ys_arc, color="black", lw=1.3)

    # Unit circle outline (for context, truncated).
    theta = np.linspace(0.0, math.pi, 800)
    ax.plot(np.cos(theta), np.sin(theta), color="black", lw=0.8, alpha=0.35)

    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(0.0, y_max)
    ax.set_xlabel(r"$\Re(\tau)$")
    ax.set_ylabel(r"$\Im(\tau)$")
    ax.set_title("Fundamental domain for $\\mathrm{PSL}_2(\\mathbb{Z})$ (truncated)")

    ax.text(-0.45, 2.45, r"$\mathcal{F}$", fontsize=12)
    ax.annotate(
        "cusp at $i\\infty$",
        xy=(0.0, y_max),
        xytext=(0.15, 2.25),
        arrowprops={"arrowstyle": "->", "lw": 1.0},
        fontsize=9,
    )

    # Elliptic points: i and exp(i*pi/3)
    ax.scatter([0.0, 0.5], [1.0, math.sqrt(3) / 2], s=18, color="black")
    ax.text(0.03, 1.02, r"$i$", fontsize=9)
    ax.text(0.52, math.sqrt(3) / 2 + 0.02, r"$e^{i\pi/3}$", fontsize=9)

    out_pdf = out_dir / "fig02_modular_fundamental_domain.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig02_modular_fundamental_domain.png", bbox_inches="tight")
    plt.close(fig)


