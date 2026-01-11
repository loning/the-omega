#!/usr/bin/env python3
"""
Coupling unification audit in the r coordinate (bounded family, deterministic).

Writes:
  - sections/generated/coupling_unification_audit_rows.tex
  - sections/generated/coupling_unification_audit_summary.tex

English only (repo rule).
"""

from __future__ import annotations

import math
from pathlib import Path


def fmt(x: float, nd: int = 3) -> str:
    return f"{x:.{nd}f}"


def main() -> None:
    root = Path(__file__).resolve().parents[1]  # .../docs/papers/.../ (paper root)
    gen = root / "sections" / "generated"
    gen.mkdir(parents=True, exist_ok=True)

    phi = (1.0 + math.sqrt(5.0)) / 2.0
    logphi = math.log(phi)
    pi = math.pi
    pi2 = pi * pi

    # One-loop SM beta coefficients (as used in appendix 31).
    b1 = 41.0 / 6.0
    b2 = -19.0 / 6.0
    b3 = -7.0

    # Anchor at mu_Z, with r=0 at mu_Z.
    alpha2_inv_0 = 3.0 * pi2  # alpha_w^{-1}
    alpha1_inv_0 = 10.0 * pi2  # alpha_Y^{-1} with Q = T3 + Y convention used in the paper

    def r_ij(alpha_i_inv: float, alpha_j_inv: float, bi: float, bj: float) -> float:
        return (2.0 * pi * (alpha_i_inv - alpha_j_inv)) / ((bi - bj) * logphi)

    r12 = r_ij(alpha1_inv_0, alpha2_inv_0, b1, b2)

    rows = []
    best = None  # (Einf, n, r13, r23)

    for n in range(1, 51):
        alpha3_inv_0 = n * pi2
        r13 = r_ij(alpha1_inv_0, alpha3_inv_0, b1, b3)
        r23 = r_ij(alpha2_inv_0, alpha3_inv_0, b2, b3)
        einf = max(abs(r12 - r13), abs(r12 - r23), abs(r13 - r23))

        if best is None or (einf, n) < (best[0], best[1]):
            best = (einf, n, r13, r23)

        rows.append((n, float(n), r12, r13, r23, einf))

    assert best is not None
    best_einf, best_n, best_r13, best_r23 = best

    # Deterministic compact table: show all n but keep numeric width small.
    # If you want a shorter table later, restrict to a window around the winner.
    row_lines = []
    for n, n_pi2, r12_v, r13_v, r23_v, _einf in rows:
        row_lines.append(
            f"{n} & {fmt(n_pi2, 0)} & {fmt(r12_v)} & {fmt(r13_v)} & {fmt(r23_v)} \\\\"
        )

    (gen / "coupling_unification_audit_rows.tex").write_text(
        "\n".join(row_lines) + "\n",
        encoding="utf-8",
    )

    summary = (
        "\\paragraph{Audit winner (within the declared family).}\n"
        "\\AuditTag "
        f"Within the discrete family $\\alpha_3^{{-1}}(\\mu_Z)=n\\pi^2$ for $1\\le n\\le 50$, "
        f"the lexicographic minimizer of $(E_\\infty,n)$ is $n={best_n}$, "
        f"with $E_\\infty\\approx {fmt(best_einf)}$ and "
        f"intersection points $r_{{12}}\\approx {fmt(r12)}$, "
        f"$r_{{13}}\\approx {fmt(best_r13)}$, $r_{{23}}\\approx {fmt(best_r23)}$.\n"
    )
    (gen / "coupling_unification_audit_summary.tex").write_text(summary, encoding="utf-8")

    print("Wrote sections/generated/coupling_unification_audit_rows.tex")
    print("Wrote sections/generated/coupling_unification_audit_summary.tex")


if __name__ == "__main__":
    main()

