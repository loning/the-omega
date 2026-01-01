# -*- coding: utf-8 -*-
"""
Bounded-coefficient rigidity search for the depth ansatz used in the mass-spectrum closure.

We search integer triples (a,b,c) in the box |a|,|b|,|c| <= B for B=1..20
in the ansatz:
  r_hat(w) = a * ΔV + b * Δg + c * Δ|w|_1

where differences are taken relative to the electron reference stable type.

We evaluate the depth mismatch on a fermion anchor set:
  {u, d, s, c, b, t, mu, tau}
using r(mu) = log(mu/m_e)/log(phi).

The script writes a LaTeX table-row fragment to:
  sections/generated/mass_depth_rigidity_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import exp_sm_labeling_solver as sml


PHI = (1.0 + math.sqrt(5.0)) / 2.0
LOG_PHI = math.log(PHI)


def r_of_mu(mu: float, mu0: float) -> float:
    return math.log(mu / mu0) / LOG_PHI


@dataclass(frozen=True)
class Hit:
    a: int
    b: int
    c: int
    max_lep: float
    sum_lep: float
    max_ext: float
    sum_ext: float
    max_coeff: int
    abs_sum: int

    def key(self) -> Tuple[float, float, int, int, int]:
        # Lexicographic minimization:
        # 1) leptonic minimax, 2) leptonic sum,
        # 3) extended minimax, 4) extended sum,
        # 5) coefficient complexity (max coeff then abs-sum), then lexical.
        return (
            self.max_lep,
            self.sum_lep,
            self.max_ext,
            self.sum_ext,
            float(self.max_coeff),
            float(self.abs_sum),
            float(self.a),
            float(self.b),
            float(self.c),
        )


def build_word_for_field() -> Dict[Tuple[int, str], str]:
    # Mirror the assignment logic used by exp_sm_labeling_solver, without parsing LaTeX.
    X6 = sml.all_x6()
    cyclic = [w for w in X6 if not sml.is_boundary_word(w)]
    cyclic_sorted = sorted(cyclic, key=lambda w: sml.stable_type_sort_key(w))
    fields = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
    if len(cyclic_sorted) != len(fields):
        raise AssertionError("Cyclic set and fermion targets must match.")
    out: Dict[Tuple[int, str], str] = {}
    for w, f in zip(cyclic_sorted, fields):
        out[(f.generation, f.name)] = w
    return out


def invariants_for_word(w: str) -> Tuple[int, int, int]:
    V = sml.zeckendorf_value(w)
    g = sml.degeneracy_g(w)
    wt = w.count("1")
    return V, g, wt


def main() -> None:
    # Scheme-stable reference masses (GeV), consistent with the PCG calibration table.
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

    word_for = build_word_for_field()
    w_e = word_for[(1, "e_R")]
    V_e, g_e, wt_e = invariants_for_word(w_e)

    # Map anchors to stable-type labels under the closed labeling map.
    # We use u_R^(g) for {u,c,t} and d_R^(g) for {d,s,b}, consistent with exp_mass_spectrum.py.
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

    anchor_depths: List[Tuple[str, float, Tuple[int, int, int]]] = []
    for name, mu in anchors:
        w = anchor_words[name]
        r_ref = r_of_mu(mu, m_e)
        inv = invariants_for_word(w)
        anchor_depths.append((name, r_ref, inv))

    leptonic_names = {"mu", "tau"}

    rows: List[str] = []
    for B in range(1, 21):
        best: Optional[Hit] = None
        best_count = 0

        for a in range(-B, B + 1):
            for b in range(-B, B + 1):
                for c in range(-B, B + 1):
                    if a == 0 and b == 0 and c == 0:
                        continue
                    # Fix sign convention: require a >= 0, and if a==0 require b >= 0, etc.
                    if a < 0:
                        continue
                    if a == 0 and b < 0:
                        continue
                    if a == 0 and b == 0 and c < 0:
                        continue

                    errs_lep: List[float] = []
                    errs_ext: List[float] = []
                    for name, r_ref, inv in anchor_depths:
                        V, g, wt = inv
                        dV = V - V_e
                        dg = g - g_e
                        dwt = wt - wt_e
                        r_hat = a * dV + b * dg + c * dwt
                        err = abs(r_ref - float(r_hat))
                        errs_ext.append(err)
                        if name in leptonic_names:
                            errs_lep.append(err)

                    max_lep = max(errs_lep)
                    sum_lep = sum(errs_lep)
                    max_ext = max(errs_ext)
                    sum_ext = sum(errs_ext)

                    max_coeff = max(abs(a), abs(b), abs(c))
                    abs_sum = abs(a) + abs(b) + abs(c)

                    hit = Hit(
                        a=a,
                        b=b,
                        c=c,
                        max_lep=max_lep,
                        sum_lep=sum_lep,
                        max_ext=max_ext,
                        sum_ext=sum_ext,
                        max_coeff=max_coeff,
                        abs_sum=abs_sum,
                    )
                    if best is None or hit.key() < best.key():
                        best = hit
                        best_count = 1
                    elif best is not None and hit.key() == best.key():
                        best_count += 1

        if best is None:
            raise AssertionError("No candidates found.")

        # Re-evaluate selected best on both metric sets for output.
        a, b, c = best.a, best.b, best.c
        errs_lep_out: List[float] = []
        errs_ext_out: List[float] = []
        for name, r_ref, inv in anchor_depths:
            V, g, wt = inv
            dV = V - V_e
            dg = g - g_e
            dwt = wt - wt_e
            r_hat = a * dV + b * dg + c * dwt
            err = abs(r_ref - float(r_hat))
            errs_ext_out.append(err)
            if name in leptonic_names:
                errs_lep_out.append(err)

        max_lep = max(errs_lep_out)
        sum_lep = sum(errs_lep_out)
        max_ext = max(errs_ext_out)
        sum_ext = sum(errs_ext_out)

        rows.append(
            f"{B} & $({a},{b},{c})$ & {max_lep:.6f} & {sum_lep:.6f} & {max_ext:.6f} & {sum_ext:.6f} \\\\"
        )

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_with_rules = rows + ["\\bottomrule"]
    out_path = out_dir / "mass_depth_rigidity_rows.tex"
    # Important: do not add a trailing blank line; this fragment is included inside a tabular environment.
    out_path.write_text("\n".join(rows_with_rules), encoding="utf-8")
    print("Wrote sections/generated/mass_depth_rigidity_rows.tex")


if __name__ == "__main__":
    main()


