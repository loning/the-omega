# -*- coding: utf-8 -*-
"""
List the boundary-mapping codons under mu* for each Fold_m, restricted to the codon-scale range.

Because mu* is a bijection between codons and indices N in {0..63}, the boundary codon set at a given m
is exactly the preimage of B_m(<=63) under the labeling induced by mu*.

Outputs:
  - sections/generated/foldm_boundary_codon_list_mu_star.tex (+ .meta.json)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import GENETIC_CODE, fold_codon_m


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


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
    p = argparse.ArgumentParser(description="Boundary-mapping codon list across Fold_m under mu*.")
    p.add_argument("--m-list", default="6,7,8,9", help="Comma-separated m values.")
    p.add_argument("--n-max", type=int, default=63, help="Max index N (default 63).")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "foldm_boundary_codon_list_mu_star.tex"),
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
        "analysis": "foldm_boundary_codon_list_mu_star",
        "version": int(SCRIPT_VERSION),
        "m_list": [int(m) for m in ms],
        "n_max": int(n_max),
        "mu_star": MU_STAR,
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    codons = sorted(GENETIC_CODE.keys())
    if len(codons) != 64:
        raise SystemExit("Expected 64 codons in GENETIC_CODE")

    # Precompute folds at each m to avoid repeated parsing.
    rows: list[tuple[int, str, str, int, str, int, int]] = []
    for m in ms:
        for c in codons:
            f = fold_codon_m(c, MU_STAR, m=int(m))
            if int(f.n) > int(n_max):
                continue
            if not f.is_boundary:
                continue
            rows.append((int(m), str(f.codon), str(f.bits), int(f.n), str(f.w), int(f.v), int(f.delta)))

    rows.sort(key=lambda r: (r[0], r[3], r[1]))

    lines: list[str] = []
    lines.append(f"Boundary-mapping codons under $\\mu^\\ast$ across Fold$_m$ (restricted to $N\\le {n_max}$).")
    lines.append("")
    lines.append("\\begin{center}")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{tabular}{r l l r l r r}")
    lines.append("\\toprule")
    lines.append("$m$ & codon & bits & $N$ & $w_m$ & $V_m$ & $\\Delta_m$ \\\\")
    lines.append("\\midrule")
    for m, codon, bits, n, w, v, d in rows:
        lines.append(f"{m} & $\\mathrm{{{codon}}}$ & \\texttt{{{bits}}} & {n} & \\texttt{{{w}}} & {v} & {d} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print("Wrote:", out_tex)


if __name__ == "__main__":
    main()


