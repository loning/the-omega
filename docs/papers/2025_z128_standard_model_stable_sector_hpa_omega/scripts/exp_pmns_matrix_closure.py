# -*- coding: utf-8 -*-
"""
PMNS full-matrix closure from bounded-complexity angles + a discrete CP-phase closure.

We use the PDG standard 3-angle + 1-Dirac-phase parameterization (Majorana phases
do not affect oscillation probabilities and are ignored here).

We construct:
  1) a "reference reconstruction" from representative global-fit central values,
  2) a "closed prediction" from the bounded-complexity angle closure and a
     protocol-level discrete CP-phase closure over a tiny finite candidate family.

For the Dirac phase delta we use a bounded-denominator rational-angle candidate family:
  delta = (k*pi)/q, with 1 <= q <= Q and 1 <= k <= 2q-1, reduced by gcd(k,q)=1.
We select delta by an auditable CP-odd anchor rule against the reference reconstruction:
  - prefer candidates with sign(J_pred) == sign(J_ref),
  - prefer candidates with sign(cos delta) == sign(cos delta_ref) (to fix the quadrant; magnitudes depend on cos delta),
  - then minimize |log(|J_pred|/|J_ref|)|,
  - then minimize (q, k) as a bounded-complexity tie-break.

Outputs (LaTeX fragments):
  - sections/generated/pmns_delta_sweep_rows.tex
  - sections/generated/pmns_angles_rows.tex
  - sections/generated/pmns_matrix_rows.tex
  - sections/generated/pmns_unitarity_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import exp_pmns_mixing_depth_rigidity as pmns
from common_constants import PMNS_DELTA_REF_DEG, PMNS_SIN2_T12_REF, PMNS_SIN2_T13_REF, PMNS_SIN2_T23_REF


@dataclass(frozen=True)
class Angles:
    s12: float
    s23: float
    s13: float
    delta: float  # radians


@dataclass(frozen=True)
class DeltaCand:
    q: int
    k: int
    delta: float  # radians in [0,2pi)


def pmns_parameterization(s12: float, s23: float, s13: float, delta: float) -> List[List[complex]]:
    c12 = math.sqrt(max(0.0, 1.0 - s12 * s12))
    c23 = math.sqrt(max(0.0, 1.0 - s23 * s23))
    c13 = math.sqrt(max(0.0, 1.0 - s13 * s13))

    e_m = cmath.exp(-1j * delta)
    e_p = cmath.exp(+1j * delta)

    Ue1 = c12 * c13
    Ue2 = s12 * c13
    Ue3 = s13 * e_m

    Um1 = -s12 * c23 - c12 * s23 * s13 * e_p
    Um2 = c12 * c23 - s12 * s23 * s13 * e_p
    Um3 = s23 * c13

    Ut1 = s12 * s23 - c12 * c23 * s13 * e_p
    Ut2 = -c12 * s23 - s12 * c23 * s13 * e_p
    Ut3 = c23 * c13

    return [
        [Ue1, Ue2, Ue3],
        [Um1, Um2, Um3],
        [Ut1, Ut2, Ut3],
    ]


def J_from_angles(s12: float, s23: float, s13: float, delta: float) -> float:
    c12 = math.sqrt(max(0.0, 1.0 - s12 * s12))
    c23 = math.sqrt(max(0.0, 1.0 - s23 * s23))
    c13 = math.sqrt(max(0.0, 1.0 - s13 * s13))
    return s12 * s23 * s13 * c12 * c23 * (c13 * c13) * math.sin(delta)


def unitarity_deviation(U: List[List[complex]]) -> Tuple[List[float], List[float]]:
    row_dev: List[float] = []
    col_dev: List[float] = []
    for i in range(3):
        row_dev.append(sum(abs(U[i][j]) ** 2 for j in range(3)) - 1.0)
    for j in range(3):
        col_dev.append(sum(abs(U[i][j]) ** 2 for i in range(3)) - 1.0)
    return row_dev, col_dev


def _sgn(x: float, eps: float = 0.0) -> int:
    if x > eps:
        return +1
    if x < -eps:
        return -1
    return 0


def _abs_log_ratio(x: float, y: float) -> float:
    if x <= 0.0 or y <= 0.0:
        return float("inf")
    return abs(math.log(x / y))


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a)


def delta_candidates_bounded_denominator(Q: int) -> List[DeltaCand]:
    """
    Enumerate reduced rational multiples delta=(k*pi)/q with 1<=q<=Q and 1<=k<=2q-1.
    Returned candidates are unique by (q,k) with gcd(k,q)=1 and sorted by (q,k).
    """
    if Q < 1:
        raise ValueError("Q must be >= 1")
    out: List[DeltaCand] = []
    for q in range(1, Q + 1):
        for k in range(1, 2 * q):
            if _gcd(k, q) != 1:
                continue
            d = (float(k) * math.pi) / float(q)
            # normalize to [0,2pi)
            d = d % (2.0 * math.pi)
            out.append(DeltaCand(q=q, k=k, delta=d))
    out.sort(key=lambda c: (c.q, c.k))
    return out


def select_delta_discrete(
    s12: float,
    s23: float,
    s13: float,
    J_ref: float,
    cos_ref_sign: int,
    candidates: List[DeltaCand],
) -> DeltaCand:
    """
    Select delta from a finite candidate set by a CP-odd anchor rule:
      - prefer candidates with sign(J_pred) == sign(J_ref),
      - then prefer candidates with sign(cos delta) matching the reference quadrant,
      - break ties by minimizing |log(|J_pred|/|J_ref|)|,
      - then by bounded-complexity order (q,k).
    """
    best = None  # (sign_mismatch, cos_mismatch, eJ, q, k)
    best_cand = candidates[0]
    for c in candidates:
        Jp = J_from_angles(s12, s23, s13, c.delta)
        sign_mismatch = 0 if _sgn(Jp) == _sgn(J_ref) else 1
        cos_mismatch = 0 if _sgn(math.cos(c.delta)) == cos_ref_sign else 1
        eJ = _abs_log_ratio(abs(Jp), abs(J_ref)) if (Jp != 0.0 and J_ref != 0.0) else float("inf")
        cand = (sign_mismatch, cos_mismatch, eJ, c.q, c.k)
        if best is None or cand < best:
            best = cand
            best_cand = c
    return best_cand


def main() -> None:
    # Reference inputs (representative global-fit central values; PDG conventions).
    sin2_t12 = PMNS_SIN2_T12_REF
    sin2_t23 = PMNS_SIN2_T23_REF
    sin2_t13 = PMNS_SIN2_T13_REF
    # A representative Dirac phase (degrees). This parameter remains uncertain;
    # the paper treats delta_pred below as a discrete protocol-level closure.
    delta_ref_deg = PMNS_DELTA_REF_DEG

    ref = Angles(
        s12=math.sqrt(sin2_t12),
        s23=math.sqrt(sin2_t23),
        s13=math.sqrt(sin2_t13),
        delta=delta_ref_deg * math.pi / 180.0,
    )
    cos_ref_sign = _sgn(math.cos(ref.delta))

    # Closed prediction:
    # angles from bounded-complexity minimizer at B=20
    best20 = pmns.best_triple_at_B(B=20, s12_ref=ref.s12, s23_ref=ref.s23, s13_ref=ref.s13)
    s12_pred = math.sqrt(float(best20.p12) / float(best20.q12))
    s23_pred = math.sqrt(float(best20.p23) / float(best20.q23))
    # Use the same phi^{ -k/2 } amplitude family as in CKM.
    PHI = (1.0 + math.sqrt(5.0)) / 2.0
    s13_pred = PHI ** (-0.5 * float(best20.k13))

    J_ref = J_from_angles(ref.s12, ref.s23, ref.s13, ref.delta)
    # Bounded-denominator rational-angle closure for delta.
    # The candidate family size grows quadratically with Q; we keep Q small and auditable.
    Q_MAX = 12
    delta_candidates_QMAX = delta_candidates_bounded_denominator(Q_MAX)
    delta_pred_cand = select_delta_discrete(
        s12=s12_pred,
        s23=s23_pred,
        s13=s13_pred,
        J_ref=J_ref,
        cos_ref_sign=cos_ref_sign,
        candidates=delta_candidates_QMAX,
    )

    pred = Angles(s12=s12_pred, s23=s23_pred, s13=s13_pred, delta=delta_pred_cand.delta)

    U_ref = pmns_parameterization(ref.s12, ref.s23, ref.s13, ref.delta)
    U_pred = pmns_parameterization(pred.s12, pred.s23, pred.s13, pred.delta)

    J_pred = J_from_angles(pred.s12, pred.s23, pred.s13, pred.delta)

    row_ref, col_ref = unitarity_deviation(U_ref)
    row_pred, col_pred = unitarity_deviation(U_pred)

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Delta bounded-denominator rigidity rows (Q=1..Q_MAX).
    sweep_rows: List[str] = []
    for Q in range(1, Q_MAX + 1):
        cands = delta_candidates_bounded_denominator(Q)
        best_c = select_delta_discrete(
            s12=pred.s12,
            s23=pred.s23,
            s13=pred.s13,
            J_ref=J_ref,
            cos_ref_sign=cos_ref_sign,
            candidates=cands,
        )
        Jd = J_from_angles(pred.s12, pred.s23, pred.s13, best_c.delta)
        sign_ok = "OK" if _sgn(Jd) == _sgn(J_ref) else "FLIP"
        cos_ok = "OK" if _sgn(math.cos(best_c.delta)) == cos_ref_sign else "FLIP"
        eJ = _abs_log_ratio(abs(Jd), abs(J_ref)) if (Jd != 0.0 and J_ref != 0.0) else float("inf")
        deg = best_c.delta * 180.0 / math.pi
        tag_Q = f"{Q}"
        if Q == Q_MAX:
            tag_Q = rf"\textbf{{{tag_Q}}}"
        form = rf"$\delta={best_c.k}\pi/{best_c.q}$"
        sweep_rows.append(f"{tag_Q} & {form} & {deg:.1f} & {sign_ok} & {cos_ok} & {Jd:+.6g} & {eJ:.3f} \\\\")
    sweep_rows.append("\\bottomrule")
    (out_dir / "pmns_delta_sweep_rows.tex").write_text("\n".join(sweep_rows), encoding="utf-8")

    # Angles rows.
    angle_rows: List[str] = []
    angle_rows.append(
        f"$s_{{12}}$ & {ref.s12:.9g} & {pred.s12:.9g} & {math.log(pred.s12/ref.s12):.6f} \\\\"
    )
    angle_rows.append(
        f"$s_{{23}}$ & {ref.s23:.9g} & {pred.s23:.9g} & {math.log(pred.s23/ref.s23):.6f} \\\\"
    )
    angle_rows.append(
        f"$s_{{13}}$ & {ref.s13:.9g} & {pred.s13:.9g} & {math.log(pred.s13/ref.s13):.6f} \\\\"
    )
    deg_ref = ref.delta * 180.0 / math.pi
    deg_pred = pred.delta * 180.0 / math.pi
    angle_rows.append(
        f"$\\delta$ [deg] & {deg_ref:.6f} & {deg_pred:.6f} & {deg_pred-deg_ref:.6f} \\\\"
    )
    # J can be negative depending on delta convention; report signed value and compare by ratio of magnitudes.
    if J_ref == 0.0:
        jr = 0.0
    else:
        jr = math.log(abs(J_pred) / abs(J_ref))
    angle_rows.append(f"$J_\\ell$ & {J_ref:+.6g} & {J_pred:+.6g} & {jr:.6f} \\\\")
    angle_rows.append("\\bottomrule")
    (out_dir / "pmns_angles_rows.tex").write_text("\n".join(angle_rows), encoding="utf-8")

    # Matrix magnitude rows.
    names = [
        ("e1", 0, 0),
        ("e2", 0, 1),
        ("e3", 0, 2),
        ("\\mu1", 1, 0),
        ("\\mu2", 1, 1),
        ("\\mu3", 1, 2),
        ("\\tau1", 2, 0),
        ("\\tau2", 2, 1),
        ("\\tau3", 2, 2),
    ]

    mat_rows: List[str] = []
    for tag, i, j in names:
        ref_val = abs(U_ref[i][j])
        pred_val = abs(U_pred[i][j])
        mat_rows.append(
            f"$|U_{{{tag}}}|$ & {ref_val:.9g} & {pred_val:.9g} & {math.log(pred_val/ref_val):.6f} \\\\"
        )
    mat_rows.append("\\bottomrule")
    (out_dir / "pmns_matrix_rows.tex").write_text("\n".join(mat_rows), encoding="utf-8")

    # Unitarity diagnostic rows.
    uni_rows: List[str] = []
    for k in range(3):
        uni_rows.append(f"row {k+1} & {row_ref[k]:+.3e} & {row_pred[k]:+.3e} \\\\")
    for k in range(3):
        uni_rows.append(f"col {k+1} & {col_ref[k]:+.3e} & {col_pred[k]:+.3e} \\\\")
    uni_rows.append("\\bottomrule")
    (out_dir / "pmns_unitarity_rows.tex").write_text("\n".join(uni_rows), encoding="utf-8")

    print(
        "Wrote sections/generated/pmns_delta_sweep_rows.tex, pmns_angles_rows.tex, pmns_matrix_rows.tex, pmns_unitarity_rows.tex"
    )


if __name__ == "__main__":
    main()


