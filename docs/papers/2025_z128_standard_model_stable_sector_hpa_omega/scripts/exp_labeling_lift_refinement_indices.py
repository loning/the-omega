# -*- coding: utf-8 -*-
"""
Canonical refinement indices for functorial label lifts under window uplift.

We work with the admissible sets X_m (binary words with no consecutive ones) and
the truncation projection:
  pi_{m->6}: X_m -> X_6,   pi_{m->6}(w_1...w_m) = w_1...w_6.

Given a base type u in X_6, define its lift fiber:
  Ext_m(u) := { w in X_m : pi_{m->6}(w) = u }.

To support "refinement beyond the coarse lift" L_m := L_SM ∘ pi_{m->6}, we
introduce a deterministic index rho that enumerates lifts at fixed m using only
protocol-internal, Fibonacci/Zeckendorf structure.

Let L := m-6 and write w = u || s where s is the suffix of length L.
If u_6 = 0, the suffix s is any admissible word in X_L.
If u_6 = 1, the first suffix bit is forced 0, so s = 0 || t with t in X_{L-1}.

Definition (free suffix index rho):
  - If u_6 = 0:   rho(w) := V_Z(s) where V_Z uses Fibonacci weights [F2..F_{L+1}].
  - If u_6 = 1:   rho(w) := V_Z(t) where t is the "free" suffix (drop the forced 0),
                  using Fibonacci weights [F2..F_{L}].

This yields contiguous index ranges:
  rho in {0, ..., F_{m-4}-1} if u_6 = 0,
  rho in {0, ..., F_{m-5}-1} if u_6 = 1.

We also record the boundary subset of lifts under the pi-channel wrap-around
defect predicate (w_1 = w_m = 1), expressed as the set of rho values that yield
boundary lifts for each base type u.

Outputs (LaTeX fragments):
  - sections/generated/label_lift_suffix_catalog_rows.tex
  - sections/generated/label_lift_boundary_rho_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import exp_sm_labeling_solver as sml
import exp_xm_enumeration as xm
from common_tex import write_lines


def fib_weights(L: int) -> List[int]:
    """
    Return the Fibonacci weights [F2, F3, ..., F_{L+1}] with F1=F2=1.

    Examples:
      L=0 -> []
      L=1 -> [1]
      L=2 -> [1,2]
      L=3 -> [1,2,3]
      L=4 -> [1,2,3,5]
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


def _set_tex(xs: List[int]) -> str:
    if not xs:
        return r"$\varnothing$"
    inner = ", ".join(str(x) for x in xs)
    return rf"$\{{{inner}\}}$"


def parse_label_map_from_rows(rows: List[str]) -> Dict[str, str]:
    """
    Build mapping u (as plain 6-bit string) -> label TeX (e.g. $Q_L^{(1)}$).
    """
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


def suffix_catalog_rows(m_list: List[int]) -> List[str]:
    """
    Produce a universal catalog of admissible suffixes and their free-index rho,
    for both u_6=0 and u_6=1 at selected m.
    """
    rows: List[str] = []

    for m in m_list:
        if m < 6:
            raise ValueError("m must be >= 6.")
        L = m - 6

        # Case u_6 = 0: full suffix s is any admissible word in X_L.
        s_list = xm.all_xm(L) if L > 0 else [""]
        cat0: List[Tuple[int, str, str, int]] = []
        for s in s_list:
            t = s  # free suffix equals full suffix
            rho = zeckendorf_value_word(t)
            last = int(s[-1]) if s else 0
            cat0.append((rho, s, t, last))
        cat0.sort(key=lambda x: (x[0], x[1]))
        for rho, s, t, last in cat0:
            rows.append(f"{m} & 0 & \\texttt{{{s}}} & \\texttt{{{t}}} & {rho} & {last} \\\\")

        # Case u_6 = 1: first extension bit is forced 0; full suffix is s=0||t.
        if L == 0:
            free_list = [""]
        else:
            free_list = xm.all_xm(L - 1) if (L - 1) > 0 else [""]
        cat1: List[Tuple[int, str, str, int]] = []
        for t in free_list:
            s = ("0" + t) if L > 0 else ""
            rho = zeckendorf_value_word(t)
            last = int(s[-1]) if s else 0
            cat1.append((rho, s, t, last))
        cat1.sort(key=lambda x: (x[0], x[1]))
        for rho, s, t, last in cat1:
            rows.append(f"{m} & 1 & \\texttt{{{s}}} & \\texttt{{{t}}} & {rho} & {last} \\\\")

    rows.append("\\bottomrule")
    return rows


def boundary_rho_rows(m_list: List[int]) -> List[str]:
    """
    For each base type u in X6, report the boundary-lift rho subsets at selected m.
    """
    base_rows = sml.generate_rows()
    label_of = parse_label_map_from_rows(base_rows)

    X6 = sml.all_x6()
    if len(X6) != 21:
        raise AssertionError("Expected |X6|=21.")

    # Precompute boundary-rho sets by brute enumeration (small at the m used here).
    bdry_rhos: Dict[Tuple[str, int], List[int]] = {}
    for m in m_list:
        Xm = xm.all_xm(m)
        for u in X6:
            u6 = u[-1]
            rhos: List[int] = []
            for w in Xm:
                if w[:6] != u:
                    continue
                if not xm.is_boundary_word(w):
                    continue
                suffix = w[6:]  # length L
                if u6 == "0":
                    free = suffix
                else:
                    if not suffix or suffix[0] != "0":
                        raise AssertionError("Expected forced leading 0 after a trailing-1 prefix bit.")
                    free = suffix[1:]
                rhos.append(zeckendorf_value_word(free))
            bdry_rhos[(u, m)] = sorted(set(rhos))

    def sort_key(u: str) -> Tuple[int, str]:
        return (sml.zeckendorf_value(u), u)

    rows: List[str] = []
    for u in sorted(X6, key=sort_key):
        lab = label_of[u]
        u1 = int(u[0])
        u6 = int(u[-1])
        bcols = [_set_tex(bdry_rhos[(u, m)]) for m in m_list]
        # Expect exactly two m values for the intended table layout.
        if len(bcols) != 2:
            raise AssertionError("boundary_rho_rows expects exactly two m values.")
        rows.append(f"\\texttt{{{u}}} & {lab} & {u1} & {u6} & {bcols[0]} & {bcols[1]} \\\\")

    rows.append("\\bottomrule")
    return rows


def main() -> None:
    # Balanced-coupling uplifts (m=2n) beyond the base (m=6) used elsewhere in the paper.
    m_list = [8, 10]

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    write_lines(out_dir / "label_lift_suffix_catalog_rows.tex", suffix_catalog_rows(m_list))
    print("Wrote sections/generated/label_lift_suffix_catalog_rows.tex")

    write_lines(out_dir / "label_lift_boundary_rho_rows.tex", boundary_rho_rows(m_list))
    print("Wrote sections/generated/label_lift_boundary_rho_rows.tex")


if __name__ == "__main__":
    main()


