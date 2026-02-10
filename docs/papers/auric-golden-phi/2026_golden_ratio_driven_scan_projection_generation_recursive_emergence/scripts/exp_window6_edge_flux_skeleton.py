#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit certificate: window-6 edge–flux skeleton on the 6-cube under Fold^{bin}_6.

All output is English-only by repository convention.

We use the dyadic (binary-interval) fold at m=6:
  Fold^{bin}_6 : {0,...,63} -> X_6,
and the 6-cube graph Q_6 on vertices {0,1}^6 (encoded as integers 0..63),
with edges given by single-bit flips.

We consider the rigid 9+6+3+3 partition of X_6 (Table tab_window6_patisalam_9633_partition):
  X_6 = X_6^{(2)} ⊔ X_6^{(1)} ⊔ X_6^{(L)} ⊔ X_6^{(R)}.

Aggregating Q_6 edges by the induced micro-vertex unions U_alpha, we compute:
  - micro-volumes |U_alpha|,
  - the undirected edge-count matrix E_{alpha,beta},
  - the coarse 4-state Markov kernel T induced by one cube step,
  - the exact characteristic polynomial of T,
  - boundary-sector cut constants and flux.

Outputs:
  - artifacts/export/window6_edge_flux_skeleton.json
  - sections/generated/eq_window6_edge_flux_skeleton.tex
"""

from __future__ import annotations

import argparse
import json
from fractions import Fraction
from math import gcd
from pathlib import Path
from typing import Dict, List, Tuple

from common_paths import export_dir, generated_dir
from common_phi_fold import word_to_str, zeckendorf_digits


BLOCKS = ["2", "1", "L", "R"]  # output order: (9,6,3,3)


def _golden_words(m: int) -> List[str]:
    """All length-m binary words with no adjacent ones, lexicographic order."""
    out: List[str] = []

    def rec(pos: int, prev1: int, acc: List[int]) -> None:
        if pos == m:
            out.append(word_to_str(acc))
            return
        acc.append(0)
        rec(pos + 1, 0, acc)
        acc.pop()
        if prev1 == 0:
            acc.append(1)
            rec(pos + 1, 1, acc)
            acc.pop()

    rec(0, 0, [])
    return sorted(out)


def _is_boundary_word(w: str) -> bool:
    return len(w) == 6 and w[0] == "1" and w[-1] == "1"


def _hamming_weight(w: str) -> int:
    return w.count("1")


def _K_of_limit(limit: int) -> int:
    """Unique K with F_{K+1} <= limit < F_{K+2} (F_1=F_2=1)."""
    if limit < 0:
        raise ValueError("limit must be non-negative")
    fib = [1, 1]
    while fib[-1] <= limit:
        fib.append(fib[-1] + fib[-2])
    return len(fib) - 2


def _fold_bin_prefix_word(N: int, m: int) -> str:
    """Compute Fold^{bin}_m(N) = prefix_m(Zeckendorf(N)) as an m-bit string."""
    limit = (1 << m) - 1
    if not (0 <= N <= limit):
        raise ValueError(f"N must be in [0,{limit}] for m={m}")
    K = _K_of_limit(limit)
    digits = zeckendorf_digits(N, K)  # c_1..c_K
    return word_to_str(digits[:m])


def _partition_X6() -> Dict[str, List[str]]:
    """Rigid four-block partition of X_6 (9+6+3+3), as word lists."""
    X6 = _golden_words(6)
    bdry = sorted([w for w in X6 if _is_boundary_word(w)])
    cyc = sorted([w for w in X6 if w not in set(bdry)])
    if (len(X6), len(cyc), len(bdry)) != (21, 18, 3):
        raise RuntimeError("Unexpected X6 cyclic/boundary split sizes.")
    if bdry != ["100001", "100101", "101001"]:
        raise RuntimeError(f"Unexpected boundary words: {bdry}")

    X2 = sorted([w for w in cyc if _hamming_weight(w) == 2])
    X1 = sorted([w for w in cyc if _hamming_weight(w) == 1])
    XL = sorted([w for w in cyc if _hamming_weight(w) in (0, 3)])
    XR = bdry
    if (len(X2), len(X1), len(XL), len(XR)) != (9, 6, 3, 3):
        raise RuntimeError("Unexpected 9+6+3+3 partition sizes.")
    return {"2": X2, "1": X1, "L": XL, "R": XR}


def _matmul(A: List[List[Fraction]], B: List[List[Fraction]]) -> List[List[Fraction]]:
    n = len(A)
    m = len(B[0])
    p = len(B)
    out = [[Fraction(0) for _ in range(m)] for _ in range(n)]
    for i in range(n):
        for k in range(p):
            if A[i][k] == 0:
                continue
            for j in range(m):
                out[i][j] += A[i][k] * B[k][j]
    return out


def _trace(A: List[List[Fraction]]) -> Fraction:
    return sum(A[i][i] for i in range(len(A)))


def _eye(n: int) -> List[List[Fraction]]:
    return [[Fraction(1 if i == j else 0) for j in range(n)] for i in range(n)]


def _charpoly_faddeev_leverrier(M: List[List[Fraction]]) -> List[Fraction]:
    """Coefficients [1,c1,...,cn] for chi(t)=t^n + c1 t^{n-1}+...+cn."""
    n = len(M)
    B = _eye(n)
    coeff: List[Fraction] = [Fraction(1)]
    for k in range(1, n + 1):
        TB = _matmul(M, B)
        ck = -_trace(TB) / Fraction(k, 1)
        coeff.append(ck)
        B = [[TB[i][j] + (ck if i == j else 0) for j in range(n)] for i in range(n)]
    return coeff


def _synthetic_div(poly: List[Fraction], root: Fraction) -> Tuple[List[Fraction], Fraction]:
    """Divide poly by (t-root). poly is [a0..an] for degrees n..0."""
    q = [poly[0]]
    for a in poly[1:]:
        q.append(a + q[-1] * root)
    rem = q.pop()
    return q, rem


def _lcm(a: int, b: int) -> int:
    return abs(a // gcd(a, b) * b) if a and b else abs(a or b)


def _fmt_frac(fr: Fraction) -> str:
    if fr.denominator == 1:
        return str(fr.numerator)
    return f"\\frac{{{fr.numerator}}}{{{fr.denominator}}}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit the window-6 edge–flux skeleton under Fold^{bin}_6.")
    ap.add_argument("--m", type=int, default=6)
    ap.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "window6_edge_flux_skeleton.json"),
    )
    ap.add_argument(
        "--tex-out",
        type=str,
        default=str(generated_dir() / "eq_window6_edge_flux_skeleton.tex"),
    )
    args = ap.parse_args()

    m = int(args.m)
    if m != 6:
        raise ValueError("This audit is anchored at m=6 (use --m 6).")

    part = _partition_X6()
    block_of_word: Dict[str, str] = {}
    for b, ws in part.items():
        for w in ws:
            block_of_word[w] = b

    # Map each microstate n to its block via its stable type.
    block_of_n: Dict[int, str] = {}
    for n in range(0, 1 << m):
        w = _fold_bin_prefix_word(n, m)
        block_of_n[n] = block_of_word[w]

    # Micro volumes by block.
    U_size = {b: 0 for b in BLOCKS}
    for n in range(0, 1 << m):
        U_size[block_of_n[n]] += 1
    if [U_size[b] for b in BLOCKS] != [27, 22, 9, 6]:
        raise RuntimeError(f"Unexpected micro-volumes by block: {U_size}")

    # Undirected edge counts between blocks.
    idx = {b: i for i, b in enumerate(BLOCKS)}
    E = [[0 for _ in BLOCKS] for _ in BLOCKS]
    edges_total = 0
    for n in range(0, 1 << m):
        for j in range(m):
            nn = n ^ (1 << j)
            if n < nn:  # count each undirected edge once
                a = block_of_n[n]
                b = block_of_n[nn]
                ia, ib = idx[a], idx[b]
                E[ia][ib] += 1
                if ia != ib:
                    E[ib][ia] += 1
                edges_total += 1
    if edges_total != (1 << m) * m // 2:
        raise RuntimeError("Edge enumeration mismatch for Q_6.")
    E_expected = [
        [28, 63, 23, 20],
        [63, 21, 21, 6],
        [23, 21, 2, 6],
        [20, 6, 6, 2],
    ]
    if E != E_expected:
        raise RuntimeError(f"Unexpected block edge-count matrix E: got={E}")

    # Coarse 4-state Markov kernel T: uniform within U_alpha.
    T: List[List[Fraction]] = [[Fraction(0) for _ in BLOCKS] for _ in BLOCKS]
    for a in BLOCKS:
        ia = idx[a]
        denom = Fraction(m * U_size[a], 1)
        for b in BLOCKS:
            ib = idx[b]
            if ia == ib:
                T[ia][ib] = Fraction(2 * E[ia][ib], 1) / denom
            else:
                T[ia][ib] = Fraction(E[ia][ib], 1) / denom

    # Characteristic polynomial and (t-1) factorization.
    poly = _charpoly_faddeev_leverrier(T)  # degrees 4..0
    q, rem = _synthetic_div(poly, Fraction(1, 1))
    if rem != 0:
        raise RuntimeError("Expected (t-1) factor (row-stochastic), but remainder != 0.")
    # q is degree-3 quotient: [1, a2, a1, a0] for t^3 + a2 t^2 + a1 t + a0.
    den = 1
    for c in q:
        den = _lcm(den, c.denominator)
    ints = [int(c * den) for c in q]
    if (den, ints) != (48114, [48114, 7263, -506, -55]):
        raise RuntimeError(f"Unexpected characteristic polynomial factorization: den={den}, ints={ints}")

    # Boundary cut constants for block R.
    iR = idx["R"]
    E_RR = int(E[iR][iR])
    boundary_edges_R = sum(int(E[iR][idx[b]]) for b in BLOCKS if b != "R")
    flux_R = Fraction(boundary_edges_R, (1 << m) * m)
    leave_prob_R = Fraction(boundary_edges_R, m * U_size["R"])
    if (E_RR, boundary_edges_R, flux_R, leave_prob_R) != (2, 32, Fraction(1, 12), Fraction(8, 9)):
        raise RuntimeError(
            "Unexpected boundary cut constants: "
            f"E_RR={E_RR}, boundary={boundary_edges_R}, flux={flux_R}, leave={leave_prob_R}"
        )

    payload = {
        "m": m,
        "blocks": BLOCKS,
        "partition": part,
        "U_size": U_size,
        "E_edge_counts": E,
        "T_kernel": [[str(x) for x in row] for row in T],
        "charpoly": {
            "coeff_t4_to_t0": [str(x) for x in poly],
            "factorization": {
                "root": "1",
                "cubic_coeff_t3_to_t0": [str(x) for x in q],
                "cubic_scaled_den": den,
                "cubic_scaled_ints_t3_to_t0": ints,
            },
        },
        "boundary_block": {
            "block": "R",
            "U_size": U_size["R"],
            "E_internal": E_RR,
            "boundary_edges": boundary_edges_R,
            "flux_per_step_unif_micro": str(flux_R),
            "leave_prob_given_R": str(leave_prob_R),
        },
    }

    json_out = Path(str(args.json_out))
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # TeX snippet.
    tex_out = Path(str(args.tex_out))
    tex_out.parent.mkdir(parents=True, exist_ok=True)

    def _mat_tex_int(M: List[List[int]]) -> str:
        rows = [" & ".join(str(x) for x in r) for r in M]
        return "\\begin{pmatrix}" + "\\\\".join(rows) + "\\end{pmatrix}"

    def _mat_tex_frac(M: List[List[Fraction]]) -> str:
        rows = [" & ".join(_fmt_frac(x) for x in r) for r in M]
        return "\\begin{pmatrix}" + "\\\\".join(rows) + "\\end{pmatrix}"

    u_tuple = ",".join(str(U_size[b]) for b in BLOCKS)
    a3, a2, a1, a0 = ints
    chi_tex = f"(t-1)\\cdot\\frac{{{a3}t^3+{a2}t^2{a1:+d}t{a0:+d}}}{{{den}}}"

    lines: List[str] = []
    lines.append("% AUTO-GENERATED by scripts/exp_window6_edge_flux_skeleton.py")
    lines.append("\\begin{equation}\\label{eq:window6_edge_flux_skeleton}")
    lines.append("\\begin{aligned}")
    lines.append(f"(|U_2|,|U_1|,|U_L|,|U_R|)&=({u_tuple}),\\\\")
    lines.append(f"E&={_mat_tex_int(E)},\\\\")
    lines.append(f"T&={_mat_tex_frac(T)},\\\\")
    lines.append(f"\\chi_T(t)&={chi_tex},\\\\")
    lines.append(
        f"|E(U_R)|&={E_RR},\\qquad |\\partial U_R|={boundary_edges_R},\\qquad "
        f"\\Phi_R=\\frac{{|\\partial U_R|}}{{64\\cdot 6}}={_fmt_frac(flux_R)},\\\\"
    )
    lines.append(
        f"\\mathbb{{P}}(\\text{{leave }}U_R\\mid U_R)"
        f"&=\\frac{{|\\partial U_R|}}{{6|U_R|}}={_fmt_frac(leave_prob_R)}."
    )
    lines.append("\\end{aligned}")
    lines.append("\\end{equation}")
    lines.append("")
    tex_out.write_text("\n".join(lines), encoding="utf-8")

    print(f"File: {json_out.relative_to(export_dir().parent.parent)}")
    print(f"File: {tex_out.relative_to(generated_dir().parent.parent)}")


if __name__ == "__main__":
    main()

