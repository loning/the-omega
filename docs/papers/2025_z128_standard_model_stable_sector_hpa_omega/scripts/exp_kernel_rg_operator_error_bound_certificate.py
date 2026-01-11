# -*- coding: utf-8 -*-
"""
Protocol RG operator: error-budget / decomposition certificate (balanced chain).

For each n=3..7 (m=2n), for each micro-field q in {weight,value,dpi,logg},
we decompose the predict-vs-recompute gap on the 16-vector block quotient:

  v_true - v_pred = (v_true - v_uplift) + (v_uplift - v_pred)

where:
  - v_true   := P_{n+1} q_{n+1}    (recompute at new resolution)
  - v_pred   := F_n (P_n q_n)      (coarse operator prediction)
  - v_uplift := P_{n+1} (U_n q_n)  (micro-uplifted field, then coarse-grain)

The first term is a recompute/refinement term, the second is a coarse-graining
loss term (within-block fluctuation not captured by P_n^* P_n).

Output (LaTeX fragment):
  - sections/generated/kernel_rg_operator_error_budget_rows.tex

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
    parent_index_map,
)


def _fmt(x: float) -> str:
    return f"{x:.6f}"


def _errs(a: List[float], b: List[float]) -> Tuple[float, float]:
    if len(a) != len(b):
        raise ValueError("Dimension mismatch.")
    diffs = [float(x) - float(y) for x, y in zip(a, b, strict=True)]
    max_abs = max(abs(d) for d in diffs)
    rmse = math.sqrt(sum(d * d for d in diffs) / float(len(diffs)))
    return max_abs, rmse


def _uplift_micro_field(n_bits: int, qn: List[float]) -> List[float]:
    parents = parent_index_map(n_bits)
    out = [0.0] * len(parents)
    for kp1, p in enumerate(parents):
        out[kp1] = float(qn[p])
    return out


def main() -> None:
    rows: List[str] = []

    # Columns:
    # n, q, max_abs_total, rmse_total, max_abs_recompute, rmse_recompute, max_abs_coarse, rmse_coarse.
    q_order = ["weight", "value", "dpi", "logg"]
    for n in range(3, 8):
        F = build_F_matrix(n)
        qn = micro_q_fields_for_balanced_chain(n)
        qnp1 = micro_q_fields_for_balanced_chain(n + 1)

        for qname in q_order:
            v_true = block_average_vector(n + 1, qnp1[qname])
            v_n = block_average_vector(n, qn[qname])
            v_pred = mat_vec(F, v_n)

            q_u = _uplift_micro_field(n, qn[qname])
            v_u = block_average_vector(n + 1, q_u)

            max_abs_total, rmse_total = _errs(v_true, v_pred)
            max_abs_rec, rmse_rec = _errs(v_true, v_u)
            max_abs_coarse, rmse_coarse = _errs(v_u, v_pred)

            rows.append(
                f"{n} & {qname} & {_fmt(max_abs_total)} & {_fmt(rmse_total)}"
                f" & {_fmt(max_abs_rec)} & {_fmt(rmse_rec)}"
                f" & {_fmt(max_abs_coarse)} & {_fmt(rmse_coarse)} \\\\"
            )

    rows.append("\\bottomrule")

    out = generated_dir() / "kernel_rg_operator_error_budget_rows.tex"
    write_lines(out, rows)
    print("Wrote sections/generated/kernel_rg_operator_error_budget_rows.tex")


if __name__ == "__main__":
    main()

