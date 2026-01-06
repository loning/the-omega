# -*- coding: utf-8 -*-
"""
Brief, main-text-friendly summary of the 4-codon control-set null.

This is a lightweight companion to exp_genetic_code_decompiler.generate_control_objective_null_over_all_4codon_sets().
It recomputes only the quantities needed for a compact "how special is it?" statement.

Outputs:
  - sections/generated/control_objective_null_brief.tex (+ .meta.json)
"""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from genetic_code_tools import BOUNDARY_WORDS, GENETIC_CODE, STOP_CODONS, all_encodings, fold_codon


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Brief control-set null summary for the main text.")
    p.add_argument(
        "--out-tex",
        default=str(generated_dir() / "control_objective_null_brief.tex"),
        help="Output LaTeX fragment path.",
    )
    p.add_argument("--force", action="store_true", help="Ignore cache and recompute.")
    return p.parse_args()


def _codon_bitmask_index() -> tuple[list[str], dict[str, int]]:
    codons = sorted(GENETIC_CODE.keys())
    if len(codons) != 64:
        raise AssertionError("Expected 64 codons in GENETIC_CODE")
    return codons, {c: i for i, c in enumerate(codons)}


def main() -> None:
    args = parse_args()
    out_tex = Path(args.out_tex)

    cache_key = {"analysis": "control_objective_null_brief", "version": int(SCRIPT_VERSION), "out": str(out_tex)}
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    codons, bit_idx = _codon_bitmask_index()
    encs = all_encodings()

    boundary_masks: list[int] = []
    for mu in encs:
        m = 0
        for c in codons:
            if fold_codon(c, mu).w in BOUNDARY_WORDS:
                m |= 1 << bit_idx[c]
        boundary_masks.append(int(m))
    if len(boundary_masks) != 24:
        raise AssertionError("Expected 24 encodings")

    mu_star_idx = None
    for i, mu in enumerate(encs):
        if mu == MU_STAR:
            mu_star_idx = int(i)
            break
    if mu_star_idx is None:
        raise AssertionError("Failed to locate MU_STAR among encodings")

    def _score_mask(kmask: int) -> tuple[int, int, int | None]:
        best = -1
        n_best = 0
        for bm in boundary_masks:
            s = int((bm & kmask).bit_count())
            if s > best:
                best = s
                n_best = 1
            elif s == best:
                n_best += 1
        if n_best != 1:
            return int(best), int(n_best), None
        idx0: int | None = None
        for i, bm in enumerate(boundary_masks):
            if int((bm & kmask).bit_count()) == int(best):
                if idx0 is None:
                    idx0 = int(i)
                else:
                    return int(best), int(n_best), None
        return int(best), int(n_best), idx0

    # Control set of interest.
    control_codons = ("AUG", "UAA", "UAG", "UGA")
    control_mask = 0
    for c in control_codons:
        control_mask |= 1 << bit_idx[c]
    control_smax, control_m, control_best_idx = _score_mask(control_mask)
    if control_best_idx is None or int(control_m) != 1:
        raise AssertionError("Expected biological control set to have unique argmax")
    if int(control_best_idx) != int(mu_star_idx):
        raise AssertionError("Expected mu* to be the biological control-set argmax")

    # Enumerate all 4-codon subsets.
    total = 0
    unique_any = 0
    mu_star_unique = 0
    mu_star_unique_smax2 = 0
    for a, b, c, d in itertools.combinations(range(64), 4):
        kmask = (1 << a) | (1 << b) | (1 << c) | (1 << d)
        smax, m, best_idx = _score_mask(int(kmask))
        total += 1
        if int(m) == 1:
            unique_any += 1
            if best_idx is not None and int(best_idx) == int(mu_star_idx):
                mu_star_unique += 1
                if int(smax) == int(control_smax):
                    mu_star_unique_smax2 += 1
    if total != 635_376:
        raise AssertionError(f"Unexpected total subsets: {total}")

    # Stop-fixed null (condition on the standard stop set).
    stop_mask = 0
    for c in STOP_CODONS:
        stop_mask |= 1 << bit_idx[c]
    start_candidates = [c for c in codons if c not in STOP_CODONS]
    if len(start_candidates) != 61:
        raise AssertionError("Expected 61 non-stop codons")
    fixed_unique = 0
    fixed_mu_star = 0
    for s in start_candidates:
        kmask = int(stop_mask | (1 << bit_idx[s]))
        _, m, best_idx = _score_mask(kmask)
        if int(m) == 1:
            fixed_unique += 1
            if best_idx is not None and int(best_idx) == int(mu_star_idx):
                fixed_mu_star += 1

    p_unique_any = unique_any / float(total)
    p_mu_star_unique = mu_star_unique / float(total)
    p_mu_star_unique_s2 = mu_star_unique_smax2 / float(total)
    p_fixed_unique = fixed_unique / 61.0
    p_fixed_mu_star = fixed_mu_star / 61.0

    # Brief fragment: keep it short and avoid overfull boxes.
    lines: list[str] = []
    lines.append(
        "Exact null enumeration over all $4$-codon control sets shows that a unique encoding argmax occurs for "
        f"{unique_any}/{total} subsets (probability {p_unique_any:.6f}). "
        f"The specific event that $\\mu^\\ast$ is the unique maximizer has probability {p_mu_star_unique:.6f} "
        f"({mu_star_unique}/{total}); conditioning on $S_{{\\max}}=2$ gives {p_mu_star_unique_s2:.6f} "
        f"({mu_star_unique_smax2}/{total})."
    )
    lines.append("")
    lines.append(
        f"Under the stop-fixed null (fix $\\{{\\mathrm{{UAA,UAG,UGA}}\\}}$ and vary one additional codon), "
        f"the argmax is unique for {fixed_unique}/61 choices and equals $\\mu^\\ast$ for {fixed_mu_star}/61 "
        f"(probability {p_fixed_mu_star:.6f})."
    )
    lines.append("")

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print("Wrote:", out_tex)


if __name__ == "__main__":
    main()


