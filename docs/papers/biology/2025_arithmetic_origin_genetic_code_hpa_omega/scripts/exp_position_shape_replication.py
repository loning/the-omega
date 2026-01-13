#!/usr/bin/env python3
"""
exp_position_shape_replication.py - H2-5: Position-shape replication across species

Tests whether the per-position Uplift curve shape is conserved across species:
1. Compute per-position mean Uplift for positions j=-20 to -1 (before stop)
2. Compare curve shapes across species using correlation
3. Identify universal vs species-specific positional effects
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


def compute_position_curve(
    species_dir: Path,
    max_positions: int = 20,
    max_records: int = 0,
) -> dict[str, Any] | None:
    """Compute per-position mean Uplift curve for a species."""
    metadata_path = species_dir / "metadata.json"
    cds_path = species_dir / "cds_from_genomic.fna.gz"
    if not cds_path.exists():
        cds_path = species_dir / "cds.fasta.gz"
    
    if not metadata_path.exists() or not cds_path.exists():
        return None
    
    # Position data by stop codon: position -> list of Uplift values
    curves: dict[str, dict[int, list[float]]] = {
        "UAA": defaultdict(list),
        "UAG": defaultdict(list),
        "UGA": defaultdict(list),
    }
    count = 0
    
    with gzip.open(cds_path, "rt") as f:
        current_seq = []
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if current_seq:
                    seq = "".join(current_seq)
                    codons = parse_orf_from_cds(seq)
                    if codons and len(codons) >= max_positions + 2:
                        stop = codons[-1]
                        if stop in curves:
                            # Compute Uplift at each position before stop
                            # Position -1 is the codon just before stop
                            for i in range(1, max_positions + 1):
                                pos = -(max_positions + 2) + i  # -max_positions to -1
                                codon_idx = len(codons) - 1 - i
                                if 0 <= codon_idx < len(codons) - 1:
                                    u = compute_uplift(codons[codon_idx])
                                    curves[stop][-i].append(u)
                            count += 1
                            if max_records > 0 and count >= max_records:
                                break
                current_seq = []
            else:
                current_seq.append(line)
        
        # Process last sequence
        if current_seq and (max_records == 0 or count < max_records):
            seq = "".join(current_seq)
            codons = parse_orf_from_cds(seq)
            if codons and len(codons) >= max_positions + 2:
                stop = codons[-1]
                if stop in curves:
                    for i in range(1, max_positions + 1):
                        codon_idx = len(codons) - 1 - i
                        if 0 <= codon_idx < len(codons) - 1:
                            u = compute_uplift(codons[codon_idx])
                            curves[stop][-i].append(u)
    
    if count < 500:
        return None
    
    # Compute mean curves
    result: dict[str, Any] = {
        "species": species_dir.name,
        "domain": species_dir.parent.name,
        "n_orfs": count,
        "curves": {},
    }
    
    for stop in ["UAA", "UAG", "UGA"]:
        positions = sorted(curves[stop].keys())
        means = [np.mean(curves[stop][p]) if curves[stop][p] else np.nan for p in positions]
        sems = [np.std(curves[stop][p]) / np.sqrt(len(curves[stop][p])) if len(curves[stop][p]) > 1 else np.nan for p in positions]
        n_samples = [len(curves[stop][p]) for p in positions]
        
        result["curves"][stop] = {
            "positions": positions,
            "means": [float(m) if not np.isnan(m) else None for m in means],
            "sems": [float(s) if not np.isnan(s) else None for s in sems],
            "n_samples": n_samples,
        }
    
    return result


def compute_curve_similarity(curves_a: list[float], curves_b: list[float]) -> float:
    """Compute Pearson correlation between two Uplift curves."""
    valid = [(a, b) for a, b in zip(curves_a, curves_b) if a is not None and b is not None]
    if len(valid) < 5:
        return np.nan
    a_vals = [v[0] for v in valid]
    b_vals = [v[1] for v in valid]
    r, _ = stats.pearsonr(a_vals, b_vals)
    return float(r)


def generate_latex_summary(all_results: list[dict[str, Any]], max_positions: int) -> str:
    """Generate LaTeX summary of position-shape analysis."""
    lines = [
        f"% Position-shape replication analysis (positions=-{max_positions} to -1)",
        "% Generated by exp_position_shape_replication.py",
        "",
        "\\paragraph{Position-shape replication.}",
        f"We computed per-position mean Uplift at positions $j=-{max_positions}$ to $j=-1$ (codons before stop) across {len(all_results)} species.",
    ]
    
    # Compute pairwise correlations within species (UAA vs UGA curves)
    within_species_r = []
    for r in all_results:
        uaa_means = r["curves"]["UAA"]["means"]
        uga_means = r["curves"]["UGA"]["means"]
        corr = compute_curve_similarity(uaa_means, uga_means)
        if not np.isnan(corr):
            within_species_r.append(corr)
    
    if within_species_r:
        mean_within = np.mean(within_species_r)
        lines.append(f"Within-species UAA--UGA curve correlation: $\\bar{{r}} = {mean_within:.2f}$ (n={len(within_species_r)}).")
    
    # Compute cross-species correlation for UAA curves
    if len(all_results) >= 2:
        cross_species_r = []
        for i, r1 in enumerate(all_results):
            for r2 in all_results[i+1:]:
                corr = compute_curve_similarity(r1["curves"]["UAA"]["means"], r2["curves"]["UAA"]["means"])
                if not np.isnan(corr):
                    cross_species_r.append(corr)
        
        if cross_species_r:
            mean_cross = np.mean(cross_species_r)
            lines.append(f"Cross-species UAA curve correlation: $\\bar{{r}} = {mean_cross:.2f}$ (n={len(cross_species_r)} pairs).")
    
    lines.append("")
    
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="H2-5: Position-shape replication analysis")
    p.add_argument("--max-positions", type=int, default=20, help="Max positions before stop")
    p.add_argument("--max-records", type=int, default=0, help="Max records per species (0=all)")
    args = p.parse_args()
    
    max_positions = args.max_positions
    
    # Find all species
    corpora_dir = data_root() / "corpora"
    species_dirs: list[tuple[str, Path]] = []
    
    for domain in ["archaea", "bacteria", "eukarya"]:
        domain_dir = corpora_dir / domain
        if domain_dir.exists():
            for sp_dir in domain_dir.iterdir():
                if sp_dir.is_dir() and (sp_dir / "metadata.json").exists():
                    species_dirs.append((f"{domain}/{sp_dir.name}", sp_dir))
    
    print(f"Analyzing position curves for {len(species_dirs)} species (positions=-{max_positions} to -1)...")
    
    all_results: list[dict[str, Any]] = []
    for sp_name, sp_dir in sorted(species_dirs):
        print(f"  [{sp_name}]", end=" ", flush=True)
        result = compute_position_curve(sp_dir, max_positions, args.max_records)
        if result:
            all_results.append(result)
            print(f"n={result['n_orfs']}")
        else:
            print("skipped")
    
    # Save results
    cache_dir = data_root() / "_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = cache_dir / f"position_shape_replication_{max_positions}pos.json"
    write_json_atomic(output_path, {
        "max_positions": max_positions,
        "n_species": len(all_results),
        "results": all_results,
    })
    print(f"\nWrote: {output_path}")
    
    # Generate LaTeX summary
    gen_dir = Path(__file__).parent.parent / "sections" / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    
    tex_path = gen_dir / f"position_shape_replication_{max_positions}pos.tex"
    tex_content = generate_latex_summary(all_results, max_positions)
    tex_path.write_text(tex_content)
    print(f"Wrote: {tex_path}")
    
    # Print summary
    if all_results:
        print("\n=== Summary ===")
        # Within-species UAA vs UGA correlation
        within_r = []
        for r in all_results:
            corr = compute_curve_similarity(r["curves"]["UAA"]["means"], r["curves"]["UGA"]["means"])
            if not np.isnan(corr):
                within_r.append(corr)
        if within_r:
            print(f"  Within-species UAA-UGA curve correlation: mean r = {np.mean(within_r):.2f}")
        
        # Cross-species UAA correlation
        if len(all_results) >= 2:
            cross_r = []
            for i, r1 in enumerate(all_results):
                for r2 in all_results[i+1:]:
                    corr = compute_curve_similarity(r1["curves"]["UAA"]["means"], r2["curves"]["UAA"]["means"])
                    if not np.isnan(corr):
                        cross_r.append(corr)
            if cross_r:
                print(f"  Cross-species UAA curve correlation: mean r = {np.mean(cross_r):.2f}")


if __name__ == "__main__":
    main()
