# -*- coding: utf-8 -*-
"""
ISA-M1: Codon -> OpCode + microcode compiler (Fold_6 control stream).

This script turns the existing Fold_6 layer into a minimal executable interface:
  payload(c) = Gen(c)   (AA / Stop; standard genetic code)
  control(c) = (N, w, V, Δ, sector, boundary)
    - N = 6-bit microstate index under μ*
    - w = Fold_6(N) ∈ X_6
    - V = Zeckendorf value V(w)
    - Δ = N - V(w) ∈ {0,21,34,55} on N∈[0,63]
    - sector = cyclic vs boundary (18 ⊕ 3 split)

Outputs:
  - data/_cache/codon_opcode_table_mu_star_m6.json
  - sections/generated/codon_opcode_compiler_summary.tex
  - sections/generated/codon_opcode_compiler_summary.tex.meta.json

Standard library only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import (
    GENETIC_CODE,
    START_CODON,
    STOP_CODONS,
    all_encodings,
    boundary_words_m,
    codon_index,
    fold6,
    fold_codon,
    is_boundary_word,
    x_m,
    zeckendorf_value_word,
)


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_dir() -> Path:
    d = root_dir() / "data" / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fmt_set(xs: list[int]) -> str:
    return "{" + ",".join(str(int(x)) for x in sorted(set(xs))) + "}"


def _encoding_to_str(mu: dict[str, str]) -> str:
    return f"A={mu['A']}, C={mu['C']}, G={mu['G']}, U={mu['U']}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ISA-M1: Codon opcode compiler + closure audit (μ*, Fold_6).")
    p.add_argument(
        "--out-json",
        default=str(cache_dir() / "codon_opcode_table_mu_star_m6.json"),
        help="Output JSON path for frozen ISA opcode table.",
    )
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "codon_opcode_compiler_summary.tex"),
        help="Output LaTeX summary fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Force recomputation (ignore cache).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_json = Path(args.out_json)
    out_tex = Path(args.out_tex)

    cache_key: dict[str, Any] = {
        "analysis": "codon_opcode_compiler",
        "version": int(SCRIPT_VERSION),
        "mu_star": MU_STAR,
        "out_json": str(out_json),
        "out_tex": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True) and out_json.exists():
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    # ---- Closure checks (deterministic, theorem-level) ----
    x6 = x_m(6)
    b6 = boundary_words_m(6)
    assert len(x6) == 21, f"|X6| mismatch: {len(x6)}"
    assert len(b6) == 3, f"|X6^bdry| mismatch: {len(b6)}"
    assert b6 == {"100001", "100101", "101001"}, f"Boundary words mismatch: {sorted(b6)}"
    cyc6 = [w for w in x6 if w not in b6]
    assert len(cyc6) == 18, f"|X6^cyc| mismatch: {len(cyc6)}"

    # Δ values on the 6-bit index range.
    deltas_by_n = []
    for n in range(64):
        w = fold6(n)
        v = zeckendorf_value_word(w)
        deltas_by_n.append(int(n - v))
    delta_values = sorted(set(deltas_by_n))
    assert delta_values == [0, 21, 34, 55], f"Δ-values mismatch: {delta_values}"

    # Boundary preimages at m=6 are encoding-independent (index-space statement).
    preimages: dict[str, list[int]] = {w: [] for w in sorted(b6)}
    for n in range(64):
        w = fold6(n)
        if w in preimages:
            preimages[w].append(int(n))
    assert preimages["100001"] == [14, 48], f"Boundary preimages mismatch for 100001: {preimages['100001']}"
    assert preimages["100101"] == [19, 53], f"Boundary preimages mismatch for 100101: {preimages['100101']}"
    assert preimages["101001"] == [17, 51], f"Boundary preimages mismatch for 101001: {preimages['101001']}"

    # μ* control-set facts.
    aug = fold_codon(START_CODON, MU_STAR)
    uaa = fold_codon("UAA", MU_STAR)
    uag = fold_codon("UAG", MU_STAR)
    uga = fold_codon("UGA", MU_STAR)
    assert aug.w == "100001", f"AUG boundary word mismatch: {aug.w}"
    assert uaa.w == "100001", f"UAA boundary word mismatch: {uaa.w}"
    assert aug.n == 14 and uaa.n == 48, f"AUG/UAA indices mismatch: AUG={aug.n}, UAA={uaa.n}"
    assert (uaa.n - aug.n) == 34, f"AUG/UAA split mismatch: {uaa.n - aug.n}"

    # Theorem-style negative: no encoding puts all three standard stops in the boundary sector at m=6.
    stop_boundary_counts: list[int] = []
    all3_boundary: list[str] = []
    for mu in all_encodings():
        hits = 0
        for s in STOP_CODONS:
            if fold_codon(s, mu).is_boundary:
                hits += 1
        stop_boundary_counts.append(int(hits))
        if hits == 3:
            all3_boundary.append(_encoding_to_str(mu))
    assert not all3_boundary, f"Unexpected encodings with all 3 stops boundary: {all3_boundary[:3]}"

    # ---- Build opcode table (frozen, payload + control streams) ----
    rows: list[dict[str, object]] = []
    for codon, aa in sorted(GENETIC_CODE.items()):
        f = fold_codon(codon, MU_STAR)
        rows.append(
            {
                "codon": f.codon,
                "payload": str(aa),
                "bits": f.bits,
                "N": int(f.n),
                "w": str(f.w),
                "V": int(f.v),
                "Delta": int(f.delta),
                "sector": ("boundary" if bool(f.is_boundary) else "cyclic"),
                "boundary": bool(f.is_boundary),
            }
        )

    out_obj = {
        "analysis": "codon_opcode_compiler",
        "script_version": int(SCRIPT_VERSION),
        "mu_star": MU_STAR,
        "opcode_table": rows,
        "closure": {
            "X6_size": int(len(x6)),
            "X6_cyclic_size": int(len(cyc6)),
            "X6_boundary_size": int(len(b6)),
            "boundary_words": sorted(b6),
            "delta_values_N_le_63": delta_values,
            "boundary_preimages": {k: v for (k, v) in preimages.items()},
            "mu_star_control": {
                "AUG": {"N": int(aug.n), "w": aug.w, "Delta": int(aug.delta), "payload": aug.aa},
                "UAA": {"N": int(uaa.n), "w": uaa.w, "Delta": int(uaa.delta), "payload": uaa.aa},
                "UAG": {"N": int(uag.n), "w": uag.w, "Delta": int(uag.delta), "payload": uag.aa},
                "UGA": {"N": int(uga.n), "w": uga.w, "Delta": int(uga.delta), "payload": uga.aa},
            },
            "stop_boundary_count_hist_over_24_encodings": {
                "hist": {str(k): int(stop_boundary_counts.count(k)) for k in sorted(set(stop_boundary_counts))},
                "max": int(max(stop_boundary_counts) if stop_boundary_counts else 0),
            },
        },
    }
    write_json_atomic(out_json, out_obj)

    # ---- Emit LaTeX summary fragment ----
    h = out_obj["closure"]["stop_boundary_count_hist_over_24_encodings"]["hist"]  # type: ignore[index]
    hist_s = ", ".join(f"{k}:{v}" for k, v in sorted(h.items(), key=lambda x: int(x[0])))  # type: ignore[attr-defined]
    lines: list[str] = []
    lines.append("\\paragraph{ISA-M1: Codon opcode compiler (Fold$_6$ control stream).}")
    lines.append(
        "Closure checks: $|X_6|=21$ with $|X_6^{\\mathrm{cyc}}|=18$ and $|X_6^{\\mathrm{bdry}}|=3$; "
        f"$X_6^{{\\mathrm{{bdry}}}}={{{', '.join(sorted(b6))}}}$. "
        f"On $N\\in\\{{0,\\dots,63\\}}$, microcode values are $\\Delta\\in{_fmt_set(delta_values)}$."
    )
    lines.append(
        "Under $\\mu^\\ast$ (A=00,C=01,G=10,U=11), AUG and UAA compile to the same boundary word "
        f"$w=\\texttt{{{aug.w}}}$ but distinct preimages $N=14$ vs $N=48$ (split by $34$), i.e. "
        f"$\\Delta(\\mathrm{{AUG}})={int(aug.delta)}$ and $\\Delta(\\mathrm{{UAA}})={int(uaa.delta)}$."
    )
    lines.append(
        "Exhaustive encoding audit (24 two-bit encodings): no encoding places all three standard stops "
        "$\\{\\mathrm{UAA,UAG,UGA}\\}$ in the boundary sector at $m=6$; histogram of boundary-stop counts is "
        f"$\\{{{hist_s}\\}}$."
    )
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print(f"[write] {out_json}", flush=True)
    print(f"[write] {out_tex}", flush=True)


if __name__ == "__main__":
    main()

