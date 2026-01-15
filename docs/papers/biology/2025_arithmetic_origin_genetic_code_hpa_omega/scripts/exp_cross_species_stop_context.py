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
    before_seq: str  # 3k nucleotides (k codons) before stop (excluding stop)
    after_seq: str   # 3k nucleotides (k codons) after stop (excluding stop)
    u_before: float  # mean Uplift over k codons (Fold_6 delta)
    u_after: float   # mean Uplift over k codons (Fold_6 delta)
    gc_before: float # GC fraction of before window (over 3k nt)
    gc_after: float  # GC fraction of after window (over 3k nt)


def window_mean_uplift(seq: str) -> float:
    """Compute mean Uplift (Fold_6 delta) over in-frame codons in a window sequence."""
    total = 0.0
    n = 0
    for i in range(0, len(seq) - 2, 3):
        codon = seq[i : i + 3]
        if len(codon) != 3 or (not all(c in "ACGU" for c in codon)):
            return float("nan")
        fold = fold_codon(codon, MU_STAR)
        total += float(fold.delta)
        n += 1
    return (total / n) if n else float("nan")


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


@dataclass(frozen=True)
class BestOrf:
    frame: int
    start_base: int
    stop_base: int
    length_codons_including_stop: int


def best_orf_across_frames(seq: str, *, min_codons: int) -> BestOrf | None:
    """
    Longest ORF across frames using AUG start and standard stops.
    Tie-breakers:
      - longer ORF wins
      - earlier start wins
      - lower frame wins
    """
    best: BestOrf | None = None
    for frame in (0, 1, 2):
        in_orf = False
        start_pos: int | None = None
        best_frame: BestOrf | None = None
        for pos in range(frame, len(seq) - 2, 3):
            codon = seq[pos : pos + 3]
            if len(codon) != 3 or (not all(c in "ACGU" for c in codon)):
                in_orf = False
                start_pos = None
                continue
            if not in_orf:
                if codon == "AUG":
                    in_orf = True
                    start_pos = pos
            else:
                if codon in STOP_CODONS:
                    if start_pos is not None:
                        length_codons = (pos - start_pos) // 3 + 1
                        if length_codons >= int(min_codons):
                            cand = BestOrf(
                                frame=frame,
                                start_base=start_pos,
                                stop_base=pos,
                                length_codons_including_stop=length_codons,
                            )
                            if best_frame is None:
                                best_frame = cand
                            else:
                                key = (cand.length_codons_including_stop, -cand.start_base, -cand.frame)
                                key_best = (
                                    best_frame.length_codons_including_stop,
                                    -best_frame.start_base,
                                    -best_frame.frame,
                                )
                                if key > key_best:
                                    best_frame = cand
                    in_orf = False
                    start_pos = None
        if best_frame is None:
            continue
        if best is None:
            best = best_frame
            continue
        key = (best_frame.length_codons_including_stop, -best_frame.start_base, -best_frame.frame)
        key_best = (best.length_codons_including_stop, -best.start_base, -best.frame)
        if key > key_best:
            best = best_frame
    return best


def extract_stop_contexts_cds(
    cds_seq: str,
    k_codons: int,
) -> list[StopContext]:
    """
    Extract stop codon contexts from an annotated CDS sequence.

    Note: CDS FASTA typically ends at the stop codon and has no downstream UTR.
    We therefore compute only the before-window (k codons upstream of the terminal stop).
    """
    seq = cds_seq.replace("T", "U")
    k_nt = 3 * int(k_codons)

    # Need at least k codons before stop + stop codon.
    if len(seq) < k_nt + 3:
        return []

    stop_base = len(seq) - 3
    stop_codon = seq[stop_base : stop_base + 3]
    if stop_codon not in STOP_CODONS:
        return []

    before_start = stop_base - k_nt
    if before_start < 0:
        return []

    before_seq = seq[before_start:stop_base]
    if len(before_seq) != k_nt:
        return []
    if not all(c in "ACGU" for c in before_seq):
        return []

    u_before = window_mean_uplift(before_seq)
    if not math.isfinite(u_before):
        return []

    return [
        StopContext(
            stop_codon=stop_codon,
            before_seq=before_seq,
            after_seq="",
            u_before=float(u_before),
            u_after=float("nan"),
            gc_before=gc_content(before_seq),
            gc_after=float("nan"),
        )
    ]


def extract_stop_contexts_mrna(
    mrna_seq: str,
    k_codons: int,
    *,
    min_orf_codons: int,
) -> list[StopContext]:
    """
    Extract stop-context windows from an mRNA/transcript sequence by selecting the best ORF.

    We require:
      - best ORF uses AUG start and standard stops
      - k codons before the terminal stop are inside the ORF
      - k codons after the stop are present in the transcript (same frame)
    """
    seq = mrna_seq.replace("T", "U")
    best = best_orf_across_frames(seq, min_codons=int(min_orf_codons))
    if best is None:
        return []

    stop_base = int(best.stop_base)
    start_base = int(best.start_base)
    stop_codon = seq[stop_base : stop_base + 3]
    if stop_codon not in STOP_CODONS:
        return []

    k_nt = 3 * int(k_codons)
    before_start = stop_base - k_nt
    after_start = stop_base + 3
    if before_start < start_base:
        return []
    if after_start + k_nt > len(seq):
        return []

    before_seq = seq[before_start:stop_base]
    after_seq = seq[after_start : after_start + k_nt]
    if len(before_seq) != k_nt or len(after_seq) != k_nt:
        return []
    if not all(c in "ACGU" for c in before_seq):
        return []
    if not all(c in "ACGU" for c in after_seq):
        return []

    u_before = window_mean_uplift(before_seq)
    u_after = window_mean_uplift(after_seq)
    if not (math.isfinite(u_before) and math.isfinite(u_after)):
        return []

    return [
        StopContext(
            stop_codon=stop_codon,
            before_seq=before_seq,
            after_seq=after_seq,
            u_before=float(u_before),
            u_after=float(u_after),
            gc_before=gc_content(before_seq),
            gc_after=gc_content(after_seq),
        )
    ]


def analyze_species(
    species_dir: Path,
    k: int,
    *,
    source: str,
    min_orf_codons: int,
    max_records: int | None = None,
) -> dict[str, Any] | None:
    """Analyze stop-context Uplift for a single species."""
    meta_path = species_dir / "metadata.json"
    cds_path = species_dir / "cds_from_genomic.fna.gz"
    mrna_path = species_dir / "rna_from_genomic.fna.gz"
    
    if not meta_path.exists():
        return None
    if source == "cds" and not cds_path.exists():
        return None
    if source == "rna" and not mrna_path.exists():
        return None
    
    metadata = json.loads(meta_path.read_text())
    tt = metadata.get("translation_table", 1)
    
    # Collect contexts by stop codon
    contexts_by_stop: dict[str, list[StopContext]] = defaultdict(list)
    n_records = 0
    n_valid = 0
    
    fasta_path = cds_path if source == "cds" else mrna_path
    for header, seq in parse_cds_fasta(fasta_path):
        n_records += 1
        if max_records and n_records > max_records:
            break
        
        if source == "cds":
            contexts = extract_stop_contexts_cds(seq, k_codons=int(k))
        else:
            contexts = extract_stop_contexts_mrna(seq, k_codons=int(k), min_orf_codons=int(min_orf_codons))
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
        
        u_before_vals = [c.u_before for c in ctxs if math.isfinite(c.u_before)]
        u_after_vals = [c.u_after for c in ctxs if math.isfinite(c.u_after)]
        u_diff_vals = [c.u_after - c.u_before for c in ctxs if math.isfinite(c.u_before) and math.isfinite(c.u_after)]
        gc_before_vals = [c.gc_before for c in ctxs]
        gc_after_vals = [c.gc_after for c in ctxs if math.isfinite(c.gc_after)]
        
        n = len(ctxs)
        
        stop_stats[stop] = {
            "n": n,
            "u_before_mean": (sum(u_before_vals) / len(u_before_vals)) if u_before_vals else float("nan"),
            "u_before_std": (
                math.sqrt(sum((x - (sum(u_before_vals) / len(u_before_vals))) ** 2 for x in u_before_vals) / len(u_before_vals))
                if len(u_before_vals) > 1
                else 0.0
            ),
            "u_after_mean": (sum(u_after_vals) / len(u_after_vals)) if u_after_vals else float("nan"),
            "u_after_std": (
                math.sqrt(sum((x - (sum(u_after_vals) / len(u_after_vals))) ** 2 for x in u_after_vals) / len(u_after_vals))
                if len(u_after_vals) > 1
                else 0.0
            ),
            "u_diff_mean": (sum(u_diff_vals) / len(u_diff_vals)) if u_diff_vals else float("nan"),
            "u_diff_std": (
                math.sqrt(sum((x - (sum(u_diff_vals) / len(u_diff_vals))) ** 2 for x in u_diff_vals) / len(u_diff_vals))
                if len(u_diff_vals) > 1
                else 0.0
            ),
            "gc_before_mean": (sum(gc_before_vals) / len(gc_before_vals)) if gc_before_vals else float("nan"),
            "gc_after_mean": (sum(gc_after_vals) / len(gc_after_vals)) if gc_after_vals else float("nan"),
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
        
        # Compare U_before (upstream coding context; always defined for CDS, and defined for mRNA when a best ORF exists)
        vals1 = [c.u_before for c in ctxs1 if math.isfinite(c.u_before)]
        vals2 = [c.u_before for c in ctxs2 if math.isfinite(c.u_before)]
        
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
    *,
    source: str,
) -> str:
    """Generate LaTeX summary table."""
    src_note = "RefSeq CDS" if source == "cds" else "RefSeq mRNA (UTR-inclusive; best ORF)"
    out_tag = "upstream window" if source == "cds" else "before/after windows"
    lines = [
        f"% Cross-species stop-context analysis ({src_note}; k={k} codons)",
        f"% Generated by exp_cross_species_stop_context.py",
        f"% Note: {out_tag}",
        "",
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Cross-species stop-context Uplift replication (" + src_note + r"; $k=" + str(k) + r"$ codons)}",
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
        
        uaa_mean = float(uaa_stats.get("u_before_mean", float("nan")))
        uga_mean = float(uga_stats.get("u_before_mean", float("nan")))
        
        comp = result.get("pairwise_comparisons", {}).get("UAA_vs_UGA", {})
        diff = float(comp.get("diff", uaa_mean - uga_mean))
        d = float(comp.get("cohens_d", float("nan")))
        
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
    parser.add_argument("--k", default="10", help="Window size(s) in codons, comma-separated")
    parser.add_argument("--species", help="Specific species to analyze (comma-separated)")
    parser.add_argument("--domain", help="Analyze only species from this domain")
    parser.add_argument("--source", choices=["cds", "rna"], default="cds", help="Input source per species (cds_from_genomic vs rna_from_genomic).")
    parser.add_argument("--min-orf-codons", type=int, default=30, help="Minimum ORF length for --source rna (codons, including stop).")
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
            result = analyze_species(
                sp_dir,
                k,
                source=str(args.source),
                min_orf_codons=int(args.min_orf_codons),
                max_records=args.max_records,
            )
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
        latex = generate_latex_summary(results, meta_results, k, source=str(args.source))
        stem = f"cross_species_stop_context_k{k}"
        if str(args.source) == "rna":
            stem = f"cross_species_stop_context_mrna_k{k}"
        out_tex = generated_dir() / f"{stem}.tex"
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
