from __future__ import annotations

from pathlib import Path

from common import golden_alpha


def build(out_dir: Path, *, png: bool = False) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    alpha = golden_alpha()
    window_end = 1.0 - alpha

    n_scatter = 1200
    t = np.arange(n_scatter, dtype=float)
    xs = (alpha * t) % 1.0

    n_hist = 200_000
    k = 20
    xs_big = (alpha * np.arange(n_hist, dtype=float)) % 1.0
    counts, edges = np.histogram(xs_big, bins=k, range=(0.0, 1.0))
    probs = counts / n_hist
    centers = 0.5 * (edges[:-1] + edges[1:])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.3, 3.6))

    ax1.axhspan(0.0, window_end, alpha=0.12, color="tab:blue", label=r"window $W=[0,1-\alpha)$")
    ax1.scatter(t, xs, s=8, alpha=0.65, color="black", linewidths=0)
    ax1.set_xlim(0, n_scatter - 1)
    ax1.set_ylim(0.0, 1.0)
    ax1.set_xlabel("tick $t$")
    ax1.set_ylabel(r"phase $x_t$")
    ax1.set_title(r"Golden rotation: $x_t = t\alpha \;(\mathrm{mod}\,1)$")
    ax1.legend(loc="upper right", frameon=False)

    width = 1.0 / k
    ax2.bar(centers, probs, width=0.95 * width, color="tab:gray", edgecolor="none", alpha=0.85)
    ax2.axhline(1.0 / k, color="tab:red", lw=1.2, label=r"uniform $1/k$")
    ax2.set_xlim(0.0, 1.0)
    ax2.set_xlabel(r"phase bin on $[0,1)$")
    ax2.set_ylabel("empirical probability")
    ax2.set_title(f"Histogram (N={n_hist:,}, k={k})")
    ax2.legend(loc="upper right", frameon=False)

    fig.suptitle(r"Equidistribution induced by irrational rotation ($\alpha=\varphi^{-1}$)", y=1.02)
    fig.tight_layout()

    out_pdf = out_dir / "fig03_golden_rotation_equidistribution.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig03_golden_rotation_equidistribution.png", bbox_inches="tight")
    plt.close(fig)


