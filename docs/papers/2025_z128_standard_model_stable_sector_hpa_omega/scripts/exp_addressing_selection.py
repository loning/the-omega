# -*- coding: utf-8 -*-
"""
Addressing-basis selection audit (finite, tick-first).

Goal:
  Provide an explicit, auditable comparison of a small candidate family of
  addressing bases (Hilbert vs a row-major counterfactual) at the minimal
  anchor (m,n)=(6,3).

We report protocol-internal metrics that do not import external physics targets:
  (i) edge fiber-matching overhead, summarized by cost quantiles, and
  (ii) a phase-lift computability diagnostic on nontrivial plaquettes,
       summarized by a Gram--Schmidt failure rate.

Selection rule (CAP-style, deterministic):
  pick the unique minimizer of the lexicographic tuple
    (edge_q90, fail_frac, edge_q99, name)
  within the stated finite candidate family.

Output (LaTeX fragment):
  - sections/generated/addressing_selection_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import exp_edge_mismatch_decomposition as edge
import exp_fold6_stats as fold
import exp_hilbert_chirality_index as hil
import exp_holonomy_loops as holo
import exp_holonomy_phase_lift_cp_invariant as ph
from common_tex import write_lines


Coord = Tuple[int, int]


def grid_labels_hilbert(n_bits: int = 3) -> Dict[Coord, str]:
    # Same labeling as in exp_edge_mismatch_decomposition / exp_holonomy_loops.
    return edge.grid_labels(n_bits=n_bits)


def grid_labels_row_major(n_bits: int = 3) -> Dict[Coord, str]:
    L = 1 << n_bits
    out: Dict[Coord, str] = {}
    for y in range(L):
        for x in range(L):
            k = x + L * y
            out[(x, y)] = fold.fold6(k)
    return out


def path_hilbert(n_bits: int = 3) -> List[Coord]:
    # Use the canonical Hilbert curve order as the scan path.
    return [(int(x), int(y)) for (x, y) in hil.hilbert_curve(n_bits)]


def path_row_major(n_bits: int = 3) -> List[Coord]:
    # Counterfactual scan path induced by row-major indexing.
    L = 1 << n_bits
    out: List[Coord] = []
    for k in range(L * L):
        x = k % L
        y = k // L
        out.append((x, y))
    return out


def _scan_jump_quantiles(path: List[Coord]) -> Tuple[float, float, float, float]:
    """
    Return (q50,q90,q99,max) of Manhattan jump lengths |dx|+|dy| along the scan path.
    """
    if len(path) < 2:
        raise ValueError("Path must have length >= 2.")
    jumps: List[float] = []
    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        jumps.append(float(abs(x2 - x1) + abs(y2 - y1)))
    s = sorted(jumps)
    return edge.quantile(s, 0.50), edge.quantile(s, 0.90), edge.quantile(s, 0.99), float(max(s))


def _edge_cost_quantiles(labels: Dict[Coord, str]) -> Tuple[float, float, float]:
    """
    Return (q50,q90,q99) of the minimum matching cost on edges of the 8x8 grid.
    """
    pre = edge.preimages()
    costs: List[int] = []
    for a, b in edge.all_edges(L=7):
        wa = labels[a]
        wb = labels[b]
        fa = edge.fiber4(pre, wa)
        fb = edge.fiber4(pre, wb)
        _p, cost = edge.best_perm(fa, fb)
        costs.append(cost)
    s = sorted(float(c) for c in costs)
    return edge.quantile(s, 0.50), edge.quantile(s, 0.90), edge.quantile(s, 0.99)


def _phase_lift_failure(labels: Dict[Coord, str], denom: int = 64, map_name: str = "id") -> Tuple[int, int, float]:
    """
    On unit plaquettes whose underlying permutation holonomy has cycle type 3 or 4,
    compute the phase-lifted 4x4 holonomy and attempt to project+Gram--Schmidt to a 3x3 unitary.

    Return (failures, total_nontrivial, fail_frac).
    """
    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)
    B = ph.basis_B()

    total = 0
    fails = 0
    for x in range(7):
        for y in range(7):
            a = (x, y)
            b = (x + 1, y)
            c = (x + 1, y + 1)
            d = (x, y + 1)

            p_ab = edge_p[(a, b)]
            p_bc = edge_p[(b, c)]
            p_cd = edge_p[(c, d)]
            p_da = edge_p[(d, a)]
            hol_p = holo.compose(p_da, holo.compose(p_cd, holo.compose(p_bc, p_ab)))
            ct = holo.cycle_type(hol_p)
            if ct not in ("3", "4"):
                continue

            total += 1
            U_ab = ph.edge_unitary_with_denom(a, b, labels, pre, edge_p, denom=denom, map_name=map_name, bits=6)
            U_bc = ph.edge_unitary_with_denom(b, c, labels, pre, edge_p, denom=denom, map_name=map_name, bits=6)
            U_cd = ph.edge_unitary_with_denom(c, d, labels, pre, edge_p, denom=denom, map_name=map_name, bits=6)
            U_da = ph.edge_unitary_with_denom(d, a, labels, pre, edge_p, denom=denom, map_name=map_name, bits=6)
            H = ph.matmul(U_da, ph.matmul(U_cd, ph.matmul(U_bc, U_ab)))
            M3 = ph.project_3x3(H, B=B)
            Q = ph.gram_schmidt_unitary(M3)
            if Q is None:
                fails += 1

    frac = float(fails) / float(total) if total > 0 else 1.0
    return fails, total, frac


def _score_row(
    name: str,
    jump90: float,
    jump99: float,
    edge90: float,
    edge99: float,
    fails: int,
    total: int,
    frac: float,
    is_selected: bool,
) -> str:
    sel = "\\textbf{selected}" if is_selected else ""
    return (
        f"\\texttt{{{name}}} & {jump90:.3f} & {jump99:.3f} & {edge90:.3f} & {edge99:.3f} & {fails}/{total} & {frac:.3f} & {sel} \\\\"
    )


def main() -> None:
    # Candidate family (explicit, finite).
    candidates = [
        ("hilbert", grid_labels_hilbert(n_bits=3), path_hilbert(n_bits=3)),
        ("row-major", grid_labels_row_major(n_bits=3), path_row_major(n_bits=3)),
    ]

    rows: List[Tuple[str, float, float, float, float, int, int, float]] = []
    for name, labels, path in candidates:
        _jump50, jump90, jump99, _jumpmax = _scan_jump_quantiles(path)
        _e50, edge90, edge99 = _edge_cost_quantiles(labels)
        fails, total, frac = _phase_lift_failure(labels, denom=64, map_name="id")
        rows.append((name, jump90, jump99, edge90, edge99, fails, total, frac))

    # CAP-style deterministic selection.
    best = None  # (jump90, jump99, edge90, frac, edge99, name, fails, total)
    for name, jump90, jump99, edge90, edge99, fails, total, frac in rows:
        cand = (jump90, jump99, edge90, frac, edge99, name, fails, total)
        if best is None or cand < best:
            best = cand
    if best is None:
        raise AssertionError("No addressing candidates evaluated.")
    _jump90, _jump99, _edge90, _frac, _edge99, best_name, *_rest = best

    out_lines: List[str] = []
    for name, jump90, jump99, edge90, edge99, fails, total, frac in rows:
        out_lines.append(
            _score_row(name, jump90, jump99, edge90, edge99, fails, total, frac, is_selected=(name == best_name))
        )
    out_lines.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "addressing_selection_rows.tex", out_lines)
    print("Wrote sections/generated/addressing_selection_rows.tex")


if __name__ == "__main__":
    main()


