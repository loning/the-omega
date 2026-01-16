# -*- coding: utf-8 -*-
"""
Robustness / counterfactual addressing sweep for the Higgs-like doublet construction.

We sweep a bounded family of deterministic variants around the audited m=10 uplift:
  - 2D screen: (m,n)=(10,5), side=32
    addressing variants: Hilbert (canonical), Hilbert-y-reflect, Hilbert-reverse,
                         row-major (counterfactual), row-major-reverse
    coarse blocks: 2,4,8
  - 3D screen: (m,n3)=(10,4), side=16 (sparse occupancy of 2^10 sites)
    addressing variants: canonical, y-reflect, reverse
    coarse blocks: 1,2,4

For each setting, we recompute the deterministic doublet pairing selection and
report whether it matches the canonical audited pairing (up to pair ordering and
within-pair swap).

Outputs
  - sections/generated/higgs_doublet_robustness_rows.tex
  - sections/generated/higgs_doublet_robustness_summary.tex
  - figures/adaptive/higgs_geometry/higgs_doublet_robustness_sweep.png
  - figures/adaptive/higgs_geometry/data/higgs_doublet_robustness_sweep.json
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import exp_foldm_stats as foldm
import exp_hilbert_chirality_index as hil2d
from common_paths import figures_dir, generated_dir
from common_tex import write_lines
from hilbert_nd import hilbert_index_to_coords


Point2 = Tuple[int, int]
Coord3 = Tuple[int, int, int]


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else 0.0


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(x) * float(y) for x, y in zip(a, b))


def _corr(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or (not a):
        return 0.0
    ma = _mean(a)
    mb = _mean(b)
    da = [float(x) - ma for x in a]
    db = [float(y) - mb for y in b]
    va = _dot(da, da)
    vb = _dot(db, db)
    if va <= 0.0 or vb <= 0.0:
        return 0.0
    return _dot(da, db) / math.sqrt(va * vb)


def _flatten2(grid: List[List[float]]) -> List[float]:
    return [float(v) for row in grid for v in row]


def _reflect_y_grid(grid: List[List[float]]) -> List[List[float]]:
    # grid[y][x] -> reflect y
    return list(reversed(grid))


def _block_avg_2d(grid: List[List[float]], block: int) -> List[List[float]]:
    side = len(grid)
    if side == 0 or any(len(r) != side for r in grid):
        raise ValueError("grid must be non-empty square")
    if block <= 0 or (side % block) != 0:
        raise ValueError("block must divide side")
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


def _turn_sign_2d(path: Sequence[Point2], side: int) -> List[List[float]]:
    # Signed turn field on visited sites; endpoints 0.
    t: List[List[float]] = [[0.0 for _ in range(side)] for _ in range(side)]
    for i in range(1, len(path) - 1):
        x0, y0 = path[i - 1]
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        v1x, v1y = x1 - x0, y1 - y0
        v2x, v2y = x2 - x1, y2 - y1
        cross = v1x * v2y - v1y * v2x
        if cross > 0:
            sgn = 1.0
        elif cross < 0:
            sgn = -1.0
        else:
            sgn = 0.0
        t[y1][x1] = sgn
    return t


def _pairings4() -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    a, b, c, d = 0, 1, 2, 3
    return [((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c))]


def _canonicalize_pairing(p: Tuple[Tuple[int, int], Tuple[int, int]]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    (a, b), (c, d) = p
    p1 = tuple(sorted((int(a), int(b))))
    p2 = tuple(sorted((int(c), int(d))))
    return tuple(sorted((p1, p2)))  # type: ignore[return-value]


def _component_cross_corr(re_a: Sequence[float], im_a: Sequence[float], re_b: Sequence[float], im_b: Sequence[float]) -> float:
    cs = [
        abs(_corr(re_a, re_b)),
        abs(_corr(re_a, im_b)),
        abs(_corr(im_a, re_b)),
        abs(_corr(im_a, im_b)),
    ]
    return max(cs)


@dataclass(frozen=True)
class PairingScore:
    pairing: Tuple[Tuple[int, int], Tuple[int, int]]
    score: float
    cross: float
    parity_pen: float
    turn_pen: float


def _select_pairing_2d(b4: List[List[List[float]]], t4: List[List[float]]) -> PairingScore:
    t_vec = _flatten2(t4)
    # Penalize deviation from parity-even (corr near 1 under y-reflection) and correlation with parity-odd t.
    parity_pen = []
    turn_pen = []
    for j in range(4):
        v = _flatten2(b4[j])
        v_ref = _flatten2(_reflect_y_grid(b4[j]))
        parity_pen.append(1.0 - max(-1.0, min(1.0, _corr(v, v_ref))))  # want corr -> 1
        turn_pen.append(abs(_corr(v, t_vec)))  # want corr -> 0

    best: PairingScore | None = None
    for p in _pairings4():
        (i, j), (k, l) = p
        re_a = _flatten2(b4[i])
        im_a = _flatten2(b4[j])
        re_b = _flatten2(b4[k])
        im_b = _flatten2(b4[l])
        cross = _component_cross_corr(re_a, im_a, re_b, im_b)
        pen_par = (parity_pen[i] + parity_pen[j] + parity_pen[k] + parity_pen[l]) / 4.0
        pen_turn = (turn_pen[i] + turn_pen[j] + turn_pen[k] + turn_pen[l]) / 4.0
        score = cross + 0.65 * pen_par + 0.35 * pen_turn
        cand = PairingScore(pairing=p, score=score, cross=cross, parity_pen=pen_par, turn_pen=pen_turn)
        if best is None or cand.score < best.score:
            best = cand
    assert best is not None
    return best


def _coords_row_major_2d(n_bits: int) -> List[Point2]:
    side = 1 << n_bits
    return [(x, y) for y in range(side) for x in range(side)]


def _coords_row_major_reverse_2d(n_bits: int) -> List[Point2]:
    coords = _coords_row_major_2d(n_bits)
    return list(reversed(coords))


def _coords_hilbert_2d(n_bits: int) -> List[Point2]:
    return hil2d.hilbert_curve(n_bits)


def _coords_hilbert_reflecty_2d(n_bits: int) -> List[Point2]:
    side = 1 << n_bits
    L = side - 1
    return [hil2d.reflect_y(L, p) for p in hil2d.hilbert_curve(n_bits)]


def _coords_hilbert_reverse_2d(n_bits: int) -> List[Point2]:
    return list(reversed(hil2d.hilbert_curve(n_bits)))


def _build_fields_2d(*, m_bits: int, n_bits: int, coords: Sequence[Point2]) -> Tuple[List[List[List[float]]], List[List[float]]]:
    side = 1 << n_bits
    N = 1 << m_bits
    if len(coords) != N:
        raise ValueError("coords length mismatch")
    outs = foldm.cached_foldm_outputs(m_bits)
    if len(outs) != N:
        raise AssertionError("Foldm outputs length mismatch")

    b: List[List[List[float]]] = [[[0.0 for _ in range(side)] for _ in range(side)] for _ in range(4)]
    for k, (x, y) in enumerate(coords):
        w = outs[k]
        for j in range(4):
            b[j][y][x] = float(1 if w[6 + j] == "1" else 0)
    t = _turn_sign_2d(coords, side)
    return b, t


def _block_avg_sparse_3d(values: Dict[Coord3, float], side: int, block: int, *, empty_fill: float | None) -> Tuple[List[float], List[Coord3], List[bool]]:
    if side <= 0 or block <= 0 or (side % block) != 0:
        raise ValueError("block must divide side")
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
                    if empty_fill is None:
                        out_vals.append(float("nan"))
                        out_mask.append(False)
                    else:
                        out_vals.append(float(empty_fill))
                        out_mask.append(True)
                else:
                    out_vals.append(s / float(cnt))
                    out_mask.append(True)
    return out_vals, out_centers, out_mask


def _corr_masked(a: Sequence[float], b: Sequence[float], mask: Sequence[bool]) -> float:
    aa: List[float] = []
    bb: List[float] = []
    for x, y, ok in zip(a, b, mask):
        if ok and (not math.isnan(float(x))) and (not math.isnan(float(y))):
            aa.append(float(x))
            bb.append(float(y))
    if len(aa) < 2:
        return 0.0
    return _corr(aa, bb)


def _triple_sign(v1: Coord3, v2: Coord3, v3: Coord3) -> float:
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


def _turn_sign_3d(path: Sequence[Coord3]) -> Dict[Coord3, float]:
    # Parity-odd "turn" scalar at interior points i (uses i-1,i,i+1,i+2).
    t: Dict[Coord3, float] = {}
    for i in range(1, len(path) - 2):
        p0 = path[i - 1]
        p1 = path[i]
        p2 = path[i + 1]
        p3 = path[i + 2]
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
        v3 = (p3[0] - p2[0], p3[1] - p2[1], p3[2] - p2[2])
        t[p1] = _triple_sign(v1, v2, v3)
    return t


def _reflect_y_3d(c: Coord3, L: int) -> Coord3:
    x, y, z = c
    return (x, L - y, z)


def _build_fields_3d(
    *,
    m_bits: int,
    n_bits: int,
    coords: Sequence[Coord3],
) -> Tuple[List[Dict[Coord3, float]], Dict[Coord3, float]]:
    side = 1 << n_bits
    N = 1 << m_bits
    if len(coords) != N:
        raise ValueError("coords length mismatch")
    outs = foldm.cached_foldm_outputs(m_bits)

    b_maps: List[Dict[Coord3, float]] = [dict() for _ in range(4)]
    for k, c in enumerate(coords):
        w = outs[k]
        for j in range(4):
            b_maps[j][c] = float(1 if w[6 + j] == "1" else 0)
    t_map = _turn_sign_3d(coords)
    # Ensure every visited site has a defined value; endpoints default to 0.
    for c in coords:
        if c not in t_map:
            t_map[c] = 0.0
    return b_maps, t_map


def _select_pairing_3d(
    *,
    b_vals: List[List[float]],
    t_vals: List[float],
    mask: List[bool],
) -> PairingScore:
    # Parity-even proxy under y-reflection is approximated here by low correlation with the parity-odd turn field
    # plus low cross-correlation between complex components (masked).
    turn_pen = [abs(_corr_masked(b_vals[j], t_vals, mask)) for j in range(4)]
    best: PairingScore | None = None
    for p in _pairings4():
        (i, j), (k, l) = p
        cross = max(
            abs(_corr_masked(b_vals[i], b_vals[k], mask)),
            abs(_corr_masked(b_vals[i], b_vals[l], mask)),
            abs(_corr_masked(b_vals[j], b_vals[k], mask)),
            abs(_corr_masked(b_vals[j], b_vals[l], mask)),
        )
        pen_turn = (turn_pen[i] + turn_pen[j] + turn_pen[k] + turn_pen[l]) / 4.0
        # No separate parity term here; 3D reflection-evenness is audited elsewhere.
        score = cross + 0.45 * pen_turn
        cand = PairingScore(pairing=p, score=score, cross=cross, parity_pen=0.0, turn_pen=pen_turn)
        if best is None or cand.score < best.score:
            best = cand
    assert best is not None
    return best


@dataclass(frozen=True)
class Row:
    screen: str
    addressing: str
    block: int
    empty_fill: str  # "occ" or "zero" (3D only; 2D uses "full")
    pairing: Tuple[Tuple[int, int], Tuple[int, int]]
    pairing_canon: Tuple[Tuple[int, int], Tuple[int, int]]
    match_canon: bool
    score: float
    cross: float
    turn_pen: float


def _ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def _render_match_plot(rows: List[Row], out_png: Path) -> None:
    import matplotlib.pyplot as plt

    # Split 2D vs 3D and plot as a simple categorical grid.
    rows2 = [r for r in rows if r.screen == "2D"]
    rows3 = [r for r in rows if r.screen == "3D"]

    def plot_panel(ax, rows_panel: List[Row], title: str) -> None:
        if not rows_panel:
            ax.axis("off")
            return
        labels = [f"{r.addressing}|b{r.block}|{r.empty_fill}" for r in rows_panel]
        vals = [1.0 if r.match_canon else 0.0 for r in rows_panel]
        ax.bar(range(len(vals)), vals, color=["#2E7D32" if v > 0.5 else "#C62828" for v in vals])
        ax.set_ylim(0.0, 1.05)
        ax.set_yticks([0.0, 1.0])
        ax.set_yticklabels(["diff", "same"])
        ax.set_title(title, fontsize=10)
        ax.set_xticks(range(len(vals)))
        ax.set_xticklabels(labels, rotation=90, fontsize=7)
        ax.grid(axis="y", alpha=0.25)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12.5, 8.0), dpi=180, constrained_layout=True)
    plot_panel(ax1, rows2, "2D (m=10,n=5): pairing match vs canonical")
    plot_panel(ax2, rows3, "3D (m=10,n3=4): pairing match vs canonical")
    fig.suptitle("Higgs-like doublet robustness sweep (bounded family)", fontsize=12)
    _ensure_dir(out_png)
    fig.savefig(out_png)
    plt.close(fig)


def main() -> None:
    m_bits = 10

    # Canonical audited pairing from the Higgs-doublet interface (m=10): (0,3),(1,2)
    pairing_canon = _canonicalize_pairing(((0, 3), (1, 2)))

    rows: List[Row] = []

    # 2D sweep
    n2 = 5
    side2 = 1 << n2
    N = 1 << m_bits
    if side2 * side2 != N:
        raise AssertionError("Expected balanced 2D embedding at (m,n)=(10,5).")

    addr2: List[Tuple[str, Sequence[Point2]]] = [
        ("hilbert", _coords_hilbert_2d(n2)),
        ("hilbert_reflect_y", _coords_hilbert_reflecty_2d(n2)),
        ("hilbert_reverse", _coords_hilbert_reverse_2d(n2)),
        ("row_major", _coords_row_major_2d(n2)),
        ("row_major_reverse", _coords_row_major_reverse_2d(n2)),
    ]
    for name, coords in addr2:
        b_raw, t_raw = _build_fields_2d(m_bits=m_bits, n_bits=n2, coords=coords)
        for block in (2, 4, 8):
            b4 = [_block_avg_2d(b_raw[j], block) for j in range(4)]
            t4 = _block_avg_2d(t_raw, block)
            best = _select_pairing_2d(b4, t4)
            rows.append(
                Row(
                    screen="2D",
                    addressing=name,
                    block=block,
                    empty_fill="full",
                    pairing=_canonicalize_pairing(best.pairing),
                    pairing_canon=pairing_canon,
                    match_canon=(_canonicalize_pairing(best.pairing) == pairing_canon),
                    score=float(best.score),
                    cross=float(best.cross),
                    turn_pen=float(best.turn_pen),
                )
            )

    # 3D sweep (sparse)
    n3 = 4
    side3 = 1 << n3
    if side3 ** 3 < N:
        raise AssertionError("Expected 3D screen to have >= 2^m sites.")

    coords3_canon = [tuple(int(v) for v in hilbert_index_to_coords(k, p=n3, n=3)) for k in range(N)]  # type: ignore[misc]
    coords3_ref = [_reflect_y_3d(c, side3 - 1) for c in coords3_canon]
    coords3_rev = list(reversed(coords3_canon))
    addr3: List[Tuple[str, Sequence[Coord3]]] = [
        ("hilbert3d", coords3_canon),
        ("hilbert3d_reflect_y", coords3_ref),
        ("hilbert3d_reverse", coords3_rev),
    ]

    for name, coords in addr3:
        b_maps, t_map = _build_fields_3d(m_bits=m_bits, n_bits=n3, coords=coords)
        for block in (1, 2, 4):
            for empty_fill, empty_tag in ((None, "occ"), (0.0, "zero")):
                b_vals: List[List[float]] = []
                mask: List[bool] | None = None
                for j in range(4):
                    vals, _, msk = _block_avg_sparse_3d(b_maps[j], side3, block, empty_fill=empty_fill)
                    b_vals.append(vals)
                    if mask is None:
                        mask = msk
                assert mask is not None
                t_vals, _, msk_t = _block_avg_sparse_3d(t_map, side3, block, empty_fill=empty_fill)
                mask = [a and b for a, b in zip(mask, msk_t)]
                best = _select_pairing_3d(b_vals=b_vals, t_vals=t_vals, mask=mask)
                rows.append(
                    Row(
                        screen="3D",
                        addressing=name,
                        block=block,
                        empty_fill=empty_tag,
                        pairing=_canonicalize_pairing(best.pairing),
                        pairing_canon=pairing_canon,
                        match_canon=(_canonicalize_pairing(best.pairing) == pairing_canon),
                        score=float(best.score),
                        cross=float(best.cross),
                        turn_pen=float(best.turn_pen),
                    )
                )

    # Deterministic ordering in output tables.
    rows.sort(key=lambda r: (r.screen, r.addressing, r.block, r.empty_fill))

    # LaTeX rows
    tex_rows: List[str] = []
    for r in rows:
        pairing_tex = f"$\\{{\\{{{r.pairing[0][0]},{r.pairing[0][1]}\\}},\\{{{r.pairing[1][0]},{r.pairing[1][1]}\\}}\\}}$"
        ok = "yes" if r.match_canon else "no"
        tex_rows.append(
            f"{r.screen} & {r.addressing} & {r.block} & {r.empty_fill} & {pairing_tex} & {ok} & "
            f"{r.score:.4f} & {r.cross:.4f} & {r.turn_pen:.4f} \\\\"
        )
    write_lines(generated_dir() / "higgs_doublet_robustness_rows.tex", tex_rows)

    match_rate = sum(1 for r in rows if r.match_canon) / float(len(rows)) if rows else 0.0
    summary = [
        "\\noindent "
        "Robustness sweep for the uplift-derived Higgs-like doublet (interface): "
        "we recompute the deterministic pairing selection over a bounded family of "
        "addressing and coarse-graining variants around the audited $m=10$ instance. "
        f"The canonical pairing is $\\{{\\{{0,3\\}},\\{{1,2\\}}\\}}$, and the sweep match rate is {match_rate:.3f}. "
        "A mismatch under a counterfactual addressing basis is treated as an explicit sensitivity finding "
        "and is recorded in the table."
    ]
    write_lines(generated_dir() / "higgs_doublet_robustness_summary.tex", summary)

    # JSON
    out_json = figures_dir() / "adaptive" / "higgs_geometry" / "data" / "higgs_doublet_robustness_sweep.json"
    _ensure_dir(out_json)
    out_json.write_text(
        json.dumps(
            {
                "m_bits": m_bits,
                "pairing_canonical": pairing_canon,
                "rows": [r.__dict__ for r in rows],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    # Figure
    out_png = figures_dir() / "adaptive" / "higgs_geometry" / "higgs_doublet_robustness_sweep.png"
    _render_match_plot(rows, out_png)

    print("Wrote sections/generated/higgs_doublet_robustness_rows.tex")
    print("Wrote sections/generated/higgs_doublet_robustness_summary.tex")
    print(f"Wrote {out_png}")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()

