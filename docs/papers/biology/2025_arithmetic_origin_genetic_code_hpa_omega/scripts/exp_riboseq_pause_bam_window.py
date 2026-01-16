# -*- coding: utf-8 -*-
"""
Window-level Ribo-seq pausing from transcriptome-aligned BAM (raw reads).

This script is the BAM analogue of `exp_riboseq_pause_bigwig_window.py`. It
computes a stop-proximal pause index per transcript from aligned reads and
tests whether it correlates with the arithmetic Uplift windows.

Pause metric (per transcript):
  - pause_before: read-midpoint density on [stop-30nt, stop)
  - pause_body:   read-midpoint density on [stop-330nt, stop-300nt) (within CDS)
  - pause_index:  pause_before / pause_body

Inputs:
  - data/refseq_hsapiens_mrna/stop_context_candidates.jsonl (k=10 by default)
  - one or more BAM files aligned to the RefSeq transcriptome

Outputs:
  - sections/generated/riboseq_pause_bam_window.tex
  - data/_cache/riboseq_pause_bam_window.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

try:
    import pysam  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    pysam = None  # type: ignore[assignment]

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from cache_manager import cache_meta_path, write_json_atomic, write_text_atomic
from exp_cross_species_stop_context import random_effects_meta
from stats_tools import cohen_d


def root_dir() -> Path:
    return SCRIPT_DIR.parent


def data_dir() -> Path:
    return root_dir() / "data"


def cache_dir() -> Path:
    d = data_dir() / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass(frozen=True)
class TrackSpec:
    track_id: str
    bam: Path


def _default_tracks_json() -> Path:
    return root_dir() / "config" / "riboseq_bam_tracks.json"


def load_tracks_json(path: Path) -> list[TrackSpec]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    raw = obj.get("tracks") if isinstance(obj, dict) else obj
    if not isinstance(raw, list):
        raise SystemExit(f"Invalid tracks JSON (expected list or {{'tracks': [...]}}): {path}")

    out: list[TrackSpec] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise SystemExit(f"Invalid track entry (expected object): {entry}")
        track_id = str(entry.get("track_id") or "").strip()
        bam_s = str(entry.get("bam") or "").strip()
        if not track_id or not bam_s:
            raise SystemExit(f"Each track must have 'track_id' and 'bam': {entry}")
        bam = Path(bam_s)
        if not bam.is_absolute():
            bam = root_dir() / bam
        out.append(TrackSpec(track_id=track_id, bam=bam))
    return out


def _spearman(x: list[float], y: list[float]) -> dict[str, float]:
    xs = np.array(x, dtype=float)
    ys = np.array(y, dtype=float)
    m = np.isfinite(xs) & np.isfinite(ys)
    n = int(np.sum(m))
    if n < 10:
        return {"n": float(n), "rho": float("nan"), "p": float("nan")}
    rho, p = stats.spearmanr(xs[m], ys[m])
    return {"n": float(n), "rho": float(rho), "p": float(p)}


def _compare(xs_hi: list[float], xs_lo: list[float]) -> dict[str, float]:
    a = [float(v) for v in xs_hi if np.isfinite(v)]
    b = [float(v) for v in xs_lo if np.isfinite(v)]
    if len(a) < 10 or len(b) < 10:
        return {"n1": float(len(a)), "n2": float(len(b)), "cohens_d": float("nan"), "p": float("nan")}
    d = cohen_d(a, b)
    _, p = stats.ttest_ind(a, b, equal_var=False)
    return {"n1": float(len(a)), "n2": float(len(b)), "cohens_d": float(d) if d is not None else float("nan"), "p": float(p)}


def _fmt(x: float | None, *, nd: int = 3) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "--"
    return f"{float(x):.{nd}f}"


def _p_fmt(p: float | None) -> str:
    if p is None or (isinstance(p, float) and not np.isfinite(p)):
        return "--"
    if p < 0.001:
        return "$<$0.001"
    return f"{p:.3f}"


def _load_stop_candidates(path: Path, *, k: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if int(obj.get("k", -1)) != int(k):
                continue
            rows.append(obj)
    return rows


def _resolve_contig(refs: set[str], record_id: str, *, strip_version: bool) -> str | None:
    rid = (record_id or "").strip()
    if not rid:
        return None
    if rid in refs:
        return rid
    if strip_version and "." in rid:
        base = rid.split(".", 1)[0]
        if base in refs:
            return base
    return None


def _count_read_midpoints(
    bam: Any,
    *,
    contig: str,
    start: int,
    end: int,
    min_mapq: int,
    min_align_len: int,
    max_align_len: int,
) -> int:
    if start < 0 or end <= start:
        return 0
    n = 0
    for read in bam.fetch(contig, int(start), int(end)):
        if read.is_unmapped or read.is_secondary or read.is_supplementary:
            continue
        if int(getattr(read, "mapping_quality", 0) or 0) < int(min_mapq):
            continue
        alen = int(getattr(read, "query_alignment_length", 0) or 0)
        if int(min_align_len) > 0 and alen < int(min_align_len):
            continue
        if int(max_align_len) > 0 and alen > int(max_align_len):
            continue
        r0 = read.reference_start
        r1 = read.reference_end
        if r0 is None or r1 is None:
            continue
        mid = (int(r0) + int(r1)) // 2
        if mid < int(start) or mid >= int(end):
            continue
        n += 1
    return int(n)


def analyze_one_bam(
    *,
    track_id: str,
    bam_path: Path,
    rows: list[dict[str, Any]],
    k_codons: int,
    body_offset_nt: int,
    min_mapq: int,
    min_align_len: int,
    max_align_len: int,
    strip_version: bool,
) -> dict[str, Any]:
    if pysam is None:
        raise SystemExit("Missing dependency: pysam. Install into the active environment.")
    if not bam_path.exists():
        raise SystemExit(f"Missing BAM: {bam_path}")
    if not (bam_path.with_suffix(bam_path.suffix + ".bai").exists() or bam_path.with_suffix(".bai").exists()):
        raise SystemExit(f"Missing BAM index (.bai) for: {bam_path}")

    bam = pysam.AlignmentFile(str(bam_path), "rb")
    refs = set(bam.references or [])

    # stop_context_candidates.jsonl contains multiple "group_label" subsets that may
    # repeat the same transcript/stop coordinates. For pausing correlations we must
    # operate at the transcript level, so we compute pause metrics once per record_id
    # and then reuse them for the subset-based comparisons.
    base_by_rid: dict[str, dict[str, Any]] = {}
    groups_by_rid: dict[str, set[str]] = {}
    for r in rows:
        rid = str(r.get("record_id") or "").strip()
        if not rid:
            continue
        base_by_rid.setdefault(rid, r)
        groups_by_rid.setdefault(rid, set()).add(str(r.get("group_label") or "").strip())

    out_by_rid: dict[str, dict[str, Any]] = {}
    n_mapped = 0
    n_used = 0

    k_nt = 3 * int(k_codons)
    body_w = 3 * int(k_codons)

    for rid0, r in base_by_rid.items():
        rid0 = str(r.get("record_id") or "")
        contig = _resolve_contig(refs, rid0, strip_version=bool(strip_version))
        if contig is None:
            continue

        stop_base = r.get("stop_base")
        start_base = r.get("start_base")
        if stop_base is None or start_base is None:
            continue
        try:
            stop_base_i = int(stop_base)
            start_base_i = int(start_base)
        except Exception:
            continue
        if stop_base_i < k_nt:
            continue

        before_t0 = stop_base_i - k_nt
        before_t1 = stop_base_i

        body_t1 = stop_base_i - int(body_offset_nt)
        body_t0 = body_t1 - body_w
        body_ok = body_t0 >= int(start_base_i)

        n_mapped += 1

        before_cnt = _count_read_midpoints(
            bam,
            contig=contig,
            start=before_t0,
            end=before_t1,
            min_mapq=int(min_mapq),
            min_align_len=int(min_align_len),
            max_align_len=int(max_align_len),
        )
        before = float(before_cnt) / float(k_nt)

        if body_ok:
            body_cnt = _count_read_midpoints(
                bam,
                contig=contig,
                start=body_t0,
                end=body_t1,
                min_mapq=int(min_mapq),
                min_align_len=int(min_align_len),
                max_align_len=int(max_align_len),
            )
            body = float(body_cnt) / float(body_w)
        else:
            body_cnt = 0
            body = float("nan")

        pause_index = float(before / body) if np.isfinite(before) and np.isfinite(body) and body > 0 else float("nan")

        n_used += 1
        out_by_rid[rid0] = (
            {
                "record_id": rid0,
                "bam_contig": contig,
                "stop_codon": str(r.get("stop_codon") or ""),
                "u_before": float(r.get("before_mean_delta")) if r.get("before_mean_delta") is not None else float("nan"),
                "u_after": float(r.get("after_mean_delta")) if r.get("after_mean_delta") is not None else float("nan"),
                "diff": float(r.get("diff")) if r.get("diff") is not None else float("nan"),
                "pause_before": float(before),
                "pause_body": float(body),
                "pause_index": float(pause_index),
                "pause_before_n": float(before_cnt),
                "pause_body_n": float(body_cnt),
            }
        )

    try:
        bam.close()
    except Exception:
        pass
    out_rows = list(out_by_rid.values())

    corr = {
        "pause_before_vs_u_before": _spearman([rr["pause_before"] for rr in out_rows], [rr["u_before"] for rr in out_rows]),
        "pause_before_vs_diff": _spearman([rr["pause_before"] for rr in out_rows], [rr["diff"] for rr in out_rows]),
        "pause_index_vs_u_before": _spearman([rr["pause_index"] for rr in out_rows], [rr["u_before"] for rr in out_rows]),
        "pause_index_vs_diff": _spearman([rr["pause_index"] for rr in out_rows], [rr["diff"] for rr in out_rows]),
    }

    by_group: dict[str, list[float]] = {}
    for rid, groups in groups_by_rid.items():
        rr = out_by_rid.get(rid)
        if rr is None:
            continue
        pi = float(rr.get("pause_index", float("nan")))
        for g in groups:
            if not g:
                continue
            by_group.setdefault(g, []).append(pi)

    comps = {
        "high_after_vs_low_after": _compare(by_group.get("high_after", []), by_group.get("low_after", [])),
        "matched_after_high_vs_matched_after_low": _compare(by_group.get("matched_after_high", []), by_group.get("matched_after_low", [])),
        "high_diff_vs_low_diff": _compare(by_group.get("high_diff", []), by_group.get("low_diff", [])),
    }

    return {
        "species": track_id,  # for meta-analysis helper
        "track_id": track_id,
        "bam": str(bam_path),
        "k_codons": int(k_codons),
        "body_offset_nt": int(body_offset_nt),
        "filters": {
            "min_mapq": int(min_mapq),
            "min_align_len": int(min_align_len),
            "max_align_len": int(max_align_len),
            "strip_version": bool(strip_version),
        },
        "n_candidates": int(len(rows)),
        "n_candidates_unique": int(len(base_by_rid)),
        "n_mapped_bam_refs": int(n_mapped),
        "n_used_pause": int(n_used),
        "correlations": corr,
        "pairwise_comparisons": comps,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Module E (H3-3c): BAM pausing vs Uplift (raw reads).")
    ap.add_argument("--k", type=int, default=10, help="Window size in codons (must match stop_context_candidates.jsonl).")
    ap.add_argument("--body-offset-nt", type=int, default=300, help="Offset upstream of stop for body baseline window (nt).")
    ap.add_argument(
        "--in-jsonl",
        default=str(data_dir() / "refseq_hsapiens_mrna" / "stop_context_candidates.jsonl"),
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
    ap.add_argument("--min-mapq", type=int, default=20, help="Min MAPQ filter (0 disables).")
    ap.add_argument("--min-align-len", type=int, default=25, help="Min aligned length filter (0 disables).")
    ap.add_argument("--max-align-len", type=int, default=35, help="Max aligned length filter (0 disables).")
    ap.add_argument("--strip-version", action="store_true", help="Allow mapping record_id by stripping version suffix (NM_... .2 -> NM_...).")
    ap.add_argument("--force", action="store_true", help="Force recomputation (ignore cached outputs).")
    args = ap.parse_args()

    in_path = Path(args.in_jsonl)
    if not in_path.exists():
        raise SystemExit(f"Missing input: {in_path}")

    rows = _load_stop_candidates(in_path, k=int(args.k))
    if not rows:
        raise SystemExit(f"No rows with k={args.k} found in {in_path}")

    out_tex = generated_dir() / "riboseq_pause_bam_window.tex"
    meta = {
        "analysis": "riboseq_pause_bam_window",
        "k": int(args.k),
        "body_offset_nt": int(args.body_offset_nt),
        "min_mapq": int(args.min_mapq),
        "min_align_len": int(args.min_align_len),
        "max_align_len": int(args.max_align_len),
        "strip_version": bool(args.strip_version),
    }
    if out_tex.exists() and cache_meta_path(out_tex).exists() and not args.force:
        try:
            prev = json.loads(cache_meta_path(out_tex).read_text(encoding="utf-8"))
            if isinstance(prev, dict) and all(prev.get(k) == meta.get(k) for k in meta.keys()):
                print(f"[cache] hit: {out_tex}")
                return
        except Exception:
            pass

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
            "  python scripts/exp_riboseq_pause_bam_window.py --bam <path> [--track-id <name>] ...\n"
            "or create a config file at:\n"
            f"  {tracks_json or _default_tracks_json()}\n"
        )

    # Run per-track analyses
    track_results: list[dict[str, Any]] = []
    for t in tracks:
        print(f"[run] {t.track_id} -> {t.bam}", flush=True)
        track_results.append(
            analyze_one_bam(
                track_id=str(t.track_id),
                bam_path=Path(t.bam),
                rows=rows,
                k_codons=int(args.k),
                body_offset_nt=int(args.body_offset_nt),
                min_mapq=int(args.min_mapq),
                min_align_len=int(args.min_align_len),
                max_align_len=int(args.max_align_len),
                strip_version=bool(args.strip_version),
            )
        )

    meta_re = random_effects_meta(track_results, "high_diff_vs_low_diff")
    out = {"meta": meta_re, "tracks": track_results}
    write_json_atomic(cache_dir() / "riboseq_pause_bam_window.json", out)

    # Emit LaTeX fragment
    meta_line = ""
    if not meta_re.get("insufficient_data"):
        meta_line = (
            f"Meta-analysis (random-effects) on pause-index $d$ (high $\\Delta U$ vs low): "
            f"$d={_fmt(meta_re.get('random_effect'), nd=2)}$ "
            f"[{_fmt(meta_re.get('ci_95_low'), nd=2)}, {_fmt(meta_re.get('ci_95_high'), nd=2)}], "
            f"$I^2={_fmt(meta_re.get('I2_percent'), nd=1)}\\%$."
        )

    lines: list[str] = [
        "\\paragraph{Ribo-seq pausing from BAM alignments (raw-read pipeline).}",
        "We aligned raw Ribo-seq reads to a RefSeq transcriptome reference and computed a stop-proximal pause index per transcript, defined as the read-midpoint density in the $k$-codon window immediately upstream of the terminal stop divided by a same-length baseline window 300 nt upstream (within CDS when available).",
        "The table reports per-track results and a random-effects meta-analysis across tracks (not necessarily independent studies).",
        "",
        "\\begin{center}\\small",
        "\\begin{tabular}{lrrrrr}\\toprule",
        "Track & $n$ & $\\rho(PI, U_{\\mathrm{before}})$ & $\\rho(PI,\\Delta U)$ & $d(\\Delta U\\uparrow\\downarrow)$ & $p$ \\\\",
        "\\midrule",
    ]

    for s in track_results:
        track_id = str(s.get("track_id", "") or "")
        track_tex = (r"\path{" + track_id + r"}") if track_id else ""
        corr = s.get("correlations", {}).get("pause_index_vs_u_before", {})
        corr_d = s.get("correlations", {}).get("pause_index_vs_diff", {})
        comp = s.get("pairwise_comparisons", {}).get("high_diff_vs_low_diff", {})
        lines.append(
            f"{track_tex} & {int(s.get('n_used_pause',0))} & "
            f"{_fmt(corr.get('rho'))} & {_fmt(corr_d.get('rho'))} & "
            f"{_fmt(comp.get('cohens_d'), nd=2)} & {_p_fmt(comp.get('p'))} \\\\"
        )

    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{center}",
        ]
    )
    if meta_line:
        lines.append(meta_line)

    meta_out = dict(meta)
    meta_out.update(
        {
            "n_tracks": int(len(track_results)),
            "track_ids": [str(s.get("track_id", "") or "") for s in track_results],
            "bams": [str(s.get("bam", "") or "") for s in track_results],
            "tracks_json": str(tracks_json_used) if tracks_json_used is not None else "",
        }
    )
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta_out)
    print(f"Wrote: {out_tex}")


if __name__ == "__main__":
    main()
