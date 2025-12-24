from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import math

    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Wedge

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.6, 3.2))
    fig.suptitle("Window readout: from scan points to an induced binary readout", fontsize=12)

    # Left: scan orbit points on a circle with a window W.
    ax1.set_aspect("equal")
    ax1.set_axis_off()
    ax1.add_patch(Circle((0.0, 0.0), 1.0, fill=False, lw=1.2, ec="black"))
    phi = (1.0 + 5.0**0.5) / 2.0
    alpha = 1.0 / phi
    x0 = 0.0
    N = 40
    xs = (x0 + alpha * np.arange(N)) % 1.0
    angles = 2.0 * math.pi * xs
    ax1.plot(np.cos(angles), np.sin(angles), "o", ms=3.6, color="black")
    # Canonical window W=[0,1-alpha).
    theta1 = 0.0
    theta2 = 360.0 * (1.0 - alpha)
    ax1.add_patch(Wedge((0.0, 0.0), 1.0, theta1, theta2, width=0.20, facecolor="#90caf9", edgecolor="none"))
    ax1.text(0.0, 1.25, r"window $W=[0,1-\alpha)$", ha="center", fontsize=9)
    ax1.text(0.0, -1.35, r"$x_t=x_0+t\alpha\ (\mathrm{mod}\,1)$", ha="center", fontsize=9)
    ax1.text(0.0, 1.42, r"scan on $\mathbb{R}/\mathbb{Z}$", ha="center", fontsize=10)

    # Right: the induced symbolic readout s_t = 1_W(x_t) as a 0/1 strip.
    s = (xs < (1.0 - alpha)).astype(int)
    strip = s.reshape(1, -1)
    ax2.imshow(strip, aspect="auto", cmap="Greys", interpolation="nearest", vmin=0, vmax=1)
    ax2.set_yticks([])
    ax2.set_xlabel(r"tick $t$")
    ax2.set_title(r"readout $s_t=\mathbf{1}_W(x_t)$", fontsize=10.5)
    ax2.set_xlim(-0.5, N - 0.5)

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))

    out_pdf = out_dir / "fig04_window_induced_measure.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig04_window_induced_measure.png", bbox_inches="tight")
    plt.close(fig)


