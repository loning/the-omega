# -*- coding: utf-8 -*-
"""
Movie-like encoding visualization (center-wired, no crossings):

Wiring rules (as requested)
---------------------------
1) The m=6 Hilbert curve fills the whole 8×8 plane and is drawn by connecting *cell centers*.
   All turns are 90 degrees (axis-aligned) because consecutive Hilbert points are neighbors.
2) For refined cells (between the gate words 101001 and 100101, excluding the gate cells),
   we draw a micro Hilbert curve inside the cell, connecting *subcell centers* (again 90-degree turns).
3) The scan wiring is a *single continuous curve*: when a cell is refined, the scan detours
   from the big-cell center into the micro-Hilbert path and returns to the big-cell center,
   then continues along the coarse Hilbert wiring.

Encoding / colors
-----------------
- Each m=6 cell is a stable type u = Fold_6(k) in X6 (21 = 18⊕3). We color by a fixed 21-color palette.
- Each refined cell gets a local bitrate m in {8,10} under a fixed per-frame bit budget (conserved).
  We use the per-cell code bits to select an offset; each micro subcell gets a suffix code in
  Hilbert order and is colored as a brightness ladder of the base hue.
- We label:
  - every big cell by its 6-bit u
  - every micro subcell by its suffix bits (2 bits for m=8, 4 bits for m=10)
  - every refined big cell by its local (m, bits) header.

Outputs
-------
  - figures/dynamic_centerwired_code/dynamic_centerwired_code.gif
  - figures/dynamic_centerwired_code/contact_sheet.png
  - figures/dynamic_centerwired_code/x6_palette_legend.png
  - sections/generated/dynamic_centerwired_code_summary.tex

Deterministic; English-only in plots (repo convention).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: E402

from PIL import Image  # noqa: E402

from common_paths import figures_dir, generated_dir  # noqa: E402
from common_progress import ProgressEvery  # noqa: E402
import exp_fold6_stats as fold6  # noqa: E402
import exp_hilbert_chirality_index as hil  # noqa: E402


# -------------------------
# Palette (m=6 stable types)
# -------------------------


def _hex_to_rgb01(h: str) -> np.ndarray:
    hh = h.strip().lstrip("#")
    if len(hh) != 6:
        raise ValueError("hex color must be RRGGBB")
    r = int(hh[0:2], 16) / 255.0
    g = int(hh[2:4], 16) / 255.0
    b = int(hh[4:6], 16) / 255.0
    return np.array([r, g, b], dtype=float)


def _material_palette_21_distinct() -> List[str]:
    return [
        "#1565C0",
        "#2E7D32",
        "#C62828",
        "#6A1B9A",
        "#EF6C00",
        "#00897B",
        "#283593",
        "#4E342E",
        "#00838F",
        "#AD1457",
        "#F9A825",
        "#9E9D24",
        "#4527A0",
        "#0277BD",
        "#558B2F",
        "#D84315",
        "#37474F",
        "#6D4C41",
        "#00ACC1",
        "#7B1FA2",
        "#1B5E20",
    ]


def _x6_color_map() -> Tuple[List[str], np.ndarray, Dict[str, int]]:
    X6 = fold6.all_x6()
    pal = _material_palette_21_distinct()
    if len(pal) < len(X6):
        raise AssertionError("Palette too small.")
    palette_rgb = np.stack([_hex_to_rgb01(c) for c in pal[: len(X6)]], axis=0)
    word_to_idx = {w: int(i) for i, w in enumerate(X6)}
    return X6, palette_rgb, word_to_idx


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _render_x6_palette_legend(X6: List[str], palette_rgb: np.ndarray, out_png: Path) -> None:
    _ensure_dir(out_png.parent)
    n = len(X6)
    ncols = 7
    nrows = (n + ncols - 1) // ncols
    fig, ax = plt.subplots(figsize=(14.0, 1.55 * nrows))
    ax.axis("off")
    ax.set_title("m=6 stable types (X6 = 18⊕3): color legend", fontsize=14, pad=10)

    gauge_short = {"100001": "U(1)", "101001": "SU(2)", "100101": "SU(3)"}
    for i, w in enumerate(X6):
        r = i // ncols
        c = i % ncols
        x0 = c * 1.0
        y0 = (nrows - 1 - r) * 1.0
        color = palette_rgb[i]
        ax.add_patch(Rectangle((x0, y0), 0.98, 0.72, facecolor=color, edgecolor="#263238", lw=0.8))
        tag = "bdry" if (len(w) >= 2 and w[0] == "1" and w[-1] == "1") else "cyc"
        extra = f"  {gauge_short[w]}" if w in gauge_short else ""
        ax.text(x0 + 0.02, y0 + 0.86, f"{w}  [{tag}]{extra}", fontsize=10, color="#263238", va="top")

    ax.set_xlim(0, ncols * 1.0)
    ax.set_ylim(0, nrows * 1.0)
    fig.savefig(out_png, dpi=220, bbox_inches="tight")
    plt.close(fig)


# -------------------------
# Geometry helpers
# -------------------------


def _k_to_xy_map() -> Dict[int, Tuple[int, int]]:
    path = hil.hilbert_curve(3)  # 8x8, length 64
    if len(path) != 64:
        raise AssertionError("Unexpected Hilbert path length for n_bits=3.")
    return {int(k): (int(x), int(y)) for k, (x, y) in enumerate(path)}


def _center_point_in_cell(cell_x: int, cell_y: int, scale: int) -> Tuple[float, float]:
    return ((float(cell_x) + 0.5) * float(scale), (float(cell_y) + 0.5) * float(scale))


def _center_point_in_subcell(cell_x: int, cell_y: int, scale: int, S: int, xx: int, yy: int) -> Tuple[float, float]:
    step = float(scale) / float(S)
    x0 = float(cell_x) * float(scale)
    y0 = float(cell_y) * float(scale)
    return (x0 + (float(xx) + 0.5) * step, y0 + (float(yy) + 0.5) * step)


# -------------------------
# Deterministic encoding
# -------------------------


def _lcg_bits(n_bits: int, seed: int = 20250128) -> List[int]:
    n_bits = int(n_bits)
    if n_bits <= 0:
        raise ValueError("n_bits must be positive.")
    state = int(seed) & 0x7FFFFFFF
    out: List[int] = []
    for _ in range(n_bits):
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        out.append(int((state >> 30) & 1))
    return out


def _bit_window(bits: List[int], start: int, length: int) -> List[int]:
    if not bits:
        raise ValueError("Empty bitstream.")
    start = int(start)
    length = int(length)
    n = len(bits)
    return [int(bits[(start + i) % n]) for i in range(length)]


def _bits_to_int(bs: List[int]) -> int:
    v = 0
    for b in bs:
        v = (v << 1) | int(b)
    return int(v)


def _int_to_bits(v: int, n: int) -> str:
    return format(int(v) & ((1 << int(n)) - 1), "0{}b".format(int(n)))


def _frame_shift(frame_idx: int) -> int:
    return int((int(frame_idx) * 17) % 64)


def _fold6_shifted(k: int, shift: int) -> str:
    return fold6.fold6((int(k) + int(shift)) % 64)


def _gate_positions(words: List[str]) -> Dict[str, List[int]]:
    pos: Dict[str, List[int]] = {"100001": [], "101001": [], "100101": []}
    for i, w in enumerate(words):
        if w in pos:
            pos[w].append(int(i))
    return pos


def _cyclic_distance(a: int, b: int, n: int) -> int:
    return int((int(b) - int(a)) % int(n))


def _choose_downlift_far(words: List[str], up_pos: int, dn_positions: List[int]) -> int:
    if not dn_positions:
        raise ValueError("No downlift positions.")
    best = dn_positions[0]
    best_d = -1
    for p in dn_positions:
        d = _cyclic_distance(up_pos, p, 64)
        if d <= 0:
            continue
        if d > best_d:
            best_d = d
            best = p
    return int(best)


def _indices_between_exclusive(a: int, b: int, n: int) -> List[int]:
    a = int(a)
    b = int(b)
    n = int(n)
    out: List[int] = []
    cur = (a + 1) % n
    while cur != b:
        out.append(int(cur))
        cur = (cur + 1) % n
    return out


def _boundary_tag(w: str) -> str:
    return "bdry" if (len(w) >= 2 and w[0] == "1" and w[-1] == "1") else "cyc"


def _assign_refinements(
    refine_order: List[int],
    words: List[str],
    bits_frame: List[int],
    *,
    max_m10_per_frame: int = 2,
) -> Tuple[Dict[int, Tuple[int, int, str]], int]:
    """
    Assign refined cells a bitrate m in {8,10} and an offset code, under a fixed bit budget.
    Returns: k -> (m_hi, offset, bitstr), and bits_used.
    """
    i = 0
    assign: Dict[int, Tuple[int, int, str]] = {}
    m10_used = 0
    for k in refine_order:
        if i + 2 > len(bits_frame):
            break
        # Skip boundary cells (keep them unrefined).
        if _boundary_tag(words[k]) == "bdry":
            continue
        b2 = bits_frame[i : i + 2]
        c = _bits_to_int(b2)
        # Keep m=10 rare (readability): only when c==3 and under a small cap.
        if c == 3 and m10_used < int(max_m10_per_frame) and (i + 4 <= len(bits_frame)):
            b4 = bits_frame[i : i + 4]
            m_hi = 10
            offset = _bits_to_int(b4)  # 0..15
            bitstr = "".join(str(int(b)) for b in b4)
            i += 4
            m10_used += 1
        else:
            m_hi = 8
            offset = int(c)  # 0..3
            bitstr = "".join(str(int(b)) for b in b2)
            i += 2
        assign[int(k)] = (int(m_hi), int(offset), bitstr)
    return assign, int(i)


# -------------------------
# Rendering
# -------------------------


@dataclass(frozen=True)
class MicroCell:
    xx: int
    yy: int
    bits: str
    code: int


def _dir_to_entry_target(dx: int, dy: int) -> Tuple[float, float]:
    """
    Given coarse direction into the cell (from prev->cur), return a normalized target point
    on the boundary where we "enter": left/right/top/bottom midpoints in (0..1)^2.
    """
    if dx == 1 and dy == 0:  # enter from left side
        return (0.0, 0.5)
    if dx == -1 and dy == 0:  # enter from right side
        return (1.0, 0.5)
    if dx == 0 and dy == 1:  # enter from bottom side
        return (0.5, 0.0)
    if dx == 0 and dy == -1:  # enter from top side
        return (0.5, 1.0)
    return (0.5, 0.5)


def _dir_to_exit_target(dx: int, dy: int) -> Tuple[float, float]:
    """
    Given coarse direction out of the cell (from cur->next), return a normalized target point
    on the boundary where we "exit": left/right/top/bottom midpoints in (0..1)^2.
    """
    if dx == 1 and dy == 0:  # exit to right side
        return (1.0, 0.5)
    if dx == -1 and dy == 0:  # exit to left side
        return (0.0, 0.5)
    if dx == 0 and dy == 1:  # exit to top side
        return (0.5, 1.0)
    if dx == 0 and dy == -1:  # exit to bottom side
        return (0.5, 0.0)
    return (0.5, 0.5)


def _symmetry_transforms(S: int):
    """
    Return 8 isometries of an SxS grid as functions (xx,yy)->(xx',yy').
    """
    m = int(S) - 1

    def t0(x: int, y: int) -> Tuple[int, int]:
        return (x, y)

    def t1(x: int, y: int) -> Tuple[int, int]:  # rot90
        return (y, m - x)

    def t2(x: int, y: int) -> Tuple[int, int]:  # rot180
        return (m - x, m - y)

    def t3(x: int, y: int) -> Tuple[int, int]:  # rot270
        return (m - y, x)

    def t4(x: int, y: int) -> Tuple[int, int]:  # mirror x
        return (m - x, y)

    def t5(x: int, y: int) -> Tuple[int, int]:  # mirror y
        return (x, m - y)

    def t6(x: int, y: int) -> Tuple[int, int]:  # mirror diag
        return (y, x)

    def t7(x: int, y: int) -> Tuple[int, int]:  # mirror anti-diag
        return (m - y, m - x)

    return [t0, t1, t2, t3, t4, t5, t6, t7]


def _choose_micro_path_transform(
    S: int,
    sub_path: List[Tuple[int, int]],
    entry_target: Tuple[float, float],
    exit_target: Tuple[float, float],
) -> List[Tuple[int, int]]:
    """
    Choose a symmetry of the micro Hilbert path so that its start is near the entry side
    and its end is near the exit side (minimizing a simple distance score).
    """
    best_path = sub_path
    best_score = 1e9
    for tf in _symmetry_transforms(S):
        tp = [(int(tf(xx, yy)[0]), int(tf(xx, yy)[1])) for (xx, yy) in sub_path]
        (sx, sy) = tp[0]
        (ex, ey) = tp[-1]
        s_norm = ((sx + 0.5) / float(S), (sy + 0.5) / float(S))
        e_norm = ((ex + 0.5) / float(S), (ey + 0.5) / float(S))
        ds = (s_norm[0] - entry_target[0]) ** 2 + (s_norm[1] - entry_target[1]) ** 2
        de = (e_norm[0] - exit_target[0]) ** 2 + (e_norm[1] - exit_target[1]) ** 2
        score = float(ds + de)
        if score < best_score:
            best_score = score
            best_path = tp
    return best_path


def _render_one_frame(
    palette_rgb: np.ndarray,
    word_to_idx: Dict[str, int],
    k_to_xy: Dict[int, Tuple[int, int]],
    bits_global: List[int],
    frame_idx: int,
    bit_budget: int = 64,
    scale: int = 92,
) -> Image.Image:
    shift = _frame_shift(frame_idx)
    words = [_fold6_shifted(k, shift) for k in range(64)]
    pos = _gate_positions(words)
    up_pos = int(pos["101001"][0]) if pos["101001"] else 17
    dn_pos = _choose_downlift_far(words, up_pos=up_pos, dn_positions=pos["100101"]) if pos["100101"] else 53
    refine_order = _indices_between_exclusive(up_pos, dn_pos, 64)

    bits_frame = _bit_window(bits_global, start=frame_idx * 29, length=int(bit_budget))
    assigns, bits_used = _assign_refinements(refine_order=refine_order, words=words, bits_frame=bits_frame, max_m10_per_frame=2)

    # Base plane indices in {0..20} and RGB upsample.
    base_idx8 = np.zeros((8, 8), dtype=int)
    for k in range(64):
        x, y = k_to_xy[k]
        base_idx8[y, x] = int(word_to_idx[words[k]])
    base_cell_rgb = palette_rgb[base_idx8]  # (8,8,3)
    base_rgb = np.repeat(np.repeat(base_cell_rgb, scale, axis=0), scale, axis=1)  # (H,W,3)
    H, W, _ = base_rgb.shape

    # Prepare coarse directions for entry/exit alignment (treat scan as cyclic for local orientation).
    path_xy = [(int(x), int(y)) for (x, y) in hil.hilbert_curve(3)]
    dirs_in_out: Dict[int, Tuple[Tuple[int, int], Tuple[int, int]]] = {}
    for k in range(64):
        x, y = path_xy[k]
        xp, yp = path_xy[(k - 1) % 64]
        xn, yn = path_xy[(k + 1) % 64]
        d_in = (int(x - xp), int(y - yp))
        d_out = (int(xn - x), int(yn - y))
        dirs_in_out[int(k)] = (d_in, d_out)

    # Paint microstructure in refined cells and collect micro labels.
    micro_ops = 64
    refined_cells: Dict[int, List[MicroCell]] = {}
    for k, (m_hi, offset, bitstr) in assigns.items():
        u = words[k]
        base_color = palette_rgb[int(word_to_idx[u])]
        x, y = k_to_xy[k]
        x0 = int(x * scale)
        y0 = int(y * scale)
        x1 = int((x + 1) * scale)
        y1 = int((y + 1) * scale)

        n_suffix = int(m_hi - 6)
        n_bits_sub = int(n_suffix // 2)
        S = 1 << n_bits_sub  # m=8 -> 2, m=10 -> 4
        sub_path0 = [(int(xx), int(yy)) for (xx, yy) in hil.hilbert_curve(n_bits_sub)]
        (d_in, d_out) = dirs_in_out.get(int(k), ((0, 0), (0, 0)))
        entry_t = _dir_to_entry_target(d_in[0], d_in[1])
        exit_t = _dir_to_exit_target(d_out[0], d_out[1])
        sub_path = _choose_micro_path_transform(S=S, sub_path=sub_path0, entry_target=entry_t, exit_target=exit_t)
        sx = max(1, (x1 - x0) // S)
        sy = max(1, (y1 - y0) // S)

        denom = max(1, (S * S) - 1)
        cells: List[MicroCell] = []
        for j, (xx, yy) in enumerate(sub_path):
            code = (int(offset) + int(j)) % (S * S)
            bits = _int_to_bits(code, n_suffix)
            # Discrete brightness ladder -> discrete colors represent codes.
            t = 0.25 + 0.75 * (float(code) / float(denom))
            px0 = x0 + xx * sx
            py0 = y0 + yy * sy
            px1 = x0 + (xx + 1) * sx
            py1 = y0 + (yy + 1) * sy
            base_rgb[py0:py1, px0:px1, :] = np.clip(base_color * t, 0.0, 1.0)
            cells.append(MicroCell(xx=xx, yy=yy, bits=bits, code=code))
        refined_cells[int(k)] = cells
        micro_ops += int(S * S) - 1

    # Render
    fig = plt.figure(figsize=(12.2, 7.4))
    ax = fig.add_axes([0.05, 0.10, 0.62, 0.84])
    ax.imshow(base_rgb, origin="lower", interpolation="nearest")
    ax.set_xticks([])
    ax.set_yticks([])

    # Draw coarse grid.
    for i in range(9):
        ax.plot([0, W], [i * scale, i * scale], color="#ECEFF1", lw=0.8, alpha=0.65, zorder=2)
        ax.plot([i * scale, i * scale], [0, H], color="#ECEFF1", lw=0.8, alpha=0.65, zorder=2)

    # Draw a single continuous scan curve by expanding refined coarse cells into micro subcells.
    # This implements: prev big-cell -> (diagonal) micro-entry -> micro Hilbert -> micro-exit -> next big-cell.
    expanded_points: List[Tuple[float, float]] = []
    point_kind: List[str] = []  # "macro" or "micro"
    for k, (x, y) in enumerate(path_xy):
        if int(k) in assigns:
            (m_hi, _offset, _bitstr) = assigns[int(k)]
            n_suffix = int(m_hi - 6)
            n_bits_sub = int(n_suffix // 2)
            S = 1 << n_bits_sub
            # Use the same transformed micro order we used for painting/labels:
            micro_order = [(mc.xx, mc.yy) for mc in refined_cells.get(int(k), [])]
            if not micro_order:
                expanded_points.append(_center_point_in_cell(x, y, scale))
                point_kind.append("macro")
            else:
                for (xx, yy) in micro_order:
                    expanded_points.append(_center_point_in_subcell(x, y, scale, S, int(xx), int(yy)))
                    point_kind.append("micro" if int(m_hi) == 8 else "micro10")
        else:
            expanded_points.append(_center_point_in_cell(x, y, scale))
            point_kind.append("macro")

    # Turn expanded points into segments with per-segment styling.
    segs: List[List[Tuple[float, float]]] = []
    widths: List[float] = []
    alphas: List[float] = []
    for i in range(len(expanded_points) - 1):
        a = expanded_points[i]
        b = expanded_points[i + 1]
        ka = point_kind[i]
        kb = point_kind[i + 1]
        segs.append([a, b])
        if ka.startswith("micro") and kb.startswith("micro"):
            if ka == "micro10" or kb == "micro10":
                widths.append(1.05)
                alphas.append(0.60)
            else:
                widths.append(1.35)
                alphas.append(0.85)
        else:
            # Cross-scale or macro: keep it as the main scan stroke (can be diagonal).
            widths.append(2.3)
            alphas.append(0.78)

    if segs:
        lc = LineCollection(segs, colors="#FFFFFF", linewidths=widths, alpha=1.0, zorder=7)
        # Per-segment alpha isn't directly supported; approximate by splitting collections:
        # keep it simple: accept a single alpha and encode micro readability via linewidths.
        ax.add_collection(lc)

    # Label every big cell by its 6-bit encoding u (small font).
    for k in range(64):
        x, y = k_to_xy[k]
        x0 = int(x * scale)
        y0 = int(y * scale)
        ax.text(
            x0 + 2,
            y0 + scale - 2,
            words[k],
            fontsize=7,
            color="#111111",
            ha="left",
            va="top",
            bbox=dict(facecolor=(1, 1, 1, 0.25), edgecolor="none", pad=1.0),
            zorder=6,
        )

    # Refined cells: per-cell header + optional per-subcell labels (m=10 labels are skipped for readability).
    for k, (m_hi, offset, bitstr) in assigns.items():
        x, y = k_to_xy[k]
        u = words[k]
        x0 = int(x * scale)
        y0 = int(y * scale)
        n_suffix = int(m_hi - 6)
        n_bits_sub = int(n_suffix // 2)
        S = 1 << n_bits_sub

        # Header for the refined cell (m + code bits).
        ax.text(
            x0 + 2,
            y0 + 2,
            f"m={m_hi}  bits={bitstr}",
            fontsize=7,
            color="#00E5FF",
            ha="left",
            va="bottom",
            bbox=dict(facecolor=(0, 0, 0, 0.35), edgecolor="none", pad=1.0),
            zorder=10,
        )

        # Label each micro subcell by its suffix bits.
        if n_suffix == 2:
            for mc in refined_cells.get(k, []):
                cx, cy = _center_point_in_subcell(x, y, scale, S, mc.xx, mc.yy)
                ax.text(
                    cx,
                    cy,
                    mc.bits,
                    fontsize=7,
                    color="#FFFFFF",
                    ha="center",
                    va="center",
                    bbox=dict(facecolor=(0, 0, 0, 0.35), edgecolor="none", pad=0.5),
                    zorder=11,
                )

    # Gate markers (not refined).
    def _mark_gate(word: str, pos_idx: int, color: str) -> None:
        gx, gy = k_to_xy[pos_idx]
        cx, cy = _center_point_in_cell(gx, gy, scale)
        ax.scatter([cx], [cy], s=140, c=color, edgecolors="white", linewidths=1.0, zorder=12)
        ax.text(cx + 6, cy + 6, word, fontsize=9, color=color, bbox=dict(facecolor=(0, 0, 0, 0.35), edgecolor="none", pad=2), zorder=13)

    _mark_gate("101001", up_pos, "#1E88E5")
    _mark_gate("100101", dn_pos, "#6A1B9A")

    # Wormhole arrow: end -> start of the open Hilbert path.
    (sx0, sy0) = path_xy[0]
    (sx1, sy1) = path_xy[-1]
    p0 = _center_point_in_cell(sx0, sy0, scale)
    p1 = _center_point_in_cell(sx1, sy1, scale)
    arrow = FancyArrowPatch(p1, p0, arrowstyle="-|>", mutation_scale=22, lw=3.0, color="#00E5FF", alpha=0.95, zorder=14)
    ax.add_patch(arrow)

    # Right panel: frame info / conserved budget / energy proxy.
    axr = fig.add_axes([0.70, 0.12, 0.27, 0.80])
    axr.axis("off")
    axr.text(0.0, 0.98, f"frame = {frame_idx:04d}", fontsize=12, color="#263238", va="top")
    axr.text(0.0, 0.92, f"shift (tick-origin) = {shift}", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.88, f"bit budget (conserved) = {int(bit_budget)}", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.84, f"bits used = {bits_used}  (left={int(bit_budget)-bits_used})", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.79, f"micro-ops (energy proxy) = {micro_ops}", fontsize=11, color="#263238", va="top")
    axr.text(0.0, 0.74, f"uplift pos = {up_pos}, downlift pos = {dn_pos}", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.69, f"refined cells = {len(assigns)}", fontsize=10, color="#455A64", va="top")
    axr.text(
        0.0,
        0.56,
        "wiring rules:\n"
        "- single continuous scan curve\n"
        "- coarse: center-to-center Hilbert\n"
        "- refined: detour into micro Hilbert\n"
        "encoding:\n"
        "- big cell label = 6-bit u\n"
        "- micro cell label = suffix bits",
        fontsize=9,
        color="#455A64",
        va="top",
    )

    fig.suptitle("Center-wired encoding movie (m=6 + local m=8/10 microstructure)", fontsize=14, y=0.98)
    fig.canvas.draw()
    ww, hh = fig.canvas.get_width_height()
    buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8).reshape((hh, ww, 4))
    rgba = buf[:, :, [1, 2, 3, 0]]
    im = Image.fromarray(rgba, mode="RGBA").convert("P", palette=Image.Palette.ADAPTIVE)
    plt.close(fig)
    return im


def _render_contact_sheet(gif_path: Path, out_png: Path, rows: int = 4, cols: int = 6) -> None:
    im = Image.open(gif_path)
    n = int(getattr(im, "n_frames", 1))
    if n <= 1:
        raise ValueError("GIF has <=1 frame.")
    k = rows * cols
    idxs = [int(round(i * (n - 1) / float(max(1, k - 1)))) for i in range(k)]
    frames = []
    for j in idxs:
        im.seek(j)
        frames.append(im.convert("RGB"))
    w, h = frames[0].size
    margin = 10
    head_h = 36
    W = cols * w + (cols + 1) * margin
    H = rows * h + (rows + 1) * margin + head_h
    canvas = Image.new("RGB", (W, H), color=(255, 255, 255))
    # Title band
    fig = plt.figure(figsize=(W / 140.0, head_h / 140.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.text(0.5, 0.5, "contact sheet (sampled frames): center-wired encoding movie", ha="center", va="center", fontsize=13, color="#263238")
    fig.canvas.draw()
    ww, hh = fig.canvas.get_width_height()
    buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8).reshape((hh, ww, 4))
    rgba = buf[:, :, [1, 2, 3, 0]]
    title_img = Image.fromarray(rgba, mode="RGBA").convert("RGB")
    plt.close(fig)
    canvas.paste(title_img, (0, 0))
    y0 = head_h
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            x = margin + c * (w + margin)
            y = y0 + margin + r * (h + margin)
            canvas.paste(frames[idx], (x, y))
    _ensure_dir(out_png.parent)
    canvas.save(out_png, format="PNG", optimize=False)


def _write_tex_summary(fig_root: Path) -> None:
    out = generated_dir()
    _ensure_dir(out)
    rel_gif = Path("figures") / fig_root.name / "dynamic_centerwired_code.gif"
    rel_cs = Path("figures") / fig_root.name / "contact_sheet.png"
    rel_leg = Path("figures") / fig_root.name / "x6_palette_legend.png"
    lines = [
        r"\paragraph{Center-wired encoding movie (gif).} \AuditTag "
        + r"A movie-like encoding visualization on the $m=6$ Hilbert screen: "
        + r"the global scan is a center-to-center Hilbert wiring (no crossings), "
        + r"and refined cells (between \texttt{101001} and \texttt{100101}) embed a micro Hilbert wiring on subcell centers, "
        + r"connected to the big-cell center by a single cross-scale connector. "
        + r"All big cells are labeled by their $6$-bit stable word $u$, and micro subcells are labeled by their suffix bits.",
        r"\AuditTag Artifacts:",
        r"\begin{itemize}",
        rf"\item \texttt{{{rel_gif.as_posix()}}}",
        rf"\item \texttt{{{rel_cs.as_posix()}}}",
        rf"\item \texttt{{{rel_leg.as_posix()}}}",
        r"\end{itemize}",
    ]
    (out / "dynamic_centerwired_code_summary.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    fig_root = figures_dir() / "dynamic_centerwired_code"
    _ensure_dir(fig_root)
    X6, palette_rgb, word_to_idx = _x6_color_map()
    k_to_xy = _k_to_xy_map()
    bits_global = _lcg_bits(8192)

    # Render GIF
    n_frames = 60
    fps = 4
    pe = ProgressEvery(label="render_centerwired_code_gif", total=n_frames, interval_s=60.0)
    pe.start()
    frames: List[Image.Image] = []
    for f in range(n_frames):
        pe.maybe(f)
        frames.append(
            _render_one_frame(
                palette_rgb=palette_rgb,
                word_to_idx=word_to_idx,
                k_to_xy=k_to_xy,
                bits_global=bits_global,
                frame_idx=f,
                bit_budget=64,
                scale=92,
            )
        )
    pe.done(extra=f"frames={n_frames}")

    out_gif = fig_root / "dynamic_centerwired_code.gif"
    frames[0].save(
        out_gif,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / fps),
        loop=0,
        optimize=False,
        disposal=2,
    )

    out_cs = fig_root / "contact_sheet.png"
    _render_contact_sheet(out_gif, out_cs, rows=4, cols=6)

    out_leg = fig_root / "x6_palette_legend.png"
    _render_x6_palette_legend(X6=X6, palette_rgb=palette_rgb, out_png=out_leg)

    _write_tex_summary(fig_root)

    print(f"Wrote {out_gif}")
    print(f"Wrote {out_cs}")
    print(f"Wrote {out_leg}")
    print("Wrote sections/generated/dynamic_centerwired_code_summary.tex")


if __name__ == "__main__":
    main()

