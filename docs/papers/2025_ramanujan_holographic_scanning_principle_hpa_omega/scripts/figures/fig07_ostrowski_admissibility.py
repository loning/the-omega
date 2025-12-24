from __future__ import annotations

from pathlib import Path


def build(out_dir: Path, *, png: bool = False) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.8, 3.2))
    fig.suptitle("Ostrowski coding and the Zeckendorf specialization (example)", fontsize=12)

    for ax in (ax1, ax2):
        ax.set_axis_off()

    def cell(ax, x, y, w, h, text, *, face="#f2f2f2", weight="normal"):
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
            fontsize=9.5,
            fontweight=weight,
        )

    # Left panel: a concrete Ostrowski-style encoding example for alpha=[0;2,2,2,...] (sqrt(2)-1).
    q = [1, 2, 5, 12, 29, 70]
    b = [1, 1, 0, 2, 0, 1]  # valid digits with the local rule (if b_n=2 then b_{n-1}=0)
    n_val = sum(qi * bi for qi, bi in zip(q, b))

    ax1.text(0.02, 0.92, r"Example slope: $\alpha=[0;2,2,2,\dots]$", transform=ax1.transAxes, fontsize=10)
    ax1.text(
        0.02,
        0.84,
        r"Convergent basis $q_n$ (Pell-type growth) and digits $b_n$",
        transform=ax1.transAxes,
        fontsize=9,
    )

    x0 = 0.02
    y_q = 0.62
    y_b = 0.44
    w_left = 0.145
    h = 0.12

    ax1.text(x0, y_q + 0.14, r"$q_n$:", transform=ax1.transAxes, fontsize=9.5)
    ax1.text(x0, y_b + 0.14, r"$b_n$:", transform=ax1.transAxes, fontsize=9.5)

    for i, (qi, bi) in enumerate(zip(q, b)):
        face_q = "#e3f2fd"
        face_b = "#e8f5e9" if bi != 0 else "#f2f2f2"
        cell(ax1, x0 + (i + 1) * w_left, y_q, w_left * 0.92, h, f"{qi}", face=face_q)
        cell(
            ax1,
            x0 + (i + 1) * w_left,
            y_b,
            w_left * 0.92,
            h,
            f"{bi}",
            face=face_b,
            weight="bold" if bi else "normal",
        )

    ax1.text(
        0.02,
        0.26,
        rf"$N=\sum_n b_n q_n = {n_val}$",
        transform=ax1.transAxes,
        fontsize=10,
    )
    ax1.text(
        0.02,
        0.18,
        r"Local admissibility (typical): $0\leq b_n\leq a_{n+1}$ and",
        transform=ax1.transAxes,
        fontsize=9,
    )
    ax1.text(
        0.02,
        0.11,
        r"if $b_n=a_{n+1}$ then $b_{n-1}=0$ (checkable without global carries).",
        transform=ax1.transAxes,
        fontsize=9,
    )

    # Highlight the "max digit implies previous zero" pattern in the example at n=3 (b_3=2, b_2=0).
    hi_x = x0 + (3 + 1) * w_left
    cell(ax1, hi_x, y_b, w_left * 0.92, h, "2", face="#fff3e0", weight="bold")
    cell(ax1, x0 + (2 + 1) * w_left, y_b, w_left * 0.92, h, "0", face="#fff3e0")
    ax1.text(0.64, 0.29, r"$b_3=2$ forces $b_2=0$", transform=ax1.transAxes, fontsize=9)

    # Right panel: golden branch = Zeckendorf example for the same N.
    fib = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
    digits = [0, 0, 0, 0, 1, 0, 0, 0, 0, 1]  # 89 + 8 = 97

    ax2.text(0.02, 0.92, r"Golden branch: $\alpha=\varphi^{-1}$", transform=ax2.transAxes, fontsize=10)
    ax2.text(0.02, 0.84, r"Zeckendorf representation (no adjacent $1$'s)", transform=ax2.transAxes, fontsize=9)

    y_f = 0.62
    y_d = 0.44
    ax2.text(0.02, y_f + 0.14, "Fibonacci:", transform=ax2.transAxes, fontsize=9.5)
    ax2.text(0.02, y_d + 0.14, "digit:", transform=ax2.transAxes, fontsize=9.5)

    w_right = 0.085
    for i, (fi, di) in enumerate(zip(fib, digits)):
        face_f = "#e3f2fd" if di else "#f2f2f2"
        face_d = "#e8f5e9" if di else "#f2f2f2"
        cell(
            ax2,
            x0 + (i + 1) * w_right,
            y_f,
            w_right * 0.92,
            h,
            f"{fi}",
            face=face_f,
            weight="bold" if di else "normal",
        )
        cell(
            ax2,
            x0 + (i + 1) * w_right,
            y_d,
            w_right * 0.92,
            h,
            f"{di}",
            face=face_d,
            weight="bold" if di else "normal",
        )

    ax2.text(
        0.02,
        0.26,
        rf"$N={n_val}=89+8$",
        transform=ax2.transAxes,
        fontsize=10,
    )
    ax2.text(
        0.02,
        0.18,
        r"Rule: $\epsilon_k\in\{0,1\}$ and $\epsilon_k\epsilon_{k+1}=0$",
        transform=ax2.transAxes,
        fontsize=9,
    )

    out_pdf = out_dir / "fig07_ostrowski_admissibility.pdf"
    fig.savefig(out_pdf, bbox_inches="tight")
    if png:
        fig.savefig(out_dir / "fig07_ostrowski_admissibility.png", bbox_inches="tight")
    plt.close(fig)


