# -*- coding: utf-8 -*-
"""
Prepare boundary-enrichment inputs from the GenBank transl_except recoding dataset.

This script generates:
  - a FASTA of translated-orientation CDS ORFs (one per CDS with transl_except),
  - a TSV of codon positions (0-based) defining labeled site sets around Sec/Pyl recoding codons.

These artefacts can be fed into exp_boundary_enrichment.py to run boundary-sector enrichment tests.

Standard library only (plus project-local modules).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic
from exp_recoding_sites import _TRANSL_EXCEPT_RE, build_spliced_cds, parse_cds_location, parse_features, parse_origin_seq, parse_version
from progress_tools import Heartbeat


ANALYSIS_VERSION = 1
SCHEMA_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    d = root_dir() / "data" / "boundary_enrichment"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _gb_inputs_digest(files: list[Path]) -> str:
    h = hashlib.sha256()
    for fp in files:
        st = fp.stat()
        h.update(fp.name.encode("utf-8"))
        h.update(b"\0")
        h.update(str(int(st.st_size)).encode("utf-8"))
        h.update(b"\0")
        h.update(str(int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def _cds_record_id(*, version: str, cds_location: str, codon_start: int) -> str:
    # Keep ID stable and whitespace-free; iter_fasta uses the first whitespace-delimited token.
    loc = str(cds_location).replace(" ", "")
    return f"{version}|cs{int(codon_start)}|{loc}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare boundary-enrichment inputs from GenBank transl_except recoding dataset.")
    p.add_argument("--k-window", type=int, default=10, help="Window radius (codons) for before/after site sets.")
    p.add_argument("--max-files", type=int, default=0, help="Optional limit on number of gb files (0=all).")
    p.add_argument("--heartbeat-s", type=float, default=60.0, help="Emit a progress heartbeat at least once per this many seconds (0 disables).")
    p.add_argument("--force", action="store_true", help="Force recomputation even if cached outputs exist.")
    p.add_argument(
        "--out-fasta",
        default=str(data_dir() / "recoding_cds_orfs.fasta.gz"),
        help="Output FASTA(.gz) path (translated-orientation CDS ORFs).",
    )
    p.add_argument(
        "--out-positions-tsv",
        default=str(data_dir() / "recoding_site_sets.tsv"),
        help="Output TSV path with columns: record_id, codon_index, label.",
    )
    p.add_argument(
        "--out-summary-json",
        default=str(data_dir() / "recoding_boundary_inputs_summary.json"),
        help="Output summary JSON (used for caching).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    k = int(args.k_window)
    if k < 0:
        raise SystemExit("--k-window must be >= 0")

    gb_dir = root_dir() / "data" / "recoding_genbank" / "genbank"
    if not gb_dir.exists():
        raise SystemExit(f"Missing GenBank directory: {gb_dir}")
    gb_files = sorted(gb_dir.glob("*.gb"))
    if int(args.max_files) > 0:
        gb_files = gb_files[: int(args.max_files)]
    if not gb_files:
        raise SystemExit(f"No .gb files found under: {gb_dir}")

    out_fasta = Path(args.out_fasta)
    out_pos = Path(args.out_positions_tsv)
    out_summary = Path(args.out_summary_json)

    inputs_digest = _gb_inputs_digest(gb_files)
    cache_key = {
        "analysis": "recoding_boundary_inputs",
        "analysis_version": int(ANALYSIS_VERSION),
        "k_window": int(k),
        "max_files": int(args.max_files or 0),
        "inputs_digest": inputs_digest,
        "out_fasta": str(out_fasta),
        "out_positions_tsv": str(out_pos),
        "out_summary_json": str(out_summary),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}

    if (not args.force) and out_fasta.exists() and out_pos.exists() and cache_hit(out_summary, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_summary}")
        return

    hb = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress] recoding_boundary_inputs")
    hb.force(f"start files={len(gb_files)} k_window={k}")

    # Deduplicate by CDS record_id.
    cds_seqs: dict[str, str] = {}
    pos_rows: list[tuple[str, int, str]] = []
    n_sites = 0
    n_sites_by_aa: dict[str, int] = {}

    for i, fp in enumerate(gb_files, start=1):
        text = fp.read_text(encoding="utf-8", errors="replace")
        version = parse_version(text)
        if not version:
            continue
        seq_dna = parse_origin_seq(text)
        if not seq_dna:
            continue
        feats = parse_features(text)
        hb.maybe(f"files={i}/{len(gb_files)} last={fp.name} cds={len(cds_seqs)} sites={n_sites}")

        for feat in feats:
            if feat.key != "CDS":
                continue
            if "transl_except" not in feat.qualifiers:
                continue

            ploc = parse_cds_location(feat.location)
            if ploc is None:
                continue
            strand = int(ploc.strand)

            codon_start = 1
            if "codon_start" in feat.qualifiers and feat.qualifiers["codon_start"]:
                try:
                    codon_start = int(feat.qualifiers["codon_start"][0] or "1")
                except Exception:
                    codon_start = 1
            codon_start = 1 if codon_start not in (1, 2, 3) else int(codon_start)

            cds_seq_dna, _genomic_pos_by_i, genomic_to_i = build_spliced_cds(seq_dna, ploc.spans, strand=strand)
            if not cds_seq_dna:
                continue
            translation_start_idx0 = int(codon_start - 1)
            if translation_start_idx0 < 0 or translation_start_idx0 + 2 >= len(cds_seq_dna):
                continue
            n_codons = (len(cds_seq_dna) - translation_start_idx0) // 3
            if n_codons <= 0:
                continue

            rid = _cds_record_id(version=str(version), cds_location=str(feat.location), codon_start=int(codon_start))
            orf_seq_dna = cds_seq_dna[translation_start_idx0 : translation_start_idx0 + 3 * int(n_codons)]
            if len(orf_seq_dna) < 3:
                continue
            # Keep length multiple of 3.
            orf_seq_dna = orf_seq_dna[: (len(orf_seq_dna) // 3) * 3]

            prev = cds_seqs.get(rid)
            if prev is None:
                cds_seqs[rid] = orf_seq_dna
            elif prev != orf_seq_dna:
                raise SystemExit(f"CDS sequence conflict for record_id={rid}")

            # Positions for Sec/Pyl sites (codon indices in translated CDS).
            for val in feat.qualifiers.get("transl_except", []):
                m = _TRANSL_EXCEPT_RE.search(val)
                if not m:
                    continue
                pos_start = int(m.group("start"))
                pos_end = int(m.group("end"))
                aa_raw = str(m.group("aa") or "").strip()
                aa = aa_raw
                if aa.lower() == "sec":
                    aa = "Sec"
                elif aa.lower() == "pyl":
                    aa = "Pyl"
                if aa not in ("Sec", "Pyl"):
                    continue
                if pos_end - pos_start != 2:
                    continue

                # For minus-strand codons, the first translated base is at the high coordinate.
                anchor = pos_start if strand == 1 else pos_end
                idx0 = genomic_to_i.get(int(anchor))
                if idx0 is None:
                    continue
                idx0_i = int(idx0)
                if idx0_i < translation_start_idx0 or (idx0_i - translation_start_idx0) % 3 != 0:
                    continue
                ci0 = (idx0_i - translation_start_idx0) // 3
                if ci0 < 0 or ci0 >= int(n_codons):
                    continue

                n_sites += 1
                n_sites_by_aa[aa] = int(n_sites_by_aa.get(aa, 0)) + 1

                if k > 0:
                    for j in range(1, int(k) + 1):
                        if (ci0 - j) >= 0:
                            pos_rows.append((rid, int(ci0 - j), f"before_k{int(k)}:{aa}"))
                            pos_rows.append((rid, int(ci0 - j), f"before_k{int(k)}:all"))
                        if (ci0 + j) < int(n_codons):
                            pos_rows.append((rid, int(ci0 + j), f"after_k{int(k)}:{aa}"))
                            pos_rows.append((rid, int(ci0 + j), f"after_k{int(k)}:all"))

    hb.force(f"done files={len(gb_files)} cds={len(cds_seqs)} sites={n_sites}")

    out_fasta.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_fasta, "wt", encoding="utf-8", newline="") as f:
        for rid in sorted(cds_seqs):
            f.write(f">{rid}\n")
            seq = cds_seqs[rid]
            for j in range(0, len(seq), 80):
                f.write(seq[j : j + 80] + "\n")

    out_pos.parent.mkdir(parents=True, exist_ok=True)
    # Deterministic order, but keep duplicates (the enrichment script will deduplicate per-record per-label).
    pos_rows.sort(key=lambda x: (x[0], x[2], int(x[1])))
    with out_pos.open("w", encoding="utf-8", newline="") as f:
        f.write("record_id\tcodon_index\tlabel\n")
        for rid, ci0, lbl in pos_rows:
            f.write(f"{rid}\t{int(ci0)}\t{lbl}\n")

    summary_obj: dict[str, Any] = {
        "schema_version": int(SCHEMA_VERSION),
        "analysis_version": int(ANALYSIS_VERSION),
        "k_window": int(k),
        "max_files": int(args.max_files or 0),
        "inputs": {
            "genbank_dir": str(gb_dir),
            "inputs_digest": inputs_digest,
            "n_files": int(len(gb_files)),
        },
        "outputs": {
            "fasta": str(out_fasta),
            "positions_tsv": str(out_pos),
        },
        "n_cds": int(len(cds_seqs)),
        "n_sites": int(n_sites),
        "n_sites_by_aa": {k: int(v) for k, v in sorted(n_sites_by_aa.items())},
        "n_rows_positions": int(len(pos_rows)),
    }
    out_summary.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out_summary, summary_obj)
    write_json_atomic(cache_meta_path(out_summary), cache_meta)

    print("Wrote:", out_fasta)
    print("Wrote:", out_pos)
    print("Wrote:", out_summary)


if __name__ == "__main__":
    main()


