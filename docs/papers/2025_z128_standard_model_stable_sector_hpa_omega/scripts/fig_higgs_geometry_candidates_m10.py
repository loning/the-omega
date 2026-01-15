# -*- coding: utf-8 -*-
"""
Geometry-first search for Higgs-like scalar candidates at the m=10 uplift.

Context (paper semantics)
  - Higgs is not a primitive stable type at m=6; scalar behavior is expected to
    appear under uplift/coarse graining (Prop. scalar_sector_closed).
  - This script does NOT assert an identification. It only exports geometric
    descriptors of the Fold_m preimages on a balanced 2D Hilbert screen and
    ranks stable words by parity-even symmetry proxies.

Reproducibility
  - No external parameters.
  - Deterministic outputs under the fixed (m,n) = (10,5) balanced 2D embedding.

Outputs
  - figures/adaptive/higgs_geometry/data/higgs_geometry_m10_ranked.json
  - figures/adaptive/higgs_geometry/data/higgs_uplift_texture_m10.json
  - figures/adaptive/higgs_geometry/higgs_geometry_candidates_m10.png
  - figures/adaptive/higgs_geometry/higgs_uplift_texture_m10.png
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Set, Tuple

import exp_foldm_stats as foldm
import exp_hilbert_chirality_index as hil
from common_paths import figures_dir


Point = Tuple[int, int]


def _jaccard(a: Set[Point], b: Set[Point]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a.intersection(b))
    union = len(a.union(b))
    return float(inter) / float(union)


def _reflect_x(L: int, p: Point) -> Point:
    x, y = p
    return (L - x, y)


def _reflect_y(L: int, p: Point) -> Point:
    return hil.reflect_y(L, p)


def _rotate_180(L: int, p: Point) -> Point:
    x, y = p
    return (L - x, L - y)


def _transpose(p: Point) -> Point:
    x, y = p
    return (y, x)


def _bbox(points: Sequence[Point]) -> Tuple[int, int, int, int]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _perimeter_4nbr(point_set: Set[Point]) -> int:
    per = 0
    for (x, y) in point_set:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y + dy) not in point_set:
                per += 1
    return per


def _cov_eigs(points: Sequence[Point]) -> Tuple[float, float, float, float]:
    # Returns (mx, my, eig_min, eig_max) for the 2x2 covariance matrix.
    n = float(len(points))
    mx = sum(float(x) for x, _ in points) / n
    my = sum(float(y) for _, y in points) / n
    vx = sum((float(x) - mx) ** 2 for x, _ in points) / n
    vy = sum((float(y) - my) ** 2 for _, y in points) / n
    cxy = sum((float(x) - mx) * (float(y) - my) for x, y in points) / n
    tr = vx + vy
    det = vx * vy - cxy * cxy
    disc = max(0.0, tr * tr - 4.0 * det)
    s = math.sqrt(disc)
    e1 = 0.5 * (tr - s)
    e2 = 0.5 * (tr + s)
    return mx, my, min(e1, e2), max(e1, e2)


@dataclass(frozen=True)
class GeoRow:
    m: int
    n: int
    w: str
    prefix6: str
    is_carryover_6pad: bool
    g: int
    area: int
    perimeter: int
    bbox_w: int
    bbox_h: int
    bbox_area: int
    fill: float
    mx: float
    my: float
    anisotropy: float
    sym_x: float
    sym_y: float
    sym_r180: float
    sym_t: float
    scalar_sym: float
    score: float


def _geo_for_word(*, w: str, points: List[Point], L: int, m_bits: int, n_bits: int) -> GeoRow:
    s: Set[Point] = set(points)
    area = len(points)
    per = _perimeter_4nbr(s)
    x0, y0, x1, y1 = _bbox(points)
    bw = x1 - x0 + 1
    bh = y1 - y0 + 1
    barea = bw * bh
    fill = float(area) / float(barea) if barea > 0 else 0.0
    mx, my, e_min, e_max = _cov_eigs(points)
    anis = 0.0
    if e_max > 0.0:
        anis = 1.0 - float(e_min) / float(e_max)

    sx = _jaccard(s, {_reflect_x(L, p) for p in s})
    sy = _jaccard(s, {_reflect_y(L, p) for p in s})
    sr = _jaccard(s, {_rotate_180(L, p) for p in s})
    st = _jaccard(s, {_transpose(p) for p in s})

    scalar_sym = (sx + sy + sr) / 3.0

    # A simple composite score: symmetry first, then compactness, then isotropy.
    # Perimeter enters weakly to prefer smooth/compact shapes at fixed area.
    score = 10.0 * scalar_sym + 2.0 * fill + 0.5 * (1.0 - anis) + 0.1 * (1.0 / (1.0 + float(per)))

    return GeoRow(
        m=m_bits,
        n=n_bits,
        w=w,
        prefix6=w[:6],
        is_carryover_6pad=w.endswith("0" * (m_bits - 6)),
        g=area,
        area=area,
        perimeter=per,
        bbox_w=bw,
        bbox_h=bh,
        bbox_area=barea,
        fill=fill,
        mx=mx,
        my=my,
        anisotropy=anis,
        sym_x=sx,
        sym_y=sy,
        sym_r180=sr,
        sym_t=st,
        scalar_sym=scalar_sym,
        score=score,
    )


def _to_jsonable(rows: Sequence[GeoRow]) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for r in rows:
        out.append(
            {
                "m": r.m,
                "n": r.n,
                "w": r.w,
                "prefix6": r.prefix6,
                "is_carryover_6pad": r.is_carryover_6pad,
                "g": r.g,
                "area": r.area,
                "perimeter": r.perimeter,
                "bbox": {"w": r.bbox_w, "h": r.bbox_h, "area": r.bbox_area, "fill": r.fill},
                "centroid": {"x": r.mx, "y": r.my},
                "shape": {"anisotropy": r.anisotropy},
                "symmetry": {
                    "reflect_x": r.sym_x,
                    "reflect_y": r.sym_y,
                    "rotate_180": r.sym_r180,
                    "transpose": r.sym_t,
                    "scalar_sym": r.scalar_sym,
                },
                "score": r.score,
            }
        )
    return out


def _mean(xs: Sequence[float]) -> float:
    if not xs:
        raise ValueError("mean() requires a non-empty list.")
    return sum(xs) / float(len(xs))


def _var_pop(xs: Sequence[float]) -> float:
    if not xs:
        raise ValueError("var() requires a non-empty list.")
    m = _mean(xs)
    return _mean([(x - m) ** 2 for x in xs])


def _block_avgs_grid(grid: List[List[float]], *, block: int) -> List[List[float]]:
    side = len(grid)
    if side == 0 or any(len(row) != side for row in grid):
        raise ValueError("grid must be a non-empty square matrix.")
    if block <= 0 or (side % block) != 0:
        raise ValueError("block must be positive and divide side length.")
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


def _render_uplift_texture(
    *,
    suffix_weight_grid: List[List[float]],
    block4_grid: List[List[float]],
    out_png,
) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), dpi=180)
    ax0, ax1 = axes
    im0 = ax0.imshow(suffix_weight_grid, cmap="viridis", interpolation="nearest")
    ax0.set_title("m=10,n=5: suffix-4 Hamming weight per site", fontsize=9)
    ax0.set_axis_off()
    fig.colorbar(im0, ax=ax0, fraction=0.046, pad=0.04)

    im1 = ax1.imshow(block4_grid, cmap="viridis", interpolation="nearest")
    ax1.set_title("4x4 block averages (coarse scalar field)", fontsize=9)
    ax1.set_axis_off()
    fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)

    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)


def _render_top_grid(
    *,
    rows: Sequence[GeoRow],
    points_by_w: Dict[str, List[Point]],
    n_bits: int,
    out_png,
    top_k: int = 24,
) -> None:
    import matplotlib.pyplot as plt

    side = 1 << n_bits
    k = min(top_k, len(rows))
    cols = 6
    rows_n = (k + cols - 1) // cols
    fig, axes = plt.subplots(rows_n, cols, figsize=(cols * 2.2, rows_n * 2.2), dpi=180)
    if rows_n == 1:
        axes = [axes]  # type: ignore[assignment]
    axes_flat = [ax for row in axes for ax in (row if isinstance(row, Iterable) else [row])]

    for i, ax in enumerate(axes_flat):
        ax.set_axis_off()
        if i >= k:
            continue
        r = rows[i]
        pts = points_by_w[r.w]
        grid = [[0 for _ in range(side)] for _ in range(side)]
        for x, y in pts:
            grid[y][x] = 1
        ax.imshow(grid, cmap="gray_r", interpolation="nearest", vmin=0, vmax=1)
        ax.set_title(
            f"w={r.w}\n"
            f"g={r.g}, sym={r.scalar_sym:.3f}\n"
            f"score={r.score:.3f}",
            fontsize=7,
        )

    fig.suptitle("m=10, n=5: Fold_m preimage geometry ranked by parity-even symmetry proxies", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out_png)
    plt.close(fig)


def main() -> None:
    m_bits = 10
    n_bits = 5  # balanced 2D: m=2n
    N = 1 << m_bits
    side = 1 << n_bits
    if N != side * side:
        raise AssertionError("Expected balanced 2D embedding: 2^m == (2^n)^2.")
    L = side - 1

    path = hil.hilbert_curve(n_bits)
    if len(path) != N:
        raise AssertionError("Unexpected Hilbert path length.")

    # Build point clouds for each stable word w in X_m.
    points_by_w: Dict[str, List[Point]] = {}
    # Also export a grid-level "uplift texture" derived from the suffix (new microstructure).
    # This matches the scalar-sector narrative: scalars appear as parity-even coarse observables.
    w_grid: List[List[str]] = [["" for _ in range(side)] for _ in range(side)]
    suffix_weight_grid: List[List[float]] = [[0.0 for _ in range(side)] for _ in range(side)]
    is_carry_grid: List[List[int]] = [[0 for _ in range(side)] for _ in range(side)]
    for k, (x, y) in enumerate(path):
        w = foldm.foldm(k, m_bits)
        points_by_w.setdefault(w, []).append((x, y))
        w_grid[y][x] = w
        suf = w[6:]
        suffix_weight_grid[y][x] = float(suf.count("1"))
        is_carry_grid[y][x] = 1 if w.endswith("0" * (m_bits - 6)) else 0

    # Sanity: compare against enumerated X_m.
    Xm = foldm.all_xm(m_bits)
    if set(points_by_w.keys()) != set(Xm):
        missing = sorted(set(Xm) - set(points_by_w.keys()))
        extra = sorted(set(points_by_w.keys()) - set(Xm))
        raise AssertionError(f"X_m mismatch at m={m_bits}. missing={missing[:10]}, extra={extra[:10]}")

    rows: List[GeoRow] = []
    for w in Xm:
        pts = points_by_w[w]
        rows.append(_geo_for_word(w=w, points=pts, L=L, m_bits=m_bits, n_bits=n_bits))

    rows.sort(key=lambda r: (r.score, r.scalar_sym, r.fill, -r.anisotropy, -r.area), reverse=True)

    out_base = figures_dir() / "adaptive" / "higgs_geometry"
    data_dir = out_base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_json = data_dir / "higgs_geometry_m10_ranked.json"
    out_json.write_text(json.dumps(_to_jsonable(rows), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_json.relative_to(out_json.parents[3])}")

    # Uplift texture export (grid-level geometry for further inspection).
    block2 = _block_avgs_grid(suffix_weight_grid, block=2)
    block4 = _block_avgs_grid(suffix_weight_grid, block=4)
    block8 = _block_avgs_grid(suffix_weight_grid, block=8)

    texture = {
        "m": m_bits,
        "n": n_bits,
        "side": side,
        "definition": {
            "site_value": "Hamming weight of suffix bits w[6:10] (new microstructure at m=10 relative to m=6).",
            "carryover_flag": "1 iff w endswith 0000 (canonical 6->10 padding).",
            "coarse_graining": "block averages over 2x2, 4x4, 8x8 blocks on the Hilbert grid.",
        },
        "grid": {
            "w": w_grid,
            "suffix_weight": suffix_weight_grid,
            "is_carryover_6pad": is_carry_grid,
        },
        "blocks": {
            "2": {"grid": block2, "mu": _mean([v for row in block2 for v in row]), "var": _var_pop([v for row in block2 for v in row])},
            "4": {"grid": block4, "mu": _mean([v for row in block4 for v in row]), "var": _var_pop([v for row in block4 for v in row])},
            "8": {"grid": block8, "mu": _mean([v for row in block8 for v in row]), "var": _var_pop([v for row in block8 for v in row])},
        },
    }
    out_texture = data_dir / "higgs_uplift_texture_m10.json"
    out_texture.write_text(json.dumps(texture, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_texture.relative_to(out_texture.parents[3])}")

    out_png = out_base / "higgs_geometry_candidates_m10.png"
    _render_top_grid(rows=rows, points_by_w=points_by_w, n_bits=n_bits, out_png=out_png, top_k=24)
    print(f"Wrote {out_png.relative_to(out_png.parents[3])}")

    out_tex_png = out_base / "higgs_uplift_texture_m10.png"
    _render_uplift_texture(
        suffix_weight_grid=suffix_weight_grid,
        block4_grid=block4,
        out_png=out_tex_png,
    )
    print(f"Wrote {out_tex_png.relative_to(out_tex_png.parents[3])}")


if __name__ == "__main__":
    main()

