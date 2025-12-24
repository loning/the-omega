from __future__ import annotations

from pathlib import Path

from common import primes_upto, tau_up_to


def build(out_dir: Path, *, png: bool = False) -> None:
    import math

    import matplotlib.pyplot as plt

    # Absolutely convergent regime: Re(s) > 13/2 for Delta.
    s = 10.0
    cutoffs = [50, 100, 200, 500, 1000, 2000]
    n_max = max(cutoffs)

    tau = tau_up_to(n_max)

    # Dirichlet partial sums S_N.
    S: dict[int, float] = {}
    running = 0.0
    next_cutoff_idx = 0
    targets = cutoffs[:]
    for n in range(1, n_max + 1):
        running += tau[n] / (n**s)
        if next_cutoff_idx < len(targets) and n == targets[next_cutoff_idx]:
            S[n] = running
            next_cutoff_idx += 1

    # Euler partial products P_N.
    P: dict[int, float] = {0: 1.0}
    prod = 1.0
    primes = primes_upto(n_max)
    cutoff_set = set(cutoffs)
    p_iter = iter(primes)
    current_p = next(p_iter, None)
    for n in range(1, n_max + 1):
        while current_p is not None and current_p == n:
            p = current_p
            a_p = tau[p]
            prod *= 1.0 / (1.0 - a_p * (p ** (-s)) + (p ** (11 - 2 * s)))
            current_p = next(p_iter, None)
        if n in cutoff_set:
            P[n] = prod

    Ns = cutoffs
    abs_diff = [abs(P[n] - S[n]) for n in Ns]
    rel_diff = [abs(P[n] - S[n]) / abs(S[n]) for n in Ns]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.8, 3.4))

    ax1.loglog(Ns, abs_diff, marker="o")
    ax1.set_xlabel(r"cutoff $N$")
    ax1.set_ylabel(r"$|P_N - S_N|$")
    ax1.set_title(r"Euler product closure (absolute error), $s=10$")

    ax2.loglog(Ns, rel_diff, marker="o", color="tab:purple")
    ax2.set_xlabel(r"cutoff $N$")
    ax2.set_ylabel("relative difference")
    ax2.set_title(r"Euler product closure (relative error), $s=10$")

    fig.tight_layout()

    out_pdf = out_dir / "fig09_euler_product_closure_error.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig09_euler_product_closure_error.png", bbox_inches="tight")
    plt.close(fig)


