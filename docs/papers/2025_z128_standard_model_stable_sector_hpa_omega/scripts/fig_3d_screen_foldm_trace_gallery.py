# -*- coding: utf-8 -*-
"""
Figure: trace gallery on a 3D screen for non-(m=2n) cases by choosing d=3 so that m=3n.

Key idea (option C):
  Use a 3D addressing screen with 2^n × 2^n × 2^n sites so that
    |screen| = 2^{3n} = 2^m  <=>  m = 3n,
  giving a bijection k <-> (x,y,z) without additional many-to-one conventions.

Addressing used here:
  We use a deterministic 3D locality-preserving space-filling addressing based on
  bit interleaving (Morton/Z-order). This is a "Hilbert-type" 3D addressing in the
  sense of being a fixed explicit space-filling order, but it is not the classical
  3D Hilbert curve recursion. It is used purely for visualization.

Per row (m,n) with m=3n we trace one representative stable type w0=0...0:
  (A) scan-index axis highlighting k with Fold_m(k)=w0
  (B) three orthogonal projections (xy/xz/yz) showing where those k land on the 3D screen
  (C) a small table listing (k, bits_m(k), (x,y,z))

Output:
  - figures/screen3d_foldm_trace_gallery.png
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


def morton3_decode(k: int, n: int) -> Tuple[int, int, int]:
    """
    Decode interleaved bits into (x,y,z) where each has n bits.

    We take the bitstream of k as groups of 3 bits:
      ... x_{i} y_{i} z_{i} ... x_0 y_0 z_0
    """
    x = y = z = 0
    for i in range(n):
        # Take 3 bits at positions 3*i,3*i+1,3*i+2 (LSB-first grouping).
        xb = (k >> (3 * i + 0)) & 1
        yb = (k >> (3 * i + 1)) & 1
        zb = (k >> (3 * i + 2)) & 1
        x |= xb << i
        y |= yb << i
        z |= zb << i
    return x, y, z


def main() -> None:
    out_dir: Path = figures_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 3D balanced pairs: m = 3n.
    pairs: List[Tuple[int, int]] = [(6, 2), (9, 3)]

    nrows = len(pairs)
    fig, axes = plt.subplots(nrows=nrows, ncols=3, figsize=(16.0, 5.1 * nrows))
    if nrows == 1:
        axes = np.array([axes])  # type: ignore

    c_bg = "#CFD8DC"
    c_hi = "#D84315"
    c_grid = "#ECEFF1"
    c_text = "#263238"

    for r, (m, n) in enumerate(pairs):
        axA, axB, axT = axes[r]
        if m != 3 * n:
            raise AssertionError("This gallery assumes m=3n.")

        N = 1 << m
        L = 1 << n
        w0 = "0" * m
        ks = [k for k in range(N) if fm.foldm(k, m) == w0]
        if not ks:
            raise AssertionError(f"Empty preimage for w0 at m={m}.")

        # ---- A: 1D index axis ----
        axA.axis("off")
        axA.set_xlim(0, N - 1)
        axA.set_ylim(0, 1)
        axA.plot([0, N - 1], [0.5, 0.5], color="#90A4AE", lw=2.0)
        axA.scatter(ks, [0.5] * len(ks), s=60, c=c_hi, edgecolors="white", linewidths=0.7, zorder=3)
        for k in ks[:10]:
            axA.text(k, 0.62, str(k), ha="center", va="bottom", fontsize=8.5, color=c_hi)
        if len(ks) > 10:
            axA.text(0.98, 0.62, f"+{len(ks)-10} more", transform=axA.transAxes, ha="right", va="bottom", fontsize=9, color=c_hi)
        axA.text(0.0, 0.92, f"(d=3)  (m,n)=({m},{n})  screen=({L}×{L}×{L})\nSelect k with Fold_m(k)=w0", transform=axA.transAxes, ha="left", va="top", fontsize=11, color=c_text)

        # ---- B: 3 orthogonal projections ----
        axB.axis("off")
        axB.set_xlim(0, 1)
        axB.set_ylim(0, 1)

        # Precompute all coordinates (for background density) only for small N.
        # For m=9, N=512 is fine.
        coords = np.array([morton3_decode(k, n) for k in range(N)], dtype=float)
        coords_hi = np.array([morton3_decode(k, n) for k in ks], dtype=float)

        def _proj(ax, x0, y0, w, h, u, v, title):
            # draw mini-axes as inset within axB
            iax = ax.inset_axes([x0, y0, w, h])
            for i in range(L + 1):
                iax.plot([-0.5, L - 0.5], [i - 0.5, i - 0.5], color=c_grid, lw=0.6, zorder=0)
                iax.plot([i - 0.5, i - 0.5], [-0.5, L - 0.5], color=c_grid, lw=0.6, zorder=0)
            # Faint scan-order polyline: connect k -> k+1 on this 3D screen projection.
            segs = np.stack([coords[:-1, [u, v]], coords[1:, [u, v]]], axis=1)
            t = np.linspace(0.0, 1.0, len(segs))
            iax.add_collection(LineCollection(segs, array=t, cmap="viridis", linewidths=0.95, alpha=0.28, zorder=1))

            t_pts = np.linspace(0.0, 1.0, len(coords))
            iax.scatter(coords[:, u], coords[:, v], s=6, c=t_pts, cmap="viridis", edgecolors="none", alpha=0.14, zorder=1.5)
            iax.scatter(coords[:, u], coords[:, v], s=10, c=c_bg, edgecolors="none", alpha=0.30, zorder=2)
            iax.scatter(coords_hi[:, u], coords_hi[:, v], s=45, c=c_hi, edgecolors="#263238", linewidths=0.4, zorder=3)
            iax.set_aspect("equal")
            iax.set_xlim(-0.6, L - 0.4)
            iax.set_ylim(-0.6, L - 0.4)
            iax.set_xticks([])
            iax.set_yticks([])
            iax.set_title(title, fontsize=10, pad=2)

        _proj(axB, 0.02, 0.54, 0.31, 0.42, 0, 1, "xy")
        _proj(axB, 0.35, 0.54, 0.31, 0.42, 0, 2, "xz")
        _proj(axB, 0.68, 0.54, 0.31, 0.42, 1, 2, "yz")
        axB.text(0.02, 0.48, "B. 3D screen projections (Morton/Z-order addressing)\nHighlighted points correspond to the same selected k", fontsize=11, color=c_text)

        # ---- C: table ----
        axT.axis("off")
        lines: List[str] = []
        lines.append(f"w0 = {w0}")
        lines.append(f"|preimage| = {len(ks)}")
        lines.append("")
        lines.append("k    bits_m(k)           (x,y,z)")
        lines.append("--------------------------------------")
        max_rows = 18
        for k in ks[:max_rows]:
            b = bits_m(k, m)
            x, y, z = morton3_decode(k, n)
            lines.append(f"{k:4d}  {b}   ({x:2d},{y:2d},{z:2d})")
        if len(ks) > max_rows:
            lines.append("...")
        axT.text(0.0, 0.98, "\n".join(lines), va="top", ha="left", family="monospace", fontsize=9.5, color=c_text)
        axT.text(0.0, 0.08, "Note: this is a visualization addressing choice\nfor d=3 (m=3n), not the 2D Hilbert screen.", fontsize=10, color="#455A64")

    fig.suptitle("Non-(m=2n) visualization via a 3D screen (choose d=3 so m=3n)", fontsize=14, y=0.995)
    out_png = out_dir / "screen3d_foldm_trace_gallery.png"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")


if __name__ == "__main__":
    main()

