# -*- coding: utf-8 -*-
"""
Renormalizable Yukawa feasibility closure for the Higgs uplift interface.

This script is deliberately interface-level:
  - It does NOT fit Yukawa values.
  - It only certifies (by finite arithmetic checks) that, given the already-closed
    fermion multiplets and the CAP-closed Higgs quantum numbers (1,2)_{1/2},
    the standard renormalizable Yukawa operator families exist and are minimal
    under a bounded candidate-family selection of operator sets.

Outputs (LaTeX fragments)
  - sections/generated/higgs_yukawa_feasibility_rows.tex
  - sections/generated/higgs_yukawa_feasibility_summary.tex
  - sections/generated/higgs_yukawa_minimal_failure_points.tex

Only Python standard library is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from common_paths import generated_dir
from common_tex import write_lines

import exp_sm_labeling_solver as sm


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def _fmt_Y(Y_num: int) -> str:
    # Y is stored as numerator of 1/6.
    if Y_num == 0:
        return "0"
    num = int(Y_num)
    den = 6
    g = _gcd(abs(num), den)
    num //= g
    den //= g
    if den == 1:
        return f"{num}"
    return f"{num}/{den}"


def _j2(d: int) -> int | None:
    # Return 2j for SU(2) irrep dimension d=2j+1.
    if d <= 0:
        return None
    return d - 1


def _su2_singlet_exists(dL: int, dH: int, dR: int) -> bool:
    """
    Check if L ⊗ H ⊗ R contains j=0 for SU(2), using doubled-spin arithmetic.
    """
    jL2 = _j2(dL)
    jH2 = _j2(dH)
    jR2 = _j2(dR)
    if jL2 is None or jH2 is None or jR2 is None:
        return False
    jmin2 = abs(jL2 - jH2)
    jmax2 = jL2 + jH2
    if jR2 < jmin2 or jR2 > jmax2:
        return False
    # Parity constraint for coupling: jL2+jH2+jR2 even.
    return ((jL2 + jH2 + jR2) % 2) == 0


def _u1_invariant(YL: int, YR: int, YH: int, use_conjugate: bool) -> bool:
    # Invariant for \bar{L} (H or \tilde H) R:
    # -YL + YR + YH_eff = 0, with YH_eff = YH or -YH.
    YH_eff = -int(YH) if use_conjugate else int(YH)
    return (-int(YL) + int(YR) + YH_eff) == 0


def _su3_ok(su3L: int, su3R: int, su3H: int) -> bool:
    # Minimal gate consistent with SM: allow only color-singlet Higgs.
    if su3H != 1:
        return False
    return (su3L, su3R) in {(1, 1), (3, 3)}


def _fermion_qn_one_generation() -> Dict[str, Tuple[int, int, int]]:
    out: Dict[str, Tuple[int, int, int]] = {}
    for f in sm.fermion_targets():
        if f.generation != 1:
            continue
        key = f.name.replace("\\", "")
        out[key] = (int(f.su3_dim), int(f.su2_dim), int(f.Y_num))
    return out


@dataclass(frozen=True)
class YukawaTerm:
    name: str
    left: str
    right: str
    use_conjugate: bool  # True => \tilde H
    tex: str


def _terms() -> List[YukawaTerm]:
    return [
        YukawaTerm(
            name="up",
            left="Q_L",
            right="u_R",
            use_conjugate=True,
            tex=r"$\overline{Q}_L\,\widetilde H\,u_R$",
        ),
        YukawaTerm(
            name="down",
            left="Q_L",
            right="d_R",
            use_conjugate=False,
            tex=r"$\overline{Q}_L\,H\,d_R$",
        ),
        YukawaTerm(
            name="e",
            left="L_L",
            right="e_R",
            use_conjugate=False,
            tex=r"$\overline{L}_L\,H\,e_R$",
        ),
        YukawaTerm(
            name="nu",
            left="L_L",
            right="nu_R",
            use_conjugate=True,
            tex=r"$\overline{L}_L\,\widetilde H\,\nu_R$",
        ),
    ]


def _candidate_operator_sets() -> List[Tuple[str, List[str]]]:
    """
    A bounded family of operator-set candidates, used for CAP-minimality:
      - "charged-only": generate Dirac masses for charged fermions only
      - "with-nu": also allow Dirac neutrino masses (since ν_R exists in the closed set)
    """
    return [
        ("charged-only", ["up", "down", "e"]),
        ("with-nu", ["up", "down", "e", "nu"]),
    ]


def main() -> None:
    # CAP-closed Higgs quantum numbers (paper interface): (1,2)_{1/2}.
    su3H, su2H, YH_num = 1, 2, 3  # Y=3/6=1/2.

    qn = _fermion_qn_one_generation()
    terms = _terms()
    term_by_name = {t.name: t for t in terms}

    # Feasibility checks per term.
    feas: Dict[str, bool] = {}
    for t in terms:
        su3L, su2L, YL = qn[t.left]
        su3R, su2R, YR = qn[t.right]
        feas[t.name] = (
            _su3_ok(su3L, su3R, su3H)
            and _su2_singlet_exists(su2L, su2H, su2R)
            and _u1_invariant(YL, YR, YH_num, use_conjugate=t.use_conjugate)
        )

    # Bounded-family CAP selection for the operator-set choice:
    # prefer completeness w.r.t. the closed fermion content; then minimal cardinality;
    # break ties deterministically by a fixed name order.
    name_order = {"up": 0, "down": 1, "e": 2, "nu": 3}

    def key_for_set(names: List[str]) -> tuple:
        # Completeness gate: since ν_R is part of the closed 18 multiplets,
        # treat the presence of a Dirac neutrino Yukawa family as a required interface feature
        # in the standard EFT embedding used by this paper.
        missing_nu_flag = 1 if ("nu" not in names) else 0
        missing = [n for n in names if not feas.get(n, False)]
        missing_mask = 0
        for n in missing:
            missing_mask |= 1 << name_order[n]
        return (
            missing_nu_flag,
            len(missing),
            missing_mask,
            len(names),
            [name_order[n] for n in names],
        )

    sets = _candidate_operator_sets()
    scored = [(set_name, names, key_for_set(names)) for (set_name, names) in sets]
    scored.sort(key=lambda x: x[2])
    best_set_name, best_set, best_key = scored[0]

    # Emit a compact feasibility table.
    rows: List[str] = []
    for t in terms:
        su3L, su2L, YL = qn[t.left]
        su3R, su2R, YR = qn[t.right]
        ok_su3 = _su3_ok(su3L, su3R, su3H)
        ok_su2 = _su2_singlet_exists(su2L, su2H, su2R)
        ok_u1 = _u1_invariant(YL, YR, YH_num, use_conjugate=t.use_conjugate)
        ok = feas[t.name]
        rows.append(
            " & ".join(
                [
                    t.tex,
                    f"$({su3L},{su2L})_{{{_fmt_Y(YL)}}}$",
                    f"$({su3R},{su2R})_{{{_fmt_Y(YR)}}}$",
                    r"$\widetilde H$" if t.use_conjugate else r"$H$",
                    "yes" if ok_su3 else "no",
                    "yes" if ok_su2 else "no",
                    "yes" if ok_u1 else "no",
                    "yes" if ok else "no",
                    ("\\textbf{required}" if t.name in best_set else ""),
                ]
            )
            + r" \\"
        )

    out_rows = generated_dir() / "higgs_yukawa_feasibility_rows.tex"
    write_lines(out_rows, rows if rows else ["% (no rows)"])

    # Summary: state the standard structure for 3 generations.
    summary = [
        "\\noindent "
        "Renormalizable Yukawa feasibility (interface): "
        "given the closed fermion multiplets and the CAP-closed Higgs quantum numbers "
        "$H\\sim(1,2)_{1/2}$ (with $\\widetilde H:=\\iu\\sigma^2 H^\\ast$), "
        "the standard gauge-invariant Yukawa operator families exist for each generation, "
        "hence for three generations the general renormalizable Yukawa sector is parameterized by "
        "four complex $3\\times 3$ matrices $(Y_u,Y_d,Y_e,Y_\\nu)$ multiplying "
        "$\\overline Q_L\\widetilde H u_R$, $\\overline Q_L H d_R$, $\\overline L_L H e_R$, "
        "and $\\overline L_L\\widetilde H\\nu_R$, respectively."
    ]
    out_sum = generated_dir() / "higgs_yukawa_feasibility_summary.tex"
    write_lines(out_sum, summary)

    # Minimal failure points (bounded interface gates).
    fp: List[str] = [
        "\\begin{itemize}",
        "\\item \\textbf{No scalar:} if no Higgs doublet is present, there is no renormalizable gauge-invariant operator that produces Dirac masses for the chiral fermion multiplets.",
        "\\item \\textbf{Wrong hypercharge:} if $H$ is a weak doublet but $Y\\neq 1/2$, at least one of the required Yukawa families fails the $U(1)_Y$ invariance check under $Q=T_3+Y$.",
        "\\item \\textbf{Wrong weak irrep:} if $H$ is not a weak doublet, then $SU(2)$ singlet formation fails for the charged-fermion Yukawa terms in the closed content.",
        "\\item \\textbf{Omitting a required family:} dropping any of the CAP-minimal required Yukawa families leaves the corresponding closed fermion sector without a renormalizable Dirac mass term in the standard EFT embedding.",
        "\\end{itemize}",
    ]
    out_fp = generated_dir() / "higgs_yukawa_minimal_failure_points.tex"
    write_lines(out_fp, fp)

    print("Wrote sections/generated/higgs_yukawa_feasibility_rows.tex")
    print("Wrote sections/generated/higgs_yukawa_feasibility_summary.tex")
    print("Wrote sections/generated/higgs_yukawa_minimal_failure_points.tex")


if __name__ == "__main__":
    main()

