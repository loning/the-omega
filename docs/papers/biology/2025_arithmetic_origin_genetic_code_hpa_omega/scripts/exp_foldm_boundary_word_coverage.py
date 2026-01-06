# -*- coding: utf-8 -*-
"""
Coverage of boundary words within the codon-scale range N in [0,63] across Fold_m.

For each m, we compare:
  - the full boundary subset X_m^{bdry} (all admissible words with w1=wm=1)
  - the realized boundary words among N<=63: {Fold_m(N) : N<=63 and Fold_m(N) is boundary}

Outputs:
  - sections/generated/foldm_boundary_word_coverage.tex (+ .meta.json)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import boundary_words_m, fold_m, is_boundary_word


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
    p = argparse.ArgumentParser(description="Fold_m boundary-word coverage for N<=63.")
    p.add_argument("--m-list", default="6,7,8,9", help="Comma-separated m values.")
    p.add_argument("--n-max", type=int, default=63, help="Max index N (default 63).")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "foldm_boundary_word_coverage.tex"),
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
        "analysis": "foldm_boundary_word_coverage",
        "version": int(SCRIPT_VERSION),
        "m_list": [int(m) for m in ms],
        "n_max": int(n_max),
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    rows: list[tuple[int, int, int, list[str]]] = []
    for m in ms:
        all_bdry = set(boundary_words_m(int(m)))
        realized: set[str] = set()
        for n in range(0, n_max + 1):
            w = fold_m(int(n), int(m))
            if is_boundary_word(w):
                realized.add(str(w))
        missing = sorted(all_bdry - realized)
        rows.append((int(m), int(len(all_bdry)), int(len(realized)), missing))

    lines: list[str] = []
    lines.append(f"Boundary-word coverage on the codon-scale range $N\\le {n_max}$ across Fold$_m$.")
    lines.append("")
    lines.append("\\begin{center}")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{tabular}{r r r r}")
    lines.append("\\toprule")
    lines.append("$m$ & $|X_m^{\\mathrm{bdry}}|$ & realized (distinct) & missing \\\\")
    lines.append("\\midrule")
    for m, total_b, realized_b, missing in rows:
        lines.append(f"{m} & {total_b} & {realized_b} & {len(missing)} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")

    # List missing boundary words when any exist (notably for m>=9 on N<=63).
    for m, total_b, realized_b, missing in rows:
        if not missing:
            continue
        miss_s = ",\\allowbreak ".join(f"\\texttt{{{w}}}" for w in missing)
        lines.append(f"For $m={m}$, the missing boundary words among $N\\le {n_max}$ are: {miss_s}.")
        lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print("Wrote:", out_tex)


if __name__ == "__main__":
    main()


