# -*- coding: utf-8 -*-
"""
Two-loop chain best-fit scan for holonomy→mixing diagnostics (finite diagnostic).

We restrict to the small, auditable set of square k×k loops (k<=7) whose underlying
S4 holonomy permutation is a 3- or 4-cycle. For each such loop we compute an
effective 3×3 unitary Q via phase lift (map family + denom=2^p), projection to the
sum-zero subspace, and Gram-Schmidt renormalization.

We then form a *two-loop chain* by multiplying two loop unitaries:
  Q_chain := Q2 · Q1,
where each Qi may be replaced by its adjoint (inverse loop). This yields a bounded
finite search family of effective U(3) holonomies.

For each chain, we allow a global S3×S3 relabeling (row/col permutation) and score
the resulting PDG-style sines (s12,s23,s13) against PMNS and CKM targets by the
minimax log-mismatch:
  E_inf := max_i |log(s_i / s_i^ref)|.

Outputs (LaTeX fragment):
  - sections/generated/holonomy_two_loop_chain_bestfit_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
import math
import time
from pathlib import Path
from typing import List, Optional, Tuple

import exp_holonomy_loops as holo
import exp_holonomy_loop_scale_sweep as ls
import exp_holonomy_phase_lift_angles as ang
import exp_holonomy_phase_lift_cp_invariant as ph
from common_tex import write_lines


Coord = Tuple[int, int]
Perm3 = Tuple[int, int, int]


def eye4() -> List[List[complex]]:
    return [[1.0 + 0j if i == j else 0j for j in range(4)] for i in range(4)]


def matmul3(A: List[List[complex]], B: List[List[complex]]) -> List[List[complex]]:
    out = [[0j] * 3 for _ in range(3)]
    for i in range(3):
        for k in range(3):
            aik = A[i][k]
            if aik == 0j:
                continue
            for j in range(3):
                out[i][j] += aik * B[k][j]
    return out


def adj3(U: List[List[complex]]) -> List[List[complex]]:
    return [[U[j][i].conjugate() for j in range(3)] for i in range(3)]


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0 or math.isnan(pred) or (not math.isfinite(pred)):
        return float("inf")
    return abs(math.log(pred / ref))


def two_best_candidates(
    ref: Tuple[float, float, float],
    loops: List[Tuple[int, int, int, str, List[Tuple[Coord, Coord]]]],
    map_names: List[str],
    denoms: List[int],
    progress_every_s: float = 60.0,
) -> Tuple[
    Tuple[float, float, str, int, int, bool, int, bool, Perm3, Perm3, float, float, float, float],
    Tuple[float, float, str, int, int, bool, int, bool, Perm3, Perm3, float, float, float, float],
    int,
]:
    """
    Return (best, second, domain_eval_count).

    Candidate tuple:
      (Einf, E1, map_name, denom, i, inv_i, j, inv_j, rperm, cperm, s12, s23, s13, |J|)
    """
    labels = holo.grid_labels(n_bits=3)
    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)
    B = ph.basis_B()

    perms = list(itertools.permutations((0, 1, 2), 3))
    best = None
    second = None
    domain = 0

    t0 = time.time()
    last = t0

    for map_name in map_names:
        for denom in denoms:
            # Compute per-loop effective Q matrices for this (map,denom).
            Qs: List[Optional[List[List[complex]]]] = []
            for (_k, _x, _y, _ct, edges) in loops:
                H = eye4()
                for a, b in edges:
                    U_ab = ph.edge_unitary_with_denom(
                        a, b, labels, pre, edge_p, denom=denom, map_name=map_name, bits=6
                    )
                    H = ph.matmul(U_ab, H)
                M3 = ph.project_3x3(H, B=B)
                Q = ph.gram_schmidt_unitary(M3)
                Qs.append(Q)

            # Build option list including adjoints (inverse loops).
            opts: List[Tuple[int, bool, List[List[complex]]]] = []
            for idx, Q in enumerate(Qs):
                if Q is None:
                    continue
                opts.append((idx, False, Q))
                opts.append((idx, True, adj3(Q)))

            for i, inv_i, Qi in opts:
                for j, inv_j, Qj in opts:
                    Q = matmul3(Qj, Qi)
                    for r in perms:
                        for c in perms:
                            domain += 1
                            Qp = [[Q[r[ii]][c[jj]] for jj in range(3)] for ii in range(3)]
                            s12, s23, s13, _delta_deg, J = ang.extract_angles(Qp)
                            e12 = abs_log_ratio(s12, ref[0])
                            e23 = abs_log_ratio(s23, ref[1])
                            e13 = abs_log_ratio(s13, ref[2])
                            Einf = max(e12, e23, e13)
                            E1 = e12 + e23 + e13
                            cand = (Einf, E1, map_name, denom, i, inv_i, j, inv_j, r, c, s12, s23, s13, abs(J))
                            if best is None or cand < best:
                                if best is not None:
                                    second = best
                                best = cand
                                continue
                            if best is not None and cand == best:
                                continue
                            if second is None or cand < second:
                                second = cand

            now = time.time()
            if now - last >= progress_every_s:
                dt = now - t0
                print(f"[two-loop] elapsed={dt:.0f}s map={map_name} denom={denom} domain={domain}")
                last = now

    if best is None:
        raise AssertionError("No candidates enumerated.")
    if second is None:
        second = best
    return best, second, domain


def main() -> None:
    # Targets (physical layer references).
    pmns_ref = (math.sqrt(0.307), math.sqrt(0.545), math.sqrt(0.0218))
    ckm_ref = (0.2243, 0.0422, 0.00394)

    map_names = ["id", "gray", "bitrev", "not"]
    denoms = [1 << p for p in range(6, 19)]  # 64..262144

    # Precompute the small loop set (3/4-cycle S4 holonomies) on the n=3 grid.
    labels = holo.grid_labels(n_bits=3)
    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)
    loops: List[Tuple[int, int, int, str, List[Tuple[Coord, Coord]]]] = []
    for k in range(1, 8):
        max_xy = 8 - k - 1
        for x in range(max_xy + 1):
            for y in range(max_xy + 1):
                hol_p = (0, 1, 2, 3)
                edges = list(ls.loop_edges_square(x, y, k=k))
                for a, b in edges:
                    hol_p = holo.compose(edge_p[(a, b)], hol_p)
                ct = holo.cycle_type(hol_p)
                if ct in ("3", "4"):
                    loops.append((k, x, y, ct, edges))

    if not loops:
        raise AssertionError("No 3/4-cycle loops found.")

    # Run bounded scans.
    # Progress: print once per minute for long-running scans.
    best_p, second_p, domain_p = two_best_candidates(pmns_ref, loops, map_names, denoms, progress_every_s=60.0)
    best_c, second_c, domain_c = two_best_candidates(ckm_ref, loops, map_names, denoms, progress_every_s=60.0)

    rows: List[str] = []

    def fmt_loop(idx: int, inv: bool) -> str:
        k, x, y, ct, _edges = loops[idx]
        sgn = "-" if inv else "+"
        return f"{k},{x},{y},\\texttt{{{ct}}},{sgn}"

    def fmt_perm(p: Perm3) -> str:
        return f"({p[0]},{p[1]},{p[2]})"

    def add_row(name: str, best, second, domain: int) -> None:
        Einf, E1, map_name, denom, i, inv_i, j, inv_j, r, c, s12, s23, s13, Jabs = best
        Einf2 = second[0]
        gap = Einf2 - Einf
        rows.append(
            f"\\texttt{{{name}}} & {domain} & \\texttt{{{map_name}}} & {denom} & \\texttt{{({fmt_loop(i,inv_i)})}} & \\texttt{{({fmt_loop(j,inv_j)})}} & \\texttt{{{fmt_perm(r)}}}/\\texttt{{{fmt_perm(c)}}} & {s12:.4f} & {s23:.4f} & {s13:.6g} & {Jabs:.6g} & {Einf:.3f} & {E1:.3f} & {Einf2:.3f} & {gap:.3f} \\\\"
        )

    add_row("PMNS", best_p, second_p, domain_p)
    add_row("CKM", best_c, second_c, domain_c)
    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_two_loop_chain_bestfit_rows.tex", rows)
    print("Wrote sections/generated/holonomy_two_loop_chain_bestfit_rows.tex")


if __name__ == "__main__":
    main()


