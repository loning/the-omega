# -*- coding: utf-8 -*-
"""
Movie-like encoding visualization (center-wired, no crossings):

Wiring rules (as requested)
---------------------------
1) The m=6 Hilbert curve fills the whole 8x8 plane and is drawn by connecting *cell centers*.
   All turns are 90 degrees (axis-aligned) because consecutive Hilbert points are neighbors.
2) For refined cells (between the gate words 101001 and 100101, excluding the gate cells),
   we draw a micro Hilbert curve inside the cell, connecting *subcell centers* (also 90-degree turns).
3) Same-m wiring uses only 90/180-degree segments (no diagonal lines).
   Cross-m wiring (m=6 <-> m=8/10) uses the shortest diagonal connector to preserve the coarse direction.
4) The spatial bottom-left and bottom-right coarse cells are fixed to 100001.
5) If a segment choice would self-intersect, we backtrack and try rotated/mirrored Hilbert
   micro-orders (and alternate connector routings). If exhaustive search fails, we treat it
   as a *data constraint violation* that depends only on the m uplift/downlift pattern.

Encoding / colors
-----------------
- Each m=6 cell is a stable type u = Fold_6(k) in X6 (21 = 18+3). We color by a fixed 21-color palette.
- Each refined cell gets a local bitrate m in {8,10} under a fixed per-frame bit budget (conserved).
  We use the per-cell code bits to select an offset; each micro subcell gets a suffix code in
  Hilbert order and is colored as a brightness ladder of the base hue.
- We label:
  - every big cell by its 6-bit u
  - every micro subcell by its full m-bit word (prefix inherits the m=6 stable type)
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
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np  # type: ignore

import matplotlib  # type: ignore

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # type: ignore # noqa: E402
from matplotlib.collections import LineCollection  # type: ignore # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # type: ignore # noqa: E402

from PIL import Image  # type: ignore # noqa: E402

from common_paths import figures_dir, generated_dir  # noqa: E402
from common_progress import ProgressEvery  # noqa: E402
import exp_fold6_stats as fold6  # noqa: E402
import exp_foldm_stats as foldm  # noqa: E402
import exp_hilbert_chirality_index as hil  # noqa: E402

from hilbert_scan_codec import SelfCodecSpec, SelfDescribingHilbertCodec, zeckendorf_word6  # noqa: E402


# Cache a wiring-feasible m-profile (data) once found.
_CACHED_M_BY_K_CENTER_GRAPH: Dict[Tuple[int, int], Dict[int, int]] = {}


def _m_schedule_fixed() -> Dict[int, int]:
    """
    User-specified m uplift/downlift schedule (by coarse scan index k):
      - k=18 uplift to m=8
      - k=20 uplift to m=10
      - k=23 downlift to m=8
      - k=27 downlift to m=6

    We interpret this as piecewise-constant on k:
      - 18..19 : m=8
      - 20..22 : m=10
      - 23..26 : m=8
      - 27..52 : m=6
    Outside the refined span, m is macro (6) by construction.
    """
    m_by_k: Dict[int, int] = {}
    for k in range(18, 53):
        if 18 <= k <= 19:
            m_by_k[int(k)] = 8
        elif 20 <= k <= 22:
            m_by_k[int(k)] = 10
        elif 23 <= k <= 26:
            m_by_k[int(k)] = 8
        else:
            m_by_k[int(k)] = 6
    return m_by_k

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


def _descendants_unique(u6: str, m_hi: int, *, avoid_word: Optional[str] = None) -> List[str]:
    """
    Return unique admissible descendants in X_m with prefix u6 (Fold_6 fiber).
    Ordered by suffix code (then lexicographic) for deterministic display.
    """
    outs_hi = foldm.cached_foldm_outputs(m_hi)
    uniq: Dict[str, None] = {}
    for k, w_hi in enumerate(outs_hi):
        if avoid_word is not None and w_hi == avoid_word:
            continue
        if foldm.foldm(k, 6) == u6:
            uniq[w_hi] = None
    if not uniq:
        raise ValueError(f"No descendants for u6={u6}, m={m_hi}.")

    def sort_key(w: str) -> Tuple[int, str]:
        suffix = w[6:]
        return (int(suffix, 2) if suffix else 0, w)

    return sorted(uniq.keys(), key=sort_key)


def _render_x6_palette_legend(X6: List[str], palette_rgb: np.ndarray, out_png: Path) -> None:
    _ensure_dir(out_png.parent)
    n = len(X6)
    row_h = 3.0
    w_base = 2.2
    w_m8 = 1.8
    w_m10 = 1.8
    w_list = 6.6
    gap = 0.45
    top_pad = 2.0
    total_w = w_base + w_m8 + w_m10 + w_list + 3 * gap
    total_h = top_pad + n * row_h
    fig, ax = plt.subplots(figsize=(16.5, 0.30 * total_h))
    ax.axis("off")
    ax.set_xlim(0, total_w)
    ax.set_ylim(0, total_h)
    ax.set_title("m=6 stable types with m=8/m=10 descendants (prefix inheritance)", fontsize=13, pad=10)

    ax.text(0.0, total_h - 0.35, "descendants keep the first 6 bits = u6", fontsize=9, color="#455A64", va="top")
    ax.text(0.05, total_h - 0.75, "m=6 (u6)", fontsize=9, color="#263238", va="top")
    ax.text(w_base + gap + 0.05, total_h - 0.75, "m=8 descendants", fontsize=9, color="#263238", va="top")
    ax.text(w_base + gap + w_m8 + gap + 0.05, total_h - 0.75, "m=10 descendants", fontsize=9, color="#263238", va="top")
    x_list = w_base + gap + w_m8 + gap + w_m10 + gap
    ax.text(x_list + 0.05, total_h - 0.75, "unique suffix list", fontsize=9, color="#263238", va="top")

    gauge_short = {"100001": "U(1)", "101001": "SU(2)", "100101": "SU(3)"}

    def descendants_for(u6: str, m_hi: int, count: int) -> List[str]:
        avoid = _downlift_marker_for_m(m_hi)
        pool = _descendants_unique(u6, m_hi, avoid_word=avoid)
        if not pool:
            raise ValueError(f"No descendants for u6={u6}, m={m_hi}.")
        offset = int(u6, 2) % len(pool)
        return [pool[(offset + i) % len(pool)] for i in range(int(count))]

    def suffix_list(words: List[str], per_line: int) -> str:
        tokens = [w[6:] for w in words]
        lines = [" ".join(tokens[i : i + per_line]) for i in range(0, len(tokens), per_line)]
        return "\n".join(lines)

    for i, w in enumerate(X6):
        y0 = total_h - top_pad - (i + 1) * row_h
        color = palette_rgb[i]
        tag = "bdry" if (len(w) >= 2 and w[0] == "1" and w[-1] == "1") else "cyc"
        extra = f"  {gauge_short[w]}" if w in gauge_short else ""

        ax.add_patch(Rectangle((0.0, y0 + 0.05), w_base - 0.1, row_h - 0.1, facecolor=color, edgecolor="#263238", lw=0.8))
        ax.text(0.06, y0 + row_h - 0.12, f"{w}  [{tag}]{extra}", fontsize=8.5, color="#263238", va="top")

        m8_words = descendants_for(w, 8, 4)
        m10_words = descendants_for(w, 10, 16)
        uniq8 = _descendants_unique(w, 8, avoid_word=_downlift_marker_for_m(8))
        uniq10 = _descendants_unique(w, 10, avoid_word=_downlift_marker_for_m(10))

        cell8 = row_h / 2.0
        x8 = w_base + gap
        for idx, w8 in enumerate(m8_words):
            r = 1 - (idx // 2)
            c = idx % 2
            x = x8 + c * cell8
            y = y0 + r * cell8
            suffix = w8[6:]
            code = _bits_to_int([int(b) for b in suffix]) if suffix else 0
            denom = 3
            t = 0.25 + 0.75 * (float(code) / float(denom))
            ax.add_patch(Rectangle((x, y), cell8 - 0.02, cell8 - 0.02, facecolor=np.clip(color * t, 0.0, 1.0), edgecolor="#263238", lw=0.35))
            ax.text(x + 0.5 * cell8, y + 0.5 * cell8, w8, fontsize=6, color="#FFFFFF", ha="center", va="center")

        cell10 = row_h / 4.0
        x10 = w_base + gap + w_m8 + gap
        for idx, w10 in enumerate(m10_words):
            r = 3 - (idx // 4)
            c = idx % 4
            x = x10 + c * cell10
            y = y0 + r * cell10
            suffix = w10[6:]
            code = _bits_to_int([int(b) for b in suffix]) if suffix else 0
            denom = 15
            t = 0.25 + 0.75 * (float(code) / float(denom))
            ax.add_patch(Rectangle((x, y), cell10 - 0.01, cell10 - 0.01, facecolor=np.clip(color * t, 0.0, 1.0), edgecolor="#263238", lw=0.30))
            ax.text(
                x + 0.5 * cell10,
                y + 0.5 * cell10,
                _format_micro_label(w10),
                fontsize=4.3,
                color="#FFFFFF",
                ha="center",
                va="center",
            )

        list_text = "m8: " + suffix_list(uniq8, per_line=8) + "\n" + "m10: " + suffix_list(uniq10, per_line=4)
        ax.text(
            x_list + 0.05,
            y0 + row_h - 0.12,
            list_text,
            fontsize=6.0,
            color="#455A64",
            va="top",
        )

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


def _corner_indices() -> Tuple[int, int]:
    path = hil.hilbert_curve(3)
    idx = {(int(x), int(y)): int(k) for k, (x, y) in enumerate(path)}
    if (0, 0) not in idx or (7, 0) not in idx:
        raise AssertionError("Corner indices not found in Hilbert path.")
    return int(idx[(0, 0)]), int(idx[(7, 0)])


def _center_point_in_cell(cell_x: int, cell_y: int, scale: int) -> Tuple[float, float]:
    return ((float(cell_x) + 0.5) * float(scale), (float(cell_y) + 0.5) * float(scale))


def _center_point_in_subcell(cell_x: int, cell_y: int, scale: int, S: int, xx: int, yy: int) -> Tuple[float, float]:
    step = float(scale) / float(S)
    x0 = float(cell_x) * float(scale)
    y0 = float(cell_y) * float(scale)
    return (x0 + (float(xx) + 0.5) * step, y0 + (float(yy) + 0.5) * step)


def _grid_params(scale: int, s_max: int) -> Tuple[float, int]:
    micro = float(scale) / float(s_max)
    gmax = int(8 * int(s_max) * 2)
    return micro, gmax


def _to_grid(pt: Tuple[float, float], scale: int, s_max: int) -> Tuple[int, int]:
    micro, _gmax = _grid_params(scale, s_max)
    gx = int(round((float(pt[0]) / micro) * 2.0))
    gy = int(round((float(pt[1]) / micro) * 2.0))
    return (int(gx), int(gy))


def _from_grid(gp: Tuple[int, int], scale: int, s_max: int) -> Tuple[float, float]:
    micro, _gmax = _grid_params(scale, s_max)
    return (float(gp[0]) * micro / 2.0, float(gp[1]) * micro / 2.0)


def _edge_key(a: Tuple[int, int], b: Tuple[int, int]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    return (a, b) if a <= b else (b, a)


def _bfs_route(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    blocked_nodes: set[Tuple[int, int]],
    used_edges: set[Tuple[Tuple[int, int], Tuple[int, int]]],
    *,
    bounds: Tuple[int, int, int, int],
) -> Optional[List[Tuple[int, int]]]:
    from collections import deque

    (minx, maxx, miny, maxy) = bounds
    q = deque([start])
    prev: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
    while q:
        x, y = q.popleft()
        if (x, y) == goal:
            path: List[Tuple[int, int]] = []
            cur: Optional[Tuple[int, int]] = (x, y)
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            path.reverse()
            return path
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if nx < minx or nx > maxx or ny < miny or ny > maxy:
                continue
            nb = (int(nx), int(ny))
            if nb in blocked_nodes and nb != goal:
                continue
            ek = _edge_key((x, y), nb)
            if ek in used_edges:
                continue
            if nb in prev:
                continue
            prev[nb] = (x, y)
            q.append(nb)
    return None


def _route_grid_shortest(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    blocked_nodes: set[Tuple[int, int]],
    used_edges: set[Tuple[Tuple[int, int], Tuple[int, int]]],
    *,
    grid_max: int,
) -> Optional[List[Tuple[int, int]]]:
    if start == goal:
        return [start]
    sx, sy = start
    gx, gy = goal
    margin = 2
    while True:
        minx = max(0, min(sx, gx) - margin)
        maxx = min(grid_max, max(sx, gx) + margin)
        miny = max(0, min(sy, gy) - margin)
        maxy = min(grid_max, max(sy, gy) + margin)
        path = _bfs_route(start, goal, blocked_nodes, used_edges, bounds=(minx, maxx, miny, maxy))
        if path is not None:
            return path
        if minx == 0 and maxx == grid_max and miny == 0 and maxy == grid_max:
            return None
        margin += 2


def _point_on_segment(
    a: Tuple[float, float],
    p: Tuple[float, float],
    b: Tuple[float, float],
    *,
    eps: float = 1e-6,
) -> bool:
    return _orientation(a, p, b, eps) == 0 and _on_segment(a, p, b, eps)


def _segment_hits_any_center(
    a: Tuple[float, float],
    b: Tuple[float, float],
    centers: List[Tuple[float, float]],
    *,
    allow_endpoints: Tuple[Tuple[float, float], Tuple[float, float]],
    eps: float = 1e-6,
) -> bool:
    """
    Return True if segment (a,b) passes through the center of any cell/subcell other than endpoints.
    This prevents "cutting through" other centers, matching the center-wired constraint.
    """
    ea, eb = allow_endpoints
    for c in centers:
        if _pt_eq(c, ea, eps) or _pt_eq(c, eb, eps):
            continue
        if _pt_eq(c, a, eps) or _pt_eq(c, b, eps):
            continue
        if _point_on_segment(a, c, b, eps=eps):
            return True
    return False


def _route_hits_any_center(
    route: List[Tuple[float, float]],
    centers: List[Tuple[float, float]],
    *,
    allow_endpoints: Tuple[Tuple[float, float], Tuple[float, float]],
    eps: float = 1e-6,
) -> bool:
    if len(route) < 2:
        return False
    for i in range(len(route) - 1):
        if _segment_hits_any_center(route[i], route[i + 1], centers, allow_endpoints=allow_endpoints, eps=eps):
            return True
    return False


def _wiring_m_constraints_text() -> str:
    """
    A practical, checkable constraint on the data for a guaranteed one-stroke, non-crossing,
    center-wired Hilbert drawing.

    Key idea: the wiring geometry depends only on the *m uplift/downlift pattern* (where the scan
    switches resolutions), not on the actual bit payloads.

    Constraint (strong microblock alignment):
      - m switches are allowed only at boundaries between whole Hilbert microblocks.
      - At fixed local m, each refined coarse cell must emit a full microblock of length 2^(m-6),
        i.e. it fully populates a 2^((m-6)/2) x 2^((m-6)/2) subgrid in Hilbert order.
      - Therefore: no partial microblocks and no mid-cell m switches.
    """
    return (
        "Wiring constraint (depends only on m uplift/downlift): "
        "m switches must be aligned to whole Hilbert microblocks; "
        "at fixed m each refined coarse cell must emit a full microblock of length 2^(m-6) "
        "(fully populating its 2^((m-6)/2)x2^((m-6)/2) subgrid). "
        "No partial microblocks and no mid-cell m switches. "
        "Additionally (practical planarity constraint): along the refined scan, "
        "the m-profile should be unimodal (at most one 8->10 uplift run and at most one 10->8 downlift run), "
        "i.e. the number of switches in the sequence m(k) is <= 2 and there are no isolated single-cell runs."
    )


def _m_profile_stats(refined: List[int], m_by_k: Dict[int, int]) -> Tuple[List[int], int, List[int]]:
    """
    Return (m_seq, n_switches, run_lengths) for the refined scan indices.
    """
    m_seq = [int(m_by_k.get(int(k), 8)) for k in refined]
    n_switches = sum(1 for i in range(len(m_seq) - 1) if int(m_seq[i]) != int(m_seq[i + 1]))
    run_lengths: List[int] = []
    if not m_seq:
        return (m_seq, 0, run_lengths)
    cur = m_seq[0]
    r = 1
    for i in range(1, len(m_seq)):
        if m_seq[i] == cur:
            r += 1
        else:
            run_lengths.append(int(r))
            cur = m_seq[i]
            r = 1
    run_lengths.append(int(r))
    return (m_seq, int(n_switches), run_lengths)


def _m_profile_is_wiring_friendly(refined: List[int], m_by_k: Dict[int, int]) -> bool:
    """
    A conservative check: allow at most two switches and forbid isolated runs (length==1).
    This is a data constraint that depends only on the uplift/downlift pattern (m(k)).
    """
    _m_seq, n_switches, run_lengths = _m_profile_stats(refined, m_by_k)
    if n_switches > 2:
        return False
    if any(int(r) <= 1 for r in run_lengths):
        return False
    return True


def _search_refinement_pattern_center_graph(
    *,
    refined_span: List[int],
    max_refined_len: int,
    dirs_in_out: Dict[int, Tuple[Tuple[int, int], Tuple[int, int]]],
    scale: int,
) -> Dict[int, int]:
    """
    Search a refinement pattern (m_by_k over refined_span) that admits a strict center-graph,
    non-self-intersecting one-stroke wiring under the user rules:
      - nodes are centers
      - same-m edges: axis-aligned only
      - cross-m edges: direct diagonal
      - no intermediate routing

    We restrict the search space to a single contiguous refined block in the span:
      m=8 on [a..b], m=6 otherwise.
    Returns a mapping k->m (for k in refined_span) for the first feasible pattern found.
    """
    refined_span = [int(k) for k in refined_span]
    n = len(refined_span)
    max_refined_len = int(max(0, min(int(max_refined_len), n)))
    if n <= 0:
        return {}

    # A cheap geometric feasibility predicate (no drawing) based on local port choices:
    # We attempt wiring with m=8 microblocks (S=2) only, using backtracking over micro orders.
    # This is deterministic and fast for small blocks.

    # Precompute candidate micro orders for S=2 for each k (independent of data payload).
    S = 2
    sub_path0 = [(int(xx), int(yy)) for (xx, yy) in hil.hilbert_curve(1)]  # 2x2 length 4
    orders_by_k: Dict[int, List[List[Tuple[int, int]]]] = {}
    for k in refined_span:
        (d_in, d_out) = dirs_in_out.get(int(k), ((0, 0), (0, 0)))
        orders_by_k[int(k)] = _candidate_micro_orders_for_cell(S=S, n_bits_sub=1, d_in=d_in, d_out=d_out)[:8]

    def try_pattern(m_by_k: Dict[int, int]) -> bool:
        # Build per-coarse-cell sequences:
        # - if m(k)=6: visit only the coarse cell center (macro)
        # - if m(k)=8: visit only the 2x2 subcell centers (micro) in a Hilbert order variant
        #
        # Cross-level (m differs) edges must be straight diagonal segments.
        eps = 1e-6
        state = _WireState(wire_points=[], wire_kind=[], segments=[])

        # Precompute all centers used (macro for m=6 cells; micro for m=8 cells).
        centers_all: List[Tuple[float, float]] = []
        path_xy = [(int(x), int(y)) for (x, y) in hil.hilbert_curve(3)]
        for kk, (x, y) in enumerate(path_xy):
            if int(kk) in m_by_k and int(m_by_k[int(kk)]) == 8:
                for xx in range(2):
                    for yy in range(2):
                        centers_all.append(_center_point_in_subcell(x, y, scale, 2, xx, yy))
            else:
                centers_all.append(_center_point_in_cell(x, y, scale))

        def axis_aligned(a: Tuple[float, float], b: Tuple[float, float]) -> bool:
            return abs(a[0] - b[0]) <= eps or abs(a[1] - b[1]) <= eps

        def diagonal(a: Tuple[float, float], b: Tuple[float, float]) -> bool:
            return abs(a[0] - b[0]) > eps and abs(a[1] - b[1]) > eps

        def can_add(a: Tuple[float, float], b: Tuple[float, float], same_m: bool) -> bool:
            if same_m:
                if not axis_aligned(a, b):
                    return False
            else:
                if not diagonal(a, b):
                    return False
            if _segment_hits_any_center(a, b, centers_all, allow_endpoints=(a, b), eps=eps):
                return False
            if not _segment_is_clear_allow_endpoint_touches(a, b, state.segments, allow_touch_points=(a, b), eps=eps):
                return False
            return True

        # Depth-first over refined cells only (coarse scan order), choosing micro order per refined cell.
        # Non-refined cells have fixed macro-only node.
        chosen_order: Dict[int, int] = {}

        def expand_cell(kk: int) -> Tuple[List[Tuple[float, float]], List[str]]:
            x, y = path_xy[kk]
            if int(kk) not in m_by_k or int(m_by_k[int(kk)]) != 8:
                return ([_center_point_in_cell(x, y, scale)], ["macro"])
            ord_idx = int(chosen_order.get(int(kk), 0))
            ord_xy = orders_by_k[int(kk)][ord_idx]
            pts = [_center_point_in_subcell(x, y, scale, 2, xx, yy) for (xx, yy) in ord_xy]
            return (pts, ["micro"] * len(pts))

        refined_cells = [k for k in refined_span if int(m_by_k.get(int(k), 6)) == 8]
        # Map refined cell index in scan to its position for recursion:
        refined_in_scan = [int(k) for k in range(64) if int(k) in refined_cells]

        # Pre-seed chosen_order with 0.
        for kk in refined_in_scan:
            chosen_order[int(kk)] = 0

        # Build full polyline points for a given chosen_order and check incrementally.
        # We backtrack over micro order choices only; macro sequence fixed.
        def walk_from_scratch() -> bool:
            state.wire_points.clear()
            state.wire_kind.clear()
            state.segments.clear()
            prev_pt: Optional[Tuple[float, float]] = None
            prev_kind: Optional[str] = None
            for kk in range(64):
                pts, kinds = expand_cell(kk)
                for idx, p in enumerate(pts):
                    if prev_pt is None:
                        state.wire_points.append(p)
                        state.wire_kind.append(kinds[idx])
                        prev_pt = p
                        prev_kind = kinds[idx]
                        continue
                    same_m = _kind_to_m(str(prev_kind)) == _kind_to_m(str(kinds[idx]))
                    if not can_add(prev_pt, p, same_m=same_m):
                        return False
                    _append_route(state, [prev_pt, p], kind_from=str(prev_kind), kind_to=str(kinds[idx]))
                    prev_pt = p
                    prev_kind = kinds[idx]
            return True

        # Backtracking over refined cells.
        def dfs(i: int) -> bool:
            if i >= len(refined_in_scan):
                return walk_from_scratch()
            kk = refined_in_scan[i]
            opts = orders_by_k[int(kk)]
            for oi in range(len(opts)):
                chosen_order[int(kk)] = int(oi)
                # Quick prune: if the micro-start diagonal from macro hits other micro centers in that cell,
                # the full walk will fail; let walk_from_scratch catch it.
                if dfs(i + 1):
                    return True
            return False

        return dfs(0)

    # Try small blocks first (find any feasible data quickly), then grow.
    for L in range(1, max_refined_len + 1):
        for start in range(0, n - L + 1):
            m_by_k = {int(k): 6 for k in refined_span}
            for j in range(start, start + L):
                m_by_k[int(refined_span[j])] = 8
            if try_pattern(m_by_k):
                return m_by_k

    # Fallback: nothing refined.
    return {int(k): 6 for k in refined_span}

def _pt_eq(a: Tuple[float, float], b: Tuple[float, float], eps: float = 1e-6) -> bool:
    return abs(a[0] - b[0]) <= eps and abs(a[1] - b[1]) <= eps


def _seg_len(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return float(math.hypot(b[0] - a[0], b[1] - a[1]))


def _orientation(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float], eps: float = 1e-6) -> int:
    v = (b[1] - a[1]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[1] - a[1])
    if abs(v) <= eps:
        return 0
    return 1 if v > 0 else -1


def _on_segment(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float], eps: float = 1e-6) -> bool:
    return (
        min(a[0], c[0]) - eps <= b[0] <= max(a[0], c[0]) + eps
        and min(a[1], c[1]) - eps <= b[1] <= max(a[1], c[1]) + eps
    )


@dataclass
class _WireState:
    wire_points: List[Tuple[float, float]]
    wire_kind: List[str]
    segments: List[Tuple[Tuple[float, float], Tuple[float, float]]]


def _append_route(
    state: _WireState,
    route: List[Tuple[float, float]],
    *,
    kind_from: str,
    kind_to: str,
) -> Tuple[int, int]:
    """
    Append a polyline `route` to the wiring state.
    Assumes route[0] equals state.wire_points[-1] (or state is empty).
    Returns (n_points_added, n_segments_added) for backtracking.
    """
    if len(route) < 2:
        return (0, 0)
    if not state.wire_points:
        state.wire_points.append(route[0])
        state.wire_kind.append(kind_from)
    n_points_added = 0
    n_segs_added = 0
    for j in range(1, len(route)):
        a = route[j - 1]
        b = route[j]
        if _pt_eq(a, b):
            continue
        state.segments.append((a, b))
        n_segs_added += 1
        state.wire_points.append(b)
        state.wire_kind.append(kind_to if j == len(route) - 1 else kind_from)
        n_points_added += 1
    return (n_points_added, n_segs_added)


def _pop_route(state: _WireState, n_points_added: int, n_segs_added: int) -> None:
    if n_segs_added > 0:
        del state.segments[-n_segs_added:]
    if n_points_added > 0:
        del state.wire_points[-n_points_added:]
        del state.wire_kind[-n_points_added:]


@dataclass
class _WireGridState:
    """
    Grid-based self-avoiding wiring state (no edge reuse, no node reuse),
    where plotting is done by converting grid nodes back to XY.
    """

    wire_grid: List[Tuple[int, int]]
    wire_points: List[Tuple[float, float]]
    wire_kind: List[str]
    used_nodes: set[Tuple[int, int]]
    used_edges: set[Tuple[Tuple[int, int], Tuple[int, int]]]


def _append_grid_route(
    state: _WireGridState,
    route: List[Tuple[int, int]],
    *,
    kind_from: str,
    kind_to: str,
    scale: int,
    s_max: int,
) -> Tuple[int, int, int]:
    """
    Append a grid-node route to the wiring state.
    Returns (n_grid_nodes_added, n_used_nodes_added, n_used_edges_added) for backtracking.
    """
    if len(route) < 2:
        return (0, 0, 0)
    if not state.wire_grid:
        state.wire_grid.append(route[0])
        state.wire_points.append(_from_grid(route[0], scale, s_max))
        state.wire_kind.append(kind_from)
        state.used_nodes.add(route[0])
    n_grid_added = 0
    n_nodes_added = 0
    n_edges_added = 0
    for j in range(1, len(route)):
        a = route[j - 1]
        b = route[j]
        if a == b:
            continue
        ek = _edge_key(a, b)
        state.used_edges.add(ek)
        n_edges_added += 1
        if b not in state.used_nodes:
            state.used_nodes.add(b)
            n_nodes_added += 1
        state.wire_grid.append(b)
        state.wire_points.append(_from_grid(b, scale, s_max))
        state.wire_kind.append(kind_to if j == len(route) - 1 else kind_from)
        n_grid_added += 1
    return (n_grid_added, n_nodes_added, n_edges_added)


def _pop_grid_route(state: _WireGridState, n_grid_added: int, n_nodes_added: int, n_edges_added: int) -> None:
    if n_edges_added > 0:
        # Remove last n_edges_added edges by recomputing from tail segments.
        # (We don't keep an edge stack, so do a safe reconstruction for the trimmed suffix.)
        # Fast enough for our sizes.
        pass
    if n_grid_added > 0:
        del state.wire_grid[-n_grid_added:]
        del state.wire_points[-n_grid_added:]
        del state.wire_kind[-n_grid_added:]
    if n_nodes_added > 0:
        # Rebuild used_nodes from current wire_grid (safe and deterministic).
        state.used_nodes = set(state.wire_grid)
    if n_edges_added > 0:
        # Rebuild used_edges from current wire_grid (safe and deterministic).
        used: set[Tuple[Tuple[int, int], Tuple[int, int]]] = set()
        for i in range(len(state.wire_grid) - 1):
            used.add(_edge_key(state.wire_grid[i], state.wire_grid[i + 1]))
        state.used_edges = used


def _candidate_micro_orders_for_cell(
    *,
    S: int,
    n_bits_sub: int,
    d_in: Tuple[int, int],
    d_out: Tuple[int, int],
) -> List[List[Tuple[int, int]]]:
    """
    Enumerate candidate micro Hilbert orders for an SxS subgrid.
    Try all symmetries and both directions (forward/reversed), then sort by an alignment score.
    """
    sub_path0 = [(int(xx), int(yy)) for (xx, yy) in hil.hilbert_curve(n_bits_sub)]
    entry_t = _dir_to_entry_target(d_in[0], d_in[1])
    exit_t = _dir_to_exit_target(d_out[0], d_out[1])

    scored: List[Tuple[float, List[Tuple[int, int]]]] = []
    for tf in _symmetry_transforms(S):
        tp = [(int(tf(xx, yy)[0]), int(tf(xx, yy)[1])) for (xx, yy) in sub_path0]
        for direction in (1, -1):
            pp = tp if direction == 1 else list(reversed(tp))
            (sx, sy) = pp[0]
            (sx1, sy1) = pp[1] if len(pp) > 1 else pp[0]
            (ex, ey) = pp[-1]
            (ex1, ey1) = pp[-2] if len(pp) > 1 else pp[-1]
            s_norm = ((sx + 0.5) / float(S), (sy + 0.5) / float(S))
            e_norm = ((ex + 0.5) / float(S), (ey + 0.5) / float(S))
            ds = math.hypot(s_norm[0] - entry_t[0], s_norm[1] - entry_t[1])
            de = math.hypot(e_norm[0] - exit_t[0], e_norm[1] - exit_t[1])
            step_in = (int(sx1 - sx), int(sy1 - sy))
            step_out = (int(ex - ex1), int(ey - ey1))
            penalty = 0.0
            if d_in != (0, 0) and step_in != d_in:
                penalty += 0.8
            if d_out != (0, 0) and step_out != d_out:
                penalty += 0.8
            scored.append((float(ds + de + penalty), pp))
    scored.sort(key=lambda t: float(t[0]))
    return [p for (_s, p) in scored]


def _connector_candidates(
    a: Tuple[float, float],
    b: Tuple[float, float],
    *,
    same_m: bool,
    ca: Tuple[int, int],
    cb: Tuple[int, int],
    scale: int,
) -> List[List[Tuple[float, float]]]:
    """
    Candidate connector polylines from a->b.
    - Same-m: prefer axis-aligned (including boundary-guided).
    - Cross-m: allow diagonal direct link first, then axis-aligned alternatives.
    """
    if ca == cb:
        return [[a, b]]
    candidates: List[List[Tuple[float, float]]] = []
    eps = 1e-6
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    diag = abs(dx) > eps and abs(dy) > eps
    if not diag:
        candidates.append([a, b])
    else:
        if not same_m:
            candidates.append([a, b])
        p_h = (b[0], a[1])
        p_v = (a[0], b[1])
        candidates.append([a, p_h, b])
        candidates.append([a, p_v, b])
    candidates.append(_boundary_route(a, b, ca, cb, scale))
    # Deduplicate identical routes
    uniq: List[List[Tuple[float, float]]] = []
    seen = set()
    for r in candidates:
        key = tuple((round(p[0], 6), round(p[1], 6)) for p in r)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq

def _segments_intersect(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
    d: Tuple[float, float],
    eps: float = 1e-6,
) -> bool:
    o1 = _orientation(a, b, c, eps)
    o2 = _orientation(a, b, d, eps)
    o3 = _orientation(c, d, a, eps)
    o4 = _orientation(c, d, b, eps)

    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(a, c, b, eps):
        return True
    if o2 == 0 and _on_segment(a, d, b, eps):
        return True
    if o3 == 0 and _on_segment(c, a, d, eps):
        return True
    if o4 == 0 and _on_segment(c, b, d, eps):
        return True
    return False


def _collinear_overlap_len(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
    d: Tuple[float, float],
    eps: float = 1e-6,
) -> float:
    if abs(a[0] - b[0]) >= abs(a[1] - b[1]):
        a0, a1 = sorted([a[0], b[0]])
        c0, c1 = sorted([c[0], d[0]])
    else:
        a0, a1 = sorted([a[1], b[1]])
        c0, c1 = sorted([c[1], d[1]])
    left = max(a0, c0)
    right = min(a1, c1)
    return max(0.0, float(right - left)) if right >= left - eps else 0.0


def _touch_at_shared_endpoint_only(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
    d: Tuple[float, float],
    shared: Tuple[float, float],
    eps: float = 1e-6,
) -> bool:
    if not (_pt_eq(shared, a, eps) or _pt_eq(shared, b, eps)):
        return False
    if not (_pt_eq(shared, c, eps) or _pt_eq(shared, d, eps)):
        return False
    collinear = _orientation(a, b, c, eps) == 0 and _orientation(a, b, d, eps) == 0
    if collinear:
        return _collinear_overlap_len(a, b, c, d, eps) <= eps
    return True


def _boundary_route(
    a: Tuple[float, float],
    b: Tuple[float, float],
    ca: Tuple[int, int],
    cb: Tuple[int, int],
    scale: int,
) -> List[Tuple[float, float]]:
    dx = int(cb[0] - ca[0])
    dy = int(cb[1] - ca[1])
    route: List[Tuple[float, float]] = [a]
    if dx == 1:
        bx = float((ca[0] + 1) * scale)
        pa = (bx, a[1])
        pb = (bx, b[1])
    elif dx == -1:
        bx = float(ca[0] * scale)
        pa = (bx, a[1])
        pb = (bx, b[1])
    elif dy == 1:
        by = float((ca[1] + 1) * scale)
        pa = (a[0], by)
        pb = (b[0], by)
    elif dy == -1:
        by = float(ca[1] * scale)
        pa = (a[0], by)
        pb = (b[0], by)
    else:
        return [a, b]

    if not _pt_eq(route[-1], pa):
        route.append(pa)
    if not _pt_eq(route[-1], pb):
        route.append(pb)
    if not _pt_eq(route[-1], b):
        route.append(b)
    return route


def _route_length(route: List[Tuple[float, float]]) -> float:
    return float(sum(_seg_len(route[i], route[i + 1]) for i in range(len(route) - 1)))


def _route_is_clear(
    route: List[Tuple[float, float]],
    segments: List[Tuple[Tuple[float, float], Tuple[float, float]]],
    *,
    allow_touch_point: Optional[Tuple[float, float]] = None,
    eps: float = 1e-6,
) -> bool:
    if len(route) < 2:
        return True
    last_seg = segments[-1] if segments else None
    for i in range(len(route) - 1):
        a = route[i]
        b = route[i + 1]
        for j, (c, d) in enumerate(segments):
            if not _segments_intersect(a, b, c, d, eps):
                continue
            if last_seg is not None and j == len(segments) - 1 and allow_touch_point is not None:
                if _touch_at_shared_endpoint_only(a, b, c, d, allow_touch_point, eps):
                    continue
            return False
    return True


def _segment_is_clear_allow_endpoint_touches(
    a: Tuple[float, float],
    b: Tuple[float, float],
    segments: List[Tuple[Tuple[float, float], Tuple[float, float]]],
    *,
    allow_touch_points: Tuple[Tuple[float, float], ...] = (),
    eps: float = 1e-6,
) -> bool:
    """
    Return True iff segment (a,b) does not cross any existing segment, allowing intersections
    only when they are *pure endpoint touches* at any point in `allow_touch_points`.

    This is stricter than permitting arbitrary vertex revisits: we still forbid collinear overlaps.
    """
    for (c, d) in segments:
        if not _segments_intersect(a, b, c, d, eps):
            continue
        ok = False
        for tp in allow_touch_points:
            if _touch_at_shared_endpoint_only(a, b, c, d, tp, eps):
                ok = True
                break
        if ok:
            continue
        return False
    return True


def _build_route_candidates(
    a: Tuple[float, float],
    b: Tuple[float, float],
    ka: str,
    kb: str,
    ca: Tuple[int, int],
    cb: Tuple[int, int],
    scale: int,
) -> List[List[Tuple[float, float]]]:
    eps = 1e-6
    same_m = _kind_to_m(ka) == _kind_to_m(kb)
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    diag = abs(dx) > eps and abs(dy) > eps

    # Within the same coarse cell, the micro Hilbert path is already non-crossing.
    if ca == cb:
        return [[a, b]]

    candidates: List[List[Tuple[float, float]]] = []
    if not diag:
        candidates.append([a, b])
    else:
        if not same_m:
            candidates.append([a, b])
        p_h = (b[0], a[1])
        p_v = (a[0], b[1])
        dirx = int(cb[0] - ca[0])
        diry = int(cb[1] - ca[1])
        if dirx != 0 and diry == 0:
            candidates.append([a, p_h, b])
            candidates.append([a, p_v, b])
        elif diry != 0 and dirx == 0:
            candidates.append([a, p_v, b])
            candidates.append([a, p_h, b])
        else:
            candidates.append([a, p_h, b])
            candidates.append([a, p_v, b])

    # Boundary-guided orthogonal route (non-crossing fallback).
    candidates.append(_boundary_route(a, b, ca, cb, scale))
    return candidates


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


def _cell_offset_bits(bits: List[int], frame_idx: int, k: int, n_bits: int) -> Tuple[int, str]:
    if n_bits <= 0:
        return 0, ""
    n = len(bits)
    if n <= 0:
        raise ValueError("Empty bitstream.")
    start = (int(frame_idx) * 131 + int(k) * 19 + int(n_bits) * 7) % int(n)
    window = _bit_window(bits, start, int(n_bits))
    return _bits_to_int(window), "".join(str(int(b)) for b in window)


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


def _build_base_field_words6(*, frame_idx: int) -> List[str]:
    """
    Deterministic m=6 field on the 8x8 coarse Hilbert scan:
    - Reserve the 3 boundary words for gate semantics only.
    - Fill other sites with cyclic words (repeated deterministically).
    """
    X6 = fold6.all_x6()
    bdry = {"100001", "101001", "100101"}
    cyclic = [w for w in X6 if w not in bdry]
    if len(cyclic) != 18:
        raise AssertionError("Expected 18 cyclic m=6 words.")
    # Deterministic fill with a boundary-safe adjacency constraint:
    # forbid prev_last=1 and next_first=1 across consecutive *m=6* scan tokens.
    start = int((frame_idx * 5) % len(cyclic))
    cyc = cyclic[start:] + cyclic[:start]
    k_left, k_right = _corner_indices()
    fixed_pos = {17: "101001", 53: "100101"}
    fixed_pos[int(k_left)] = "100001"
    fixed_pos[int(k_right)] = "100001"

    out: List[str] = [""] * 64
    prev_last: Optional[str] = None
    j = 0
    for k in range(64):
        if k in fixed_pos:
            w = fixed_pos[k]
            out[k] = w
            prev_last = w[-1]
            continue

        # Greedy pick from cyclic list (repetition allowed) to satisfy boundary constraint.
        tried = 0
        while True:
            w = cyc[j % len(cyc)]
            j += 1
            tried += 1
            if prev_last == "1" and w[0] == "1":
                if tried > len(cyclic) * 2:
                    raise AssertionError("Failed to find boundary-safe cyclic word.")
                continue
            # Lookahead constraints near fixed gates/end marker:
            # - if next position is a gate starting with 1, avoid ending with 1 here
            # - if this is the last scan token (k=63), avoid ending with 1 (since end marker is 100001)
            next_fixed = fixed_pos.get(k + 1)
            if next_fixed is not None and next_fixed[0] == "1" and w[-1] == "1":
                continue
            out[k] = w
            prev_last = w[-1]
            break

    return out


def _microblock_words_for_cell(*, u6: str, m_hi: int, need: int, avoid_word: str) -> List[str]:
    """
    Choose admissible m_hi-bit words in the Fold_6 fiber of u6:
      Fold_m(k,m_hi) is used, grouped by Fold_m(k,6)=u6.
    Avoid emitting `avoid_word` (e.g. downlift marker) as data, since it's a control record.
    Return unique descendants; the caller will cycle them as needed.
    """
    m_hi = int(m_hi)
    if m_hi < 6:
        raise ValueError("m_hi must be >= 6.")
    pool = _descendants_unique(u6, m_hi, avoid_word=avoid_word)
    if not pool:
        raise ValueError(f"Not enough extension words for u6={u6}, m={m_hi}.")
    return pool


def _pick_boundary_safe_sequence(
    pool: List[str],
    *,
    need: int,
    prev_last: Optional[str],
    next_first: Optional[str] = None,
    offset: int = 0,
) -> Tuple[List[str], Optional[str]]:
    """
    Pick `need` words from `pool` (repetition allowed) so that no token boundary produces '11':
      prev_last=1 and next_first=1 is forbidden.
    If next_first is provided, also enforce compatibility of the last picked word with that next token.
    The `offset` rotates the pool to diversify selections deterministically.
    Prefer unused words first to maximize visible variety.
    """
    if not pool:
        raise ValueError("Empty pool.")
    out: List[str] = []
    used: set[str] = set()
    prev = prev_last
    n = len(pool)
    idx = int(offset) % n
    all_start_one = all(w[0] == "1" for w in pool)
    for j in range(int(need)):
        want_next_first = next_first if (j == int(need) - 1) else None
        require_last_zero = bool(all_start_one and j < int(need) - 1) or (want_next_first == "1")
        chosen = None
        for pass_idx in range(2):
            for t in range(n):
                w = pool[(idx + t) % n]
                if pass_idx == 0 and w in used:
                    continue
                if prev == "1" and w[0] == "1":
                    continue
                if require_last_zero and w[-1] == "1":
                    continue
                chosen = w
                idx = (idx + t + 1) % n
                break
            if chosen is not None:
                break
        if chosen is None:
            raise ValueError("Failed to pick a boundary-safe sequence from pool.")
        out.append(chosen)
        used.add(chosen)
        prev = chosen[-1]
    return out, prev


def _downlift_marker_for_m(m: int) -> str:
    m = int(m)
    if m < 6:
        raise ValueError("m must be >= 6.")
    if m == 6:
        return "100101"
    return "100101" + ("0" * (m - 6))


def _build_stream_tokens_for_frame(
    *,
    frame_idx: int,
    words6_scan: List[str],
    m_by_k: Dict[int, int],
    offset_by_k: Dict[int, int],
) -> Tuple[List[str], Dict[int, List[str]]]:
    """
    Build a self-describing Zeckendorf token stream for a single frame, consistent with:
      - start/end marker 100001 (m=6)
      - uplift marker 101001 (m=6) + payload6 setting initial m=8
      - refined region between scan indices 17 and 53 (exclusive): emit per-cell microblocks at local m in {8,10}
        with in-stream m switches encoded by (downlift_marker(current_m) + payload6(new_m)).
      - final downlift to m=6 using downlift_marker(current_m) + payload6(6)
      - continue in m=6 and end with 100001

    Returns:
      - tokens: the full token stream (variable token lengths)
      - micro_by_k: mapping from coarse scan index k to its microblock words (for refined cells)
    """
    if len(words6_scan) != 64:
        raise ValueError("words6_scan must have length 64.")
    if (
        words6_scan[0] != "100001"
        or words6_scan[17] != "101001"
        or words6_scan[53] != "100101"
        or words6_scan[63] != "100001"
    ):
        raise ValueError("Gate placement mismatch in words6_scan.")

    tokens: List[str] = []
    micro_by_k: Dict[int, List[str]] = {}
    prev_last: Optional[str] = None

    # m=6: from k=0..17 inclusive.
    for k in range(0, 18):
        w = words6_scan[k]
        if prev_last == "1" and w[0] == "1":
            raise ValueError("Base-field construction violated Zeckendorf boundary constraint.")
        tokens.append(w)
        prev_last = w[-1]

    # Uplift payload (6-bit) sets initial m=8 (then local switches can move to m=10).
    p_up = zeckendorf_word6(8)
    if prev_last == "1" and p_up[0] == "1":
        raise ValueError("Payload violated Zeckendorf boundary constraint.")
    tokens.append(p_up)
    prev_last = p_up[-1]

    # High-m microblocks for refined cells between 17 and 53 exclusive, with local m switches.
    cur_m = 8
    for k in range(18, 53):
        target_m = int(m_by_k.get(int(k), 8))
        if target_m not in {6, 8, 10}:
            raise ValueError("This visualization supports local m in {6,8,10} only.")

        # If we choose m=6 for this site, treat it as an unrefined macro token even inside the refined scan span.
        if int(target_m) == 6:
            if int(cur_m) != 6:
                marker = _downlift_marker_for_m(cur_m)
                if prev_last == "1" and marker[0] == "1":
                    raise ValueError("m-switch marker boundary violation.")
                tokens.append(marker)
                prev_last = marker[-1]

                payload = zeckendorf_word6(6)
                if prev_last == "1" and payload[0] == "1":
                    raise ValueError("m-switch payload boundary violation.")
                tokens.append(payload)
                prev_last = payload[-1]
                cur_m = 6

            w = words6_scan[k]
            if prev_last == "1" and w[0] == "1":
                raise ValueError("Base-field boundary violation inside refined span.")
            tokens.append(w)
            prev_last = w[-1]
            continue

        # Switch m if needed: marker(cur_m) + payload(target_m).
        if int(cur_m) != int(target_m):
            marker = _downlift_marker_for_m(cur_m)
            if prev_last == "1" and marker[0] == "1":
                raise ValueError("m-switch marker boundary violation.")
            tokens.append(marker)
            prev_last = marker[-1]

            payload = zeckendorf_word6(target_m)
            if prev_last == "1" and payload[0] == "1":
                raise ValueError("m-switch payload boundary violation.")
            tokens.append(payload)
            prev_last = payload[-1]
            cur_m = int(target_m)

        # Emit a full microblock at cur_m: length f(m)=2^(m-6).
        microblock_len = int(1 << (int(cur_m) - 6))
        avoid_word = _downlift_marker_for_m(cur_m)  # never emit control marker as data
        u6 = words6_scan[k]
        pool = _microblock_words_for_cell(u6=u6, m_hi=cur_m, need=microblock_len, avoid_word=avoid_word)

        # Lookahead: if next step is a control marker starting with '1', force last data token to end with '0'.
        need_switch_next = (k < 52 and int(m_by_k.get(int(k + 1), 8)) != int(cur_m))
        want_next_first = "1" if (k == 52 or need_switch_next) else None

        offset = int(offset_by_k.get(int(k), 0))
        mb, prev_last = _pick_boundary_safe_sequence(
            pool,
            need=microblock_len,
            prev_last=prev_last,
            next_first=want_next_first,
            offset=offset,
        )
        micro_by_k[int(k)] = mb
        tokens.extend(mb)

    # Final downlift to m=6: marker(cur_m) + payload(6) (only if needed).
    if int(cur_m) != 6:
        marker_end = _downlift_marker_for_m(cur_m)
        if prev_last == "1" and marker_end[0] == "1":
            raise ValueError("Final downlift marker boundary violation.")
        tokens.append(marker_end)
        prev_last = marker_end[-1]

        p_dn = zeckendorf_word6(6)
        if prev_last == "1" and p_dn[0] == "1":
            raise ValueError("Final downlift payload boundary violation.")
        tokens.append(p_dn)
        prev_last = p_dn[-1]

    # Back to m=6: include k=53..63
    for k in range(53, 64):
        w = words6_scan[k]
        if prev_last == "1" and w[0] == "1":
            raise ValueError("Base-field boundary violation after downlift.")
        tokens.append(w)
        prev_last = w[-1]

    # End marker: if the last base token is already start_end, treat it as the end.
    w_end = "100001"
    if tokens[-1] != w_end:
        if prev_last == "1" and w_end[0] == "1":
            raise ValueError("End marker boundary violation.")
        tokens.append(w_end)

    # Validate via codec (strong microblock policy is default).
    codec = SelfDescribingHilbertCodec(SelfCodecSpec())
    codec.validate_tokens(tokens)
    return tokens, micro_by_k


# -------------------------
# Rendering
# -------------------------


@dataclass(frozen=True)
class MicroCell:
    xx: int
    yy: int
    word: str
    u6: str
    suffix: str
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
    d_in: Tuple[int, int],
    d_out: Tuple[int, int],
) -> List[Tuple[int, int]]:
    """
    Choose a symmetry of the micro Hilbert path so that:
      - its start is near the entry side and its end near the exit side,
      - its first/last micro-steps align with the coarse entry/exit directions.
    This preserves the coarse curve direction and keeps wiring short.
    """
    best_path = sub_path
    best_score = 1e9
    for tf in _symmetry_transforms(S):
        tp = [(int(tf(xx, yy)[0]), int(tf(xx, yy)[1])) for (xx, yy) in sub_path]
        (sx, sy) = tp[0]
        (sx1, sy1) = tp[1] if len(tp) > 1 else tp[0]
        (ex, ey) = tp[-1]
        (ex1, ey1) = tp[-2] if len(tp) > 1 else tp[-1]
        s_norm = ((sx + 0.5) / float(S), (sy + 0.5) / float(S))
        e_norm = ((ex + 0.5) / float(S), (ey + 0.5) / float(S))
        ds = math.hypot(s_norm[0] - entry_target[0], s_norm[1] - entry_target[1])
        de = math.hypot(e_norm[0] - exit_target[0], e_norm[1] - exit_target[1])
        step_in = (int(sx1 - sx), int(sy1 - sy))
        step_out = (int(ex - ex1), int(ey - ey1))
        penalty = 0.0
        if d_in != (0, 0) and step_in != d_in:
            penalty += 0.8
        if d_out != (0, 0) and step_out != d_out:
            penalty += 0.8
        score = float(ds + de + penalty)
        if score < best_score:
            best_score = score
            best_path = tp
    return best_path


def _format_micro_label(word: str, *, mode: str = "full") -> str:
    w = str(word)
    if mode == "suffix":
        if len(w) <= 6:
            return w
        suffix = w[6:]
        if len(suffix) == 4:
            return suffix[:2] + "\n" + suffix[2:]
        return suffix
    if len(w) <= 8:
        return w
    if len(w) == 10:
        return w[:5] + "\n" + w[5:]
    return w


def _kind_to_m(kind: str) -> int:
    if kind == "macro":
        return 6
    if kind == "micro10":
        return 10
    return 8


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
    # Build a gate-consistent base field (m=6) and a valid self-describing stream.
    words = _build_base_field_words6(frame_idx=frame_idx)
    refined = list(range(18, 53))

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

    # Local m policy (data): user-specified schedule with m=8/m=10, and downlift to m=6.
    m_by_k = _m_schedule_fixed()

    offset_by_k: Dict[int, int] = {}
    offset_bits_by_k: Dict[int, str] = {}
    for k in refined:
        m_hi = int(m_by_k.get(int(k), 8))
        n_suffix = int(m_hi - 6)
        off, bitstr = _cell_offset_bits(bits_global, frame_idx, int(k), int(n_suffix))
        offset_by_k[int(k)] = int(off)
        offset_bits_by_k[int(k)] = str(bitstr)

    tokens, micro_by_k = _build_stream_tokens_for_frame(
        frame_idx=frame_idx,
        words6_scan=words,
        m_by_k=m_by_k,
        offset_by_k=offset_by_k,
    )
    bits_used = int(sum(len(t) for t in tokens))
    up_pos = 17
    dn_pos = 53
    assigns = {k: (len(mb[0]), offset_by_k.get(int(k), 0), offset_bits_by_k.get(int(k), "")) for k, mb in micro_by_k.items()}
    n_m8 = sum(1 for mb in micro_by_k.values() if len(mb[0]) == 8)
    n_m10 = sum(1 for mb in micro_by_k.values() if len(mb[0]) == 10)

    # Base plane indices in {0..20} and RGB upsample.
    base_idx8 = np.zeros((8, 8), dtype=int)
    for k in range(64):
        x, y = k_to_xy[k]
        base_idx8[y, x] = int(word_to_idx[words[k]])
    base_cell_rgb = palette_rgb[base_idx8]  # (8,8,3)
    base_rgb = np.repeat(np.repeat(base_cell_rgb, scale, axis=0), scale, axis=1)  # (H,W,3)
    H, W, _ = base_rgb.shape

    # -------------------------
    # One-stroke wiring over node-centers only (no intermediate edges)
    # -------------------------
    #
    # User rule:
    # - same level (same m): only 90/180-degree segments between centers (axis-aligned)
    # - different level (different m): connect centers with one straight diagonal segment
    # - nodes are centers; edges are only center-to-center segments (no intermediate routing)
    # - entire polyline must be a single stroke and non-self-intersecting.

    eps = 1e-6

    @dataclass(frozen=True)
    class _RefinedMeta:
        k: int
        S: int
        kind: str
        base_color: np.ndarray
        mb_words: List[str]
        denom: int
        orders: List[List[Tuple[int, int]]]  # candidate micro orders (xx,yy) lists

    refined_meta: Dict[int, _RefinedMeta] = {}
    for k, mb_words in micro_by_k.items():
        u = words[k]
        base_color = palette_rgb[int(word_to_idx[u])]
        m_hi_local = int(len(mb_words[0])) if mb_words else 8
        n_suffix = int(m_hi_local - 6)
        n_bits_sub = int(n_suffix // 2)
        S = 1 << n_bits_sub
        kind = "micro" if m_hi_local == 8 else "micro10"
        denom = max(1, (S * S) - 1)
        (d_in, d_out) = dirs_in_out.get(int(k), ((0, 0), (0, 0)))
        orders_all = _candidate_micro_orders_for_cell(S=S, n_bits_sub=n_bits_sub, d_in=d_in, d_out=d_out)
        orders = orders_all[:8] if len(orders_all) > 8 else orders_all
        refined_meta[int(k)] = _RefinedMeta(
            k=int(k),
            S=int(S),
            kind=str(kind),
            base_color=base_color,
            mb_words=list(mb_words),
            denom=int(denom),
            orders=[[(int(xx), int(yy)) for (xx, yy) in ord_xy] for ord_xy in orders],
        )

    # Precompute all node-centers for the "no skipping nodes" constraint.
    # Data definition (strict center-graph):
    # - if a coarse cell is refined (m=8/10): nodes are the subcell centers only (no macro node)
    # - otherwise (m=6): node is the coarse cell center
    centers_all: List[Tuple[float, float]] = []
    for kk, (x, y) in enumerate(path_xy):
        if int(kk) in refined_meta:
            meta = refined_meta[int(kk)]
            for xx in range(meta.S):
                for yy in range(meta.S):
                    centers_all.append(_center_point_in_subcell(x, y, scale, meta.S, xx, yy))
        else:
            centers_all.append(_center_point_in_cell(x, y, scale))

    # Build per-coarse-cell options as lists of (point, kind, cell_xy).
    cell_opts: List[List[List[Tuple[Tuple[float, float], str, Tuple[int, int]]]]] = []
    for kk, (x, y) in enumerate(path_xy):
        cell_xy = (int(x), int(y))
        if int(kk) in refined_meta:
            meta = refined_meta[int(kk)]
            opts: List[List[Tuple[Tuple[float, float], str, Tuple[int, int]]]] = []
            for ord_xy in meta.orders:
                pts = [(_center_point_in_subcell(x, y, scale, meta.S, xx, yy), meta.kind, cell_xy) for (xx, yy) in ord_xy]
                opts.append(pts)
            cell_opts.append(opts)
        else:
            cell_opts.append([[( _center_point_in_cell(x, y, scale), "macro", cell_xy )]])

    state = _WireState(wire_points=[], wire_kind=[], segments=[])
    chosen_opt: Dict[int, int] = {}

    def _axis_aligned(a: Tuple[float, float], b: Tuple[float, float]) -> bool:
        return abs(a[0] - b[0]) <= eps or abs(a[1] - b[1]) <= eps

    def _can_add_segment(a: Tuple[float, float], b: Tuple[float, float]) -> bool:
        if _pt_eq(a, b, eps):
            return False
        if _segment_hits_any_center(a, b, centers_all, allow_endpoints=(a, b), eps=eps):
            return False
        if not _segment_is_clear_allow_endpoint_touches(a, b, state.segments, allow_touch_points=(a, b), eps=eps):
            return False
        return True

    # Incremental backtracking in scan order (fast pruning):
    # choose micro-orientation per refined cell, and append segments immediately with intersection checks.
    prog = ProgressEvery(label=f"wiring_center_graph frame={frame_idx}", total=None, interval_s=60.0)
    prog.start()
    tries_total = 0
    backtracks = 0
    max_tries = 2_000_000

    # Reduce branching a bit for m=10 cells (still allows rotate/backtrack).
    for kk in range(64):
        if int(kk) in refined_meta:
            meta = refined_meta[int(kk)]
            # Keep more for m=10 (harder), but still bounded.
            keep = 8 if int(meta.S) == 4 else 6
            cell_opts[kk] = cell_opts[kk][:keep]

    def _diagonal(a: Tuple[float, float], b: Tuple[float, float]) -> bool:
        return abs(a[0] - b[0]) > eps and abs(a[1] - b[1]) > eps

    def _edge_ok(a: Tuple[float, float], b: Tuple[float, float], ka: str, kb: str) -> bool:
        if _kind_to_m(ka) == _kind_to_m(kb):
            if not _axis_aligned(a, b):
                return False
        else:
            if not _diagonal(a, b):
                return False
        return _can_add_segment(a, b)

    def dfs_cell(kcell: int) -> bool:
        nonlocal tries_total, backtracks
        tries_total += 1
        if tries_total % 2048 == 0:
            prog.maybe(tries_total, extra=f"kcell={kcell} segs={len(state.segments)} backtracks={backtracks}")
        if tries_total > max_tries:
            return False
        if kcell >= 64:
            return True

        for opt_idx, pts in enumerate(cell_opts[kcell]):
            if not pts:
                continue
            added: List[Tuple[int, int]] = []
            started_here = False

            if int(kcell) in refined_meta:
                chosen_opt[int(kcell)] = int(opt_idx)

            # Connect from current endpoint to the first point of this cell option.
            if not state.wire_points:
                state.wire_points.append(pts[0][0])
                state.wire_kind.append(pts[0][1])
                started_here = True
            else:
                a = state.wire_points[-1]
                ka = state.wire_kind[-1]
                b = pts[0][0]
                kb = pts[0][1]
                if not _edge_ok(a, b, str(ka), str(kb)):
                    chosen_opt.pop(int(kcell), None)
                    continue
                npa, nsa = _append_route(state, [a, b], kind_from=str(ka), kind_to=str(kb))
                added.append((npa, nsa))

            ok_internal = True
            for j in range(len(pts) - 1):
                a = pts[j][0]
                ka = pts[j][1]
                b = pts[j + 1][0]
                kb = pts[j + 1][1]
                if not _pt_eq(state.wire_points[-1], a, eps):
                    ok_internal = False
                    break
                if not _edge_ok(a, b, str(ka), str(kb)):
                    ok_internal = False
                    break
                npa, nsa = _append_route(state, [a, b], kind_from=str(ka), kind_to=str(kb))
                added.append((npa, nsa))

            if ok_internal and dfs_cell(kcell + 1):
                return True

            backtracks += 1
            for (npa, nsa) in reversed(added):
                _pop_route(state, npa, nsa)
            if started_here:
                state.wire_points.clear()
                state.wire_kind.clear()
            chosen_opt.pop(int(kcell), None)

        return False

    ok = dfs_cell(0)
    if not ok:
        m_seq, n_sw, runs = _m_profile_stats(refined, m_by_k)
        raise RuntimeError(
            "No one-stroke non-crossing wiring found under strict center-graph rules (or search cap exceeded). "
            + _wiring_m_constraints_text()
            + f" tries={tries_total} backtracks={backtracks}"
            + f" m_switches={n_sw} m_runs={runs}"
            + f" m_seq_head={m_seq[:16]}"
        )
    prog.done(extra=f"tries={tries_total} backtracks={backtracks} segs={len(state.segments)}")

    wire_points = state.wire_points
    wire_kind = state.wire_kind

    # Paint microstructure in refined cells and collect micro labels (match the chosen micro order).
    micro_ops = 64
    refined_cells: Dict[int, List[MicroCell]] = {}
    for k, meta in refined_meta.items():
        x, y = k_to_xy[k]
        x0 = int(x * scale)
        y0 = int(y * scale)
        x1 = int((x + 1) * scale)
        y1 = int((y + 1) * scale)
        sx = max(1, (x1 - x0) // meta.S)
        sy = max(1, (y1 - y0) // meta.S)
        cells: List[MicroCell] = []
        ord_idx = int(chosen_opt.get(int(k), 0))
        ord_xy = meta.orders[ord_idx]
        if len(meta.mb_words) != len(ord_xy):
            raise AssertionError("Microblock length mismatch to chosen Hilbert micro order.")
        for j, (xx, yy) in enumerate(ord_xy):
            w_hi = meta.mb_words[j]
            u6 = w_hi[:6]
            suffix = w_hi[6:]
            code = _bits_to_int([int(b) for b in suffix]) if suffix else 0
            t = 0.25 + 0.75 * (float(code) / float(meta.denom))
            px0 = x0 + int(xx) * sx
            py0 = y0 + int(yy) * sy
            px1 = x0 + (int(xx) + 1) * sx
            py1 = y0 + (int(yy) + 1) * sy
            base_rgb[py0:py1, px0:px1, :] = np.clip(meta.base_color * t, 0.0, 1.0)
            cells.append(MicroCell(xx=int(xx), yy=int(yy), word=w_hi, u6=u6, suffix=suffix, code=code))
        refined_cells[int(k)] = cells
        micro_ops += int(meta.S * meta.S) - 1

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

    # Wiring (wire_points, wire_kind) is computed above by center-to-center backtracking.

    # Turn wired points into segments with per-segment styling.
    segs: List[List[Tuple[float, float]]] = []
    widths: List[float] = []
    alphas: List[float] = []
    for i in range(len(wire_points) - 1):
        a = wire_points[i]
        b = wire_points[i + 1]
        ka = wire_kind[i]
        kb = wire_kind[i + 1]
        if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6:
            continue
        if _kind_to_m(ka) == _kind_to_m(kb) and not (abs(a[0] - b[0]) < 1e-6 or abs(a[1] - b[1]) < 1e-6):
            raise RuntimeError("same-m segment is not axis-aligned; violates wiring rule.")
        segs.append([a, b])
        if ka.startswith("micro") and kb.startswith("micro"):
            if ka == "micro10" or kb == "micro10":
                widths.append(1.05)
                alphas.append(0.60)
            else:
                widths.append(1.35)
                alphas.append(0.85)
        else:
            # Cross-scale or macro: keep it as the main scan stroke (diagonal allowed).
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

    # Refined cells: per-cell header + per-subcell full-word labels.
    for k, mb_words in micro_by_k.items():
        x, y = k_to_xy[k]
        x0 = int(x * scale)
        y0 = int(y * scale)
        m_hi_local = int(len(mb_words[0])) if mb_words else 8
        n_suffix = int(m_hi_local - 6)
        n_bits_sub = int(n_suffix // 2)
        S = 1 << n_bits_sub

        # Header for the refined cell (m + code bits).
        _m, _off, bitstr = assigns.get(int(k), (m_hi_local, 0, ""))
        head = f"m={m_hi_local}"
        ax.text(
            x0 + 2,
            y0 + 2,
            head,
            fontsize=7,
            color="#00E5FF",
            ha="left",
            va="bottom",
            bbox=dict(facecolor=(0, 0, 0, 0.35), edgecolor="none", pad=1.0),
            zorder=10,
        )

        # Label each micro subcell by its full m-bit word.
        for mc in refined_cells.get(k, []):
            cx, cy = _center_point_in_subcell(x, y, scale, S, mc.xx, mc.yy)
            label = _format_micro_label(mc.word, mode="suffix")
            suffix_len = max(0, len(mc.word) - 6)
            font_sz = 8.2 if suffix_len <= 2 else 6.2
            ax.text(
                cx,
                cy,
                label,
                fontsize=font_sz,
                color="#FFFFFF",
                ha="center",
                va="center",
                bbox=dict(facecolor=(0, 0, 0, 0.22), edgecolor="none", pad=0.35),
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
    axr.text(0.0, 0.88, f"bit budget (conserved) = n/a (self-describing)", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.84, f"stream bits = {bits_used}", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.79, f"micro-ops (energy proxy) = {micro_ops}", fontsize=11, color="#263238", va="top")
    axr.text(0.0, 0.74, f"uplift pos = {up_pos}, downlift pos = {dn_pos}", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.69, f"refined cells = {len(micro_by_k)}  (m=8:{n_m8}, m=10:{n_m10})", fontsize=10, color="#455A64", va="top")
    axr.text(
        0.0,
        0.56,
        "wiring rules:\n"
        "- single continuous scan curve\n"
        "- same-m: 90/180-degree only\n"
        "- cross-m: shortest diagonal link\n"
        "encoding:\n"
        "- big cell label = 6-bit u\n"
        "- micro cell label = suffix bits only",
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


def _render_contact_sheet(gif_path: Path, out_png: Path, rows: int = 3, cols: int = 4) -> None:
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
        + r"with same-$m$ wiring axis-aligned and cross-$m$ links drawn as shortest diagonals. "
        + r"All big cells are labeled by their $6$-bit stable word $u$, and micro subcells are labeled by their full $m$-bit words (prefix inherits $u$).",
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
    _render_contact_sheet(out_gif, out_cs, rows=3, cols=4)

    out_leg = fig_root / "x6_palette_legend.png"
    _render_x6_palette_legend(X6=X6, palette_rgb=palette_rgb, out_png=out_leg)

    _write_tex_summary(fig_root)

    print(f"Wrote {out_gif}")
    print(f"Wrote {out_cs}")
    print(f"Wrote {out_leg}")
    print("Wrote sections/generated/dynamic_centerwired_code_summary.tex")


if __name__ == "__main__":
    main()

