from __future__ import annotations

from pathlib import Path


def _gauss_step(x: float) -> tuple[int, float]:
    a = int(1.0 / x)
    return a, (1.0 / x) - a


def _gauss_digit_prob(k: int) -> float:
    import math

    return math.log(1.0 + 1.0 / (k * (k + 2.0)), 2.0)


def build(out_dir: Path, *, png: bool = False) -> None:
    import math

    import matplotlib.pyplot as plt
    import numpy as np

    # Deterministic seed, as in Experiment 11.
    x0 = math.modf(math.pi)[0]
    if x0 <= 0.0:
        x0 = math.sqrt(2.0) - 1.0

    burn_in = 2000
    k_max = 10
    ns = [10_000, 100_000, 1_000_000]
    n_max = max(ns)

    # Burn-in.
    x = x0
    for _ in range(burn_in):
        _, x = _gauss_step(x)

    # Theory for digits 1..k_max and a tail bin.
    p_theory = np.zeros(k_max + 2, dtype=float)
    for k in range(1, k_max + 1):
        p_theory[k] = _gauss_digit_prob(k)
    p_theory[k_max + 1] = 1.0 - float(np.sum(p_theory[1 : k_max + 1]))

    counts = np.zeros(k_max + 2, dtype=int)
    results: dict[int, tuple[float, float, float]] = {}

    for t in range(1, n_max + 1):
        a, x = _gauss_step(x)
        if 1 <= a <= k_max:
            counts[a] += 1
        else:
            counts[k_max + 1] += 1

        if t in ns:
            phat = counts.astype(float) / float(t)
            l1 = float(np.sum(np.abs(phat[1:] - p_theory[1:])))
            linf = float(np.max(np.abs(phat[1:] - p_theory[1:])))
            tail_err = float(abs(phat[k_max + 1] - p_theory[k_max + 1]))
            results[t] = (l1, linf, tail_err)

    # Bar chart for the largest N.
    phat_final = counts.astype(float) / float(n_max)

    labels = [str(k) for k in range(1, k_max + 1)] + ["tail"]
    x_pos = np.arange(len(labels), dtype=float)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.8, 3.4))

    width = 0.42
    ax1.bar(x_pos - width / 2, phat_final[1:], width=width, label="empirical", color="tab:gray", alpha=0.85)
    ax1.bar(x_pos + width / 2, p_theory[1:], width=width, label="theory", color="tab:red", alpha=0.55)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(labels)
    ax1.set_xlabel("continued-fraction digit")
    ax1.set_ylabel("probability")
    ax1.set_title(f"Gauss digit law fit (N={n_max:,})")
    ax1.legend(frameon=False, loc="best")

    # Error scaling with N.
    ns_sorted = sorted(ns)
    l1s = [results[n][0] for n in ns_sorted]
    linfs = [results[n][1] for n in ns_sorted]
    tails = [results[n][2] for n in ns_sorted]

    ax2.loglog(ns_sorted, l1s, marker="o", label=r"$\ell^1$ error")
    ax2.loglog(ns_sorted, linfs, marker="s", label=r"$\ell^\infty$ error")
    ax2.loglog(ns_sorted, tails, marker="^", label="tail error")
    ax2.set_xlabel(r"$N$")
    ax2.set_ylabel("error")
    ax2.set_title("Fit errors vs sample size")
    ax2.legend(frameon=False, loc="best")

    fig.tight_layout()

    out_pdf = out_dir / "fig11_gauss_digit_law_fit.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig11_gauss_digit_law_fit.png", bbox_inches="tight")
    plt.close(fig)


