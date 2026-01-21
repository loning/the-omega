#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resolution-weighted electroweak match audit.

Goal
----
Test whether increasing the word-resolution m (still fully discrete, still under
the Zeckendorf/no-"11" admissibility constraint) can improve matching-layer
agreement with Z-scale electroweak reference targets by replacing the fixed
anchor weight sum_f Y_f^2 = 10 (three generations) with an m-dependent effective
weight induced by a protocol-native pushforward measure.

Core idea
---------
For each m in a small sweep, define a discrete microstate space Ω_m={0,...,2^m-1}
with uniform counting measure. Push forward this measure to X_m via Fold_m, then
project to X_6 by the prefix map w[:6]. This yields a probability distribution
μ_6^(m) over the 21 base types u in X_6.

Using the closed labeling order used in the paper, cyclic base types u∈X_6^cyc
are mapped to the 18 chiral multiplets (including ν_R) across three generations.
Each multiplet carries a hypercharge Y (PDG convention Q = T3 + Y) and a
multiplicity (#colors * #SU(2) components). Define b(u)=mult(u)*Y(u)^2 on cyclic
u and b(u)=0 on boundary u. Then:

  W_Y_eff(m) := 21 * Σ_{u∈X_6} μ_6^(m)(u) * b(u).

If μ_6^(m) were uniform over X_6, then W_Y_eff(m)=Σ b(u)=10 exactly.

We then define an m-dependent electroweak prediction in the same "weighted
volume" normalization used in the manuscript, keeping the SU(2) weight fixed at
dim(su(2))=3 and replacing the U(1)_Y weight with W_Y_eff(m):

  alpha_inv(mu_Z; m) := (3 + W_Y_eff(m)) * pi^2
  sin2(theta_W; m)   := 3 / (3 + W_Y_eff(m))

We report the audit-norm log mismatches to PDG reference targets.

Outputs
-------
- sections/generated/ew_resolution_weighted_match_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from common_constants import ALPHAZ_INV_PDG, SIN2_THETAW_PDG
from common_paths import generated_dir
import exp_sm_labeling_solver as sml
import protocol_kernel as pk


@dataclass(frozen=True)
class Row:
    m: int
    n_states: int
    p_cyc: float
    n_cyc_eff: float
    w_y_eff: float
    alpha_inv: float
    e_alpha: float
    sin2: float
    e_sin2: float


def _build_x6_to_field_map() -> Dict[str, sml.SMField]:
    """
    Reproduce the cyclic assignment logic used by the closed labeling solver:
      cyclic types ordered by stable_type_sort_key
      fermion targets ordered by SMField.complexity_key()
    """
    X6 = sml.all_x6()
    cyc = [w for w in X6 if not sml.is_boundary_word(w)]
    cyc_sorted = sorted(cyc, key=lambda w: sml.stable_type_sort_key(w))
    fields_sorted = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
    if len(cyc_sorted) != len(fields_sorted):
        raise AssertionError("Cyclic base types and fermion targets must have same size (18).")
    return {u: f for (u, f) in zip(cyc_sorted, fields_sorted)}


def _b_weight_for_u(u: str, u_to_field: Dict[str, sml.SMField]) -> float:
    """
    Return b(u) = multiplicity * Y^2 for cyclic u, else 0 for boundary u.
    Multiplicity is (#colors * #SU2 components) = su3_dim * su2_dim.
    Hypercharge uses Y_num = 6Y.
    """
    if sml.is_boundary_word(u):
        return 0.0
    f = u_to_field.get(u)
    if f is None:
        raise AssertionError("Missing cyclic u in u_to_field map.")
    mult = int(f.su3_dim) * int(f.su2_dim)
    y = float(f.Y_num) / 6.0
    return float(mult) * (y * y)


def _mu6_from_foldm(m: int) -> Dict[str, float]:
    """
    Compute μ_6^(m) on X6 induced by uniform microstates on Ω_m, pushed through Fold_m,
    then projected to the 6-prefix.
    """
    if m < 6:
        raise ValueError("m must be >= 6.")
    outs = pk.cached_foldm_outputs(m)  # length 2^m; outs[k]=Fold_m(k)
    if len(outs) != (1 << m):
        raise AssertionError("Fold_m output length mismatch.")
    counts: Dict[str, int] = {u: 0 for u in sml.all_x6()}
    for w in outs:
        u = w[:6]
        if u not in counts:
            # Should not happen: prefix of an admissible word is admissible.
            raise AssertionError("Prefix u not in X6.")
        counts[u] += 1
    denom = float(1 << m)
    return {u: float(c) / denom for (u, c) in counts.items()}


def _audit_row(m: int, u_to_field: Dict[str, sml.SMField]) -> Row:
    mu6 = _mu6_from_foldm(m)
    X6 = sml.all_x6()
    cyc = [u for u in X6 if not sml.is_boundary_word(u)]

    p_cyc = sum(mu6[u] for u in cyc)
    n_cyc_eff = 21.0 * p_cyc

    w_y_eff = 21.0 * sum(mu6[u] * _b_weight_for_u(u, u_to_field=u_to_field) for u in X6)
    alpha_inv = (3.0 + w_y_eff) * (math.pi**2)
    sin2 = 3.0 / (3.0 + w_y_eff)

    e_alpha = abs(math.log(alpha_inv / float(ALPHAZ_INV_PDG)))
    e_sin2 = abs(math.log(sin2 / float(SIN2_THETAW_PDG)))

    return Row(
        m=m,
        n_states=(1 << m),
        p_cyc=p_cyc,
        n_cyc_eff=n_cyc_eff,
        w_y_eff=w_y_eff,
        alpha_inv=alpha_inv,
        e_alpha=e_alpha,
        sin2=sin2,
        e_sin2=e_sin2,
    )


def main() -> None:
    out_dir = generated_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    u_to_field = _build_x6_to_field_map()

    m_list = [6, 8, 10, 12, 14, 16]
    rows = [_audit_row(m, u_to_field=u_to_field) for m in m_list]

    best_alpha = min(rows, key=lambda r: (r.e_alpha, r.m))
    best_sin2 = min(rows, key=lambda r: (r.e_sin2, r.m))
    best_joint = min(rows, key=lambda r: (r.e_alpha + r.e_sin2, r.m))

    tex_lines: List[str] = []
    for r in rows:
        tex_lines.append(
            rf"{r.m} & {r.n_states} & {r.p_cyc:.6f} & {r.n_cyc_eff:.3f} & {r.w_y_eff:.6f} & "
            rf"{r.alpha_inv:.10f} & {r.e_alpha:.3e} & {r.sin2:.10f} & {r.e_sin2:.3e} \\"
        )
    tex_lines.append(r"\addlinespace")
    tex_lines.append(
        rf"\multicolumn{{9}}{{l}}{{best $e_\alpha$: $m={best_alpha.m}$, $e_\alpha={best_alpha.e_alpha:.3e}$;\ "
        rf"best $e_{{\sin^2}}$: $m={best_sin2.m}$, $e_{{\sin^2}}={best_sin2.e_sin2:.3e}$;\ "
        rf"best joint $e_\alpha+e_{{\sin^2}}$: $m={best_joint.m}$}} \\"
    )
    tex_lines.append(r"\bottomrule")

    out_path = out_dir / "ew_resolution_weighted_match_rows.tex"
    out_path.write_text("\n".join(tex_lines), encoding="utf-8")

    print("Wrote sections/generated/ew_resolution_weighted_match_rows.tex")
    print(f"Best e_alpha: m={best_alpha.m} e_alpha={best_alpha.e_alpha:.6e} W_Y_eff={best_alpha.w_y_eff:.6f}")
    print(f"Best e_sin2:  m={best_sin2.m} e_sin2={best_sin2.e_sin2:.6e} W_Y_eff={best_sin2.w_y_eff:.6f}")
    print(
        f"Best joint:   m={best_joint.m} e_sum={(best_joint.e_alpha + best_joint.e_sin2):.6e} "
        f"W_Y_eff={best_joint.w_y_eff:.6f}"
    )
    print(
        "[protocol_state] Electroweak resolution-weighted match: "
        "for each m in {6,8,10,12,14,16} use the microstate-pushforward kernel on X_m "
        "induced by uniform sampling on Omega_m, push forward to X_6 by pi_{m->6}, "
        "and compute W_Y^eff and the implied alpha^{-1}(mu_Z), sin^2(theta_W)."
    )
    print(
        "[protocol_state] Note: the joint protocol-state selector J_{mu_Z} is reported via the "
        "finite kernel-family sweep table (tempered family); this script is the microstate-pushforward baseline."
    )


if __name__ == "__main__":
    main()

