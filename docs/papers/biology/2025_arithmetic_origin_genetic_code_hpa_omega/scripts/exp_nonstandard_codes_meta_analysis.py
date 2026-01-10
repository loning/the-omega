# -*- coding: utf-8 -*-
"""
Nonstandard translation tables: meta-analysis + 24-encoding negative control (Reinforcement 7).

Idea:
  For each NCBI translation table (gc.prt), take its stop-codon set and measure
  boundary-hit enrichment under a fixed encoding μ at m=6:
    k_obs = #stops with w_mu(c) in X_6^bdry
  Under a simple codon-level null (stop codons are a random subset of size n_stop),
  k_obs follows a Hypergeometric(N=64, K=6, n=n_stop). We compute the one-sided
  enrichment p-value p_t(μ)=P(X>=k_obs).

  Then combine per-table p-values with Fisher's statistic:
    F(μ) = -2 * sum_t log p_t(μ)

  Finally, use the exact encoding-null (enumeration over 24 encodings) to assess
  how extreme μ* is among all μ.

Outputs:
  - sections/generated/nonstandard_codes_meta_analysis.tex
  - data/_cache/nonstandard_codes_meta_analysis_v1.json (+ meta)

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, read_json, write_json_atomic
from genetic_code_tools import all_encodings, encoding_to_str, fold_codon, is_boundary_word

from exp_nonstandard_codes import codons_for_table, parse_gc_prt


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
ANALYSIS_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_dir() -> Path:
    d = root_dir() / "data" / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _is_mu_star(mu: dict[str, str]) -> bool:
    return all(mu.get(b) == MU_STAR[b] for b in ("A", "C", "G", "U"))


def _hypergeom_tail_p(*, N: int, K: int, n: int, k: int) -> float:
    """
    P(X >= k) for Hypergeom(N, K, n) using exact comb sums.
    """
    if k <= 0:
        return 1.0
    if n <= 0 or K <= 0:
        return 1.0
    if k > min(K, n):
        return 0.0
    denom = math.comb(N, n)
    s = 0
    for x in range(k, min(K, n) + 1):
        s += math.comb(K, x) * math.comb(N - K, n - x)
    return float(s) / float(denom)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="Force recomputation even if cache exists.")
    args = ap.parse_args()

    out_json = cache_dir() / "nonstandard_codes_meta_analysis_v1.json"
    out_tex = generated_dir() / "nonstandard_codes_meta_analysis.tex"

    cache_key = {"analysis": "nonstandard_codes_meta_analysis", "analysis_version": ANALYSIS_VERSION}
    expected_meta = {"cache_key": cache_key, "cache_key_digest": cache_key_digest(cache_key), "schema_version": 1}

    if (not args.force) and cache_hit(out_json, expected_meta=expected_meta, require_meta=True):
        obj = read_json(out_json)
        write_text(out_tex, str(obj["latex"]) + "\n")
        return

    tables = parse_gc_prt((root_dir() / "data" / "gc.prt").read_text(encoding="utf-8"))
    # Use tables with explicit stop codons ('*' markers).
    table_rows = []
    skipped_no_stop: list[int] = []
    for t in tables:
        codons = codons_for_table(t)
        stops = [codons[i] for i, aa in enumerate(t.ncbieaa) if aa == "*"]
        if not stops:
            skipped_no_stop.append(int(t.code_id))
            continue
        table_rows.append({"code_id": int(t.code_id), "name": t.primary_name(), "stops": stops})

    encs = all_encodings()
    N = 64
    K_boundary = 6  # fixed size of Fold_6 boundary preimage set

    results = []
    for mu in encs:
        p_list = []
        hits_total = 0
        stops_total = 0
        for tr in table_rows:
            stops = tr["stops"]
            n_stop = len(stops)
            k_obs = 0
            for c in stops:
                w = str(fold_codon(str(c), mu).w)
                if is_boundary_word(w):
                    k_obs += 1
            hits_total += int(k_obs)
            stops_total += int(n_stop)
            p = _hypergeom_tail_p(N=N, K=K_boundary, n=int(n_stop), k=int(k_obs))
            # Avoid log(0) in Fisher score (should not occur for valid params, but be safe).
            p_list.append(max(1e-300, float(p)))

        fisher_stat = -2.0 * sum(math.log(p) for p in p_list)
        results.append(
            {
                "mu": encoding_to_str(mu),
                "is_mu_star": bool(_is_mu_star(mu)),
                "fisher_stat": float(fisher_stat),
                "mean_hit_per_table": float(hits_total) / float(len(table_rows)) if table_rows else 0.0,
                "mean_hit_per_stop": float(hits_total) / float(stops_total) if stops_total > 0 else 0.0,
            }
        )

    # Rank by Fisher statistic (larger => more enrichment).
    results_sorted = sorted(results, key=lambda r: float(r["fisher_stat"]), reverse=True)
    mu_star_rank = None
    for i, r in enumerate(results_sorted, start=1):
        if bool(r["is_mu_star"]):
            mu_star_rank = i
            break
    if mu_star_rank is None:
        raise AssertionError("μ* missing from encoding list")
    p_enc = float(mu_star_rank) / 24.0  # conservative tail probability under uniform encoding prior

    top5 = results_sorted[:5]
    mu_star_row = next(r for r in results_sorted if bool(r["is_mu_star"]))

    # LaTeX
    tex = []
    tex.append(
        "Nonstandard-code meta-analysis (NCBI \\path{gc.prt})."
        f" Tables with explicit stop codons: {len(table_rows)}/{len(tables)}."
        " For each encoding $\\mu$ we compute per-table hypergeometric enrichment p-values for stop boundary-hits"
        " (boundary preimage size $6$ of $64$ codons) and combine them with Fisher's statistic."
        f" Among the $24$ encodings, $\\mu^\\ast$ ranks {mu_star_rank}/24 by Fisher score (encoding-null $p={p_enc:.4f}$)."
        f" For $\\mu^\\ast$, mean boundary-hit per table = {mu_star_row['mean_hit_per_table']:.4f},"
        f" mean boundary-hit per stop codon = {mu_star_row['mean_hit_per_stop']:.4f}."
    )
    tex.append(r"\begin{center}")
    tex.append(r"\small")
    tex.append(r"\setlength{\tabcolsep}{6pt}")
    tex.append(r"\renewcommand{\arraystretch}{1.15}")
    tex.append(r"\begin{tabular}{rllrr}")
    tex.append(r"\toprule")
    tex.append(r"rank & $A,C,G,U$ bits & tag & Fisher score & mean-hit/table \\")
    tex.append(r"\midrule")
    for i, r in enumerate(top5, start=1):
        tag = r"$\mu^\ast$" if bool(r["is_mu_star"]) else "-"
        tex.append(
            f"{i} & \\texttt{{{r['mu']}}} & {tag} & {float(r['fisher_stat']):.2f} & {float(r['mean_hit_per_table']):.4f} \\\\"
        )
    tex.append(r"\bottomrule")
    tex.append(r"\end{tabular}")
    tex.append(r"\end{center}")
    latex = "\n".join(tex)

    obj = {
        "ok": True,
        "analysis_version": ANALYSIS_VERSION,
        "n_tables_total": len(tables),
        "n_tables_used": len(table_rows),
        "tables_skipped_no_stop": sorted(skipped_no_stop),
        "mu_star_rank": int(mu_star_rank),
        "p_encoding_null": float(p_enc),
        "results": results,
        "top5": top5,
        "mu_star": mu_star_row,
        "latex": latex,
    }
    write_json_atomic(out_json, obj)
    write_json_atomic(cache_meta_path(out_json), expected_meta)
    write_text(out_tex, latex + "\n")
    print(f"Wrote: {out_tex}")
    print(f"Wrote: {out_json}")


if __name__ == "__main__":
    main()

