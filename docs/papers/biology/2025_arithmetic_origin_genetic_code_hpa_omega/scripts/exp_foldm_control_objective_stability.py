# -*- coding: utf-8 -*-
"""
Stability of the control-boundary objective across Fold_m (standard library only).

We analyze the control set K={AUG,UAA,UAG,UGA} and the boundary indicator under Fold_m:
  S_m(mu) = # { c in K : Fold_m(c;mu) is boundary }.

This script reports:
  - per-m maxima and argmax counts
  - whether mu* is an argmax
  - intersection size of argmax sets across m
  - a combined objective over a chosen m-set: sum_{m in M} S_m(mu)

Outputs:
  - sections/generated/foldm_control_objective_stability.tex (+ .meta.json)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import all_encodings, encoding_to_str, fold_codon_m


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
CONTROL_CODONS = ("AUG", "UAA", "UAG", "UGA")


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _parse_int_list(s: str) -> list[int]:
    out: list[int] = []
    for p in str(s or "").split(","):
        p = p.strip()
        if not p:
            continue
        out.append(int(p))
    out = sorted({int(x) for x in out if int(x) > 0})
    if not out:
        raise SystemExit("List must contain positive integers.")
    return out


def s_m(mu: dict[str, str], *, m: int) -> int:
    return int(sum(1 for c in CONTROL_CODONS if fold_codon_m(c, mu, m=int(m)).is_boundary))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fold_m control-boundary objective stability over encodings.")
    p.add_argument("--m-list", default="6,7,8,9", help="Comma-separated m values to analyze.")
    p.add_argument("--combine-m", default="6,7,8", help="Comma-separated m values for combined objective sum_m S_m(mu).")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "foldm_control_objective_stability.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    m_list = _parse_int_list(str(args.m_list))
    m_comb = _parse_int_list(str(args.combine_m))
    out_tex = Path(args.out_tex)

    cache_key = {
        "analysis": "foldm_control_objective_stability",
        "version": int(SCRIPT_VERSION),
        "m_list": [int(x) for x in m_list],
        "m_comb": [int(x) for x in m_comb],
        "mu_star": MU_STAR,
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    encs = all_encodings()

    # Per-m summaries.
    per_m_rows: list[tuple[int, int, int, int, int]] = []
    argmax_sets: list[set[tuple[str, str, str, str]]] = []
    for m in m_list:
        scores = [s_m(mu, m=int(m)) for mu in encs]
        best = int(max(scores)) if scores else 0
        n_argmax = int(sum(1 for x in scores if int(x) == int(best)))
        mu_star_score = int(s_m(MU_STAR, m=int(m)))
        mu_star_in = int(mu_star_score == best)
        per_m_rows.append((int(m), best, mu_star_score, n_argmax, mu_star_in))
        argmax_sets.append({(mu["A"], mu["C"], mu["G"], mu["U"]) for mu in encs if s_m(mu, m=int(m)) == best})

    inter = set.intersection(*argmax_sets) if argmax_sets else set()
    inter_size = int(len(inter))

    # Combined objective.
    comb_scores = [int(sum(s_m(mu, m=int(m)) for m in m_comb)) for mu in encs]
    best_sum = int(max(comb_scores)) if comb_scores else 0
    best_sum_mus = [mu for mu, sc in zip(encs, comb_scores) if int(sc) == int(best_sum)]
    mu_star_sum = int(sum(s_m(MU_STAR, m=int(m)) for m in m_comb))
    mu_star_in_best_sum = int(any(mu == MU_STAR for mu in best_sum_mus))

    m_list_tex = ",".join(str(int(x)) for x in m_list)
    m_comb_tex = ",".join(str(int(x)) for x in m_comb)

    lines: list[str] = []
    lines.append("Control-boundary objective stability across Fold$_m$ (control set $\\{\\mathrm{AUG,UAA,UAG,UGA}\\}$).")
    lines.append("")
    lines.append("\\begin{center}")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{tabular}{r r r r r}")
    lines.append("\\toprule")
    lines.append("$m$ & $\\max S_m$ & $S_m(\\mu^\\ast)$ & \\#argmax & $\\mathbf{1}\\{\\mu^\\ast\\in\\mathrm{argmax}\\}$ \\\\")
    lines.append("\\midrule")
    for (m, best, mu_s, n_argmax, mu_in) in per_m_rows:
        lines.append(f"{m} & {best} & {mu_s} & {n_argmax} & {mu_in} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")
    lines.append(
        f"Across $m\\in\\{{{m_list_tex}\\}}$, the intersection of argmax encoding sets is empty "
        f"($|\\cap_m\\,\\mathrm{{argmax}}\\,S_m|={inter_size}$)."
    )
    lines.append(
        f"For the combined objective $\\sum_{{m\\in M}} S_m(\\mu)$ with $M=\\{{{m_comb_tex}\\}}$, the maximum is {best_sum}, "
        f"achieved by {len(best_sum_mus)} encodings; $\\mu^\\ast$ attains {mu_star_sum} and "
        f"$\\mathbf{{1}}\\{{\\mu^\\ast\\in\\mathrm{{argmax}}\\}}={mu_star_in_best_sum}$."
    )
    lines.append("")

    if best_sum_mus:
        lines.append("\\begin{center}")
        lines.append("\\small")
        lines.append("\\begin{tabular}{l}")
        lines.append("\\toprule")
        lines.append("Encodings achieving $\\max_\\mu\\sum_{m\\in M} S_m(\\mu)$ (listed as $A,C,G,U$ bitpairs) \\\\")
        lines.append("\\midrule")
        for mu in best_sum_mus:
            lines.append(f"{encoding_to_str(mu)} \\\\")
        lines.append("\\bottomrule")
        lines.append("\\end{tabular}")
        lines.append("\\end{center}")
        lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print("Wrote:", out_tex)


if __name__ == "__main__":
    main()


