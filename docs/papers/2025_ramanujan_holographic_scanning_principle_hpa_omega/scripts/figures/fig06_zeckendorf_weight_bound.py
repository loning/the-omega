from __future__ import annotations

from pathlib import Path

from common import golden_alpha, rotation_orbit, star_discrepancy_1d, zeckendorf_weight


def build(out_dir: Path, *, png: bool = False) -> None:
    import matplotlib.pyplot as plt

    alpha = golden_alpha()
    ns = [50, 100, 500, 1000, 1597, 2000, 4000, 8000, 12816]

    d_obs: list[float] = []
    d_bound: list[float] = []
    ratios: list[float] = []
    weights: list[int] = []

    for n in ns:
        w = zeckendorf_weight(n)
        d = star_discrepancy_1d(rotation_orbit(alpha, n))
        b = 2.0 * w / n if n > 0 else 0.0
        r = (d / b) if b > 0 else float("inf")
        weights.append(w)
        d_obs.append(d)
        d_bound.append(b)
        ratios.append(r)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.6, 3.2))

    ax1.loglog(ns, d_obs, marker="o", label=r"observed $D_N^*$")
    ax1.loglog(ns, d_bound, marker="s", linestyle="--", label=r"bound $2w_Z(N)/N$")
    ax1.set_xlabel(r"$N$")
    ax1.set_ylabel(r"value")
    ax1.set_title("Zeckendorf digit-sum control of discrepancy")
    ax1.legend(frameon=False, loc="best")

    ax2.semilogx(ns, ratios, marker="o")
    ax2.axhline(1.0, color="tab:red", lw=1.2, alpha=0.8)
    ax2.set_xlabel(r"$N$")
    ax2.set_ylabel(r"$D_N^*/(2w_Z(N)/N)$")
    ax2.set_title("Observed/bound ratio")

    for n, w in zip(ns, weights):
        ax2.annotate(f"$w_Z={w}$", xy=(n, ratios[ns.index(n)]), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8)

    fig.tight_layout()

    out_pdf = out_dir / "fig06_zeckendorf_weight_bound.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig06_zeckendorf_weight_bound.png", bbox_inches="tight")
    plt.close(fig)


