# -*- coding: utf-8 -*-
"""
CAP selection audit for visualization addressing (boundary-face focus).

We treat a visualization "scheme" as:
  - a face dimension D_face and resolution n (dyadic side 2^n),
  - a deterministic injection k ∈ {0..2^m-1} -> coord_face(k) ∈ {0..2^n-1}^{D_face},
  - (optional) a bulk embedding via x0=0, which does not change locality stats.

We then score schemes by a CAP-style lexicographic key that is explicit and auditable.

Candidate family (finite, explicit):
  1) hilbert-face: coord_face(k) = Hilbert_{D_face,n}(k)  (prefix of length 2^m)
  2) vfs-face:     coord_face(k) = VFS_{m,n}(k)           (variable-fanout dyadic refinement)
  3) lex-face:     coord_face(k) = base-(2^n) digits of k (row-major in D_face dims)

Key metrics:
  - slack := D_face*n - m (capacity overhead on the face, in bits)
  - locality: max L1 jump and q99 L1 jump along k->k+1 on the face
  - projection overlap (readability): unique count in the x1-x2 projection (when defined)

Selection key (CAP-style, deterministic):
  minimize (slack, max_jump, q99_jump, avg_proj_multiplicity, name)

Output (LaTeX fragment):
  - sections/generated/cap_visualization_selection_rows.tex
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Sequence, Tuple

from common_tex import write_lines
from hilbert_nd import hilbert_index_to_coords
from screen_universal_vfs import bits_per_level, embedding_dimension, vfs_coord_from_k


Coord = Tuple[int, ...]


def quantile(sorted_x: Sequence[float], q: float) -> float:
    """
    Linear interpolation quantile; assumes sorted_x is non-empty.
    """
    if not sorted_x:
        raise ValueError("quantile on empty sequence")
    if q <= 0.0:
        return float(sorted_x[0])
    if q >= 1.0:
        return float(sorted_x[-1])
    n = len(sorted_x)
    pos = q * float(n - 1)
    i = int(pos)
    frac = pos - float(i)
    if i >= n - 1:
        return float(sorted_x[-1])
    return float(sorted_x[i]) * (1.0 - frac) + float(sorted_x[i + 1]) * frac


def l1_jumps(path: Sequence[Coord]) -> List[int]:
    out: List[int] = []
    for a, b in zip(path[:-1], path[1:]):
        out.append(sum(abs(int(ai) - int(bi)) for ai, bi in zip(a, b)))
    return out


def unique_proj_count(path: Sequence[Coord], a: int, b: int) -> int:
    seen = set()
    for c in path:
        seen.add((int(c[a]), int(c[b])))
    return len(seen)


def lex_face_coord(k: int, n: int, D_face: int) -> Coord:
    """
    Row-major digits of k in base 2^n across D_face axes (LSB-first).
    This is an injection for k < 2^{D_face*n}.
    """
    Lmask = (1 << n) - 1
    coords = []
    kk = int(k)
    for i in range(D_face):
        coords.append(kk & Lmask)
        kk >>= n
    return tuple(int(x) for x in coords)


@dataclass(frozen=True)
class Scheme:
    name: str
    coord_fn: Callable[[int, int, int, int], Coord]  # (k,m,n,D_face)->Coord


def make_schemes() -> List[Scheme]:
    def _hilbert(k: int, m: int, n: int, D_face: int) -> Coord:
        # Prefix of a full Hilbert scan on the D_face-dim face (order n).
        return tuple(int(x) for x in hilbert_index_to_coords(int(k), p=int(n), n=int(D_face)))

    def _vfs(k: int, m: int, n: int, D_face: int) -> Coord:
        g = bits_per_level(int(m), int(n), D=int(D_face))
        return tuple(int(x) for x in vfs_coord_from_k(int(k), int(m), int(n), D=int(D_face), g=g))

    def _lex(k: int, m: int, n: int, D_face: int) -> Coord:
        return lex_face_coord(int(k), int(n), int(D_face))

    return [
        Scheme("hilbert-face", _hilbert),
        Scheme("vfs-face", _vfs),
        Scheme("lex-face", _lex),
    ]


def score_scheme(m: int, n: int, scheme: Scheme) -> Tuple[int, int, float, float, int, float]:
    """
    Return:
      slack_bits, max_jump, q99_jump, avg_proj_mult, proj_unique, N
    """
    D_face = embedding_dimension(m, n)
    N = 1 << m
    # Build the face path in scan order k=0..N-1.
    path = [scheme.coord_fn(k, m, n, D_face) for k in range(N)]
    jumps = l1_jumps(path)
    s = sorted(float(x) for x in jumps) if jumps else [0.0]
    q99 = quantile(s, 0.99)
    mx = int(max(jumps)) if jumps else 0

    slack = int(D_face * n - m)
    # Projection readability: use axes 0 and 1 when available.
    if D_face >= 2:
        uniq = unique_proj_count(path, 0, 1)
    else:
        uniq = int(N)
    avg_mult = float(N) / float(uniq) if uniq > 0 else float("inf")
    return slack, mx, q99, avg_mult, int(uniq), float(N)


def main() -> None:
    # Representative (m,n) set; extend as needed.
    pairs: List[Tuple[int, int]] = [
        (6, 3),
        (7, 3),
        (10, 3),
        (11, 3),
    ]
    schemes = make_schemes()

    out_lines: List[str] = []
    for (m, n) in pairs:
        D_face = embedding_dimension(m, n)
        best_slack = None  # (key, scheme_name)
        best_local = None  # (key, scheme_name)
        scored = []
        for sch in schemes:
            slack, mx, q99, avg_mult, uniq, N = score_scheme(m, n, sch)
            key_slack = (slack, mx, q99, avg_mult, sch.name)
            key_local = (mx, q99, slack, avg_mult, sch.name)
            scored.append((sch.name, slack, mx, q99, avg_mult, uniq, int(N), key_slack, key_local))
            if best_slack is None or key_slack < best_slack[0]:
                best_slack = (key_slack, sch.name)
            if best_local is None or key_local < best_local[0]:
                best_local = (key_local, sch.name)
        if best_slack is None or best_local is None:
            raise AssertionError("No schemes scored.")

        best_slack_name = best_slack[1]
        best_local_name = best_local[1]
        for name, slack, mx, q99, avg_mult, uniq, N, _key_slack, _key_local in scored:
            sel_slack = "\\textbf{selected}" if name == best_slack_name else ""
            sel_local = "\\textbf{selected}" if name == best_local_name else ""
            out_lines.append(
                f"{m} & {n} & {D_face} & \\texttt{{{name}}} & {slack} & {mx} & {q99:.2f} & {uniq}/{N} & {avg_mult:.2f} & {sel_slack} & {sel_local} \\\\"
            )
    out_lines.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "cap_visualization_selection_rows.tex", out_lines)
    print("Wrote sections/generated/cap_visualization_selection_rows.tex")


if __name__ == "__main__":
    main()

