# -*- coding: utf-8 -*-
"""
Minimal matching layer for the mass-spectrum closure.

We work in the resolution coordinate r(mu)=log(mu/m_e)/log(phi), and the closure
provides an integer depth r_hat for each field (or a chosen anchor integer for
bosonic thresholds). The data mismatch is:
  Delta r := r_ref - r_hat,
equivalently mu_ref/mu_pred = phi^{Delta r}.

This script encodes a *minimal* matching-layer hypothesis:
  - Matching shifts Delta r are approximately quantized on a 1/4 lattice:
        Delta r ≈ k/4,  k in Z,
    motivated by the frequent appearance of square-root normalizations and
    two-step composition effects (half-depth + half-depth -> quarter steps)
    in finite-resolution protocol weights.

We compute, for each field in the mass-spectrum table:
  - Delta r
  - nearest k/4
  - residual Delta r - k/4
  - implied quantized matching factor phi^{k/4}

Outputs (LaTeX fragments):
  - sections/generated/mass_matching_layer_rows.tex
  - sections/generated/mass_matching_layer_summary_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import exp_mass_spectrum as ms
import exp_sm_labeling_solver as sml


PHI = (1.0 + math.sqrt(5.0)) / 2.0
LOG_PHI = math.log(PHI)


def r_of_mu(mu: float, mu0: float) -> float:
    return math.log(mu / mu0) / LOG_PHI


def build_word_for_field() -> Dict[Tuple[int, str], str]:
    return ms.build_word_for_field()


def r_star_of_word(w: str, n_hilbert: int = 3) -> int:
    return ms.r_star_of_word(w, n_hilbert=n_hilbert)


def main() -> None:
    # Reference masses (GeV), matching exp_mass_spectrum.py.
    m_e = 5.1099895e-4
    ref: Dict[str, float] = {
        "e": m_e,
        "mu": 1.0565838e-1,
        "tau": 1.77686,
        "u": 2.16e-3,
        "d": 4.67e-3,
        "s": 9.30e-2,
        "c": 1.27,
        "b": 4.18,
        "t": 172.76,
        "W": 80.377,
        "Z": 91.1876,
        "H": 125.25,
    }

    word_for = build_word_for_field()

    # Electron reference: e_R^(1)
    w_e = word_for[(1, "e_R")]
    r_star_e = r_star_of_word(w_e)
    g_e = sml.degeneracy_g(w_e)
    wt_e = w_e.count("1")

    kappa = 2  # m/n = 2 for (m,n)=(6,3)

    def r_hat_from_word(w: str) -> int:
        g_w = sml.degeneracy_g(w)
        wt_w = w.count("1")
        return kappa * (r_star_of_word(w) - r_star_e) + (wt_w - wt_e) + (g_e - g_w)

    def nearest_k_over_q(x: float, q: int) -> Tuple[int, float]:
        k = int(round(x * float(q)))
        return k, float(k) / float(q)

    q = 4  # quarter-step matching lattice

    # Fields and their corresponding r_hat sources.
    entries: List[Tuple[str, str, Optional[Tuple[int, str]], Optional[int]]] = [
        ("$e$", "e", (1, "e_R"), None),
        ("$\\mu$", "mu", (2, "e_R"), None),
        ("$\\tau$", "tau", (3, "e_R"), None),
        ("$u$", "u", (1, "u_R"), None),
        ("$d$", "d", (1, "d_R"), None),
        ("$s$", "s", (2, "d_R"), None),
        ("$c$", "c", (2, "u_R"), None),
        ("$b$", "b", (3, "d_R"), None),
        ("$t$", "t", (3, "u_R"), None),
        ("$W$", "W", None, 25),
        ("$Z$", "Z", None, 25),
        ("$H$", "H", None, 26),
    ]

    rows: List[str] = []
    abs_resids: List[float] = []
    for field_tex, key, fkey, rh_override in entries:
        mu_ref = ref[key]
        r_ref = r_of_mu(mu_ref, m_e)
        if rh_override is not None:
            r_hat = rh_override
        else:
            if fkey is None:
                raise AssertionError("Expected either a fermion key or an override r_hat.")
            w = word_for[fkey]
            r_hat = r_hat_from_word(w)
        delta_r = r_ref - float(r_hat)
        k_int, dq = nearest_k_over_q(delta_r, q=q)
        resid = delta_r - dq
        abs_resids.append(abs(resid))
        # Quantized matching factor for mu_ref/mu_pred.
        match_factor = PHI ** dq
        rows.append(
            f"{field_tex} & {r_ref:.3f} & {r_hat:d} & {delta_r:+.3f} & ${k_int}/{q}$ & {resid:+.3f} & ${match_factor:.6g}$ \\\\"
        )

    rows.append("\\bottomrule")

    # Summary statistics for the residual size |Delta r - k/4|.
    abs_resids_sorted = sorted(abs_resids)
    n = len(abs_resids_sorted)
    if n == 0:
        raise AssertionError("No matching-layer entries produced.")
    if n % 2 == 1:
        median = abs_resids_sorted[n // 2]
    else:
        median = 0.5 * (abs_resids_sorted[n // 2 - 1] + abs_resids_sorted[n // 2])
    p90_idx = max(0, min(n - 1, int(math.ceil(0.90 * n)) - 1))
    p90 = abs_resids_sorted[p90_idx]
    max_abs = abs_resids_sorted[-1]
    n_le_001 = sum(1 for x in abs_resids_sorted if x <= 0.01 + 1e-12)
    n_le_005 = sum(1 for x in abs_resids_sorted if x <= 0.05 + 1e-12)

    summary_rows: List[str] = []
    summary_rows.append(f"entries & {n:d} \\\\")
    summary_rows.append(rf"median $|\Delta r-k/4|$ & {median:.3f} \\")
    summary_rows.append(rf"p90 $|\Delta r-k/4|$ & {p90:.3f} \\")
    summary_rows.append(rf"max $|\Delta r-k/4|$ & {max_abs:.3f} \\")
    summary_rows.append(rf"$N_{{|\cdot|\le 0.01}}$ & {n_le_001:d} \\")
    summary_rows.append(rf"$N_{{|\cdot|\le 0.05}}$ & {n_le_005:d} \\")
    summary_rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "mass_matching_layer_rows.tex").write_text("\n".join(rows), encoding="utf-8")
    print("Wrote sections/generated/mass_matching_layer_rows.tex")
    (out_dir / "mass_matching_layer_summary_rows.tex").write_text(
        "\n".join(summary_rows), encoding="utf-8"
    )
    print("Wrote sections/generated/mass_matching_layer_summary_rows.tex")


if __name__ == "__main__":
    main()


