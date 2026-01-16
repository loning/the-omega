# -*- coding: utf-8 -*-
"""
Figure: internal-dimension "fractal unfolding" on the 2D Hilbert screen.

Narrative goal:
  Visualize the idea that a fixed spatial point on the Hilbert screen carries a
  resolution-dependent internal structure: the base X6 label (18⊕3 interface)
  plus increasingly many suffix-bit channels under uplift in m.

We compare three balanced 2D instances (m=2n):
  - (m,n)=(6,3): anchor, only the base label u=w[:6] is available.
  - (m,n)=(10,5): first audited uplift; suffix bits w[7..10] form 4 channels.
  - (m,n)=(14,7): deeper uplift; suffix bits w[7..14] form 8 channels.

We render:
  - base scalar q0(x): normalized Hamming weight |u|_1 / 3 on the screen (exists at all m),
  - uplift scalar q1(x): normalized suffix weight |w_{7..m}|_1 / (m-6) (new internal channels),
  - a zoom-in of a deterministically selected macro-block (4×4 block quotient),
    together with a bar-glyph showing block-averaged suffix channels.

Outputs:
  - figures/adaptive/lattice_qft_bridge/internal_dimension_fractal_unfolding_2d.png
  - figures/adaptive/lattice_qft_bridge/data/internal_dimension_fractal_unfolding_2d.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402

import exp_foldm_stats as foldm  # noqa: E402
import exp_hilbert_chirality_index as hil  # noqa: E402
from common_paths import figures_dir  # noqa: E402


Point2 = Tuple[int, int]


def _hamming01(s: str) -> int:
    return sum(1 for ch in s if ch == "1")


def _grid(side: int, fill: float = 0.0) -> List[List[float]]:
    return [[float(fill) for _ in range(side)] for _ in range(side)]


def _block_mean(grid: List[List[float]], block: int) -> List[List[float]]:
    side = len(grid)
    if side == 0 or any(len(r) != side for r in grid):
        raise ValueError("grid must be non-empty square")
    if block <= 0 or (side % block) != 0:
        raise ValueError("block must be positive and divide side")
    out_side = side // block
    out: List[List[float]] = [[0.0 for _ in range(out_side)] for _ in range(out_side)]
    for by in range(out_side):
        for bx in range(out_side):
            s = 0.0
            for dy in range(block):
                for dx in range(block):
                    s += float(grid[by * block + dy][bx * block + dx])
            out[by][bx] = s / float(block * block)
    return out


def _select_block(score: List[List[float]]) -> Tuple[int, int]:
    """
    Deterministically select a (by,bx) from a 4x4 score grid.
    Tie-break: larger score, then smaller by, then smaller bx.
    """
    best = (-1.0, 0, 0)
    for by in range(4):
        for bx in range(4):
            v = float(score[by][bx])
            cand = (v, -by, -bx)
            if cand > (best[0], -best[1], -best[2]):
                best = (v, by, bx)
    return best[1], best[2]


@dataclass(frozen=True)
class Instance2D:
    m: int
    n: int
    side: int
    block: int  # macro block size in pixels, so macro grid is 4x4
    q0: List[List[float]]  # base scalar
    q1: List[List[float]]  # uplift scalar (0 for m=6)
    suffix_channels: List[List[List[float]]]  # raw per-site suffix bit channels (length m-6, possibly 0)


def _build_instance(m: int) -> Instance2D:
    if m % 2 != 0:
        raise ValueError("This figure assumes balanced 2D coupling m=2n.")
    n = m // 2
    side = 1 << n
    N = 1 << m
    if side * side != N:
        raise AssertionError("Expected balanced embedding N=4^n=2^m.")
    if n < 3:
        raise ValueError("Need n>=3 for the 4x4 macro block quotient.")
    block = 1 << (n - 2)  # always yields a 4x4 macro grid

    path: List[Point2] = hil.hilbert_curve(n)
    outs = foldm.cached_foldm_outputs(m)
    if len(path) != N or len(outs) != N:
        raise AssertionError("Unexpected length mismatch for Hilbert path / Foldm outputs.")

    q0 = _grid(side)
    q1 = _grid(side)
    k_suf = max(0, m - 6)
    suffix_channels: List[List[List[float]]] = [_grid(side) for _ in range(k_suf)]

    for k, (x, y) in enumerate(path):
        w = outs[k]
        u = w[:6]
        q0[y][x] = float(_hamming01(u)) / 3.0  # X6 max weight is 3
        if k_suf > 0:
            suf = w[6:]
            q1[y][x] = float(_hamming01(suf)) / float(k_suf)
            for j in range(k_suf):
                suffix_channels[j][y][x] = float(1.0 if suf[j] == "1" else 0.0)
        else:
            q1[y][x] = 0.0

    return Instance2D(m=m, n=n, side=side, block=block, q0=q0, q1=q1, suffix_channels=suffix_channels)


def _imshow(ax, arr: np.ndarray, title: str, vmin: float = 0.0, vmax: float = 1.0) -> None:
    im = ax.imshow(arr, origin="lower", cmap="viridis", vmin=vmin, vmax=vmax, interpolation="nearest")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, fontsize=10, pad=4)
    return im


def main() -> None:
    out_root: Path = figures_dir() / "adaptive" / "lattice_qft_bridge"
    out_data: Path = out_root / "data"
    out_root.mkdir(parents=True, exist_ok=True)
    out_data.mkdir(parents=True, exist_ok=True)

    ms = [6, 10, 14]
    inst = {m: _build_instance(m) for m in ms}

    # Select a macro-block (4x4) using the deepest uplift's block-mean uplift scalar.
    deep = inst[14]
    q1_macro = _block_mean(deep.q1, deep.block)
    by_sel, bx_sel = _select_block(q1_macro)

    # Figure layout: 3 columns (m), 3 rows (q0 full, q1 full, zoom+glyph).
    fig = plt.figure(figsize=(16.8, 9.2))
    gs = fig.add_gridspec(nrows=3, ncols=3, height_ratios=[1.0, 1.0, 1.15], hspace=0.24, wspace=0.10)

    payload: Dict[str, object] = {
        "selected_block": {"by": by_sel, "bx": bx_sel},
        "instances": {},
    }

    for ci, m in enumerate(ms):
        it = inst[m]
        side = it.side
        block = it.block
        y0 = by_sel * block
        x0 = bx_sel * block

        # --- Row 1: base scalar ---
        ax0 = fig.add_subplot(gs[0, ci])
        im0 = _imshow(ax0, np.array(it.q0), title=f"(m,n)=({m},{it.n})  base scalar q0=|u|1/3")
        fig.colorbar(im0, ax=ax0, fraction=0.046, pad=0.02)

        # --- Row 2: uplift scalar ---
        ax1 = fig.add_subplot(gs[1, ci])
        im1 = _imshow(ax1, np.array(it.q1), title=f"uplift scalar q1=|suffix|1/(m-6)  (dim={max(0,m-6)})")
        fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.02)

        # Overlay selected macro-block rectangle for orientation.
        for ax in (ax0, ax1):
            ax.add_patch(
                plt.Rectangle((x0 - 0.5, y0 - 0.5), block, block, fill=False, lw=2.0, ec="#D84315")
            )

        # --- Row 3: zoom + suffix glyph ---
        sub = gs[2, ci].subgridspec(nrows=1, ncols=2, width_ratios=[1.1, 0.9], wspace=0.20)
        axZ = fig.add_subplot(sub[0, 0])
        zoom = np.array([row[x0 : x0 + block] for row in it.q1[y0 : y0 + block]])
        _imshow(axZ, zoom, title=f"zoom-in: selected macro-block (4×4 quotient)  block={block}")

        axG = fig.add_subplot(sub[0, 1])
        axG.set_title("block-avg suffix channels", fontsize=10, pad=4)
        axG.set_ylim(0.0, 1.0)
        axG.set_xlim(-0.5, max(0, len(it.suffix_channels)) - 0.5 if it.suffix_channels else 3.5)
        axG.set_yticks([0.0, 0.5, 1.0])
        axG.grid(True, axis="y", color="#ECEFF1", lw=0.8)

        # Compute block-averaged suffix channels.
        ch_means: List[float] = []
        for ch in it.suffix_channels:
            s = 0.0
            for yy in range(y0, y0 + block):
                for xx in range(x0, x0 + block):
                    s += float(ch[yy][xx])
            ch_means.append(s / float(block * block))

        if not ch_means:
            # At m=6 there is no suffix; show a deterministic placeholder bar group.
            xs = [0, 1, 2, 3]
            ys = [0.0, 0.0, 0.0, 0.0]
            axG.bar(xs, ys, color="#90A4AE")
            axG.set_xticks(xs)
            axG.set_xticklabels(["-", "-", "-", "-"])
        else:
            xs = list(range(len(ch_means)))
            axG.bar(xs, ch_means, color="#1976D2" if m == 10 else "#2E7D32")
            if len(xs) <= 12:
                axG.set_xticks(xs)
                axG.set_xticklabels([f"s{7+i}" for i in range(len(xs))], rotation=0, fontsize=8)
            else:
                axG.set_xticks([])

        axG.text(
            0.02,
            0.95,
            f"selected block (by,bx)=({by_sel},{bx_sel})\n"
            f"mean q0={np.mean(np.array([row[x0:x0+block] for row in it.q0[y0:y0+block]])):.3f}\n"
            f"mean q1={np.mean(zoom):.3f}",
            transform=axG.transAxes,
            ha="left",
            va="top",
            fontsize=9,
            family="monospace",
            color="#263238",
        )

        payload["instances"][str(m)] = {
            "m": m,
            "n": it.n,
            "side": side,
            "macro_block": block,
            "selected_block": {"by": by_sel, "bx": bx_sel, "x0": x0, "y0": y0},
            "suffix_dim": max(0, m - 6),
            "selected_block_suffix_means": ch_means,
        }

    fig.suptitle(
        "Internal-dimension unfolding on the Hilbert screen (no extra spatial axes): base label + uplift suffix channels",
        fontsize=14,
        y=0.995,
    )
    out_png = out_root / "internal_dimension_fractal_unfolding_2d.png"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")

    out_json = out_data / "internal_dimension_fractal_unfolding_2d.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()

