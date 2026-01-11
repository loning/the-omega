# -*- coding: utf-8 -*-
"""
Padé / pole-barrier audit for the confinement-proxy Wilson-loop series (audit-only).

HPA/Abel-first viewpoint:
  - treat a finite set of Wilson-loop magnitudes as coefficients of a power series,
  - approximate its analytic continuation by small Padé approximants,
  - audit whether the approximant introduces poles inside the unit disk (|z|<1),
    which would violate the "pole barrier" discipline used elsewhere in the paper.

This is heuristic and audit-only: Padé approximants can introduce spurious poles.
We therefore report a small bounded family sweep over (L,M) orders.

Inputs:
  - sections/generated/holonomy_wilson_loop_rows.tex

Outputs (LaTeX fragments):
  - sections/generated/qcd_confinement_pade_pole_rows.tex
  - sections/generated/qcd_confinement_pade_pole_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from common_tex import write_lines


@dataclass(frozen=True)
class ObsRow:
    k: int
    count: int
    mean_w: float


def _parse_float(s: str) -> float:
    s = s.strip().strip("$")
    if s in {"-", "$-$"}:
        return float("nan")
    return float(s)


def _read_wilson_rows(path: Path) -> List[ObsRow]:
    rows: List[ObsRow] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("\\") or "bottomrule" in line:
            continue
        if "&" not in line:
            continue
        parts = [p.strip() for p in line.split("&")]
        if len(parts) < 3:
            continue
        try:
            k = int(parts[0])
            cnt = int(parts[1])
            mean_w = _parse_float(parts[2])
        except Exception:
            continue
        rows.append(ObsRow(k=k, count=cnt, mean_w=float(mean_w)))
    return rows


def _gauss_solve(A: List[List[float]], b: List[float]) -> List[float]:
    """
    Solve A x = b by naive Gaussian elimination with partial pivoting.
    A is modified in-place.
    """
    n = len(A)
    if n == 0:
        return []
    m = len(A[0])
    if m != n:
        raise ValueError("A must be square.")
    if len(b) != n:
        raise ValueError("b length mismatch.")

    # Augment
    M = [row[:] + [b_i] for row, b_i in zip(A, b)]

    for col in range(n):
        # pivot
        piv = col
        piv_val = abs(M[col][col])
        for r in range(col + 1, n):
            v = abs(M[r][col])
            if v > piv_val:
                piv = r
                piv_val = v
        if piv_val == 0.0:
            raise ValueError("Singular system.")
        if piv != col:
            M[col], M[piv] = M[piv], M[col]

        # normalize row
        denom = M[col][col]
        for j in range(col, n + 1):
            M[col][j] /= denom

        # eliminate
        for r in range(n):
            if r == col:
                continue
            factor = M[r][col]
            if factor == 0.0:
                continue
            for j in range(col, n + 1):
                M[r][j] -= factor * M[col][j]

    return [M[i][n] for i in range(n)]


def _pade_denominator_q(c: List[float], L: int, M: int) -> List[float]:
    """
    Compute Padé denominator coefficients q0..qM with q0=1 for [L/M] Padé approximant.
    We solve:
      sum_{j=1..M} q_j * c[n-j] = -c[n]   for n=L+1..L+M
    """
    if L < 0 or M <= 0:
        raise ValueError("Invalid L/M.")
    if L + M >= len(c):
        raise ValueError("Need coefficients up to L+M.")

    A: List[List[float]] = []
    b: List[float] = []
    for i in range(1, M + 1):
        n = L + i
        row = []
        for j in range(1, M + 1):
            row.append(c[n - j])
        A.append(row)
        b.append(-c[n])
    qs = _gauss_solve(A, b)
    return [1.0] + qs


def _poly_eval(coeffs: List[complex], z: complex) -> complex:
    out = 0j
    # Horner
    for a in reversed(coeffs):
        out = out * z + a
    return out


def _durand_kerner_roots(coeffs: List[complex], iters: int = 80) -> List[complex]:
    """
    Durand–Kerner for monic or non-monic polynomial.
    coeffs: [a0,a1,...,ad] with ad != 0.
    """
    d = len(coeffs) - 1
    if d <= 0:
        return []
    ad = coeffs[-1]
    if ad == 0:
        raise ValueError("Leading coefficient is zero.")

    # normalize to monic
    c = [a / ad for a in coeffs]

    # initial seeds on circle
    R = 1.1
    roots = [R * cmath.exp(2j * math.pi * k / d) for k in range(d)]

    for _ in range(iters):
        new_roots = []
        for i in range(d):
            zi = roots[i]
            fzi = _poly_eval(c, zi)
            denom = 1.0 + 0j
            for j in range(d):
                if j == i:
                    continue
                denom *= (zi - roots[j])
            if denom == 0j:
                denom = 1e-12 + 0j
            new_roots.append(zi - fzi / denom)
        roots = new_roots
    return roots


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    gen = root / "sections" / "generated"
    src = gen / "holonomy_wilson_loop_rows.tex"
    if not src.is_file():
        raise FileNotFoundError("Missing sections/generated/holonomy_wilson_loop_rows.tex; run exp_holonomy_wilson_loop_sweep.py first.")

    data = _read_wilson_rows(src)
    w_abs_by_k = {}
    for r in data:
        if r.count <= 0:
            continue
        if 1 <= r.k <= 6:
            w = abs(float(r.mean_w))
            if w > 0 and math.isfinite(w):
                w_abs_by_k[r.k] = w

    # Build a sparse power series c_n up to N=36, with c_0=1, c_{k^2}=|W_k|.
    N = 36
    c = [0.0 for _ in range(N + 1)]
    c[0] = 1.0
    for k, w in w_abs_by_k.items():
        n = k * k
        if 0 <= n <= N:
            c[n] = float(w)

    # Bounded family of Padé orders.
    # Keep small M to make root finding stable and to keep audit finite.
    pairs: List[Tuple[int, int]] = []
    for M in (3, 4, 5, 6):
        for L in (12, 16, 20, 24, 28):
            if L + M <= N and L >= 1:
                pairs.append((L, M))

    out_rows: List[str] = []
    for L, M in pairs:
        try:
            q = _pade_denominator_q(c, L=L, M=M)  # real coefficients, ascending degree
            # Q(z) = 1 + q1 z + ... + qM z^M
            Q_coeffs = [complex(a) for a in q]  # ascending
            # roots need coeffs in ascending; our root routine expects ascending too.
            roots = _durand_kerner_roots(Q_coeffs, iters=80)
            abs_roots = [abs(z) for z in roots]
            min_abs = min(abs_roots) if abs_roots else float("nan")
            count_inside = sum(1 for a in abs_roots if a < 1.0 - 1e-8)
            out_rows.append(f"{L} & {M} & {min_abs:.6g} & {count_inside} \\\\")
        except Exception:
            out_rows.append(f"{L} & {M} & $-$ & $-$ \\\\")

    out_rows.append("\\bottomrule")

    summary = [
        r"\paragraph{Audit summary (Padé pole barrier).} \AuditTag "
        r"We treat the finite Wilson-loop magnitude sequence as coefficients of a sparse power series "
        r"$F(z)=\sum_{n=0}^{36} c_n z^n$ with $c_0=1$ and $c_{k^2}=|W_k|$ for $k\in\{1,\dots,6\}$. "
        r"For a bounded family of Padé orders $[L/M]$, we compute the denominator polynomial $Q_{L,M}(z)$ and "
        r"a numerical root set, then report whether any root lies inside the unit disk (interpreted as a heuristic interior pole). "
        r"This check is audit-only: Padé can introduce spurious poles and zeros for short/sparse series."
    ]

    write_lines(gen / "qcd_confinement_pade_pole_rows.tex", out_rows)
    write_lines(gen / "qcd_confinement_pade_pole_summary.tex", summary)
    print("Wrote sections/generated/qcd_confinement_pade_pole_rows.tex")
    print("Wrote sections/generated/qcd_confinement_pade_pole_summary.tex")


if __name__ == "__main__":
    main()

