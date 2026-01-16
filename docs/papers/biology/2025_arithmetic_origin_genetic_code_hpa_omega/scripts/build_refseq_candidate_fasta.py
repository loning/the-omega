# -*- coding: utf-8 -*-
"""
Build a small RefSeq transcriptome FASTA containing only the stop-context candidates.

This helper is used by the raw-read Ribo-seq pipeline (H3-3c) to build a
lightweight bowtie2 index for quick pilots.

Notes:
  - Candidate sequences are stored as RNA (U) in our analysis code; aligners
    typically expect DNA (T). We therefore emit FASTA with U->T.
  - Output lives under data/_cache/ (ignored by git).
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any, Iterable

from genetic_code_tools import iter_fasta


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    return root_dir() / "data"


def cache_dir() -> Path:
    d = data_dir() / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _wrap_fasta(seq: str, *, width: int = 60) -> Iterable[str]:
    for i in range(0, len(seq), int(width)):
        yield seq[i : i + int(width)]


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a candidate-only RefSeq FASTA for H3-3c pilots.")
    ap.add_argument("--k", type=int, default=10, help="Candidate window size in codons (filters stop_context_candidates.jsonl).")
    ap.add_argument(
        "--in-jsonl",
        default=str(data_dir() / "refseq_hsapiens_mrna" / "stop_context_candidates.jsonl"),
        help="Stop-context candidates JSONL.",
    )
    ap.add_argument(
        "--refseq-glob",
        default=str(data_dir() / "refseq_hsapiens_mrna" / "human.*.rna.fna.gz"),
        help="Glob for RefSeq FASTA shards (input).",
    )
    ap.add_argument(
        "--out-fasta",
        default=str(cache_dir() / "refseq_hsapiens_candidates_k10.dna.fasta"),
        help="Output FASTA path (DNA alphabet).",
    )
    ap.add_argument("--force", action="store_true", help="Rebuild even if output exists.")
    args = ap.parse_args()

    in_jsonl = Path(str(args.in_jsonl))
    if not in_jsonl.is_absolute():
        in_jsonl = root_dir() / in_jsonl
    if not in_jsonl.exists():
        raise SystemExit(f"Missing input: {in_jsonl}")

    out_fa = Path(str(args.out_fasta))
    if not out_fa.is_absolute():
        out_fa = root_dir() / out_fa
    out_fa.parent.mkdir(parents=True, exist_ok=True)

    if out_fa.exists() and not args.force:
        print(f"[skip] exists: {out_fa}", flush=True)
        return

    rows = _read_jsonl(in_jsonl)
    rows = [r for r in rows if int(r.get("k", -1)) == int(args.k)]
    if not rows:
        raise SystemExit(f"No candidate rows with k={args.k} in {in_jsonl}")

    keep = {str(r.get("record_id") or "").strip() for r in rows if str(r.get("record_id") or "").strip()}
    if not keep:
        raise SystemExit(f"No record_id found in {in_jsonl}")

    shard_glob = str(args.refseq_glob)
    if not Path(shard_glob).is_absolute():
        shard_glob = str(root_dir() / shard_glob)
    shards = sorted(Path(p) for p in glob.glob(shard_glob))
    if not shards:
        raise SystemExit(f"No FASTA shards matched --refseq-glob: {args.refseq_glob}")

    found: dict[str, str] = {}
    for fp in shards:
        for rid, seq_rna in iter_fasta(str(fp)):
            if rid in keep:
                found[rid] = seq_rna.replace("U", "T")

    missing = sorted([rid for rid in keep if rid not in found])
    if missing:
        print(f"[warn] missing {len(missing)}/{len(keep)} record_ids (showing up to 10): {missing[:10]}", flush=True)

    tmp = out_fa.with_suffix(out_fa.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        for rid in sorted(found.keys()):
            f.write(f">{rid}\n")
            for line in _wrap_fasta(found[rid]):
                f.write(line + "\n")
    tmp.replace(out_fa)

    print(f"Wrote: {out_fa} (records={len(found)}/{len(keep)})", flush=True)


if __name__ == "__main__":
    main()
