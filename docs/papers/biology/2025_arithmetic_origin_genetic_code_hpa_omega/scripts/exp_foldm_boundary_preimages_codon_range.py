# -*- coding: utf-8 -*-
"""
Boundary preimages within the codon-scale range N in [0,63] across Fold_m.

This reports the *index-level* set:
  B_m(<=63) = { N in {0..63} : Fold_m(N) is boundary (w1=wm=1) }.

Because every encoding mu is a bijection between codons and indices N, the *count* |B_m(<=63)|
equals the number of boundary-mapping codons under any encoding; only the labels change.

Outputs:
  - sections/generated/foldm_boundary_preimages_codon_range.tex (+ .meta.json)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import fold_m, is_boundary_word, zeckendorf_value_word


SCRIPT_VERSION = 1


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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Boundary preimages in N<=63 across Fold_m.")
    p.add_argument("--m-list", default="6,7,8,9", help="Comma-separated m values.")
    p.add_argument("--n-max", type=int, default=63, help="Max index N to include (default 63).")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "foldm_boundary_preimages_codon_range.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    ms = _parse_int_list(str(args.m_list))
    n_max = int(args.n_max)
    if n_max < 0:
        raise SystemExit("--n-max must be >= 0")
    out_tex = Path(args.out_tex)

    cache_key = {
        "analysis": "foldm_boundary_preimages_codon_range",
        "version": int(SCRIPT_VERSION),
        "m_list": [int(m) for m in ms],
        "n_max": int(n_max),
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    lines: list[str] = []
    lines.append(
        f"Boundary preimages in the codon-scale range $N\\in\\{{0,\\dots,{n_max}\\}}$ across Fold$_m$."
    )
    lines.append(
        "Here $w_m(N)=\\mathrm{Fold}_m(N)$ and boundary means $w_1=w_m=1$ (with golden-mean admissibility)."
    )
    lines.append("")
    lines.append("\\begin{center}")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{tabular}{r r r r}")
    lines.append("\\toprule")
    lines.append("$m$ & $|B_m(\\le %d)|$ & distinct boundary words & boundary indices $N$ \\\\" % int(n_max))
    lines.append("\\midrule")

    for m in ms:
        idxs: list[int] = []
        words: list[str] = []
        for n in range(0, n_max + 1):
            w = fold_m(int(n), int(m))
            if is_boundary_word(w):
                idxs.append(int(n))
                words.append(str(w))
        uniq_words = sorted(set(words))
        idxs_s = ", ".join(str(i) for i in idxs) if idxs else "-"
        words_s = ", ".join(f"\\texttt{{{w}}}" for w in uniq_words) if uniq_words else "-"
        lines.append(f"{int(m)} & {len(idxs)} & {len(uniq_words)} & {idxs_s} \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")
    lines.append(
        "For each $m$, the count $|B_m(\\le %d)|$ is encoding-independent (it depends only on the index set $\\{0,\\dots,%d\\}$)."  # noqa: E501
        % (int(n_max), int(n_max))
    )
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print("Wrote:", out_tex)


if __name__ == "__main__":
    main()


