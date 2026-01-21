# -*- coding: utf-8 -*-
"""
Figure: "all information on the boundary" as a holographic boundary-face screen (VFS).

For any (m,n), define:
  d_eff := m/n,
  D_face := ceil(d_eff),
  D_bulk := D_face + 1.

We map microstates k∈{0..2^m-1} bijectively to a D_face-dimensional dyadic screen of side 2^n
using the universal VFS convention, then embed that screen as a single boundary face of a
D_bulk-dimensional cube by fixing one extra coordinate (x0=0).

This makes the "boundary encoding" literal in the discrete visualization: every occupied
site satisfies x0=0, hence lies on the bulk boundary.

Output:
  - figures/universal_screen_vfs_holo_face_gallery.png
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
from screen_universal_vfs import bits_per_level, effective_dimension, embedding_dimension, vfs_holo_face_coord_from_k  # noqa: E402


def bits_m(k: int, m: int) -> str:
    return format(int(k), f"0{m}b")


def style_grid(ax, L: int) -> None:
    if L <= 64:
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

    # Same representative sweep as the universal (bulk) VFS gallery, but rendered as boundary-face.
    pairs: List[Tuple[int, int]] = [
        (6, 3),
        (7, 3),
        (10, 3),
        (11, 3),
    ]

    nrows = len(pairs)
    fig, axes = plt.subplots(nrows=nrows, ncols=3, figsize=(17.8, 4.8 * nrows))
    if nrows == 1:
        axes = np.array([axes])  # type: ignore

    c_hi = "#D84315"
    c_text = "#263238"
    c_bg = "#CFD8DC"

    for r, (m, n) in enumerate(pairs):
        axA, axB, axT = axes[r]
        N = 1 << m
        L = 1 << n

        d_eff = effective_dimension(m, n)
        D_face = embedding_dimension(m, n)
        D_bulk = D_face + 1
        g = bits_per_level(m, n, D=D_face)

        w0 = "0" * m
        ks = [k for k in range(N) if fm.foldm(k, m) == w0]
        if not ks:
            raise AssertionError(f"Empty preimage for w0 at m={m}.")

        coords = np.array([vfs_holo_face_coord_from_k(k, m, n, face_axis=0, face_side=0) for k in range(N)], dtype=float)  # (N,D_bulk)
        coords_hi = coords[np.array(ks, dtype=int), :]

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
        axA.text(
            0.0,
            0.92,
            f"(holo boundary-face VFS)  (m,n)=({m},{n})  N=2^{m}={N}\n"
            f"d_eff=m/n={d_eff:.3f},  D_face=ceil(d_eff)={D_face},  D_bulk=D_face+1={D_bulk}\n"
            f"g_i on face: {g}\n"
            "Select k with Fold_m(k)=w0",
            transform=axA.transAxes,
            ha="left",
            va="top",
            fontsize=10.5,
            color=c_text,
        )

        # ---- B: pairwise 2D projections (including the boundary axis x0) ----
        axB.axis("off")
        axB.set_xlim(0, 1)
        axB.set_ylim(0, 1)

        d_show = min(D_bulk, 4)
        if d_show == 1:
            projs = [(0, 0)]
        elif d_show == 2:
            projs = [(0, 1)]
        elif d_show == 3:
            projs = [(0, 1), (0, 2), (1, 2)]
        else:
            projs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]

        def _proj(outer_ax, x0, y0, w, h, a, b, title):
            iax = outer_ax.inset_axes([x0, y0, w, h])
            style_grid(iax, L)
            xy = coords[:, [a, b]]
            xy_hi = coords_hi[:, [a, b]]

            segs = np.stack([xy[:-1], xy[1:]], axis=1)
            t_segs = np.linspace(0.0, 1.0, len(segs))
            t_pts = np.linspace(0.0, 1.0, len(xy))

            iax.add_collection(LineCollection(segs, array=t_segs, cmap="viridis", linewidths=0.95, alpha=0.28, zorder=1))
            iax.scatter(xy[:, 0], xy[:, 1], s=6 if L >= 64 else 9, c=t_pts, cmap="viridis", alpha=0.12, edgecolors="none", zorder=1.5)
            iax.scatter(xy[:, 0], xy[:, 1], s=10 if L >= 64 else 12, c=c_bg, alpha=0.16, edgecolors="none", zorder=2)
            iax.scatter(xy_hi[:, 0], xy_hi[:, 1], s=55, c=c_hi, edgecolors="#263238", linewidths=0.4, zorder=3)
            iax.set_title(title, fontsize=10, pad=2)

        if len(projs) == 1:
            a, b = projs[0]
            _proj(axB, 0.04, 0.12, 0.92, 0.82, a, b, f"x{a}–x{b}")
        elif len(projs) == 3:
            (a0, b0), (a1, b1), (a2, b2) = projs
            _proj(axB, 0.02, 0.54, 0.31, 0.42, a0, b0, f"x{a0}–x{b0}")
            _proj(axB, 0.35, 0.54, 0.31, 0.42, a1, b1, f"x{a1}–x{b1}")
            _proj(axB, 0.68, 0.54, 0.31, 0.42, a2, b2, f"x{a2}–x{b2}")
            axB.text(
                0.02,
                0.48,
                "B. Pairwise 2D projections including the boundary axis x0\nAll occupied sites satisfy x0=0 (boundary face)",
                fontsize=11,
                color=c_text,
            )
        else:
            (a0, b0), (a1, b1), (a2, b2), (a3, b3), (a4, b4), (a5, b5) = projs
            _proj(axB, 0.02, 0.54, 0.31, 0.40, a0, b0, f"x{a0}–x{b0}")
            _proj(axB, 0.35, 0.54, 0.31, 0.40, a1, b1, f"x{a1}–x{b1}")
            _proj(axB, 0.68, 0.54, 0.31, 0.40, a2, b2, f"x{a2}–x{b2}")
            _proj(axB, 0.02, 0.08, 0.31, 0.40, a3, b3, f"x{a3}–x{b3}")
            _proj(axB, 0.35, 0.08, 0.31, 0.40, a4, b4, f"x{a4}–x{b4}")
            _proj(axB, 0.68, 0.08, 0.31, 0.40, a5, b5, f"x{a5}–x{b5}")
            axB.text(
                0.02,
                0.01,
                "B. Pairwise 2D projections among the first 4 axes\nAll occupied sites satisfy x0=0 (boundary face)",
                fontsize=11,
                color=c_text,
            )

        # ---- C: table ----
        axT.axis("off")
        lines: List[str] = []
        lines.append(f"w0 = {w0}")
        lines.append(f"|preimage| = {len(ks)}")
        lines.append(f"D_face = {D_face},  D_bulk = {D_bulk},  n = {n},  d_eff = m/n = {d_eff:.3f}")
        lines.append("")
        lines.append("k    bits_m(k)           bulk coord (x0,...,x_{D_bulk-1})")
        lines.append("----------------------------------------------------------")
        max_rows = 14
        for k in ks[:max_rows]:
            b = bits_m(k, m)
            c = vfs_holo_face_coord_from_k(k, m, n, face_axis=0, face_side=0)
            lines.append(f"{k:4d}  {b}   {tuple(int(x) for x in c)}")
        if len(ks) > max_rows:
            lines.append("...")
        axT.text(0.0, 0.98, "\n".join(lines), va="top", ha="left", family="monospace", fontsize=9.1, color=c_text)
        axT.text(
            0.0,
            0.08,
            "Interpretation: bulk is D_bulk-dim, but all points lie on the boundary face x0=0.\n"
            "This makes the boundary encoding explicit at finite resolution.",
            fontsize=10,
            color="#455A64",
        )

    fig.suptitle("Holographic boundary-face screen for arbitrary (m,n) via VFS (all points satisfy x0=0)", fontsize=14, y=0.995)
    out_png = out_dir / "universal_screen_vfs_holo_face_gallery.png"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")


if __name__ == "__main__":
    main()

