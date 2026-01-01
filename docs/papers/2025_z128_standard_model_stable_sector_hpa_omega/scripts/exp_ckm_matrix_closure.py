# -*- coding: utf-8 -*-
"""
CKM full-matrix closure from three magnitudes + a Jarlskog anchor.

We construct a complex CKM matrix using the PDG standard parameterization
(three angles + one CP phase). We do this twice:
  1) a "PDG reference reconstruction" from the PDG central values of
     |V_us|, |V_cb|, |V_ub| and J (as used elsewhere in this paper),
  2) a "closed prediction" from the bounded-complexity magnitude closure
     (|V_us|,|V_cb|,|V_ub|) together with the rigid J_geo = 1/(11*pi^7).

This yields a reproducible, fully specified 3x3 magnitude table |V_ij| for both,
plus unitarity diagnostics.

Outputs (LaTeX fragments):
  - sections/generated/ckm_angles_rows.tex
  - sections/generated/ckm_matrix_rows.tex
  - sections/generated/ckm_unitarity_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import exp_ckm_mixing_depth_rigidity as ckm


PHI = (1.0 + math.sqrt(5.0)) / 2.0


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        raise ValueError("abs_log_ratio requires positive arguments.")
    return abs(math.log(pred / ref))


@dataclass(frozen=True)
class PDGAngles:
    s12: float
    s23: float
    s13: float
    delta: float  # radians


def delta_from_J(J: float, s12: float, s23: float, s13: float) -> float:
    if not (0.0 < s12 < 1.0 and 0.0 < s23 < 1.0 and 0.0 < s13 < 1.0):
        raise ValueError("sines must lie in (0,1).")
    c12 = math.sqrt(max(0.0, 1.0 - s12 * s12))
    c23 = math.sqrt(max(0.0, 1.0 - s23 * s23))
    c13 = math.sqrt(max(0.0, 1.0 - s13 * s13))
    denom = s12 * s23 * s13 * c12 * c23 * (c13 * c13)
    if denom <= 0.0:
        raise ValueError("Invalid denominator for delta extraction.")
    x = J / denom
    # Numerical safety: clamp to [-1,1].
    x = max(-1.0, min(1.0, x))
    # Choose the principal solution delta in [0,pi], consistent with positive J.
    delta = math.asin(x)
    if delta < 0.0:
        delta = -delta
    return delta


def pdg_parameterization(s12: float, s23: float, s13: float, delta: float) -> List[List[complex]]:
    c12 = math.sqrt(max(0.0, 1.0 - s12 * s12))
    c23 = math.sqrt(max(0.0, 1.0 - s23 * s23))
    c13 = math.sqrt(max(0.0, 1.0 - s13 * s13))

    e_m = cmath.exp(-1j * delta)
    e_p = cmath.exp(+1j * delta)

    Vud = c12 * c13
    Vus = s12 * c13
    Vub = s13 * e_m

    Vcd = -s12 * c23 - c12 * s23 * s13 * e_p
    Vcs = c12 * c23 - s12 * s23 * s13 * e_p
    Vcb = s23 * c13

    Vtd = s12 * s23 - c12 * c23 * s13 * e_p
    Vts = -c12 * s23 - s12 * c23 * s13 * e_p
    Vtb = c23 * c13

    return [
        [Vud, Vus, Vub],
        [Vcd, Vcs, Vcb],
        [Vtd, Vts, Vtb],
    ]


def J_from_angles(s12: float, s23: float, s13: float, delta: float) -> float:
    c12 = math.sqrt(max(0.0, 1.0 - s12 * s12))
    c23 = math.sqrt(max(0.0, 1.0 - s23 * s23))
    c13 = math.sqrt(max(0.0, 1.0 - s13 * s13))
    return s12 * s23 * s13 * c12 * c23 * (c13 * c13) * math.sin(delta)


def unitarity_deviation(V: List[List[complex]]) -> Tuple[List[float], List[float]]:
    # Return row and column deviations of sum |V_ij|^2 from 1.
    row_dev: List[float] = []
    col_dev: List[float] = []
    for i in range(3):
        row_dev.append(sum(abs(V[i][j]) ** 2 for j in range(3)) - 1.0)
    for j in range(3):
        col_dev.append(sum(abs(V[i][j]) ** 2 for i in range(3)) - 1.0)
    return row_dev, col_dev


def format_sci(x: float, sig: int = 6) -> str:
    if x == 0.0:
        return "0"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = ax / (10.0**exp)
    mant_s = f"{mant:.{sig}g}"
    if exp == 0:
        return mant_s
    return f"{mant_s}\\times 10^{{{exp}}}"


def main() -> None:
    # PDG reference inputs (central values; conventions per PDG RPP).
    vus_ref = 0.2243
    vcb_ref = 0.0422
    vub_ref = 0.00394
    J_ref = 3.00e-5

    # Closed prediction inputs.
    # 1) bounded-complexity minimizer at B=20 for magnitudes
    vmax = ckm.v_max_x6()
    best20 = ckm.best_triple_at_B(B=20, vus_ref=vus_ref, vcb_ref=vcb_ref, vub_ref=vub_ref, vmax=vmax)
    vus_pred = 1.0 / math.sqrt(float(best20.m))
    vcb_pred = PHI ** (-0.5 * float(best20.k23))
    vub_pred = PHI ** (-0.5 * float(best20.k13))

    # 2) rigid J_geo
    J_geo = 1.0 / (11.0 * (math.pi**7))

    # Extract angles from the magnitude triplets.
    def angles_from_magnitudes(vus: float, vcb: float, vub: float, J: float) -> PDGAngles:
        s13 = vub
        c13 = math.sqrt(max(0.0, 1.0 - s13 * s13))
        s12 = vus / c13
        s23 = vcb / c13
        delta = delta_from_J(J, s12=s12, s23=s23, s13=s13)
        return PDGAngles(s12=s12, s23=s23, s13=s13, delta=delta)

    ang_ref = angles_from_magnitudes(vus_ref, vcb_ref, vub_ref, J_ref)
    ang_pred = angles_from_magnitudes(vus_pred, vcb_pred, vub_pred, J_geo)

    V_ref = pdg_parameterization(ang_ref.s12, ang_ref.s23, ang_ref.s13, ang_ref.delta)
    V_pred = pdg_parameterization(ang_pred.s12, ang_pred.s23, ang_pred.s13, ang_pred.delta)

    # Derived J values (consistency diagnostics).
    J_ref_back = J_from_angles(ang_ref.s12, ang_ref.s23, ang_ref.s13, ang_ref.delta)
    J_pred_back = J_from_angles(ang_pred.s12, ang_pred.s23, ang_pred.s13, ang_pred.delta)

    # Unitarity deviations.
    row_ref, col_ref = unitarity_deviation(V_ref)
    row_pred, col_pred = unitarity_deviation(V_pred)

    # Build element-wise magnitude comparison.
    names = [
        ("ud", 0, 0),
        ("us", 0, 1),
        ("ub", 0, 2),
        ("cd", 1, 0),
        ("cs", 1, 1),
        ("cb", 1, 2),
        ("td", 2, 0),
        ("ts", 2, 1),
        ("tb", 2, 2),
    ]

    def absV(V: List[List[complex]], i: int, j: int) -> float:
        return abs(V[i][j])

    # Output directories.
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Angles table rows.
    angle_rows: List[str] = []
    angle_rows.append(
        f"$s_{{12}}$ & {ang_ref.s12:.9g} & {ang_pred.s12:.9g} & {math.log(ang_pred.s12/ang_ref.s12):.6f} \\\\"
    )
    angle_rows.append(
        f"$s_{{23}}$ & {ang_ref.s23:.9g} & {ang_pred.s23:.9g} & {math.log(ang_pred.s23/ang_ref.s23):.6f} \\\\"
    )
    angle_rows.append(
        f"$s_{{13}}$ & {ang_ref.s13:.9g} & {ang_pred.s13:.9g} & {math.log(ang_pred.s13/ang_ref.s13):.6f} \\\\"
    )
    deg_ref = ang_ref.delta * 180.0 / math.pi
    deg_pred = ang_pred.delta * 180.0 / math.pi
    angle_rows.append(
        f"$\\delta$ [deg] & {deg_ref:.6f} & {deg_pred:.6f} & {deg_pred-deg_ref:.6f} \\\\"
    )
    angle_rows.append(
        f"$J$ & ${format_sci(J_ref, sig=6)}$ & ${format_sci(J_pred_back, sig=6)}$ & {math.log(J_pred_back/J_ref):.6f} \\\\"
    )
    angle_rows.append("\\bottomrule")
    (out_dir / "ckm_angles_rows.tex").write_text("\n".join(angle_rows), encoding="utf-8")

    # Matrix magnitude rows.
    mat_rows: List[str] = []
    for tag, i, j in names:
        ref_val = absV(V_ref, i, j)
        pred_val = absV(V_pred, i, j)
        mat_rows.append(
            f"$|V_{{{tag}}}|$ & {ref_val:.9g} & {pred_val:.9g} & {math.log(pred_val/ref_val):.6f} \\\\"
        )
    mat_rows.append("\\bottomrule")
    (out_dir / "ckm_matrix_rows.tex").write_text("\n".join(mat_rows), encoding="utf-8")

    # Unitarity diagnostic rows.
    uni_rows: List[str] = []
    for k in range(3):
        uni_rows.append(
            f"row {k+1} & {row_ref[k]:+.3e} & {row_pred[k]:+.3e} \\\\"
        )
    for k in range(3):
        uni_rows.append(
            f"col {k+1} & {col_ref[k]:+.3e} & {col_pred[k]:+.3e} \\\\"
        )
    uni_rows.append("\\bottomrule")
    (out_dir / "ckm_unitarity_rows.tex").write_text("\n".join(uni_rows), encoding="utf-8")

    print("Wrote sections/generated/ckm_angles_rows.tex, ckm_matrix_rows.tex, ckm_unitarity_rows.tex")
    # Extra diagnostics (not written to LaTeX):
    print("B=20 minimizer (m,k23,k13):", (best20.m, best20.k23, best20.k13))
    print("J_ref_back:", J_ref_back, "J_pred_back:", J_pred_back, "J_geo:", J_geo)


if __name__ == "__main__":
    main()



