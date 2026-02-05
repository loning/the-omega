#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fold6 (m=6) B3/C3 Lie-seed dictionary from the rigid 18 ⊕ 3 split.

This script is intended as a *reproducible audit artifact* for the manuscript narrative:

  |X_6| = 21 with the rigid split
      X_6 = X_6^{cyc} ⊔ X_6^{bdry},  |X_6^{cyc}|=18, |X_6^{bdry}|=3,
  and the additional "two-length fingerprint" inside X_6^{cyc}:
      # { w in X_6^{cyc} : wt(w)=1 } = 6,
      # { w in X_6^{cyc} : wt(w)≠1 } = 12.

The count 3 + 18 matches the Cartan/root-space decomposition of a rank-3 simple Lie algebra
with 18 roots (dim = 21), hence the only ADE/BC candidate types are B3 or C3.

What this script outputs:
- a compact LaTeX equation fragment with the verified counts and the 6+12 split;
- a deterministic *dictionary* mapping the 18 cyclic Fold6 types to a concrete
  coordinate model of the B3 or C3 root system (and hence inducing a Weyl-group action).

Important:
- The B3 vs C3 choice is a *normalization choice* (long/short swap); both are exported.
- The dictionary is deterministic, but it is still a choice of identification (a gauge);
  the rigid content is the forced type-class (B3/C3) and the 6+12 split.

Only the Python standard library is used (imports from sibling scripts are also stdlib-only).
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import exp_sm_labeling_solver as sml
from common_paths import generated_dir


RootVec = Tuple[int, int, int]


def _hamming_weight(w: str) -> int:
    return w.count("1")


def _roots_B3() -> Tuple[List[RootVec], List[RootVec]]:
    """
    Return (short_roots, long_roots) for B3 in the standard e_i basis:
      short: ±e_i  (6)
      long:  ±e_i ± e_j (12)
    """
    short: List[RootVec] = [
        (+1, 0, 0),
        (-1, 0, 0),
        (0, +1, 0),
        (0, -1, 0),
        (0, 0, +1),
        (0, 0, -1),
    ]
    long: List[RootVec] = [
        (+1, +1, 0),
        (+1, -1, 0),
        (-1, +1, 0),
        (-1, -1, 0),
        (+1, 0, +1),
        (+1, 0, -1),
        (-1, 0, +1),
        (-1, 0, -1),
        (0, +1, +1),
        (0, +1, -1),
        (0, -1, +1),
        (0, -1, -1),
    ]
    return short, long


def _roots_C3() -> Tuple[List[RootVec], List[RootVec]]:
    """
    Return (short_roots, long_roots) for C3 in the standard e_i basis:
      short: ±e_i ± e_j (12)
      long:  ±2 e_i (6)
    """
    # In this coordinate model, the 12 short roots coincide with B3's long roots.
    short12 = _roots_B3()[1]
    long6: List[RootVec] = [
        (+2, 0, 0),
        (-2, 0, 0),
        (0, +2, 0),
        (0, -2, 0),
        (0, 0, +2),
        (0, 0, -2),
    ]
    return short12, long6


def _word_axis_for_weight1(w: str) -> int:
    """
    Assign one of three Cartan axes to a weight=1 word, by its 1-position.

    We use the Zeckendorf/Fibonacci-weighted ordering (z7..z2) implicit in the papers.
    The 6-bit word positions are:
      w = (z7 z6 z5 z4 z3 z2).

    We group the 6 singleton directions into three involutive pairs:
      axis 1 : positions 1 and 6  (z7 vs z2)   -> {100000, 000001}
      axis 2 : positions 2 and 5  (z6 vs z3)   -> {010000, 000010}
      axis 3 : positions 3 and 4  (z5 vs z4)   -> {001000, 000100}

    This is purely combinatorial and matches the standard Fold6 symmetries used elsewhere
    (reversal pairs and Fibonacci weights 13↔1, 8↔2, 5↔3).
    """
    if len(w) != 6 or _hamming_weight(w) != 1:
        raise ValueError("expected a 6-bit word of Hamming weight 1")
    pos = w.index("1")  # 0-based
    if pos in (0, 5):
        return 1
    if pos in (1, 4):
        return 2
    if pos in (2, 3):
        return 3
    raise AssertionError("unreachable")


def _sign_for_weight1(w: str) -> int:
    """
    Return a deterministic sign (+1 or -1) for a weight=1 word within its axis pair.

    Convention: the earlier (left) position gets +, the later (right) position gets -.
    So:
      100000 -> +, 000001 -> -
      010000 -> +, 000010 -> -
      001000 -> +, 000100 -> -
    """
    if len(w) != 6 or _hamming_weight(w) != 1:
        raise ValueError("expected a 6-bit word of Hamming weight 1")
    pos = w.index("1")  # 0-based
    if pos in (0, 1, 2):
        return +1
    if pos in (3, 4, 5):
        return -1
    raise AssertionError("unreachable")


def _build_dictionary(*, variant: str) -> Dict[str, RootVec]:
    """
    Build a deterministic bijection:
      X6^{cyc}  ->  Φ(B3) or Φ(C3),
    returning word -> rootvec.
    """
    if variant not in ("B3", "C3"):
        raise ValueError("variant must be 'B3' or 'C3'")

    X6 = sml.all_x6()
    cyc = [w for w in X6 if not sml.is_boundary_word(w)]
    if len(cyc) != 18:
        raise AssertionError("Expected |X6^{cyc}|=18.")

    # Split cyclic words into the 6 singleton directions vs the remaining 12.
    cyc_w1 = sorted([w for w in cyc if _hamming_weight(w) == 1])
    cyc_rest = [w for w in cyc if _hamming_weight(w) != 1]
    if len(cyc_w1) != 6 or len(cyc_rest) != 12:
        raise AssertionError("Expected cyclic weight split 6+12.")

    # Root lists for the chosen variant.
    if variant == "B3":
        short6, long12 = _roots_B3()
        # weight=1 -> short roots ±e_i
        weight1_roots = short6
        rest_roots = long12
    else:
        short12, long6 = _roots_C3()
        # weight=1 -> long roots ±2e_i
        weight1_roots = long6
        rest_roots = short12

    # Build axis-wise maps for the 6 weight=1 words.
    # For each axis a in {1,2,3}, pick the + and - root vector on that axis.
    # In B3, that's ±e_a; in C3, that's ±2 e_a.
    axis_to_pm: Dict[int, Tuple[RootVec, RootVec]] = {}
    for rv in weight1_roots:
        # Identify axis by which coordinate is nonzero (expect exactly one).
        nz = [i for i, x in enumerate(rv) if x != 0]
        if len(nz) != 1:
            raise AssertionError(f"Unexpected weight1 root shape: {rv}")
        a = int(nz[0] + 1)  # 1..3
        if rv[nz[0]] > 0:
            pos = rv
            neg = (-rv[0], -rv[1], -rv[2])
            axis_to_pm[a] = (pos, neg)
    if set(axis_to_pm.keys()) != {1, 2, 3}:
        raise AssertionError("Failed to build axis +/- roots for all three axes.")

    out: Dict[str, RootVec] = {}
    for w in cyc_w1:
        ax = _word_axis_for_weight1(w)
        sgn = _sign_for_weight1(w)
        pos, neg = axis_to_pm[ax]
        out[w] = pos if sgn > 0 else neg

    # Map the remaining 12 cyclic words to the remaining 12 roots deterministically.
    # We reuse the paper's stable-type ordering key (r_*,V,w) as a canonical interface order.
    cyc_rest_sorted = sorted(cyc_rest, key=lambda w: sml.stable_type_sort_key(w))
    rest_roots_sorted = list(rest_roots)  # already deterministic order from constructors
    if len(cyc_rest_sorted) != len(rest_roots_sorted):
        raise AssertionError("rest-set size mismatch")
    for w, rv in zip(cyc_rest_sorted, rest_roots_sorted, strict=True):
        out[w] = rv

    if len(out) != 18 or len(set(out.values())) != 18:
        raise AssertionError("Dictionary is not a bijection on cyclic types.")
    return out


def _signed_permutations_WB3() -> List[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]:
    """
    Enumerate the Weyl group W(B3)=W(C3) as signed permutations:
      v -> (s1 v_{p1}, s2 v_{p2}, s3 v_{p3})
    where p is a permutation of (0,1,2) and s_i in {±1}.
    """
    perms = [
        (0, 1, 2),
        (0, 2, 1),
        (1, 0, 2),
        (1, 2, 0),
        (2, 0, 1),
        (2, 1, 0),
    ]
    signs = [(a, b, c) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)]
    return [(p, s) for p in perms for s in signs]


def _act_signed_perm(v: RootVec, p: Tuple[int, int, int], s: Tuple[int, int, int]) -> RootVec:
    vv = (v[p[0]], v[p[1]], v[p[2]])
    return (s[0] * vv[0], s[1] * vv[1], s[2] * vv[2])


@dataclass(frozen=True)
class SeedReport:
    X6_size: int
    cyc_size: int
    bdry_size: int
    bdry_words: List[str]
    cyc_weight_hist: Dict[int, int]
    cyc_weight1_words: List[str]
    cyc_nonweight1_words: List[str]
    b3_dict: Dict[str, RootVec]
    c3_dict: Dict[str, RootVec]
    weyl_group_order: int
    weyl_orbit_sizes_B3: Dict[str, int]
    weyl_orbit_sizes_C3: Dict[str, int]


def _orbit_sizes(words: Sequence[str], mapping: Dict[str, RootVec]) -> Dict[str, int]:
    """Return orbit sizes under signed-permutation Weyl action, pulled back to word labels."""
    inv = {rv: w for (w, rv) in mapping.items()}
    W = _signed_permutations_WB3()

    unseen = set(words)
    out: Dict[str, int] = {}
    while unseen:
        w0 = next(iter(unseen))
        rv0 = mapping[w0]
        orb: List[str] = []
        for (p, s) in W:
            rv = _act_signed_perm(rv0, p=p, s=s)
            if rv in inv:
                orb.append(inv[rv])
        orb_set = set(orb)
        for w in orb_set:
            if w in unseen:
                unseen.remove(w)
        out[w0] = len(orb_set)
    return out


def _write_tex_eq(report: SeedReport, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("% AUTO-GENERATED by scripts/exp_fold6_b3c3_seed.py")
    lines.append("\\[")
    lines.append("\\begin{aligned}")
    lines.append(
        rf"|X_6|&={report.X6_size},\qquad |X_6^{{\mathrm{{cyc}}}}|={report.cyc_size},\qquad |X_6^{{\mathrm{{bdry}}}}|={report.bdry_size},\\"
    )
    bd = ",\\ ".join([f"\\texttt{{{w}}}" for w in report.bdry_words])
    lines.append(rf"X_6^{{\mathrm{{bdry}}}}&=\{{{bd}\}},\\")
    # Weight histogram on cyclic sector
    hist_tex = ",\\ ".join([f"{k}:{v}" for k, v in sorted(report.cyc_weight_hist.items())])
    lines.append(rf"\mathrm{{wt}}\text{{-hist}}(X_6^{{\mathrm{{cyc}}}})&=\{{{hist_tex}\}},\\")
    lines.append(
        rf"\#\{{w\in X_6^{{\mathrm{{cyc}}}}:\ \mathrm{{wt}}(w)=1\}}&={len(report.cyc_weight1_words)},\qquad \#\{{w\in X_6^{{\mathrm{{cyc}}}}:\ \mathrm{{wt}}(w)\neq 1\}}={len(report.cyc_nonweight1_words)}."
    )
    lines.append("\\end{aligned}")
    lines.append("\\]")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _write_tex_table(
    mapping: Dict[str, RootVec], *, title: str, label: str, out_path: Path
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Deterministic order: reuse the paper's canonical stable-type ordering.
    rows = sorted(mapping.items(), key=lambda kv: sml.stable_type_sort_key(kv[0]))
    lines: List[str] = []
    lines.append("% AUTO-GENERATED by scripts/exp_fold6_b3c3_seed.py")
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{10pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append(f"\\caption{{{title}}}")
    lines.append(f"\\label{{{label}}}")
    lines.append("\\begin{tabular}{l r r}")
    lines.append("\\toprule")
    lines.append("$w\\in X_6^{\\mathrm{cyc}}$ & $\\mathrm{wt}(w)$ & root vector\\\\")
    lines.append("\\midrule")
    for w, rv in rows:
        wt = _hamming_weight(w)
        lines.append(f"\\texttt{{{w}}} & {wt} & $({rv[0]},{rv[1]},{rv[2]})$\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    X6 = sml.all_x6()
    cyc = [w for w in X6 if not sml.is_boundary_word(w)]
    bdry = [w for w in X6 if sml.is_boundary_word(w)]
    if len(X6) != 21 or len(cyc) != 18 or len(bdry) != 3:
        raise AssertionError("Unexpected X6 / cyclic / boundary sizes.")

    bdry_sorted = sorted(bdry, key=lambda w: (sml.zeckendorf_value(w), w))

    cyc_weight_hist = Counter(_hamming_weight(w) for w in cyc)
    cyc_w1 = sorted([w for w in cyc if _hamming_weight(w) == 1])
    cyc_rest = sorted([w for w in cyc if _hamming_weight(w) != 1])

    b3_dict = _build_dictionary(variant="B3")
    c3_dict = _build_dictionary(variant="C3")

    # Weyl group order (by construction)
    W = _signed_permutations_WB3()
    if len(W) != 48:
        raise AssertionError("Expected |W(B3)|=48.")

    # Orbit sizes on cyclic words (pulled back via the chosen dictionaries).
    orb_B3 = _orbit_sizes(cyc, b3_dict)
    orb_C3 = _orbit_sizes(cyc, c3_dict)

    report = SeedReport(
        X6_size=len(X6),
        cyc_size=len(cyc),
        bdry_size=len(bdry),
        bdry_words=list(bdry_sorted),
        cyc_weight_hist=dict(sorted(cyc_weight_hist.items())),
        cyc_weight1_words=list(cyc_w1),
        cyc_nonweight1_words=list(cyc_rest),
        b3_dict=b3_dict,
        c3_dict=c3_dict,
        weyl_group_order=len(W),
        weyl_orbit_sizes_B3=orb_B3,
        weyl_orbit_sizes_C3=orb_C3,
    )

    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)

    # JSON payload (kept under sections/generated for this paper's conventions).
    json_path = gen / "fold6_b3c3_seed.json"
    json_path.write_text(
        json.dumps(
            {
                "X6_size": report.X6_size,
                "cyc_size": report.cyc_size,
                "bdry_size": report.bdry_size,
                "bdry_words": report.bdry_words,
                "cyc_weight_hist": report.cyc_weight_hist,
                "cyc_weight1_words": report.cyc_weight1_words,
                "cyc_nonweight1_words": report.cyc_nonweight1_words,
                "B3_dictionary": report.b3_dict,
                "C3_dictionary": report.c3_dict,
                "weyl_group_order": report.weyl_group_order,
                "weyl_orbit_sizes_B3": report.weyl_orbit_sizes_B3,
                "weyl_orbit_sizes_C3": report.weyl_orbit_sizes_C3,
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    # LaTeX fragments.
    _write_tex_eq(report, gen / "eq_fold6_b3c3_seed.tex")
    _write_tex_table(
        report.b3_dict,
        title="A deterministic identification (dictionary) of $X_6^{\\mathrm{cyc}}$ with the $B_3$ root system (choice of normalization).",
        label="tab:fold6_b3c3_root_dictionary_b3",
        out_path=gen / "tab_fold6_b3c3_root_dictionary_B3.tex",
    )
    _write_tex_table(
        report.c3_dict,
        title="A deterministic identification (dictionary) of $X_6^{\\mathrm{cyc}}$ with the $C_3$ root system (long/short swapped normalization).",
        label="tab:fold6_b3c3_root_dictionary_c3",
        out_path=gen / "tab_fold6_b3c3_root_dictionary_C3.tex",
    )

    print(f"[fold6-b3c3-seed] wrote {json_path}", flush=True)
    print(f"[fold6-b3c3-seed] wrote {gen / 'eq_fold6_b3c3_seed.tex'}", flush=True)
    print(f"[fold6-b3c3-seed] wrote {gen / 'tab_fold6_b3c3_root_dictionary_B3.tex'}", flush=True)
    print(f"[fold6-b3c3-seed] wrote {gen / 'tab_fold6_b3c3_root_dictionary_C3.tex'}", flush=True)
    print("[fold6-b3c3-seed] done", flush=True)


if __name__ == "__main__":
    main()

