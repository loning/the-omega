from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.2))
    fig.suptitle("Langlands semantics (schematic): prime-indexed data and its reorganizations", fontsize=12)
    for ax in (ax1, ax2):
        ax.set_axis_off()

    primes = [2, 3, 5, 7, 11, 13]

    def cell(ax, x, y, w, h, text, *, face="#f2f2f2", weight="normal", fs=10.0):
        patch = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.01,rounding_size=0.02",
            linewidth=1.0,
            edgecolor="black",
            facecolor=face,
            transform=ax.transAxes,
        )
        ax.add_patch(patch)
        ax.text(
            x + w / 2,
            y + h / 2,
            text,
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=fs,
            fontweight=weight,
        )

    # Left panel: a compact table indexed by primes.
    left = 0.02
    label_w = 0.20
    col_w = 0.11
    row_h = 0.18
    x0 = left + label_w
    y_top = 0.68
    row_gap = 0.04

    rows = [
        (r"prime $p$", [rf"${p}$" for p in primes], "#ffffff"),
        (r"Hecke: $a_p$", [rf"$a_{{{p}}}$" for p in primes], "#e3f2fd"),
        (r"local: $L_p(s)$", [rf"$L_{{{p}}}(s)$" for p in primes], "#e8f5e9"),
    ]

    for r, (label, vals, face) in enumerate(rows):
        y = y_top - r * (row_h + row_gap)
        cell(ax1, left, y, label_w - 0.02, row_h, label, face="#ffffff", fs=10.0, weight="bold" if r == 0 else "normal")
        for i, val in enumerate(vals):
            cell(ax1, x0 + i * col_w, y, col_w - 0.01, row_h, val, face=face, fs=10.0)

    ax1.text(
        0.02,
        0.08,
        r"Same index $p$ threads through coefficients and local factors.",
        transform=ax1.transAxes,
        fontsize=9,
    )

    # Right panel: reorganizations and identities (no numeric checking implied).
    ax2.text(0.02, 0.78, "Euler product", transform=ax2.transAxes, fontsize=10, fontweight="bold")
    ax2.text(0.02, 0.66, r"$L(s,f)=\prod_p L_p(s)$", transform=ax2.transAxes, fontsize=11)

    ax2.text(0.02, 0.50, r"Typical $\mathrm{GL}_2$ local factor (weight $k$)", transform=ax2.transAxes, fontsize=10, fontweight="bold")
    ax2.text(0.02, 0.38, r"$L_p(s)=(1-a_p p^{-s}+p^{k-1-2s})^{-1}$", transform=ax2.transAxes, fontsize=11)

    ax2.text(0.02, 0.22, "When available (Galois)", transform=ax2.transAxes, fontsize=10, fontweight="bold")
    ax2.text(0.02, 0.10, r"$\mathrm{tr}\,\rho(\mathrm{Frob}_p)=a_p$", transform=ax2.transAxes, fontsize=11)

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))

    out_pdf = out_dir / "fig06_langlands_pipeline.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig06_langlands_pipeline.png", bbox_inches="tight")
    plt.close(fig)


