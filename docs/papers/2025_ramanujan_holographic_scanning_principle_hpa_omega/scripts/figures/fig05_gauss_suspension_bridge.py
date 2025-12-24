from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import numpy as np
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.4, 3.4))
    fig.suptitle("Gauss map and roof function (visualizing the suspension data)", fontsize=12)

    # Left: Gauss map branches. Each branch corresponds to a digit k = floor(1/xi).
    K = 8
    for k in range(1, K + 1):
        x_lo = 1.0 / (k + 1)
        x_hi = 1.0 / k
        xs = np.linspace(x_lo + 1e-4, x_hi - 1e-4, 400)
        ys = 1.0 / xs - k
        ax1.plot(xs, ys, lw=1.3)
        # Label only small digits; higher digits cluster near xi -> 0 and would overlap.
        if k <= 4:
            x_mid = 1.0 / (k + 0.5)
            y_mid = 1.0 / x_mid - k
            ax1.text(x_mid, min(0.95, y_mid + 0.07), f"{k}", ha="center", va="center", fontsize=9)

    # Mark the standard partition points xi = 1/k.
    for k in range(1, K + 1):
        ax1.axvline(1.0 / k, color="black", alpha=0.10, lw=0.9)
    ax1.axhline(0.0, color="black", alpha=0.15, lw=0.9)
    ax1.axhline(1.0, color="black", alpha=0.10, lw=0.9)

    ax1.set_xlim(0.0, 1.0)
    ax1.set_ylim(0.0, 1.0)
    ax1.set_xlabel(r"$\xi\in(0,1)$")
    ax1.set_ylabel(r"$G(\xi)$")
    ax1.set_title(r"Gauss map $G(\xi)=\{1/\xi\}$")
    ax1.text(0.03, 0.95, "digit $k$ on branch\nlabels shown for k<=4", fontsize=9, va="top")

    # Right: roof function r(xi) = -2 log xi (return time in the suspension model).
    xs = np.linspace(1e-3, 1.0, 800)
    rs = -2.0 * np.log(xs)
    ax2.plot(xs, rs, color="black", lw=1.3)
    ax2.set_xlabel(r"$\xi$")
    ax2.set_ylabel(r"$r(\xi)$")
    ax2.set_title(r"roof $r(\xi)=-2\log \xi$")
    ax2.set_xscale("log")
    ax2.set_ylim(0.0, 14.0)
    ax2.text(2e-3, 12.5, "large near $\\xi\\to 0$", fontsize=9)

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.92))

    out_pdf = out_dir / "fig05_gauss_suspension_bridge.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig05_gauss_suspension_bridge.png", bbox_inches="tight")
    plt.close(fig)


