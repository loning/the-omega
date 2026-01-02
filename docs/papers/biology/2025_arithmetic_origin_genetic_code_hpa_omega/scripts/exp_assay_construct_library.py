#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build an assay construct library (JSONL) from existing candidate-context exports.

Default input:
  - data/refseq_hsapiens_mrna/stop_context_candidates.jsonl

Default output:
  - data/assays/readthrough_constructs.jsonl

Design goals:
  - Standard library only
  - Deterministic construct_key for idempotent upserts into Supabase (assay_constructs)
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def construct_key(
    *,
    assay_type: str,
    dataset: str,
    candidate_set: str,
    k: int,
    stop_codon: str,
    before_seq_dna: str,
    stop_codon_dna: str,
    after_seq_dna: str,
) -> str:
    # Use a stable, human-auditable serialization. Do not include JSON dumps of payload.
    parts = [
        f"assay_type={assay_type}",
        f"dataset={dataset}",
        f"candidate_set={candidate_set}",
        f"k={int(k)}",
        f"stop_codon={stop_codon}",
        f"before_seq_dna={before_seq_dna}",
        f"stop_codon_dna={stop_codon_dna}",
        f"after_seq_dna={after_seq_dna}",
    ]
    return _sha256_hex("\n".join(parts))


def _parse_csv_list(s: str) -> list[str]:
    out: list[str] = []
    for part in (s or "").split(","):
        part = part.strip()
        if part:
            out.append(part)
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build assay construct JSONL from stop-context candidates.")
    p.add_argument(
        "--in-jsonl",
        default="data/refseq_hsapiens_mrna/stop_context_candidates.jsonl",
        help="Input candidates JSONL (relative to project root).",
    )
    p.add_argument(
        "--out-jsonl",
        default="data/assays/readthrough_constructs.jsonl",
        help="Output constructs JSONL (relative to project root).",
    )
    p.add_argument(
        "--out-summary-json",
        default="data/assays/readthrough_constructs_summary.json",
        help="Optional output summary JSON (relative to project root).",
    )
    p.add_argument("--assay-type", default="readthrough", help="Assay type label (e.g. readthrough/sec/pyl).")
    p.add_argument(
        "--dataset",
        default="",
        help="Optional dataset override (empty uses dataset from input rows).",
    )
    p.add_argument("--candidate-set", default="reporter_v1", help="candidate_set filter.")
    p.add_argument(
        "--group-labels",
        default="matched_after_high,matched_after_low",
        help="Comma-separated group_label filter.",
    )
    p.add_argument("--k", type=int, default=10, help="Window radius k filter.")
    p.add_argument("--stop-codons", default="UAA,UAG,UGA", help="Comma-separated stop-codon filter.")
    p.add_argument("--max-per-stop", type=int, default=10, help="Max rank per (stop_codon, group_label).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = root_dir()
    in_path = (root / str(args.in_jsonl)).resolve()
    out_path = (root / str(args.out_jsonl)).resolve()
    out_summary = (root / str(args.out_summary_json)).resolve() if str(args.out_summary_json).strip() else None

    if not in_path.exists():
        raise SystemExit(f"Missing input JSONL: {in_path}")

    assay_type = str(args.assay_type).strip() or "readthrough"
    candidate_set = str(args.candidate_set).strip()
    if not candidate_set:
        raise SystemExit("Empty --candidate-set")
    k = int(args.k)
    if k <= 0:
        raise SystemExit("Invalid --k")
    group_labels = set(_parse_csv_list(str(args.group_labels)))
    if not group_labels:
        raise SystemExit("Empty --group-labels")
    stop_codons = set(_parse_csv_list(str(args.stop_codons)))
    if not stop_codons:
        raise SystemExit("Empty --stop-codons")
    max_per = int(args.max_per_stop)
    if max_per <= 0:
        raise SystemExit("Invalid --max-per-stop")

    dataset_override = str(args.dataset).strip()

    # Keep rank counts per (stop_codon, group_label).
    seen_counts: dict[tuple[str, str], int] = {}
    kept = 0
    total = 0
    rows_out: list[dict[str, Any]] = []

    with in_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            total += 1
            obj = json.loads(line)
            if not isinstance(obj, dict):
                continue

            if str(obj.get("candidate_set") or "") != candidate_set:
                continue
            if int(obj.get("k", 0) or 0) != int(k):
                continue
            stop = str(obj.get("stop_codon") or "")
            if stop not in stop_codons:
                continue
            gl = str(obj.get("group_label") or "")
            if gl not in group_labels:
                continue
            rk = int(obj.get("rank", 0) or 0)
            if rk <= 0:
                continue
            key_cnt = (stop, gl)
            if seen_counts.get(key_cnt, 0) >= max_per:
                continue

            before_seq = str(obj.get("before_seq_dna") or "")
            stop_dna = str(obj.get("stop_codon_dna") or "")
            after_seq = str(obj.get("after_seq_dna") or "")
            if not before_seq or not stop_dna or not after_seq:
                continue

            ds = dataset_override or str(obj.get("dataset") or "")
            if not ds:
                continue

            ck = construct_key(
                assay_type=assay_type,
                dataset=ds,
                candidate_set=candidate_set,
                k=int(k),
                stop_codon=stop,
                before_seq_dna=before_seq,
                stop_codon_dna=stop_dna,
                after_seq_dna=after_seq,
            )

            rows_out.append(
                {
                    "construct_key": ck,
                    "assay_type": assay_type,
                    "dataset": ds,
                    "candidate_set": candidate_set,
                    "group_label": gl,
                    "rank": int(rk),
                    "k": int(k),
                    "stop_codon": stop,
                    "before_seq_dna": before_seq,
                    "stop_codon_dna": stop_dna,
                    "after_seq_dna": after_seq,
                    "plus4_nt": obj.get("plus4_nt"),
                    "after_nt6": obj.get("after_nt6"),
                    "predicted_before_mean_delta": obj.get("before_mean_delta"),
                    "predicted_after_mean_delta": obj.get("after_mean_delta"),
                    "predicted_diff": obj.get("diff"),
                    "predicted_before_gc": obj.get("before_gc"),
                    "predicted_after_gc": obj.get("after_gc"),
                    "predicted_before_dinuc": obj.get("before_dinuc"),
                    "predicted_after_dinuc": obj.get("after_dinuc"),
                    "source_record_id": obj.get("record_id"),
                    "source_frame": obj.get("frame"),
                    "source_start_base": obj.get("start_base"),
                    "source_stop_base": obj.get("stop_base"),
                    "payload": obj,
                }
            )
            seen_counts[key_cnt] = seen_counts.get(key_cnt, 0) + 1
            kept += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows_out.sort(
        key=lambda r: (
            str(r.get("stop_codon") or ""),
            str(r.get("group_label") or ""),
            int(r.get("rank") or 0),
            str(r.get("source_record_id") or ""),
            int(r.get("source_stop_base") or 0),
        )
    )
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows_out:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    print("Wrote:", out_path, f"(rows={len(rows_out)} from input_lines={total})")

    if out_summary is not None:
        out_summary.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "assay_type": assay_type,
            "dataset": dataset_override or "(from input rows)",
            "candidate_set": candidate_set,
            "group_labels": sorted(group_labels),
            "k": int(k),
            "stop_codons": sorted(stop_codons),
            "max_per_stop": int(max_per),
            "input": str(in_path),
            "output": str(out_path),
            "rows": int(len(rows_out)),
            "counts_by_stop_and_group": {f"{a}:{b}": int(n) for (a, b), n in sorted(seen_counts.items())},
        }
        out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("Wrote:", out_summary)


if __name__ == "__main__":
    main()


