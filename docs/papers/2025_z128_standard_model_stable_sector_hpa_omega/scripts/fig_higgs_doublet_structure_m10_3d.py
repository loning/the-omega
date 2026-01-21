# -*- coding: utf-8 -*-
"""
3D Hilbert version of the geometry-driven Higgs-doublet structure at the m=10 uplift.

2D vs 3D embedding
  - 2D: (m,n)=(10,5) is balanced (32x32 has exactly 2^10 sites), so every site is filled.
  - 3D: choose n3=ceil(m/3)=4, so the 3D screen is 16^3=4096 sites while we embed only
        the prefix path of length 2^10=1024 (sparse occupancy).

Construction (deterministic)
  - Use hilbert_nd.hilbert_index_to_coords(k,p=n3,n=3) for k=0..2^m-1.
  - Define four scalar channels b0..b3 from suffix bits w[6:10] as 0/1 on visited sites.
  - Define a parity-odd 3D "turn" scalar t via the scalar triple product sign of
    consecutive step vectors (uses 4 successive points).
  - Coarse-grain on the 3D screen by 2x2x2 block averages computed over occupied sites.
  - Choose a complex-doublet pairing H=(H1,H2) from {b0..b3} by:
      (i) coarse reflection-evenness under y-reflection on the block grid,
     (ii) low correlation with the parity-odd turn field,
    (iii) minimal cross-correlation between H1 and H2 real/imag parts.

Outputs
  - figures/adaptive/higgs_geometry/data/higgs_doublet_structure_m10_3d.json
  - figures/adaptive/higgs_geometry/higgs_doublet_structure_m10_3d.png
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import exp_foldm_stats as foldm
from common_paths import figures_dir
from hilbert_nd import hilbert_index_to_coords


Coord3 = Tuple[int, int, int]


def _mean(xs: Sequence[float]) -> float:
    if not xs:
        raise ValueError("mean() requires non-empty list.")
    return sum(xs) / float(len(xs))


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


def _corr_masked(a: Sequence[float], b: Sequence[float], m: Sequence[bool]) -> float:
    aa: List[float] = []
    bb: List[float] = []
    for x, y, ok in zip(a, b, m):
        if ok:
            aa.append(float(x))
            bb.append(float(y))
    if len(aa) < 2:
        return 0.0
    return _corr(aa, bb)


def _reflect_y(c: Coord3, L: int) -> Coord3:
    x, y, z = c
    return (x, L - y, z)


def _triple_sign(v1: Coord3, v2: Coord3, v3: Coord3) -> float:
    # det([v1 v2 v3]) as scalar triple product sign.
    a1, a2, a3 = v1
    b1, b2, b3 = v2
    c1, c2, c3 = v3
    det = (
        a1 * (b2 * c3 - b3 * c2)
        - a2 * (b1 * c3 - b3 * c1)
        + a3 * (b1 * c2 - b2 * c1)
    )
    if det > 0:
        return 1.0
    if det < 0:
        return -1.0
    return 0.0


def _block_avg_sparse(
    *,
    values: Dict[Coord3, float],
    side: int,
    block: int,
) -> tuple[List[float], List[Coord3], List[bool]]:
    """
    Return (vals, centers, mask) over all blocks in a side^3 grid.
    - vals: block average (NaN if empty)
    - centers: integer block centers (for plotting)
    - mask: True iff block had >=1 occupied site (finite value)
    """
    if side <= 0 or block <= 0 or (side % block) != 0:
        raise ValueError("block must be positive and divide side.")
    B = side // block
    out_vals: List[float] = []
    out_centers: List[Coord3] = []
    out_mask: List[bool] = []
    half = (block - 1) / 2.0
    for bz in range(B):
        for by in range(B):
            for bx in range(B):
                s = 0.0
                cnt = 0
                x0, y0, z0 = bx * block, by * block, bz * block
                for dz in range(block):
                    for dy in range(block):
                        for dx in range(block):
                            c = (x0 + dx, y0 + dy, z0 + dz)
                            if c in values:
                                s += float(values[c])
                                cnt += 1
                cx = int(round(x0 + half))
                cy = int(round(y0 + half))
                cz = int(round(z0 + half))
                out_centers.append((cx, cy, cz))
                if cnt == 0:
                    out_vals.append(float("nan"))
                    out_mask.append(False)
                else:
                    out_vals.append(s / float(cnt))
                    out_mask.append(True)
    return out_vals, out_centers, out_mask


def _component_cross_corr(
    *,
    re_a: Sequence[float],
    im_a: Sequence[float],
    re_b: Sequence[float],
    im_b: Sequence[float],
    mask: Sequence[bool],
) -> float:
    cs = [
        abs(_corr_masked(re_a, re_b, mask)),
        abs(_corr_masked(re_a, im_b, mask)),
        abs(_corr_masked(im_a, re_b, mask)),
        abs(_corr_masked(im_a, im_b, mask)),
    ]
    return max(cs)


@dataclass(frozen=True)
class ChannelReport:
    name: str
    bit_index: int
    mu: float
    corr_reflect_y: float
    corr_with_turn: float


def _pairings(idxs: Sequence[int]) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    a, b, c, d = idxs
    return [((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c))]


def _render(
    *,
    centers: Sequence[Coord3],
    mask: Sequence[bool],
    b_vals: Sequence[Sequence[float]],
    t_vals: Sequence[float],
    pairing: Tuple[Tuple[int, int], Tuple[int, int]],
    out_png,
) -> None:
    import matplotlib

    matplotlib.use("Agg")  # type: ignore
    import matplotlib.pyplot as plt  # noqa: E402

    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401,E402

    def scatter(ax, vals: Sequence[float], title: str, cmap: str, vmin, vmax):
        xs: List[float] = []
        ys: List[float] = []
        zs: List[float] = []
        cs: List[float] = []
        for (x, y, z), v, ok in zip(centers, vals, mask):
            if not ok:
                continue
            xs.append(float(x))
            ys.append(float(y))
            zs.append(float(z))
            cs.append(float(v))
        p = ax.scatter(xs, ys, zs, c=cs, cmap=cmap, s=22, alpha=0.92, vmin=vmin, vmax=vmax, depthshade=False)
        ax.set_title(title, fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        ax.set_box_aspect((1, 1, 1))
        return p

    fig = plt.figure(figsize=(12.0, 8.6), dpi=180)
    gs = fig.add_gridspec(2, 3, wspace=0.10, hspace=0.10)

    axs = [fig.add_subplot(gs[r, c], projection="3d") for r in range(2) for c in range(3)]
    p0 = scatter(axs[0], b_vals[0], "b0 (suffix bit 6)  2x2x2 avg", "viridis", 0.0, 1.0)
    p1 = scatter(axs[1], b_vals[1], "b1 (suffix bit 7)  2x2x2 avg", "viridis", 0.0, 1.0)
    p2 = scatter(axs[2], b_vals[2], "b2 (suffix bit 8)  2x2x2 avg", "viridis", 0.0, 1.0)
    p3 = scatter(axs[3], b_vals[3], "b3 (suffix bit 9)  2x2x2 avg", "viridis", 0.0, 1.0)
    pt = scatter(axs[4], t_vals, "t (triple-product sign)  2x2x2 avg", "coolwarm", -1.0, 1.0)

    (i, j), (k, l) = pairing
    axs[5].remove()
    ax_txt = fig.add_subplot(gs[1, 2])
    ax_txt.axis("off")
    ax_txt.text(0.0, 0.88, "Chosen Higgs-like doublet (3D geometry):", fontsize=11, transform=ax_txt.transAxes)
    ax_txt.text(0.0, 0.68, f"H1 = b{i} + i b{j}", fontsize=11, transform=ax_txt.transAxes)
    ax_txt.text(0.0, 0.52, f"H2 = b{k} + i b{l}", fontsize=11, transform=ax_txt.transAxes)
    ax_txt.text(
        0.0,
        0.26,
        "3D is sparse: only the 2^10 prefix sites are occupied\non the 16^3 Hilbert screen; block averages use occupied sites.",
        fontsize=9,
        transform=ax_txt.transAxes,
    )

    fig.colorbar(p0, ax=axs[0], fraction=0.03, pad=0.01)
    fig.colorbar(p1, ax=axs[1], fraction=0.03, pad=0.01)
    fig.colorbar(p2, ax=axs[2], fraction=0.03, pad=0.01)
    fig.colorbar(p3, ax=axs[3], fraction=0.03, pad=0.01)
    fig.colorbar(pt, ax=axs[4], fraction=0.03, pad=0.01)

    fig.suptitle("m=10: 3D Hilbert screen (n=4) uplift → scalar channels → Higgs-like doublet", fontsize=12)
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    m_bits = 10
    n_bits = 4  # ceil(m/3)
    side = 1 << n_bits  # 16
    L = side - 1
    N = 1 << m_bits  # 1024
    cap = 1 << (3 * n_bits)  # 4096
    if N > cap:
        raise AssertionError("Need N <= 2^(3n).")

    coords: List[Coord3] = [tuple(int(v) for v in hilbert_index_to_coords(k, p=n_bits, n=3)) for k in range(N)]

    # Raw scalar channels on occupied sites.
    b_maps: List[Dict[Coord3, float]] = [dict() for _ in range(4)]
    for k, c in enumerate(coords):
        w = foldm.foldm(k, m_bits)
        suf = w[6:10]
        for j in range(4):
            b_maps[j][c] = 1.0 if suf[j] == "1" else 0.0

    # Parity-odd 3D turn scalar via triple product sign (4-point local pattern).
    t_map: Dict[Coord3, float] = {}
    t_seq: List[float] = [0.0 for _ in range(N)]
    for i in range(0, N - 3):
        p0 = coords[i]
        p1 = coords[i + 1]
        p2 = coords[i + 2]
        p3 = coords[i + 3]
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
        v3 = (p3[0] - p2[0], p3[1] - p2[1], p3[2] - p2[2])
        sgn = _triple_sign(v1, v2, v3)
        # Assign to the second point (a "central" site for this 4-tuple).
        t_map[p2] = sgn
        t_seq[i + 2] = sgn

    # Sanity: reflection flips orientation, so the triple-sign sequence should flip sign.
    coords_ref: List[Coord3] = [_reflect_y(c, L) for c in coords]
    t_seq_ref: List[float] = [0.0 for _ in range(N)]
    for i in range(0, N - 3):
        p0 = coords_ref[i]
        p1 = coords_ref[i + 1]
        p2 = coords_ref[i + 2]
        p3 = coords_ref[i + 3]
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
        v3 = (p3[0] - p2[0], p3[1] - p2[1], p3[2] - p2[2])
        t_seq_ref[i + 2] = _triple_sign(v1, v2, v3)
    corr_sanity = _corr(t_seq_ref[2:-2], [-x for x in t_seq[2:-2]])
    if corr_sanity < 0.99:
        raise AssertionError("3D turn-sign reflection sanity check failed.")

    # Coarse grain on 3D blocks.
    block = 2  # 2x2x2 -> 8^3 blocks
    b_vals: List[List[float]] = []
    centers: List[Coord3] = []
    mask: List[bool] = []
    for j in range(4):
        vals, cc, mk = _block_avg_sparse(values=b_maps[j], side=side, block=block)
        b_vals.append(vals)
        if j == 0:
            centers = cc
            mask = mk
    t_vals, _, t_mask = _block_avg_sparse(values=t_map, side=side, block=block)
    # Use union mask so we can correlate on blocks that have any data.
    mask_u = [bool(a or b) for a, b in zip(mask, t_mask)]

    # Reflection-evenness proxy for channels on the block grid:
    # build reflected arrays by reflecting block centers (y -> L-y) and matching values.
    # We'll compute correlations only on blocks where both are finite.
    B = side // block
    idx_by_center: Dict[Coord3, int] = {c: i for i, c in enumerate(centers)}
    centers_ref = [_reflect_y(c, L) for c in centers]
    ref_idx = [idx_by_center.get(c, -1) for c in centers_ref]

    def reflect_vals(vals: Sequence[float]) -> tuple[List[float], List[bool]]:
        out: List[float] = [float("nan") for _ in vals]
        ok: List[bool] = [False for _ in vals]
        for i, j in enumerate(ref_idx):
            if j < 0:
                continue
            out[i] = float(vals[j])
            ok[i] = True
        return out, ok

    reports: List[ChannelReport] = []
    for j in range(4):
        v = b_vals[j]
        v_ref, ok_map = reflect_vals(v)
        ok = [mk and okk and (not math.isnan(a)) and (not math.isnan(b)) for mk, okk, a, b in zip(mask_u, ok_map, v, v_ref)]
        corr_ref = _corr_masked(v, v_ref, ok)
        # Turn correlation on finite blocks.
        ok_t = [mk and (not math.isnan(a)) and (not math.isnan(tt)) for mk, a, tt in zip(mask_u, v, t_vals)]
        corr_turn = _corr_masked(v, t_vals, ok_t)
        # Mean on occupied blocks only.
        v_f = [float(a) for a, mk in zip(v, mask_u) if mk and (not math.isnan(a))]
        reports.append(ChannelReport(name=f"b{j}", bit_index=6 + j, mu=_mean(v_f) if v_f else 0.0, corr_reflect_y=corr_ref, corr_with_turn=corr_turn))

    # Choose pairing.
    best = None
    best_score = None
    idxs = [0, 1, 2, 3]
    for (a, b), (c, d) in _pairings(idxs):
        cross = _component_cross_corr(re_a=b_vals[a], im_a=b_vals[b], re_b=b_vals[c], im_b=b_vals[d], mask=mask_u)
        pen = 0.0
        for j in (a, b, c, d):
            pen += max(0.0, 0.90 - reports[j].corr_reflect_y) * 5.0
            pen += abs(reports[j].corr_with_turn) * 2.0
        score = cross + pen
        if best_score is None or score < best_score:
            best_score = score
            best = ((a, b), (c, d))
    if best is None or best_score is None:
        raise AssertionError("Failed to choose pairing.")

    out_base = figures_dir() / "adaptive" / "higgs_geometry"
    data_dir = out_base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_json = data_dir / "higgs_doublet_structure_m10_3d.json"
    out_png = out_base / "higgs_doublet_structure_m10_3d.png"

    payload = {
        "m": m_bits,
        "n3": n_bits,
        "side3": side,
        "N": N,
        "block": block,
        "sanity": {"corr_turn_reflect_y": corr_sanity},
        "channels": [{"name": r.name, "bit_index": r.bit_index, "mu": r.mu, "reflect_y_corr": r.corr_reflect_y, "corr_with_turn": r.corr_with_turn} for r in reports],
        "doublet": {"H1": {"re": best[0][0], "im": best[0][1]}, "H2": {"re": best[1][0], "im": best[1][1]}, "objective": best_score},
        "note": "3D is sparse: values are defined on the 2^m prefix sites of the 3D Hilbert scan; block averages use occupied sites.",
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_json.relative_to(out_json.parents[3])}")

    _render(centers=centers, mask=mask_u, b_vals=b_vals, t_vals=t_vals, pairing=best, out_png=out_png)
    print(f"Wrote {out_png.relative_to(out_png.parents[3])}")


if __name__ == "__main__":
    main()

