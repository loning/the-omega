from __future__ import annotations

from pathlib import Path

from common import fibonacci_word, golden_alpha, rotation_word


def build(out_dir: Path, *, png: bool = False) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    alpha = golden_alpha()
    n = 160

    w = rotation_word(alpha, n + 1, x0=0.0)  # canonical mechanical word
    w_drop = w[1 : 1 + n]  # match Experiment 1 convention
    fib = fibonacci_word(n)

    a = np.array([[int(ch) for ch in w_drop], [int(ch) for ch in fib]], dtype=int)
    mismatches = int(np.sum(a[0] != a[1]))

    fig, ax = plt.subplots(figsize=(7.2, 2.2))
    ax.imshow(a, cmap="Greys", aspect="auto", interpolation="nearest", vmin=0, vmax=1)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["rotation word", "Fibonacci word"])
    ax.set_xlabel("index")
    ax.set_title(
        r"Golden rotation window readout yields the Fibonacci/Sturmian word "
        + f"(prefix length {n}, mismatches={mismatches})"
    )
    ax.grid(False)

    out_pdf = out_dir / "fig04_sturmian_fibonacci_word.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig04_sturmian_fibonacci_word.png", bbox_inches="tight")
    plt.close(fig)


