# -*- coding: utf-8 -*-
"""
Figure: internal-dimension field visualization on adaptive-dimension Hilbert-face screens.

We visualize the idea "no extra spatial axes, only more internal information at a site"
in the adaptive-dimension (boundary-face) display dictionary:
  - choose D_face = ceil(m/n) so the face has capacity 2^{D_face n} >= 2^m,
  - place k=0..2^m-1 on the D_face-dimensional face via an nD Hilbert scan,
  - interpret a scalar observable q(k) as a field value at that face coordinate.

We use two protocol-native scalars:
  - q0(k) = |u|_1/3 where u = Fold_m(k)[:6] (X6 prefix; 18⊕3 interface anchor),
  - q1(k) = |suffix|_1/(m-6) where suffix = Fold_m(k)[6:] (uplift microtexture).

We render pairwise 2D projections of the face axes (x1..x_{D_face}), colored by q1.
A small right panel summarizes (q0,q1) statistics and shows a q1 histogram.

Outputs:
  - figures/adaptive/lattice_qft_bridge/internal_dimension_hilbert_face_gallery.png
  - figures/adaptive/lattice_qft_bridge/data/internal_dimension_hilbert_face_gallery.json
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

import exp_foldm_stats as foldm  # noqa: E402
from common_paths import figures_dir  # noqa: E402
from hilbert_nd import hilbert_index_to_coords  # noqa: E402
from screen_universal_vfs import embedding_dimension, effective_dimension  # noqa: E402


def _hamming01(s: str) -> int:
    return sum(1 for ch in s if ch == "1")


def _style_grid(ax, L: int) -> None:
    if L <= 64:
        for i in range(L + 1):
            ax.plot([-0.5, L - 0.5], [i - 0.5, i - 0.5], color="#ECEFF1", lw=0.6, zorder=0)
            ax.plot([i - 0.5, i - 0.5], [-0.5, L - 0.5], color="#ECEFF1", lw=0.6, zorder=0)
    ax.set_aspect("equal")
    ax.set_xlim(-0.6, L - 0.4)
    ax.set_ylim(-0.6, L - 0.4)
    ax.set_xticks([])
    ax.set_yticks([])


def _max_l1_jump(coords: np.ndarray) -> int:
    if coords.shape[0] < 2:
        return 0
    dif = np.abs(coords[1:, :] - coords[:-1, :])
    return int(np.max(np.sum(dif, axis=1)))


def _hist(xs: np.ndarray, bins: int = 12) -> Tuple[np.ndarray, np.ndarray]:
    # Deterministic histogram over [0,1].
    edges = np.linspace(0.0, 1.0, bins + 1)
    counts, edges = np.histogram(xs, bins=edges)
    return counts.astype(int), edges


def main() -> None:
    out_root: Path = figures_dir() / "adaptive" / "lattice_qft_bridge"
    out_data: Path = out_root / "data"
    out_root.mkdir(parents=True, exist_ok=True)
    out_data.mkdir(parents=True, exist_ok=True)

    # Representative adaptive-dimension pairs (keep N moderate for plotting).
    pairs: List[Tuple[int, int]] = [
        (7, 3),   # D_face=3, N=128
        (10, 3),  # D_face=4, N=1024
        (12, 3),  # D_face=4, N=4096
    ]

    nrows = len(pairs)
    fig, axes = plt.subplots(nrows=nrows, ncols=2, figsize=(16.8, 5.0 * nrows))
    if nrows == 1:
        axes = np.array([axes])  # type: ignore

    c_text = "#263238"
    payload: Dict[str, object] = {"pairs": [], "version": 1}

    for r, (m, n) in enumerate(pairs):
        axB, axT = axes[r]
        N = 1 << m
        L = 1 << n
        d_eff = effective_dimension(m, n)
        D_face = embedding_dimension(m, n)
        D_bulk = D_face + 1

        # Face coords for k=0..2^m-1.
        face_coords = np.array([hilbert_index_to_coords(k, p=n, n=D_face) for k in range(N)], dtype=float)  # (N,D_face)
        bulk_coords = np.concatenate([np.zeros((N, 1), dtype=float), face_coords], axis=1)  # x0=0 boundary face

        outs = foldm.cached_foldm_outputs(m)
        if len(outs) != N:
            raise AssertionError("Unexpected Foldm outputs length.")

        q0 = np.zeros((N,), dtype=float)
        q1 = np.zeros((N,), dtype=float)
        k_suf = max(0, m - 6)
        for k in range(N):
            w = outs[k]
            u = w[:6]
            q0[k] = float(_hamming01(u)) / 3.0
            if k_suf > 0:
                suf = w[6:]
                q1[k] = float(_hamming01(suf)) / float(k_suf)
            else:
                q1[k] = 0.0

        # ---- Left: pairwise 2D projections (like the existing gallery) ----
        axB.axis("off")
        axB.set_xlim(0, 1)
        axB.set_ylim(0, 1)

        d_show = min(D_face, 4)
        if d_show == 1:
            projs = [(1, 1)]
        elif d_show == 2:
            projs = [(1, 2)]
        elif d_show == 3:
            projs = [(1, 2), (1, 3), (2, 3)]
        else:
            projs = [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]

        def _proj(outer_ax, x0, y0, w, h, a, b, title):
            iax = outer_ax.inset_axes([x0, y0, w, h])
            _style_grid(iax, L)
            xy = bulk_coords[:, [a, b]]
            segs = np.stack([xy[:-1], xy[1:]], axis=1)
            # faint curve geometry
            t_segs = np.linspace(0.0, 1.0, len(segs))
            iax.add_collection(LineCollection(segs, array=t_segs, cmap="Greys", linewidths=0.65, alpha=0.22, zorder=1))
            # field values (q1) as colors at points
            iax.scatter(xy[:, 0], xy[:, 1], s=16 if N <= 1024 else 9, c=q1, cmap="viridis", vmin=0.0, vmax=1.0, alpha=0.78, edgecolors="none", zorder=2)
            # start/end
            iax.scatter([xy[0, 0]], [xy[0, 1]], s=60, c="#D84315", edgecolors="white", linewidths=0.7, zorder=5)
            iax.scatter([xy[-1, 0]], [xy[-1, 1]], s=60, c="#1B5E20", edgecolors="white", linewidths=0.7, zorder=5)
            iax.set_title(title, fontsize=10, color=c_text, pad=2)
            return iax

        if len(projs) == 1:
            (a, b) = projs[0]
            _proj(axB, 0.06, 0.14, 0.88, 0.78, a, b, f"x{a}–x{b} (colored by q1)")
        elif len(projs) == 3:
            (a0, b0), (a1, b1), (a2, b2) = projs
            _proj(axB, 0.02, 0.54, 0.31, 0.42, a0, b0, f"x{a0}–x{b0}")
            _proj(axB, 0.35, 0.54, 0.31, 0.42, a1, b1, f"x{a1}–x{b1}")
            _proj(axB, 0.68, 0.54, 0.31, 0.42, a2, b2, f"x{a2}–x{b2}")
            axB.text(
                0.02,
                0.48,
                "Field coloring: q1(k)=|suffix|1/(m-6) on the D_face-dimensional Hilbert-face.\n"
                "Projection overlaps can occur when D_face>2 (hidden coordinates).",
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
                "Shown: pairwise projections among the first 4 face axes (D_face≥4).",
                fontsize=11,
                color=c_text,
            )

        # ---- Right: stats + histogram ----
        axT.axis("off")
        mx_face = _max_l1_jump(face_coords)
        # x1-x2 projection multiplicity (overlaps only in projection).
        if D_face >= 2:
            proj12 = bulk_coords[:, [1, 2]]
            unique12 = len({(int(x), int(y)) for x, y in proj12.tolist()})
        else:
            unique12 = N
        avg_mult = float(N) / float(unique12) if unique12 > 0 else float("inf")

        counts, edges = _hist(q1, bins=12)
        # Embed a histogram axes.
        hax = axT.inset_axes([0.06, 0.10, 0.86, 0.32])
        centers = 0.5 * (edges[:-1] + edges[1:])
        hax.bar(centers, counts, width=(edges[1] - edges[0]) * 0.90, color="#546E7A")
        hax.set_xlim(0.0, 1.0)
        hax.set_yticks([])
        hax.set_xlabel("q1", fontsize=9)
        hax.set_title("q1 histogram", fontsize=10, pad=2)
        hax.grid(True, axis="y", color="#ECEFF1", lw=0.8)

        lines: List[str] = []
        lines.append(f"(m,n)=({m},{n})  N=2^{m}={N}")
        lines.append(f"d_eff=m/n={d_eff:.3f}")
        lines.append(f"D_face=ceil(d_eff)={D_face},  face size=({L}^{D_face})  D_bulk=D_face+1={D_bulk}")
        lines.append(f"suffix_dim = max(0,m-6) = {k_suf}")
        lines.append(f"q0 mean={float(np.mean(q0)):.4f},  q1 mean={float(np.mean(q1)):.4f},  q1 max={float(np.max(q1)):.4f}")
        lines.append("")
        lines.append("Locality (Hilbert adjacency on the full face):")
        lines.append(f"  max L1 jump on face = {mx_face} (expected 1)")
        lines.append("Projection note (x1–x2):")
        lines.append(f"  unique cells={unique12} of {L*L}, avg multiplicity≈{avg_mult:.2f}")
        axT.text(0.06, 0.98, "\n".join(lines), va="top", ha="left", family="monospace", fontsize=10, color=c_text)

        payload["pairs"].append(
            {
                "m": m,
                "n": n,
                "N": int(N),
                "L": int(L),
                "d_eff": float(d_eff),
                "D_face": int(D_face),
                "D_bulk": int(D_bulk),
                "suffix_dim": int(k_suf),
                "stats": {"q0_mean": float(np.mean(q0)), "q1_mean": float(np.mean(q1)), "q1_max": float(np.max(q1))},
                "projection_x1x2": {"unique": int(unique12), "avg_mult": float(avg_mult)},
                "max_l1_jump_face": int(mx_face),
                "q1_hist": {"bins": 12, "edges": [float(e) for e in edges.tolist()], "counts": [int(c) for c in counts.tolist()]},
            }
        )

    fig.suptitle(
        "Internal-dimension field on adaptive-dimension Hilbert-face screens (colored by uplift scalar q1)",
        fontsize=14,
        y=0.995,
    )
    out_png = out_root / "internal_dimension_hilbert_face_gallery.png"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")

    out_json = out_data / "internal_dimension_hilbert_face_gallery.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()

