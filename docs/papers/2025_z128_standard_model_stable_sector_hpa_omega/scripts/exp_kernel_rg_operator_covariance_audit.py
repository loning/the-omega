# -*- coding: utf-8 -*-
"""
Protocol RG operator: 2-point library (cross-observable covariance) audit.

For each n=3..8 (balanced chain m=2n), we build the 16-vector block averages
v_q = P_n \tilde q_n for the intrinsic scalars q in {weight,value,dpi,logg},
and compute the cross-observable covariance and correlation over the uniform
block index b∈{1..16}:

  Cov(q_i,q_j) = (1/16) Σ_b (v_i[b]-μ_i)(v_j[b]-μ_j),
  Corr(q_i,q_j) = Cov(q_i,q_j)/sqrt(Var(q_i)Var(q_j)).

This is a finite-dimensional proxy for a 2-point readout library on the
block quotient (and can be packaged by 2-point kernels on tensor lifts).

Output (LaTeX fragment):
  - sections/generated/kernel_rg_operator_covariance_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import block_average_vector, micro_q_fields_for_balanced_chain


def _mean(x: List[float]) -> float:
    return sum(float(v) for v in x) / float(len(x))


def _cov(x: List[float], y: List[float]) -> float:
    if len(x) != len(y):
        raise ValueError("Dimension mismatch.")
    mx = _mean(x)
    my = _mean(y)
    return sum((float(a) - mx) * (float(b) - my) for a, b in zip(x, y, strict=True)) / float(len(x))


def _corr(x: List[float], y: List[float]) -> float:
    vx = _cov(x, x)
    vy = _cov(y, y)
    if vx <= 0.0 or vy <= 0.0:
        return 0.0
    return _cov(x, y) / math.sqrt(vx * vy)


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def main() -> None:
    rows: List[str] = []

    q_order = ["weight", "value", "dpi", "logg"]
    pairs: List[Tuple[str, str]] = [
        ("weight", "value"),
        ("weight", "dpi"),
        ("weight", "logg"),
        ("value", "dpi"),
        ("value", "logg"),
        ("dpi", "logg"),
    ]

    for n in range(3, 9):
        qn = micro_q_fields_for_balanced_chain(n)
        v: Dict[str, List[float]] = {q: block_average_vector(n, qn[q]) for q in q_order}

        corrs = [_corr(v[a], v[b]) for (a, b) in pairs]
        rows.append(
            f"{n} & " + " & ".join(_fmt(c) for c in corrs) + r" \\"
        )

    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_operator_covariance_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_operator_covariance_rows.tex")


if __name__ == "__main__":
    main()

