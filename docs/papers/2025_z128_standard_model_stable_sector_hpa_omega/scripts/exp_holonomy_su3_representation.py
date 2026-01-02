# -*- coding: utf-8 -*-
"""
SO(3) ⊂ SU(3) representation summary for finite S4 plaquette holonomy.

The finite connection in this paper assigns an S4-valued transport to each grid edge.
For each unit-square plaquette on the n=3 Hilbert grid, exp_holonomy_loops.py
computes the loop holonomy as a permutation in S4.

This script provides a minimal "representation bridge" from S4 holonomy to a
continuous group action, suitable as a skeleton for later mixing-matrix work:

  - Start from the 4D permutation representation of S4 on R^4.
  - Restrict to the 3D sum-zero subspace {x : x_1+...+x_4 = 0}, yielding a
    3×3 real orthogonal representation.
  - Apply a sign twist by the parity homomorphism so that the image lies in
    SO(3), hence also in SU(3) when viewed as real unitary matrices.

We then summarize the induced rotation angle distribution by S4 cycle type.

Outputs (LaTeX fragment):
  - sections/generated/holonomy_su3_rotation_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import exp_holonomy_loops as holo
from common_tex import write_lines


Perm = Tuple[int, int, int, int]


def parity(p: Perm) -> int:
    # +1 for even permutations, -1 for odd permutations.
    inv = 0
    for i in range(4):
        for j in range(i + 1, 4):
            if p[i] > p[j]:
                inv += 1
    return -1 if (inv % 2) else 1


def perm_matrix(p: Perm) -> List[List[float]]:
    # Matrix M such that M e_i = e_{p[i]}.
    M = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        M[p[i]][i] = 1.0
    return M


def transpose(A: List[List[float]]) -> List[List[float]]:
    return [list(row) for row in zip(*A)]


def matmul(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    ra = len(A)
    ca = len(A[0]) if A else 0
    rb = len(B)
    cb = len(B[0]) if B else 0
    if ca != rb:
        raise ValueError("Incompatible matrix shapes.")
    out = [[0.0] * cb for _ in range(ra)]
    for i in range(ra):
        for k in range(ca):
            aik = A[i][k]
            if aik == 0.0:
                continue
            for j in range(cb):
                out[i][j] += aik * B[k][j]
    return out


def basis_B() -> List[List[float]]:
    """
    Orthonormal basis for the sum-zero subspace of R^4.

    Columns are:
      v1 = (1,-1,0,0)/sqrt(2)
      v2 = (1,1,-2,0)/sqrt(6)
      v3 = (1,1,1,-3)/sqrt(12)

    Return as a 4x3 matrix B with these basis vectors as columns.
    """
    s2 = math.sqrt(2.0)
    s6 = math.sqrt(6.0)
    s12 = math.sqrt(12.0)
    v1 = [1.0 / s2, -1.0 / s2, 0.0, 0.0]
    v2 = [1.0 / s6, 1.0 / s6, -2.0 / s6, 0.0]
    v3 = [1.0 / s12, 1.0 / s12, 1.0 / s12, -3.0 / s12]
    # Convert column vectors to row-major 4x3.
    B = [[v1[i], v2[i], v3[i]] for i in range(4)]
    return B


def su3_rep(p: Perm, B: List[List[float]]) -> List[List[float]]:
    """
    Return the 3x3 SO(3) matrix representing p under the sign-twisted
    standard representation.
    """
    P = perm_matrix(p)
    Bt = transpose(B)
    PB = matmul(P, B)  # 4x3
    O = matmul(Bt, PB)  # 3x3 (orthogonal, det = parity(p))
    s = float(parity(p))
    # Sign twist makes det always +1.
    U = [[s * O[i][j] for j in range(3)] for i in range(3)]
    return U


def rotation_angle_deg(R: List[List[float]]) -> float:
    tr = R[0][0] + R[1][1] + R[2][2]
    x = 0.5 * (tr - 1.0)
    # Clamp for numerical safety.
    x = max(-1.0, min(1.0, x))
    return math.degrees(math.acos(x))


def plaquette_holonomies() -> List[Perm]:
    labels = holo.grid_labels(n_bits=3)
    pre = holo.preimages()
    edge_p = holo.edge_perm_cache(labels, pre)
    hols: List[Perm] = []
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
            hol = holo.compose(p_da, holo.compose(p_cd, holo.compose(p_bc, p_ab)))
            hols.append(hol)
    if len(hols) != 49:
        raise AssertionError(f"Expected 49 plaquettes at 8x8, got {len(hols)}.")
    return hols


def main() -> None:
    B = basis_B()
    hols = plaquette_holonomies()

    # Aggregate angles by cycle type.
    angles: Dict[str, List[float]] = defaultdict(list)
    for p in hols:
        ct = holo.cycle_type(p)
        R = su3_rep(p, B=B)
        angles[ct].append(rotation_angle_deg(R))

    rows: List[str] = []
    for ct in ["1", "2", "2x2", "3", "4", "other"]:
        xs = angles.get(ct, [])
        if not xs:
            rows.append(f"\\texttt{{{ct}}} & 0 & $-$ & $-$ & $-$ \\\\")
            continue
        cnt = len(xs)
        mean = sum(xs) / float(cnt)
        mn = min(xs)
        mx = max(xs)
        rows.append(f"\\texttt{{{ct}}} & {cnt} & {mean:.3f} & {mn:.3f} & {mx:.3f} \\\\")
    rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "holonomy_su3_rotation_rows.tex", rows)
    print("Wrote sections/generated/holonomy_su3_rotation_rows.tex")


if __name__ == "__main__":
    main()


