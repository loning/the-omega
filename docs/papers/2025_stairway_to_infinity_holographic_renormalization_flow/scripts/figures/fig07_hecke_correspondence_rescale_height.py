from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import numpy as np
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.2))
    fig.suptitle(r"Hecke correspondence $T_p$ (schematic): height rescaling and cusp coordinate", fontsize=12)

    # Panel 1: geometric action on a point τ=x+iy in the upper half-plane.
    p = 3
    x0, y0 = 0.23, 0.75
    base = (x0, y0)
    deep = ((p * x0) % 1.0, p * y0)
    shallows = [(((x0 + b) / p) % 1.0, y0 / p) for b in range(p)]

    ax1.set_xlim(0.0, 1.0)
    ax1.set_ylim(0.0, p * y0 * 1.15)
    ax1.set_xlabel(r"$x=\Re\tau\ (\mathrm{mod}\,1)$")
    ax1.set_ylabel(r"$y=\Im\tau$")
    ax1.set_title(r"Images of $\tau$ under $\tau\mapsto p\tau$ and $\tau\mapsto(\tau+b)/p$", fontsize=10.3)
    ax1.grid(alpha=0.18)

    ax1.plot([base[0]], [base[1]], "o", ms=6.5, color="black")
    ax1.text(base[0] + 0.02, base[1] + 0.02, r"$\tau$", fontsize=10)

    ax1.plot([deep[0]], [deep[1]], "o", ms=6.5, color="#43a047")
    ax1.text(deep[0] + 0.02, deep[1] + 0.02, r"$p\tau$", fontsize=10, color="#2e7d32")

    sx = [pt[0] for pt in shallows]
    sy = [pt[1] for pt in shallows]
    ax1.plot(sx, sy, "o", ms=6.0, color="#fb8c00")
    for b, pt in enumerate(shallows):
        ax1.text(pt[0] + 0.02, pt[1] + 0.02, rf"$b={b}$", fontsize=9, color="#ef6c00")

    ax1.annotate("", xy=deep, xytext=base, arrowprops={"arrowstyle": "->", "lw": 1.1, "color": "#43a047"})
    for pt in shallows:
        ax1.annotate("", xy=pt, xytext=base, arrowprops={"arrowstyle": "->", "lw": 0.8, "color": "#fb8c00", "alpha": 0.7})

    ax1.text(
        0.02,
        0.96,
        rf"deep branch: $y\mapsto {p}y$   |   shallow branches: $y\mapsto y/{p}$",
        transform=ax1.transAxes,
        fontsize=9.5,
        va="top",
    )

    # Panel 2: induced action on the cusp coordinate q=e^{2π i τ}, hence |q|=e^{-2π y}.
    q = np.linspace(0.02, 0.98, 400)
    ax2.plot(q, q**p, color="#43a047", lw=1.4, label=rf"deep: $|q|\mapsto |q|^{p}$")
    ax2.plot(q, q ** (1.0 / p), color="#fb8c00", lw=1.4, label=rf"shallow: $|q|\mapsto |q|^{{1/{p}}}$")
    ax2.plot(q, q, color="black", alpha=0.15, lw=1.0)
    ax2.set_xlim(0.0, 1.0)
    ax2.set_ylim(0.0, 1.0)
    ax2.set_xlabel(r"$|q|$")
    ax2.set_ylabel(r"$|q|'$")
    ax2.set_title(r"$q=e^{2\pi i\tau}$:  $\tau\mapsto p\tau$ or $(\tau+b)/p$", fontsize=10.3)
    ax2.grid(alpha=0.18)
    ax2.legend(frameon=False, fontsize=9, loc="upper left")
    ax2.text(0.02, 0.02, r"shallow has phase $e^{2\pi i b/p}$ (magnitude shown)", transform=ax2.transAxes, fontsize=9, va="bottom")

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))

    out_pdf = out_dir / "fig07_hecke_correspondence_rescale_height.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig07_hecke_correspondence_rescale_height.png", bbox_inches="tight")
    plt.close(fig)


