# -*- coding: utf-8 -*-
"""
Geometry-driven Higgs-doublet structure at the m=10 uplift (balanced 2D).

Goal
  Find a concrete, reproducible "Higgs-like scalar doublet structure" purely from
  the Hilbert-screen geometry of the uplift microstructure.

Protocol semantics used (consistent with the paper)
  - Scalars are parity-even protocol observables obtained by coarse graining on
    the Hilbert grid (Prop. scalar_sector_closed).
  - A parity-odd comparator exists: the local turn-sign field of the Hilbert path
    (built from signed turns; cf. chi_H).

Construction (deterministic)
  - Fix (m,n)=(10,5) so 2^m equals the 2D grid sites (balanced embedding).
  - For each site (x,y), compute w = Fold_m(k) and its suffix bits s = w[6:10].
  - Define four raw scalar channels b0..b3 as the suffix bits (0/1 fields).
  - Define a parity-odd field t(x,y) from the signed turn at that site along the
    Hilbert traversal (endpoints set to 0).
  - Coarse-grain by 4x4 block averaging, then score each bi for:
      (i) reflection-invariance under y-reflection (parity-even proxy),
     (ii) low correlation with the parity-odd turn field.
  - Choose a pairing of {b0,b1,b2,b3} into two pairs to form a complex doublet:
      H = (b_i + i b_j, b_k + i b_l),
    by minimizing cross-correlation between the two complex components.

Outputs
  - figures/adaptive/higgs_geometry/data/higgs_doublet_structure_m10.json
  - figures/adaptive/higgs_geometry/higgs_doublet_structure_m10.png
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import exp_foldm_stats as foldm
import exp_hilbert_chirality_index as hil
from common_paths import figures_dir


Point = Tuple[int, int]


def _mean(xs: Sequence[float]) -> float:
    if not xs:
        raise ValueError("mean() requires non-empty list.")
    return sum(xs) / float(len(xs))


def _var_pop(xs: Sequence[float]) -> float:
    if not xs:
        raise ValueError("var() requires non-empty list.")
    m = _mean(xs)
    return _mean([(x - m) ** 2 for x in xs])


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("dot() requires equal lengths.")
    return sum(float(x) * float(y) for x, y in zip(a, b))


def _corr(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("corr() requires equal lengths.")
    ma = _mean(list(a))
    mb = _mean(list(b))
    da = [float(x) - ma for x in a]
    db = [float(y) - mb for y in b]
    va = _dot(da, da)
    vb = _dot(db, db)
    if va <= 0.0 or vb <= 0.0:
        return 0.0
    return _dot(da, db) / math.sqrt(va * vb)


def _reflect_y_grid_correct(grid: List[List[float]]) -> List[List[float]]:
    # Our grid is indexed as grid[y][x]. Reflect y means y -> L - y.
    return list(reversed(grid))


def _block_avg(grid: List[List[float]], *, block: int) -> List[List[float]]:
    side = len(grid)
    if side == 0 or any(len(r) != side for r in grid):
        raise ValueError("grid must be non-empty square.")
    if block <= 0 or (side % block) != 0:
        raise ValueError("block must be positive and divide side.")
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


def _l2_rel(a: Sequence[float], b: Sequence[float]) -> float:
    # ||a-b|| / (||a||+||b||+eps)
    if len(a) != len(b):
        raise ValueError("l2 requires equal lengths.")
    da = [float(x) - float(y) for x, y in zip(a, b)]
    na = math.sqrt(_dot(a, a))
    nb = math.sqrt(_dot(b, b))
    nd = math.sqrt(_dot(da, da))
    return nd / (na + nb + 1e-12)


@dataclass(frozen=True)
class ChannelReport:
    name: str
    bit_index: int
    mu: float
    var: float
    reflect_y_corr: float
    reflect_y_l2rel: float
    corr_with_turn: float


def _pairings(idxs: Sequence[int]) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    # All pairings of four distinct indices into two unordered pairs.
    a, b, c, d = idxs
    return [((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c))]


def _component_cross_corr(
    *,
    re_a: Sequence[float],
    im_a: Sequence[float],
    re_b: Sequence[float],
    im_b: Sequence[float],
) -> float:
    # Use the maximum absolute correlation across the 4 real cross-combinations.
    cs = [
        abs(_corr(re_a, re_b)),
        abs(_corr(re_a, im_b)),
        abs(_corr(im_a, re_b)),
        abs(_corr(im_a, im_b)),
    ]
    return max(cs)


def _render(
    *,
    b4: List[List[List[float]]],
    t4: List[List[float]],
    pairing: Tuple[Tuple[int, int], Tuple[int, int]],
    out_png,
) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(10.5, 7.0), dpi=180)
    (ax00, ax01, ax02), (ax10, ax11, ax12) = axes

    for j, ax in enumerate([ax00, ax01, ax02, ax10]):
        im = ax.imshow(b4[j], cmap="viridis", interpolation="nearest", vmin=0.0, vmax=1.0)
        ax.set_title(f"b{j} = suffix bit {6+j} (4x4 avg)", fontsize=9)
        ax.set_axis_off()
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    imt = ax11.imshow(t4, cmap="coolwarm", interpolation="nearest", vmin=-1.0, vmax=1.0)
    ax11.set_title("turn sign field t (4x4 avg, parity-odd)", fontsize=9)
    ax11.set_axis_off()
    fig.colorbar(imt, ax=ax11, fraction=0.046, pad=0.04)

    (i, j), (k, l) = pairing
    ax12.axis("off")
    ax12.text(
        0.0,
        0.9,
        "Chosen Higgs-like doublet (geometry):",
        fontsize=10,
        transform=ax12.transAxes,
    )
    ax12.text(
        0.0,
        0.72,
        f"H1 = b{i} + i b{j}",
        fontsize=10,
        transform=ax12.transAxes,
    )
    ax12.text(
        0.0,
        0.56,
        f"H2 = b{k} + i b{l}",
        fontsize=10,
        transform=ax12.transAxes,
    )
    ax12.text(
        0.0,
        0.34,
        "Each bℓ is a parity-even scalar channel\n(after coarse graining), and t is parity-odd.",
        fontsize=9,
        transform=ax12.transAxes,
    )

    fig.suptitle("m=10,n=5: uplift microstructure → scalar channels → Higgs-like doublet", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_png)
    plt.close(fig)


def main() -> None:
    m_bits = 10
    n_bits = 5
    side = 1 << n_bits
    N = 1 << m_bits
    if side * side != N:
        raise AssertionError("Expected balanced 2D embedding: 2^m == (2^n)^2.")
    L = side - 1

    path = hil.hilbert_curve(n_bits)
    if len(path) != N:
        raise AssertionError("Unexpected Hilbert path length.")

    # Build raw grids on the 32x32 screen.
    b_raw: List[List[List[float]]] = [[[0.0 for _ in range(side)] for _ in range(side)] for _ in range(4)]
    t_raw: List[List[float]] = [[0.0 for _ in range(side)] for _ in range(side)]

    # Map index->coord for placing turn-sign at the middle point.
    for k, (x, y) in enumerate(path):
        w = foldm.foldm(k, m_bits)
        suf = w[6:10]
        for j in range(4):
            b_raw[j][y][x] = 1.0 if suf[j] == "1" else 0.0

    # Turn-sign field from local signed turns along the traversal.
    for i in range(1, len(path) - 1):
        x0, y0 = path[i - 1]
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        v1 = (x1 - x0, y1 - y0)
        v2 = (x2 - x1, y2 - y1)
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        sgn = 0.0
        if cross > 0:
            sgn = 1.0
        elif cross < 0:
            sgn = -1.0
        t_raw[y1][x1] = sgn

    # Sanity: reflect the path, recompute turn signs, and compare to -pullback of the original.
    path_ref = [hil.reflect_y(L, p) for p in path]
    t_raw_ref: List[List[float]] = [[0.0 for _ in range(side)] for _ in range(side)]
    for i in range(1, len(path_ref) - 1):
        x0, y0 = path_ref[i - 1]
        x1, y1 = path_ref[i]
        x2, y2 = path_ref[i + 1]
        v1 = (x1 - x0, y1 - y0)
        v2 = (x2 - x1, y2 - y1)
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        sgn = 0.0
        if cross > 0:
            sgn = 1.0
        elif cross < 0:
            sgn = -1.0
        t_raw_ref[y1][x1] = sgn

    t_pull = _reflect_y_grid_correct(t_raw)
    t_pull_neg = [[-float(v) for v in row] for row in t_pull]
    corr_t = _corr(_flatten(t_raw_ref), _flatten(t_pull_neg))
    if corr_t < 0.99:
        raise AssertionError("Expected reflected turn-sign field to match -pullback of original.")

    # Coarse graining level for scalar channels (4x4 gives an 8x8 field).
    block = 4
    b4 = [_block_avg(b_raw[j], block=block) for j in range(4)]
    t4 = _block_avg(t_raw, block=block)

    # Reports per channel (parity-even proxy and orthogonality to parity-odd).
    reports: List[ChannelReport] = []
    for j in range(4):
        v = _flatten(b4[j])
        v_ref = _flatten(_reflect_y_grid_correct(b4[j]))
        reports.append(
            ChannelReport(
                name=f"b{j}",
                bit_index=6 + j,
                mu=_mean(v),
                var=_var_pop(v),
                reflect_y_corr=_corr(v, v_ref),
                reflect_y_l2rel=_l2_rel(v, v_ref),
                corr_with_turn=_corr(v, _flatten(t4)),
            )
        )

    # Choose a doublet pairing by minimizing cross-correlation between components.
    idxs = [0, 1, 2, 3]
    best = None
    best_score = None
    for (a, b), (c, d) in _pairings(idxs):
        re1, im1 = _flatten(b4[a]), _flatten(b4[b])
        re2, im2 = _flatten(b4[c]), _flatten(b4[d])
        cross = _component_cross_corr(re_a=re1, im_a=im1, re_b=re2, im_b=im2)
        # Prefer pairings where each component is individually parity-even and turn-orthogonal.
        pen = 0.0
        for j in (a, b, c, d):
            r = reports[j]
            pen += max(0.0, 0.95 - r.reflect_y_corr) * 5.0
            pen += abs(r.corr_with_turn) * 2.0
        score = cross + pen
        if best_score is None or score < best_score:
            best_score = score
            best = ((a, b), (c, d))
    if best is None or best_score is None:
        raise AssertionError("Failed to select a pairing.")

    out_base = figures_dir() / "adaptive" / "higgs_geometry"
    data_dir = out_base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_json = data_dir / "higgs_doublet_structure_m10.json"
    out_png = out_base / "higgs_doublet_structure_m10.png"

    payload = {
        "m": m_bits,
        "n": n_bits,
        "block": block,
        "definition": {
            "channels": "b0..b3 are the suffix bits w[6:10] as 0/1 scalar fields on the Hilbert grid.",
            "turn_field": "t is the signed turn (cross product sign) at each Hilbert step; parity-odd under y-reflection.",
            "criteria": [
                "parity-even proxy: y-reflection invariance after 4x4 coarse graining",
                "scalar-vs-chiral separation: low correlation with parity-odd turn field",
                "doublet pairing: minimal cross-correlation between the two complex components",
            ],
        },
        "sanity": {"corr_turn_with_reflect_y": corr_t},
        "channels": [
            {
                "name": r.name,
                "bit_index": r.bit_index,
                "mu": r.mu,
                "var": r.var,
                "reflect_y_corr": r.reflect_y_corr,
                "reflect_y_l2rel": r.reflect_y_l2rel,
                "corr_with_turn": r.corr_with_turn,
            }
            for r in reports
        ],
        "doublet": {"H1": {"re": best[0][0], "im": best[0][1]}, "H2": {"re": best[1][0], "im": best[1][1]}, "objective": best_score},
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_json.relative_to(out_json.parents[3])}")

    _render(b4=b4, t4=t4, pairing=best, out_png=out_png)
    print(f"Wrote {out_png.relative_to(out_png.parents[3])}")


if __name__ == "__main__":
    main()

