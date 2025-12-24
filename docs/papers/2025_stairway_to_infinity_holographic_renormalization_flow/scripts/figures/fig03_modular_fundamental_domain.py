from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import math

    import matplotlib.pyplot as plt
    import numpy as np

    y_max = 2.8
    x_left, x_right = -0.5, 0.5

    xs = np.linspace(x_left, x_right, 500)
    ys_arc = np.sqrt(1.0 - xs**2)

    # Fundamental domain polygon (truncated at y_max).
    poly_x = np.concatenate([[x_left, x_left], xs, [x_right, x_right]])
    poly_y = np.concatenate([[ys_arc[0], y_max], ys_arc, [y_max, ys_arc[-1]]])

    fig, ax = plt.subplots(figsize=(6.8, 3.9))
    ax.fill(poly_x, poly_y, alpha=0.18, edgecolor="none")

    # Boundary: vertical lines and unit-circle arc.
    ax.plot([x_left, x_left], [ys_arc[0], y_max], color="black", lw=1.3)
    ax.plot([x_right, x_right], [ys_arc[-1], y_max], color="black", lw=1.3)
    ax.plot(xs, ys_arc, color="black", lw=1.3)

    # Unit circle outline (context).
    theta = np.linspace(0.0, math.pi, 900)
    ax.plot(np.cos(theta), np.sin(theta), color="black", lw=0.8, alpha=0.35)

    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(0.0, y_max)
    ax.set_xlabel(r"$\Re(\tau)$")
    ax.set_ylabel(r"$\Im(\tau)=y$")
    ax.set_title(r"Modular fundamental domain (truncated) and the cusp interface")

    ax.text(-0.45, 2.65, r"$\mathcal{F}$", fontsize=12)

    # Cusp annotation
    ax.annotate(
        r"cusp at $i\infty$",
        xy=(0.0, y_max),
        xytext=(0.18, 2.35),
        arrowprops={"arrowstyle": "->", "lw": 1.0},
        fontsize=9,
    )
    ax.text(0.18, 2.18, r"$q=\mathrm{e}^{2\pi i\tau}$", fontsize=9)

    # Height direction hint
    ax.annotate(
        "",
        xy=(0.92, 2.4),
        xytext=(0.92, 0.6),
        arrowprops={"arrowstyle": "->", "lw": 1.0},
    )
    ax.text(0.94, 1.55, "height", rotation=90, fontsize=9, va="center")

    # Elliptic points: i and exp(i*pi/3)
    ax.scatter([0.0, 0.5], [1.0, math.sqrt(3) / 2], s=18, color="black")
    ax.text(0.03, 1.02, r"$i$", fontsize=9)
    ax.text(0.52, math.sqrt(3) / 2 + 0.02, r"$\mathrm{e}^{i\pi/3}$", fontsize=9)

    out_pdf = out_dir / "fig03_modular_fundamental_domain.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig03_modular_fundamental_domain.png", bbox_inches="tight")
    plt.close(fig)


