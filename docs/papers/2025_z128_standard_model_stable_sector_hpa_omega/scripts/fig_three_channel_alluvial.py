# -*- coding: utf-8 -*-
"""
Figure: "bio-style" folding/funneling visualization for the m=6 anchor.

We mimic protein/DNA-style pathway/folding-funnel readability:
  Ω6 (64 microstates)  --Fold_6-->  X6 (21 stable labels, with fiber sizes g(w))
                               --π-->  cyclic vs boundary split (18 ⊕ 3 at the label level)
  ε is shown as an annotation layer (analytic dictionary), not a geometric axis.

Output:
  - figures/three_channel_alluvial.png
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, PathPatch  # noqa: E402
from matplotlib.path import Path as MplPath  # noqa: E402

import exp_fold6_stats as fold  # noqa: E402
from common_paths import figures_dir  # noqa: E402


def is_boundary_word(w: str) -> bool:
    return len(w) == 6 and w[0] == "1" and w[-1] == "1"


def _rounded_box(ax, x: float, y: float, w: float, h: float, fc: str, ec: str, text: str, fs: int = 11) -> None:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.2,
        facecolor=fc,
        edgecolor=ec,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color="#111111")


def _ribbon(ax, x0: float, y0a: float, y0b: float, x1: float, y1a: float, y1b: float, color: str, alpha: float = 0.55) -> None:
    """
    Draw a smooth alluvial ribbon between [y0a,y0b] at x0 and [y1a,y1b] at x1.
    """
    # Cubic Bezier control points for smoothness.
    dx = x1 - x0
    c1 = x0 + 0.35 * dx
    c2 = x0 + 0.65 * dx

    verts = [
        (x0, y0a),
        (c1, y0a),
        (c2, y1a),
        (x1, y1a),
        (x1, y1b),
        (c2, y1b),
        (c1, y0b),
        (x0, y0b),
        (x0, y0a),
    ]
    codes = [
        MplPath.MOVETO,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.LINETO,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CURVE4,
        MplPath.CLOSEPOLY,
    ]
    patch = PathPatch(MplPath(verts, codes), facecolor=color, edgecolor="none", alpha=alpha)
    ax.add_patch(patch)


def main() -> None:
    out_dir: Path = figures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build Fold_6 preimages: k=0..63 -> w in X6.
    pre: Dict[str, List[int]] = defaultdict(list)
    for k in range(64):
        w = fold.fold6(k)
        pre[w].append(k)

    X6 = sorted(pre.keys())
    if len(X6) != 21:
        raise AssertionError(f"Expected 21 stable types at m=6, got {len(X6)}.")

    # Order panels by V(w) (Zeckendorf value) then by word (deterministic).
    X6 = sorted(X6, key=lambda w: (fold.zeckendorf_value_of_word(w), w))

    # Sizes.
    sizes = {w: len(pre[w]) for w in X6}
    total = sum(sizes.values())
    if total != 64:
        raise AssertionError("Preimage sizes must sum to 64.")

    # Colors (Material-ish).
    c_omega = "#ECEFF1"
    c_mid_cyc = "#1565C0"  # blue
    c_mid_bdry = "#2E7D32"  # green
    c_edge = "#263238"
    c_eps = "#EF6C00"  # orange

    # Layout coordinates in [0,1] figure space.
    x_omega = 0.08
    x_mid = 0.46
    x_pi = 0.84
    box_w = 0.10

    # Vertical extent for the flow area.
    y0 = 0.12
    y1 = 0.88
    H = y1 - y0

    # Map total=64 to full height.
    unit = H / float(total)

    fig, ax = plt.subplots(figsize=(12.8, 7.0))
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")

    # Left: Ω6 box
    _rounded_box(ax, x_omega, y0, box_w, H, fc=c_omega, ec=c_edge, text="Ω₆\n64", fs=13)

    # Middle: stacked 21 blocks (X6) with widths fixed, heights proportional to g(w).
    # Right: two blocks (cyc vs bdry) but we also show the internal 21 split by ribbons.
    # Compute stack positions for X6.
    mid_pos: Dict[str, Tuple[float, float]] = {}
    cur = y0
    for w in X6:
        h = unit * float(sizes[w])
        mid_pos[w] = (cur, cur + h)
        cur += h

    # Draw middle stack blocks + labels.
    for w in X6:
        ya, yb = mid_pos[w]
        h = yb - ya
        fc = c_mid_bdry if is_boundary_word(w) else c_mid_cyc
        ax.add_patch(
            FancyBboxPatch(
                (x_mid, ya),
                box_w,
                h,
                boxstyle="round,pad=0.006,rounding_size=0.01",
                linewidth=0.8,
                facecolor=fc,
                edgecolor="white",
                alpha=0.95,
            )
        )
        v = fold.zeckendorf_value_of_word(w)
        g = sizes[w]
        # Small label; keep readable by truncating to word+g.
        ax.text(x_mid + box_w + 0.012, (ya + yb) / 2, f"{w}  g={g}", ha="left", va="center", fontsize=9, color="#111111")
        # Optional: value as lighter text when space allows.
        if h >= 3.0 * unit:
            ax.text(x_mid + box_w + 0.012, (ya + yb) / 2 - 0.016, f"V={v}", ha="left", va="center", fontsize=8, color="#546E7A")

    # Left->Middle ribbons: Ω6 funnels into 21 stable labels with thickness g(w).
    cur_left = y0
    for w in X6:
        h = unit * float(sizes[w])
        yla, ylb = cur_left, cur_left + h
        yma, ymb = mid_pos[w]
        cur_left += h
        color = c_mid_bdry if is_boundary_word(w) else c_mid_cyc
        _ribbon(ax, x_omega + box_w, yla, ylb, x_mid, yma, ymb, color=color, alpha=0.30)

    # Right: π split blocks (aggregate by microstate weight).
    cyc_mass = sum(sizes[w] for w in X6 if not is_boundary_word(w))
    bdry_mass = sum(sizes[w] for w in X6 if is_boundary_word(w))
    if cyc_mass + bdry_mass != 64:
        raise AssertionError("Split masses must sum to 64.")

    # Place two blocks on the right, stacked (cyc on top for convention).
    # We'll stack with same total height H.
    bdry_h = unit * float(bdry_mass)
    cyc_h = unit * float(cyc_mass)
    y_bdry = (y0, y0 + bdry_h)
    y_cyc = (y0 + bdry_h, y0 + bdry_h + cyc_h)

    # Draw right blocks.
    ax.add_patch(
        FancyBboxPatch(
            (x_pi, y_cyc[0]),
            box_w,
            y_cyc[1] - y_cyc[0],
            boxstyle="round,pad=0.008,rounding_size=0.02",
            linewidth=1.0,
            facecolor=c_mid_cyc,
            edgecolor=c_edge,
            alpha=0.90,
        )
    )
    ax.add_patch(
        FancyBboxPatch(
            (x_pi, y_bdry[0]),
            box_w,
            y_bdry[1] - y_bdry[0],
            boxstyle="round,pad=0.008,rounding_size=0.02",
            linewidth=1.0,
            facecolor=c_mid_bdry,
            edgecolor=c_edge,
            alpha=0.90,
        )
    )
    ax.text(x_pi + box_w / 2, (y_cyc[0] + y_cyc[1]) / 2, f"π: cyclic\nmass={cyc_mass}", ha="center", va="center", fontsize=11, color="white")
    ax.text(x_pi + box_w / 2, (y_bdry[0] + y_bdry[1]) / 2, f"π: boundary\nmass={bdry_mass}", ha="center", va="center", fontsize=11, color="white")

    # Middle->Right ribbons: each stable label goes to cyc or bdry aggregate.
    cur_cyc = y_cyc[0]
    cur_bdry = y_bdry[0]
    for w in X6:
        h = unit * float(sizes[w])
        yma, ymb = mid_pos[w]
        if is_boundary_word(w):
            y1a, y1b = cur_bdry, cur_bdry + h
            cur_bdry += h
            color = c_mid_bdry
        else:
            y1a, y1b = cur_cyc, cur_cyc + h
            cur_cyc += h
            color = c_mid_cyc
        _ribbon(ax, x_mid + box_w, yma, ymb, x_pi, y1a, y1b, color=color, alpha=0.35)

    # ε annotation "layer" (bio-style: like a functional annotation bar).
    ax.text(
        0.50,
        0.95,
        "ε channel: analytic dictionary layer (Artin–Mazur zeta + Abel normalization)\n"
        "Used for interpretation / higher-m templates; not an extra reduction at m=6",
        ha="center",
        va="top",
        fontsize=11,
        color=c_eps,
    )

    ax.text(0.50, 0.04, "Fold_6 funnel + π split (width ∝ microstate degeneracy g(w))", ha="center", va="bottom", fontsize=10, color="#455A64")

    out_png = out_dir / "three_channel_alluvial.png"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")


if __name__ == "__main__":
    main()

