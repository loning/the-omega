#!/usr/bin/env python3
"""
exp_loso_generalization.py - H2-2: Leave-One-Species-Out generalization test

Tests whether the stop-context Uplift signal generalizes across species by:
1. Training on N-1 species
2. Testing on held-out species
3. Checking sign consistency and effect size preservation
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

# Local imports
sys.path.insert(0, str(Path(__file__).parent))
from genetic_code_tools import fold_codon
from stats_tools import cohen_d
from cache_manager import write_json_atomic


# μ* encoding
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
MU_STAR_INT = {"A": 0, "C": 1, "G": 2, "U": 3}


def data_root() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def compute_uplift(codon: str) -> int:
    """Compute Uplift value for a codon using μ* encoding."""
    val = 0
    for base in codon:
        val = (val << 2) | MU_STAR_INT.get(base, 0)
    return val


def parse_orf_from_cds(seq: str) -> list[str]:
    """Parse a CDS sequence into codons."""
    seq = seq.upper().replace("T", "U")
    seq = "".join(c for c in seq if c in "ACGU")
    if len(seq) % 3 != 0:
        seq = seq[:-(len(seq) % 3)]
    return [seq[i:i+3] for i in range(0, len(seq), 3)]


def compute_window_uplift(codons: list[str], k: int) -> float:
    """Compute mean Uplift for k codons before stop."""
    window = codons[-(k + 1):-1] if len(codons) > k else codons[:-1]
    if not window:
        return np.nan
    return np.mean([compute_uplift(c) for c in window])


def load_species_data(species_dir: Path, k: int, max_records: int = 0) -> dict[str, list[float]]:
    """Load Uplift values per stop codon for a species."""
    metadata_path = species_dir / "metadata.json"
    cds_path = species_dir / "cds_from_genomic.fna.gz"
    if not cds_path.exists():
        cds_path = species_dir / "cds.fasta.gz"
    
    if not metadata_path.exists() or not cds_path.exists():
        return {}
    
    results: dict[str, list[float]] = {"UAA": [], "UAG": [], "UGA": []}
    count = 0
    
    with gzip.open(cds_path, "rt") as f:
        current_seq = []
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if current_seq:
                    seq = "".join(current_seq)
                    codons = parse_orf_from_cds(seq)
                    if codons and len(codons) >= k + 2:
                        stop = codons[-1]
                        if stop in results:
                            u = compute_window_uplift(codons, k)
                            if not np.isnan(u):
                                results[stop].append(u)
                                count += 1
                                if max_records > 0 and count >= max_records:
                                    return results
                current_seq = []
            else:
                current_seq.append(line)
        
        # Process last sequence
        if current_seq:
            seq = "".join(current_seq)
            codons = parse_orf_from_cds(seq)
            if codons and len(codons) >= k + 2:
                stop = codons[-1]
                if stop in results:
                    u = compute_window_uplift(codons, k)
                    if not np.isnan(u):
                        results[stop].append(u)
    
    return results


def loso_analysis(
    species_data: dict[str, dict[str, list[float]]],
    comparison: tuple[str, str] = ("UAA", "UGA"),
) -> list[dict[str, Any]]:
    """Perform Leave-One-Species-Out analysis."""
    stop_a, stop_b = comparison
    species_list = list(species_data.keys())
    results = []
    
    for held_out in species_list:
        # Training set: all species except held_out
        train_a, train_b = [], []
        for sp in species_list:
            if sp != held_out:
                train_a.extend(species_data[sp].get(stop_a, []))
                train_b.extend(species_data[sp].get(stop_b, []))
        
        if len(train_a) < 100 or len(train_b) < 100:
            continue
        
        # Training statistics
        train_mean_diff = np.mean(train_a) - np.mean(train_b)
        train_d = cohen_d(train_a, train_b) or np.nan
        
        # Test on held-out species
        test_a = species_data[held_out].get(stop_a, [])
        test_b = species_data[held_out].get(stop_b, [])
        
        if len(test_a) < 30 or len(test_b) < 30:
            continue
        
        test_mean_diff = np.mean(test_a) - np.mean(test_b)
        test_d = cohen_d(test_a, test_b) or np.nan
        
        # Sign consistency
        sign_consistent = (train_mean_diff * test_mean_diff) > 0
        
        results.append({
            "held_out": held_out,
            "n_train_a": len(train_a),
            "n_train_b": len(train_b),
            "train_mean_diff": float(train_mean_diff),
            "train_d": float(train_d) if not np.isnan(train_d) else None,
            "n_test_a": len(test_a),
            "n_test_b": len(test_b),
            "test_mean_diff": float(test_mean_diff),
            "test_d": float(test_d) if not np.isnan(test_d) else None,
            "sign_consistent": bool(sign_consistent),
        })
    
    return results


def generate_latex_table(results: list[dict[str, Any]], comparison: tuple[str, str], k: int) -> str:
    """Generate LaTeX table for LOSO results."""
    stop_a, stop_b = comparison
    
    lines = [
        f"% LOSO generalization analysis ({stop_a} vs {stop_b}, k={k})",
        "% Generated by exp_loso_generalization.py",
        "",
        "\\begin{table}[htbp]",
        "\\centering",
        f"\\caption{{Leave-One-Species-Out generalization ({stop_a} vs {stop_b}, k={k})}}",
        "\\label{tab:loso_generalization}",
        "\\begin{tabular}{lrrrrrr}",
        "\\toprule",
        f"Held-out & $n_{{\\mathrm{{train}}}}$ & $d_{{\\mathrm{{train}}}}$ & $n_{{\\mathrm{{test}}}}$ & $d_{{\\mathrm{{test}}}}$ & Sign \\\\",
        "\\midrule",
    ]
    
    n_consistent = 0
    for r in results:
        sign_str = "\\checkmark" if r["sign_consistent"] else "$\\times$"
        if r["sign_consistent"]:
            n_consistent += 1
        
        train_d_str = f"{r['train_d']:.2f}" if r["train_d"] is not None else "--"
        test_d_str = f"{r['test_d']:+.2f}" if r["test_d"] is not None else "--"
        
        lines.append(
            f"{r['held_out'][:12]} & {r['n_train_a']+r['n_train_b']:,} & {train_d_str} & "
            f"{r['n_test_a']+r['n_test_b']:,} & {test_d_str} & {sign_str} \\\\"
        )
    
    # Summary
    lines.append("\\midrule")
    pct_consistent = n_consistent / len(results) * 100 if results else 0
    lines.append(f"\\textbf{{Summary}} & \\multicolumn{{5}}{{l}}{{Sign consistent: {n_consistent}/{len(results)} ({pct_consistent:.0f}\\%)}} \\\\")
    
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ])
    
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="H2-2: LOSO generalization analysis")
    p.add_argument("--k", type=int, default=10, help="Window size")
    p.add_argument("--comparison", type=str, default="UAA,UGA", help="Stop codon comparison (e.g., UAA,UGA)")
    p.add_argument("--max-records", type=int, default=0, help="Max records per species (0=all)")
    args = p.parse_args()
    
    k = args.k
    comparison = tuple(args.comparison.split(","))
    
    # Find all species
    corpora_dir = data_root() / "corpora"
    species_dirs: list[tuple[str, Path]] = []
    
    for domain in ["archaea", "bacteria", "eukarya"]:
        domain_dir = corpora_dir / domain
        if domain_dir.exists():
            for sp_dir in domain_dir.iterdir():
                if sp_dir.is_dir() and (sp_dir / "metadata.json").exists():
                    species_dirs.append((f"{domain}/{sp_dir.name}", sp_dir))
    
    print(f"Loading data from {len(species_dirs)} species (k={k})...")
    
    # Load all species data
    species_data: dict[str, dict[str, list[float]]] = {}
    for sp_name, sp_dir in sorted(species_dirs):
        print(f"  [{sp_name}]", end=" ", flush=True)
        data = load_species_data(sp_dir, k, args.max_records)
        n_total = sum(len(v) for v in data.values())
        if n_total >= 500:
            species_data[sp_name] = data
            print(f"n={n_total}")
        else:
            print("skipped (insufficient data)")
    
    if len(species_data) < 3:
        print("Error: Need at least 3 species for LOSO analysis")
        return
    
    # Run LOSO analysis
    print(f"\nRunning LOSO analysis ({comparison[0]} vs {comparison[1]})...")
    results = loso_analysis(species_data, comparison)
    
    # Save results
    cache_dir = data_root() / "_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = cache_dir / f"loso_generalization_{comparison[0]}_{comparison[1]}_k{k}.json"
    write_json_atomic(output_path, {
        "k": k,
        "comparison": list(comparison),
        "n_species": len(species_data),
        "results": results,
    })
    print(f"\nWrote: {output_path}")
    
    # Generate LaTeX
    gen_dir = Path(__file__).parent.parent / "sections" / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    
    tex_path = gen_dir / f"loso_generalization_{comparison[0]}_{comparison[1]}_k{k}.tex"
    tex_content = generate_latex_table(results, comparison, k)
    tex_path.write_text(tex_content)
    print(f"Wrote: {tex_path}")
    
    # Summary
    if results:
        n_consistent = sum(1 for r in results if r["sign_consistent"])
        print(f"\n=== Summary ===")
        print(f"  Species tested: {len(results)}")
        print(f"  Sign consistent: {n_consistent}/{len(results)} ({n_consistent/len(results)*100:.0f}%)")


if __name__ == "__main__":
    main()
