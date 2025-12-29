"""
Sequence spectrum CLI for the Fold_6 genetic-code interface.

Reads FASTA (DNA or RNA), normalizes T->U, and outputs per-codon (Z,U) traces.
Optionally scans ORFs in a chosen reading frame.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, deque
from pathlib import Path

from genetic_code_tools import (
    START_CODON,
    STOP_CODONS,
    codon_stream,
    find_orfs,
    fold_codon,
    iter_fasta,
)


MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fold_6 codon spectrum (Z,U) extractor")
    p.add_argument("--fasta", required=True, help="Input FASTA file (DNA or RNA).")
    p.add_argument("--frame", type=int, default=0, choices=(0, 1, 2), help="Reading frame (0,1,2).")
    p.add_argument(
        "--orfs",
        action="store_true",
        help=f"Extract ORFs in the chosen frame using start {START_CODON} and stops {STOP_CODONS}.",
    )
    p.add_argument("--min-codons", type=int, default=0, help="Minimum ORF length in codons (if --orfs).")
    p.add_argument("--out", help="Optional output TSV path for per-codon traces.")
    p.add_argument("--summary-out", help="Optional output JSONL path for per-segment summary statistics.")
    p.add_argument(
        "--stop-window",
        type=int,
        default=0,
        help="Codon window size for stop-context uplift statistics (0 disables).",
    )
    return p.parse_args()


def _counter_dict(c: Counter) -> dict[str, int]:
    return {str(k): int(v) for k, v in sorted(c.items(), key=lambda kv: kv[0])}


def process_segment(
    seq: str,
    frame: int,
    segment_id: str,
    mu: dict[str, str],
    *,
    record_id: str,
    out_writer: csv.DictWriter | None,
    stop_window: int,
    start_base: int = 0,
    end_base_exclusive: int | None = None,
) -> dict[str, object]:
    """
    Process a sequence segment and optionally write per-codon rows.
    Returns a JSON-serializable summary dict.
    """
    if end_base_exclusive is None:
        end_base_exclusive = len(seq)
    if stop_window < 0:
        raise ValueError("stop_window must be nonnegative")

    codon_counts: Counter[str] = Counter()
    aa_counts: Counter[str] = Counter()
    v_hist: Counter[int] = Counter()
    delta_hist: Counter[int] = Counter()

    boundary_count = 0
    start_count = 0
    stop_count = 0
    stop_codon_counts: Counter[str] = Counter()
    start_vdelta_hist: Counter[tuple[int, int]] = Counter()
    stop_vdelta_hist: Counter[tuple[str, int, int]] = Counter()

    # Stop-context uplift statistics (U=Delta) in a +-window around stop codons.
    stop_ctx: dict[str, dict[str, object]] = {}
    pending: list[dict[str, int]] = []
    prev_u: deque[int] = deque(maxlen=stop_window if stop_window > 0 else 1)
    if stop_window > 0:
        for sc in STOP_CODONS:
            stop_ctx[sc] = {
                "before_sum": 0,
                "before_count": 0,
                "after_sum": 0,
                "after_count": 0,
                "before_hist": Counter(),
                "after_hist": Counter(),
            }

    codon_index = 0
    for base_pos, codon in codon_stream(seq, frame=frame):
        if base_pos < start_base:
            continue
        if base_pos + 3 > end_base_exclusive:
            break

        f = fold_codon(codon, mu)

        codon_counts[codon] += 1
        aa_counts[f.aa] += 1
        v_hist[f.v] += 1
        delta_hist[f.delta] += 1

        if f.is_boundary:
            boundary_count += 1

        is_start = int(codon == START_CODON)
        is_stop = int(codon in STOP_CODONS)

        if is_start:
            start_count += 1
            start_vdelta_hist[(f.v, f.delta)] += 1
        if is_stop:
            stop_count += 1
            stop_codon_counts[codon] += 1
            stop_vdelta_hist[(codon, f.v, f.delta)] += 1

        # Stop-context window accounting (streaming).
        if stop_window > 0:
            # First, contribute current codon uplift to the after-window of pending stops.
            if pending:
                new_pending: list[dict[str, int]] = []
                for entry in pending:
                    sc = entry["stop"]
                    stop_ctx[sc]["after_sum"] = int(stop_ctx[sc]["after_sum"]) + f.delta  # type: ignore[assignment]
                    stop_ctx[sc]["after_count"] = int(stop_ctx[sc]["after_count"]) + 1  # type: ignore[assignment]
                    stop_ctx[sc]["after_hist"][f.delta] += 1  # type: ignore[index]
                    entry["remaining"] -= 1
                    if entry["remaining"] > 0:
                        new_pending.append(entry)
                pending = new_pending

            # If current codon is a stop, snapshot the before-window uplift values.
            if codon in STOP_CODONS:
                sc = codon
                for u in list(prev_u):
                    stop_ctx[sc]["before_sum"] = int(stop_ctx[sc]["before_sum"]) + u  # type: ignore[assignment]
                    stop_ctx[sc]["before_count"] = int(stop_ctx[sc]["before_count"]) + 1  # type: ignore[assignment]
                    stop_ctx[sc]["before_hist"][u] += 1  # type: ignore[index]
                pending.append({"stop": sc, "remaining": stop_window})

            prev_u.append(f.delta)

        if out_writer is not None:
            out_writer.writerow(
                {
                    "record_id": record_id,
                    "segment": segment_id,
                    "frame": frame,
                    "codon_index": codon_index,
                    "base_pos": base_pos,
                    "codon": codon,
                    "aa": f.aa,
                    "bits": f.bits,
                    "N": f.n,
                    "Fold6": f.w,
                    "V": f.v,
                    "Delta": f.delta,
                    "is_boundary": int(f.is_boundary),
                    "is_start": is_start,
                    "is_stop": is_stop,
                }
            )

        codon_index += 1

    summary: dict[str, object] = {
        "record_id": record_id,
        "segment": segment_id,
        "frame": frame,
        "start_base": start_base,
        "end_base_exclusive": end_base_exclusive,
        "codons": codon_index,
        "boundary_count": boundary_count,
        "start_count": start_count,
        "stop_count": stop_count,
        "stop_codon_counts": _counter_dict(stop_codon_counts),
        "start_VDelta_hist": {f"{k[0]},{k[1]}": int(v) for k, v in start_vdelta_hist.items()},
        "stop_VDelta_hist": {f"{k[0]},{k[1]},{k[2]}": int(v) for k, v in stop_vdelta_hist.items()},
        "V_hist": _counter_dict(v_hist),
        "Delta_hist": _counter_dict(delta_hist),
        "aa_counts": _counter_dict(aa_counts),
        "codon_counts": _counter_dict(codon_counts),
    }

    if stop_window > 0:
        ctx_out: dict[str, object] = {}
        for sc in STOP_CODONS:
            before_count = int(stop_ctx[sc]["before_count"])
            after_count = int(stop_ctx[sc]["after_count"])
            before_sum = int(stop_ctx[sc]["before_sum"])
            after_sum = int(stop_ctx[sc]["after_sum"])
            ctx_out[sc] = {
                "window": stop_window,
                "before_mean": (before_sum / before_count) if before_count > 0 else None,
                "after_mean": (after_sum / after_count) if after_count > 0 else None,
                "before_hist": _counter_dict(stop_ctx[sc]["before_hist"]),  # type: ignore[arg-type]
                "after_hist": _counter_dict(stop_ctx[sc]["after_hist"]),  # type: ignore[arg-type]
                "before_count": before_count,
                "after_count": after_count,
            }
        summary["stop_context_uplift"] = ctx_out

    return summary


def main() -> None:
    args = parse_args()
    if not args.out and not args.summary_out:
        raise SystemExit("At least one of --out or --summary-out must be provided.")

    out_writer = None
    out_f = None
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_f = out_path.open("w", encoding="utf-8", newline="")
        out_writer = csv.DictWriter(
            out_f,
            fieldnames=[
                "record_id",
                "segment",
                "frame",
                "codon_index",
                "base_pos",
                "codon",
                "aa",
                "bits",
                "N",
                "Fold6",
                "V",
                "Delta",
                "is_boundary",
                "is_start",
                "is_stop",
            ],
            delimiter="\t",
        )
        out_writer.writeheader()

    summary_f = None
    if args.summary_out:
        summary_path = Path(args.summary_out)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_f = summary_path.open("w", encoding="utf-8")

    try:
        for rid, seq in iter_fasta(args.fasta):
            if args.orfs:
                orfs = find_orfs(seq, frame=args.frame, min_codons=args.min_codons)
                if not orfs:
                    continue
                for j, (s, t) in enumerate(orfs, start=1):
                    seg = f"orf{j}:{s}-{t}"
                    summary = process_segment(
                        seq,
                        frame=args.frame,
                        segment_id=seg,
                        mu=MU_STAR,
                        record_id=rid,
                        out_writer=out_writer,
                        stop_window=int(args.stop_window),
                        start_base=s,
                        end_base_exclusive=t + 3,
                    )
                    if summary_f is not None:
                        summary_f.write(json.dumps(summary, ensure_ascii=False) + "\n")
            else:
                summary = process_segment(
                    seq,
                    frame=args.frame,
                    segment_id="full",
                    mu=MU_STAR,
                    record_id=rid,
                    out_writer=out_writer,
                    stop_window=int(args.stop_window),
                    start_base=0,
                    end_base_exclusive=len(seq),
                )
                if summary_f is not None:
                    summary_f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    finally:
        if out_f is not None:
            out_f.close()
        if summary_f is not None:
            summary_f.close()


if __name__ == "__main__":
    main()


