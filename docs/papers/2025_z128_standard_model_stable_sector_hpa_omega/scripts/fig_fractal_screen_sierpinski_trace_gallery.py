# -*- coding: utf-8 -*-
"""
Figure: non-integer effective dimension via a fractal screen (Sierpiński carpet).

We use a 2D Sierpiński-carpet screen with scale factor s=3 and branching b=8:
  - fractal dimension d = log(b)/log(s) = log(8)/log(3) ≈ 1.8928 (non-integer)
  - at iteration depth t, the number of occupied cells is b^t = 8^t = 2^{3t}

Hence, for m = 3t we have |Ω_m| = 2^m = 8^t, giving a bijection between
microstate indices k ∈ {0..2^m-1} and occupied fractal cells at depth t.

Addressing (explicit, deterministic):
  - write k in base-8 (equivalently, group m bits into 3-bit chunks),
  - each octal digit selects one of the 8 allowed (dx,dy) positions in a 3×3 block
    excluding the center (1,1),
  - recurse to obtain an (x,y) coordinate on a 3^t × 3^t grid.

Per row we trace one representative stable type w0=0...0:
  (A) scan-index axis highlighting k with Fold_m(k)=w0
  (B) fractal screen highlight of the corresponding (x,y) sites
  (C) a small table listing (k, bits_m(k), screen(x,y))

Output:
  - figures/fractal_screen_sierpinski_trace_gallery.png
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

import exp_foldm_stats as fm  # noqa: E402
from common_paths import figures_dir  # noqa: E402


def bits_m(k: int, m: int) -> str:
    return format(int(k), f"0{m}b")


# 8 allowed positions in a 3×3 block excluding center (1,1), row-major.
_POS8: List[Tuple[int, int]] = [
    (0, 0),
    (1, 0),
    (2, 0),
    (0, 1),
    (2, 1),
    (0, 2),
    (1, 2),
    (2, 2),
]


def sierpinski_carpet_coord_from_k(k: int, t: int) -> Tuple[int, int]:
    """
    Map k in {0..8^t-1} to an occupied Sierpiński-carpet cell coordinate (x,y) on a 3^t grid.
    Uses 3-bit chunks (base-8 digits) as the recursion choices.
    """
    x = 0
    y = 0
    p = 1
    for i in range(t):
        d = (k >> (3 * i)) & 7  # base-8 digit from 3 bits
        dx, dy = _POS8[d]
        x += dx * p
        y += dy * p
        p *= 3
    return x, y


def style_grid(ax, L: int) -> None:
    # Draw a light grid; useful for small L.
    for i in range(L + 1):
        ax.plot([-0.5, L - 0.5], [i - 0.5, i - 0.5], color="#ECEFF1", lw=0.6, zorder=0)
        ax.plot([i - 0.5, i - 0.5], [-0.5, L - 0.5], color="#ECEFF1", lw=0.6, zorder=0)
    ax.set_aspect("equal")
    ax.set_xlim(-0.6, L - 0.4)
    ax.set_ylim(-0.6, L - 0.4)
    ax.set_xticks([])
    ax.set_yticks([])


def main() -> None:
    out_dir: Path = figures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Choose m values that satisfy m=3t (exact bijection).
    ms: List[int] = [6, 9, 12]
    pairs = [(m, m // 3) for m in ms]

    nrows = len(pairs)
    fig, axes = plt.subplots(nrows=nrows, ncols=3, figsize=(16.5, 4.6 * nrows))
    if nrows == 1:
        axes = np.array([axes])  # type: ignore

    c_bg = "#B0BEC5"  # blue grey
    c_hi = "#D84315"  # deep orange
    c_text = "#263238"

    for r, (m, t) in enumerate(pairs):
        axA, axB, axT = axes[r]
        N = 1 << m
        if N != (1 << (3 * t)):
            raise AssertionError("This gallery assumes m=3t for exact bijection.")
        L = 3**t

        w0 = "0" * m
        ks = [k for k in range(N) if fm.foldm(k, m) == w0]
        if not ks:
            raise AssertionError(f"Empty preimage for w0 at m={m}.")

        # ---- A: 1D index axis ----
        axA.axis("off")
        axA.set_xlim(0, N - 1)
        axA.set_ylim(0, 1)
        axA.plot([0, N - 1], [0.5, 0.5], color="#90A4AE", lw=2.0)
        axA.scatter(ks, [0.5] * len(ks), s=55, c=c_hi, edgecolors="white", linewidths=0.7, zorder=3)
        for k in ks[:10]:
            axA.text(k, 0.62, str(k), ha="center", va="bottom", fontsize=8.5, color=c_hi)
        if len(ks) > 10:
            axA.text(0.98, 0.62, f"+{len(ks)-10} more", transform=axA.transAxes, ha="right", va="bottom", fontsize=9, color=c_hi)
        d_eff = float(np.log(8.0) / np.log(3.0))
        axA.text(
            0.0,
            0.92,
            f"(fractal screen)  m={m} (t={t})  |Ω_m|=2^{m}={N}\n"
            f"Sierpiński carpet: L=3^{t}={L}, |cells|=8^{t}={N}, d≈{d_eff:.3f}\n"
            "Select k with Fold_m(k)=w0",
            transform=axA.transAxes,
            ha="left",
            va="top",
            fontsize=10.5,
            color=c_text,
        )

        # ---- B: fractal screen ----
        style_grid(axB, L if L <= 27 else 0)  # do not draw grid lines for huge L
        # Background: all occupied cells (computed from all k) and the induced scan path (k -> k+1).
        coords = np.array([sierpinski_carpet_coord_from_k(k, t) for k in range(N)], dtype=float)
        coords_hi = np.array([sierpinski_carpet_coord_from_k(k, t) for k in ks], dtype=float)
        # Faint scan path induced by the fractal addressing (not the 2D Hilbert curve).
        segs = np.stack([coords[:-1], coords[1:]], axis=1)  # (N-1,2,2)
        tt = np.linspace(0.0, 1.0, len(segs))
        lc = LineCollection(segs, array=tt, cmap="viridis", linewidths=0.85, alpha=0.28, zorder=1)
        axB.add_collection(lc)

        # Occupied cells (very light) + highlighted sites.
        t_pts = np.linspace(0.0, 1.0, len(coords))
        axB.scatter(coords[:, 0], coords[:, 1], s=5 if L >= 81 else 8, c=t_pts, cmap="viridis", edgecolors="none", alpha=0.12, zorder=1.5)
        axB.scatter(coords[:, 0], coords[:, 1], s=8 if L >= 81 else 12, c=c_bg, edgecolors="none", alpha=0.14, zorder=2)
        axB.scatter(coords_hi[:, 0], coords_hi[:, 1], s=55, c=c_hi, edgecolors="#263238", linewidths=0.4, zorder=3)
        axB.set_aspect("equal")
        axB.set_xlim(-0.6, L - 0.4)
        axB.set_ylim(-0.6, L - 0.4)
        axB.set_xticks([])
        axB.set_yticks([])
        axB.set_title("B. Fractal screen (Sierpiński carpet)\n(faint scan path k→k+1 + highlighted sites)", fontsize=11, pad=8)

        # ---- C: table ----
        axT.axis("off")
        lines: List[str] = []
        lines.append(f"w0 = {w0}")
        lines.append(f"|preimage| = {len(ks)}")
        lines.append("")
        lines.append("k    bits_m(k)           screen(x,y)")
        lines.append("------------------------------------------")
        max_rows = 18
        for k in ks[:max_rows]:
            b = bits_m(k, m)
            x, y = sierpinski_carpet_coord_from_k(k, t)
            lines.append(f"{k:4d}  {b}   ({x:3d},{y:3d})")
        if len(ks) > max_rows:
            lines.append("...")
        axT.text(0.0, 0.98, "\n".join(lines), va="top", ha="left", family="monospace", fontsize=9.3, color=c_text)
        axT.text(0.0, 0.08, "Note: this is a fractal screen visualization choice\n(d = log8/log3), not the 2D Hilbert screen.", fontsize=10, color="#455A64")

    fig.suptitle("Non-integer effective dimension visualization via a fractal screen (Sierpiński carpet)", fontsize=14, y=0.995)
    out_png = out_dir / "fractal_screen_sierpinski_trace_gallery.png"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")


if __name__ == "__main__":
    main()

