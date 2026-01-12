#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resolution-weighted electroweak match audit (family sweep).

Motivation
----------
The basic resolution-weighted audit (exp_ew_resolution_weighted_match.py) fixes a
single protocol-native measure by pushing forward the uniform microstate measure
on Ω_m through Fold_m, then projecting to X6 by prefix.

Empirically, W_Y_eff(m) converges quickly to a limiting value > 10, while PDG
targets correspond to an implied W_Y_target ≈ 9.97 under the same normalization.
Hence "just increase m" cannot drive mismatch to zero; one must refine the
measurement kernel / weighting rule (still fully discrete and auditable).

This script sweeps a *finite* family of tempered weights on X_m:

  μ_m^(t)(w) ∝ g_m(w)^t

where g_m(w)=|Fold_m^{-1}(w)| is the folding degeneracy (protocol-native),
and t is chosen from a small bounded rational grid (default: t ∈ {0,1/4,1/2,3/4,1}).

We then project to X6 via the prefix map and compute:
  W_Y_eff(m,t), alpha^{-1}(mu_Z; m,t), sin^2(theta_W; m,t), and log-mismatches.

Outputs
-------
- sections/generated/ew_resolution_weighted_match_family_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Iterable, List, Tuple

from common_constants import ALPHAZ_INV_PDG, SIN2_THETAW_PDG
from common_paths import generated_dir

import exp_sm_labeling_solver as sml
import protocol_kernel as pk
import protocol_state_selection as psel


@dataclass(frozen=True)
class Cand:
    m: int
    t: Fraction
    W: float
    alpha_inv: float
    sin2: float
    e_alpha: float
    e_sin2: float


def _build_x6_to_field_map() -> Dict[str, sml.SMField]:
    X6 = sml.all_x6()
    cyc = [w for w in X6 if not sml.is_boundary_word(w)]
    cyc_sorted = sorted(cyc, key=lambda w: sml.stable_type_sort_key(w))
    fields_sorted = sorted(sml.fermion_targets(), key=lambda f: f.complexity_key())
    if len(cyc_sorted) != len(fields_sorted):
        raise AssertionError("Expected 18 cyclic base types and 18 fermion targets.")
    return {u: f for (u, f) in zip(cyc_sorted, fields_sorted)}


def _b_weight_for_u(u: str, u_to_field: Dict[str, sml.SMField]) -> float:
    if sml.is_boundary_word(u):
        return 0.0
    f = u_to_field.get(u)
    if f is None:
        raise AssertionError("Missing cyclic u in field map.")
    mult = int(f.su3_dim) * int(f.su2_dim)
    y = float(f.Y_num) / 6.0
    return float(mult) * (y * y)


def _mu6_from_tempered_degeneracy(m: int, t: Fraction) -> Dict[str, float]:
    """
    Define μ_m^(t)(w) ∝ g_m(w)^t over w∈X_m, then project to X6 by prefix.
    This is a finite family of kernel choices (dictionary/audit), not a theorem-level object.
    """
    if m < 6:
        raise ValueError("m must be >= 6.")
    Xm = pk.all_xm(m)
    gm = pk.cached_degeneracy_map(m)
    if set(gm.keys()) != set(Xm):
        raise AssertionError("Degeneracy map domain mismatch.")

    # Work in log space for numerical stability:
    # weight(w)=exp(t*log(gm[w])).
    t_float = float(t)
    logs = [t_float * math.log(float(gm[w])) for w in Xm]
    max_log = max(logs) if logs else 0.0
    weights = [math.exp(lv - max_log) for lv in logs]
    Z = sum(weights)
    if not (Z > 0.0):
        raise AssertionError("Normalization failed.")

    mu6 = {u: 0.0 for u in sml.all_x6()}
    for w, wt in zip(Xm, weights):
        u = w[:6]
        if u not in mu6:
            raise AssertionError("Prefix not in X6.")
        mu6[u] += wt / Z
    # Sanity: sum to 1
    s = sum(mu6.values())
    if abs(s - 1.0) > 1e-12:
        # tolerate very small floating error
        raise AssertionError(f"mu6 sum != 1 (got {s}).")
    return mu6


def _candidate(m: int, t: Fraction, u_to_field: Dict[str, sml.SMField]) -> Cand:
    mu6 = _mu6_from_tempered_degeneracy(m, t)
    X6 = sml.all_x6()
    W = 21.0 * sum(mu6[u] * _b_weight_for_u(u, u_to_field=u_to_field) for u in X6)
    alpha_inv = (3.0 + W) * (math.pi**2)
    sin2 = 3.0 / (3.0 + W)
    e_alpha = abs(math.log(alpha_inv / float(ALPHAZ_INV_PDG)))
    e_sin2 = abs(math.log(sin2 / float(SIN2_THETAW_PDG)))
    return Cand(m=m, t=t, W=W, alpha_inv=alpha_inv, sin2=sin2, e_alpha=e_alpha, e_sin2=e_sin2)


def _t_grid() -> List[Fraction]:
    # Small bounded rational family (can be expanded if desired).
    return [Fraction(0, 1), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4), Fraction(1, 1)]


def _t_complexity_key(t: Fraction) -> Tuple[int, int]:
    # Lower denominator/numerator preferred as a minimal-complexity tie-break.
    return (t.denominator, abs(t.numerator))


def main() -> None:
    out_dir = generated_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    u_to_field = _build_x6_to_field_map()

    m_list = [6, 8, 10, 12, 14, 16]
    ts = _t_grid()

    cands: List[Cand] = []
    for m in m_list:
        for t in ts:
            cands.append(_candidate(m=m, t=t, u_to_field=u_to_field))

    # Primary objective: minimize joint mismatch e_alpha + e_sin2.
    # Tie-break: smaller t complexity, then smaller m, then smaller e_alpha, then e_sin2.
    best = min(
        cands,
        key=lambda c: (
            c.e_alpha + c.e_sin2,
            _t_complexity_key(c.t),
            c.m,
            c.e_alpha,
            c.e_sin2,
        ),
    )

    # Joint protocol-state selection (theory-first): read the selected (m,t) from protocol_state_selection.
    sel = psel.load_selected_state("mu_Z")
    sel_t = Fraction(str(sel.kernel.t))
    sel_cand = next((x for x in cands if x.m == int(sel.m) and x.t == sel_t), None)

    # Emit a compact table: for each m, list all t in the fixed grid.
    lines: List[str] = []
    for m in m_list:
        for t in ts:
            c = next(x for x in cands if x.m == m and x.t == t)
            t_tex = rf"{t.numerator}/{t.denominator}" if t.denominator != 1 else rf"{t.numerator}"
            lines.append(
                rf"{m} & ${t_tex}$ & {c.W:.6f} & {c.alpha_inv:.10f} & {c.e_alpha:.3e} & {c.sin2:.10f} & {c.e_sin2:.3e} \\"
            )
        lines.append(r"\addlinespace")
    lines.append(
        rf"\multicolumn{{7}}{{l}}{{best (min $e_\alpha+e_{{\sin^2}}$): $m={best.m}$, $t={best.t}$, "
        rf"$W={best.W:.6f}$, $e_\alpha={best.e_alpha:.3e}$, $e_{{\sin^2}}={best.e_sin2:.3e}$}} \\"
    )
    if sel_cand is not None:
        lines.append(
            rf"\multicolumn{{7}}{{l}}{{selected by joint key $J_{{\mu_Z}}$ (theory-first): $m={sel_cand.m}$, $t={sel_cand.t}$, "
            rf"$W={sel_cand.W:.6f}$, $e_\alpha={sel_cand.e_alpha:.3e}$, $e_{{\sin^2}}={sel_cand.e_sin2:.3e}$}} \\"
        )
    lines.append(r"\bottomrule")

    out_path = out_dir / "ew_resolution_weighted_match_family_rows.tex"
    out_path.write_text("\n".join(lines), encoding="utf-8")

    print("Wrote sections/generated/ew_resolution_weighted_match_family_rows.tex")
    print(
        f"Best (joint): m={best.m} t={best.t} W={best.W:.6f} "
        f"e_alpha={best.e_alpha:.6e} e_sin2={best.e_sin2:.6e}"
    )
    if sel_cand is not None:
        print(
            f"Selected by J_muZ: m={sel_cand.m} t={sel_cand.t} W={sel_cand.W:.6f} "
            f"e_alpha={sel_cand.e_alpha:.6e} e_sin2={sel_cand.e_sin2:.6e}"
        )
    print(
        "[protocol_state] Electroweak kernel-family sweep: "
        "scan a finite tempered family K_t on X_m with t in a fixed rational grid; "
        "objective is joint mismatch (e_alpha+e_sin2) with deterministic tie-break "
        "preferring lower t-complexity, then smaller m."
    )


if __name__ == "__main__":
    main()

