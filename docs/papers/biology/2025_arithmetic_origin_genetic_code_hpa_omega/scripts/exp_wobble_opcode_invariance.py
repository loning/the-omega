# -*- coding: utf-8 -*-
"""
ISA-M2: Wobble re-interpretation as a pure math audit on the codon mutation graph.

We quantify how single-nucleotide substitutions at positions 1/2/3 perturb the
Fold_6 control stream under μ*:
  control(c) = (w, sector, V, Δ)

If the 3rd position is "more conserved" in this control layer, we should observe
higher invariance probabilities for w / sector (and smaller Δ perturbations) for
position-3 mutations compared to positions 1/2.

Outputs:
  - sections/generated/wobble_opcode_invariance.tex
  - sections/generated/wobble_opcode_invariance.tex.meta.json

Standard library only.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import BASES, GENETIC_CODE, fold_codon


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass(frozen=True)
class CodonCtl:
    aa: str
    w: str
    v: int
    delta: int
    is_boundary: bool


def _ctl(codon: str) -> CodonCtl:
    f = fold_codon(codon, MU_STAR)
    return CodonCtl(aa=str(f.aa), w=str(f.w), v=int(f.v), delta=int(f.delta), is_boundary=bool(f.is_boundary))


def _mutate(codon: str, pos0: int, base: str) -> str:
    return codon[:pos0] + base + codon[pos0 + 1 :]


def _mean(xs: list[float]) -> float:
    return float(sum(xs) / len(xs)) if xs else float("nan")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ISA-M2 wobble audit: opcode invariance under point mutations (μ*).")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "wobble_opcode_invariance.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Force recomputation (ignore cache).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_tex = Path(args.out_tex)

    cache_key: dict[str, Any] = {
        "analysis": "wobble_opcode_invariance",
        "version": int(SCRIPT_VERSION),
        "mu_star": MU_STAR,
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    codons = sorted(GENETIC_CODE.keys())
    assert len(codons) == 64, f"Expected 64 codons, got {len(codons)}"

    # Per-position accumulators.
    pos_stats: dict[int, Counter[str]] = {0: Counter(), 1: Counter(), 2: Counter()}
    delta_abs_hist: dict[int, Counter[int]] = {0: Counter(), 1: Counter(), 2: Counter()}
    delta_abs_values: dict[int, list[float]] = defaultdict(list)

    for codon in codons:
        c0 = _ctl(codon)
        for pos0 in (0, 1, 2):
            for b in BASES:
                if b == codon[pos0]:
                    continue
                codon2 = _mutate(codon, pos0, b)
                c1 = _ctl(codon2)

                pos_stats[pos0]["n_mut"] += 1
                if c1.aa == c0.aa:
                    pos_stats[pos0]["payload_same"] += 1
                if c1.w == c0.w:
                    pos_stats[pos0]["w_same"] += 1
                if c1.is_boundary == c0.is_boundary:
                    pos_stats[pos0]["sector_same"] += 1
                if c1.delta == c0.delta:
                    pos_stats[pos0]["delta_same"] += 1
                dabs = abs(int(c1.delta) - int(c0.delta))
                delta_abs_hist[pos0][int(dabs)] += 1
                delta_abs_values[pos0].append(float(dabs))

    def p(count: int, total: int) -> float:
        if total <= 0:
            return float("nan")
        return float(count) / float(total)

    # Emit LaTeX.
    lines: list[str] = []
    lines.append(
        "ISA-M2 wobble audit: opcode/control invariance under single-nucleotide substitutions "
        "(uniformly over the 64 codons; μ$^\\ast$)."
    )
    lines.append("")
    lines.append("\\begin{center}")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{tabular}{r r r r r r r}")
    lines.append("\\toprule")
    lines.append("pos & $n$ & $p(\\mathrm{payload\\ same})$ & $p(w\\ \\mathrm{same})$ & $p(\\mathrm{sector\\ same})$ & $p(\\Delta\\ \\mathrm{same})$ & $\\mathbb{E}|\\Delta' - \\Delta|$ \\\\")
    lines.append("\\midrule")
    for pos0 in (0, 1, 2):
        st = pos_stats[pos0]
        n = int(st.get("n_mut", 0))
        lines.append(
            f"{pos0+1} & {n} & {p(int(st.get('payload_same', 0)), n):.4f} & {p(int(st.get('w_same', 0)), n):.4f} & "
            f"{p(int(st.get('sector_same', 0)), n):.4f} & {p(int(st.get('delta_same', 0)), n):.4f} & {_mean(delta_abs_values[pos0]):.3f} \\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")

    # Δ-perturbation histogram (abs diff) per position.
    lines.append("\\noindent $|\\Delta'-\\Delta|$ histogram by mutation position (counts over 192 mutations per position):")
    lines.append("\\begin{center}")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.10}")
    lines.append("\\begin{tabular}{r l}")
    lines.append("\\toprule")
    lines.append("pos & histogram \\\\")
    lines.append("\\midrule")
    for pos0 in (0, 1, 2):
        h = delta_abs_hist[pos0]
        parts = [f"{k}:{h[k]}" for k in sorted(h.keys())]
        lines.append(f"{pos0+1} & $\\{{{', '.join(parts)}\\}}$ \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print(f"[write] {out_tex}", flush=True)


if __name__ == "__main__":
    main()
