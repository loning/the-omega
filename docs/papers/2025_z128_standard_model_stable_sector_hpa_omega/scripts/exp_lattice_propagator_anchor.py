# -*- coding: utf-8 -*-
"""
Minimal lattice-QFT bridge artifact at the RG-operator anchor.

We build a symmetric positive kernel K from the audited 16x16 protocol RG operator F_n
and report simple Gaussian-anchor observables:
  - Tr(K^{-1}) (a basic propagator trace),
  - log det K  (a basic spectral/normalization summary).

Design constraints:
  - Deterministic output (no timestamps).
  - Only Python standard library + existing paper-local helpers.

Outputs (LaTeX fragments):
  - sections/generated/lattice_propagator_anchor_rows.tex
  - sections/generated/lattice_propagator_anchor_summary.tex
"""

from __future__ import annotations

import math
from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import Mat, build_F_matrix, det, mat_mul, mat_transpose, solve_linear


def _eye(n: int) -> Mat:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _add_scaled_I(A: Mat, alpha: float) -> Mat:
    n = len(A)
    out: Mat = []
    for i in range(n):
        row = [float(A[i][j]) for j in range(n)]
        row[i] += float(alpha)
        out.append(row)
    return out


def _trace_inv(K: Mat) -> float:
    """
    Compute Tr(K^{-1}) by solving K x = e_i for i=1..n and summing x_i.
    """
    n = len(K)
    tr = 0.0
    for i in range(n):
        e = [0.0] * n
        e[i] = 1.0
        x = solve_linear(K, e)
        tr += float(x[i])
    return tr


def _build_kernel_from_F(F: Mat, *, z: float, eps: float) -> Mat:
    """
    Build an SPD kernel:
      A = I - z F
      K = A^T A + eps I
    """
    n = len(F)
    I = _eye(n)
    A = [[float(I[i][j]) - float(z) * float(F[i][j]) for j in range(n)] for i in range(n)]
    AtA = mat_mul(mat_transpose(A), A)
    return _add_scaled_I(AtA, eps)


def _fmt_sci(x: float) -> str:
    if x == 0.0:
        return "0"
    ax = abs(float(x))
    if ax < 1e-3 or ax >= 1e3:
        return f"{x:.3e}"
    return f"{x:.6f}"


def _compute_row(n_bits: int, *, z: float, eps: float) -> Tuple[str, str]:
    F = build_F_matrix(n_bits)
    K = _build_kernel_from_F(F, z=z, eps=eps)
    detK = float(det(K))
    if detK <= 0.0:
        # For an SPD target, negative/zero det indicates numerical instability.
        # Keep the artifact deterministic by reporting log|det| and a flag.
        logdet = math.log(abs(detK)) if detK != 0.0 else float("inf")
        det_note = "nonpos"
    else:
        logdet = math.log(detK)
        det_note = "ok"

    trG = _trace_inv(K)

    row = (
        f"{n_bits} & {z:.3f} & {_fmt_sci(eps)} & {_fmt_sci(trG)} & {_fmt_sci(logdet)} & {det_note} \\\\"
    )

    summary = (
        "\\noindent Lattice-QFT Gaussian anchor on the Hilbert-screen RG quotient (audit-facing): "
        f"for $n={n_bits}$, we build $K=(I-zF_n)^\\top(I-zF_n)+\\epsilon I$ with "
        f"$z={z:.3f}$ and $\\epsilon={_fmt_sci(eps)}$, and report "
        f"$\\Tr(K^{{-1}})={_fmt_sci(trG)}$ and $\\log\\det K={_fmt_sci(logdet)}$ "
        f"(det status: {det_note})."
    )
    return row, summary


def main() -> None:
    # Anchor choice: the smallest audited RG operator instance (n=3) on the 16-block quotient.
    n_bits = 3
    z = 0.25
    eps = 1e-8

    row, summary = _compute_row(n_bits, z=z, eps=eps)

    out_rows = generated_dir() / "lattice_propagator_anchor_rows.tex"
    write_lines(out_rows, [row, "\\bottomrule"])
    print("Wrote sections/generated/lattice_propagator_anchor_rows.tex")

    out_summary = generated_dir() / "lattice_propagator_anchor_summary.tex"
    write_lines(out_summary, [summary])
    print("Wrote sections/generated/lattice_propagator_anchor_summary.tex")


if __name__ == "__main__":
    main()

