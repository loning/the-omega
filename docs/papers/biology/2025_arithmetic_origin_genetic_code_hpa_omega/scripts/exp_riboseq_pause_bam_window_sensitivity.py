# -*- coding: utf-8 -*-
"""
Robustness / sensitivity sweep for the raw-read BAM pausing endpoint (H3-3e).

This script re-runs the BAM pausing analysis under a small set of parameter
variants (read-length filter and read-site definition) and reports the
random-effects meta-analysis on pause-index effect size d (high ΔU vs low ΔU).

Outputs:
  - sections/generated/riboseq_pause_bam_window_sensitivity.tex
  - sections/generated/riboseq_pause_bam_window_sensitivity.tex.meta.json
  - data/_cache/riboseq_pause_bam_window_sensitivity.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from cache_manager import cache_meta_path, write_json_atomic, write_text_atomic  # noqa: E402
from exp_riboseq_pause_bam_window import (  # noqa: E402
    TrackSpec,
    _default_tracks_json,
    _load_stop_candidates,
    analyze_one_bam,
    cache_dir,
    generated_dir,
    load_tracks_json,
    random_effects_meta,
    root_dir,
)


@dataclass(frozen=True)
class SweepConfig:
    config_id: str
    min_mapq: int
    min_align_len: int
    max_align_len: int
    read_site: str
    psite_offset_nt: int


def _fmt(x: float | None, *, nd: int = 2) -> str:
    if x is None:
        return "--"
    try:
        v = float(x)
    except Exception:
        return "--"
    if v != v:  # NaN
        return "--"
    return f"{v:.{nd}f}"


def main() -> None:
    ap = argparse.ArgumentParser(description="H3-3e: sensitivity sweep for BAM pausing meta-analysis.")
    ap.add_argument("--k", type=int, default=10, help="Window size in codons (must match stop_context_candidates.jsonl).")
    ap.add_argument("--body-offset-nt", type=int, default=300, help="Offset upstream of stop for body baseline window (nt).")
    ap.add_argument(
        "--in-jsonl",
        default=str(root_dir() / "data" / "refseq_hsapiens_mrna" / "stop_context_candidates.jsonl"),
        help="Input stop-context candidates JSONL.",
    )
    ap.add_argument("--tracks-json", default=str(_default_tracks_json()), help="Optional JSON listing BAM tracks.")
    ap.add_argument(
        "--include-tracks-json",
        action="store_true",
        help="When --bam is provided, also include tracks from --tracks-json (default: ignore tracks-json to avoid duplicates).",
    )
    ap.add_argument("--bam", action="append", default=[], help="BAM path (repeatable).")
    ap.add_argument("--track-id", action="append", default=[], help="Track id label for each --bam (repeatable).")
    ap.add_argument("--strip-version", action="store_true", help="Allow mapping record_id by stripping version suffix (NM_... .2 -> NM_...).")
    ap.add_argument("--force", action="store_true", help="Force recomputation (ignore cached outputs).")
    args = ap.parse_args()

    in_path = Path(args.in_jsonl)
    if not in_path.exists():
        raise SystemExit(f"Missing input: {in_path}")

    rows = _load_stop_candidates(in_path, k=int(args.k))
    if not rows:
        raise SystemExit(f"No rows with k={args.k} found in {in_path}")

    out_tex = generated_dir() / "riboseq_pause_bam_window_sensitivity.tex"

    # Track loading (same semantics as exp_riboseq_pause_bam_window.py)
    tracks: list[TrackSpec] = []
    bam_args = [str(x).strip() for x in (args.bam or []) if str(x).strip()]
    ids = [str(x).strip() for x in (args.track_id or []) if str(x).strip()]

    tracks_json_path = Path(str(args.tracks_json)) if str(args.tracks_json).strip() else None
    tracks_json_used: Path | None = None
    if tracks_json_path is not None and tracks_json_path.exists() and (not bam_args or bool(args.include_tracks_json)):
        tracks.extend(load_tracks_json(tracks_json_path))
        tracks_json_used = tracks_json_path

    for i, bam_s in enumerate(bam_args):
        bam_p = Path(bam_s)
        if not bam_p.is_absolute():
            bam_p = root_dir() / bam_p
        track_id = ids[i] if i < len(ids) and ids[i] else bam_p.stem
        tracks.append(TrackSpec(track_id=track_id, bam=bam_p))

    if not tracks:
        raise SystemExit(
            "No BAM tracks provided.\n\n"
            "Use either:\n"
            "  python scripts/exp_riboseq_pause_bam_window_sensitivity.py --bam <path> [--track-id <name>] ...\n"
            "or create a config file at:\n"
            f"  {args.tracks_json}\n"
        )

    sweep = [
        SweepConfig(
            config_id="baseline_mid_25_35",
            min_mapq=20,
            min_align_len=25,
            max_align_len=35,
            read_site="midpoint",
            psite_offset_nt=12,
        ),
        SweepConfig(
            config_id="mid_28_32",
            min_mapq=20,
            min_align_len=28,
            max_align_len=32,
            read_site="midpoint",
            psite_offset_nt=12,
        ),
        SweepConfig(
            config_id="psite12_25_35",
            min_mapq=20,
            min_align_len=25,
            max_align_len=35,
            read_site="psite",
            psite_offset_nt=12,
        ),
    ]

    meta = {
        "analysis": "riboseq_pause_bam_window_sensitivity",
        "k": int(args.k),
        "body_offset_nt": int(args.body_offset_nt),
        "strip_version": bool(args.strip_version),
        "tracks_json": str(tracks_json_used) if tracks_json_used is not None else "",
        "track_ids": [t.track_id for t in tracks],
        "bams": [str(t.bam) for t in tracks],
        "sweep": [c.__dict__ for c in sweep],
    }
    if out_tex.exists() and cache_meta_path(out_tex).exists() and not args.force:
        try:
            prev = json.loads(cache_meta_path(out_tex).read_text(encoding="utf-8"))
            if isinstance(prev, dict) and all(prev.get(k) == meta.get(k) for k in meta.keys()):
                print(f"[cache] hit: {out_tex}", flush=True)
                return
        except Exception:
            pass

    results: list[dict[str, Any]] = []
    for cfg in sweep:
        track_results: list[dict[str, Any]] = []
        for t in tracks:
            track_results.append(
                analyze_one_bam(
                    track_id=str(t.track_id),
                    bam_path=Path(t.bam),
                    rows=rows,
                    k_codons=int(args.k),
                    body_offset_nt=int(args.body_offset_nt),
                    min_mapq=int(cfg.min_mapq),
                    min_align_len=int(cfg.min_align_len),
                    max_align_len=int(cfg.max_align_len),
                    read_site=str(cfg.read_site),
                    psite_offset_nt=int(cfg.psite_offset_nt),
                    strip_version=bool(args.strip_version),
                )
            )
        meta_re = random_effects_meta(track_results, "high_diff_vs_low_diff")
        results.append({"config": cfg.__dict__, "meta": meta_re, "n_tracks_total": int(len(track_results))})

    out = {"meta": meta, "results": results}
    write_json_atomic(cache_dir() / "riboseq_pause_bam_window_sensitivity.json", out)

    lines: list[str] = [
        "\\paragraph{Robustness: read-length and P-site sensitivity (BAM pausing meta-analysis).}",
        "We re-ran the raw-read BAM pausing endpoint under a small set of parameter variants (read-length filters and alternative read-site definitions) and report the random-effects meta-analysis on pause-index effect size $d$ (high $\\Delta U$ vs low).",
        "",
        "\\begin{center}\\small",
        "\\begin{tabular}{lrrrr}\\toprule",
        "Config & $n_{\\mathrm{tracks}}$ & $d$ & 95\\% CI & $I^2$ \\\\",
        "\\midrule",
    ]

    for r in results:
        cfg = r.get("config", {})
        m = r.get("meta", {})
        n = m.get("n_studies")
        cfg_id = str(cfg.get("config_id", "") or "")

        if m.get("insufficient_data"):
            lines.append(f"\\path{{{cfg_id}}} & {int(n or 0)} & -- & -- & -- \\\\")
            continue

        d = _fmt(m.get("random_effect"), nd=2)
        ci = f"[{_fmt(m.get('ci_95_low'), nd=2)}, {_fmt(m.get('ci_95_high'), nd=2)}]"
        i2 = f"{_fmt(m.get('I2_percent'), nd=1)}\\%"
        lines.append(f"\\path{{{cfg_id}}} & {int(n or 0)} & {d} & {ci} & {i2} \\\\")

    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{center}"])

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    print(f"Wrote: {out_tex}", flush=True)


if __name__ == "__main__":
    main()

