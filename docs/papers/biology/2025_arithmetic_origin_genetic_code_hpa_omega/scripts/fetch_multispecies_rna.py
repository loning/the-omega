# -*- coding: utf-8 -*-
"""
Fetch multi-species RefSeq mRNA datasets (UTR-inclusive) from NCBI for H2-1b.

This script complements fetch_multispecies_cds.py by downloading the
`*_rna_from_genomic.fna.gz` file for each staged Tier-1 species, using the same
assembly already recorded in `data/corpora/<domain>/<species>/metadata.json`.

Outputs are stored under the paper-local data directory (ignored by git):
  data/corpora/<domain>/<species>/rna_from_genomic.fna.gz

Usage:
  python scripts/fetch_multispecies_rna.py --species all
  python scripts/fetch_multispecies_rna.py --domain eukarya
  python scripts/fetch_multispecies_rna.py --species human,mouse,yeast
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from data_manager import download_file, utc_now_iso, write_json


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def data_root() -> Path:
    return root_dir() / "data"


def corpora_root() -> Path:
    return data_root() / "corpora"


def _select_species_dirs(*, selector: str) -> list[Path]:
    corpora = corpora_root()
    if not corpora.exists():
        raise SystemExit("No corpora directory found. Run fetch_multispecies_cds.py first.")

    selector = str(selector or "").strip().lower()
    out: list[Path] = []

    for domain in ("eukarya", "bacteria", "archaea"):
        ddir = corpora / domain
        if not ddir.exists():
            continue
        if selector in ("eukarya", "bacteria", "archaea") and selector != domain:
            continue
        for sp_dir in sorted([p for p in ddir.iterdir() if p.is_dir()]):
            if selector and selector not in ("all", "eukarya", "bacteria", "archaea"):
                allowed = {s.strip() for s in selector.split(",") if s.strip()}
                if sp_dir.name not in allowed:
                    continue
            out.append(sp_dir)

    return out


def _download_rna_for_species(
    species_dir: Path,
    *,
    force: bool,
    verify_ssl: bool,
) -> dict[str, Any] | None:
    meta_path = species_dir / "metadata.json"
    if not meta_path.exists():
        return None

    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    asm = (metadata.get("assembly") or {}) if isinstance(metadata, dict) else {}
    ftp_base = str(asm.get("ftp_path") or "").strip().rstrip("/")
    if not ftp_base:
        return None
    asm_name = ftp_base.split("/")[-1]
    rna_filename = f"{asm_name}_rna_from_genomic.fna.gz"
    rna_url = f"{ftp_base}/{rna_filename}"

    out_path = species_dir / "rna_from_genomic.fna.gz"
    if out_path.exists() and not force:
        return metadata

    print(f"[download] {species_dir.parent.name}/{species_dir.name}: {rna_filename}", flush=True)
    res = download_file(
        rna_url,
        out_path,
        verify_ssl=bool(verify_ssl),
        timeout_s=1200.0,
        retries=4,
    )

    metadata["rna_file"] = {
        "filename": rna_filename,
        "url": rna_url,
        "local_path": str(out_path.relative_to(root_dir())),
        "bytes": int(res.bytes),
        "sha256": str(res.sha256),
        "retrieved_at_utc": str(res.retrieved_at_utc),
    }
    metadata["retrieved_at_utc_rna"] = utc_now_iso()
    write_json(meta_path, metadata)
    return metadata


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch multi-species RefSeq rna_from_genomic FASTA for H2-1b (UTR-inclusive).")
    ap.add_argument(
        "--species",
        default="all",
        help="Comma-separated species names, 'all', or a domain name (eukarya/bacteria/archaea).",
    )
    ap.add_argument("--force", action="store_true", help="Re-download even if present.")
    ap.add_argument("--insecure", action="store_true", help="Disable SSL verification.")
    ap.add_argument("--list", action="store_true", help="List available staged species and exit.")
    args = ap.parse_args()

    species_dirs = _select_species_dirs(selector=str(args.species))
    if not species_dirs:
        raise SystemExit(f"No species matched selector: {args.species}")

    if args.list:
        for sp_dir in species_dirs:
            meta_path = sp_dir / "metadata.json"
            ok_meta = meta_path.exists()
            ok_rna = (sp_dir / "rna_from_genomic.fna.gz").exists()
            print(f"{sp_dir.parent.name}/{sp_dir.name}\tmetadata={ok_meta}\trna={ok_rna}")
        return

    verify_ssl = not bool(args.insecure)
    results: list[dict[str, Any]] = []
    for sp_dir in species_dirs:
        meta = _download_rna_for_species(sp_dir, force=bool(args.force), verify_ssl=verify_ssl)
        if meta:
            results.append(meta)

    out = corpora_root() / "species_rna_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        out,
        {
            "species_count": int(len(results)),
            "generated_at_utc": utc_now_iso(),
            "species": results,
        },
    )
    print(f"Wrote: {out.relative_to(root_dir())}", flush=True)


if __name__ == "__main__":
    main()

