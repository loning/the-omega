# -*- coding: utf-8 -*-
"""
H2-1: Cross-domain stop-context replication at scale.

This experiment tests whether the stop-codon Uplift signal replicates across
multiple species from different domains (Eukarya, Bacteria, Archaea).

Endpoints:
- U_after(s;k) and D(s;k) = U_after - U_before for s∈{UAA,UAG,UGA}, k∈{3,5,10,20}
- Composition controls: GC + dinucleotide matching
- Effect sizes + CIs + heterogeneity (random-effects meta-analysis)

Output:
- Per-species JSON summary
- Meta-analysis LaTeX fragment
- Cross-species comparison tables

Usage:
    python scripts/exp_cross_species_stop_context.py --k 10 --force
    python scripts/exp_cross_species_stop_context.py --species yeast,ecoli --k 10
    python scripts/exp_cross_species_stop_context.py --domain eukarya --k 3,5,10,20
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from genetic_code_tools import fold_codon
from cache_manager import write_json_atomic, write_text_atomic
from stats_tools import cohen_d, summarize_mean_diff

# μ* encoding (unique optimal under boundary-hit objective)
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def data_root() -> Path:
    return root_dir() / "data"


def generated_dir() -> Path:
    return root_dir() / "sections" / "generated"


# Stop codons
STOP_CODONS = {"UAA", "UAG", "UGA"}


@dataclass
class StopContext:
    """Context around a stop codon."""
    stop_codon: str
    before_seq: str  # k nucleotides before stop
    after_seq: str   # k nucleotides after stop (including stop)
    u_before: float  # Uplift sum for before window
    u_after: float   # Uplift sum for after window
    gc_before: float # GC content of before window
    gc_after: float  # GC content of after window


def compute_uplift(seq: str) -> float:
    """Compute Uplift sum for a sequence using Fold_6 under μ*."""
    total = 0.0
    for i in range(0, len(seq) - 2, 3):
        codon = seq[i:i+3]
        if len(codon) == 3 and all(c in "ACGU" for c in codon):
            fold = fold_codon(codon, MU_STAR)
            total += fold.delta
    return total


def gc_content(seq: str) -> float:
    """Compute GC content of a sequence."""
    if not seq:
        return 0.0
    gc = sum(1 for c in seq if c in "GC")
    return gc / len(seq)


def parse_cds_fasta(path: Path) -> Iterator[tuple[str, str]]:
    """Parse CDS FASTA file, yielding (header, sequence) pairs."""
    opener = gzip.open if str(path).endswith(".gz") else open
    header = ""
    seq_parts: list[str] = []
    
    with opener(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header and seq_parts:
                    yield header, "".join(seq_parts)
                header = line[1:]
                seq_parts = []
            else:
                seq_parts.append(line.upper())
        
        if header and seq_parts:
            yield header, "".join(seq_parts)


def extract_stop_contexts(
    cds_seq: str,
    k: int,
    translation_table: int = 1,
) -> list[StopContext]:
    """Extract stop codon contexts from a CDS sequence.
    
    Note: CDS FASTA files typically end at the stop codon without downstream UTR.
    We compute:
    - before_seq: k nucleotides upstream of stop (coding region)
    - after_seq: the stop codon + up to k nucleotides (may be shorter or just stop)
    """
    # Normalize to RNA
    seq = cds_seq.replace("T", "U")
    
    # Minimum length check: need at least start + k codons + stop
    if len(seq) < k + 3:
        return []
    
    # Find the stop codon at the end
    stop_start = len(seq) - 3
    stop_codon = seq[stop_start:stop_start + 3]
    
    if stop_codon not in STOP_CODONS:
        return []
    
    # Extract before window (k nucleotides upstream of stop)
    before_start = stop_start - k
    if before_start < 0:
        return []
    
    before_seq = seq[before_start:stop_start]
    
    # For CDS, "after" is just the stop codon (no downstream UTR available)
    # We include what's available up to k nucleotides after stop_start
    after_end = min(stop_start + 3 + k, len(seq))
    after_seq = seq[stop_start:after_end]
    
    # Validate before sequence (no ambiguous bases)
    if not all(c in "ACGU" for c in before_seq):
        return []
    
    # Compute Uplift for before window (this is the main signal)
    u_before = compute_uplift(before_seq)
    
    # For after, compute only for the stop codon portion we have
    # (In CDS, after_seq is typically just the 3-nt stop codon)
    u_after = compute_uplift(after_seq) if len(after_seq) >= 3 else 0.0
    
    return [StopContext(
        stop_codon=stop_codon,
        before_seq=before_seq,
        after_seq=after_seq,
        u_before=u_before,
        u_after=u_after,
        gc_before=gc_content(before_seq),
        gc_after=gc_content(after_seq),
    )]


def analyze_species(
    species_dir: Path,
    k: int,
    max_records: int | None = None,
) -> dict[str, Any] | None:
    """Analyze stop-context Uplift for a single species."""
    meta_path = species_dir / "metadata.json"
    cds_path = species_dir / "cds_from_genomic.fna.gz"
    
    if not meta_path.exists() or not cds_path.exists():
        return None
    
    metadata = json.loads(meta_path.read_text())
    tt = metadata.get("translation_table", 1)
    
    # Collect contexts by stop codon
    contexts_by_stop: dict[str, list[StopContext]] = defaultdict(list)
    n_records = 0
    n_valid = 0
    
    for header, seq in parse_cds_fasta(cds_path):
        n_records += 1
        if max_records and n_records > max_records:
            break
        
        contexts = extract_stop_contexts(seq, k, translation_table=tt)
        for ctx in contexts:
            contexts_by_stop[ctx.stop_codon].append(ctx)
            n_valid += 1
    
    if n_valid == 0:
        return None
    
    # Compute statistics per stop codon
    stop_stats: dict[str, dict[str, Any]] = {}
    
    for stop in STOP_CODONS:
        ctxs = contexts_by_stop.get(stop, [])
        if not ctxs:
            continue
        
        u_before_vals = [c.u_before for c in ctxs]
        u_after_vals = [c.u_after for c in ctxs]
        u_diff_vals = [c.u_after - c.u_before for c in ctxs]
        gc_before_vals = [c.gc_before for c in ctxs]
        gc_after_vals = [c.gc_after for c in ctxs]
        
        n = len(ctxs)
        
        stop_stats[stop] = {
            "n": n,
            "u_before_mean": sum(u_before_vals) / n,
            "u_before_std": math.sqrt(sum((x - sum(u_before_vals)/n)**2 for x in u_before_vals) / n) if n > 1 else 0,
            "u_after_mean": sum(u_after_vals) / n,
            "u_after_std": math.sqrt(sum((x - sum(u_after_vals)/n)**2 for x in u_after_vals) / n) if n > 1 else 0,
            "u_diff_mean": sum(u_diff_vals) / n,
            "u_diff_std": math.sqrt(sum((x - sum(u_diff_vals)/n)**2 for x in u_diff_vals) / n) if n > 1 else 0,
            "gc_before_mean": sum(gc_before_vals) / n,
            "gc_after_mean": sum(gc_after_vals) / n,
        }
    
    # Pairwise comparisons (UAA vs UGA, etc.)
    pairwise: dict[str, dict[str, Any]] = {}
    stop_pairs = [("UAA", "UGA"), ("UAA", "UAG"), ("UAG", "UGA")]
    
    for s1, s2 in stop_pairs:
        if s1 not in stop_stats or s2 not in stop_stats:
            continue
        
        ctxs1 = contexts_by_stop.get(s1, [])
        ctxs2 = contexts_by_stop.get(s2, [])
        
        if len(ctxs1) < 10 or len(ctxs2) < 10:
            continue
        
        # Compare U_before (upstream coding context - available in CDS FASTA)
        vals1 = [c.u_before for c in ctxs1]
        vals2 = [c.u_before for c in ctxs2]
        
        summary = summarize_mean_diff(vals1, vals2)
        d = cohen_d(vals1, vals2)
        
        # Determine significance: CI excludes 0 = significant
        is_sig = False
        if summary and summary.ci_low is not None and summary.ci_high is not None:
            is_sig = (summary.ci_low > 0) or (summary.ci_high < 0)
        
        pairwise[f"{s1}_vs_{s2}"] = {
            "n1": len(vals1),
            "n2": len(vals2),
            "mean1": sum(vals1) / len(vals1),
            "mean2": sum(vals2) / len(vals2),
            "diff": summary.diff if summary else 0.0,
            "ci_low": summary.ci_low if summary else None,
            "ci_high": summary.ci_high if summary else None,
            "significant": is_sig,
            "cohens_d": d if d is not None else 0.0,
        }
    
    return {
        "species": metadata.get("short_name"),
        "scientific_name": metadata.get("scientific_name"),
        "domain": metadata.get("domain"),
        "translation_table": tt,
        "k": k,
        "n_records": n_records,
        "n_valid_stops": n_valid,
        "stop_stats": stop_stats,
        "pairwise_comparisons": pairwise,
    }


def random_effects_meta(
    species_results: list[dict[str, Any]],
    comparison_key: str,
) -> dict[str, Any]:
    """
    Perform random-effects meta-analysis on a pairwise comparison across species.
    Uses DerSimonian-Laird estimator for between-study variance.
    """
    effects: list[tuple[float, float, int, int, str]] = []  # (effect, se, n1, n2, species)
    
    for result in species_results:
        comp = result.get("pairwise_comparisons", {}).get(comparison_key)
        if not comp:
            continue
        
        n1 = comp["n1"]
        n2 = comp["n2"]
        if n1 < 10 or n2 < 10:
            continue
        
        # Effect size (Cohen's d)
        d = comp.get("cohens_d", 0)
        
        # SE of Cohen's d (approximation)
        se = math.sqrt((n1 + n2) / (n1 * n2) + d**2 / (2 * (n1 + n2)))
        
        effects.append((d, se, n1, n2, result.get("species", "")))
    
    if len(effects) < 2:
        return {"n_studies": len(effects), "insufficient_data": True}
    
    # Fixed-effect weights
    weights = [1 / (se**2) for (d, se, _, _, _) in effects]
    total_weight = sum(weights)
    
    # Fixed-effect estimate
    fe_effect = sum(w * d for (d, se, _, _, _), w in zip(effects, weights)) / total_weight
    
    # Q statistic for heterogeneity
    Q = sum(w * (d - fe_effect)**2 for (d, se, _, _, _), w in zip(effects, weights))
    df = len(effects) - 1
    
    # Between-study variance (DerSimonian-Laird)
    c = total_weight - sum(w**2 for w in weights) / total_weight
    tau2 = max(0, (Q - df) / c) if c > 0 else 0
    
    # Random-effects weights
    re_weights = [1 / (se**2 + tau2) for (d, se, _, _, _) in effects]
    re_total = sum(re_weights)
    
    # Random-effects estimate
    re_effect = sum(w * d for (d, se, _, _, _), w in zip(effects, re_weights)) / re_total
    re_se = math.sqrt(1 / re_total)
    
    # 95% CI
    ci_low = re_effect - 1.96 * re_se
    ci_high = re_effect + 1.96 * re_se
    
    # I² heterogeneity
    I2 = max(0, (Q - df) / Q) if Q > 0 else 0
    
    return {
        "n_studies": len(effects),
        "comparison": comparison_key,
        "fixed_effect": fe_effect,
        "random_effect": re_effect,
        "random_effect_se": re_se,
        "ci_95_low": ci_low,
        "ci_95_high": ci_high,
        "tau2": tau2,
        "Q": Q,
        "I2": I2,
        "I2_percent": I2 * 100,
        "per_species": [
            {"species": sp, "effect": d, "se": se, "n1": n1, "n2": n2}
            for (d, se, n1, n2, sp) in effects
        ],
    }


def generate_latex_summary(
    results: list[dict[str, Any]],
    meta_results: dict[str, dict[str, Any]],
    k: int,
) -> str:
    """Generate LaTeX summary table."""
    lines = [
        f"% Cross-species stop-context analysis (k={k})",
        f"% Generated by exp_cross_species_stop_context.py",
        f"% Note: Using U_before (upstream coding context) since CDS FASTA lacks downstream UTR",
        "",
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Cross-species stop-context Uplift replication (k=" + str(k) + r", upstream window)}",
        r"\label{tab:cross_species_stop_context}",
        r"\begin{tabular}{llrrrrr}",
        r"\toprule",
        r"Species & Domain & $n$ & $\bar{U}_{\mathrm{before}}^{\mathrm{UAA}}$ & $\bar{U}_{\mathrm{before}}^{\mathrm{UGA}}$ & $\Delta$ & $d$ \\",
        r"\midrule",
    ]
    
    for result in sorted(results, key=lambda r: (r.get("domain", ""), r.get("species", ""))):
        species = result.get("species", "")[:12]
        domain = result.get("domain", "")[:3].capitalize()
        n = result.get("n_valid_stops", 0)
        
        uaa_stats = result.get("stop_stats", {}).get("UAA", {})
        uga_stats = result.get("stop_stats", {}).get("UGA", {})
        
        uaa_mean = uaa_stats.get("u_before_mean", 0)
        uga_mean = uga_stats.get("u_before_mean", 0)
        
        comp = result.get("pairwise_comparisons", {}).get("UAA_vs_UGA", {})
        diff = comp.get("diff", uaa_mean - uga_mean)
        d = comp.get("cohens_d", 0)
        
        lines.append(
            f"{species} & {domain} & {n:,} & {uaa_mean:.2f} & {uga_mean:.2f} & {diff:+.2f} & {d:+.2f} \\\\"
        )
    
    lines.extend([
        r"\midrule",
    ])
    
    # Add meta-analysis summary
    meta = meta_results.get("UAA_vs_UGA", {})
    if not meta.get("insufficient_data"):
        re = meta.get("random_effect", 0)
        ci_lo = meta.get("ci_95_low", 0)
        ci_hi = meta.get("ci_95_high", 0)
        i2 = meta.get("I2_percent", 0)
        n_studies = meta.get("n_studies", 0)
        
        lines.append(
            f"\\textbf{{Meta}} & ({n_studies}) & -- & -- & -- & -- & "
            f"{re:+.2f} [{ci_lo:.2f}, {ci_hi:.2f}] \\\\"
        )
        lines.append(f"\\multicolumn{{7}}{{l}}{{$I^2 = {i2:.1f}\\%$}} \\\\")
    
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])
    
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="H2-1: Cross-species stop-context analysis")
    parser.add_argument("--k", default="10", help="Window size(s), comma-separated")
    parser.add_argument("--species", help="Specific species to analyze (comma-separated)")
    parser.add_argument("--domain", help="Analyze only species from this domain")
    parser.add_argument("--max-records", type=int, help="Max CDS records per species")
    parser.add_argument("--force", action="store_true", help="Overwrite existing results")
    args = parser.parse_args()
    
    k_values = [int(x.strip()) for x in args.k.split(",")]
    
    # Find available species
    corpora_dir = data_root() / "corpora"
    if not corpora_dir.exists():
        print("No corpora directory found. Run fetch_multispecies_cds.py first.")
        return
    
    species_dirs: list[Path] = []
    for domain in ["eukarya", "bacteria", "archaea"]:
        domain_dir = corpora_dir / domain
        if not domain_dir.exists():
            continue
        if args.domain and args.domain != domain:
            continue
        for sp_dir in domain_dir.iterdir():
            if sp_dir.is_dir():
                if args.species:
                    allowed = {s.strip() for s in args.species.split(",")}
                    if sp_dir.name not in allowed:
                        continue
                species_dirs.append(sp_dir)
    
    if not species_dirs:
        print("No species found to analyze.")
        return
    
    print(f"Analyzing {len(species_dirs)} species with k={k_values}...")
    
    for k in k_values:
        print(f"\n=== k={k} ===")
        
        results: list[dict[str, Any]] = []
        
        for sp_dir in sorted(species_dirs):
            print(f"  [{sp_dir.parent.name}/{sp_dir.name}]", end=" ", flush=True)
            result = analyze_species(sp_dir, k, max_records=args.max_records)
            if result:
                results.append(result)
                n = result.get("n_valid_stops", 0)
                print(f"n={n}")
            else:
                print("skipped")
        
        if not results:
            print("  No valid results.")
            continue
        
        # Meta-analysis
        meta_results: dict[str, dict[str, Any]] = {}
        for comp_key in ["UAA_vs_UGA", "UAA_vs_UAG", "UAG_vs_UGA"]:
            meta_results[comp_key] = random_effects_meta(results, comp_key)
        
        # Generate outputs
        summary = {
            "k": k,
            "n_species": len(results),
            "species_results": results,
            "meta_analysis": meta_results,
        }
        
        # Write JSON
        out_json = data_root() / "_cache" / f"cross_species_stop_context_k{k}.json"
        out_json.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(out_json, summary)
        print(f"  Wrote: {out_json.relative_to(root_dir())}")
        
        # Write LaTeX
        latex = generate_latex_summary(results, meta_results, k)
        out_tex = generated_dir() / f"cross_species_stop_context_k{k}.tex"
        write_text_atomic(out_tex, latex)
        print(f"  Wrote: {out_tex.relative_to(root_dir())}")
        
        # Print summary
        meta_uaa_uga = meta_results.get("UAA_vs_UGA", {})
        if not meta_uaa_uga.get("insufficient_data"):
            re = meta_uaa_uga.get("random_effect", 0)
            ci = (meta_uaa_uga.get("ci_95_low", 0), meta_uaa_uga.get("ci_95_high", 0))
            i2 = meta_uaa_uga.get("I2_percent", 0)
            print(f"\n  Meta-analysis (UAA vs UGA):")
            print(f"    Random-effect d = {re:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]")
            print(f"    Heterogeneity I² = {i2:.1f}%")


if __name__ == "__main__":
    main()
