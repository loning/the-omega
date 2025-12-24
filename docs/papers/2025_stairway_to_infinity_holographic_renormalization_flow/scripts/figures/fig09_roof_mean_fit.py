from __future__ import annotations

from pathlib import Path

from common import gauss_step, roof


def build(out_dir: Path, *, png: bool = False) -> None:
    import math
    import random

    import matplotlib.pyplot as plt
    import numpy as np

    theo = (math.pi * math.pi) / (6.0 * math.log(2.0))
    rng = random.Random(0)

    burn = 2000
    n_orbits = 20
    x0s = [rng.random() for _ in range(n_orbits)]
    ns = [10_000, 50_000, 100_000, 300_000, 1_000_000]

    means = np.zeros((n_orbits, len(ns)), dtype=float)
    for i, x0 in enumerate(x0s):
        x = x0
        for _ in range(burn):
            x = gauss_step(x)
        s = 0.0
        j = 0
        targets = set(ns)
        max_n = max(ns)
        row = {}
        for t in range(1, max_n + 1):
            x = gauss_step(x)
            s += roof(x)
            if t in targets:
                row[t] = s / t
        for k, n in enumerate(ns):
            means[i, k] = row[n]

    mean_over_orbits = np.mean(means, axis=0)
    std_over_orbits = np.std(means, axis=0, ddof=1)
    abs_err = np.abs(mean_over_orbits - theo)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.8, 3.3))

    ax1.errorbar(ns, mean_over_orbits, yerr=std_over_orbits, marker="o", capsize=3, linestyle="-", color="black")
    ax1.axhline(theo, color="tab:red", lw=1.2, label=r"theory $\pi^2/(6\log 2)$")
    ax1.set_xscale("log")
    ax1.set_xlabel(r"$N$")
    ax1.set_ylabel(r"mean of $r(G^j\xi)$")
    ax1.set_title("Roof-function mean over orbits")
    ax1.legend(frameon=False, loc="best")

    ax2.loglog(ns, abs_err, marker="o", color="tab:purple")
    ax2.set_xlabel(r"$N$")
    ax2.set_ylabel("absolute error")
    ax2.set_title("Convergence to the theoretical constant")

    fig.tight_layout()

    out_pdf = out_dir / "fig09_roof_mean_fit.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig09_roof_mean_fit.png", bbox_inches="tight")
    plt.close(fig)


