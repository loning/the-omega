# -*- coding: utf-8 -*-
"""
Two-loop chain best-fit scan (mixed cycle types) for holonomy→mixing diagnostics (toy).

This is a bounded-complexity variant of exp_holonomy_two_loop_chain_bestfit.py that:
  - expands the admissible loop pool to include 2-, 2x2-, 3-, and 4-cycle S4 holonomies
    (excluding the identity class), and
  - restricts the phase-map/denominator families to keep the search domain small:
      map ∈ {id, gray}, denom ∈ {2^8,2^9,2^10} = {256,512,1024}.

We scan:
  - two selected square loops (k<=7) from this loop pool, allowing inverses (adjoints),
  - a global S3×S3 relabeling,
and evaluate both PMNS and CKM target sines using the minimax log-mismatch E_inf.

Outputs (LaTeX fragment):
  - sections/generated/holonomy_two_loop_chain_mixed_cycles_bestfit_rows.tex

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


def update_best_two(best, second, cand):
    if best is None or cand < best:
        return cand, best
    if cand == best:
        return best, second
    if second is None or cand < second:
        return best, cand
    return best, second


def main() -> None:
    # Targets (physical layer references).
    pmns_ref = (math.sqrt(0.307), math.sqrt(0.545), math.sqrt(0.0218))
    ckm_ref = (0.2243, 0.0422, 0.00394)

    # Restricted candidate families.
    map_names = ["id", "gray"]
    denoms = [256, 512, 1024]
    perms = list(itertools.permutations((0, 1, 2), 3))

    # Build loop pool on the n=3 grid (8x8): keep only nontrivial cycle types.
    labels = holo.grid_labels(n_bits=3)
    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)

    keep_ct = {"2", "2x2", "3", "4"}
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
                if ct in keep_ct:
                    loops.append((k, x, y, ct, edges))

    if not loops:
        raise AssertionError("No nontrivial loops found.")

    B = ph.basis_B()

    best_pmns = None
    second_pmns = None
    best_ckm = None
    second_ckm = None
    domain = 0  # evaluated (s12,s23,s13) candidates across the full scan

    t0 = time.time()
    last = t0

    for map_name in map_names:
        for denom in denoms:
            # Compute effective Q matrices for each loop at this (map,denom).
            Qs: List[Optional[List[List[complex]]]] = []
            for (_k, _x, _y, _ct, edges) in loops:
                H = eye4()
                for a, b in edges:
                    U_ab = ph.edge_unitary_with_denom(
                        a, b, labels, pre, edge_p, denom=denom, map_name=map_name, bits=6
                    )
                    H = ph.matmul(U_ab, H)
                M3 = ph.project_3x3(H, B=B)
                Qs.append(ph.gram_schmidt_unitary(M3))

            opts: List[Tuple[int, bool, List[List[complex]]]] = []
            for idx, Q in enumerate(Qs):
                if Q is None:
                    continue
                opts.append((idx, False, Q))
                opts.append((idx, True, adj3(Q)))

            # Domain contribution for this (map,denom) block.
            # Each (i,j) pair evaluates all (r,c) in S3×S3 (36 cases).
            block_pairs = len(opts) * len(opts)
            block_domain = block_pairs * len(perms) * len(perms)

            # Enumerate two-loop chains and global relabelings.
            pairs_done = 0
            for i, inv_i, Qi in opts:
                for j, inv_j, Qj in opts:
                    Q = matmul3(Qj, Qi)
                    for r in perms:
                        for c in perms:
                            Qp = [[Q[r[ii]][c[jj]] for jj in range(3)] for ii in range(3)]
                            s12, s23, s13, _delta_deg, J = ang.extract_angles(Qp)
                            Jabs = abs(J)

                            # PMNS objective.
                            e12 = abs_log_ratio(s12, pmns_ref[0])
                            e23 = abs_log_ratio(s23, pmns_ref[1])
                            e13 = abs_log_ratio(s13, pmns_ref[2])
                            Einf = max(e12, e23, e13)
                            E1 = e12 + e23 + e13
                            key_pmns = (Einf, E1, map_name, denom, i, inv_i, j, inv_j, r, c)
                            cand_pmns = key_pmns + (s12, s23, s13, Jabs)
                            best_pmns, second_pmns = update_best_two(best_pmns, second_pmns, cand_pmns)

                            # CKM objective.
                            e12 = abs_log_ratio(s12, ckm_ref[0])
                            e23 = abs_log_ratio(s23, ckm_ref[1])
                            e13 = abs_log_ratio(s13, ckm_ref[2])
                            Einf = max(e12, e23, e13)
                            E1 = e12 + e23 + e13
                            key_ckm = (Einf, E1, map_name, denom, i, inv_i, j, inv_j, r, c)
                            cand_ckm = key_ckm + (s12, s23, s13, Jabs)
                            best_ckm, second_ckm = update_best_two(best_ckm, second_ckm, cand_ckm)

                    pairs_done += 1
                    domain += len(perms) * len(perms)
                    if (pairs_done % 1024) == 0:
                        now = time.time()
                        if now - last >= 60.0:
                            dt = now - t0
                            print(f"[two-loop-mixed] elapsed={dt:.0f}s map={map_name} denom={denom} domain={domain}")
                            last = now

            if domain < 0:
                raise AssertionError("Impossible domain counter state.")
            if pairs_done != block_pairs:
                raise AssertionError("Pair counter mismatch.")
            if block_domain != block_pairs * len(perms) * len(perms):
                raise AssertionError("Block domain mismatch.")

    if best_pmns is None or best_ckm is None:
        raise AssertionError("No candidates enumerated.")
    if second_pmns is None:
        second_pmns = best_pmns
    if second_ckm is None:
        second_ckm = best_ckm

    def fmt_loop(idx: int, inv: bool) -> str:
        k, x, y, ct, _edges = loops[idx]
        sgn = "-" if inv else "+"
        return f"{k},{x},{y},\\texttt{{{ct}}},{sgn}"

    def fmt_perm(p: Perm3) -> str:
        return f"({p[0]},{p[1]},{p[2]})"

    def emit(name: str, best, second) -> str:
        Einf, E1, map_name, denom, i, inv_i, j, inv_j, r, c, s12, s23, s13, Jabs = best
        Einf2 = second[0]
        gap = Einf2 - Einf
        return (
            f"\\texttt{{{name}}} & {domain} & \\texttt{{{map_name}}} & {denom} & "
            f"\\texttt{{({fmt_loop(i, inv_i)})}} & \\texttt{{({fmt_loop(j, inv_j)})}} & "
            f"\\texttt{{{fmt_perm(r)}}}/\\texttt{{{fmt_perm(c)}}} & "
            f"{s12:.4f} & {s23:.4f} & {s13:.6g} & {Jabs:.6g} & "
            f"{Einf:.3f} & {E1:.3f} & {Einf2:.3f} & {gap:.3f} \\\\"
        )

    rows = [
        emit("PMNS", best_pmns, second_pmns),
        emit("CKM", best_ckm, second_ckm),
        "\\bottomrule",
    ]

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_two_loop_chain_mixed_cycles_bestfit_rows.tex", rows)
    print("Wrote sections/generated/holonomy_two_loop_chain_mixed_cycles_bestfit_rows.tex")


if __name__ == "__main__":
    main()


