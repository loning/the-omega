# -*- coding: utf-8 -*-
"""
Fetch multi-species CDS datasets from NCBI RefSeq for H2 cross-domain replication.

This script downloads annotated CDS FASTA files for Tier-1 species as defined in
EXPERIMENT_ANALYSIS.md M1 milestone.

Data sources:
- NCBI RefSeq: Annotated CDS sequences (preferred over ORF prediction)
- Priority: code-1 (standard genetic code) species first

Species organization:
- data/corpora/eukarya/<species>/
- data/corpora/bacteria/<species>/
- data/corpora/archaea/<species>/

Each species directory contains:
- cds_from_genomic.fna.gz (annotated CDS)
- metadata.json (taxid, assembly accession, translation table, provenance)

Usage:
    python scripts/fetch_multispecies_cds.py --species all
    python scripts/fetch_multispecies_cds.py --species mouse,yeast
    python scripts/fetch_multispecies_cds.py --domain eukarya
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from data_manager import download_file, sha256_file, ssl_context, utc_now_iso, write_json


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def data_root() -> Path:
    return root_dir() / "data"


# Tier-1 species list from EXPERIMENT_ANALYSIS.md
# Each entry: (short_name, scientific_name, taxid, domain, translation_table, assembly_filter)
TIER1_SPECIES: list[tuple[str, str, int, str, int, dict[str, str]]] = [
    # Eukarya (code-1)
    ("human", "Homo sapiens", 9606, "eukarya", 1, {"refseq_category": "reference genome"}),
    ("mouse", "Mus musculus", 10090, "eukarya", 1, {"refseq_category": "reference genome"}),
    ("yeast", "Saccharomyces cerevisiae", 559292, "eukarya", 1, {"refseq_category": "reference genome"}),
    ("fly", "Drosophila melanogaster", 7227, "eukarya", 1, {"refseq_category": "reference genome"}),
    ("worm", "Caenorhabditis elegans", 6239, "eukarya", 1, {"refseq_category": "reference genome"}),
    ("arabidopsis", "Arabidopsis thaliana", 3702, "eukarya", 1, {"refseq_category": "reference genome"}),
    ("zebrafish", "Danio rerio", 7955, "eukarya", 1, {"refseq_category": "reference genome"}),
    
    # Bacteria (code-11, bacterial/archaeal standard)
    ("ecoli", "Escherichia coli", 562, "bacteria", 11, {"assembly_level": "Complete Genome"}),
    ("bsubtilis", "Bacillus subtilis", 1423, "bacteria", 11, {"assembly_level": "Complete Genome"}),
    ("pseudomonas", "Pseudomonas aeruginosa", 287, "bacteria", 11, {"assembly_level": "Complete Genome"}),
    ("mycobacterium", "Mycobacterium tuberculosis", 1773, "bacteria", 11, {"assembly_level": "Complete Genome"}),
    ("streptomyces", "Streptomyces coelicolor", 1902, "bacteria", 11, {"assembly_level": "Complete Genome"}),
    ("synechocystis", "Synechocystis sp. PCC 6803", 1111708, "bacteria", 11, {"assembly_level": "Complete Genome"}),
    ("caulobacter", "Caulobacter vibrioides", 155892, "bacteria", 11, {"assembly_level": "Complete Genome"}),
    ("thermus", "Thermus thermophilus", 274, "bacteria", 11, {"assembly_level": "Complete Genome"}),
    
    # Archaea (code-11)
    ("haloferax", "Haloferax volcanii", 2246, "archaea", 11, {"assembly_level": "Complete Genome"}),
    ("methanococcus", "Methanocaldococcus jannaschii", 2190, "archaea", 11, {"assembly_level": "Complete Genome"}),
    ("sulfolobus", "Sulfolobus acidocaldarius", 2285, "archaea", 11, {"assembly_level": "Complete Genome"}),
    ("pyrococcus", "Pyrococcus furiosus", 2261, "archaea", 11, {"assembly_level": "Complete Genome"}),
]


@dataclass
class AssemblyInfo:
    accession: str
    asm_name: str
    organism: str
    taxid: str
    ftp_path: str
    assembly_level: str
    refseq_category: str


def _download_text(
    url: str,
    *,
    timeout_s: float = 120.0,
    verify_ssl: bool = True,
    retries: int = 4,
) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "the-omega-genetic-code/1.0"})
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout_s, context=ssl_context(verify=verify_ssl)) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            last_err = e
            if attempt + 1 < retries:
                time.sleep(2.0 * (attempt + 1))
    raise last_err or RuntimeError("Download failed")


def _parse_assembly_summary(text: str) -> list[dict[str, str]]:
    """Parse NCBI assembly_summary.txt format."""
    header: list[str] = []
    rows: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line:
            continue
        if line.startswith("#"):
            if "assembly_accession" in line and "\t" in line:
                header = line.lstrip("#").strip().split("\t")
            continue
        if not header:
            continue
        parts = line.split("\t")
        if len(parts) < len(header):
            continue
        row = {header[i]: parts[i] for i in range(len(header))}
        rows.append(row)
    return rows


def find_best_assembly(
    taxid: int,
    filters: dict[str, str],
    *,
    verify_ssl: bool = True,
) -> AssemblyInfo | None:
    """Find best RefSeq assembly for a given taxid."""
    # Try RefSeq assembly summary
    summary_url = "https://ftp.ncbi.nlm.nih.gov/genomes/refseq/assembly_summary_refseq.txt"
    
    print(f"  [fetch] Downloading assembly summary for taxid {taxid}...")
    try:
        text = _download_text(summary_url, verify_ssl=verify_ssl, timeout_s=300.0)
    except Exception as e:
        print(f"  [warn] Failed to download assembly summary: {e}")
        return None
    
    rows = _parse_assembly_summary(text)
    
    # Filter by taxid (exact match or species-level)
    candidates = []
    for row in rows:
        row_taxid = row.get("taxid", "").strip()
        species_taxid = row.get("species_taxid", "").strip()
        if str(taxid) not in (row_taxid, species_taxid):
            continue
        
        # Apply filters
        match = True
        for key, val in filters.items():
            if row.get(key, "").strip() != val:
                match = False
                break
        if not match:
            continue
        
        ftp = row.get("ftp_path", "").strip()
        if not ftp or ftp.lower() == "na":
            continue
        
        candidates.append(row)
    
    if not candidates:
        # Relax filters and try again
        for row in rows:
            row_taxid = row.get("taxid", "").strip()
            species_taxid = row.get("species_taxid", "").strip()
            if str(taxid) not in (row_taxid, species_taxid):
                continue
            ftp = row.get("ftp_path", "").strip()
            if not ftp or ftp.lower() == "na":
                continue
            candidates.append(row)
    
    if not candidates:
        return None
    
    # Sort by: reference genome > representative > other, then by date
    def rank(r: dict[str, str]) -> tuple[int, int, str]:
        cat = r.get("refseq_category", "").strip().lower()
        if cat == "reference genome":
            cat_rank = 0
        elif cat == "representative genome":
            cat_rank = 1
        else:
            cat_rank = 2
        
        level = r.get("assembly_level", "").strip().lower()
        if level == "complete genome":
            level_rank = 0
        elif level == "chromosome":
            level_rank = 1
        else:
            level_rank = 2
        
        return (cat_rank, level_rank, r.get("assembly_accession", ""))
    
    best = min(candidates, key=rank)
    ftp = best.get("ftp_path", "").strip()
    if ftp.startswith("ftp://"):
        ftp = "https://" + ftp[6:]
    
    return AssemblyInfo(
        accession=best.get("assembly_accession", ""),
        asm_name=best.get("asm_name", ""),
        organism=best.get("organism_name", ""),
        taxid=best.get("taxid", ""),
        ftp_path=ftp,
        assembly_level=best.get("assembly_level", ""),
        refseq_category=best.get("refseq_category", ""),
    )


def download_cds_fasta(
    assembly: AssemblyInfo,
    out_dir: Path,
    *,
    verify_ssl: bool = True,
) -> dict[str, Any]:
    """Download CDS FASTA from assembly FTP path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Find CDS file in the assembly directory
    ftp_base = assembly.ftp_path.rstrip("/")
    asm_name = ftp_base.split("/")[-1]
    
    # CDS file pattern: *_cds_from_genomic.fna.gz
    cds_filename = f"{asm_name}_cds_from_genomic.fna.gz"
    cds_url = f"{ftp_base}/{cds_filename}"
    
    out_path = out_dir / "cds_from_genomic.fna.gz"
    
    print(f"  [download] {cds_filename}...")
    try:
        res = download_file(
            cds_url,
            out_path,
            verify_ssl=verify_ssl,
            timeout_s=600.0,
            retries=4,
        )
        return {
            "filename": cds_filename,
            "url": cds_url,
            "local_path": str(out_path.relative_to(root_dir())),
            "bytes": res.bytes,
            "sha256": res.sha256,
            "retrieved_at_utc": res.retrieved_at_utc,
        }
    except Exception as e:
        print(f"  [error] Failed to download CDS: {e}")
        return {}


def fetch_species(
    short_name: str,
    scientific_name: str,
    taxid: int,
    domain: str,
    translation_table: int,
    filters: dict[str, str],
    *,
    verify_ssl: bool = True,
    force: bool = False,
) -> dict[str, Any] | None:
    """Fetch CDS data for a single species."""
    out_dir = data_root() / "corpora" / domain / short_name
    meta_path = out_dir / "metadata.json"
    
    if meta_path.exists() and not force:
        print(f"[skip] {short_name} already exists (use --force to re-download)")
        return json.loads(meta_path.read_text())
    
    print(f"[fetch] {short_name} ({scientific_name}, taxid={taxid})")
    
    # Find assembly
    assembly = find_best_assembly(taxid, filters, verify_ssl=verify_ssl)
    if not assembly:
        print(f"  [error] No suitable assembly found for {short_name}")
        return None
    
    print(f"  [found] {assembly.accession} ({assembly.asm_name})")
    
    # Download CDS
    cds_info = download_cds_fasta(assembly, out_dir, verify_ssl=verify_ssl)
    if not cds_info:
        return None
    
    # Write metadata
    metadata = {
        "short_name": short_name,
        "scientific_name": scientific_name,
        "taxid": taxid,
        "domain": domain,
        "translation_table": translation_table,
        "assembly": {
            "accession": assembly.accession,
            "asm_name": assembly.asm_name,
            "organism": assembly.organism,
            "assembly_level": assembly.assembly_level,
            "refseq_category": assembly.refseq_category,
            "ftp_path": assembly.ftp_path,
        },
        "cds_file": cds_info,
        "retrieved_at_utc": utc_now_iso(),
    }
    
    write_json(meta_path, metadata)
    print(f"  [done] Wrote {meta_path.relative_to(root_dir())}")
    
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch multi-species CDS data for M1")
    parser.add_argument(
        "--species",
        default="all",
        help="Comma-separated species names, 'all', or domain name (eukarya/bacteria/archaea)",
    )
    parser.add_argument("--force", action="store_true", help="Re-download even if exists")
    parser.add_argument("--insecure", action="store_true", help="Disable SSL verification")
    parser.add_argument("--list", action="store_true", help="List available species and exit")
    args = parser.parse_args()
    
    verify_ssl = not args.insecure
    
    if args.list:
        print("Available Tier-1 species:")
        for name, sci, taxid, domain, tt, _ in TIER1_SPECIES:
            print(f"  {name:15s} {domain:10s} {sci:40s} (taxid={taxid}, table={tt})")
        return
    
    # Determine which species to fetch
    selector = args.species.lower().strip()
    if selector == "all":
        species_list = TIER1_SPECIES
    elif selector in ("eukarya", "bacteria", "archaea"):
        species_list = [s for s in TIER1_SPECIES if s[3] == selector]
    else:
        names = {n.strip() for n in selector.split(",") if n.strip()}
        species_list = [s for s in TIER1_SPECIES if s[0] in names]
    
    if not species_list:
        print(f"No species matched selector: {selector}")
        return
    
    print(f"Fetching {len(species_list)} species...")
    
    results: list[dict[str, Any]] = []
    for name, sci, taxid, domain, tt, filters in species_list:
        meta = fetch_species(
            name, sci, taxid, domain, tt, filters,
            verify_ssl=verify_ssl,
            force=args.force,
        )
        if meta:
            results.append(meta)
    
    # Write summary
    summary_path = data_root() / "corpora" / "species_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(summary_path, {
        "species_count": len(results),
        "species": results,
        "generated_at_utc": utc_now_iso(),
    })
    print(f"\nWrote summary: {summary_path.relative_to(root_dir())}")
    print(f"Successfully fetched {len(results)}/{len(species_list)} species")


if __name__ == "__main__":
    main()
