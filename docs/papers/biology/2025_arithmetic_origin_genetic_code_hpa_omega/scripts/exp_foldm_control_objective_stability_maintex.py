# -*- coding: utf-8 -*-
"""
Compact Fold_m control-objective stability table (for main text).

This is a shortened companion to exp_foldm_control_objective_stability.py.
It emits a compact table-only LaTeX fragment suitable for inclusion in the main text.

Output:
  - sections/generated/foldm_control_objective_stability_maintex.tex (+ .meta.json)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import all_encodings, fold_codon_m


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
        raise SystemExit("--m-list must contain positive integers")
    return out


def _s_m(mu: dict[str, str], *, m: int) -> int:
    return int(sum(1 for c in CONTROL_CODONS if fold_codon_m(c, mu, m=int(m)).is_boundary))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compact Fold_m control-objective stability table for main text.")
    p.add_argument("--m-list", default="6,7,8,9", help="Comma-separated m values.")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "foldm_control_objective_stability_maintex.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    m_list = _parse_int_list(str(args.m_list))
    out_tex = Path(args.out_tex)

    cache_key = {
        "analysis": "foldm_control_objective_stability_maintex",
        "version": int(SCRIPT_VERSION),
        "m_list": [int(x) for x in m_list],
        "mu_star": MU_STAR,
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    encs = all_encodings()
    rows: list[tuple[int, int, int, int]] = []
    for m in m_list:
        scores = [_s_m(mu, m=int(m)) for mu in encs]
        best = int(max(scores)) if scores else 0
        n_argmax = int(sum(1 for x in scores if int(x) == int(best)))
        mu_star_score = int(_s_m(MU_STAR, m=int(m)))
        rows.append((int(m), best, mu_star_score, n_argmax))

    lines: list[str] = []
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{tabular}{r r r r}")
    lines.append("\\toprule")
    lines.append("$m$ & $\\max S_m$ & $S_m(\\mu^\\ast)$ & \\#argmax \\\\")
    lines.append("\\midrule")
    for m, best, mu_s, n_argmax in rows:
        lines.append(f"{m} & {best} & {mu_s} & {n_argmax} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print("Wrote:", out_tex)


if __name__ == "__main__":
    main()


