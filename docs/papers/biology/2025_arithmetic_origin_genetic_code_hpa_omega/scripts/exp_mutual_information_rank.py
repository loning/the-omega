# -*- coding: utf-8 -*-
"""
Mutual-information rank of the selected encoding mu* among all 24 encodings.

This script is intentionally small and auditable (standard library only).

Outputs:
  - sections/generated/mutual_information_rank.tex
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import all_encodings, encoding_to_str, mutual_information_bits


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Mutual-information rank of mu* over all 24 encodings.")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "mutual_information_rank.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def _is_close(a: float, b: float, *, eps: float = 1e-12) -> bool:
    return abs(float(a) - float(b)) <= float(eps)


def main() -> None:
    args = parse_args()
    out_tex = Path(args.out_tex)

    cache_key = {
        "analysis": "mutual_information_rank",
        "version": int(SCRIPT_VERSION),
        "mu_star": MU_STAR,
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    entries: list[tuple[float, dict[str, str]]] = []
    for mu in all_encodings():
        mi = float(mutual_information_bits(mu))
        if math.isnan(mi) or (not math.isfinite(mi)):
            continue
        entries.append((mi, mu))
    if len(entries) != 24:
        raise SystemExit(f"Expected 24 encodings, got {len(entries)}")

    entries.sort(key=lambda x: x[0], reverse=True)
    mi_star = float(mutual_information_bits(MU_STAR))
    mi_max = float(entries[0][0])
    mi_min = float(entries[-1][0])

    better = sum(1 for mi, _ in entries if mi > mi_star + 1e-12)
    equal = sum(1 for mi, _ in entries if _is_close(mi, mi_star, eps=1e-12))
    rank_low = 1 + int(better)
    rank_high = int(better) + int(equal)

    best_encs = [mu for mi, mu in entries if _is_close(mi, mi_max, eps=1e-12)]
    best_str = "; ".join(encoding_to_str(mu) for mu in best_encs[:3])
    if len(best_encs) > 3:
        best_str += f"; ... (+{len(best_encs) - 3} ties)"

    if rank_low == rank_high:
        rank_str = f"{rank_low}/24"
    else:
        rank_str = f"{rank_low}--{rank_high}/24"

    lines: list[str] = []
    lines.append(
        "Under the uniform codon prior, $\\mu^\\ast$ has mutual information "
        f"$I(\\mathsf{{Gen}}(C);w_{{\\mu^\\ast}}(C))={mi_star:.6f}$ bits. "
        f"Across all 24 encodings this corresponds to rank {rank_str} by mutual information "
        f"(tied with {int(equal)} encodings; {int(better)} strictly higher). "
        f"(max {mi_max:.6f}, min {mi_min:.6f}; MI-opt encoding: {best_str})."
    )
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print("Wrote:", out_tex)


if __name__ == "__main__":
    main()


