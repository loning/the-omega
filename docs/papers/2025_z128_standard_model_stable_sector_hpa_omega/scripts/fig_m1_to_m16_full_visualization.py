# -*- coding: utf-8 -*-
"""
Figure: Complete visualization of m=1 to m=16 resolution spectrum.

This script generates a comprehensive visualization showing:
1. Stable type counts |X_m| for m=1 to m=16
2. Cyclic/boundary split at each m
3. Different coupling relationships: m=2n (2D), m=3n (3D), m=dn (general)
4. Energy thresholds μ_th(m) under the staircase calibration
5. Physical regime markers (electron, QCD, EW, BSM, etc.)

Key insight: n is NOT necessarily m/2. The relationship depends on the addressing dimension:
- 2D Hilbert screen: m = 2n (balanced coupling, used in paper)
- 3D screen: m = 3n
- d-dimensional: m = d*n

Outputs:
  - figures/m1_to_m16_full_visualization.png

This visualization demonstrates that balanced coupling m=2n is a diagnostic convention
for the 2D Hilbert screen, not a theorem-level necessity.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# Force a non-interactive backend for deterministic headless rendering.
import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle, FancyBboxPatch  # noqa: E402

from common_constants import M_E_GEV, PHI  # noqa: E402
from common_paths import figures_dir  # noqa: E402


def fib(n: int) -> int:
    """Fibonacci numbers with F1=F2=1."""
    if n <= 0:
        raise ValueError("n must be positive.")
    if n in (1, 2):
        return 1
    a, b = 1, 1
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b


def xm_counts(m: int) -> Tuple[int, int, int]:
    """Return (total, cyclic, boundary) counts for |X_m|."""
    total = fib(m + 2)
    bdry = fib(m - 2) if m >= 4 else 0
    cyc = total - bdry
    return total, cyc, bdry


def mu_threshold(m: int, r_step: float = 2.0 * math.pi) -> float:
    """Compute energy threshold μ_th(m) under staircase calibration."""
    r_th = float(m - 6) * r_step
    return M_E_GEV * (PHI ** r_th)


def fmt_energy(mu: float) -> str:
    """Format energy in readable units."""
    if mu == 0.0:
        return "0"
    if mu < 1.0e-3:
        return f"{mu*1e6:.3f} keV"
    if mu < 1.0:
        return f"{mu*1e3:.3f} MeV"
    if mu < 1e3:
        return f"{mu:.3f} GeV"
    return f"{mu/1e3:.3f} TeV"


def get_physical_regime(m: int) -> Tuple[str, str]:
    """Get physical regime label and color for m."""
    mu = mu_threshold(m)
    if m < 6:
        return ("pre-geometric", "#9E9E9E")
    elif m == 6:
        return ("electron/SM anchor", "#1565C0")
    elif m == 7:
        return ("nuclear binding", "#42A5F5")
    elif m == 8:
        return ("QCD scale", "#7B1FA2")
    elif m == 9:
        return ("bottom threshold", "#EF6C00")
    elif m == 10:
        return ("electroweak/Higgs", "#C62828")
    elif m == 11:
        return ("BSM frontier", "#D84315")
    elif m >= 12:
        return ("deep UV", "#37474F")
    else:
        return ("unknown", "#9E9E9E")


def main() -> None:
    out_dir: Path = figures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    m_list = list(range(1, 17))  # m=1 to m=16
    r_step = 2.0 * math.pi

    # Create figure with multiple panels
    fig = plt.figure(figsize=(20.0, 14.0))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.25,
                          height_ratios=[1.0, 1.0, 1.2],
                          width_ratios=[1.0, 1.0])

    # Panel 1: Stable type counts growth (top-left)
    ax1 = fig.add_subplot(gs[0, 0])
    totals = [xm_counts(m)[0] for m in m_list]
    cyclic = [xm_counts(m)[1] for m in m_list]
    boundary = [xm_counts(m)[2] for m in m_list]

    x_pos = np.arange(len(m_list))
    width = 0.25
    ax1.bar(x_pos - width, cyclic, width, label="Cyclic", color="#2E7D32", alpha=0.8)
    ax1.bar(x_pos, boundary, width, label="Boundary", color="#C62828", alpha=0.8)
    ax1.bar(x_pos + width, totals, width, label="Total", color="#1565C0", alpha=0.6,
            edgecolor="black", linewidth=1.5)

    ax1.set_xlabel("Window length $m$", fontsize=12)
    ax1.set_ylabel("Stable type count $|X_m|$", fontsize=12)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels([f"${m}$" for m in m_list], fontsize=9)
    ax1.legend(loc="upper left", fontsize=10)
    ax1.grid(True, alpha=0.3, axis="y")
    ax1.set_title("Stable type counts: $|X_m| = F_{m+2}$\n(Cyclic + Boundary split)", fontsize=12, pad=10)
    ax1.set_yscale("log")

    # Add annotations for key m values
    key_m = [6, 8, 10, 12]
    for m in key_m:
        if m in m_list:
            idx = m_list.index(m)
            total = totals[idx]
            ax1.annotate(f"$m={m}$\n$|X_{m}|={total}$",
                        xy=(idx, total), xytext=(idx, total * 3),
                        arrowprops=dict(arrowstyle="->", color="#D84315", lw=1.5),
                        fontsize=9, ha="center", color="#D84315", weight="bold")

    # Panel 2: Energy threshold staircase (top-right)
    ax2 = fig.add_subplot(gs[0, 1])
    energies = [mu_threshold(m, r_step) for m in m_list]
    log_energies = [math.log10(e) if e > 0 else -10 for e in energies]

    # Step plot
    ax2.step(m_list, log_energies, where="post", linewidth=2.5, color="#1565C0", label="Staircase")
    ax2.scatter(m_list, log_energies, s=60, c="#D84315", zorder=5, edgecolors="white", linewidths=1.5)

    # Color-code by physical regime
    for m in m_list:
        idx = m_list.index(m)
        regime, color = get_physical_regime(m)
        if m >= 6:
            ax2.scatter([m], [log_energies[idx]], s=100, c=color, zorder=6,
                       edgecolors="black", linewidths=1.5, alpha=0.7)

    ax2.set_xlabel("Window length $m$", fontsize=12)
    ax2.set_ylabel("log$_{10}$(threshold energy [GeV])", fontsize=12)
    ax2.set_title("Energy threshold staircase\n$\\mu_{\\mathrm{th}}(m) = m_e \\cdot \\varphi^{2\\pi(m-6)}$", fontsize=12, pad=10)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="lower right", fontsize=10)

    # Add regime labels
    for m in [6, 8, 10, 11]:
        if m in m_list:
            idx = m_list.index(m)
            regime, _ = get_physical_regime(m)
            ax2.annotate(regime, xy=(m, log_energies[idx]),
                        xytext=(10, 10), textcoords="offset points",
                        fontsize=9, bbox=dict(boxstyle="round,pad=0.3", facecolor="wheat", alpha=0.8),
                        arrowprops=dict(arrowstyle="->", lw=1.2))

    # Panel 3: Coupling relationships (bottom-left)
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.axis("off")

    # Create a conceptual diagram showing different coupling relationships
    title_text = "Coupling relationships: $m$ vs addressing dimension $d$"
    ax3.text(0.5, 0.95, title_text, transform=ax3.transAxes,
            ha="center", va="top", fontsize=13, weight="bold")

    # Show different dimensions
    dims = [
        ("2D Hilbert screen\n(paper convention)", 2, "#1565C0", "m = 2n"),
        ("3D screen\n(alternative)", 3, "#2E7D32", "m = 3n"),
        ("d-dimensional\n(general)", None, "#9E9E9E", "m = d·n"),
    ]

    y_start = 0.75
    y_step = 0.20
    for i, (label, d, color, formula) in enumerate(dims):
        y = y_start - i * y_step
        # Draw box
        rect = FancyBboxPatch((0.1, y - 0.08), 0.8, 0.12,
                             boxstyle="round,pad=0.02", facecolor=color, alpha=0.3,
                             edgecolor=color, linewidth=2)
        ax3.add_patch(rect)
        ax3.text(0.5, y, f"{label}\n${formula}$", transform=ax3.transAxes,
                ha="center", va="center", fontsize=11, weight="bold")

    # Add example table using matplotlib table
    table_y = 0.15
    ax3.text(0.5, table_y + 0.20, "Examples for $m=6$:", transform=ax3.transAxes,
            ha="center", fontsize=11, weight="bold")
    
    # Create a simple table using matplotlib table
    example_table_data = [
        ["Dimension", "Grid", "Sites"],
        ["2D: $n=3$", "$8\\times 8$", "64"],
        ["3D: $n=2$", "$4\\times 4\\times 4$", "64"],
    ]
    
    # Create table at specific position
    table3 = ax3.table(cellText=example_table_data[1:], colLabels=example_table_data[0],
                      cellLoc="center", loc="center",
                      bbox=[0.2, table_y - 0.12, 0.6, 0.10])
    table3.auto_set_font_size(False)
    table3.set_fontsize(9)
    table3.scale(1, 1.5)
    
    # Style header
    for i in range(3):
        table3[(0, i)].set_facecolor("#1565C0")
        table3[(0, i)].set_text_props(weight="bold", color="white")

    ax3.set_xlim(0, 1)
    ax3.set_ylim(0, 1)

    # Panel 4: n values for different coupling schemes (bottom-right)
    ax4 = fig.add_subplot(gs[1, 1])
    
    # Calculate n for different dimensions
    m_array = np.array(m_list)
    n_2d = m_array / 2.0  # 2D: m = 2n
    n_3d = m_array / 3.0  # 3D: m = 3n
    
    ax4.plot(m_array, n_2d, "o-", linewidth=2.5, markersize=8, label="2D: $n = m/2$", color="#1565C0")
    ax4.plot(m_array, n_3d, "s-", linewidth=2.5, markersize=8, label="3D: $n = m/3$", color="#2E7D32")
    
    # Highlight integer n values
    for m in m_list:
        n2 = m / 2.0
        n3 = m / 3.0
        if n2 == int(n2):
            ax4.scatter([m], [n2], s=150, c="#1565C0", marker="*", zorder=5, edgecolors="white", linewidths=1)
        if abs(n3 - round(n3)) < 1e-6:
            ax4.scatter([m], [n3], s=150, c="#2E7D32", marker="*", zorder=5, edgecolors="white", linewidths=1)
    
    ax4.set_xlabel("Window length $m$", fontsize=12)
    ax4.set_ylabel("Hilbert order $n$", fontsize=12)
    ax4.set_title("Coupling relationships:\n$n$ as function of $m$ for different screen dimensions", fontsize=12, pad=10)
    ax4.legend(loc="upper left", fontsize=10)
    ax4.grid(True, alpha=0.3)
    
    # Add annotations
    ax4.annotate("Balanced coupling\n(2D, paper)", xy=(6, 3), xytext=(8, 5),
                arrowprops=dict(arrowstyle="->", color="#1565C0", lw=2),
                fontsize=10, color="#1565C0", weight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))

    # Panel 5: Comprehensive table (bottom, spanning both columns)
    ax5 = fig.add_subplot(gs[2, :])
    ax5.axis("off")

    # Create a comprehensive data table
    table_data = []
    table_data.append(["$m$", "$|X_m|$", "Cyclic", "Boundary", "$\\mu_{\\mathrm{th}}$ [GeV]", "Regime", "$n$ (2D)", "$n$ (3D)"])
    
    for m in m_list:
        total, cyc, bdry = xm_counts(m)
        mu = mu_threshold(m, r_step)
        regime, _ = get_physical_regime(m)
        n_2d_val = m / 2.0
        n_3d_val = m / 3.0
        
        # Format n values (show as integer if exact, otherwise decimal)
        n2_str = f"${int(n_2d_val)}$" if n_2d_val == int(n_2d_val) else f"${n_2d_val:.1f}$"
        n3_str = f"${int(n_3d_val)}$" if abs(n_3d_val - round(n_3d_val)) < 1e-6 else f"${n_3d_val:.2f}$"
        
        table_data.append([
            f"${m}$",
            f"${total}$",
            f"${cyc}$",
            f"${bdry}$",
            fmt_energy(mu),
            regime,
            n2_str,
            n3_str
        ])

    # Create table
    table = ax5.table(cellText=table_data[1:], colLabels=table_data[0],
                     cellLoc="center", loc="center",
                     colWidths=[0.08, 0.12, 0.12, 0.12, 0.18, 0.20, 0.09, 0.09])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.0)

    # Style header
    for i in range(len(table_data[0])):
        table[(0, i)].set_facecolor("#1565C0")
        table[(0, i)].set_text_props(weight="bold", color="white")

    # Style rows by regime
    for i, m in enumerate(m_list, start=1):
        regime, color = get_physical_regime(m)
        if m >= 6:
            for j in range(len(table_data[0])):
                table[(i, j)].set_facecolor(color)
                table[(i, j)].set_alpha(0.3)
        if m in [6, 8, 10, 11]:
            for j in range(len(table_data[0])):
                table[(i, j)].set_edgecolor("#D84315")
                table[(i, j)].set_linewidth(2)

    ax5.set_title("Complete resolution spectrum: m=1 to m=16\n"
                 "Note: $n = m/2$ only for 2D balanced coupling; $n = m/3$ for 3D; general: $n = m/d$",
                 fontsize=12, pad=20, weight="bold")

    fig.suptitle(
        "Complete resolution spectrum visualization: m=1 to m=16\n"
        "Stable types, energy thresholds, and coupling relationships",
        fontsize=16,
        y=0.995,
        weight="bold"
    )

    out_png = out_dir / "m1_to_m16_full_visualization.png"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")


if __name__ == "__main__":
    main()
