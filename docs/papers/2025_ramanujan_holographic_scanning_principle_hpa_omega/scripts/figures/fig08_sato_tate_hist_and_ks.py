from __future__ import annotations

from pathlib import Path

from common import dkw_eps, ks_distance_to_semicircle, primes_upto, semicircle_pdf, tau_up_to


def build(out_dir: Path, *, png: bool = False) -> None:
    import numpy as np
    import matplotlib.pyplot as plt

    p_max = 1999
    tau = tau_up_to(p_max)
    ps = primes_upto(p_max)
    vals = np.array([tau[p] / (2.0 * (p ** (11 / 2))) for p in ps], dtype=float)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.6, 3.4))

    # Histogram + theoretical semicircle density.
    bins = 28
    ax1.hist(vals, bins=bins, range=(-1.0, 1.0), density=True, color="tab:gray", alpha=0.85, edgecolor="none")
    xs = np.linspace(-1.0, 1.0, 400)
    ax1.plot(xs, semicircle_pdf(xs.tolist()), color="tab:red", lw=1.6, label="Sato–Tate semicircle")
    ax1.set_xlim(-1.0, 1.0)
    ax1.set_xlabel(r"$x_p=\tau(p)/(2p^{11/2})$")
    ax1.set_ylabel("density")
    ax1.set_title(f"Histogram (primes $p\\leq {p_max}$, count={len(ps)})")
    ax1.legend(frameon=False, loc="upper center")

    # KS distances at representative cutoffs (as in Experiment 14).
    p_max_list = [59, 199, 499, 999, 1999]
    ks_vals: list[float] = []
    dkw95: list[float] = []
    for pm in p_max_list:
        ps_pm = primes_upto(pm)
        vals_pm = [tau[p] / (2.0 * (p ** (11 / 2))) for p in ps_pm]
        ks = ks_distance_to_semicircle(vals_pm)
        ks_vals.append(ks)
        dkw95.append(dkw_eps(0.05, len(vals_pm)))

    ax2.plot(p_max_list, ks_vals, marker="o", label="KS distance")
    ax2.plot(p_max_list, dkw95, marker="s", linestyle="--", label="DKW 95% benchmark")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel(r"prime cutoff $p_{\max}$")
    ax2.set_ylabel("distance")
    ax2.set_title("Empirical CDF vs semicircle CDF")
    ax2.legend(frameon=False, loc="best")

    fig.suptitle(r"Sato–Tate sanity checks for $\Delta$ (distribution-level)", y=1.02)
    fig.tight_layout()

    out_pdf = out_dir / "fig08_sato_tate_hist_and_ks.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig08_sato_tate_hist_and_ks.png", bbox_inches="tight")
    plt.close(fig)


