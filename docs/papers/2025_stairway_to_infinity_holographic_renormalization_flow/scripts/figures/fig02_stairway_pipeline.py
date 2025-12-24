from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig = plt.figure(figsize=(7.6, 3.4))
    ax = fig.add_subplot(111)
    ax.set_axis_off()

    nodes = [
        {"xy": (0.03, 0.62), "w": 0.28, "h": 0.25, "t": "Scan orbit", "b": r"$x_t=x_0+t\alpha\ (\mathrm{mod}\,1)$"},
        {"xy": (0.36, 0.62), "w": 0.28, "h": 0.25, "t": "Cusp slice", "b": r"$F_y(x)=f(x+iy)$"},
        {"xy": (0.69, 0.62), "w": 0.28, "h": 0.25, "t": "Fourier projection", "b": r"$\widehat a_{n,N}(y)$ estimator"},
        {"xy": (0.20, 0.20), "w": 0.28, "h": 0.25, "t": "Discrepancy control", "b": r"Koksma + digit bound"},
        {"xy": (0.52, 0.20), "w": 0.28, "h": 0.25, "t": "Arithmetic closure", "b": r"Hecke / Euler constraints"},
        {"xy": (0.84, 0.20), "w": 0.13, "h": 0.25, "t": "Semantics", "b": "Langlands\nlayer"},
    ]

    def draw_box(xy, w, h, title, body, face="#f2f2f2"):
        patch = FancyBboxPatch(
            xy,
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            linewidth=1.2,
            edgecolor="black",
            facecolor=face,
            transform=ax.transAxes,
        )
        ax.add_patch(patch)
        x, y = xy
        pad_x = 0.018
        ax.text(
            x + pad_x,
            y + h - 0.07,
            title,
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=10.0,
            fontweight="bold",
        )
        ax.text(
            x + pad_x,
            y + 0.07,
            body,
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=9.0,
        )

    for n in nodes:
        draw_box(n["xy"], n["w"], n["h"], n["t"], n["b"])

    def arrow(p1, p2):
        ax.annotate(
            "",
            xy=p2,
            xytext=p1,
            xycoords=ax.transAxes,
            textcoords=ax.transAxes,
            arrowprops={"arrowstyle": "->", "lw": 1.2, "shrinkA": 2, "shrinkB": 2, "mutation_scale": 12},
        )

    # Top row arrows
    arrow((0.31, 0.745), (0.36, 0.745))
    arrow((0.64, 0.745), (0.69, 0.745))

    # Down arrows
    arrow((0.17, 0.62), (0.34, 0.45))
    arrow((0.83, 0.62), (0.66, 0.45))

    # Bottom row arrows
    arrow((0.48, 0.325), (0.52, 0.325))
    arrow((0.80, 0.325), (0.84, 0.325))

    ax.text(
        0.50,
        0.94,
        "Stairway pipeline: scan \u2192 slice sampling \u2192 coefficient recovery \u2192 arithmetic constraints",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=11,
    )

    out_pdf = out_dir / "fig02_stairway_pipeline.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig02_stairway_pipeline.png", bbox_inches="tight")
    plt.close(fig)


