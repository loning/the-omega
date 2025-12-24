from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    ax.set_axis_off()
    ax.set_title("Prime skeleton on indices (schematic)", fontsize=12)

    # Nodes represent coefficient slots a_n; edges represent prime-generated structure on indices.
    # Layout (axes coordinates): a_{2^r} along a horizontal line; a_{3^r} upwards; coprime products at intersections.
    nodes = {
        1: (0.12, 0.40),
        2: (0.28, 0.40),
        4: (0.44, 0.40),
        8: (0.60, 0.40),
        3: (0.12, 0.68),
        9: (0.12, 0.86),
        6: (0.28, 0.68),
        12: (0.44, 0.68),
    }

    def draw_node(n: int, xy, *, face="#f2f2f2"):
        x, y = xy
        ax.add_patch(Circle((x, y), 0.045, transform=ax.transAxes, fc=face, ec="black", lw=1.1))
        ax.text(x, y, rf"$a_{{{n}}}$", transform=ax.transAxes, ha="center", va="center", fontsize=10)

    def draw_arrow(n1: int, n2: int, *, label=None, style="-"):
        x1, y1 = nodes[n1]
        x2, y2 = nodes[n2]
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            xycoords=ax.transAxes,
            textcoords=ax.transAxes,
            arrowprops={
                "arrowstyle": "->",
                "lw": 1.1,
                "linestyle": style,
                "shrinkA": 8,
                "shrinkB": 8,
                "mutation_scale": 12,
            },
        )
        if label is not None:
            mx = 0.5 * (x1 + x2)
            my = 0.5 * (y1 + y2)
            ax.text(mx, my + 0.04, label, transform=ax.transAxes, ha="center", va="center", fontsize=9)

    # Draw nodes
    draw_node(1, nodes[1], face="#e3f2fd")
    for n in (2, 4, 8):
        draw_node(n, nodes[n], face="#e3f2fd")
    for n in (3, 9):
        draw_node(n, nodes[n], face="#e8f5e9")
    for n in (6, 12):
        draw_node(n, nodes[n], face="#fff3e0")

    # Prime multiplication chains
    draw_arrow(1, 2, label=r"$\times 2$")
    draw_arrow(2, 4, label=r"$\times 2$")
    draw_arrow(4, 8, label=r"$\times 2$")

    draw_arrow(1, 3, label=r"$\times 3$")
    draw_arrow(3, 9, label=r"$\times 3$")

    # Coprime multiplicativity (schematic: dashed arrows into a_{mn})
    draw_arrow(2, 6, label=r"$(m,n)=1$", style="--")
    draw_arrow(3, 6, style="--")
    draw_arrow(4, 12, label=r"$(m,n)=1$", style="--")
    draw_arrow(3, 12, style="--")

    ax.text(
        0.72,
        0.74,
        "Prime powers obey recursions\nand coprime indices multiply:\n"
        r"$a_{mn}=a_ma_n$",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
    )
    ax.text(
        0.72,
        0.48,
        "Euler products package\nprime-indexed data into\n"
        r"$L(s,f)=\prod_p(1-a_pp^{-s}+\cdots)^{-1}$",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
    )

    out_pdf = out_dir / "fig06_hecke_prime_skeleton.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig06_hecke_prime_skeleton.png", bbox_inches="tight")
    plt.close(fig)


