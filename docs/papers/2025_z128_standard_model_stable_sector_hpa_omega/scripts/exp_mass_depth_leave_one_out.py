# -*- coding: utf-8 -*-
"""
Leave-one-out robustness diagnostic for the mass-depth coefficient search.

The paper records a bounded-coefficient rigidity certificate for the depth ansatz:
  r_hat(w) = a*ΔV + b*Δg + c*Δ|w|_1

This script repeats the B=20 search while leaving out one anchor at a time from the
finite anchor set used by exp_mass_depth_rigidity.py and reports whether the selected
minimizer (a,b,c) changes.

Output (LaTeX fragment):
  - sections/generated/mass_depth_leave_one_out_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import exp_mass_depth_rigidity as base
from common_tex import write_lines


@dataclass(frozen=True)
class Best:
    a: int
    b: int
    c: int
    max_lep: float
    sum_lep: float
    max_ext: float
    sum_ext: float

    def key(self) -> Tuple[float, float, float, float, int, int, int, int, int]:
        # Mirror the lexicographic rule used in exp_mass_depth_rigidity.py.
        max_coeff = max(abs(self.a), abs(self.b), abs(self.c))
        abs_sum = abs(self.a) + abs(self.b) + abs(self.c)
        return (
            self.max_lep,
            self.sum_lep,
            self.max_ext,
            self.sum_ext,
            max_coeff,
            abs_sum,
            self.a,
            self.b,
            self.c,
        )


def _build_anchor_depths() -> Tuple[Dict[str, Tuple[float, Tuple[int, int, int]]], Tuple[int, int, int]]:
    """
    Return:
      - anchors: name -> (r_ref, (V,g,wt)) for the finite anchor set,
      - electron invariants (V_e,g_e,wt_e).
    """
    # Same masses and naming as exp_mass_depth_rigidity.py.
    m_e = 5.1099895e-4
    anchors: List[Tuple[str, float]] = [
        ("u", 2.16e-3),
        ("d", 4.67e-3),
        ("s", 9.30e-2),
        ("c", 1.27),
        ("b", 4.18),
        ("t", 172.76),
        ("mu", 1.0565838e-1),
        ("tau", 1.77686),
    ]

    word_for = base.build_word_for_field()
    w_e = word_for[(1, "e_R")]
    V_e, g_e, wt_e = base.invariants_for_word(w_e)

    # Stable-type labels for the same anchor identification used in exp_mass_depth_rigidity.py.
    anchor_words: Dict[str, str] = {
        "u": word_for[(1, "u_R")],
        "c": word_for[(2, "u_R")],
        "t": word_for[(3, "u_R")],
        "d": word_for[(1, "d_R")],
        "s": word_for[(2, "d_R")],
        "b": word_for[(3, "d_R")],
        "mu": word_for[(2, "e_R")],
        "tau": word_for[(3, "e_R")],
    }

    out: Dict[str, Tuple[float, Tuple[int, int, int]]] = {}
    for name, mu in anchors:
        w = anchor_words[name]
        r_ref = base.r_of_mu(mu, m_e)
        inv = base.invariants_for_word(w)
        out[name] = (r_ref, inv)
    return out, (V_e, g_e, wt_e)


def _best_coeffs(
    anchors: Dict[str, Tuple[float, Tuple[int, int, int]]],
    electron_inv: Tuple[int, int, int],
    leptonic_names: Set[str],
    include: Set[str],
    B: int = 20,
) -> Best:
    V_e, g_e, wt_e = electron_inv
    best: Optional[Best] = None

    for a in range(-B, B + 1):
        for b in range(-B, B + 1):
            for c in range(-B, B + 1):
                if a == 0 and b == 0 and c == 0:
                    continue
                # Deterministic sign convention (same as base script): a>=0, then b>=0 if a==0, etc.
                if a < 0:
                    continue
                if a == 0 and b < 0:
                    continue
                if a == 0 and b == 0 and c < 0:
                    continue

                errs_lep: List[float] = []
                errs_ext: List[float] = []
                for name in include:
                    r_ref, inv = anchors[name]
                    V, g, wt = inv
                    dV = V - V_e
                    dg = g - g_e
                    dwt = wt - wt_e
                    r_hat = a * dV + b * dg + c * dwt
                    err = abs(r_ref - float(r_hat))
                    errs_ext.append(err)
                    if name in leptonic_names:
                        errs_lep.append(err)

                # If the leptonic subset is empty (should not occur), fall back to extended metrics.
                if errs_lep:
                    max_lep = max(errs_lep)
                    sum_lep = sum(errs_lep)
                else:
                    max_lep = max(errs_ext)
                    sum_lep = sum(errs_ext)
                max_ext = max(errs_ext)
                sum_ext = sum(errs_ext)

                cand = Best(a=a, b=b, c=c, max_lep=max_lep, sum_lep=sum_lep, max_ext=max_ext, sum_ext=sum_ext)
                if best is None or cand.key() < best.key():
                    best = cand

    if best is None:
        raise AssertionError("No candidates found.")
    return best


def main() -> None:
    anchors, electron_inv = _build_anchor_depths()
    names = ["u", "d", "s", "c", "b", "t", "mu", "tau"]
    leptonic = {"mu", "tau"}

    # Baseline (no leave-out).
    base_set = set(names)
    baseline = _best_coeffs(anchors, electron_inv, leptonic_names=leptonic, include=base_set, B=20)

    rows: List[str] = []
    diff_leave: List[str] = []

    def row(label: str, sel: Best) -> str:
        same = "SAME" if (sel.a, sel.b, sel.c) == (baseline.a, baseline.b, baseline.c) else "DIFF"
        return (
            f"{label} & $({sel.a},{sel.b},{sel.c})$ & {sel.max_lep:.6f} & {sel.sum_lep:.6f} & "
            f"{sel.max_ext:.6f} & {sel.sum_ext:.6f} & {same} \\\\"
        )

    rows.append(row(r"\texttt{none}", baseline))
    for leave in names:
        inc = set(names)
        inc.remove(leave)
        sel = _best_coeffs(anchors, electron_inv, leptonic_names=leptonic, include=inc, B=20)
        if (sel.a, sel.b, sel.c) != (baseline.a, baseline.b, baseline.c):
            diff_leave.append(leave)
        rows.append(row(rf"\texttt{{-{leave}}}", sel))
    rows.append(r"\bottomrule")

    # Summary: how often the baseline minimizer is preserved under leave-one-out.
    n_total = len(names)
    n_diff = len(diff_leave)
    n_same = n_total - n_diff
    diff_tex = ", ".join(rf"\texttt{{-{x}}}" for x in diff_leave) if diff_leave else r"$\varnothing$"
    summary_rows: List[str] = [
        rf"{n_total} & {n_same} & {n_diff} & {diff_tex} \\",
        r"\bottomrule",
    ]

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "mass_depth_leave_one_out_rows.tex", rows)
    print("Wrote sections/generated/mass_depth_leave_one_out_rows.tex")
    write_lines(out_dir / "mass_depth_leave_one_out_summary_rows.tex", summary_rows)
    print("Wrote sections/generated/mass_depth_leave_one_out_summary_rows.tex")


if __name__ == "__main__":
    main()


