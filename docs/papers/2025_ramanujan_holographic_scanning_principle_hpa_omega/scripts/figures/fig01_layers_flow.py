from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig = plt.figure(figsize=(6.4, 3.6))
    ax = fig.add_subplot(111)
    ax.set_axis_off()

    boxes = [
        {
            "xy": (0.08, 0.70),
            "w": 0.84,
            "h": 0.20,
            "title": "Layer 0 (Ontological)",
            "body": "States + algebras only\nNo external time / probability postulate",
        },
        {
            "xy": (0.08, 0.40),
            "w": 0.84,
            "h": 0.20,
            "title": "Layer 1 (Protocol)",
            "body": "Scan + finite-resolution readout\nInduced measures and statistics",
        },
        {
            "xy": (0.08, 0.10),
            "w": 0.84,
            "h": 0.20,
            "title": "Layer 2 (Interpretation)",
            "body": "Semantic mapping (spacetime, particles, gravity)\nMust not be used as a premise",
        },
    ]

    for b in boxes:
        patch = FancyBboxPatch(
            b["xy"],
            b["w"],
            b["h"],
            boxstyle="round,pad=0.012,rounding_size=0.02",
            linewidth=1.2,
            edgecolor="black",
            facecolor="#f2f2f2",
            transform=ax.transAxes,
        )
        ax.add_patch(patch)
        x, y = b["xy"]
        ax.text(
            x + 0.02,
            y + b["h"] - 0.06,
            b["title"],
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=11,
            fontweight="bold",
        )
        ax.text(
            x + 0.02,
            y + 0.06,
            b["body"],
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=9.5,
        )

    # Downward arrows
    ax.annotate(
        "",
        xy=(0.50, 0.62),
        xytext=(0.50, 0.60),
        xycoords=ax.transAxes,
        textcoords=ax.transAxes,
        arrowprops={"arrowstyle": "->", "lw": 1.4},
    )
    ax.annotate(
        "",
        xy=(0.50, 0.32),
        xytext=(0.50, 0.30),
        xycoords=ax.transAxes,
        textcoords=ax.transAxes,
        arrowprops={"arrowstyle": "->", "lw": 1.4},
    )
    ax.text(
        0.50,
        0.53,
        "Derivation flow",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=9,
    )

    ax.text(
        0.50,
        0.02,
        "Audit rule: interpretation cannot imply derivation",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=9,
    )

    out_pdf = out_dir / "fig01_layers_flow.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig01_layers_flow.png", bbox_inches="tight")
    plt.close(fig)


