from __future__ import annotations

from pathlib import Path

from common import fibonacci_up_to_index, golden_alpha, rotation_orbit, star_discrepancy_1d


def build(out_dir: Path, *, png: bool = False) -> None:
    import math

    import matplotlib.pyplot as plt

    alpha = golden_alpha()
    c_limit = 1.0 + 1.0 / math.sqrt(5.0)

    n_max = 20
    fib = fibonacci_up_to_index(n_max)

    ns_even: list[int] = []
    vals_even: list[float] = []
    err_even: list[float] = []

    ns_odd: list[int] = []
    vals_odd: list[float] = []

    for n in range(3, n_max + 1):
        fn = fib[n - 1]
        d = star_discrepancy_1d(rotation_orbit(alpha, fn))
        scaled = fn * d
        if n % 2 == 0:
            ns_even.append(n)
            vals_even.append(scaled)
            err_even.append(abs(scaled - c_limit))
        else:
            ns_odd.append(n)
            vals_odd.append(scaled)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.4, 3.2))

    ax1.plot(ns_even, vals_even, marker="o", label="even $n$: $F_n D_{F_n}^*$")
    ax1.plot(ns_odd, vals_odd, marker="s", linestyle="--", label="odd $n$: $F_n D_{F_n}^*$")
    ax1.axhline(c_limit, color="tab:red", lw=1.2, label=r"limit $1+1/\sqrt{5}$ (even subsequence)")
    ax1.set_xlabel(r"Fibonacci index $n$")
    ax1.set_ylabel(r"$F_n D_{F_n}^*$")
    ax1.set_title("Scaled star discrepancy at Fibonacci lengths")
    ax1.legend(frameon=False, loc="best")

    ax2.semilogy(ns_even, err_even, marker="o")
    ax2.set_xlabel(r"even index $n$")
    ax2.set_ylabel(r"$|F_n D_{F_n}^*-(1+1/\sqrt{5})|$")
    ax2.set_title("Convergence of the even subsequence")

    fig.tight_layout()

    out_pdf = out_dir / "fig05_fibonacci_discrepancy_constant.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig05_fibonacci_discrepancy_constant.png", bbox_inches="tight")
    plt.close(fig)


