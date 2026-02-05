#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Window-6 (m=6) C6 rotation-orbit decomposition and Pati–Salam Levi-skeleton audit.

All code is English-only by repository convention.

At m=6, the golden-mean legal language X_6 has size 21 and splits as:
  X_6 = X_6^{cyc} ⊔ X_6^{bdry},   |X_6^{cyc}|=18, |X_6^{bdry}|=3,
where the boundary sector is the endpoint-(1,1) fiber (u_1=u_6=1).

On the cyclic sector, the cyclic-rotation action of C6 preserves admissibility and
induces a rigid orbit multiset with sizes {1,2,3,6,6}. This yields a canonical
15 ⊕ 3 refinement inside X_6^{cyc}, hence a 21=15⊕3⊕3 Levi-type dimension skeleton
(candidate match for su(4) ⊕ su(2) ⊕ su(2)).

We also extract the dyadic (binary-interval) fold at m=6:
  Fold^{bin}_6 : {0,...,63} -> X_6,
and certify the boundary-sector two-sheet lift: each boundary word has exactly two
preimages differing by 34 (=F_9), giving a canonical Z2 "sheet parity".

Outputs:
  - artifacts/export/window6_c6_orbit_patisalam_seed.json
  - sections/generated/eq_window6_c6_orbit_decomposition.tex
  - sections/generated/tab_window6_c6_orbit_decomposition.tex
  - sections/generated/eq_fold6_bin_uplift_delta_set.tex
  - sections/generated/tab_fold6_boundary_sheet_pairs.tex
  - sections/generated/tab_foldbin_boundary_lift_m6_m8.tex
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

from common_paths import export_dir, generated_dir
from common_phi_fold import fib_upto, word_to_str, zeckendorf_digits


def _golden_words(m: int) -> List[List[int]]:
    """All length-m binary words with no adjacent ones (golden mean SFT)."""
    if m < 0:
        raise ValueError("m must be non-negative")
    out: List[List[int]] = []

    def rec(pos: int, prev1: int, acc: List[int]) -> None:
        if pos == m:
            out.append(list(acc))
            return
        acc.append(0)
        rec(pos + 1, 0, acc)
        acc.pop()
        if prev1 == 0:
            acc.append(1)
            rec(pos + 1, 1, acc)
            acc.pop()

    rec(0, 0, [])
    return out


def _is_boundary_word(w: str) -> bool:
    return len(w) == 6 and w[0] == "1" and w[-1] == "1"


def _rot_left(w: str, k: int = 1) -> str:
    n = len(w)
    kk = k % n
    return w[kk:] + w[:kk]


def _hamming_weight(w: str) -> int:
    return w.count("1")


def _V_m(w: str) -> int:
    """Zeckendorf value V_m(w)=sum_{k=1}^m w_k F_{k+1}, with F_1=F_2=1."""
    m = len(w)
    if m <= 0:
        return 0
    fib = fib_upto(m + 2)  # F_1..F_{m+2}
    return sum((1 if ch == "1" else 0) * int(fib[i + 1]) for i, ch in enumerate(w))


def _K_of_m(m: int) -> int:
    """Return K(m) s.t. F_{K+1} <= 2^m-1 < F_{K+2} (F_1=F_2=1)."""
    if m < 0:
        raise ValueError("m must be non-negative")
    target = (1 << m) - 1
    # Fibonacci sequence by index (1-based): F_1=F_2=1.
    f1, f2 = 1, 1
    idx = 2
    while f2 <= target:
        f1, f2 = f2, f1 + f2
        idx += 1
    # Now F_idx = f2 > target and F_{idx-1} <= target.
    # We need K such that K+2 = idx.
    return idx - 2


def _fold_bin_prefix(n: int, *, m: int, K: int) -> str:
    """Fold^{bin}_m(n): Zeckendorf digits prefix of length m (compute digits up to K)."""
    if n < 0:
        raise ValueError("n must be non-negative")
    digits = zeckendorf_digits(n, K)  # digits for weights F_{k+1}, k=1..K
    return word_to_str(digits[:m])


def _tex_tt_set(words: Sequence[str]) -> str:
    # Example: \{\texttt{000001}, \texttt{000010}\}
    inner = ",\\ ".join([f"\\texttt{{{w}}}" for w in words])
    return "\\{" + inner + "\\}"


@dataclass(frozen=True)
class Orbit:
    rep: str
    size: int
    weight: int
    words: List[str]


def _compute_c6_orbits(words: Sequence[str]) -> List[Orbit]:
    """C6-orbits under left rotation (k=1), deterministic ordering."""
    universe: Set[str] = set(words)
    unseen: Set[str] = set(words)
    out: List[Orbit] = []
    while unseen:
        w0 = min(unseen)
        orb = {_rot_left(w0, k) for k in range(6)}
        if not orb.issubset(universe):
            bad = sorted(list(orb - universe))
            raise AssertionError(f"Rotation left orbit escaped universe: {bad}")
        unseen -= orb
        rep = min(orb)
        ws = sorted(list(orb))
        wt = _hamming_weight(rep)
        if any(_hamming_weight(w) != wt for w in ws):
            raise AssertionError("Hamming weight not invariant under rotation (unexpected).")
        out.append(Orbit(rep=rep, size=len(ws), weight=wt, words=ws))
    out.sort(key=lambda o: (o.size, o.rep))
    return out


def write_outputs(
    *,
    json_out: Path,
    tex_eq_orbit: Path,
    tex_tab_orbit: Path,
    tex_eq_delta: Path,
    tex_tab_bdry: Path,
    tex_tab_bdry_stability: Path,
) -> None:
    # --- X6 split (cyclic/boundary) ---
    X6 = sorted([word_to_str(w) for w in _golden_words(6)])
    bdry = sorted([w for w in X6 if _is_boundary_word(w)])
    cyc = sorted([w for w in X6 if w not in set(bdry)])
    if len(X6) != 21 or len(cyc) != 18 or len(bdry) != 3:
        raise AssertionError("Unexpected X6 / cyclic / boundary sizes.")
    if bdry != ["100001", "100101", "101001"]:
        raise AssertionError(f"Unexpected boundary words at m=6: {bdry}")

    # --- C6 orbit decomposition on cyclic sector ---
    orbits = _compute_c6_orbits(cyc)
    orbit_sizes = sorted([o.size for o in orbits])
    if orbit_sizes != [1, 2, 3, 6, 6]:
        raise AssertionError(f"Unexpected orbit size multiset: {orbit_sizes}")

    # --- Fold^{bin}_6 preimages and uplift deltas ---
    m = 6
    K = _K_of_m(m)
    if K != 9:
        raise AssertionError(f"Expected K(6)=9, got {K}")
    pre: Dict[str, List[int]] = {w: [] for w in X6}
    for n in range(0, 1 << m):
        w = _fold_bin_prefix(n, m=m, K=K)
        pre[w].append(n)
    if any(len(v) == 0 for v in pre.values()):
        missing = [w for w, v in pre.items() if len(v) == 0]
        raise AssertionError(f"Some X6 words have empty Fold^bin_6 preimage: {missing}")

    delta_global: Set[int] = set()
    delta_w6_1: Set[int] = set()
    for w, ns in pre.items():
        V = _V_m(w)
        ds = {int(n - V) for n in ns}
        delta_global |= ds
        if w[-1] == "1":
            delta_w6_1 |= ds

    if delta_global != {0, 21, 34, 55}:
        raise AssertionError(f"Unexpected global delta set: {sorted(delta_global)}")
    if delta_w6_1 != {0, 34}:
        raise AssertionError(f"Unexpected delta set for w6=1: {sorted(delta_w6_1)}")

    bdry_pairs: List[Dict[str, object]] = []
    for w in bdry:
        ns = sorted(pre[w])
        V = _V_m(w)
        ds = [n - V for n in ns]
        if len(ns) != 2:
            raise AssertionError(f"Boundary word should have exactly 2 preimages: w={w} pre={ns}")
        if ns[1] - ns[0] != 34:
            raise AssertionError(f"Boundary sheet difference is not 34: w={w} pre={ns}")
        bdry_pairs.append({"w": w, "V6": V, "preimages": ns, "deltas": ds})

    # --- Cross-resolution stability scan (m=6,7,8) for boundary lift patterns (dyadic fold) ---
    bdry_lift_scan: List[Dict[str, object]] = []
    for mm in (6, 7, 8):
        Xm = sorted([word_to_str(w) for w in _golden_words(mm)])
        bdrym = sorted([w for w in Xm if w[0] == "1" and w[-1] == "1"])
        Km = _K_of_m(mm)
        prem: Dict[str, List[int]] = {w: [] for w in Xm}
        for n in range(0, 1 << mm):
            ww = _fold_bin_prefix(n, m=mm, K=Km)
            prem[ww].append(n)
        sizes = [len(prem[w]) for w in bdrym]
        patterns: Dict[str, int] = {}
        for w in bdrym:
            V = _V_m(w)
            ds = sorted({int(n - V) for n in prem[w]})
            key = ",".join(str(x) for x in ds)
            patterns[key] = patterns.get(key, 0) + 1
        bdry_lift_scan.append(
            {
                "m": mm,
                "K_of_m": Km,
                "bdry_count": len(bdrym),
                "preimage_size_min": int(min(sizes)) if sizes else 0,
                "preimage_size_max": int(max(sizes)) if sizes else 0,
                "delta_patterns": dict(sorted(patterns.items())),
            }
        )

    # --- JSON export ---
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(
            {
                "m": 6,
                "X6": X6,
                "X6_cyc": cyc,
                "X6_bdry": bdry,
                "C6_orbits_cyc": [
                    {"rep": o.rep, "size": o.size, "weight": o.weight, "words": o.words} for o in orbits
                ],
                "Fold_bin": {
                    "domain": [0, (1 << m) - 1],
                    "K_of_m": K,
                    "delta_global": sorted(list(delta_global)),
                    "delta_w6_eq_1": sorted(list(delta_w6_1)),
                    "boundary_sheet_pairs": bdry_pairs,
                    "boundary_lift_scan_m6_m8": bdry_lift_scan,
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    # --- LaTeX: orbit decomposition equation ---
    eq_lines: List[str] = []
    eq_lines.append("% AUTO-GENERATED by scripts/exp_window6_c6_orbit_patisalam_seed.py")
    eq_lines.append("\\[")
    eq_lines.append("\\begin{aligned}")
    eq_lines.append(r"X_6^{\mathrm{cyc}}&=\bigsqcup_{j=1}^{5}\mathcal{O}_j,\qquad (|\mathcal{O}_j|)_{j=1}^{5}=(1,2,3,6,6),\\")
    eq_lines.append(r"\dim \mathbb{R}[X_6^{\mathrm{cyc}}]&=18=1\oplus 2\oplus 3\oplus 6\oplus 6\qquad(\text{orbit spans under the }C_6\text{ action}).")
    eq_lines.append("\\end{aligned}")
    eq_lines.append("\\]")
    eq_lines.append("")
    tex_eq_orbit.parent.mkdir(parents=True, exist_ok=True)
    tex_eq_orbit.write_text("\n".join(eq_lines), encoding="utf-8")

    # --- LaTeX: orbit table ---
    tab_lines: List[str] = []
    tab_lines.append("% AUTO-GENERATED by scripts/exp_window6_c6_orbit_patisalam_seed.py")
    tab_lines.append("\\begin{table}[H]")
    tab_lines.append("\\centering")
    tab_lines.append("\\small")
    tab_lines.append("\\setlength{\\tabcolsep}{7pt}")
    tab_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    tab_lines.append(
        "\\caption{C6 rotation orbits of the cyclic sector $X_6^{\\mathrm{cyc}}$ (golden-mean legal words with $u_1u_6=0$). "
        "Orbit elements are shown in lexicographic order.}"
    )
    tab_lines.append("\\label{tab:window6_c6_orbit_decomposition}")
    tab_lines.append("\\begin{tabular}{r l r p{0.62\\linewidth}}")
    tab_lines.append("\\toprule")
    tab_lines.append("$|\\mathcal{O}|$ & representative & $\\mathrm{wt}$ & orbit $\\mathcal{O}$\\\\")
    tab_lines.append("\\midrule")
    for o in orbits:
        tab_lines.append(f"{o.size} & \\texttt{{{o.rep}}} & {o.weight} & ${_tex_tt_set(o.words)}$\\\\")
    tab_lines.append("\\bottomrule")
    tab_lines.append("\\end{tabular}")
    tab_lines.append("\\end{table}")
    tab_lines.append("")
    tex_tab_orbit.parent.mkdir(parents=True, exist_ok=True)
    tex_tab_orbit.write_text("\n".join(tab_lines), encoding="utf-8")

    # --- LaTeX: uplift delta set equation (dyadic fold) ---
    delta_tex = ",\\ ".join(str(x) for x in sorted(delta_global))
    delta_w6_1_tex = ",\\ ".join(str(x) for x in sorted(delta_w6_1))
    eqd_lines: List[str] = []
    eqd_lines.append("% AUTO-GENERATED by scripts/exp_window6_c6_orbit_patisalam_seed.py")
    eqd_lines.append("\\[")
    eqd_lines.append("\\begin{aligned}")
    eqd_lines.append(r"\Delta_6&:=\{\,n-V_6(\mathrm{Fold}^{\mathrm{bin}}_6(n)):\ 0\le n\le 63\,\}=" + f"\\{{{delta_tex}\\}},\\\\")
    eqd_lines.append(r"w_6=1\ &\Longrightarrow\ \{\,n-V_6(w):\ n\in (\mathrm{Fold}^{\mathrm{bin}}_6)^{-1}(w)\,\}=" + f"\\{{{delta_w6_1_tex}\\}}.")
    eqd_lines.append("\\end{aligned}")
    eqd_lines.append("\\]")
    eqd_lines.append("")
    tex_eq_delta.parent.mkdir(parents=True, exist_ok=True)
    tex_eq_delta.write_text("\n".join(eqd_lines), encoding="utf-8")

    # --- LaTeX: boundary sheet pairs table ---
    tab2_lines: List[str] = []
    tab2_lines.append("% AUTO-GENERATED by scripts/exp_window6_c6_orbit_patisalam_seed.py")
    tab2_lines.append("\\begin{table}[H]")
    tab2_lines.append("\\centering")
    tab2_lines.append("\\small")
    tab2_lines.append("\\setlength{\\tabcolsep}{10pt}")
    tab2_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    tab2_lines.append(
        "\\caption{Two-sheet dyadic lift for the window-6 boundary sector $X_6^{\\mathrm{bdry}}$: "
        "each boundary word has exactly two preimages under $\\mathrm{Fold}^{\\mathrm{bin}}_6$, differing by $34=F_9$.}"
    )
    tab2_lines.append("\\label{tab:fold6_boundary_sheet_pairs}")
    tab2_lines.append("\\begin{tabular}{l r l}")
    tab2_lines.append("\\toprule")
    tab2_lines.append("$w\\in X_6^{\\mathrm{bdry}}$ & $V_6(w)$ & $(\\mathrm{Fold}^{\\mathrm{bin}}_6)^{-1}(w)$\\\\")
    tab2_lines.append("\\midrule")
    for row in bdry_pairs:
        w = str(row["w"])
        V = int(row["V6"])
        ns = [int(x) for x in row["preimages"]]  # type: ignore[arg-type]
        tab2_lines.append(f"\\texttt{{{w}}} & {V} & $\\{{{ns[0]},{ns[1]}\\}}$\\\\")
    tab2_lines.append("\\bottomrule")
    tab2_lines.append("\\end{tabular}")
    tab2_lines.append("\\end{table}")
    tab2_lines.append("")
    tex_tab_bdry.parent.mkdir(parents=True, exist_ok=True)
    tex_tab_bdry.write_text("\n".join(tab2_lines), encoding="utf-8")

    # --- LaTeX: boundary lift stability (m=6..8) ---
    stab_lines: List[str] = []
    stab_lines.append("% AUTO-GENERATED by scripts/exp_window6_c6_orbit_patisalam_seed.py")
    stab_lines.append("\\begin{table}[H]")
    stab_lines.append("\\centering")
    stab_lines.append("\\small")
    stab_lines.append("\\setlength{\\tabcolsep}{10pt}")
    stab_lines.append("\\renewcommand{\\arraystretch}{1.10}")
    stab_lines.append(
        "\\caption{Dyadic boundary-sector lift patterns for $\\mathrm{Fold}^{\\mathrm{bin}}_m$ at $m\\in\\{6,7,8\\}$: "
        "for each $m$, all boundary words share the same uplift-delta pattern "
        "$\\{n-V_m(w): n\\in (\\mathrm{Fold}^{\\mathrm{bin}}_m)^{-1}(w)\\}$.}"
    )
    stab_lines.append("\\label{tab:foldbin_boundary_lift_m6_m8}")
    stab_lines.append("\\begin{tabular}{r r r l}")
    stab_lines.append("\\toprule")
    stab_lines.append("$m$ & $|X_m^{\\mathrm{bdry}}|$ & $\\#(\\mathrm{Fold}^{\\mathrm{bin}}_m)^{-1}(w)$ & uplift deltas\\\\")
    stab_lines.append("\\midrule")
    for row in bdry_lift_scan:
        mm = int(row["m"])
        cnt = int(row["bdry_count"])
        smin = int(row["preimage_size_min"])
        smax = int(row["preimage_size_max"])
        size_tex = str(smin) if smin == smax else f"{smin}\\text{{--}}{smax}"
        patterns = row["delta_patterns"]
        if not isinstance(patterns, dict) or len(patterns) == 0:
            raise AssertionError("Missing delta_patterns in boundary lift scan.")
        if len(patterns) == 1:
            k = next(iter(patterns.keys()))
            pat_tex = f"\\{{{k.replace(',',',\\ ')}\\}}"
        else:
            parts: List[str] = []
            for k, v in patterns.items():
                parts.append(f"\\{{{k.replace(',',',\\ ')}\\}}\\times {v}")
            pat_tex = ";\\ ".join(parts)
        stab_lines.append(f"{mm} & {cnt} & {size_tex} & ${pat_tex}$\\\\")
    stab_lines.append("\\bottomrule")
    stab_lines.append("\\end{tabular}")
    stab_lines.append("\\end{table}")
    stab_lines.append("")
    tex_tab_bdry_stability.parent.mkdir(parents=True, exist_ok=True)
    tex_tab_bdry_stability.write_text("\n".join(stab_lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Window-6 C6 orbit + dyadic boundary-sheet audit artifacts.")
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "window6_c6_orbit_patisalam_seed.json"),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--tex-eq-orbit",
        type=str,
        default=str(generated_dir() / "eq_window6_c6_orbit_decomposition.tex"),
        help="Output LaTeX equation fragment path (orbit decomposition).",
    )
    parser.add_argument(
        "--tex-tab-orbit",
        type=str,
        default=str(generated_dir() / "tab_window6_c6_orbit_decomposition.tex"),
        help="Output LaTeX table fragment path (orbit decomposition).",
    )
    parser.add_argument(
        "--tex-eq-delta",
        type=str,
        default=str(generated_dir() / "eq_fold6_bin_uplift_delta_set.tex"),
        help="Output LaTeX equation fragment path (dyadic uplift delta set).",
    )
    parser.add_argument(
        "--tex-tab-bdry",
        type=str,
        default=str(generated_dir() / "tab_fold6_boundary_sheet_pairs.tex"),
        help="Output LaTeX table fragment path (boundary sheet pairs).",
    )
    parser.add_argument(
        "--tex-tab-bdry-stability",
        type=str,
        default=str(generated_dir() / "tab_foldbin_boundary_lift_m6_m8.tex"),
        help="Output LaTeX table fragment path (boundary lift stability scan for m=6..8).",
    )
    args = parser.parse_args()

    write_outputs(
        json_out=Path(args.json_out),
        tex_eq_orbit=Path(args.tex_eq_orbit),
        tex_tab_orbit=Path(args.tex_tab_orbit),
        tex_eq_delta=Path(args.tex_eq_delta),
        tex_tab_bdry=Path(args.tex_tab_bdry),
        tex_tab_bdry_stability=Path(args.tex_tab_bdry_stability),
    )
    print(f"[window6-c6-orbit] wrote {args.json_out}", flush=True)
    print(f"[window6-c6-orbit] wrote {args.tex_eq_orbit}", flush=True)
    print(f"[window6-c6-orbit] wrote {args.tex_tab_orbit}", flush=True)
    print(f"[window6-c6-orbit] wrote {args.tex_eq_delta}", flush=True)
    print(f"[window6-c6-orbit] wrote {args.tex_tab_bdry}", flush=True)
    print(f"[window6-c6-orbit] wrote {args.tex_tab_bdry_stability}", flush=True)
    print("[window6-c6-orbit] done", flush=True)


if __name__ == "__main__":
    main()

