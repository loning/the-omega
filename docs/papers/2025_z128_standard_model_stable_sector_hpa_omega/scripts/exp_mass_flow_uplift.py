# -*- coding: utf-8 -*-
"""
Mass flow under window uplift: CAP representative vs free-energy representative.

This script implements the definitions in Appendix~51 (mass flow under uplift):
  - Lift fibers Ext_m(u) under the prefix projection pi_{m->6}.
  - A deterministic CAP representative inside each fiber.
  - A deterministic free-energy representative (entropy-aware) inside each fiber.
  - The pooled effective depth r_hat_sigma(u;m) relative to the electron reference.

Outputs (LaTeX fragments):
  - sections/generated/mass_flow_uplift_rows.tex
  - sections/generated/mass_flow_uplift_summary.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import exp_foldm_stats as foldm
import exp_sm_labeling_solver as sml
import exp_xm_enumeration as xm
from common_tex import write_lines


def fib_weights(L: int) -> List[int]:
    """
    Fibonacci weights [F2, F3, ..., F_{L+1}] with F1=F2=1.
    """
    if L < 0:
        raise ValueError("L must be nonnegative.")
    if L == 0:
        return []
    if L == 1:
        return [1]
    w = [1, 2]
    while len(w) < L:
        w.append(w[-1] + w[-2])
    return w


def zeckendorf_value_word(word: str) -> int:
    wts = fib_weights(len(word))
    return sum(int(bit) * wts[i] for i, bit in enumerate(word))


def free_suffix_index(u: str, w: str) -> int:
    """
    rho(w) from Definition def:free_suffix_index (Appendix functorial refinement).
    """
    if len(u) != 6:
        raise ValueError("u must be a 6-bit base type.")
    if not w.startswith(u):
        raise ValueError("w must have prefix u.")

    suffix = w[6:]  # length L=m-6
    if u[-1] == "0":
        free = suffix
    else:
        if suffix and suffix[0] != "0":
            raise AssertionError("Expected forced leading 0 after a trailing-1 prefix bit.")
        free = suffix[1:] if suffix else ""
    return zeckendorf_value_word(free)


def rho_suffix_depth(rho: int) -> int:
    """
    r_suf(rho) = min{ ell >= 0 : rho < F_{ell+2} } with F1=F2=1.
    """
    if rho < 0:
        raise ValueError("rho must be nonnegative.")
    ell = 0
    a, b = 1, 1  # F1, F2 (b is the current F_{ell+2} when ell=0)
    while rho >= b:
        ell += 1
        a, b = b, a + b
    return ell


@dataclass(frozen=True)
class Rep:
    w: str
    g: int
    rho: int
    r_suf: int
    wt: int


def cap_key(rep: Rep) -> Tuple[int, int, int, int, str]:
    return (rep.g, rep.r_suf, rep.wt, rep.rho, rep.w)


def select_cap_representative(reps: List[Rep]) -> Rep:
    return min(reps, key=cap_key)


def free_energy_value(rep: Rep) -> float:
    # E = g + r_suf + |w|_1; S = log g; F = E - S
    return float(rep.g + rep.r_suf + rep.wt) - math.log(float(rep.g))


def select_free_energy_representative(reps: List[Rep]) -> Rep:
    # Tie-break by the same CAP key to keep selection fully deterministic.
    return min(reps, key=lambda r: (free_energy_value(r), cap_key(r)))


def parse_label_map_from_rows(rows: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in rows:
        cols = [c.strip() for c in line.split("&")]
        if len(cols) < 7:
            continue
        w_col = cols[0]
        if not w_col.startswith("\\texttt{") or "}" not in w_col:
            continue
        u = w_col[len("\\texttt{") : w_col.index("}")]
        label = cols[6].strip()
        out[u] = label
    if len(out) != 21:
        raise AssertionError(f"Expected 21 base labels, got {len(out)}.")
    return out


def find_electron_base(label_of: Dict[str, str]) -> str:
    for u, lab in label_of.items():
        if "e_R^{(1)}" in lab:
            return u
    raise AssertionError("Could not locate electron base type for e_R^{(1)} in labeling map.")


def build_lifts_of(Xm: Iterable[str]) -> Dict[str, List[str]]:
    lifts_of: Dict[str, List[str]] = defaultdict(list)
    for w in Xm:
        lifts_of[w[:6]].append(w)
    return lifts_of


def effective_depth(
    u: str,
    V_u: int,
    u_e: str,
    V_e: int,
    rep_u: Rep,
    rep_e: Rep,
) -> int:
    # Eq. (mass flow r_hat definition) in Appendix 51.
    return (
        2 * (V_u - V_e)
        + 5 * (rep_u.g - rep_e.g)
        + (rep_u.wt - rep_e.wt)
        + 2 * (rep_u.r_suf - rep_e.r_suf)
    )


def main() -> None:
    m_list = [6, 8, 10, 12, 14, 16]

    base_rows = sml.generate_rows()
    label_of = parse_label_map_from_rows(base_rows)
    u_e = find_electron_base(label_of)
    V_e = sml.zeckendorf_value(u_e)

    X6 = sml.all_x6()
    cyc = [u for u in X6 if not sml.is_boundary_word(u)]
    # Present in the same intrinsic order used elsewhere (r_*(w), V(w), w).
    cyc_sorted = sorted(cyc, key=lambda w: sml.stable_type_sort_key(w))

    out_rows: List[str] = []
    summary_rows: List[str] = []

    for m in m_list:
        Xm = xm.all_xm(m)
        gm = foldm.cached_degeneracy_map(m)
        if set(gm.keys()) != set(Xm):
            raise AssertionError(f"Fold_m image mismatch at m={m}.")

        lifts_of = build_lifts_of(Xm)

        reps_cap: Dict[str, Rep] = {}
        reps_fe: Dict[str, Rep] = {}

        for u in cyc_sorted:
            lifts = lifts_of.get(u, [])
            if not lifts:
                raise AssertionError(f"Missing lift fiber Ext_{m}({u}).")

            reps: List[Rep] = []
            for w in lifts:
                g = gm[w]
                rho = free_suffix_index(u=u, w=w)
                r_suf = rho_suffix_depth(rho)
                wt = w.count("1")
                reps.append(Rep(w=w, g=g, rho=rho, r_suf=r_suf, wt=wt))

            rep_cap = select_cap_representative(reps)
            rep_fe = select_free_energy_representative(reps)
            reps_cap[u] = rep_cap
            reps_fe[u] = rep_fe

        if u_e not in reps_cap or u_e not in reps_fe:
            raise AssertionError("Electron base type missing from cyclic set.")
        rep_e_cap = reps_cap[u_e]
        rep_e_fe = reps_fe[u_e]

        # Summary metrics for this m.
        changed = 0
        max_abs = 0
        sum_abs = 0
        for u in cyc_sorted:
            V_u = sml.zeckendorf_value(u)
            r_cap = effective_depth(u=u, V_u=V_u, u_e=u_e, V_e=V_e, rep_u=reps_cap[u], rep_e=rep_e_cap)
            r_fe = effective_depth(u=u, V_u=V_u, u_e=u_e, V_e=V_e, rep_u=reps_fe[u], rep_e=rep_e_fe)
            if r_cap != r_fe or reps_cap[u].w != reps_fe[u].w:
                changed += 1
            d = abs(r_fe - r_cap)
            sum_abs += d
            if d > max_abs:
                max_abs = d
        mean_abs = float(sum_abs) / float(len(cyc_sorted)) if cyc_sorted else 0.0
        summary_rows.append(f"{m} & {changed} & {max_abs} & {mean_abs:.3f} \\\\")

        # Emit per-(m,u) table rows.
        for u in cyc_sorted:
            lab = label_of[u]
            V_u = sml.zeckendorf_value(u)

            rep_cap = reps_cap[u]
            rep_fe = reps_fe[u]

            r_cap = effective_depth(u=u, V_u=V_u, u_e=u_e, V_e=V_e, rep_u=rep_cap, rep_e=rep_e_cap)
            r_fe = effective_depth(u=u, V_u=V_u, u_e=u_e, V_e=V_e, rep_u=rep_fe, rep_e=rep_e_fe)

            # For compactness, report (g_m, r_suf) for the CAP representative.
            out_rows.append(
                f"{m} & \\texttt{{{u}}} & {lab} & "
                f"{r_cap} & \\texttt{{{rep_cap.w}}} & {rep_cap.g} & {rep_cap.r_suf} & "
                f"{r_fe} & \\texttt{{{rep_fe.w}}} \\\\"
            )

    out_rows.append("\\bottomrule")
    summary_rows.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    write_lines(out_dir / "mass_flow_uplift_rows.tex", out_rows)
    write_lines(out_dir / "mass_flow_uplift_summary.tex", summary_rows)
    print("Wrote sections/generated/mass_flow_uplift_rows.tex")
    print("Wrote sections/generated/mass_flow_uplift_summary.tex")


if __name__ == "__main__":
    main()

