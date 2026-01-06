# -*- coding: utf-8 -*-
"""
List the argmax encoding sets for the control-boundary objective S_m across Fold_m.

This complements the stability summary (which reports only maxima and argmax counts).

Outputs:
  - sections/generated/foldm_control_objective_argmax_list.tex (+ .meta.json)
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
        raise SystemExit("--m-list must contain positive integers")
    return out


def _s_m(mu: dict[str, str], *, m: int) -> int:
    return int(sum(1 for c in CONTROL_CODONS if fold_codon_m(c, mu, m=int(m)).is_boundary))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="List argmax encodings for Fold_m control objective.")
    p.add_argument("--m-list", default="6,7,8,9", help="Comma-separated m values.")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "foldm_control_objective_argmax_list.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    ms = _parse_int_list(str(args.m_list))
    out_tex = Path(args.out_tex)

    cache_key = {
        "analysis": "foldm_control_objective_argmax_list",
        "version": int(SCRIPT_VERSION),
        "m_list": [int(m) for m in ms],
        "mu_star": MU_STAR,
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    encs = list(all_encodings())
    if len(encs) != 24:
        raise SystemExit("Expected 24 encodings")

    lines: list[str] = []
    lines.append("Argmax encoding sets for the control-boundary objective $S_m$.")
    lines.append("Control set: $\\{\\mathrm{AUG},\\allowbreak \\mathrm{UAA},\\allowbreak \\mathrm{UAG},\\allowbreak \\mathrm{UGA}\\}$.")
    lines.append("")
    lines.append("\\begin{itemize}")
    for m in ms:
        scores = [_s_m(mu, m=int(m)) for mu in encs]
        best = int(max(scores))
        argmax = [mu for mu, sc in zip(encs, scores) if int(sc) == int(best)]
        mu_star_in = "yes" if any(mu == MU_STAR for mu in argmax) else "no"
        lines.append(f"\\item $m={int(m)}$: $\\max S_m={best}$, \\#argmax={len(argmax)}, $\\mu^\\ast\\in\\mathrm{{argmax}}$={mu_star_in}.")
        lines.append("  \\begin{itemize}")
        for mu in argmax:
            lines.append("  \\item " + encoding_to_str(mu))
        lines.append("  \\end{itemize}")
    lines.append("\\end{itemize}")
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print("Wrote:", out_tex)


if __name__ == "__main__":
    main()


