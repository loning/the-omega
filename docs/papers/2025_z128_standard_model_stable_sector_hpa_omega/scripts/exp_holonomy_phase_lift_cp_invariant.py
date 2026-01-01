# -*- coding: utf-8 -*-
"""
Phase-lifted holonomy and a CP-odd invariant (toy, protocol-level).

This script extends the toy S4-valued edge connection on the n=3 Hilbert grid by
attaching a deterministic Z_128-like phase register to microstates k in {0..63}.

For each oriented edge a->b with padded fibers (size 4):
  fa = fiber4(pre, w_a), fb = fiber4(pre, w_b),
and transport permutation p (size-4) mapping indices i -> p[i],
we define a 4x4 unitary "phase-lifted transport" U_edge by:
  (U_edge)_{p[i], i} = exp(i * (phi(fb[p[i]]) - phi(fa[i]))),
where phi(k) := 2*pi * k / 64.

For each plaquette, we multiply the four oriented edge transports to obtain a 4x4
unitary holonomy H.

To obtain an effective 3x3 unitary matrix from H, we:
  - project to the 3D sum-zero subspace using a fixed orthonormal basis B (4x3),
    M := B^T H B  (3x3, generally not unitary),
  - renormalize by complex Gram-Schmidt on the columns of M to get Q (3x3 unitary).

We then compute a CP-odd invariant J(Q) := Im(Q_00 Q_11 Q_01^* Q_10^*), which is
rephasing-invariant for 3x3 unitary matrices.

This is an exploratory bridge script: it does not claim that this particular
phase lift is physically unique; it makes the phase choice explicit, auditable,
and computable.

Outputs (LaTeX fragment):
  - sections/generated/holonomy_phase_lift_j_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import cmath
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import exp_holonomy_loops as holo
from common_tex import write_lines


Coord = Tuple[int, int]
Perm = Tuple[int, int, int, int]


def phase(k: int) -> float:
    # Z_128-like phase register embedding for k in {0..63}.
    # Use a full 64-step circle: 2*pi*k/64 = 2*pi*(2k)/128.
    return 2.0 * math.pi * (float(k) / 64.0)


def fiber4(pre: Dict[str, List[int]], w: str) -> List[int]:
    return holo.fiber4(pre, w)


def edge_unitary(a: Coord, b: Coord, labels: Dict[Coord, str], pre: Dict[str, List[int]], edge_p: Dict[Tuple[Coord, Coord], Perm]) -> List[List[complex]]:
    """
    Return the 4x4 unitary transport matrix from a -> b.
    Basis at each site is the padded fiber order returned by fiber4(...).
    """
    p = edge_p[(a, b)]
    wa = labels[a]
    wb = labels[b]
    fa = fiber4(pre, wa)
    fb = fiber4(pre, wb)

    U = [[0j] * 4 for _ in range(4)]
    for i in range(4):
        j = p[i]
        theta = phase(fb[j]) - phase(fa[i])
        U[j][i] = cmath.exp(1j * theta)
    return U


def matmul(A: List[List[complex]], B: List[List[complex]]) -> List[List[complex]]:
    ra = len(A)
    ca = len(A[0]) if A else 0
    rb = len(B)
    cb = len(B[0]) if B else 0
    if ca != rb:
        raise ValueError("Incompatible matrix shapes.")
    out = [[0j] * cb for _ in range(ra)]
    for i in range(ra):
        for k in range(ca):
            aik = A[i][k]
            if aik == 0j:
                continue
            for j in range(cb):
                out[i][j] += aik * B[k][j]
    return out


def transpose_real(B: List[List[float]]) -> List[List[float]]:
    return [list(row) for row in zip(*B)]


def basis_B() -> List[List[float]]:
    """
    Orthonormal basis for the sum-zero subspace of R^4 (same as exp_holonomy_su3_representation.py).
    Columns:
      v1 = (1,-1,0,0)/sqrt(2)
      v2 = (1,1,-2,0)/sqrt(6)
      v3 = (1,1,1,-3)/sqrt(12)
    Return 4x3 matrix with these as columns.
    """
    s2 = math.sqrt(2.0)
    s6 = math.sqrt(6.0)
    s12 = math.sqrt(12.0)
    v1 = [1.0 / s2, -1.0 / s2, 0.0, 0.0]
    v2 = [1.0 / s6, 1.0 / s6, -2.0 / s6, 0.0]
    v3 = [1.0 / s12, 1.0 / s12, 1.0 / s12, -3.0 / s12]
    return [[v1[i], v2[i], v3[i]] for i in range(4)]


def project_3x3(H: List[List[complex]], B: List[List[float]]) -> List[List[complex]]:
    # M = B^T H B
    # Convert B to complex 4x3.
    Bc = [[complex(x, 0.0) for x in row] for row in B]
    Bt = transpose_real(B)  # 3x4 real
    Btc = [[complex(x, 0.0) for x in row] for row in Bt]
    HB = matmul(H, Bc)  # 4x3
    M = matmul(Btc, HB)  # 3x3
    return M


def gram_schmidt_unitary(M: List[List[complex]], eps: float = 1.0e-12) -> List[List[complex]] | None:
    """
    Orthonormalize the columns of M to obtain a 3x3 unitary Q.
    Return None if rank deficiency is detected.
    """
    # Extract columns as vectors.
    cols = [[M[i][j] for i in range(3)] for j in range(3)]
    Qcols: List[List[complex]] = []

    def inner(u: List[complex], v: List[complex]) -> complex:
        return sum(u[i].conjugate() * v[i] for i in range(3))

    def norm(v: List[complex]) -> float:
        return math.sqrt(float(inner(v, v).real))

    for v in cols:
        w = list(v)
        for q in Qcols:
            wproj = inner(q, w)
            for i in range(3):
                w[i] -= wproj * q[i]
        n = norm(w)
        if n < eps:
            return None
        for i in range(3):
            w[i] /= n
        Qcols.append(w)

    # Reassemble as row-major 3x3.
    Q = [[Qcols[j][i] for j in range(3)] for i in range(3)]
    return Q


def jarlskog_invariant(U: List[List[complex]]) -> float:
    # J = Im(U_00 U_11 U_01^* U_10^*)
    return float((U[0][0] * U[1][1] * U[0][1].conjugate() * U[1][0].conjugate()).imag)


def plaquette_unitary_holonomies() -> List[Tuple[Perm, List[List[complex]]]]:
    labels = holo.grid_labels(n_bits=3)
    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)

    out: List[Tuple[Perm, List[List[complex]]]] = []
    for x in range(7):
        for y in range(7):
            a = (x, y)
            b = (x + 1, y)
            c = (x + 1, y + 1)
            d = (x, y + 1)

            # Underlying permutation holonomy (for cycle-type grouping).
            p_ab = edge_p[(a, b)]
            p_bc = edge_p[(b, c)]
            p_cd = edge_p[(c, d)]
            p_da = edge_p[(d, a)]
            hol_p = holo.compose(p_da, holo.compose(p_cd, holo.compose(p_bc, p_ab)))

            # Phase-lifted unitary holonomy.
            U_ab = edge_unitary(a, b, labels, pre, edge_p)
            U_bc = edge_unitary(b, c, labels, pre, edge_p)
            U_cd = edge_unitary(c, d, labels, pre, edge_p)
            U_da = edge_unitary(d, a, labels, pre, edge_p)
            H = matmul(U_da, matmul(U_cd, matmul(U_bc, U_ab)))

            out.append((hol_p, H))
    if len(out) != 49:
        raise AssertionError(f"Expected 49 plaquettes, got {len(out)}.")
    return out


def main() -> None:
    B = basis_B()
    hols = plaquette_unitary_holonomies()

    by_ct: Dict[str, List[float]] = defaultdict(list)
    failures = 0

    for p, H in hols:
        ct = holo.cycle_type(p)
        M = project_3x3(H, B=B)
        Q = gram_schmidt_unitary(M)
        if Q is None:
            failures += 1
            continue
        J = jarlskog_invariant(Q)
        by_ct[ct].append(J)

    rows: List[str] = []
    for ct in ["1", "2", "2x2", "3", "4", "other"]:
        xs = by_ct.get(ct, [])
        if not xs:
            rows.append(f"\\texttt{{{ct}}} & 0 & $-$ & $-$ & $-$ \\\\")
            continue
        cnt = len(xs)
        mean_abs = sum(abs(x) for x in xs) / float(cnt)
        max_abs = max(abs(x) for x in xs)
        mean_signed = sum(xs) / float(cnt)
        rows.append(f"\\texttt{{{ct}}} & {cnt} & {mean_abs:.6g} & {max_abs:.6g} & {mean_signed:+.6g} \\\\")

    # Report failures as a separate line (if any) using a pseudo cycle-type tag.
    if failures:
        rows.append(f"\\texttt{{rank-fail}} & {failures} & $-$ & $-$ & $-$ \\\\")
    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_phase_lift_j_rows.tex", rows)
    print("Wrote sections/generated/holonomy_phase_lift_j_rows.tex")


if __name__ == "__main__":
    main()


