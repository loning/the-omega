# -*- coding: utf-8 -*-
"""
Figure: protocol-level "quantum field" maps for the Higgs uplift at m=10 (2D Hilbert screen).

We visualize:
  - the four coarse-grained suffix-bit scalar channels \\bar b_0..\\bar b_3,
  - the induced Higgs-doublet components (H1,H2) = (\\bar b_0 + i \\bar b_3, \\bar b_1 + i \\bar b_2),
  - the scalar invariant |H|^2 = H^\\dagger H,
  - and a coupling-style summary: E[\\bar b_j], E[|H|^2] conditioned on the base X6 label
    and its closed 18⊕3 SM label (field-on-screen view).

Outputs
  - figures/adaptive/higgs_geometry/higgs_quantum_field_maps_m10.png
  - figures/adaptive/higgs_geometry/data/higgs_quantum_field_maps_m10.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import exp_foldm_stats as foldm
import exp_hilbert_chirality_index as hil
import exp_sm_labeling_solver as sm
from common_paths import figures_dir


Point2 = Tuple[int, int]


def _block_avg(grid: List[List[float]], block: int) -> List[List[float]]:
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


def _flatten(grid: List[List[float]]) -> List[float]:
    return [float(v) for row in grid for v in row]


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else 0.0


def _quantile(xs: Sequence[float], q: float) -> float:
    if not xs:
        return 0.0
    if q <= 0.0:
        return float(sorted(xs)[0])
    if q >= 1.0:
        return float(sorted(xs)[-1])
    ys = sorted(float(x) for x in xs)
    n = len(ys)
    # Linear interpolation between closest ranks.
    pos = q * float(n - 1)
    i0 = int(pos)
    i1 = min(n - 1, i0 + 1)
    t = pos - float(i0)
    return (1.0 - t) * ys[i0] + t * ys[i1]


def _grad_mag(grid: List[List[float]]) -> List[List[float]]:
    # Simple finite-difference gradient magnitude on a 2D scalar grid (edge-clamped).
    h = len(grid)
    w = len(grid[0]) if h else 0
    out: List[List[float]] = [[0.0 for _ in range(w)] for _ in range(h)]

    def at(y: int, x: int) -> float:
        yy = 0 if y < 0 else (h - 1 if y >= h else y)
        xx = 0 if x < 0 else (w - 1 if x >= w else x)
        return float(grid[yy][xx])

    for y in range(h):
        for x in range(w):
            dx = 0.5 * (at(y, x + 1) - at(y, x - 1))
            dy = 0.5 * (at(y + 1, x) - at(y - 1, x))
            out[y][x] = (dx * dx + dy * dy) ** 0.5
    return out


def _laplace(grid: List[List[float]]) -> List[List[float]]:
    # 5-point Laplacian (edge-clamped).
    h = len(grid)
    w = len(grid[0]) if h else 0
    out: List[List[float]] = [[0.0 for _ in range(w)] for _ in range(h)]

    def at(y: int, x: int) -> float:
        yy = 0 if y < 0 else (h - 1 if y >= h else y)
        xx = 0 if x < 0 else (w - 1 if x >= w else x)
        return float(grid[yy][xx])

    for y in range(h):
        for x in range(w):
            c = at(y, x)
            out[y][x] = at(y, x + 1) + at(y, x - 1) + at(y + 1, x) + at(y - 1, x) - 4.0 * c
    return out


@dataclass(frozen=True)
class LabelInfo:
    tex: str
    plain: str
    kind: str  # "fermion" | "gauge"


def _build_sm_label_map() -> Dict[str, LabelInfo]:
    """
    Return mapping u in X6 (6-bit word) -> TeX label string used in the paper,
    e.g. "$Q_L^{(1)}$" or "$SU(2)$".
    """
    X6 = sm.all_x6()
    boundary = [w for w in X6 if sm.is_boundary_word(w)]
    cyclic = [w for w in X6 if not sm.is_boundary_word(w)]
    boundary_sorted = sorted(boundary, key=lambda w: (sm.zeckendorf_value(w), w))
    cyclic_sorted = sorted(cyclic, key=lambda w: sm.stable_type_sort_key(w))
    fields = sorted(sm.fermion_targets(), key=lambda f: f.complexity_key())
    gauge = sm.boundary_gauge_labels()
    out: Dict[str, LabelInfo] = {}
    for w, f in zip(cyclic_sorted, fields):
        name_plain = f.name.replace("\\", "")
        out[w] = LabelInfo(tex=f.label_tex(), plain=f"{name_plain}({f.generation})", kind="fermion")
    for w, (lab_tex, _rep_tex) in zip(boundary_sorted, gauge):
        lab_plain = lab_tex.strip("$")
        out[w] = LabelInfo(tex=lab_tex, plain=lab_plain, kind="gauge")
    if len(out) != 21:
        raise AssertionError("Expected 21 labels in SM map.")
    return out


@dataclass(frozen=True)
class LabelStats:
    u: str
    label_tex: str
    label_plain: str
    label_kind: str
    n_sites: int
    b_mu: List[float]  # 4 entries
    h2_mu: float       # mean of |H|^2 (coarse scalar) conditioned on u


def main() -> None:
    m_bits = 10
    n_bits = 5
    side = 1 << n_bits
    N = 1 << m_bits
    if side * side != N:
        raise AssertionError("Expected balanced 2D embedding at (m,n)=(10,5).")

    # Coarse-graining block: align with the audited Higgs-doublet construction.
    block = 4

    path: List[Point2] = hil.hilbert_curve(n_bits)
    outs = foldm.cached_foldm_outputs(m_bits)
    if len(path) != N or len(outs) != N:
        raise AssertionError("Unexpected length mismatch for Hilbert path / Foldm outputs.")

    # Raw suffix-bit fields b0..b3 and base prefix u(x)=w[:6].
    b_raw: List[List[List[float]]] = [[[0.0 for _ in range(side)] for _ in range(side)] for _ in range(4)]
    u_grid: List[List[str]] = [["" for _ in range(side)] for _ in range(side)]
    for k, (x, y) in enumerate(path):
        w = outs[k]
        u = w[:6]
        u_grid[y][x] = u
        for j in range(4):
            b_raw[j][y][x] = float(1 if w[6 + j] == "1" else 0)

    # Coarse-grain.
    b4 = [_block_avg(b_raw[j], block) for j in range(4)]
    out_side = side // block

    # Define Higgs components on the coarse grid and |H|^2.
    H1_re = b4[0]
    H1_im = b4[3]
    H2_re = b4[1]
    H2_im = b4[2]
    H2norm: List[List[float]] = [[0.0 for _ in range(out_side)] for _ in range(out_side)]
    H1norm: List[List[float]] = [[0.0 for _ in range(out_side)] for _ in range(out_side)]
    H2comp_norm: List[List[float]] = [[0.0 for _ in range(out_side)] for _ in range(out_side)]
    for y in range(out_side):
        for x in range(out_side):
            h1 = float(H1_re[y][x]) ** 2 + float(H1_im[y][x]) ** 2
            h2 = float(H2_re[y][x]) ** 2 + float(H2_im[y][x]) ** 2
            H1norm[y][x] = h1
            H2comp_norm[y][x] = h2
            H2norm[y][x] = (
                float(H1_re[y][x]) ** 2
                + float(H1_im[y][x]) ** 2
                + float(H2_re[y][x]) ** 2
                + float(H2_im[y][x]) ** 2
            )

    # Field diagnostics for a more "field-like" visualization.
    Hnorm_grad = _grad_mag(H2norm)
    Hnorm_lap = _laplace(H2norm)

    # Conditioned label stats: assign each coarse cell to the majority u in its block
    # (deterministic tie-break: lexicographic).
    sm_map = _build_sm_label_map()
    bucket_b: Dict[str, List[List[float]]] = {u: [[] for _ in range(4)] for u in sm_map.keys()}
    bucket_h2: Dict[str, List[float]] = {u: [] for u in sm_map.keys()}
    bucket_n: Dict[str, int] = {u: 0 for u in sm_map.keys()}

    for by in range(out_side):
        for bx in range(out_side):
            counts: Dict[str, int] = {}
            for dy in range(block):
                for dx in range(block):
                    u = u_grid[by * block + dy][bx * block + dx]
                    counts[u] = counts.get(u, 0) + 1
            # majority with tie-break
            best_u = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            bucket_n[best_u] += 1
            for j in range(4):
                bucket_b[best_u][j].append(float(b4[j][by][bx]))
            bucket_h2[best_u].append(float(H2norm[by][bx]))

    stats: List[LabelStats] = []
    for u in sorted(sm_map.keys(), key=lambda w: (sm.zeckendorf_value(w), w)):
        info = sm_map[u]
        stats.append(
            LabelStats(
                u=u,
                label_tex=info.tex,
                label_plain=info.plain,
                label_kind=info.kind,
                n_sites=int(bucket_n[u]),
                b_mu=[_mean(bucket_b[u][j]) for j in range(4)],
                h2_mu=_mean(bucket_h2[u]),
            )
        )

    # Render figure (matplotlib is an optional paper dependency).
    import matplotlib.pyplot as plt
    import numpy as np

    # ---------------------------
    # Figure A: field maps
    # ---------------------------
    fig = plt.figure(figsize=(17.5, 11.0), dpi=240, constrained_layout=True)
    outer = fig.add_gridspec(3, 1, height_ratios=[1.0, 1.0, 1.55])

    def imshow(ax, grid, title, vmin=None, vmax=None, cmap="viridis"):
        ax.imshow(grid, interpolation="nearest", cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(title, fontsize=10)
        ax.set_axis_off()

    # Top: H1 parts + |H1|^2
    gs0 = outer[0].subgridspec(1, 4, wspace=0.10)
    imshow(fig.add_subplot(gs0[0, 0]), H1_re, r"$\Re(H_1)=\overline{b}_0$", 0.0, 1.0)
    imshow(fig.add_subplot(gs0[0, 1]), H1_im, r"$\Im(H_1)=\overline{b}_3$", 0.0, 1.0)
    imshow(fig.add_subplot(gs0[0, 2]), H1norm, r"$|H_1|^2$", 0.0, 2.0, cmap="magma")
    imshow(fig.add_subplot(gs0[0, 3]), H2norm, r"$|H|^2=|H_1|^2+|H_2|^2$", 0.0, 2.0, cmap="magma")

    # Middle: H2 parts + |H2|^2
    gs1 = outer[1].subgridspec(1, 4, wspace=0.10)
    imshow(fig.add_subplot(gs1[0, 0]), H2_re, r"$\Re(H_2)=\overline{b}_1$", 0.0, 1.0)
    imshow(fig.add_subplot(gs1[0, 1]), H2_im, r"$\Im(H_2)=\overline{b}_2$", 0.0, 1.0)
    imshow(fig.add_subplot(gs1[0, 2]), H2comp_norm, r"$|H_2|^2$", 0.0, 2.0, cmap="magma")
    # Diagnostics: gradient magnitude and Laplacian of |H|^2
    subd = gs1[0, 3].subgridspec(2, 1, hspace=0.12)
    imshow(fig.add_subplot(subd[0, 0]), Hnorm_grad, r"$|\nabla(|H|^2)|$ (finite diff.)", 0.0, None, cmap="inferno")
    # Symmetric scale for Laplacian (deterministic: max-abs on the grid).
    maxabs = 0.0
    for row in Hnorm_lap:
        for v in row:
            maxabs = max(maxabs, abs(float(v)))
    if maxabs <= 0.0:
        maxabs = 1.0
    imshow(fig.add_subplot(subd[1, 0]), Hnorm_lap, r"$\nabla^2(|H|^2)$ (5-pt)", -maxabs, maxabs, cmap="coolwarm")

    # Bottom: conditioned means heatmap + occupancy bar
    gs2 = outer[2].subgridspec(1, 2, width_ratios=[4.4, 1.0], wspace=0.08)
    axh = fig.add_subplot(gs2[0, 0])
    mat: List[List[float]] = []
    ylabels: List[str] = []
    ykinds: List[str] = []
    ns: List[int] = []
    for s in stats:
        mat.append([s.b_mu[0], s.b_mu[1], s.b_mu[2], s.b_mu[3], s.h2_mu])
        ylabels.append(s.label_plain)
        ykinds.append(s.label_kind)
        ns.append(s.n_sites)

    im = axh.imshow(mat, aspect="auto", interpolation="nearest", cmap="magma")
    axh.set_title(
        r"Conditioned coarse means on $m=10,n=5$ Hilbert screen (block=4):  "
        r"$\mathbb{E}[\overline{b}_j\,|\,u]$ and $\mathbb{E}[|H|^2\,|\,u]$",
        fontsize=10,
    )
    axh.set_xticks(list(range(5)))
    axh.set_xticklabels([r"$\overline{b}_0$", r"$\overline{b}_1$", r"$\overline{b}_2$", r"$\overline{b}_3$", r"$|H|^2$"], fontsize=9)
    axh.set_yticks(list(range(len(ylabels))))
    axh.set_yticklabels([f"{lab}" for lab in ylabels], fontsize=8)
    axh.set_xlabel("channel", fontsize=9)
    axh.set_ylabel("closed SM label (by X6 prefix)", fontsize=9)
    cbar = fig.colorbar(im, ax=axh, fraction=0.022, pad=0.02)
    cbar.ax.tick_params(labelsize=8)

    axn = fig.add_subplot(gs2[0, 1], sharey=axh)
    axn.barh(list(range(len(ns))), ns, color=["#455A64" if k == "fermion" else "#8D6E63" for k in ykinds])
    axn.set_title("n blocks", fontsize=9)
    axn.set_xlabel("count", fontsize=9)
    axn.tick_params(axis="y", left=False, labelleft=False)
    axn.grid(axis="x", alpha=0.25)

    fig.suptitle(
        "Higgs uplift as protocol-level quantum fields on a Hilbert screen (m=10,n=5; block=4)",
        fontsize=12,
    )

    out_png = figures_dir() / "adaptive" / "higgs_geometry" / "higgs_quantum_field_maps_m10.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png)
    plt.close(fig)

    # ---------------------------
    # Figure B: coupling-style distributions (per label)
    # ---------------------------
    # Use the conditioned coarse cells (block grid) distributions as the audit-facing observation class.
    labels_order = [s.label_plain for s in stats]
    kinds_order = [s.label_kind for s in stats]
    h2_lists = [bucket_h2[s.u] for s in stats]

    fig2 = plt.figure(figsize=(15.5, 10.5), dpi=240, constrained_layout=True)
    gs = fig2.add_gridspec(2, 1, height_ratios=[1.0, 1.0])

    # Panel 1: boxplot of |H|^2 per label (horizontal).
    axb = fig2.add_subplot(gs[0, 0])
    bp = axb.boxplot(
        h2_lists,
        vert=False,
        tick_labels=labels_order,
        showfliers=False,
        widths=0.65,
        patch_artist=True,
        medianprops={"color": "#263238", "linewidth": 1.2},
        boxprops={"linewidth": 0.9},
        whiskerprops={"linewidth": 0.9},
        capprops={"linewidth": 0.9},
    )
    for patch, k in zip(bp["boxes"], kinds_order):
        patch.set_facecolor("#90CAF9" if k == "fermion" else "#FFCCBC")
        patch.set_edgecolor("#455A64")
        patch.set_alpha(0.95)
    axb.set_title(r"Distributions of coarse $|H|^2$ conditioned on closed SM label (block=4)", fontsize=11)
    axb.set_xlabel(r"$|H|^2$ (coarse)", fontsize=10)
    axb.grid(axis="x", alpha=0.25)
    axb.tick_params(axis="y", labelsize=8)

    # Panel 2: per-label quantile heatmap for b0..b3 and |H|^2 (median + IQR width as two rows).
    axq = fig2.add_subplot(gs[1, 0])
    # Build 10xN matrix: medians for (b0..b3,|H|^2) then IQRs for same.
    med_rows: List[List[float]] = [[] for _ in range(5)]
    iqr_rows: List[List[float]] = [[] for _ in range(5)]
    for s in stats:
        # b0..b3
        for j in range(4):
            vals_b = bucket_b[s.u][j]
            q25 = _quantile(vals_b, 0.25)
            q50 = _quantile(vals_b, 0.50)
            q75 = _quantile(vals_b, 0.75)
            med_rows[j].append(q50)
            iqr_rows[j].append(q75 - q25)
        # |H|^2
        vals_h2 = bucket_h2[s.u]
        q25h = _quantile(vals_h2, 0.25)
        q50h = _quantile(vals_h2, 0.50)
        q75h = _quantile(vals_h2, 0.75)
        med_rows[4].append(q50h)
        iqr_rows[4].append(q75h - q25h)

    A = np.array(med_rows + iqr_rows, dtype=float)
    imq = axq.imshow(A, aspect="auto", interpolation="nearest", cmap="viridis")
    axq.set_yticks(list(range(10)))
    axq.set_yticklabels(
        [
            r"med($\overline{b}_0$)",
            r"med($\overline{b}_1$)",
            r"med($\overline{b}_2$)",
            r"med($\overline{b}_3$)",
            r"med($|H|^2$)",
            r"IQR($\overline{b}_0$)",
            r"IQR($\overline{b}_1$)",
            r"IQR($\overline{b}_2$)",
            r"IQR($\overline{b}_3$)",
            r"IQR($|H|^2$)",
        ],
        fontsize=8,
    )
    axq.set_xticks(list(range(len(labels_order))))
    axq.set_xticklabels(labels_order, rotation=90, fontsize=7)
    axq.set_title("Per-label robust summaries: medians and IQRs for channels and $|H|^2$", fontsize=11)
    fig2.colorbar(imq, ax=axq, fraction=0.018, pad=0.02)

    out_png2 = figures_dir() / "adaptive" / "higgs_geometry" / "higgs_quantum_field_coupling_m10.png"
    out_png2.parent.mkdir(parents=True, exist_ok=True)
    fig2.savefig(out_png2)
    plt.close(fig2)

    out_json = figures_dir() / "adaptive" / "higgs_geometry" / "data" / "higgs_quantum_field_maps_m10.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    label_rows = []
    for s in stats:
        vals_h2 = bucket_h2[s.u]
        bq = []
        for j in range(4):
            vb = bucket_b[s.u][j]
            bq.append(
                {
                    "q05": _quantile(vb, 0.05),
                    "q25": _quantile(vb, 0.25),
                    "q50": _quantile(vb, 0.50),
                    "q75": _quantile(vb, 0.75),
                    "q95": _quantile(vb, 0.95),
                }
            )
        label_rows.append(
            {
                "u": s.u,
                "label_tex": s.label_tex,
                "label_plain": s.label_plain,
                "label_kind": s.label_kind,
                "n_cells": s.n_sites,
                "b_mu": s.b_mu,
                "b_q": bq,
                "h2_mu": s.h2_mu,
                "h2_q": {
                    "q05": _quantile(vals_h2, 0.05),
                    "q25": _quantile(vals_h2, 0.25),
                    "q50": _quantile(vals_h2, 0.50),
                    "q75": _quantile(vals_h2, 0.75),
                    "q95": _quantile(vals_h2, 0.95),
                },
            }
        )
    out_json.write_text(
        json.dumps(
            {
                "m": m_bits,
                "n": n_bits,
                "block": block,
                "definition": {
                    "H1_re": "b0 coarse field",
                    "H1_im": "b3 coarse field",
                    "H2_re": "b1 coarse field",
                    "H2_im": "b2 coarse field",
                    "H_norm2": "|H|^2 = sum of squares of coarse components",
                    "H_norm2_grad_mag": "finite-difference gradient magnitude of |H|^2 (edge-clamped)",
                    "H_norm2_laplacian": "5-point Laplacian of |H|^2 (edge-clamped)",
                    "conditioning": "each coarse cell assigned to majority X6 prefix u in its 4x4 block",
                },
                "labels": label_rows,
                "artifacts": {
                    "field_maps_png": "figures/adaptive/higgs_geometry/higgs_quantum_field_maps_m10.png",
                    "coupling_png": "figures/adaptive/higgs_geometry/higgs_quantum_field_coupling_m10.png",
                },
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"Wrote {out_png}")
    print(f"Wrote {out_png2}")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()

