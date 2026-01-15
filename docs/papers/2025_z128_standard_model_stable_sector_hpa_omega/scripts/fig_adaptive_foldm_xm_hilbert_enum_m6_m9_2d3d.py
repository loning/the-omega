# -*- coding: utf-8 -*-
"""
Adaptive-style multi-page enumeration of X_m panels (Hilbert only), for m=6..10.

User intent
-----------
- Place outputs under figures/adaptive (like other adaptive suites).
- Enumerate *all* stable types w ∈ X_m (panel per w), like foldm_xm_types_hilbert_panels_*.
- Generate BOTH 2D and 3D Hilbert-only visualizations, with deterministic n choices.
- No external parameters: one run writes a fixed set of files.

Deterministic protocol choices
------------------------------
For each m ∈ {6,7,8,9,10}:
  - 2D screen: Hilbert order n2 = ceil(m/2)
  - 3D screen: Hilbert order n3 = ceil(m/3)

We embed only the first N=2^m indices as a prefix of the finite Hilbert scan:
  - 2D uses exp_hilbert_chirality_index.hilbert_curve(n2) (length 4^{n2})
  - 3D uses hilbert_nd.hilbert_index_to_coords(k, p=n3, n=3) (length 2^{3 n3})
Requirement N ≤ screen_size is enforced by construction for these n choices.

Outputs (fixed names)
---------------------
Under figures/adaptive/hilbert_enum/:
  - foldm_xm_types_hilbert_2d_m{m}_p{01..}.png
  - foldm_xm_types_hilbert_3d_m{m}_p{01..}.png
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Line3DCollection  # noqa: E402

import exp_foldm_stats as foldm  # noqa: E402
import exp_hilbert_chirality_index as hil2  # noqa: E402
import exp_xm_enumeration as xm  # noqa: E402
from common_paths import figures_dir  # noqa: E402
from hilbert_nd import hilbert_index_to_coords  # noqa: E402


Coord2 = Tuple[int, int]


def _ceil_div(a: int, b: int) -> int:
    return int((int(a) + int(b) - 1) // int(b))


def _fib_weights(L: int) -> List[int]:
    # Weights [F2, F3, ..., F_{L+1}] with F1=F2=1.
    if L < 0:
        raise ValueError("L must be nonnegative.")
    if L == 0:
        return []
    if L == 1:
        return [1]
    w = [1, 2]
    while len(w) < L:
        w.append(w[-1] + w[-2])
    return w


def _zeckendorf_value_word(word: str) -> int:
    wts = _fib_weights(len(word))
    return sum(int(bit) * wts[i] for i, bit in enumerate(word))


def _palette_hex(K: int) -> List[str]:
    cmap = plt.get_cmap("turbo")
    if K <= 1:
        rgba = cmap(0.5)
        return ["#%02X%02X%02X" % (int(round(255 * rgba[0])), int(round(255 * rgba[1])), int(round(255 * rgba[2])))]
    out: List[str] = []
    for i in range(K):
        t = float(i) / float(K - 1)
        rgba = cmap(t)
        out.append("#%02X%02X%02X" % (int(round(255 * rgba[0])), int(round(255 * rgba[1])), int(round(255 * rgba[2]))))
    return out


def _style_grid_2d(ax, L: int) -> None:
    ax.set_aspect("equal")
    ax.set_xlim(-0.6, L - 0.4)
    ax.set_ylim(-0.6, L - 0.4)
    ax.set_xticks([])
    ax.set_yticks([])
    if L <= 16:
        ax.set_xticks(np.arange(-0.5, L, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, L, 1), minor=True)
        ax.grid(which="minor", color="#E0E0E0", linewidth=0.50)
    else:
        ax.set_xticks(np.arange(-0.5, L, 2), minor=True)
        ax.set_yticks(np.arange(-0.5, L, 2), minor=True)
        ax.grid(which="minor", color="#ECEFF1", linewidth=0.35)


def _style_3d(ax3, L: int, elev: float = 22.0, azim: float = -55.0) -> None:
    ax3.set_xticks([])
    ax3.set_yticks([])
    ax3.set_zticks([])
    ax3.set_xlim(-0.6, L - 0.4)
    ax3.set_ylim(-0.6, L - 0.4)
    ax3.set_zlim(-0.6, L - 0.4)
    ax3.view_init(elev=float(elev), azim=float(azim))
    ax3.set_box_aspect((1, 1, 1))
    ax3.grid(False)
    for axis in (ax3.xaxis, ax3.yaxis, ax3.zaxis):
        axis.pane.set_edgecolor("0.92")
        axis.pane.set_facecolor((1.0, 1.0, 1.0, 0.0))


def _decimate(segs: np.ndarray, max_keep: int) -> np.ndarray:
    """
    NOTE: For Hilbert curves, dropping segments breaks connectivity.
    Keep this utility for non-polyline uses; do NOT use it for Hilbert polylines.
    """
    if len(segs) <= max_keep:
        return segs
    stride = int(np.ceil(float(len(segs)) / float(max_keep)))
    return segs[::stride]


def _labels_on_hilbert_2d_prefix(*, m_bits: int, n_bits: int) -> Dict[Coord2, str]:
    N = 1 << int(m_bits)
    path = hil2.hilbert_curve(int(n_bits))  # full length 4^n
    if N > len(path):
        raise ValueError(f"Need 2^m <= 4^n. Got 2^{m_bits}={N} > 4^{n_bits}={len(path)}.")
    out: Dict[Coord2, str] = {}
    for k, (x, y) in enumerate(path[:N]):
        out[(int(x), int(y))] = foldm.foldm(k, int(m_bits))
    return out


def _grid_mask_for_word_2d(labels: Dict[Coord2, str], w: str, n_bits: int) -> np.ndarray:
    L = 1 << int(n_bits)
    m = np.zeros((L, L), dtype=int)
    for (x, y), ww in labels.items():
        if ww == w:
            m[y, x] = 1
    return m


def _coords_3d_prefix(*, m_bits: int, n_bits: int) -> np.ndarray:
    N = 1 << int(m_bits)
    cap = 1 << (3 * int(n_bits))
    if N > cap:
        raise ValueError(f"Need 2^m <= 2^{{3n}}. Got 2^{m_bits}={N} > 2^{{3*{n_bits}}}={cap}.")
    return np.array([hilbert_index_to_coords(k, p=int(n_bits), n=3) for k in range(N)], dtype=float)


def _render_2d_pages(*, m_bits: int, n_bits: int, out_dir: Path, rows_per_page: int = 4, cols: int = 6) -> None:
    labels = _labels_on_hilbert_2d_prefix(m_bits=m_bits, n_bits=n_bits)
    Xm = xm.all_xm(int(m_bits))
    Xm_sorted = sorted(Xm, key=lambda w: (_zeckendorf_value_word(w), w))
    K = len(Xm_sorted)
    palette = _palette_hex(K)

    N = 1 << int(m_bits)
    L = 1 << int(n_bits)

    # Hilbert prefix path overlay
    path = hil2.hilbert_curve(int(n_bits))[:N]
    pts = np.array(path, dtype=float)
    segs = np.stack([pts[:-1], pts[1:]], axis=1)
    t_segs = np.linspace(0.0, 1.0, len(segs))
    alpha_line = 0.22 if N <= 128 else 0.12
    lw_line = 1.05 if N <= 128 else 0.70

    per_page = int(rows_per_page) * int(cols)
    pages = (K + per_page - 1) // per_page

    for pi in range(pages):
        chunk = Xm_sorted[pi * per_page : (pi + 1) * per_page]
        nrows = int(rows_per_page)
        ncols = int(cols)
        fig = plt.figure(figsize=(19.2, 10.4))
        axes = fig.subplots(nrows=nrows, ncols=ncols)
        if nrows == 1:
            axes = np.array([axes])

        for j in range(nrows * ncols):
            r = j // ncols
            c = j % ncols
            axes[r][c].axis("off")

        title_fs = 7.0 if L <= 16 else 6.4
        for j, w in enumerate(chunk):
            r = j // ncols
            c = j % ncols
            ax = axes[r][c]
            ax.axis("on")
            _style_grid_2d(ax, L)

            mask = _grid_mask_for_word_2d(labels, w, n_bits=n_bits)
            g = int(mask.sum())
            tag = "bdry" if xm.is_boundary_word(w) else "cyc"

            idx = pi * per_page + j
            cmap = ListedColormap(["#FFFFFF", palette[idx]])
            ax.imshow(mask, cmap=cmap, vmin=0, vmax=1, interpolation="nearest", origin="lower", zorder=0)

            lc = LineCollection(segs, array=t_segs, cmap="viridis", linewidths=lw_line, alpha=alpha_line)
            lc.set_zorder(1)
            ax.add_collection(lc)

            ax.set_title(f"{w}  ({tag})  g={g}", fontsize=title_fs, pad=1.5, color="#263238")

        fig.suptitle(
            f"Hilbert-only enumeration (2D): (m,n)=({m_bits},{n_bits})  N=2^{m_bits}={N}  |X_m|={K}  (page {pi+1}/{pages})",
            fontsize=12.5,
            y=0.995,
        )
        out_png = out_dir / f"foldm_xm_types_hilbert_2d_m{m_bits}_p{pi+1:02d}.png"
        fig.savefig(out_png, dpi=240, bbox_inches="tight")
        plt.close(fig)
        print(f"Wrote {out_png}")


def _render_3d_pages(*, m_bits: int, n_bits: int, out_dir: Path, rows_per_page: int = 3, cols: int = 3) -> None:
    Xm = xm.all_xm(int(m_bits))
    Xm_sorted = sorted(Xm, key=lambda w: (_zeckendorf_value_word(w), w))
    K = len(Xm_sorted)
    palette = _palette_hex(K)

    N = 1 << int(m_bits)
    L = 1 << int(n_bits)

    coords = _coords_3d_prefix(m_bits=m_bits, n_bits=n_bits)  # (N,3)
    segs3 = np.stack([coords[:-1], coords[1:]], axis=1)  # (N-1,2,3)
    # IMPORTANT: do NOT decimate Hilbert segments, otherwise the polyline becomes disconnected.
    t3 = np.linspace(0.0, 1.0, len(segs3))
    lw = 0.55 if N >= 256 else 0.75
    alpha = 0.16 if N >= 256 else 0.20

    # Precompute indices per word (deterministic).
    outs = [foldm.foldm(k, int(m_bits)) for k in range(N)]
    idx_map: Dict[str, List[int]] = {w: [] for w in Xm_sorted}
    for k, w in enumerate(outs):
        idx_map[w].append(int(k))

    per_page = int(rows_per_page) * int(cols)
    pages = (K + per_page - 1) // per_page

    for pi in range(pages):
        chunk = Xm_sorted[pi * per_page : (pi + 1) * per_page]
        nrows = int(rows_per_page)
        ncols = int(cols)
        fig = plt.figure(figsize=(18.8, 11.2))

        for j, w in enumerate(chunk):
            r = j // ncols
            c = j % ncols
            ax3 = fig.add_subplot(nrows, ncols, j + 1, projection="3d")
            _style_3d(ax3, L, elev=22.0, azim=-55.0)

            idx = pi * per_page + j
            col = palette[idx]

            # Hilbert path (same for all panels): keep connectivity (no segment dropping).
            lc = Line3DCollection(segs3, array=t3, cmap="viridis", linewidths=lw, alpha=alpha)
            ax3.add_collection3d(lc)

            # Highlight this word's points.
            ks = idx_map[w]
            pts = coords[np.array(ks, dtype=int), :]
            ax3.scatter(pts[:, 0], pts[:, 1], pts[:, 2], s=18, c=col, depthshade=False, edgecolors="white", linewidths=0.3, alpha=0.92)
            tag = "bdry" if xm.is_boundary_word(w) else "cyc"
            ax3.set_title(f"{w} ({tag})  g={len(ks)}", fontsize=8.2, pad=1)

        fig.suptitle(
            f"Hilbert-only enumeration (3D): (m,n)=({m_bits},{n_bits})  N=2^{m_bits}={N}  |X_m|={K}  (page {pi+1}/{pages})",
            fontsize=12.5,
            y=0.99,
        )
        out_png = out_dir / f"foldm_xm_types_hilbert_3d_m{m_bits}_p{pi+1:02d}.png"
        fig.savefig(out_png, dpi=240, bbox_inches="tight")
        plt.close(fig)
        print(f"Wrote {out_png}")


def main() -> None:
    base = figures_dir() / "adaptive" / "hilbert_enum"
    base.mkdir(parents=True, exist_ok=True)

    for m in (6, 7, 8, 9, 10):
        n2 = _ceil_div(m, 2)
        n3 = _ceil_div(m, 3)
        _render_2d_pages(m_bits=m, n_bits=n2, out_dir=base, rows_per_page=4, cols=6)
        _render_3d_pages(m_bits=m, n_bits=n3, out_dir=base, rows_per_page=3, cols=3)


if __name__ == "__main__":
    main()

