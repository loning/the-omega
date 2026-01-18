# -*- coding: utf-8 -*-
"""
Protocol RG operator: predict vs recompute audit (balanced chain).

For each n=3..7 (so m=2n and m'=2(n+1)), we compare:
  - predicted next block-averaged vector:   v_pred = F_n v_n
  - recomputed next block-averaged vector: v_true = P_{n+1} \tilde{q}_{n+1}

This is an audit-oriented diagnostic of the "recompute at new resolution" step
in the protocol flow definition: the gap quantifies backreaction/refinement
effects not captured by the coarse 16x16 operator alone.

Output (LaTeX fragment):
  - sections/generated/kernel_rg_operator_backreaction_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines
from rg_operator import (
    block_average_vector,
    build_F_matrix,
    mat_vec,
    micro_q_fields_for_balanced_chain,
)


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def _errs(pred: List[float], true: List[float]) -> Tuple[float, float]:
    if len(pred) != len(true):
        raise ValueError("Dimension mismatch.")
    diffs = [float(p) - float(t) for p, t in zip(pred, true, strict=True)]
    max_abs = max(abs(d) for d in diffs)
    rmse = math.sqrt(sum(d * d for d in diffs) / float(len(diffs)))
    return max_abs, rmse


def main() -> None:
    rows: List[str] = []

    # Columns:
    # n, q, max_abs_err, rmse.
    q_order = ["weight", "value", "dpi", "logg"]
    for n in range(3, 8):
        F = build_F_matrix(n)

        qn = micro_q_fields_for_balanced_chain(n)
        qnp1 = micro_q_fields_for_balanced_chain(n + 1)

        for qname in q_order:
            v_n = block_average_vector(n, qn[qname])
            v_pred = mat_vec(F, v_n)
            v_true = block_average_vector(n + 1, qnp1[qname])
            max_abs, rmse = _errs(v_pred, v_true)

            rows.append(f"{n} & {qname} & {_fmt(max_abs)} & {_fmt(rmse)} \\\\")

    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_operator_backreaction_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_operator_backreaction_rows.tex")


if __name__ == "__main__":
    main()

