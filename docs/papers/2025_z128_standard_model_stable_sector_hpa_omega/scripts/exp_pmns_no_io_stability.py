# -*- coding: utf-8 -*-
"""
NO/IO stability diagnostic for the PMNS bounded-complexity closures.

We compare the selected minimizers under two representative reference target sets:
  - normal ordering (NO): common_constants.PMNS_SIN2_T**_REF
  - inverted ordering (IO): common_constants.PMNS_SIN2_T**_REF_IO

We report:
  - the B=20 minimizer for the PMNS mixing-sine closure,
  - the Q=12 minimizer for the discrete delta closure under the same chirality-anchored rule.

Output (LaTeX fragment):
  - sections/generated/pmns_no_io_stability_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

import exp_hilbert_chirality_index as hilb
import exp_pmns_matrix_closure as pmns_mat
import exp_pmns_mixing_depth_rigidity as pmns
from common_constants import (
    PHI,
    PMNS_DELTA_REF_DEG,
    PMNS_SIN2_T12_REF,
    PMNS_SIN2_T13_REF,
    PMNS_SIN2_T23_REF,
    PMNS_SIN2_T12_REF_IO,
    PMNS_SIN2_T13_REF_IO,
    PMNS_SIN2_T23_REF_IO,
)
from common_tex import write_lines


def _sgn_int(x: int) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def _fmt_trip(s2_12: float, s2_23: float, s2_13: float) -> str:
    return rf"$({s2_12:.3f},{s2_23:.3f},{s2_13:.4f})$"


def _delta_form(k: int, q: int) -> str:
    return rf"$\delta={k}\pi/{q}$"


def main() -> None:
    chi = hilb.chirality_index(hilb.hilbert_curve(n_bits=3))
    chi_sign = _sgn_int(chi)
    if chi_sign == 0:
        raise AssertionError("Unexpected chi==0; cannot anchor CP-odd sign.")

    delta_ref = float(PMNS_DELTA_REF_DEG) * math.pi / 180.0
    Q_MAX = 12
    cands = pmns_mat.delta_candidates_bounded_denominator(Q_MAX)

    cases: List[Tuple[str, float, float, float]] = [
        ("NO", PMNS_SIN2_T12_REF, PMNS_SIN2_T23_REF, PMNS_SIN2_T13_REF),
        ("IO", PMNS_SIN2_T12_REF_IO, PMNS_SIN2_T23_REF_IO, PMNS_SIN2_T13_REF_IO),
    ]

    rows: List[str] = []
    for tag, s2_12, s2_23, s2_13 in cases:
        s12_ref = math.sqrt(s2_12)
        s23_ref = math.sqrt(s2_23)
        s13_ref = math.sqrt(s2_13)

        best = pmns.best_triple_at_B(B=20, s12_ref=s12_ref, s23_ref=s23_ref, s13_ref=s13_ref)
        mix_form = rf"$({best.p12}/{best.q12},{best.p23}/{best.q23},{best.k13})$"

        # Predicted sines from the minimizer.
        s12_pred = math.sqrt(float(best.p12) / float(best.q12))
        s23_pred = math.sqrt(float(best.p23) / float(best.q23))
        s13_pred = PHI ** (-0.5 * float(best.k13))

        # Reference reconstruction uses the same delta_ref (representative), but ordering-specific sines.
        U_ref = pmns_mat.pmns_parameterization(s12_ref, s23_ref, s13_ref, delta_ref)
        J_ref_abs = abs(pmns_mat.J_from_angles(s12_ref, s23_ref, s13_ref, delta_ref))

        best_delta = pmns_mat.select_delta_discrete(
            s12=s12_pred,
            s23=s23_pred,
            s13=s13_pred,
            chi_sign=chi_sign,
            J_ref_abs=J_ref_abs,
            U_ref=U_ref,
            candidates=cands,
        )
        deg = best_delta.delta * 180.0 / math.pi
        delta_tex = rf"{_delta_form(best_delta.k, best_delta.q)} [$ {deg:.1f}^\circ $]"

        U_pred = pmns_mat.pmns_parameterization(s12_pred, s23_pred, s13_pred, best_delta.delta)
        EinfU, _E1U = pmns_mat._matrix_abs_log_mismatch(U_pred, U_ref)

        rows.append(
            f"{tag} & {_fmt_trip(s2_12, s2_23, s2_13)} & {mix_form} & {best.max_abs_log_err:.4f} & {delta_tex} & {EinfU:.3f} \\\\"
        )
    rows.append(r"\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "pmns_no_io_stability_rows.tex", rows)
    print("Wrote sections/generated/pmns_no_io_stability_rows.tex")


if __name__ == "__main__":
    main()


