# -*- coding: utf-8 -*-
"""
Stop-codon signatures across Fold_m under the selected encoding mu* (standard library only).

Outputs:
  - sections/generated/stop_fine_structure_foldm.tex (+ .meta.json)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import fold_codon_m


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
STOP_CODONS = ("UAA", "UAG", "UGA")


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
    p = argparse.ArgumentParser(description="Stop-codon signatures across Fold_m under mu*.")
    p.add_argument("--m-list", default="6,7,8,9", help="Comma-separated m values.")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "stop_fine_structure_foldm.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    ms = _parse_int_list(str(args.m_list))
    out_tex = Path(args.out_tex)

    cache_key = {
        "analysis": "stop_fine_structure_foldm",
        "version": int(SCRIPT_VERSION),
        "m_list": [int(m) for m in ms],
        "mu_star": MU_STAR,
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    lines: list[str] = []
    lines.append("Stop-codon signatures across Fold$_m$ under $\\mu^\\ast$ ($\\mathrm{UAA/UAG/UGA}$).")
    lines.append("")
    lines.append("\\begin{center}")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append("\\begin{tabular}{r l l r l r r l}")
    lines.append("\\toprule")
    lines.append("$m$ & stop & bits & $N$ & $w_m$ & $V_m$ & $\\Delta_m$ & boundary? \\\\")
    lines.append("\\midrule")

    for m in ms:
        for codon in STOP_CODONS:
            f = fold_codon_m(codon, MU_STAR, m=int(m))
            boundary = "yes" if bool(f.is_boundary) else "no"
            lines.append(
                f"{int(m)} & $\\mathrm{{{codon}}}$ & \\texttt{{{f.bits}}} & {int(f.n)} & "
                f"\\texttt{{{f.w}}} & {int(f.v)} & {int(f.delta)} & {boundary} \\\\"
            )

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{center}")
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print("Wrote:", out_tex)


if __name__ == "__main__":
    main()


