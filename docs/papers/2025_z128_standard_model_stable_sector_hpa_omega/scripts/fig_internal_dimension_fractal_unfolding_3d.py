# -*- coding: utf-8 -*-
"""
Figure: internal-dimension unfolding on a 3D (nD Hilbert) screen (m=3n).

We provide a 3D companion visualization for the "point carries internal fiber" narrative.
No extra spatial axes are introduced: the 3D screen is an addressing/display choice for
balanced capacity, analogous to the 2D balanced Hilbert screen (m=2n).

Instance:
  - (m,n)=(12,4) so that |screen| = 2^{3n} = 2^m = 4096 and the 16^3 cube is fully occupied.

We compute:
  - q0(x): normalized Hamming weight |u|_1 / 3 for u = Fold_m(k)[:6],
  - q1(x): normalized suffix weight |w_{7..m}|_1 / (m-6).

We render:
  - three z-slices (z=0, z=L/2, z=L-1) for q0 and q1,
  - plus a max-intensity projection for q1 as a coarse summary.

Outputs:
  - figures/adaptive/lattice_qft_bridge/internal_dimension_fractal_unfolding_3d.png
  - figures/adaptive/lattice_qft_bridge/data/internal_dimension_fractal_unfolding_3d.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402

import exp_foldm_stats as foldm  # noqa: E402
from common_paths import figures_dir  # noqa: E402
from hilbert_nd import hilbert_index_to_coords  # noqa: E402


def _hamming01(s: str) -> int:
    return sum(1 for ch in s if ch == "1")


def main() -> None:
    out_root: Path = figures_dir() / "adaptive" / "lattice_qft_bridge"
    out_data: Path = out_root / "data"
    out_root.mkdir(parents=True, exist_ok=True)
    out_data.mkdir(parents=True, exist_ok=True)

    # Balanced 3D: m=3n with n=4 => L=16, N=4096.
    m = 12
    n = 4
    L = 1 << n
    N = 1 << m
    if L * L * L != N:
        raise AssertionError("Expected balanced 3D embedding with m=3n.")

    outs = foldm.cached_foldm_outputs(m)
    if len(outs) != N:
        raise AssertionError("Unexpected Foldm output length.")

    q0 = np.zeros((L, L, L), dtype=float)
    q1 = np.zeros((L, L, L), dtype=float)
    k_suf = m - 6

    # Use nD Hilbert curve (Skilling) for 3D addressing: coords = (x,y,z).
    for k in range(N):
        x, y, z = hilbert_index_to_coords(k, p=n, n=3)
        w = outs[k]
        u = w[:6]
        q0[z, y, x] = float(_hamming01(u)) / 3.0
        suf = w[6:]
        q1[z, y, x] = float(_hamming01(suf)) / float(k_suf)

    z_slices = [0, L // 2, L - 1]
    q1_mip = np.max(q1, axis=0)  # (y,x) max over z

    fig = plt.figure(figsize=(16.8, 7.2))
    gs = fig.add_gridspec(nrows=2, ncols=4, height_ratios=[1.0, 1.0], wspace=0.10, hspace=0.22)

    def _panel(ax, img, title):
        im = ax.imshow(img, origin="lower", cmap="viridis", vmin=0.0, vmax=1.0, interpolation="nearest")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(title, fontsize=10, pad=4)
        return im

    # q0 slices
    for i, zz in enumerate(z_slices):
        ax = fig.add_subplot(gs[0, i])
        im = _panel(ax, q0[zz, :, :], f"q0 slice z={zz}  (|u|1/3)")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)

    # q1 slices + MIP
    for i, zz in enumerate(z_slices):
        ax = fig.add_subplot(gs[1, i])
        im = _panel(ax, q1[zz, :, :], f"q1 slice z={zz}  (|suffix|1/(m-6))")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)

    ax_mip = fig.add_subplot(gs[:, 3])
    im_mip = _panel(ax_mip, q1_mip, "q1 max-intensity projection over z")
    fig.colorbar(im_mip, ax=ax_mip, fraction=0.046, pad=0.02)
    ax_mip.text(
        0.02,
        0.98,
        f"(m,n)=(12,4)  screen=16×16×16\naddressing=Hilbert_nd(p=4,n=3)\nsuffix_dim={k_suf}",
        transform=ax_mip.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        family="monospace",
        color="#263238",
    )

    fig.suptitle("Internal-dimension unfolding on a 3D screen (balanced m=3n): slices and projection", fontsize=14, y=0.995)
    out_png = out_root / "internal_dimension_fractal_unfolding_3d.png"
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_png}")

    payload: Dict[str, object] = {
        "m": m,
        "n": n,
        "L": L,
        "suffix_dim": k_suf,
        "z_slices": z_slices,
        "addressing": "hilbert_nd",
        "addressing_params": {"p": n, "dims": 3},
        "stats": {
            "q0_mean": float(np.mean(q0)),
            "q1_mean": float(np.mean(q1)),
            "q1_max": float(np.max(q1)),
        },
    }
    out_json = out_data / "internal_dimension_fractal_unfolding_3d.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()

