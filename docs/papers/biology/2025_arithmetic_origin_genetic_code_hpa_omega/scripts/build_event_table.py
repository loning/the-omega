#!/usr/bin/env python3
"""
build_event_table.py - Unified event table builder for all computational experiments

This script generates a standardized event table (parquet format) that serves as
the foundation for all downstream experiments. Each row represents one biological
event (terminal stop, recoding site, etc.) with all computed features.

Schema:
  - species, gene_id, transcript_id, event_type, stop_codon, pos_i
  - seq_before_k, seq_after_k (for multiple k values)
  - ubefore_k, uafter_k, U_curve_before, U_curve_after
  - gc_before, gc_after, dinuc_before[16], dinuc_after[16]
  - plus optional: mfe_before, mfe_after, pause_score_curve
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import numpy as np

# Local imports
sys.path.insert(0, str(Path(__file__).parent))
from genetic_code_tools import fold_codon

# μ* encoding
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
MU_STAR_INT = {"A": 0, "C": 1, "G": 2, "U": 3}
STOP_CODONS = {"UAA", "UAG", "UGA"}
BASES = ["A", "C", "G", "U"]
DINUCS = [f"{b1}{b2}" for b1 in BASES for b2 in BASES]


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


def gc_fraction(seq: str) -> float:
    """Compute GC fraction of a sequence."""
    if not seq:
        return np.nan
    return sum(1 for c in seq if c in "GC") / len(seq)


def dinuc_vector(seq: str) -> dict[str, float]:
    """Compute normalized dinucleotide frequency vector (16D)."""
    counts = {d: 0 for d in DINUCS}
    total = 0
    for i in range(len(seq) - 1):
        dinuc = seq[i:i+2]
        if dinuc in counts:
            counts[dinuc] += 1
            total += 1
    if total > 0:
        for d in counts:
            counts[d] /= total
    return counts


def compute_uplift_curve(codons: list[str], center_idx: int, k_max: int) -> dict[int, float]:
    """Compute Uplift at each position relative to center."""
    curve = {}
    for offset in range(-k_max, k_max + 1):
        idx = center_idx + offset
        if 0 <= idx < len(codons):
            curve[offset] = compute_uplift(codons[idx])
        else:
            curve[offset] = np.nan
    return curve


def compute_window_stats(codons: list[str], center_idx: int, k: int, direction: str) -> dict[str, Any]:
    """
    Compute window statistics for k codons before or after center.
    
    Args:
        codons: List of codons
        center_idx: Index of the center codon (e.g., stop codon)
        k: Window size in codons
        direction: "before" or "after"
    
    Returns:
        Dictionary with seq, mean_uplift, gc, dinuc_vector
    """
    if direction == "before":
        start = max(0, center_idx - k)
        end = center_idx
    else:  # after
        start = center_idx + 1
        end = min(len(codons), center_idx + 1 + k)
    
    window_codons = codons[start:end]
    if not window_codons:
        return {
            "seq": "",
            "mean_uplift": np.nan,
            "gc": np.nan,
            "dinuc": {d: 0.0 for d in DINUCS},
        }
    
    seq = "".join(window_codons)
    uplifts = [compute_uplift(c) for c in window_codons]
    
    return {
        "seq": seq,
        "mean_uplift": float(np.mean(uplifts)),
        "gc": gc_fraction(seq),
        "dinuc": dinuc_vector(seq),
    }


@dataclass
class EventRecord:
    """Single biological event record."""
    species: str
    domain: str
    gene_id: str = ""
    transcript_id: str = ""
    event_type: str = "terminal_stop"  # terminal_stop, Sec, Pyl, readthrough, PRF
    stop_codon: str = ""
    pos_i: int = 0  # 1-based position in transcript
    orf_length: int = 0
    
    # Window features (computed for multiple k)
    windows: dict[int, dict[str, Any]] = field(default_factory=dict)
    
    # Position-resolved Uplift curve
    uplift_curve: dict[int, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to flat dictionary for parquet/JSON output."""
        d = {
            "species": self.species,
            "domain": self.domain,
            "gene_id": self.gene_id,
            "transcript_id": self.transcript_id,
            "event_type": self.event_type,
            "stop_codon": self.stop_codon,
            "pos_i": self.pos_i,
            "orf_length": self.orf_length,
        }
        
        # Flatten window features
        for k, w in self.windows.items():
            d[f"seq_before_{k}"] = w["before"]["seq"]
            d[f"seq_after_{k}"] = w["after"]["seq"]
            d[f"u_before_{k}"] = w["before"]["mean_uplift"]
            d[f"u_after_{k}"] = w["after"]["mean_uplift"]
            d[f"gc_before_{k}"] = w["before"]["gc"]
            d[f"gc_after_{k}"] = w["after"]["gc"]
            # Flatten dinuc vectors
            for dinuc in DINUCS:
                d[f"dinuc_before_{k}_{dinuc}"] = w["before"]["dinuc"].get(dinuc, 0)
                d[f"dinuc_after_{k}_{dinuc}"] = w["after"]["dinuc"].get(dinuc, 0)
        
        # Store curve as JSON string
        d["uplift_curve"] = json.dumps(self.uplift_curve)
        
        return d


def process_species_cds(
    species_dir: Path,
    k_list: list[int],
    k_max_curve: int = 20,
    max_records: int = 0,
) -> Iterator[EventRecord]:
    """
    Process CDS data for a species and yield event records.
    """
    metadata_path = species_dir / "metadata.json"
    cds_path = species_dir / "cds_from_genomic.fna.gz"
    if not cds_path.exists():
        cds_path = species_dir / "cds.fasta.gz"
    
    if not metadata_path.exists() or not cds_path.exists():
        return
    
    with open(metadata_path) as f:
        metadata = json.load(f)
    
    species = species_dir.name
    domain = species_dir.parent.name
    
    count = 0
    with gzip.open(cds_path, "rt") as f:
        current_header = ""
        current_seq = []
        
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if current_seq and current_header:
                    record = process_single_cds(
                        current_header, "".join(current_seq),
                        species, domain, k_list, k_max_curve
                    )
                    if record:
                        yield record
                        count += 1
                        if max_records > 0 and count >= max_records:
                            return
                
                current_header = line[1:]
                current_seq = []
            else:
                current_seq.append(line)
        
        # Process last sequence
        if current_seq and current_header:
            record = process_single_cds(
                current_header, "".join(current_seq),
                species, domain, k_list, k_max_curve
            )
            if record:
                yield record


def process_single_cds(
    header: str,
    seq: str,
    species: str,
    domain: str,
    k_list: list[int],
    k_max_curve: int,
) -> EventRecord | None:
    """Process a single CDS and return event record if valid."""
    codons = parse_orf_from_cds(seq)
    
    if not codons or len(codons) < max(k_list) + 2:
        return None
    
    stop_codon = codons[-1]
    if stop_codon not in STOP_CODONS:
        return None
    
    stop_idx = len(codons) - 1
    
    # Extract gene/transcript ID from header
    parts = header.split()
    gene_id = parts[0] if parts else ""
    transcript_id = gene_id
    
    # Create event record
    event = EventRecord(
        species=species,
        domain=domain,
        gene_id=gene_id,
        transcript_id=transcript_id,
        event_type="terminal_stop",
        stop_codon=stop_codon,
        pos_i=stop_idx + 1,  # 1-based
        orf_length=len(codons),
    )
    
    # Compute window features for each k
    for k in k_list:
        event.windows[k] = {
            "before": compute_window_stats(codons, stop_idx, k, "before"),
            "after": compute_window_stats(codons, stop_idx, k, "after"),
        }
    
    # Compute position-resolved Uplift curve
    event.uplift_curve = compute_uplift_curve(codons, stop_idx, k_max_curve)
    
    return event


def main() -> None:
    p = argparse.ArgumentParser(description="Build unified event table")
    p.add_argument("--k-list", type=str, default="3,5,10,20", help="Comma-separated k values")
    p.add_argument("--k-max-curve", type=int, default=20, help="Max k for position curve")
    p.add_argument("--max-records", type=int, default=0, help="Max records per species (0=all)")
    p.add_argument("--output", type=str, default="", help="Output path (default: data/events/)")
    p.add_argument("--format", type=str, choices=["jsonl", "parquet"], default="jsonl")
    args = p.parse_args()
    
    k_list = [int(k) for k in args.k_list.split(",")]
    
    # Find all species
    corpora_dir = data_root() / "corpora"
    species_dirs: list[Path] = []
    
    for domain in ["archaea", "bacteria", "eukarya"]:
        domain_dir = corpora_dir / domain
        if domain_dir.exists():
            for sp_dir in domain_dir.iterdir():
                if sp_dir.is_dir() and (sp_dir / "metadata.json").exists():
                    species_dirs.append(sp_dir)
    
    print(f"Building event table from {len(species_dirs)} species...")
    print(f"  k values: {k_list}")
    print(f"  k_max_curve: {args.k_max_curve}")
    
    # Process all species
    all_events: list[dict[str, Any]] = []
    
    for sp_dir in sorted(species_dirs):
        domain = sp_dir.parent.name
        species = sp_dir.name
        print(f"  [{domain}/{species}]", end=" ", flush=True)
        
        count = 0
        for event in process_species_cds(sp_dir, k_list, args.k_max_curve, args.max_records):
            all_events.append(event.to_dict())
            count += 1
        
        print(f"n={count}")
    
    # Output
    output_dir = Path(args.output) if args.output else data_root() / "events"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.format == "jsonl":
        output_path = output_dir / "terminal_stops.jsonl"
        with open(output_path, "w") as f:
            for event in all_events:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
    else:  # parquet
        try:
            import pandas as pd
            df = pd.DataFrame(all_events)
            output_path = output_dir / "terminal_stops.parquet"
            df.to_parquet(output_path, index=False)
        except ImportError:
            print("Warning: pandas not available, falling back to JSONL")
            output_path = output_dir / "terminal_stops.jsonl"
            with open(output_path, "w") as f:
                for event in all_events:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
    
    print(f"\nWrote {len(all_events)} events to {output_path}")
    
    # Summary statistics
    by_stop = defaultdict(int)
    by_domain = defaultdict(int)
    for e in all_events:
        by_stop[e["stop_codon"]] += 1
        by_domain[e["domain"]] += 1
    
    print("\n=== Summary ===")
    print(f"  Total events: {len(all_events)}")
    print(f"  By stop codon: {dict(by_stop)}")
    print(f"  By domain: {dict(by_domain)}")


if __name__ == "__main__":
    main()
