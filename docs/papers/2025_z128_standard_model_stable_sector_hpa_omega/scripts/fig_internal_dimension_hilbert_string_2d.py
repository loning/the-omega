# -*- coding: utf-8 -*-
"""
Figure: a single Hilbert "string" carrying both field value and intrinsic dimension.

User-facing intent:
  Provide a more intuitive visualization than multi-projection galleries:
  one space-filling curve (2D Hilbert) strings the whole screen, and we encode
    - field value as color along the curve,
    - local intrinsic dimension (internal fiber complexity) as line width.

Construction (balanced 2D screen):
  - Choose (m,n)=(14,7) so N=2^m=4^n=16384 on a 128×128 Hilbert screen.
  - For each k, let w = Fold_m(k), u=w[:6], suffix=w[6:].
  - Define a scalar field value along the string:
      q1(k) := |suffix|_1 / (m-6)   in [0,1].
  - Estimate a local intrinsic dimension on a *macro block* (coarse spatial bins):
      In each block, collect suffix-bit vectors s(k) ∈ {0,1}^{m-6},
      compute covariance C, and define participation-ratio dimension
        d_eff := (tr C)^2 / tr(C^2)  in [0, m-6].
    Each k inherits the d_eff of its containing block.

Rendering:
  - Draw the Hilbert polyline segments (k→k+1) as a single LineCollection.
  - Segment color = q1(k), segment linewidth = mapped d_eff(block).
  - A small side panel shows the 4×4 macro-block map of d_eff for orientation.

Outputs:
  - figures/adaptive/lattice_qft_bridge/internal_dimension_hilbert_string_2d.png
  - figures/adaptive/lattice_qft_bridge/data/internal_dimension_hilbert_string_2d.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

import exp_foldm_stats as foldm  # noqa: E402
import exp_hilbert_chirality_index as hil  # noqa: E402
from common_paths import figures_dir  # noqa: E402


Point2 = Tuple[int, int]


def _hamming01(s: str) -> int:
    return sum(1 for ch in s if ch == "1")


def _participation_ratio_dimension(C: np.ndarray) -> float:
    # d_eff = (tr C)^2 / tr(C^2), with safe guards.
    tr = float(np.trace(C))
    tr2 = float(np.sum(C * C))
    if tr2 <= 0.0:
        return 0.0
    return (tr * tr) / tr2


def main() -> None:
    out_root: Path = figures_dir() / "adaptive" / "lattice_qft_bridge"
    out_data: Path = out_root / "data"
    out_root.mkdir(parents=True, exist_ok=True)
    out_data.mkdir(parents=True, exist_ok=True)

    m = 14
    n = 7
    side = 1 << n
    N = 1 << m
    if side * side != N:
        raise AssertionError("Expected balanced 2D embedding with N=4^n=2^m.")

    # Coarse spatial bin size for local dimension estimate.
    # Use 16×16 bins for a stable estimate: 8×8 pixels per bin on the 128×128 screen.
    block = 8
    if (side % block) != 0:
        raise AssertionError("block must divide side.")
    out_side = side // block

    path: List[Point2] = hil.hilbert_curve(n)
    outs = foldm.cached_foldm_outputs(m)
    if len(path) != N or len(outs) != N:
        raise AssertionError("Unexpected length mismatch.")

    k_suf = m - 6  # suffix dim

    # Arrays aligned with k.
    coords = np.array(path, dtype=float)  # (N,2) in (x,y)
    q1 = np.zeros((N,), dtype=float)
    bid = np.zeros((N,), dtype=int)
    suf_bits = np.zeros((N, k_suf), dtype=float)

    for k, (x, y) in enumerate(path):
        w = outs[k]
        suf = w[6:]
        ones = _hamming01(suf)
        q1[k] = float(ones) / float(k_suf)
        for j in range(k_suf):
            suf_bits[k, j] = 1.0 if suf[j] == "1" else 0.0
        bx = int(x) // block
        by = int(y) // block
        bid[k] = int(by * out_side + bx)

    # Compute d_eff per block.
    d_eff_block = np.zeros((out_side * out_side,), dtype=float)
    for b in range(out_side * out_side):
        idx = np.where(bid == b)[0]
        if idx.size <= 1:
            d_eff_block[b] = 0.0
            continue
        X = suf_bits[idx, :]  # (M,k_suf)
        # Centered covariance (population).
        Xc = X - np.mean(X, axis=0, keepdims=True)
        C = (Xc.T @ Xc) / float(Xc.shape[0])
        d = _participation_ratio_dimension(C)
        # Clamp to [0,k_suf] for safety.
        d_eff_block[b] = float(max(0.0, min(float(k_suf), d)))

    # Map per-k dimension and to linewidth.
    d_eff_k = d_eff_block[bid]
    w_min, w_max = 0.35, 3.2
    lw = w_min + (w_max - w_min) * (d_eff_k / float(k_suf))

    # Build segments k->k+1.
    segs = np.stack([coords[:-1], coords[1:]], axis=1)  # (N-1,2,2)
    seg_colors = q1[:-1]
    seg_widths = lw[:-1]

    # ---- Plot ----
    fig = plt.figure(figsize=(16.8, 8.2))
    gs = fig.add_gridspec(nrows=1, ncols=2, width_ratios=[1.45, 0.55], wspace=0.12)

    ax = fig.add_subplot(gs[0, 0])
    ax.set_aspect("equal")
    ax.set_xlim(-0.6, side - 0.4)
    ax.set_ylim(-0.6, side - 0.4)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Hilbert string on 2D screen: color=q1 (uplift field), width=local d_eff (internal dimension)", fontsize=12, pad=8)

    lc = LineCollection(segs, array=seg_colors, cmap="viridis", linewidths=seg_widths, alpha=0.95, zorder=2)
    ax.add_collection(lc)

    # Start/end markers.
    ax.scatter([coords[0, 0]], [coords[0, 1]], s=85, c="#D84315", edgecolors="white", linewidths=0.9, zorder=5)
    ax.scatter([coords[-1, 0]], [coords[-1, 1]], s=85, c="#1B5E20", edgecolors="white", linewidths=0.9, zorder=5)

    cbar = fig.colorbar(lc, ax=ax, fraction=0.046, pad=0.02)
    cbar.set_label(r"$q_1(k)=|w_{7..m}(k)|_1/(m-6)$", fontsize=10)

    # ---- Right: coarse d_eff map + linewidth legend ----
    axR = fig.add_subplot(gs[0, 1])
    axR.axis("off")

    # inset: d_eff block map
    hm = axR.inset_axes([0.10, 0.52, 0.82, 0.45])
    dmap = d_eff_block.reshape((out_side, out_side))
    im = hm.imshow(dmap, origin="lower", cmap="magma", vmin=0.0, vmax=float(k_suf), interpolation="nearest")
    hm.set_xticks([])
    hm.set_yticks([])
    hm.set_title("coarse map: d_eff per block", fontsize=10, pad=4)
    cb2 = fig.colorbar(im, ax=hm, fraction=0.046, pad=0.02)
    cb2.set_label("d_eff", fontsize=9)

    # linewidth legend
    lg = axR.inset_axes([0.10, 0.12, 0.82, 0.30])
    lg.set_xlim(0.0, 1.0)
    lg.set_ylim(0.0, 1.0)
    lg.axis("off")
    lg.text(0.0, 0.92, "width legend (internal dimension)", fontsize=10, color="#263238")
    for i, d_show in enumerate([1.0, float(k_suf) / 2.0, float(k_suf)]):
        y = 0.72 - 0.22 * i
        w_line = w_min + (w_max - w_min) * (d_show / float(k_suf))
        lg.plot([0.05, 0.95], [y, y], lw=w_line, color="#37474F", solid_capstyle="round")
        lg.text(0.05, y + 0.06, f"d_eff≈{d_show:.1f}", fontsize=9, family="monospace", color="#37474F")

    axR.text(
        0.10,
        0.48,
        f"(m,n)=({m},{n})  side={side}  N={N}\n"
        f"suffix_dim={k_suf}  block={block}  blocks={out_side}×{out_side}\n"
        "d_eff(block)= (tr C)^2 / tr(C^2), C=covariance of suffix-bit vectors in the block\n"
        "Interpretation: same spatial axes; thicker segments indicate more active internal channels locally.",
        transform=axR.transAxes,
        ha="left",
        va="top",
        fontsize=9.5,
        family="monospace",
        color="#263238",
    )

    fig.suptitle("Internal dimension as line thickness along a single Hilbert string (audit-facing)", fontsize=14, y=0.995)
    out_png = out_root / "internal_dimension_hilbert_string_2d.png"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")

    payload: Dict[str, object] = {
        "m": m,
        "n": n,
        "side": side,
        "N": N,
        "suffix_dim": k_suf,
        "block": block,
        "blocks": {"out_side": out_side, "count": int(out_side * out_side)},
        "linewidth_map": {"w_min": w_min, "w_max": w_max},
        "stats": {
            "q1_mean": float(np.mean(q1)),
            "q1_max": float(np.max(q1)),
            "d_eff_mean": float(np.mean(d_eff_block)),
            "d_eff_max": float(np.max(d_eff_block)),
        },
    }
    out_json = out_data / "internal_dimension_hilbert_string_2d.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()

