from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import math

    import matplotlib.pyplot as plt
    import numpy as np

    rng = np.random.default_rng(0)
    sample_count = 200_000
    max_iter = 10
    eps = 2.0**-52

    xs = rng.random(sample_count)
    xs = np.where(xs == 0.0, eps, xs)

    log2 = math.log(2.0)

    def gauss_cdf(x: np.ndarray) -> np.ndarray:
        return np.log1p(x) / log2

    def ks_distance_to_gauss(x: np.ndarray) -> float:
        x_sorted = np.sort(x)
        n = x_sorted.size
        th = gauss_cdf(x_sorted)
        emp = (np.arange(1, n + 1, dtype=float)) / float(n)
        emp_left = (np.arange(0, n, dtype=float)) / float(n)
        return float(np.max(np.maximum(np.abs(emp - th), np.abs(emp_left - th))))

    ks_vals: list[float] = []
    for _ in range(max_iter + 1):
        ks_vals.append(ks_distance_to_gauss(xs))
        inv = 1.0 / xs
        a = np.floor(inv)
        y = inv - a
        xs = np.where(y == 0.0, eps, y)

    # Toy exponential fit on n=0..4, matching Experiment 13.
    fit_n_min = 0
    fit_n_max = 4
    fit_ns = np.arange(fit_n_min, fit_n_max + 1, dtype=float)
    fit_logs = np.log(np.array(ks_vals[fit_n_min : fit_n_max + 1], dtype=float))
    slope, intercept = np.polyfit(fit_ns, fit_logs, deg=1)
    lambda_fit = math.exp(slope)

    # DKW 95% benchmark (i.i.d. reference scale).
    eps95 = math.sqrt(math.log(2.0 / 0.05) / (2.0 * sample_count))

    ns = np.arange(0, max_iter + 1, dtype=float)
    fit_curve = np.exp(intercept + slope * ns)

    fig, ax = plt.subplots(figsize=(6.9, 3.5))
    ax.semilogy(ns, ks_vals, marker="o", label="KS distance to Gauss CDF")
    ax.semilogy(ns, fit_curve, linestyle="--", label=f"toy fit: $\\lambda_\\mathrm{{fit}}\\approx {lambda_fit:.3f}$")
    ax.axhline(eps95, color="tab:red", lw=1.2, alpha=0.85, label="DKW 95% benchmark")
    ax.set_xlabel(r"iterate $n$")
    ax.set_ylabel("distance")
    ax.set_title("Gauss–Kuzmin relaxation (toy convergence audit)")
    ax.legend(frameon=False, loc="best")

    out_pdf = out_dir / "fig12_gauss_kuzmin_convergence.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig12_gauss_kuzmin_convergence.png", bbox_inches="tight")
    plt.close(fig)


