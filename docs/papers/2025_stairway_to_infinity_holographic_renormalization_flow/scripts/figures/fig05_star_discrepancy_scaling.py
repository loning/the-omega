from __future__ import annotations

from pathlib import Path

from common import golden_alpha, rotation_orbit, star_discrepancy_1d


def build(out_dir: Path, *, png: bool = False) -> None:
    import math

    import matplotlib.pyplot as plt

    alpha = golden_alpha()
    ns = [10, 20, 50, 100, 1_000, 10_000, 50_000]

    ds: list[float] = []
    for n in ns:
        ds.append(star_discrepancy_1d(rotation_orbit(alpha, n)))

    scaled_n = [n * d for n, d in zip(ns, ds)]
    scaled_log = [d * n / math.log(n) for n, d in zip(ns, ds)]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.8, 3.3))

    ax1.loglog(ns, ds, marker="o")
    ax1.set_xlabel(r"$N$")
    ax1.set_ylabel(r"$D_N^*$")
    ax1.set_title(r"Star discrepancy for the golden rotation orbit")

    ax2.semilogx(ns, scaled_n, marker="o", label=r"$N D_N^*$")
    ax2.semilogx(ns, scaled_log, marker="s", linestyle="--", label=r"$N D_N^*/\log N$")
    ax2.set_xlabel(r"$N$")
    ax2.set_ylabel("scaled value")
    ax2.set_title("Scaling diagnostics")
    ax2.legend(frameon=False, loc="best")

    fig.tight_layout()

    out_pdf = out_dir / "fig05_star_discrepancy_scaling.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig05_star_discrepancy_scaling.png", bbox_inches="tight")
    plt.close(fig)


