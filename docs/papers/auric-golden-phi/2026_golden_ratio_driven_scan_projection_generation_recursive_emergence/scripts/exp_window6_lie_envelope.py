#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit certificate: coordinate pushforward operators on X_6 and their Lie envelope.

All code is English-only by repository convention.

Setup:
  - Omega_6 = {0,1}^6, encoded as integers n=0..63 via int_6(omega_1..omega_6)=sum omega_k 2^{6-k}.
  - Fold^{bin}_6 : {0,...,63} -> X_6 is the dyadic (binary-interval) fold at m=6.
  - Label map on the 6-cube: F6(omega) := Fold^{bin}_6(int_6(omega)) ∈ X_6.

For each coordinate direction i=1..6 (flipping omega_i), define the directed pushforward operator
  (L_i)_{uv} := #{ omega ∈ Omega_6 : F6(omega)=u and F6(omega ⊕ e_i)=v }.
Equivalently, L_i counts the number of directed i-edges from the fiber of u to the fiber of v.

We compute:
  - the six integer matrices L_i ∈ Z^{21×21},
  - the Lie algebra g_6 := Lie⟨L_1,...,L_6⟩ ⊂ gl(21,Q) generated under commutators,
  - basic invariants: dim(g_6), dim([g_6,g_6]), dim(Z(g_6)),
  - the Killing form rank/determinant (via adjoint representation),
  - the commutant dimension of the adjoint representation (detects simple vs. direct sum).

Outputs:
  - artifacts/export/window6_lie_envelope.json
  - sections/generated/eq_window6_lie_envelope_invariants.tex
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import sympy as sp

from common_paths import export_dir, generated_dir
from common_phi_fold import word_to_str, zeckendorf_digits


def _foldbin6_label(n: int) -> str:
    # For m=6, K(6)=9 (F_{10}=55 ≤ 63 < F_{11}=89), so digits up to k=9 are exact.
    digits = zeckendorf_digits(n, 9)  # digits for weights F_{k+1}, k=1..9
    return word_to_str(digits[:6])


def _mat_to_vec(M: sp.Matrix) -> sp.Matrix:
    return sp.Matrix(M).reshape(M.rows * M.cols, 1)


def _add_to_basis(vecs: List[sp.Matrix], mats: List[sp.Matrix], M: sp.Matrix) -> bool:
    v = _mat_to_vec(M)
    if not vecs:
        vecs.append(v)
        mats.append(M)
        return True
    B = sp.Matrix.hstack(*vecs, v)
    if B.rank() > len(vecs):
        vecs.append(v)
        mats.append(M)
        return True
    return False


def _lie_closure(gens: List[sp.Matrix]) -> Tuple[List[sp.Matrix], List[sp.Matrix]]:
    """Return (basis_mats, basis_vecs) for the Lie algebra span under commutators."""
    basis_mats: List[sp.Matrix] = []
    basis_vecs: List[sp.Matrix] = []
    new_idx: List[int] = []
    for G in gens:
        if _add_to_basis(basis_vecs, basis_mats, G):
            new_idx.append(len(basis_mats) - 1)

    # Expand by commutators until stable.
    while new_idx:
        added: List[int] = []
        # Snapshot current basis length for iteration; we will still allow growth.
        for i in new_idx:
            Ei = basis_mats[i]
            for j in range(len(basis_mats)):
                if i == j:
                    continue
                Ej = basis_mats[j]
                C = Ei * Ej - Ej * Ei
                if _add_to_basis(basis_vecs, basis_mats, C):
                    added.append(len(basis_mats) - 1)
        new_idx = added
    return basis_mats, basis_vecs


def _span_dim(mats: List[sp.Matrix]) -> int:
    vecs = [_mat_to_vec(M) for M in mats]
    if not vecs:
        return 0
    return int(sp.Matrix.hstack(*vecs).rank())


def _center_dim(basis_mats: List[sp.Matrix]) -> int:
    dim = len(basis_mats)
    if dim == 0:
        return 0
    blocks: List[sp.Matrix] = []
    for j in range(dim):
        cols = []
        Ej = basis_mats[j]
        for k in range(dim):
            Ek = basis_mats[k]
            cols.append(_mat_to_vec(Ek * Ej - Ej * Ek))
        blocks.append(sp.Matrix.hstack(*cols))
    C = sp.Matrix.vstack(*blocks)  # (dim*n^2) x dim
    return int(dim - C.rank())

def _adjoint_matrices(basis_mats: List[sp.Matrix], basis_vecs: List[sp.Matrix]) -> List[sp.Matrix]:
    dim = len(basis_mats)
    if dim == 0:
        return []
    B = sp.Matrix.hstack(*basis_vecs)  # (n^2) x dim
    # Left inverse for coordinates in the column span (exact over Q):
    # if columns of B are independent, then (B^T B) is invertible and x=(B^T B)^{-1} B^T v.
    Gram = (B.T * B)
    if Gram.det() == 0:
        raise RuntimeError("Unexpected singular Gram matrix for basis vectors.")
    B_left = Gram.inv() * B.T  # dim x (n^2)
    ad: List[sp.Matrix] = []
    for i in range(dim):
        Ei = basis_mats[i]
        cols: List[sp.Matrix] = []
        for j in range(dim):
            Ej = basis_mats[j]
            v = _mat_to_vec(Ei * Ej - Ej * Ei)
            cols.append(B_left * v)
        ad_i = sp.Matrix.hstack(*cols)  # dim x dim
        ad.append(ad_i)
    return ad


def _killing_form(ad: List[sp.Matrix]) -> sp.Matrix:
    dim = len(ad)
    K = sp.zeros(dim, dim)
    for i in range(dim):
        for j in range(dim):
            K[i, j] = sp.trace(ad[i] * ad[j])
    return K


def _commutant_dim(ad: List[sp.Matrix]) -> int:
    """Dimension of {X : X A = A X for all A in ad}."""
    dim = len(ad)
    if dim == 0:
        return 0
    I = sp.eye(dim)
    blocks: List[sp.Matrix] = []
    for A in ad:
        blocks.append(sp.kronecker_product(A.T, I) - sp.kronecker_product(I, A))
    M = sp.Matrix.vstack(*blocks)  # (dim*dim*dim) x (dim*dim)
    return int(dim * dim - M.rank())


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit the window-6 coordinate pushforward operators and Lie envelope.")
    ap.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "window6_lie_envelope.json"),
        help="Path to JSON audit output.",
    )
    ap.add_argument(
        "--tex-eq-out",
        type=str,
        default=str(generated_dir() / "eq_window6_lie_envelope_invariants.tex"),
        help="Path to generated TeX equation snippet (\\input{}).",
    )
    args = ap.parse_args()

    labels = [_foldbin6_label(n) for n in range(64)]
    words = sorted(set(labels))
    if len(words) != 21:
        raise RuntimeError(f"Unexpected |X_6| from Fold^{{bin}}_6: {len(words)}")
    idx = {w: i for i, w in enumerate(words)}

    fiber_size: Dict[str, int] = {w: 0 for w in words}
    for w in labels:
        fiber_size[w] += 1

    # Coordinate directions i=1..6 correspond to flipping omega_i, i.e. XOR with 2^{6-i}.
    bits = [1 << (6 - i) for i in range(1, 7)]
    L: List[sp.Matrix] = []
    for bit in bits:
        M = [[0 for _ in range(21)] for _ in range(21)]
        for n in range(64):
            nn = n ^ bit
            a = idx[labels[n]]
            b = idx[labels[nn]]
            M[a][b] += 1
        Li = sp.Matrix(M)
        # Row sums should equal fiber sizes (one outgoing i-edge per microstate).
        for w in words:
            r = idx[w]
            if int(sum(Li[r, c] for c in range(21))) != int(fiber_size[w]):
                raise RuntimeError("Row-sum check failed for some L_i.")
        L.append(Li)

    basis_mats, basis_vecs = _lie_closure(L)
    dim_g = len(basis_mats)

    # Derived algebra dimension.
    comms: List[sp.Matrix] = []
    for i in range(dim_g):
        for j in range(i + 1, dim_g):
            comms.append(basis_mats[i] * basis_mats[j] - basis_mats[j] * basis_mats[i])
    dim_derived = _span_dim(comms)

    # Center.
    dim_center = _center_dim(basis_mats)

    # Adjoint representation, Killing form, commutant dimension.
    ad = _adjoint_matrices(basis_mats, basis_vecs)
    K = _killing_form(ad)
    killing_rank = int(K.rank())
    # Commute only against a generating subset: {ad(L_i)}.
    B = sp.Matrix.hstack(*basis_vecs)  # (n^2) x dim
    Gram = (B.T * B)
    B_left = Gram.inv() * B.T
    coeff_L = [B_left * _mat_to_vec(Li) for Li in L]  # each is dim x 1
    ad_gens: List[sp.Matrix] = []
    for c in coeff_L:
        A = sp.zeros(dim_g, dim_g)
        for k in range(dim_g):
            if c[k, 0] != 0:
                A += c[k, 0] * ad[k]
        ad_gens.append(A)
    commutant_dim = _commutant_dim(ad_gens)

    payload: Dict[str, object] = {
        "m": 6,
        "words": words,
        "fiber_size_d_bin": {w: int(fiber_size[w]) for w in words},
        "L_coord_edge_counts": [[[int(Li[r, c]) for c in range(21)] for r in range(21)] for Li in L],
        "lie_envelope": {
            "dim_g": int(dim_g),
            "dim_derived": int(dim_derived),
            "dim_center": int(dim_center),
            "killing_rank": int(killing_rank),
            "commutant_dim_ad": int(commutant_dim),
        },
    }

    json_out = Path(str(args.json_out))
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # TeX equation snippet.
    tex_out = Path(str(args.tex_eq_out))
    tex_out.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append("% AUTO-GENERATED by scripts/exp_window6_lie_envelope.py")
    lines.append("\\begin{equation}\\label{eq:window6_lie_envelope_invariants}")
    lines.append("\\begin{aligned}")
    lines.append(f"\\dim\\mathfrak{{g}}_6&={dim_g},\\\\")
    lines.append(f"\\dim[\\mathfrak{{g}}_6,\\mathfrak{{g}}_6]&={dim_derived},\\\\")
    lines.append(f"\\dim Z(\\mathfrak{{g}}_6)&={dim_center},\\\\")
    lines.append(f"\\mathrm{{rank}}\\,\\kappa_6&={killing_rank},\\\\")
    lines.append(f"\\dim\\,\\mathrm{{Comm}}(\\mathrm{{ad}}(\\mathfrak{{g}}_6))&={commutant_dim}.")
    lines.append("\\end{aligned}")
    lines.append("\\end{equation}")
    lines.append("")
    tex_out.write_text("\n".join(lines), encoding="utf-8")

    print(f"File: {json_out.relative_to(export_dir().parent.parent)}")
    print(f"File: {tex_out.relative_to(generated_dir().parent.parent)}")


if __name__ == "__main__":
    main()

