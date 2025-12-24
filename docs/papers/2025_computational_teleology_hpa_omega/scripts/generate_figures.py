"""Generate figures for the HPA--Omega computational teleology paper.

This script renders Figures 1--5 into ../images as PNG files.

Requirements:
  - numpy
  - matplotlib

All labels are in English.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patches


# -----------------------------
# Styling utilities
# -----------------------------


@dataclass(frozen=True)
class Palette:
    blue: str = "#2196F3"
    green: str = "#4CAF50"
    orange: str = "#FF9800"
    purple: str = "#9C27B0"
    red: str = "#F44336"
    teal: str = "#009688"
    indigo: str = "#3F51B5"
    gray: str = "#607D8B"
    black: str = "#263238"


PAL = Palette()


def _configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "font.size": 10.0,
            "font.family": "DejaVu Sans",
            "axes.titlesize": 11.0,
            "axes.labelsize": 10.0,
            "xtick.labelsize": 9.0,
            "ytick.labelsize": 9.0,
            "legend.fontsize": 9.0,
            "lines.linewidth": 2.0,
        }
    )


def _paper_root() -> str:
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, ".."))


def _images_dir() -> str:
    return os.path.join(_paper_root(), "images")


def _save(fig: plt.Figure, filename: str) -> str:
    out_path = os.path.join(_images_dir(), filename)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


def _add_box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    fc: str,
    ec: str | None = None,
    lw: float = 1.2,
    text_color: str = "white",
    fontsize: float = 9.5,
    rounded: bool = True,
    dashed: bool = False,
) -> patches.FancyBboxPatch:
    if ec is None:
        ec = PAL.black
    boxstyle = "round,pad=0.02,rounding_size=0.02" if rounded else "square,pad=0.02"
    patch = patches.FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=boxstyle,
        linewidth=lw,
        edgecolor=ec,
        facecolor=fc,
        linestyle=(0, (5, 3)) if dashed else "solid",
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2.0,
        y + h / 2.0,
        text,
        ha="center",
        va="center",
        color=text_color,
        fontsize=fontsize,
        wrap=True,
    )
    return patch


def _arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = PAL.black,
    lw: float = 1.4,
    style: str = "-|>",
    connectionstyle: str = "arc3,rad=0.0",
) -> None:
    ax.add_patch(
        patches.FancyArrowPatch(
            start,
            end,
            arrowstyle=style,
            mutation_scale=12,
            linewidth=lw,
            color=color,
            connectionstyle=connectionstyle,
        )
    )


# -----------------------------
# Figure 1: System architecture
# -----------------------------


def fig1_architecture() -> str:
    fig = plt.figure(figsize=(10.5, 4.8))
    ax = fig.add_subplot(111)
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.text(
        0.5,
        0.975,
        "HPA–Omega system architecture: scan–readout + compilation + computability boundary",
        ha="center",
        va="top",
        fontsize=11,
        color=PAL.black,
        weight="bold",
    )

    # Left lane: HPA / scan–readout
    b1 = _add_box(
        ax,
        0.05,
        0.70,
        0.28,
        0.20,
        "HPA: multiplicative ontology\nZ(n)=ρ(n) e^{i θ×(n)}",
        fc=PAL.green,
    )
    b2 = _add_box(
        ax,
        0.05,
        0.47,
        0.28,
        0.18,
        "Unitary scan Θ\ntime = iteration k",
        fc=PAL.blue,
    )
    b3 = _add_box(
        ax,
        0.05,
        0.24,
        0.28,
        0.18,
        "Projection readout Π_W\nbitstream s_k ∈ {0,1}",
        fc=PAL.orange,
        text_color=PAL.black,
    )
    b4 = _add_box(
        ax,
        0.05,
        0.03,
        0.28,
        0.17,
        "Canonical coding\nOstrowski / Zeckendorf",
        fc=PAL.purple,
    )

    _arrow(ax, (0.19, 0.70), (0.19, 0.65))
    _arrow(ax, (0.19, 0.47), (0.19, 0.42))
    _arrow(ax, (0.19, 0.24), (0.19, 0.20))

    # Middle lane: Omega / compilation
    c1 = _add_box(
        ax,
        0.38,
        0.66,
        0.27,
        0.22,
        "Ω: PQCA microdynamics\nlocal step U_R",
        fc=PAL.indigo,
    )
    c2 = _add_box(
        ax,
        0.38,
        0.40,
        0.27,
        0.22,
        "Exact 1D NN compilation\nU_R = E† C_R E",
        fc=PAL.teal,
    )
    c3 = _add_box(
        ax,
        0.38,
        0.14,
        0.27,
        0.22,
        "Routing overhead κ(R)\n(lattice embedding cost)",
        fc=PAL.gray,
    )

    _arrow(ax, (0.515, 0.66), (0.515, 0.62))
    _arrow(ax, (0.515, 0.40), (0.515, 0.36))

    # Central merge: complexity dictionary
    m = _add_box(
        ax,
        0.69,
        0.56,
        0.28,
        0.30,
        "Complexity–geometry dictionary\n\nT ↔ scan depth / compilation depth\nS ↔ readout resolution / workspace",
        fc="#ECEFF1",
        ec=PAL.black,
        text_color=PAL.black,
        fontsize=9.2,
        rounded=True,
    )

    _arrow(ax, (0.33, 0.58), (0.69, 0.66), connectionstyle="arc3,rad=0.05")
    _arrow(ax, (0.65, 0.50), (0.69, 0.66), connectionstyle="arc3,rad=-0.05")

    # Right-bottom: computability boundary + observer interface + phenomenology
    r1 = _add_box(
        ax,
        0.69,
        0.30,
        0.28,
        0.20,
        "Universal QCA\nlocal reachability is undecidable",
        fc=PAL.red,
    )
    r2 = _add_box(
        ax,
        0.69,
        0.06,
        0.28,
        0.20,
        "Phenomenology\nMDR / time-of-flight fits",
        fc="#FFF3E0",
        ec=PAL.black,
        text_color=PAL.black,
    )

    _arrow(ax, (0.83, 0.56), (0.83, 0.50))
    _arrow(ax, (0.83, 0.56), (0.83, 0.26))

    # Observer box (interpretation layer) attached to reachability
    obs = _add_box(
        ax,
        0.69,
        0.30,
        0.28,
        0.20,
        "Observer interface (interpretation)\ninteractive + oracle-like language",
        fc="none",
        ec=PAL.black,
        text_color=PAL.black,
        dashed=True,
        lw=1.1,
        rounded=True,
        fontsize=8.6,
    )
    obs.set_zorder(10)
    r1.set_zorder(1)

    return _save(fig, "fig1_architecture.png")


# -----------------------------
# Figure 2: Lapse and compilation slowdown
# -----------------------------


def fig2_lapse() -> str:
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(10.5, 3.6), gridspec_kw={"wspace": 0.28})

    # Left: region -> 1D tape schematic
    ax0.set_axis_off()
    ax0.set_xlim(0, 1)
    ax0.set_ylim(0, 1)

    ax0.text(0.5, 0.96, "Local step → 1D compilation → routing overhead", ha="center", va="top", weight="bold")

    # Small 2D grid (region)
    grid_x0, grid_y0 = 0.08, 0.50
    cell = 0.06
    for i in range(4):
        for j in range(4):
            ax0.add_patch(
                patches.Rectangle(
                    (grid_x0 + i * cell, grid_y0 + j * cell),
                    cell * 0.92,
                    cell * 0.92,
                    facecolor="#E3F2FD",
                    edgecolor=PAL.blue,
                    linewidth=0.6,
                )
            )
    ax0.text(grid_x0 + 2 * cell, grid_y0 + 4 * cell + 0.04, "region R", ha="center", color=PAL.black)

    # Arrow to tape
    _arrow(ax0, (0.35, 0.62), (0.55, 0.62), color=PAL.black)
    ax0.text(0.45, 0.67, "compile", ha="center", color=PAL.black)

    # 1D tape
    tape_x0, tape_y0 = 0.58, 0.58
    for k in range(10):
        ax0.add_patch(
            patches.Rectangle(
                (tape_x0 + 0.035 * k, tape_y0),
                0.032,
                0.08,
                facecolor="#E8F5E9",
                edgecolor=PAL.green,
                linewidth=0.6,
            )
        )
    ax0.text(0.76, 0.71, "1D NN tape", ha="center", color=PAL.black)

    ax0.text(
        0.58,
        0.45,
        r"depth($C_R$) defines $\kappa(R)$" + "\n" + r"$\mathcal{N}(x)=\kappa_0/\kappa(x)$",
        ha="left",
        va="top",
        fontsize=9.5,
        color=PAL.black,
    )

    # Right: τ_loc vs t plot
    t = np.linspace(0, 10, 400)
    N1 = 1.0
    N2 = 0.35
    tau1 = N1 * t
    tau2 = N2 * t

    ax1.plot(t, tau1, color=PAL.blue, label=r"$\mathcal{N}=1$ (low overhead)")
    ax1.plot(t, tau2, color=PAL.red, label=r"$\mathcal{N}=0.35$ (high overhead)")

    ax1.set_xlabel("baseline depth time  t")
    ax1.set_ylabel(r"local logical time  $\tau_{\mathrm{loc}}$ ")
    ax1.set_title("Time dilation as computational slowdown", fontsize=11, weight="bold")
    ax1.grid(True, alpha=0.25)
    ax1.legend(loc="upper left", frameon=False)

    ax1.text(
        0.02,
        0.06,
        r"$d\tau_{\mathrm{loc}}=\mathcal{N}(x)\,dt\quad\;\mathcal{N}=\kappa_0/\kappa$",
        transform=ax1.transAxes,
        color=PAL.black,
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.25", facecolor="#FFFFFF", edgecolor="#B0BEC5"),
    )

    return _save(fig, "fig2_lapse.png")


# -----------------------------
# Figure 3: Window readout and canonical coding
# -----------------------------


def _wrap01(x: float) -> float:
    return x - math.floor(x)


def fig3_readout() -> str:
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(10.5, 3.8), gridspec_kw={"wspace": 0.30})

    # Left: rotation on circle + window
    ax0.set_aspect("equal")
    ax0.set_axis_off()

    ax0.set_xlim(-1.15, 1.15)
    ax0.set_ylim(-1.15, 1.15)

    # Circle
    ax0.add_patch(patches.Circle((0, 0), 1.0, fill=False, edgecolor=PAL.black, linewidth=1.2))

    # Window W as arc
    w_start = 20  # degrees
    w_width = 70
    ax0.add_patch(
        patches.Wedge(
            (0, 0),
            1.02,
            w_start,
            w_start + w_width,
            width=0.16,
            facecolor="#FFE0B2",
            edgecolor=PAL.orange,
            linewidth=1.0,
        )
    )
    ax0.text(0.45, 0.95, "window W", color=PAL.black, ha="center", va="bottom")

    # Orbit points
    alpha = (math.sqrt(5) - 1) / 2  # golden inverse
    x0 = 0.11
    K = 34
    pts = [_wrap01(x0 + k * alpha) for k in range(K)]
    angles = [2 * math.pi * p for p in pts]

    def in_window(p: float) -> bool:
        ang = (p * 360.0) % 360.0
        return (w_start <= ang <= w_start + w_width)

    xs = [math.cos(a) for a in angles]
    ys = [math.sin(a) for a in angles]

    colors = [PAL.red if in_window(p) else PAL.blue for p in pts]
    ax0.scatter(xs, ys, s=22, c=colors, alpha=0.95, edgecolors="white", linewidths=0.3)

    ax0.text(0.0, -1.08, "Unitary scan: x ↦ x+α (mod 1)", ha="center", color=PAL.black)
    ax0.text(0.0, -1.22, "Readout: s_k = 1_W(x_0+kα)", ha="center", color=PAL.black)

    # Right: bitstream + coding
    ax1.set_axis_off()
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)

    ax1.text(0.5, 0.96, "Readout resolution and canonical coding", ha="center", va="top", weight="bold")

    # Generate bitstream
    s = [1 if in_window(p) else 0 for p in pts]

    # Draw bits
    x0b, y0b = 0.06, 0.70
    bw, bh = 0.025, 0.12
    for i, bit in enumerate(s[:30]):
        fc = "#FFCDD2" if bit == 1 else "#BBDEFB"
        ec = PAL.red if bit == 1 else PAL.blue
        ax1.add_patch(patches.Rectangle((x0b + i * (bw + 0.004), y0b), bw, bh, facecolor=fc, edgecolor=ec, linewidth=0.6))
        ax1.text(x0b + i * (bw + 0.004) + bw / 2, y0b + bh / 2, str(bit), ha="center", va="center", fontsize=7, color=PAL.black)

    ax1.text(0.06, 0.60, "prefix length N increases readout resolution", ha="left", color=PAL.black)

    # Show S_N and alpha estimate
    N = 30
    SN = sum(s[:N])
    ax1.text(0.06, 0.52, f"S_N = Σ s_k = {SN}   →   α̂ = S_N/N ≈ {SN/N:.3f}", ha="left", color=PAL.black)

    # Zeckendorf-style schematic coding bar (no adjacent ones)
    ax1.text(0.06, 0.40, "canonical code (golden branch): Zeckendorf digits", ha="left", color=PAL.black)

    # A simple example digit pattern (no adjacent ones)
    digits = [1, 0, 1, 0, 0, 1, 0, 1, 0, 0]
    x0d, y0d = 0.06, 0.22
    dw, dh = 0.05, 0.12
    for i, d in enumerate(digits):
        fc = "#E1BEE7" if d == 1 else "#ECEFF1"
        ec = PAL.purple if d == 1 else "#B0BEC5"
        ax1.add_patch(patches.Rectangle((x0d + i * (dw + 0.01), y0d), dw, dh, facecolor=fc, edgecolor=ec, linewidth=0.8))
        ax1.text(x0d + i * (dw + 0.01) + dw / 2, y0d + dh / 2, str(d), ha="center", va="center", fontsize=9, color=PAL.black)

    ax1.text(0.06, 0.10, "digit depth m ~ log N (compressed description length)", ha="left", color=PAL.black)

    return _save(fig, "fig3_readout.png")


# -----------------------------
# Figure 4: Undecidable reachability
# -----------------------------


def fig4_undecidability() -> str:
    fig = plt.figure(figsize=(10.5, 3.8))
    ax = fig.add_subplot(111)
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.text(0.5, 0.96, "Universal QCA: local reachability as a halting predicate", ha="center", va="top", weight="bold")

    a = _add_box(
        ax,
        0.05,
        0.62,
        0.26,
        0.22,
        "Instance (M, x)\nreversible computation",
        fc=PAL.gray,
    )
    b = _add_box(
        ax,
        0.35,
        0.62,
        0.26,
        0.22,
        "Encode as QCA initial state\n|ψ_{M,x}⟩",
        fc=PAL.blue,
    )
    c = _add_box(
        ax,
        0.65,
        0.62,
        0.30,
        0.22,
        "Evolve by U^t\n(local unitary dynamics)",
        fc=PAL.green,
    )

    _arrow(ax, (0.31, 0.73), (0.35, 0.73))
    _arrow(ax, (0.61, 0.73), (0.65, 0.73))

    d = _add_box(
        ax,
        0.18,
        0.28,
        0.32,
        0.22,
        "Local flag region K\nprojector Π_K",
        fc=PAL.orange,
        text_color=PAL.black,
    )
    e = _add_box(
        ax,
        0.55,
        0.28,
        0.40,
        0.22,
        "Predicate: ∃t ≥ 0 such that\n⟨ψ_{M,x}|U^{†t} Π_K U^t|ψ_{M,x}⟩ > 0",
        fc="#FFF3E0",
        ec=PAL.black,
        text_color=PAL.black,
        fontsize=8.8,
    )

    _arrow(ax, (0.80, 0.62), (0.80, 0.50), connectionstyle="arc3,rad=0.0")
    _arrow(ax, (0.80, 0.50), (0.67, 0.50), connectionstyle="arc3,rad=0.0")
    _arrow(ax, (0.50, 0.39), (0.55, 0.39))

    ax.text(
        0.05,
        0.08,
        "Reduction: halting ⇔ local flag ever triggers  ⇒ reachability is undecidable.",
        ha="left",
        va="center",
        color=PAL.black,
    )

    return _save(fig, "fig4_undecidability.png")


# -----------------------------
# Figure 5: Dispersion and group velocity
# -----------------------------


def fig5_dispersion() -> str:
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(10.5, 3.8), gridspec_kw={"wspace": 0.28})

    eps = 1.0
    P_max = 0.99 * (2.0 / eps)  # domain: |eps P / 2| <= 1
    P = np.linspace(0, P_max, 700)
    E = (2 / eps) * np.arcsin((eps * P) / 2)
    ax0.plot(P, E, color=PAL.blue, label=r"$E(P)=\frac{2}{\varepsilon}\arcsin(\varepsilon P/2)$")
    ax0.plot(P, P, color=PAL.black, linestyle="--", linewidth=1.2, label=r"$E=P$ (low-energy)")

    ax0.set_title("Discrete-scan dispersion", weight="bold")
    ax0.set_xlabel("momentum  P")
    ax0.set_ylabel("energy  E")
    ax0.grid(True, alpha=0.25)
    ax0.legend(frameon=False, loc="upper left")

    vg = 1.0 / np.sqrt(1.0 - (eps * P / 2.0) ** 2)
    ax1.plot(P, vg, color=PAL.red, label=r"$v_g=dE/dP$")
    ax1.axhline(1.0, color=PAL.black, linestyle="--", linewidth=1.2, label="v=1")

    ax1.set_title("Energy-dependent group velocity", weight="bold")
    ax1.set_xlabel("momentum  P")
    ax1.set_ylabel("group velocity  v_g")
    ax1.set_ylim(0.0, min(6.0, float(np.nanmax(vg[vg < 10]))))
    ax1.grid(True, alpha=0.25)
    ax1.legend(frameon=False, loc="upper left")

    ax1.text(
        0.02,
        0.06,
        "Front velocity remains bounded\nby locality (Lieb–Robinson).",
        transform=ax1.transAxes,
        fontsize=9.5,
        color=PAL.black,
        bbox=dict(boxstyle="round,pad=0.25", facecolor="#FFFFFF", edgecolor="#B0BEC5"),
    )

    return _save(fig, "fig5_dispersion.png")


def main() -> None:
    _configure_matplotlib()
    os.makedirs(_images_dir(), exist_ok=True)

    outputs = [
        fig1_architecture(),
        fig2_lapse(),
        fig3_readout(),
        fig4_undecidability(),
        fig5_dispersion(),
    ]

    print("Generated:")
    for p in outputs:
        print(" -", p)


if __name__ == "__main__":
    main()
