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
    row_h = 1.8
    w_base = 2.2
    w_m8 = 1.8
    w_m10 = 1.8
    gap = 0.45
    top_pad = 1.6
    total_w = w_base + w_m8 + w_m10 + 2 * gap
    total_h = top_pad + n * row_h
    fig, ax = plt.subplots(figsize=(12.5, 0.40 * total_h))
    ax.axis("off")
    ax.set_xlim(0, total_w)
    ax.set_ylim(0, total_h)
    ax.set_title("m=6 stable types with m=8/m=10 descendants (prefix inheritance)", fontsize=13, pad=10)

    ax.text(0.0, total_h - 0.35, "descendants keep the first 6 bits = u6", fontsize=9, color="#455A64", va="top")
    ax.text(0.05, total_h - 0.75, "m=6 (u6)", fontsize=9, color="#263238", va="top")
    ax.text(w_base + gap + 0.05, total_h - 0.75, "m=8 descendants", fontsize=9, color="#263238", va="top")
    ax.text(w_base + gap + w_m8 + gap + 0.05, total_h - 0.75, "m=10 descendants", fontsize=9, color="#263238", va="top")

    gauge_short = {"100001": "U(1)", "101001": "SU(2)", "100101": "SU(3)"}

    def descendants_for(u6: str, m_hi: int, count: int) -> List[str]:
        avoid = _downlift_marker_for_m(m_hi)
        outs_hi = foldm.cached_foldm_outputs(m_hi)
        pool = [w_hi for k, w_hi in enumerate(outs_hi) if (w_hi != avoid and foldm.foldm(k, 6) == u6)]
        if not pool:
            raise ValueError(f"No descendants for u6={u6}, m={m_hi}.")
        offset = int(u6, 2) % len(pool)
        return [pool[(offset + i) % len(pool)] for i in range(int(count))]

    for i, w in enumerate(X6):
        y0 = total_h - top_pad - (i + 1) * row_h
        color = palette_rgb[i]
        tag = "bdry" if (len(w) >= 2 and w[0] == "1" and w[-1] == "1") else "cyc"
        extra = f"  {gauge_short[w]}" if w in gauge_short else ""

        ax.add_patch(Rectangle((0.0, y0 + 0.05), w_base - 0.1, row_h - 0.1, facecolor=color, edgecolor="#263238", lw=0.8))
        ax.text(0.06, y0 + row_h - 0.12, f"{w}  [{tag}]{extra}", fontsize=8.5, color="#263238", va="top")

        m8_words = descendants_for(w, 8, 4)
        m10_words = descendants_for(w, 10, 16)

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
    Choose `need` admissible m_hi-bit words in the Fold_6 fiber of u6:
      Fold_m(k,m_hi) is used, grouped by Fold_m(k,6)=u6.
    Avoid emitting `avoid_word` (e.g. downlift marker) as data, since it's a control record.
    """
    m_hi = int(m_hi)
    if m_hi < 6:
        raise ValueError("m_hi must be >= 6.")
    # Enumerate dyadic indices for this m_hi.
    outs_hi = foldm.cached_foldm_outputs(m_hi)  # length 2^m_hi
    pool: List[str] = []
    for k, w_hi in enumerate(outs_hi):
        if w_hi == avoid_word:
            continue
        if foldm.foldm(k, 6) == u6:
            pool.append(w_hi)
            if len(pool) >= need * 4:
                # Usually plenty; cap for speed.
                break
    if len(pool) < need:
        # Fallback: do a full scan if truncated early.
        pool = [w_hi for k, w_hi in enumerate(outs_hi) if (w_hi != avoid_word and foldm.foldm(k, 6) == u6)]
    if len(pool) < need:
        raise ValueError(f"Not enough extension words for u6={u6}, m={m_hi}: need {need}, got {len(pool)}.")
    # Return a pool; the caller will pick a boundary-safe sequence of the required length.
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
                if pass_idx == 0 and w in used and n > int(need):
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
        if target_m not in {8, 10}:
            raise ValueError("This visualization supports local m in {8,10} only.")

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

    # Final downlift to m=6: marker(cur_m) + payload(6).
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
        ds = math.hypot(s_norm[0] - entry_target[0], s_norm[1] - entry_target[1])
        de = math.hypot(e_norm[0] - exit_target[0], e_norm[1] - exit_target[1])
        score = float(ds + de)
        if score < best_score:
            best_score = score
            best_path = tp
    return best_path


def _format_micro_label(word: str) -> str:
    w = str(word)
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
    # Local m policy (dynamic bitrate): mostly m=8 with a few m=10 cells per frame.
    # Deterministic and in-stream self-describing via control records.
    m_by_k: Dict[int, int] = {}
    refined = list(range(18, 53))
    for j, k in enumerate(refined):
        m_by_k[int(k)] = 10 if ((j + 3 * int(frame_idx)) % 7 == 0) else 8
    # Ensure we don't attempt an immediate 8->10 control right after the initial uplift (microblock policy).
    m_by_k[18] = 8

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
    for k, mb_words in micro_by_k.items():
        u = words[k]
        base_color = palette_rgb[int(word_to_idx[u])]
        x, y = k_to_xy[k]
        x0 = int(x * scale)
        y0 = int(y * scale)
        x1 = int((x + 1) * scale)
        y1 = int((y + 1) * scale)

        m_hi_local = int(len(mb_words[0])) if mb_words else 8
        n_suffix = int(m_hi_local - 6)
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
        if len(mb_words) != len(sub_path):
            raise AssertionError("Microblock length mismatch to Hilbert subpath.")
        for j, (xx, yy) in enumerate(sub_path):
            w_hi = mb_words[j]
            u6 = w_hi[:6]
            suffix = w_hi[6:]
            code = _bits_to_int([int(b) for b in suffix]) if suffix else 0
            # Discrete brightness ladder -> discrete colors represent codes (visual only).
            t = 0.25 + 0.75 * (float(code) / float(denom))
            px0 = x0 + xx * sx
            py0 = y0 + yy * sy
            px1 = x0 + (xx + 1) * sx
            py1 = y0 + (yy + 1) * sy
            base_rgb[py0:py1, px0:px1, :] = np.clip(base_color * t, 0.0, 1.0)
            cells.append(MicroCell(xx=xx, yy=yy, word=w_hi, u6=u6, suffix=suffix, code=code))
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
    # Same-m steps are orthogonal; cross-m steps use shortest diagonals.
    expanded_points: List[Tuple[float, float]] = []
    point_kind: List[str] = []  # "macro", "micro" (m=8), "micro10"
    point_cell: List[Tuple[int, int]] = []
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
                point_cell.append((int(x), int(y)))
            else:
                for (xx, yy) in micro_order:
                    expanded_points.append(_center_point_in_subcell(x, y, scale, S, int(xx), int(yy)))
                    point_kind.append("micro" if int(m_hi) == 8 else "micro10")
                    point_cell.append((int(x), int(y)))
        else:
            expanded_points.append(_center_point_in_cell(x, y, scale))
            point_kind.append("macro")
            point_cell.append((int(x), int(y)))

    # Insert right-angle turns for same-m diagonal steps to avoid slanted wiring at the same level.
    wire_points: List[Tuple[float, float]] = []
    wire_kind: List[str] = []
    if expanded_points:
        wire_points.append(expanded_points[0])
        wire_kind.append(point_kind[0])
    for i in range(len(expanded_points) - 1):
        a = expanded_points[i]
        b = expanded_points[i + 1]
        ka = point_kind[i]
        kb = point_kind[i + 1]
        ca = point_cell[i]
        cb = point_cell[i + 1]
        if _kind_to_m(ka) == _kind_to_m(kb):
            dx = b[0] - a[0]
            dy = b[1] - a[1]
            if abs(dx) > 1e-6 and abs(dy) > 1e-6:
                dir_x = int(cb[0] - ca[0])
                dir_y = int(cb[1] - ca[1])
                if dir_x != 0 and dir_y == 0:
                    mid = (b[0], a[1])  # follow coarse horizontal direction first
                elif dir_y != 0 and dir_x == 0:
                    mid = (a[0], b[1])  # follow coarse vertical direction first
                else:
                    mid = (b[0], a[1])
                if abs(mid[0] - wire_points[-1][0]) > 1e-6 or abs(mid[1] - wire_points[-1][1]) > 1e-6:
                    wire_points.append(mid)
                    wire_kind.append(ka)
        wire_points.append(b)
        wire_kind.append(kb)

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
        head = f"m={m_hi_local}" + (f"  off={bitstr}" if bitstr else "")
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
            label = _format_micro_label(mc.word)
            font_sz = 7 if len(mc.word) <= 8 else 5.4
            ax.text(
                cx,
                cy,
                label,
                fontsize=font_sz,
                color="#FFFFFF",
                ha="center",
                va="center",
                bbox=dict(facecolor=(0, 0, 0, 0.35), edgecolor="none", pad=0.45),
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
            "- micro cell label = full m-bit word",
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

