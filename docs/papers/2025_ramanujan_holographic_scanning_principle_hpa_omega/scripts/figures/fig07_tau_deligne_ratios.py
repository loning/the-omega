from __future__ import annotations

from pathlib import Path

from common import primes_upto, tau_up_to


def build(out_dir: Path, *, png: bool = False) -> None:
    import math

    import matplotlib.pyplot as plt

    p_max = 1999
    tau = tau_up_to(p_max)
    ps = primes_upto(p_max)

    ratios: list[float] = []
    for p in ps:
        ratios.append(abs(tau[p]) / (2.0 * (p ** (11 / 2))))

    max_ratio = max(ratios) if ratios else 0.0
    max_p = ps[ratios.index(max_ratio)] if ratios else None

    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    ax.scatter(ps, ratios, s=14, alpha=0.75, color="black", linewidths=0)
    ax.axhline(1.0, color="tab:red", lw=1.2, alpha=0.9, label="Deligne bound")
    ax.set_xlim(0, p_max + 50)
    ax.set_ylim(0.0, 1.05)
    ax.set_xlabel(r"prime $p$")
    ax.set_ylabel(r"$|\tau(p)|/(2p^{11/2})$")
    ax.set_title(r"Deligne-normalized Ramanujan coefficients for $\Delta$")
    ax.legend(frameon=False, loc="upper right")

    if max_p is not None:
        ax.annotate(
            f"max={max_ratio:.3f} at p={max_p}",
            xy=(max_p, max_ratio),
            xytext=(0.60, 0.20),
            textcoords="axes fraction",
            arrowprops={"arrowstyle": "->", "lw": 1.0},
            fontsize=9,
        )

    out_pdf = out_dir / "fig07_tau_deligne_ratios.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig07_tau_deligne_ratios.png", bbox_inches="tight")
    plt.close(fig)


