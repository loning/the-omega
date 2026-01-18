# -*- coding: utf-8 -*-
"""
DNA/RNA sequence decoder + Hilbert-curve visualization (movie-style tiles).

Goal
----
Port the "movie-like Hilbert visualization" idea to DNA sequences:
- map a 1D sequence into a 2D Hilbert order on a 2^n x 2^n grid;
- color by decoded symbols (base-level or codon->AA);
- optionally export a GIF by sliding a fixed-length tile along the sequence.

Outputs (default under figures/):
  - dna_hilbert_frame_0000.png ... (PNG frames)
  - dna_hilbert.gif (if Pillow is available)
  - dna_hilbert_contact_sheet.png (if Pillow is available)
  - dna_hilbert_legend.png

Notes
-----
- English-only in plots (repo convention).
- This script is intentionally self-contained: it includes a standard Hilbert d2xy implementation.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Iterable, Iterator

import numpy as np

import matplotlib  # type: ignore

matplotlib.use("Agg")  # type: ignore
import matplotlib.pyplot as plt  # type: ignore  # noqa: E402
from matplotlib.collections import LineCollection  # type: ignore  # noqa: E402
from matplotlib.patches import Rectangle  # type: ignore  # noqa: E402

try:
    from PIL import Image  # type: ignore

    _HAS_PIL = True
except Exception:
    Image = None  # type: ignore
    _HAS_PIL = False

from genetic_code_tools import (
    BOUNDARY_WORDS,
    CodonFold,
    GENETIC_CODE,
    fold_codon,
    x_m,
)  # local module in this paper repo


SCRIPT_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def figures_dir() -> Path:
    d = root_dir() / "figures"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


# -------------------------
# FASTA / sequence loading
# -------------------------


def _iter_fasta_text(text: str) -> Iterator[tuple[str, str]]:
    header = None
    parts: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                yield header, "".join(parts)
            header = line[1:].split()[0] if line[1:].strip() else "record"
            parts = []
        else:
            parts.append(line)
    if header is not None:
        yield header, "".join(parts)


def _parse_genbank_origin(text: str) -> tuple[str, str]:
    """
    Minimal GenBank parser: extract ACCESSION (as name) and ORIGIN sequence.
    Accepts .gb/.gbk files commonly found in NCBI exports.
    """
    acc: str | None = None
    in_origin = False
    parts: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not acc and line.startswith("ACCESSION"):
            toks = line.split()
            if len(toks) >= 2:
                acc = toks[1].strip()
            continue
        if line.startswith("ORIGIN"):
            in_origin = True
            continue
        if in_origin:
            if line.startswith("//"):
                break
            # Typical ORIGIN lines: "    1 atgc..."; keep only letters.
            parts.append("".join(ch for ch in line if ch.isalpha()))
    name = acc if acc else "genbank_record"
    seq = "".join(parts)
    if not seq:
        raise ValueError("GenBank parse failed: ORIGIN not found or empty.")
    return name, seq


def _load_sequence(*, fasta_path: Path | None, seq: str | None) -> tuple[str, str]:
    """
    Returns (name, sequence_raw).
    """
    if fasta_path is None and seq is None:
        raise ValueError("Provide --fasta or --seq")
    if fasta_path is not None and seq is not None:
        raise ValueError("Provide only one of --fasta or --seq")

    if seq is not None:
        return ("seq", str(seq))

    assert fasta_path is not None
    text = fasta_path.read_text(encoding="utf-8", errors="ignore")
    suf = fasta_path.suffix.lower()
    if suf in {".gb", ".gbk"} or text.lstrip().startswith("LOCUS"):
        return _parse_genbank_origin(text)

    recs = list(_iter_fasta_text(text))
    if not recs:
        raise ValueError(f"Empty or invalid FASTA/GenBank: {fasta_path}")
    return recs[0][0], recs[0][1]


def normalize_dna(seq: str) -> str:
    s = "".join(ch for ch in str(seq).upper() if ch.isalpha())
    s = s.replace("U", "T")
    return s


def normalize_rna(seq: str) -> str:
    s = "".join(ch for ch in str(seq).upper() if ch.isalpha())
    s = s.replace("T", "U")
    return s


# -------------------------
# Hilbert: d -> (x,y)
# -------------------------


def _rot(s: int, x: int, y: int, rx: int, ry: int) -> tuple[int, int]:
    if ry == 0:
        if rx == 1:
            x = s - 1 - x
            y = s - 1 - y
        x, y = y, x
    return x, y


def hilbert_d2xy(n_side: int, d: int) -> tuple[int, int]:
    """
    Convert Hilbert curve index d to (x,y) on an n_side x n_side grid.
    n_side must be a power of 2.

    Reference algorithm: Wikipedia "Hilbert curve" d2xy.
    """
    if n_side <= 0 or (n_side & (n_side - 1)) != 0:
        raise ValueError("n_side must be a power of 2")
    if d < 0 or d >= n_side * n_side:
        raise ValueError("d out of range")
    x = 0
    y = 0
    t = int(d)
    s = 1
    while s < n_side:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        x, y = _rot(s, x, y, int(rx), int(ry))
        x += s * int(rx)
        y += s * int(ry)
        t //= 4
        s *= 2
    return int(x), int(y)


def hilbert_path(n_side: int) -> list[tuple[int, int]]:
    return [hilbert_d2xy(n_side, d) for d in range(n_side * n_side)]


# -------------------------
# Decoding + palettes
# -------------------------


_BASE_TO_CODE = {"A": 0, "C": 1, "G": 2, "T": 3}
_CODE_TO_BASE = {0: "A", 1: "C", 2: "G", 3: "T"}


def dna_to_2bit_codes(seq_dna: str) -> list[int]:
    """
    Map DNA bases to 2-bit codes:
      A->0, C->1, G->2, T->3
    Unknown bases map to -1.
    """
    out: list[int] = []
    for ch in seq_dna:
        out.append(int(_BASE_TO_CODE.get(ch, -1)))
    return out


def _material_palette_base() -> dict[str, tuple[float, float, float]]:
    # Material-like distinct base colors.
    return {
        "A": (0.180, 0.490, 0.196),  # green
        "C": (0.082, 0.396, 0.753),  # blue
        "G": (0.937, 0.424, 0.000),  # orange
        "T": (0.776, 0.157, 0.157),  # red
        "N": (0.545, 0.600, 0.631),  # gray
    }


def _material_palette_21() -> list[tuple[float, float, float]]:
    # Same palette family as other figures (Material-ish).
    hexs = [
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

    def hx(h: str) -> tuple[float, float, float]:
        hh = h.lstrip("#")
        r = int(hh[0:2], 16) / 255.0
        g = int(hh[2:4], 16) / 255.0
        b = int(hh[4:6], 16) / 255.0
        return (r, g, b)

    return [hx(h) for h in hexs]


def _aa_palette() -> dict[str, tuple[float, float, float]]:
    """
    Amino acid -> RGB color. We keep 21 distinct colors and map Stop to a neutral dark.
    """
    pal = _material_palette_21()
    aas = sorted({aa for aa in GENETIC_CODE.values() if aa != "Stop"})
    out: dict[str, tuple[float, float, float]] = {}
    for i, aa in enumerate(aas):
        out[aa] = pal[i % len(pal)]
    out["Stop"] = (0.10, 0.10, 0.10)
    out["NA"] = (0.75, 0.75, 0.75)
    return out


def codons(seq_rna: str, *, frame: int) -> list[str]:
    s = str(seq_rna)
    frame = int(frame) % 3
    s = s[frame:]
    n = (len(s) // 3) * 3
    s = s[:n]
    return [s[i : i + 3] for i in range(0, len(s), 3)]


# -------------------------
# Rendering
# -------------------------


def _render_legend(*, mode: str, out_png: Path) -> None:
    mode = str(mode)
    _ensure_dir(out_png.parent)
    plt.figure(figsize=(10.2, 2.6), dpi=200)
    ax = plt.gca()
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 2.6)

    if mode == "base":
        pal = _material_palette_base()
        labels = ["A", "C", "G", "T", "N"]
        ax.text(0.0, 2.45, "DNA base palette (Hilbert fill)", fontsize=12, color="#263238", va="top")
        for i, lab in enumerate(labels):
            x0 = 0.4 + i * 1.8
            ax.add_patch(Rectangle((x0, 1.2), 1.2, 0.9, facecolor=pal[lab], edgecolor="#263238", lw=0.6))
            ax.text(x0 + 0.6, 1.65, lab, ha="center", va="center", color="white", fontsize=12)
        ax.text(0.4, 0.55, "Unknown bases (not A/C/G/T) are shown as N.", fontsize=9.5, color="#455A64")
    else:
        pal = _aa_palette()
        aas = sorted({aa for aa in GENETIC_CODE.values()})
        aas = [a for a in aas if a != "NA"]
        ax.text(0.0, 2.45, "Codon->amino-acid palette (Hilbert fill)", fontsize=12, color="#263238", va="top")
        x = 0.2
        y = 1.90
        dx = 1.04
        dy = 0.38
        cols = 9
        for i, aa in enumerate(aas):
            r = i // cols
            c = i % cols
            xx = x + c * dx
            yy = y - r * dy
            ax.add_patch(Rectangle((xx, yy - 0.26), 0.34, 0.24, facecolor=pal.get(aa, pal["NA"]), edgecolor="#263238", lw=0.4))
            ax.text(xx + 0.40, yy - 0.14, aa, fontsize=7.5, color="#263238", va="center", ha="left")
        ax.text(0.2, 0.25, "Stop codons are colored near-black.", fontsize=9.5, color="#455A64")

    plt.tight_layout()
    plt.savefig(out_png, bbox_inches="tight")
    plt.close()


def _render_legend_centerwired(*, out_png: Path) -> None:
    """
    Legend for the centerwired scheme:
    - colors encode Fold_6 stable types w in X6 (21 admissible words);
    - boundary words (control symbols) are highlighted.
    """
    _ensure_dir(out_png.parent)
    x6 = x_m(6)
    pal21 = _material_palette_21()
    w_to_col = {w: pal21[i % len(pal21)] for i, w in enumerate(x6)}

    plt.figure(figsize=(12.0, 3.3), dpi=200)
    ax = plt.gca()
    ax.axis("off")
    ax.set_xlim(0, 12.0)
    ax.set_ylim(0, 3.3)
    ax.text(0.0, 3.18, "Centerwired palette: Fold_6 stable types (X6, 21 words)", fontsize=12, color="#263238", va="top")

    # Layout: 7 columns x 3 rows (21 entries)
    cols = 7
    dx = 1.62
    dy = 0.86
    x0 = 0.20
    y0 = 2.60

    for i, w in enumerate(x6):
        r = i // cols
        c = i % cols
        xx = x0 + c * dx
        yy = y0 - r * dy
        col = w_to_col[w]
        is_ctrl = w in BOUNDARY_WORDS
        edge = "#263238" if is_ctrl else "#607D8B"
        lw = 1.4 if is_ctrl else 0.6
        ax.add_patch(Rectangle((xx, yy - 0.46), 0.62, 0.42, facecolor=col, edgecolor=edge, lw=lw))
        ax.text(xx + 0.70, yy - 0.26, w, fontsize=9.5, color="#263238", va="center", ha="left")

    ax.text(
        0.20,
        0.34,
        "Boundary words are control symbols (thick border).",
        fontsize=9.5,
        color="#455A64",
        va="center",
    )
    ax.text(
        0.20,
        0.10,
        "In centerwired frames: microstructure is encoded by brightness modulation inside refined cells.",
        fontsize=9.5,
        color="#455A64",
        va="center",
    )

    plt.tight_layout()
    plt.savefig(out_png, bbox_inches="tight")
    plt.close()


def _draw_path_overlay(ax, n_side: int, scale: int, *, step: int = 64) -> None:
    """
    Draw a light Hilbert wiring overlay by subsampling the path.
    """
    step = max(1, int(step))
    pts = []
    for d in range(0, n_side * n_side, step):
        x, y = hilbert_d2xy(n_side, d)
        pts.append((x * scale + scale / 2.0, y * scale + scale / 2.0))
    if len(pts) >= 2:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, color="white", lw=0.6, alpha=0.35, zorder=10)


# -------------------------
# Center-wired (m uplift/downlift) scheme
# -------------------------


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[float, float, float]:
    h = float(h) % 1.0
    s = float(np.clip(s, 0.0, 1.0))
    v = float(np.clip(v, 0.0, 1.0))
    if s <= 1e-12:
        return (v, v, v)
    i = int(h * 6.0)
    f = h * 6.0 - float(i)
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    if i == 0:
        return (v, t, p)
    if i == 1:
        return (q, v, p)
    if i == 2:
        return (p, v, t)
    if i == 3:
        return (p, q, v)
    if i == 4:
        return (t, p, v)
    return (v, p, q)


def _palette64() -> list[tuple[float, float, float]]:
    """
    64 distinct-ish colors for 6-bit prefixes (3-mer under 2-bit coding).
    Deterministic, Material-ish readability: moderate saturation and value.
    """
    out: list[tuple[float, float, float]] = []
    for u in range(64):
        h = (u / 64.0 + 0.08) % 1.0
        s = 0.62
        v = 0.92
        out.append(_hsv_to_rgb(h, s, v))
    return out


def _bases_to_u6_int(b3: str) -> int:
    """
    Map 3 DNA bases to an integer in [0,63] using 2-bit coding A,C,G,T -> 0..3.
    Unknown bases are treated as A (0) to keep determinism.
    """
    b3 = str(b3)
    if len(b3) != 3:
        raise ValueError("b3 must have length 3")
    v = 0
    for ch in b3:
        v = (v << 2) | int(_BASE_TO_CODE.get(ch, 0))
    return int(v)


def _take(seq: str, start: int, n: int) -> str:
    seq = str(seq)
    if not seq:
        return ""
    start = int(start)
    n = int(n)
    if n <= 0:
        return ""
    L = len(seq)
    return "".join(seq[(start + i) % L] for i in range(n))


def _m_events_default() -> str:
    # Matches the original figure's piecewise-constant schedule (by coarse scan index k).
    return "18:8,20:10,23:8,27:6"


def _parse_m_events(m_events: str) -> list[tuple[int, int]]:
    """
    Parse a comma-separated list like: "18:8,20:10,23:8,27:6".
    Meaning: at coarse scan index k, set m to the given value until the next event.
    """
    s = str(m_events).strip()
    if not s:
        return []
    events: list[tuple[int, int]] = []
    for chunk in s.split(","):
        t = chunk.strip()
        if not t:
            continue
        if ":" not in t:
            raise ValueError(f"Bad m-event '{t}', expected k:m")
        a, b = t.split(":", 1)
        k = int(a.strip())
        m = int(b.strip())
        if m not in (6, 8, 10):
            raise ValueError("This centerwired visualization supports m in {6,8,10} only.")
        if k < 0 or k > 63:
            raise ValueError("m-event k must be in [0,63].")
        events.append((k, m))
    events.sort(key=lambda km: int(km[0]))
    return events


def _m_by_k_from_events(events: list[tuple[int, int]]) -> dict[int, int]:
    m_by_k = {k: 6 for k in range(64)}
    if not events:
        return m_by_k
    # Apply piecewise constant across k in [0,63].
    for i, (k0, m0) in enumerate(events):
        k1 = events[i + 1][0] if i + 1 < len(events) else 64
        for k in range(int(k0), int(k1)):
            if 0 <= k <= 63:
                m_by_k[int(k)] = int(m0)
    return m_by_k


def _centerwired_decode_codon(seq_dna: str, start_base: int, k: int, *, mu: dict[str, str]) -> CodonFold:
    """
    Centerwired coarse token = one codon (3 bases). We treat DNA as RNA by T->U.
    """
    b0 = _take(seq_dna, int(start_base) + 3 * int(k), 3)
    codon = b0.upper().replace("T", "U")
    return fold_codon(codon, mu)


def _centerwired_m_by_k_from_gates(
    *,
    seq_dna: str,
    start_base: int,
    mu: dict[str, str],
    delta_to_m10: set[int],
) -> tuple[dict[int, int], dict[str, list[int]]]:
    """
    Derive the m schedule from control symbols in the Fold_6 stream.

    Control symbols (the 3 boundary words):
      - 101001 : uplift marker (enter refined mode, default m=8)
      - 100101 : downlift marker (exit refined mode, set m=6)
      - 100001 : reset marker (treat as start/end; also sets m=6)

    Rule:
      - boundary cells are control records; they are not refined (m=6).
      - inside refined mode, payload cells use m=10 iff Δ ∈ delta_to_m10, else m=8.
    """
    gates: dict[str, list[int]] = {w: [] for w in sorted(BOUNDARY_WORDS)}
    m_by_k = {k: 6 for k in range(64)}
    refined = False
    for k in range(64):
        f = _centerwired_decode_codon(seq_dna, start_base, k, mu=mu)
        if f.w in gates:
            gates[f.w].append(int(k))
        if f.w == "101001":
            refined = True
            m_by_k[int(k)] = 6
            continue
        if f.w == "100101":
            refined = False
            m_by_k[int(k)] = 6
            continue
        if f.w == "100001":
            refined = False
            m_by_k[int(k)] = 6
            continue
        if refined:
            m_by_k[int(k)] = 10 if int(f.delta) in delta_to_m10 else 8
        else:
            m_by_k[int(k)] = 6
    return m_by_k, gates


def _symmetry_transforms(S: int):
    m = int(S) - 1

    def t0(x: int, y: int) -> tuple[int, int]:
        return (x, y)

    def t1(x: int, y: int) -> tuple[int, int]:
        return (y, m - x)

    def t2(x: int, y: int) -> tuple[int, int]:
        return (m - x, m - y)

    def t3(x: int, y: int) -> tuple[int, int]:
        return (m - y, x)

    def t4(x: int, y: int) -> tuple[int, int]:
        return (m - x, y)

    def t5(x: int, y: int) -> tuple[int, int]:
        return (x, m - y)

    def t6(x: int, y: int) -> tuple[int, int]:
        return (y, x)

    def t7(x: int, y: int) -> tuple[int, int]:
        return (m - y, m - x)

    return [t0, t1, t2, t3, t4, t5, t6, t7]


def _dir_to_entry_target(dx: int, dy: int) -> tuple[float, float]:
    # normalized target on boundary of (0..1)^2
    if dx == 1 and dy == 0:
        return (0.0, 0.5)  # enter from left
    if dx == -1 and dy == 0:
        return (1.0, 0.5)  # enter from right
    if dx == 0 and dy == 1:
        return (0.5, 0.0)  # enter from bottom
    if dx == 0 and dy == -1:
        return (0.5, 1.0)  # enter from top
    return (0.5, 0.5)


def _dir_to_exit_target(dx: int, dy: int) -> tuple[float, float]:
    if dx == 1 and dy == 0:
        return (1.0, 0.5)  # exit to right
    if dx == -1 and dy == 0:
        return (0.0, 0.5)  # exit to left
    if dx == 0 and dy == 1:
        return (0.5, 1.0)  # exit to top
    if dx == 0 and dy == -1:
        return (0.5, 0.0)  # exit to bottom
    return (0.5, 0.5)


def _candidate_micro_orders_for_cell(*, S: int, d_in: tuple[int, int], d_out: tuple[int, int]) -> list[list[tuple[int, int]]]:
    """
    Enumerate candidate micro Hilbert orders for an SxS subgrid.
    Canonical order is d=0..S^2-1 via hilbert_d2xy; then try 8 symmetries and reversal,
    scoring by entry/exit alignment with coarse directions.
    """
    if S not in (2, 4):
        raise ValueError("This centerwired visualization supports S in {2,4} only (m=8/10).")
    sub_path0 = [hilbert_d2xy(S, d) for d in range(S * S)]
    entry_t = _dir_to_entry_target(int(d_in[0]), int(d_in[1]))
    exit_t = _dir_to_exit_target(int(d_out[0]), int(d_out[1]))

    scored: list[tuple[float, list[tuple[int, int]]]] = []
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
            ds = float(math.hypot(s_norm[0] - entry_t[0], s_norm[1] - entry_t[1]))
            de = float(math.hypot(e_norm[0] - exit_t[0], e_norm[1] - exit_t[1]))
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


def _pt_eq(a: tuple[float, float], b: tuple[float, float], eps: float = 1e-9) -> bool:
    return abs(float(a[0]) - float(b[0])) <= eps and abs(float(a[1]) - float(b[1])) <= eps


def _seg_bbox(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float, float, float]:
    x0 = min(float(a[0]), float(b[0]))
    x1 = max(float(a[0]), float(b[0]))
    y0 = min(float(a[1]), float(b[1]))
    y1 = max(float(a[1]), float(b[1]))
    return (x0, x1, y0, y1)


def _segments_overlap_strict(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
    *,
    eps: float = 1e-9,
) -> bool:
    """
    Return True if two segments overlap in a visually problematic way:
    - proper intersection (crossing) not at endpoints, OR
    - colinear overlap with positive-length interior intersection.
    Endpoint-touching is NOT counted as overlap.
    """
    # Ignore degenerate segments.
    if _pt_eq(a1, a2, eps) or _pt_eq(b1, b2, eps):
        return False

    # Fast reject by bbox.
    ax0, ax1, ay0, ay1 = _seg_bbox(a1, a2)
    bx0, bx1, by0, by1 = _seg_bbox(b1, b2)
    if ax1 < bx0 - eps or bx1 < ax0 - eps or ay1 < by0 - eps or by1 < ay0 - eps:
        return False

    # Treat axis-aligned segments specially (our wiring is almost always axis-aligned).
    a_dx = float(a2[0] - a1[0])
    a_dy = float(a2[1] - a1[1])
    b_dx = float(b2[0] - b1[0])
    b_dy = float(b2[1] - b1[1])
    a_vert = abs(a_dx) <= eps and abs(a_dy) > eps
    a_horz = abs(a_dy) <= eps and abs(a_dx) > eps
    b_vert = abs(b_dx) <= eps and abs(b_dy) > eps
    b_horz = abs(b_dy) <= eps and abs(b_dx) > eps

    # Helper: endpoint-touching check.
    def is_endpoint_touch(ix: tuple[float, float]) -> bool:
        return _pt_eq(ix, a1, eps) or _pt_eq(ix, a2, eps) or _pt_eq(ix, b1, eps) or _pt_eq(ix, b2, eps)

    if (a_vert or a_horz) and (b_vert or b_horz):
        # Colinear vertical
        if a_vert and b_vert and abs(float(a1[0]) - float(b1[0])) <= eps:
            # overlap on y
            y0 = max(ay0, by0)
            y1 = min(ay1, by1)
            if y1 - y0 > eps:
                # Any positive-length colinear overlap (including exact retracing) is disallowed.
                return True
            return False
        # Colinear horizontal
        if a_horz and b_horz and abs(float(a1[1]) - float(b1[1])) <= eps:
            x0 = max(ax0, bx0)
            x1 = min(ax1, bx1)
            if x1 - x0 > eps:
                # Any positive-length colinear overlap (including exact retracing) is disallowed.
                return True
            return False
        # Perpendicular crossing
        if a_vert and b_horz:
            ix = (float(a1[0]), float(b1[1]))
            if (bx0 - eps) <= ix[0] <= (bx1 + eps) and (ay0 - eps) <= ix[1] <= (ay1 + eps):
                return not is_endpoint_touch(ix)
            return False
        if a_horz and b_vert:
            ix = (float(b1[0]), float(a1[1]))
            if (ax0 - eps) <= ix[0] <= (ax1 + eps) and (by0 - eps) <= ix[1] <= (by1 + eps):
                return not is_endpoint_touch(ix)
            return False

    # Generic segment intersection (fallback for rare diagonal cases).
    def orient(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
        return (float(q[0]) - float(p[0])) * (float(r[1]) - float(p[1])) - (float(q[1]) - float(p[1])) * (float(r[0]) - float(p[0]))

    def on_segment(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> bool:
        # q on pr
        px0, px1, py0, py1 = _seg_bbox(p, r)
        return (px0 - eps) <= float(q[0]) <= (px1 + eps) and (py0 - eps) <= float(q[1]) <= (py1 + eps)

    o1 = orient(a1, a2, b1)
    o2 = orient(a1, a2, b2)
    o3 = orient(b1, b2, a1)
    o4 = orient(b1, b2, a2)

    # Proper intersection
    if (o1 > eps and o2 < -eps) or (o1 < -eps and o2 > eps):
        if (o3 > eps and o4 < -eps) or (o3 < -eps and o4 > eps):
            return True

    # Colinear / touching cases (count only if interior overlap, not single endpoint).
    if abs(o1) <= eps and on_segment(a1, b1, a2):
        return not (_pt_eq(b1, a1, eps) or _pt_eq(b1, a2, eps))
    if abs(o2) <= eps and on_segment(a1, b2, a2):
        return not (_pt_eq(b2, a1, eps) or _pt_eq(b2, a2, eps))
    if abs(o3) <= eps and on_segment(b1, a1, b2):
        return not (_pt_eq(a1, b1, eps) or _pt_eq(a1, b2, eps))
    if abs(o4) <= eps and on_segment(b1, a2, b2):
        return not (_pt_eq(a2, b1, eps) or _pt_eq(a2, b2, eps))
    return False


def _center_point_in_cell(cell_x: int, cell_y: int, cell_px: int) -> tuple[float, float]:
    return ((float(cell_x) + 0.5) * float(cell_px), (float(cell_y) + 0.5) * float(cell_px))


def _center_point_in_subcell(cell_x: int, cell_y: int, cell_px: int, S: int, xx: int, yy: int) -> tuple[float, float]:
    step = float(cell_px) / float(S)
    x0 = float(cell_x) * float(cell_px)
    y0 = float(cell_y) * float(cell_px)
    return (x0 + (float(xx) + 0.5) * step, y0 + (float(yy) + 0.5) * step)


def _render_frame_centerwired(
    *,
    seq_dna: str,
    start_base: int,
    cell_px: int,
    m_by_k: dict[int, int],
    title: str,
    show_labels: bool = True,
    show_wiring: bool = True,
    mu: dict[str, str] | None = None,
    gates: dict[str, list[int]] | None = None,
) -> np.ndarray:
    """
    Center-wired visualization on an 8x8 coarse Hilbert screen (m=6 base, local m=8/10 refinements).
    - Each coarse cell consumes 3 bases (6 bits) as the prefix u6 (3-mer).
    - If m=8: emit a microblock of length 4 (2x2) with 1-base suffix per microcell.
    - If m=10: emit a microblock of length 16 (4x4) with 2-base suffix per microcell.
    The wiring is a single stroke connecting centers in scan order, and refined cells embed a micro Hilbert stroke.
    """
    seq_dna = normalize_dna(seq_dna)
    if not seq_dna:
        raise ValueError("Empty DNA sequence after normalization.")
    # Colors encode Fold_6 stable types (21 words), not raw 6-bit indices.
    x6 = x_m(6)
    pal21 = _material_palette_21()
    w_to_col = {w: pal21[i % len(pal21)] for i, w in enumerate(x6)}
    bg = np.array([0.05, 0.07, 0.09], dtype=np.float32)

    # Coarse Hilbert positions.
    path_xy = [hilbert_d2xy(8, d) for d in range(64)]
    k_to_xy = {k: (int(x), int(y)) for k, (x, y) in enumerate(path_xy)}

    # Coarse entry/exit directions for micro alignment.
    dirs_in_out: dict[int, tuple[tuple[int, int], tuple[int, int]]] = {}
    for k in range(64):
        x, y = path_xy[k]
        xp, yp = path_xy[(k - 1) % 64]
        xn, yn = path_xy[(k + 1) % 64]
        d_in = (int(x - xp), int(y - yp))
        d_out = (int(xn - x), int(yn - y))
        dirs_in_out[int(k)] = (d_in, d_out)

    # Paint base image at pixel resolution.
    H = 8 * int(cell_px)
    W = 8 * int(cell_px)
    base_rgb = np.zeros((H, W, 3), dtype=np.float32)
    base_rgb[:, :, :] = bg[None, None, :]

    # Decode into per-cell payloads and build wiring nodes.
    wire_pts: list[tuple[float, float]] = []
    wire_kind: list[str] = []  # "macro", "micro8", "micro10"
    # Track already added segments for overlap avoidance (centerwired refinement).
    wire_segs: list[tuple[tuple[float, float], tuple[float, float]]] = []

    pos = int(start_base)
    macro_info: dict[int, dict[str, object]] = {}

    if mu is None:
        mu = {"A": "00", "C": "01", "G": "10", "U": "11"}  # μ*

    # ---- Pass 1: decode cells, paint coarse backgrounds, cache refinement payloads ----
    refined_cells: dict[int, dict[str, object]] = {}

    for k in range(64):
        x, y = k_to_xy[int(k)]
        m_sched = int(m_by_k.get(int(k), 6))
        b3 = _take(seq_dna, pos, 3)
        pos += 3
        f = fold_codon(b3.replace("T", "U"), mu)  # codon fold; defines 18+3 control split
        u6 = int(f.n)  # 0..63 microstate index under μ
        is_ctrl = bool(f.w in BOUNDARY_WORDS)
        # Enforce: control records are not refined (m=6), regardless of schedule.
        m = 6 if is_ctrl else m_sched

        # Color by stable type w in X6 (21).
        col = np.array(w_to_col.get(str(f.w), (0.75, 0.75, 0.75)), dtype=np.float32)
        x0 = int(x * cell_px)
        y0 = int(y * cell_px)
        x1 = int((x + 1) * cell_px)
        y1 = int((y + 1) * cell_px)
        base_rgb[y0:y1, x0:x1, :] = col[None, None, :]

        macro_info[int(k)] = {
            "b3": b3,
            "u6": u6,
            "m": m,
            "w": str(f.w),
            "delta": int(f.delta),
            "boundary": bool(is_ctrl),
            "m_sched": int(m_sched),
            "x": int(x),
            "y": int(y),
            "col": (float(col[0]), float(col[1]), float(col[2])),
        }

        if m in (8, 10):
            S = 2 if m == 8 else 4
            (d_in, d_out) = dirs_in_out[int(k)]
            micro_orders = _candidate_micro_orders_for_cell(S=S, d_in=d_in, d_out=d_out)
            # Cache the suffix bases for microcells (order-independent consumption).
            if m == 8:
                suffix = [_take(seq_dna, pos + i, 1) for i in range(4)]
                pos += 4
            else:
                suffix = [_take(seq_dna, pos + i, 1) for i in range(32)]
                pos += 32
            refined_cells[int(k)] = {
                "m": int(m),
                "S": int(S),
                "micro_orders": micro_orders,
                "suffix": suffix,
            }

    bases_consumed = int(pos - int(start_base))

    # ---- Pass 2: choose micro orders by backtracking to avoid any overlaps ----
    chosen_orders: dict[int, list[tuple[int, int]]] = {}

    def _try_add_point(pt: tuple[float, float], kind: str) -> bool:
        # Add pt and the induced segment; reject if it overlaps any existing segment.
        if wire_pts:
            a1 = wire_pts[-1]
            a2 = pt
            for (b1, b2) in wire_segs:
                if _segments_overlap_strict(a1, a2, b1, b2):
                    return False
        wire_pts.append(pt)
        wire_kind.append(str(kind))
        if len(wire_pts) >= 2:
            wire_segs.append((wire_pts[-2], wire_pts[-1]))
        return True

    def _rollback(n_pts: int, n_segs: int, n_kinds: int) -> None:
        del wire_pts[n_pts:]
        del wire_kind[n_kinds:]
        del wire_segs[n_segs:]

    def _build(k: int) -> bool:
        if k >= 64:
            return True

        x = int(macro_info[int(k)]["x"])
        y = int(macro_info[int(k)]["y"])
        m_eff = int(macro_info[int(k)]["m"])

        if m_eff == 6:
            n_pts, n_segs, n_kinds = len(wire_pts), len(wire_segs), len(wire_kind)
            if not _try_add_point(_center_point_in_cell(x, y, cell_px), "macro"):
                return False
            if _build(k + 1):
                return True
            _rollback(n_pts, n_segs, n_kinds)
            return False

        info = refined_cells.get(int(k))
        if info is None:
            # Should not happen; be safe.
            return False
        m_eff = int(info["m"])
        S = int(info["S"])
        micro_orders = info["micro_orders"]  # type: ignore[assignment]
        assert isinstance(micro_orders, list)
        kind = "micro8" if m_eff == 8 else "micro10"

        for cand in micro_orders:
            n_pts, n_segs, n_kinds = len(wire_pts), len(wire_segs), len(wire_kind)
            ok = True
            # Add micro points in candidate order. The entry segment is the natural
            # segment from previous point to the first micro point (a straight line).
            for (xx, yy) in cand:
                pt = _center_point_in_subcell(x, y, cell_px, S, int(xx), int(yy))
                if not _try_add_point(pt, kind):
                    ok = False
                    break
            if ok:
                chosen_orders[int(k)] = [(int(xx), int(yy)) for (xx, yy) in cand]
                if _build(k + 1):
                    return True
                chosen_orders.pop(int(k), None)
            _rollback(n_pts, n_segs, n_kinds)
        return False

    if not _build(0):
        raise ValueError("Failed to find a non-overlapping wiring using only micro Hilbert rotations/reflections/reversal.")

    # Final verification: no overlaps anywhere (including exact retracing).
    for i in range(len(wire_segs)):
        a1, a2 = wire_segs[i]
        for j in range(i + 1, len(wire_segs)):
            if abs(j - i) <= 1:
                continue
            b1, b2 = wire_segs[j]
            if _segments_overlap_strict(a1, a2, b1, b2):
                raise ValueError("Internal error: wiring overlap remained after backtracking.")

    # ---- Pass 3: paint microblocks using chosen orders (no effect on wiring geometry) ----
    for k, info in refined_cells.items():
        x = int(macro_info[int(k)]["x"])
        y = int(macro_info[int(k)]["y"])
        x0 = int(x * cell_px)
        y0 = int(y * cell_px)
        m_eff = int(info["m"])
        S = int(info["S"])
        suffix = info["suffix"]  # type: ignore[assignment]
        assert isinstance(suffix, list)
        ord_xy = chosen_orders.get(int(k))
        if ord_xy is None:
            continue
        col_tup = macro_info[int(k)]["col"]
        col = np.array([float(col_tup[0]), float(col_tup[1]), float(col_tup[2])], dtype=np.float32)

        if m_eff == 8:
            for i, (xx, yy) in enumerate(ord_xy):
                b1 = str(suffix[i]) if i < len(suffix) else "A"
                code = int(_BASE_TO_CODE.get(b1, 0))
                t = 0.25 + 0.75 * (float(code) / 3.0)
                step_x0 = x0 + int(xx) * (cell_px // S)
                step_y0 = y0 + int(yy) * (cell_px // S)
                step_x1 = x0 + (int(xx) + 1) * (cell_px // S)
                step_y1 = y0 + (int(yy) + 1) * (cell_px // S)
                base_rgb[step_y0:step_y1, step_x0:step_x1, :] = np.clip(col * float(t), 0.0, 1.0)
        else:
            for i, (xx, yy) in enumerate(ord_xy):
                j = 2 * i
                b2 = (str(suffix[j]) if j < len(suffix) else "A") + (str(suffix[j + 1]) if (j + 1) < len(suffix) else "A")
                code = _bases_to_u6_int("A" + b2) & 0x0F
                t = 0.25 + 0.75 * (float(code) / 15.0)
                step_x0 = x0 + int(xx) * (cell_px // S)
                step_y0 = y0 + int(yy) * (cell_px // S)
                step_x1 = x0 + (int(xx) + 1) * (cell_px // S)
                step_y1 = y0 + (int(yy) + 1) * (cell_px // S)
                base_rgb[step_y0:step_y1, step_x0:step_x1, :] = np.clip(col * float(t), 0.0, 1.0)

    # Render as a figure with wiring overlay.
    fig = plt.figure(figsize=(12.4, 7.6), dpi=160)
    ax = fig.add_axes([0.05, 0.10, 0.62, 0.84])
    ax.imshow(np.repeat(np.repeat(base_rgb, 1, axis=0), 1, axis=1), origin="lower", interpolation="nearest")
    ax.set_xticks([])
    ax.set_yticks([])

    # Coarse grid.
    for i in range(9):
        ax.plot([0, W], [i * cell_px, i * cell_px], color="#ECEFF1", lw=0.8, alpha=0.55, zorder=2)
        ax.plot([i * cell_px, i * cell_px], [0, H], color="#ECEFF1", lw=0.8, alpha=0.55, zorder=2)

    if show_wiring and len(wire_pts) >= 2:
        segs: list[list[tuple[float, float]]] = []
        widths: list[float] = []
        for i in range(len(wire_pts) - 1):
            a = wire_pts[i]
            b = wire_pts[i + 1]
            segs.append([a, b])
            ka = wire_kind[i]
            kb = wire_kind[i + 1]
            if ka.startswith("micro") and kb.startswith("micro"):
                widths.append(1.2 if ("10" in ka or "10" in kb) else 1.5)
            else:
                widths.append(2.4)
        lc = LineCollection(segs, colors="#FFFFFF", linewidths=widths, alpha=0.78, zorder=8)
        ax.add_collection(lc)

    if show_labels:
        for k in range(64):
            x, y = k_to_xy[int(k)]
            x0 = int(x * cell_px)
            y0 = int(y * cell_px)
            info = macro_info[int(k)]
            b3 = str(info["b3"])
            u6 = int(info["u6"])
            m = int(info["m"])
            w6 = str(info["w"])
            dlt = int(info["delta"])
            bd = bool(info["boundary"])
            tag = "CTRL" if bd else "DATA"
            # Keep labels short and clipped to the cell to avoid overlap.
            if bd:
                lab = f"{b3}\nCTRL"
            elif m > 6:
                lab = f"{b3} N{u6:02d}\nΔ{dlt:02d} m{m}"
            else:
                lab = f"{b3}"
            clip_rect = Rectangle((x0, y0), cell_px, cell_px, transform=ax.transData)
            ax.text(
                x0 + 2,
                y0 + cell_px - 2,
                lab,
                fontsize=6.2,
                color="#111111",
                ha="left",
                va="top",
                linespacing=1.05,
                bbox=dict(facecolor=(1, 1, 1, 0.18), edgecolor="none", pad=0.6),
                clip_on=True,
                clip_path=clip_rect,
                zorder=9,
            )

    axr = fig.add_axes([0.70, 0.12, 0.27, 0.80])
    axr.axis("off")
    # Count effective m values (after control-word forcing).
    n_m8 = sum(1 for k in range(64) if int(macro_info[int(k)]["m"]) == 8)
    n_m10 = sum(1 for k in range(64) if int(macro_info[int(k)]["m"]) == 10)
    axr.text(0.0, 0.98, title, fontsize=12, color="#263238", va="top")
    axr.text(0.0, 0.90, "scheme = centerwired (8x8 coarse Hilbert)", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.85, f"m uplifts: m=8 cells={n_m8}, m=10 cells={n_m10}", fontsize=10, color="#455A64", va="top")
    if gates is not None:
        axr.text(0.0, 0.80, f"control words (18+3): {', '.join(sorted(BOUNDARY_WORDS))}", fontsize=9.5, color="#455A64", va="top")
        axr.text(
            0.0,
            0.75,
            "gate hits: " + "; ".join(f"{w}:{len(gates.get(w, []))}" for w in sorted(BOUNDARY_WORDS)),
            fontsize=9.5,
            color="#455A64",
            va="top",
        )
        axr.text(
            0.0,
            0.70,
            "gate positions k: " + "; ".join(f"{w}:{gates.get(w, [])}" for w in sorted(BOUNDARY_WORDS)),
            fontsize=8.5,
            color="#455A64",
            va="top",
        )
    axr.text(0.0, 0.62, f"start_base = {int(start_base)}", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.56, f"bases consumed (cyclic) ≈ {int(bases_consumed)}", fontsize=10, color="#455A64", va="top")
    axr.text(
        0.0,
        0.44,
        "wiring:\n"
        "- single continuous stroke (no overlaps)\n"
        "- refined cells embed micro Hilbert strokes\n"
        "encoding:\n"
        "- per coarse cell: 3-mer prefix (6 bits)\n"
        "- m=8: 2x2 microblock (1-base suffix)\n"
        "- m=10: 4x4 microblock (2-base suffix)\n"
        "colors:\n"
        "- Fold_6 stable types (X6, 21 words)\n"
        "rule:\n"
        "- control (boundary) cells forced to m=6",
        fontsize=9,
        color="#455A64",
        va="top",
    )

    fig.suptitle("DNA center-wired Hilbert decoder (m uplift/downlift + microstructure)", fontsize=14, y=0.98)
    fig.canvas.draw()
    ww, hh = fig.canvas.get_width_height()
    buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8).reshape((hh, ww, 4))
    rgba = buf[:, :, [1, 2, 3, 0]]
    plt.close(fig)
    return rgba


def _render_frame_base(
    *,
    seq_dna: str,
    start: int,
    n_side: int,
    scale: int,
    draw_path: bool,
    title: str,
) -> np.ndarray:
    pal = _material_palette_base()
    bg = (0.05, 0.07, 0.09)
    n_pix = int(n_side * n_side)
    tile = seq_dna[int(start) : int(start) + n_pix]

    img = np.zeros((n_side, n_side, 3), dtype=np.float32)
    img[:, :, 0] = bg[0]
    img[:, :, 1] = bg[1]
    img[:, :, 2] = bg[2]

    for i, ch in enumerate(tile):
        x, y = hilbert_d2xy(n_side, i)
        c = pal.get(ch, pal["N"])
        img[y, x, 0] = float(c[0])
        img[y, x, 1] = float(c[1])
        img[y, x, 2] = float(c[2])

    # Upscale pixels by repetition (fast enough for our sizes).
    img_up = np.repeat(np.repeat(img, scale, axis=0), scale, axis=1)

    fig = plt.figure(figsize=(12.0, 7.1), dpi=160)
    ax = fig.add_axes([0.05, 0.10, 0.62, 0.84])
    ax.imshow(img_up, origin="lower", interpolation="nearest")
    ax.set_xticks([])
    ax.set_yticks([])

    if draw_path:
        _draw_path_overlay(ax, n_side, scale, step=max(8, n_side // 4))

    axr = fig.add_axes([0.70, 0.12, 0.27, 0.80])
    axr.axis("off")
    n_used = len(tile)
    gc = sum(1 for c in tile if c in ("G", "C"))
    a = tile.count("A")
    c = tile.count("C")
    g = tile.count("G")
    t = tile.count("T")
    axr.text(0.0, 0.98, title, fontsize=12, color="#263238", va="top")
    axr.text(0.0, 0.90, f"mode = base (DNA)", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.85, f"grid = {n_side} x {n_side} (Hilbert order)", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.80, f"start = {int(start)} bases", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.75, f"tile length = {n_used}/{n_pix} bases", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.69, f"counts: A={a} C={c} G={g} T={t}", fontsize=10, color="#455A64", va="top")
    axr.text(
        0.0,
        0.63,
        f"GC fraction = {((gc / n_used) if n_used else float('nan')):.4f}",
        fontsize=10,
        color="#455A64",
        va="top",
    )
    axr.text(
        0.0,
        0.52,
        "Interpretation:\n"
        "- 1D sequence is laid along Hilbert path\n"
        "- local motifs produce local clusters on the plane\n"
        "- use tiles to scan long sequences",
        fontsize=9,
        color="#455A64",
        va="top",
    )

    fig.suptitle("DNA sequence decoded on a Hilbert plane (tile view)", fontsize=14, y=0.98)
    fig.canvas.draw()
    ww, hh = fig.canvas.get_width_height()
    buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8).reshape((hh, ww, 4))
    rgba = buf[:, :, [1, 2, 3, 0]]
    plt.close(fig)
    return rgba


def _render_frame_codon(
    *,
    seq_rna: str,
    frame: int,
    start_codon: int,
    n_side: int,
    scale: int,
    draw_path: bool,
    title: str,
) -> np.ndarray:
    pal = _aa_palette()
    bg = (0.05, 0.07, 0.09)
    n_pix = int(n_side * n_side)
    cods = codons(seq_rna, frame=int(frame))
    tile = cods[int(start_codon) : int(start_codon) + n_pix]

    img = np.zeros((n_side, n_side, 3), dtype=np.float32)
    img[:, :, 0] = bg[0]
    img[:, :, 1] = bg[1]
    img[:, :, 2] = bg[2]

    aa_counts: dict[str, int] = {}
    stop = 0
    for i, c3 in enumerate(tile):
        aa = GENETIC_CODE.get(c3, "NA")
        aa_counts[aa] = int(aa_counts.get(aa, 0)) + 1
        if aa == "Stop":
            stop += 1
        x, y = hilbert_d2xy(n_side, i)
        col = pal.get(aa, pal["NA"])
        img[y, x, 0] = float(col[0])
        img[y, x, 1] = float(col[1])
        img[y, x, 2] = float(col[2])

    img_up = np.repeat(np.repeat(img, scale, axis=0), scale, axis=1)

    fig = plt.figure(figsize=(12.0, 7.1), dpi=160)
    ax = fig.add_axes([0.05, 0.10, 0.62, 0.84])
    ax.imshow(img_up, origin="lower", interpolation="nearest")
    ax.set_xticks([])
    ax.set_yticks([])

    if draw_path:
        _draw_path_overlay(ax, n_side, scale, step=max(8, n_side // 4))

    axr = fig.add_axes([0.70, 0.12, 0.27, 0.80])
    axr.axis("off")
    n_used = len(tile)
    axr.text(0.0, 0.98, title, fontsize=12, color="#263238", va="top")
    axr.text(0.0, 0.90, f"mode = codon (RNA)  frame = {int(frame)}", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.85, f"grid = {n_side} x {n_side} (Hilbert order)", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.80, f"start = {int(start_codon)} codons", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.75, f"tile length = {n_used}/{n_pix} codons", fontsize=10, color="#455A64", va="top")
    axr.text(0.0, 0.69, f"Stop codons in tile = {stop}", fontsize=10, color="#455A64", va="top")

    # Show top-8 AAs by count for quick reading.
    tops = sorted(aa_counts.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))[:8]
    y = 0.60
    axr.text(0.0, y, "Top symbols:", fontsize=10, color="#455A64", va="top")
    y -= 0.05
    for aa, cnt in tops:
        axr.text(0.02, y, f"{aa}: {cnt}", fontsize=10, color="#455A64", va="top")
        y -= 0.045

    fig.suptitle("DNA/RNA decoded as codons on a Hilbert plane (tile view)", fontsize=14, y=0.98)
    fig.canvas.draw()
    ww, hh = fig.canvas.get_width_height()
    buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8).reshape((hh, ww, 4))
    rgba = buf[:, :, [1, 2, 3, 0]]
    plt.close(fig)
    return rgba


def _rgba_to_pil(rgba: np.ndarray):
    if not _HAS_PIL:
        raise RuntimeError("Pillow not available")
    assert Image is not None
    im = Image.fromarray(rgba, mode="RGBA").convert("P", palette=Image.Palette.ADAPTIVE)
    return im


def _render_contact_sheet(gif_path: Path, out_png: Path, rows: int = 3, cols: int = 4) -> None:
    if not _HAS_PIL:
        return
    assert Image is not None
    im = Image.open(gif_path)
    n = int(getattr(im, "n_frames", 1))
    if n <= 1:
        # Nothing to sample; keep the pipeline robust for quick 1-frame runs.
        return
    k = int(rows) * int(cols)
    idxs = [int(round(i * (n - 1) / float(max(1, k - 1)))) for i in range(k)]
    frames = []
    for j in idxs:
        im.seek(j)
        frames.append(im.convert("RGB"))
    w, h = frames[0].size
    margin = 10
    head_h = 36
    W = int(cols) * w + (int(cols) + 1) * margin
    H = int(rows) * h + (int(rows) + 1) * margin + head_h
    canvas = Image.new("RGB", (W, H), color=(255, 255, 255))

    # Title band using matplotlib (consistent typography).
    fig = plt.figure(figsize=(W / 140.0, head_h / 140.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.text(0.5, 0.5, "contact sheet (sampled frames): DNA Hilbert tiles", ha="center", va="center", fontsize=13, color="#263238")
    fig.canvas.draw()
    ww, hh = fig.canvas.get_width_height()
    buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8).reshape((hh, ww, 4))
    rgba = buf[:, :, [1, 2, 3, 0]]
    title_img = Image.fromarray(rgba, mode="RGBA").convert("RGB")
    plt.close(fig)
    canvas.paste(title_img, (0, 0))

    y0 = head_h
    for r in range(int(rows)):
        for c in range(int(cols)):
            idx = r * int(cols) + c
            x = margin + c * (w + margin)
            y = y0 + margin + r * (h + margin)
            canvas.paste(frames[idx], (x, y))
    _ensure_dir(out_png.parent)
    canvas.save(out_png, format="PNG", optimize=False)


# -------------------------
# CLI
# -------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Decode DNA/RNA and visualize on a Hilbert curve grid.")
    p.add_argument("--fasta", type=str, default=None, help="Input FASTA path (first record is used).")
    p.add_argument("--seq", type=str, default=None, help="Raw sequence string (DNA/RNA).")
    p.add_argument("--name", type=str, default=None, help="Optional label for figure titles.")

    p.add_argument(
        "--scheme",
        type=str,
        default="tile",
        choices=["tile", "centerwired"],
        help="Visualization scheme: tile (generic Hilbert fill) or centerwired (8x8 + m uplift/downlift + one-stroke wiring).",
    )

    p.add_argument("--mode", type=str, default="base", choices=["base", "codon"], help="Decoding mode.")
    p.add_argument("--frame", type=int, default=0, help="Reading frame for codon mode (0/1/2).")

    p.add_argument("--n-bits", type=int, default=8, help="Hilbert order n, grid side = 2^n.")
    p.add_argument("--scale", type=int, default=3, help="Pixel upscale factor for display (nearest).")
    p.add_argument("--draw-path", action="store_true", help="Overlay a faint Hilbert wiring (subsampled).")

    p.add_argument("--frames", type=int, default=12, help="Number of frames to render (tiles along sequence).")
    p.add_argument("--stride", type=int, default=0, help="Stride between frames (bases for base-mode; codons for codon-mode). 0 means one full tile.")
    p.add_argument("--start", type=int, default=0, help="Start offset (bases for base-mode; codons for codon-mode).")

    p.add_argument(
        "--m-events",
        type=str,
        default=_m_events_default(),
        help="Centerwired m schedule as comma-separated k:m events (k in [0,63], m in {6,8,10}).",
    )
    p.add_argument(
        "--m-policy",
        type=str,
        default="gates",
        choices=["gates", "events"],
        help="(centerwired) How to decide m: gates (18+3 control symbols) or events (fixed k:m schedule).",
    )
    p.add_argument(
        "--delta-m10",
        type=str,
        default="55",
        help="(centerwired, m-policy=gates) Comma-separated Δ values that trigger m=10 inside refined mode (default: 55).",
    )
    p.add_argument("--no-labels", action="store_true", help="(centerwired) Disable per-cell labels.")
    p.add_argument("--no-wiring", action="store_true", help="(centerwired) Disable one-stroke wiring overlay.")

    p.add_argument("--out-prefix", type=str, default=str(figures_dir() / "dna_hilbert"), help="Output prefix (no extension).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    scheme = str(args.scheme)
    mode = str(args.mode)

    n_bits = int(args.n_bits)
    if n_bits < 1 or n_bits > 12:
        raise SystemExit("--n-bits must be in [1,12] for practical rendering.")
    n_side = 1 << n_bits
    scale = max(1, int(args.scale))
    n_frames = max(1, int(args.frames))
    draw_path = bool(args.draw_path)

    name, raw = _load_sequence(fasta_path=Path(args.fasta) if args.fasta else None, seq=args.seq)
    label = str(args.name) if args.name else name

    out_prefix = Path(args.out_prefix)
    _ensure_dir(out_prefix.parent)
    out_frames_dir = out_prefix.parent / (out_prefix.name + "_frames")
    _ensure_dir(out_frames_dir)

    # Legend. For centerwired, use a Fold_6 (21-type) palette legend.
    out_legend = out_prefix.parent / (out_prefix.name + "_legend.png")
    if scheme == "centerwired":
        _render_legend_centerwired(out_png=out_legend)
    else:
        _render_legend(mode=mode, out_png=out_legend)

    # Determine stride.
    tile_len = int(n_side * n_side)
    stride = int(args.stride)
    if stride <= 0:
        stride = tile_len

    start = int(args.start)
    frames_rgba: list[np.ndarray] = []

    if scheme == "centerwired":
        if mode != "base":
            raise SystemExit("scheme=centerwired currently supports --mode base only (DNA).")
        mu_star = {"A": "00", "C": "01", "G": "10", "U": "11"}
        delta_to_m10: set[int] = set()
        for p in str(args.delta_m10).split(","):
            p = p.strip()
            if not p:
                continue
            delta_to_m10.add(int(p))
        m_policy = str(args.m_policy)
        gates = None
        if m_policy == "events":
            events = _parse_m_events(str(args.m_events))
            m_by_k = _m_by_k_from_events(events)
        else:
            m_by_k, gates = _centerwired_m_by_k_from_gates(seq_dna=normalize_dna(raw), start_base=start, mu=mu_star, delta_to_m10=delta_to_m10)
        seq_dna = normalize_dna(raw)
        # For centerwired, interpret --scale as coarse cell pixel size (bigger gives more readable microcells).
        cell_px = max(40, int(scale) * 10)
        for fi in range(n_frames):
            st = start + fi * stride  # bases
            title = f"{label}  (frame {fi}/{n_frames-1})"
            rgba = _render_frame_centerwired(
                seq_dna=seq_dna,
                start_base=st,
                cell_px=cell_px,
                m_by_k=m_by_k,
                title=title,
                show_labels=not bool(args.no_labels),
                show_wiring=not bool(args.no_wiring),
                mu=mu_star,
                gates=gates,
            )
            frames_rgba.append(rgba)
            out_png = out_frames_dir / f"{out_prefix.name}_frame_{fi:04d}.png"
            plt.imsave(out_png, rgba)
            print(f"[write] {out_png}", flush=True)
    else:
        if mode == "base":
            seq_dna = normalize_dna(raw)
            for fi in range(n_frames):
                st = start + fi * stride
                title = f"{label}  (frame {fi}/{n_frames-1})"
                rgba = _render_frame_base(
                    seq_dna=seq_dna,
                    start=st,
                    n_side=n_side,
                    scale=scale,
                    draw_path=draw_path,
                    title=title,
                )
                frames_rgba.append(rgba)
                out_png = out_frames_dir / f"{out_prefix.name}_frame_{fi:04d}.png"
                plt.imsave(out_png, rgba)
                print(f"[write] {out_png}", flush=True)
        else:
            seq_rna = normalize_rna(raw)
            frame = int(args.frame) % 3
            for fi in range(n_frames):
                st = start + fi * stride
                title = f"{label}  (frame {fi}/{n_frames-1})"
                rgba = _render_frame_codon(
                    seq_rna=seq_rna,
                    frame=frame,
                    start_codon=st,
                    n_side=n_side,
                    scale=scale,
                    draw_path=draw_path,
                    title=title,
                )
                frames_rgba.append(rgba)
                out_png = out_frames_dir / f"{out_prefix.name}_frame_{fi:04d}.png"
                plt.imsave(out_png, rgba)
                print(f"[write] {out_png}", flush=True)

    # GIF export (optional).
    if _HAS_PIL and frames_rgba:
        assert Image is not None
        frames = [_rgba_to_pil(rgba) for rgba in frames_rgba]
        out_gif = out_prefix.parent / (out_prefix.name + ".gif")
        fps = 4
        frames[0].save(
            out_gif,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000 / fps),
            loop=0,
            optimize=False,
            disposal=2,
        )
        print(f"[write] {out_gif}", flush=True)
        out_cs = out_prefix.parent / (out_prefix.name + "_contact_sheet.png")
        _render_contact_sheet(out_gif, out_cs, rows=3, cols=4)
        print(f"[write] {out_cs}", flush=True)
    else:
        print("[info] Pillow not available; skipping GIF export (PNG frames are written).", flush=True)

    print(f"[write] {out_legend}", flush=True)
    print("[done]", flush=True)


if __name__ == "__main__":
    main()

