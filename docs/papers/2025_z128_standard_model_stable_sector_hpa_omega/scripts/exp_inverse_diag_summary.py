# -*- coding: utf-8 -*-
"""
Main-text summary: inverse interface diagnostics for the closed 21->SM labeling.

This script aggregates a compact summary table (baseline vs best accuracy) from the
inverse-diagnostic fragments generated in Appendix~app:inverse_quantum_numbers.

Design:
  - Deterministic.
  - Standard library only.
  - Regenerates the dependent inverse-diagnostic fragments before summarizing.

Output (LaTeX fragment):
  - sections/generated/inverse_diag_summary_rows.tex
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from common_tex import read_lines, write_lines

import exp_inverse_generation_fit as gen_fit
import exp_inverse_hypercharge_fit as y2_fit
import exp_inverse_hypercharge_full_fit as yfull_fit
import exp_inverse_hypercharge_sign_fit as ysign_fit
import exp_inverse_rep_dim_fit as rep_fit


def _strip_row_end(s: str) -> str:
    s = s.strip()
    if s.endswith(r"\\"):
        s = s[: -len(r"\\")].strip()
    return s


def _cols(row: str) -> List[str]:
    return [c.strip() for c in _strip_row_end(row).split("&")]


def _parse_float(s: str) -> float:
    return float(s.strip())


def _read_first_data_row(path: Path) -> str:
    for line in read_lines(path):
        if not line.strip():
            continue
        if line.strip().startswith("\\"):
            continue
        return line
    raise FileNotFoundError(f"No data rows found in {path}")


def _read_all_data_rows(path: Path) -> List[str]:
    out: List[str] = []
    for line in read_lines(path):
        if not line.strip():
            continue
        if line.strip().startswith("\\"):
            continue
        out.append(line)
    if not out:
        raise FileNotFoundError(f"No data rows found in {path}")
    return out


def _best_acc_from_rows_last_col(rows: List[str]) -> float:
    best = 0.0
    for r in rows:
        cs = _cols(r)
        acc = _parse_float(cs[-1])
        best = max(best, acc)
    return best


def main() -> None:
    # Ensure dependent fragments exist and are up to date (deterministic regeneration).
    y2_fit.main()
    ysign_fit.main()
    yfull_fit.main()
    rep_fit.main()
    gen_fit.main()

    root = Path(__file__).resolve().parent.parent
    gen_dir = root / "sections" / "generated"

    # (6Y)^2 summary: accuracy is the 3rd column in the single-row fragment.
    y2_row = _read_first_data_row(gen_dir / "inverse_hypercharge_fit_rows.tex")
    y2_cols = _cols(y2_row)
    acc_y2 = _parse_float(y2_cols[2])

    # sign(Y) summary: last column in the single-row fragment.
    ysign_row = _read_first_data_row(gen_dir / "inverse_hypercharge_sign_fit_rows.tex")
    acc_ysign = _parse_float(_cols(ysign_row)[-1])

    # full Y_num summary: take the best accuracy across the multiple-family fragment.
    yfull_rows = _read_all_data_rows(gen_dir / "inverse_hypercharge_full_fit_rows.tex")
    acc_yfull = _best_acc_from_rows_last_col(yfull_rows)

    # rep dims: two rows, last column is accuracy; take each explicitly.
    rep_rows = _read_all_data_rows(gen_dir / "inverse_rep_dim_fit_rows.tex")
    acc_su3 = None
    acc_su2 = None
    for r in rep_rows:
        cs = _cols(r)
        tgt = cs[1]
        acc = _parse_float(cs[-1])
        if "SU(3)" in tgt:
            acc_su3 = acc
        if "SU(2)" in tgt:
            acc_su2 = acc
    if acc_su3 is None or acc_su2 is None:
        raise AssertionError("Failed to parse inverse_rep_dim_fit_rows.tex.")

    # generation: take the best accuracy across the score variants (last column).
    gen_rows = _read_all_data_rows(gen_dir / "inverse_generation_fit_rows.tex")
    acc_gen = _best_acc_from_rows_last_col(gen_rows)

    # Build summary rows for main text.
    rows: List[str] = []
    rows.append(
        r"$(6Y)^2$ class & $1/6$ & " f"{acc_y2:.3f}" r" & Table~\ref{tab:inverse_hypercharge_fit} \\"
    )
    rows.append(
        r"$\mathrm{sign}(Y)$ & $1/2$ & " f"{acc_ysign:.3f}" r" & Table~\ref{tab:inverse_hypercharge_sign_fit} \\"
    )
    rows.append(
        r"$Y_{\mathrm{num}}=6Y$ & $1/6$ & " f"{acc_yfull:.3f}" r" & Table~\ref{tab:inverse_hypercharge_full_fit} \\"
    )
    rows.append(
        r"$\dim(SU(3))$ & $1/2$ & " f"{acc_su3:.3f}" r" & Table~\ref{tab:inverse_rep_dim_fit} \\"
    )
    rows.append(
        r"$\dim(SU(2))$ & $2/3$ & " f"{acc_su2:.3f}" r" & Table~\ref{tab:inverse_rep_dim_fit} \\"
    )
    rows.append(
        r"generation $g$ & $1/3$ & " f"{acc_gen:.3f}" r" & Table~\ref{tab:inverse_generation_fit} \\"
    )
    rows.append(r"\bottomrule")

    write_lines(gen_dir / "inverse_diag_summary_rows.tex", rows)
    print("Wrote sections/generated/inverse_diag_summary_rows.tex")


if __name__ == "__main__":
    main()


