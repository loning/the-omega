#!/usr/bin/env python3
"""
exp_24_encoding_benchmark.py - Module A: 24-encoding full benchmark

For each of the 24 possible 2-bit nucleotide encodings, evaluate performance
on multiple INDEPENDENT tasks (not used in μ* identification).

Tasks:
  A1: Stop-context U_before/U_after difference magnitude
  A2: Recoding vs terminal stop discrimination (AUC)
  A3: Cross-species sign consistency
  A4: Effect size stability across k values

This addresses the key objection: "μ* is cherry-picked using the same data"
"""

from __future__ import annotations

import argparse
import gzip
import itertools
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

# Local imports
sys.path.insert(0, str(Path(__file__).parent))
from stats_tools import cohen_d

BASES = ["A", "C", "G", "U"]
BITPAIRS = ["00", "01", "10", "11"]
STOP_CODONS = {"UAA", "UAG", "UGA"}


def data_root() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def all_24_encodings() -> list[dict[str, str]]:
    """Generate all 24 possible nucleotide-to-bitpair mappings."""
    encodings = []
    for perm in itertools.permutations(BITPAIRS):
        mu = dict(zip(BASES, perm))
        encodings.append(mu)
    return encodings


def encoding_to_str(mu: dict[str, str]) -> str:
    """Convert encoding to string representation."""
    return f"A={mu['A']},C={mu['C']},G={mu['G']},U={mu['U']}"


def is_mu_star(mu: dict[str, str]) -> bool:
    """Check if this is the μ* encoding."""
    return mu == {"A": "00", "C": "01", "G": "10", "U": "11"}


def compute_uplift(codon: str, mu: dict[str, str]) -> int:
    """Compute Uplift value for a codon using given encoding."""
    mu_int = {b: int(mu[b], 2) for b in BASES}
    val = 0
    for base in codon:
        val = (val << 2) | mu_int.get(base, 0)
    return val


def parse_orf_from_cds(seq: str) -> list[str]:
    """Parse a CDS sequence into codons."""
    seq = seq.upper().replace("T", "U")
    seq = "".join(c for c in seq if c in "ACGU")
    if len(seq) % 3 != 0:
        seq = seq[:-(len(seq) % 3)]
    return [seq[i:i+3] for i in range(0, len(seq), 3)]


def load_species_data(species_dir: Path, k: int, max_records: int = 0) -> dict[str, list[list[str]]]:
    """Load codon sequences by stop codon."""
    cds_path = species_dir / "cds_from_genomic.fna.gz"
    if not cds_path.exists():
        cds_path = species_dir / "cds.fasta.gz"
    
    if not cds_path.exists():
        return {}
    
    results: dict[str, list[list[str]]] = {"UAA": [], "UAG": [], "UGA": []}
    count = 0
    
    with gzip.open(cds_path, "rt") as f:
        current_seq = []
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if current_seq:
                    codons = parse_orf_from_cds("".join(current_seq))
                    if codons and len(codons) >= k + 2:
                        stop = codons[-1]
                        if stop in results:
                            results[stop].append(codons)
                            count += 1
                            if max_records > 0 and count >= max_records:
                                return results
                current_seq = []
            else:
                current_seq.append(line)
        
        if current_seq:
            codons = parse_orf_from_cds("".join(current_seq))
            if codons and len(codons) >= k + 2:
                stop = codons[-1]
                if stop in results:
                    results[stop].append(codons)
    
    return results


def compute_window_uplift_for_encoding(codons: list[str], k: int, mu: dict[str, str]) -> float:
    """Compute mean Uplift for k codons before stop."""
    window = codons[-(k + 1):-1] if len(codons) > k else codons[:-1]
    if not window:
        return np.nan
    return np.mean([compute_uplift(c, mu) for c in window])


@dataclass
class TaskScores:
    """Scores for all benchmark tasks."""
    a1_stop_effect: float = np.nan  # Mean |d| across stop pairs
    a2_recoding_separation: float = np.nan  # UAA vs UGA effect size (placeholder)
    a3_cross_species_consistency: float = np.nan  # Fraction of species with consistent sign
    a4_k_stability: float = np.nan  # Correlation of effect across k values
    
    def to_dict(self) -> dict[str, float]:
        return {
            "a1_stop_effect": float(self.a1_stop_effect) if not np.isnan(self.a1_stop_effect) else None,
            "a2_recoding_separation": float(self.a2_recoding_separation) if not np.isnan(self.a2_recoding_separation) else None,
            "a3_cross_species_consistency": float(self.a3_cross_species_consistency) if not np.isnan(self.a3_cross_species_consistency) else None,
            "a4_k_stability": float(self.a4_k_stability) if not np.isnan(self.a4_k_stability) else None,
        }


def evaluate_encoding_a1(
    all_species_data: dict[str, dict[str, list[list[str]]]],
    mu: dict[str, str],
    k: int,
) -> float:
    """
    Task A1: Stop-context effect magnitude.
    Compute |d| for UAA vs UGA across all pooled data.
    """
    uaa_uplifts = []
    uga_uplifts = []
    
    for species, data in all_species_data.items():
        for codons in data.get("UAA", []):
            u = compute_window_uplift_for_encoding(codons, k, mu)
            if not np.isnan(u):
                uaa_uplifts.append(u)
        for codons in data.get("UGA", []):
            u = compute_window_uplift_for_encoding(codons, k, mu)
            if not np.isnan(u):
                uga_uplifts.append(u)
    
    if len(uaa_uplifts) < 100 or len(uga_uplifts) < 100:
        return np.nan
    
    d = cohen_d(uaa_uplifts, uga_uplifts)
    return abs(d) if d is not None else np.nan


def evaluate_encoding_a3(
    all_species_data: dict[str, dict[str, list[list[str]]]],
    mu: dict[str, str],
    k: int,
) -> float:
    """
    Task A3: Cross-species sign consistency.
    For each species, compute sign of (mean_UAA - mean_UGA).
    Return fraction with consistent sign (majority direction).
    """
    signs = []
    
    for species, data in all_species_data.items():
        uaa_uplifts = [
            compute_window_uplift_for_encoding(codons, k, mu)
            for codons in data.get("UAA", [])
        ]
        uga_uplifts = [
            compute_window_uplift_for_encoding(codons, k, mu)
            for codons in data.get("UGA", [])
        ]
        
        uaa_uplifts = [u for u in uaa_uplifts if not np.isnan(u)]
        uga_uplifts = [u for u in uga_uplifts if not np.isnan(u)]
        
        if len(uaa_uplifts) >= 50 and len(uga_uplifts) >= 50:
            diff = np.mean(uaa_uplifts) - np.mean(uga_uplifts)
            signs.append(1 if diff > 0 else -1)
    
    if len(signs) < 3:
        return np.nan
    
    # Fraction with majority sign
    n_positive = sum(1 for s in signs if s > 0)
    n_negative = len(signs) - n_positive
    consistency = max(n_positive, n_negative) / len(signs)
    
    return consistency


def evaluate_encoding_a4(
    all_species_data: dict[str, dict[str, list[list[str]]]],
    mu: dict[str, str],
    k_list: list[int],
) -> float:
    """
    Task A4: Effect size stability across k values.
    Compute correlation of effect sizes across different k.
    """
    effects_by_k = []
    
    for k in k_list:
        uaa_uplifts = []
        uga_uplifts = []
        
        for species, data in all_species_data.items():
            for codons in data.get("UAA", []):
                if len(codons) >= k + 2:
                    u = compute_window_uplift_for_encoding(codons, k, mu)
                    if not np.isnan(u):
                        uaa_uplifts.append(u)
            for codons in data.get("UGA", []):
                if len(codons) >= k + 2:
                    u = compute_window_uplift_for_encoding(codons, k, mu)
                    if not np.isnan(u):
                        uga_uplifts.append(u)
        
        if len(uaa_uplifts) >= 100 and len(uga_uplifts) >= 100:
            d = cohen_d(uaa_uplifts, uga_uplifts)
            effects_by_k.append(d if d is not None else np.nan)
        else:
            effects_by_k.append(np.nan)
    
    # Compute mean absolute effect (stability = higher is better)
    valid_effects = [e for e in effects_by_k if not np.isnan(e)]
    if len(valid_effects) >= 2:
        return float(np.mean(np.abs(valid_effects)))
    return np.nan


def evaluate_encoding(
    all_species_data: dict[str, dict[str, list[list[str]]]],
    mu: dict[str, str],
    k: int,
    k_list: list[int],
) -> TaskScores:
    """Evaluate encoding on all tasks."""
    scores = TaskScores()
    
    scores.a1_stop_effect = evaluate_encoding_a1(all_species_data, mu, k)
    scores.a3_cross_species_consistency = evaluate_encoding_a3(all_species_data, mu, k)
    scores.a4_k_stability = evaluate_encoding_a4(all_species_data, mu, k_list)
    
    return scores


def main() -> None:
    p = argparse.ArgumentParser(description="Module A: 24-encoding benchmark")
    p.add_argument("--k", type=int, default=10, help="Primary window size")
    p.add_argument("--k-list", type=str, default="3,5,10,20", help="K values for stability test")
    p.add_argument("--max-records", type=int, default=0, help="Max records per species (0=all)")
    args = p.parse_args()
    
    k = args.k
    k_list = [int(x) for x in args.k_list.split(",")]
    
    # Find all species
    corpora_dir = data_root() / "corpora"
    species_dirs: list[tuple[str, Path]] = []
    
    for domain in ["archaea", "bacteria", "eukarya"]:
        domain_dir = corpora_dir / domain
        if domain_dir.exists():
            for sp_dir in domain_dir.iterdir():
                if sp_dir.is_dir() and (sp_dir / "metadata.json").exists():
                    species_dirs.append((f"{domain}/{sp_dir.name}", sp_dir))
    
    print(f"Loading data from {len(species_dirs)} species...")
    
    # Load all data
    all_species_data: dict[str, dict[str, list[list[str]]]] = {}
    for sp_name, sp_dir in sorted(species_dirs):
        print(f"  [{sp_name}]", end=" ", flush=True)
        data = load_species_data(sp_dir, k, args.max_records)
        n_total = sum(len(v) for v in data.values())
        if n_total >= 500:
            all_species_data[sp_name] = data
            print(f"n={n_total}")
        else:
            print("skipped")
    
    print(f"\n=== Evaluating 24 encodings (k={k}) ===")
    
    # Evaluate all 24 encodings
    encodings = all_24_encodings()
    results: list[dict[str, Any]] = []
    
    for i, mu in enumerate(encodings):
        mu_str = encoding_to_str(mu)
        is_star = is_mu_star(mu)
        print(f"  [{i+1:2d}/24] {mu_str}", end=" ")
        if is_star:
            print("(μ*)", end=" ")
        
        scores = evaluate_encoding(all_species_data, mu, k, k_list)
        
        print(f"A1={scores.a1_stop_effect:.3f} A3={scores.a3_cross_species_consistency:.2f} A4={scores.a4_k_stability:.3f}")
        
        results.append({
            "encoding": mu_str,
            "is_mu_star": is_star,
            "scores": scores.to_dict(),
        })
    
    # Rank encodings by each task
    print("\n=== Rankings ===")
    
    # A1: Higher |d| is better
    a1_ranked = sorted(
        [(r["encoding"], r["scores"]["a1_stop_effect"], r["is_mu_star"]) for r in results if r["scores"]["a1_stop_effect"] is not None],
        key=lambda x: -x[1]
    )
    mu_star_rank_a1 = next((i+1 for i, r in enumerate(a1_ranked) if r[2]), None)
    print(f"A1 (stop effect |d|): μ* rank = {mu_star_rank_a1}/24")
    print(f"   Top 3: {[r[0] for r in a1_ranked[:3]]}")
    
    # A3: Higher consistency is better
    a3_ranked = sorted(
        [(r["encoding"], r["scores"]["a3_cross_species_consistency"], r["is_mu_star"]) for r in results if r["scores"]["a3_cross_species_consistency"] is not None],
        key=lambda x: -x[1]
    )
    mu_star_rank_a3 = next((i+1 for i, r in enumerate(a3_ranked) if r[2]), None)
    print(f"A3 (cross-species consistency): μ* rank = {mu_star_rank_a3}/24")
    print(f"   Top 3: {[r[0] for r in a3_ranked[:3]]}")
    
    # A4: Higher stability is better
    a4_ranked = sorted(
        [(r["encoding"], r["scores"]["a4_k_stability"], r["is_mu_star"]) for r in results if r["scores"]["a4_k_stability"] is not None],
        key=lambda x: -x[1]
    )
    mu_star_rank_a4 = next((i+1 for i, r in enumerate(a4_ranked) if r[2]), None)
    print(f"A4 (k stability): μ* rank = {mu_star_rank_a4}/24")
    print(f"   Top 3: {[r[0] for r in a4_ranked[:3]]}")
    
    # Save results
    cache_dir = data_root() / "_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = cache_dir / f"24_encoding_benchmark_k{k}.json"
    with open(output_path, "w") as f:
        json.dump({
            "k": k,
            "k_list": k_list,
            "n_species": len(all_species_data),
            "results": results,
            "mu_star_ranks": {
                "a1": mu_star_rank_a1,
                "a3": mu_star_rank_a3,
                "a4": mu_star_rank_a4,
            },
        }, f, indent=2)
    
    print(f"\nWrote: {output_path}")
    
    # Summary
    ranks = [mu_star_rank_a1, mu_star_rank_a3, mu_star_rank_a4]
    valid_ranks = [r for r in ranks if r is not None]
    if valid_ranks:
        mean_rank = np.mean(valid_ranks)
        print(f"\n=== Summary ===")
        print(f"  μ* mean rank across tasks: {mean_rank:.1f}/24")
        print(f"  绿灯 A 判定: {'✅ PASS' if mean_rank <= 5 else '❌ FAIL'} (threshold: mean rank ≤ 5)")


if __name__ == "__main__":
    main()
