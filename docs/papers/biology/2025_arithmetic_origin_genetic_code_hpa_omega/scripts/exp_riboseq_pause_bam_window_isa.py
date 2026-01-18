# -*- coding: utf-8 -*-
"""
ISA-P2: Raw-read Ribo-seq pausing overlay with ISA control features.

This is a lightweight extension of the standardized BAM pausing pipeline:
we keep the same pause-index definition, but stratify the stop-window sets by
ISA features:
  - stop family control features at m=6 under μ* (sector/Δ6; deterministic per stop)
  - stop+2nt refinement microstate projected to the m=6 anchor (m=10 -> prefix-6)

Primary endpoint in this script:
  Compare pause-index between boundary-anchored vs non-boundary-anchored stop+2nt
  contexts, pooling all terminal-stop candidates used by the BAM pausing pipeline.

Secondary endpoint:
  The same comparison within the pre-registered low-ΔU subset ("low_diff"), and
  stratified by stop codon where sample size permits.

Inputs:
  - data/refseq_hsapiens_mrna/stop_context_candidates.jsonl
  - config/riboseq_bam_tracks.json (default) or --bam/--track-id overrides

Outputs:
  - sections/generated/riboseq_pause_bam_window_isa.tex
  - sections/generated/riboseq_pause_bam_window_isa.tex.meta.json
  - data/_cache/riboseq_pause_bam_window_isa.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, write_json_atomic, write_text_atomic
from exp_cross_species_stop_context import random_effects_meta
from exp_riboseq_pause_bam_window import TrackSpec, _default_tracks_json, _load_stop_candidates, analyze_one_bam, load_tracks_json
from genetic_code_tools import fold_m, is_boundary_word
from stats_tools import cohen_d


SCRIPT_VERSION = 2
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}


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


def _file_fingerprint(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"name": str(path), "missing": True}
    st = path.stat()
    return {
        "name": str(path),
        "bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


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


def _tex_escape(s: str) -> str:
    return str(s).replace("_", "\\_")


def _normalize_rna(seq: str) -> str:
    return str(seq).strip().upper().replace("T", "U")


def _kmer_bits(seq: str) -> str:
    return "".join(MU_STAR[b] for b in seq)


@dataclass(frozen=True)
class Anchor10to6:
    motif5: str
    u6: str
    is_boundary: bool


def stop_plus2_anchor(stop_codon_rna: str, plus4_nt: str, after_nt6: str) -> Anchor10to6 | None:
    stop = _normalize_rna(stop_codon_rna)
    if len(stop) != 3:
        return None
    plus4 = _normalize_rna(plus4_nt)
    nt6 = _normalize_rna(after_nt6)
    plus5 = nt6[1] if len(nt6) >= 2 else ""
    if plus4 not in MU_STAR or plus5 not in MU_STAR or any(b not in MU_STAR for b in stop):
        return None
    motif5 = f"{stop}{plus4}{plus5}"
    n10 = int(_kmer_bits(motif5), 2)
    w10 = fold_m(n10, 10)
    u6 = str(w10[:6])
    return Anchor10to6(motif5=str(motif5), u6=u6, is_boundary=bool(is_boundary_word(u6)))


def _compare(xs_a: list[float], xs_b: list[float]) -> dict[str, float]:
    a = [float(v) for v in xs_a if np.isfinite(v)]
    b = [float(v) for v in xs_b if np.isfinite(v)]
    if len(a) < 10 or len(b) < 10:
        return {"n1": float(len(a)), "n2": float(len(b)), "cohens_d": float("nan"), "p": float("nan")}
    d = cohen_d(a, b)
    _, p = stats.ttest_ind(a, b, equal_var=False)
    return {"n1": float(len(a)), "n2": float(len(b)), "cohens_d": float(d) if d is not None else float("nan"), "p": float(p)}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ISA-P2: Ribo-seq BAM pausing overlay stratified by ISA features.")
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
    ap.add_argument(
        "--read-site",
        default="midpoint",
        choices=["midpoint", "fiveprime", "threeprime", "psite"],
        help="Which aligned site to count within windows: midpoint, 5' end, 3' end, or P-site (5' offset).",
    )
    ap.add_argument("--psite-offset-nt", type=int, default=12, help="P-site offset from 5' end (nt) when --read-site=psite.")
    ap.add_argument("--strip-version", action="store_true", help="Allow mapping record_id by stripping version suffix (NM_... .2 -> NM_...).")
    ap.add_argument("--force", action="store_true", help="Force recomputation (ignore cached outputs).")
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    in_path = Path(args.in_jsonl)
    if not in_path.exists():
        raise SystemExit(f"Missing input: {in_path}")

    rows = _load_stop_candidates(in_path, k=int(args.k))
    if not rows:
        raise SystemExit(f"No rows with k={args.k} found in {in_path}")

    out_tex = generated_dir() / "riboseq_pause_bam_window_isa.tex"
    out_json = cache_dir() / "riboseq_pause_bam_window_isa.json"

    tracks: list[TrackSpec] = []
    bam_args = [str(x).strip() for x in (args.bam or []) if str(x).strip()]
    ids = [str(x).strip() for x in (args.track_id or []) if str(x).strip()]

    tracks_json_path = Path(str(args.tracks_json)) if str(args.tracks_json).strip() else None
    if tracks_json_path is not None and tracks_json_path.exists() and (not bam_args or bool(args.include_tracks_json)):
        tracks.extend(load_tracks_json(tracks_json_path))

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
            "  python scripts/exp_riboseq_pause_bam_window_isa.py --bam <path> [--track-id <name>] ...\n"
            "or create a config file at:\n"
            f"  {tracks_json_path or _default_tracks_json()}\n"
        )

    cache_key: dict[str, Any] = {
        "analysis": "riboseq_pause_bam_window_isa",
        "version": int(SCRIPT_VERSION),
        "k": int(args.k),
        "body_offset_nt": int(args.body_offset_nt),
        "min_mapq": int(args.min_mapq),
        "min_align_len": int(args.min_align_len),
        "max_align_len": int(args.max_align_len),
        "read_site": str(args.read_site),
        "psite_offset_nt": int(args.psite_offset_nt),
        "strip_version": bool(args.strip_version),
        "inputs": {
            "stop_candidates": _file_fingerprint(in_path),
            "tracks_json": _file_fingerprint(tracks_json_path) if tracks_json_path is not None else {"missing": True},
            "bams": [_file_fingerprint(Path(t.bam)) for t in tracks],
        },
        "out": str(out_tex),
    }
    cache_meta = {"cache_key": cache_key, "cache_digest": cache_key_digest(cache_key)}
    if (not args.force) and cache_hit(out_tex, expected_meta=cache_meta, require_meta=True):
        print(f"[cache] hit: {out_tex}", flush=True)
        return

    # Per-track stratified comparisons.
    track_results: list[dict[str, Any]] = []
    for t in tracks:
        print(f"[run] {t.track_id} -> {t.bam}", flush=True)
        base = analyze_one_bam(
            track_id=str(t.track_id),
            bam_path=Path(t.bam),
            rows=rows,
            k_codons=int(args.k),
            body_offset_nt=int(args.body_offset_nt),
            min_mapq=int(args.min_mapq),
            min_align_len=int(args.min_align_len),
            max_align_len=int(args.max_align_len),
            read_site=str(args.read_site),
            psite_offset_nt=int(args.psite_offset_nt),
            strip_version=bool(args.strip_version),
            return_rows=True,
        )

        out_rows = base.get("rows") or []
        stop_codons = sorted({str(r.get("stop_codon") or "") for r in out_rows if str(r.get("stop_codon") or "")})

        all_boundary: list[float] = []
        all_non: list[float] = []
        lowdiff_boundary: list[float] = []
        lowdiff_non: list[float] = []

        by_stop_boundary: dict[str, list[float]] = {}
        by_stop_non: dict[str, list[float]] = {}
        by_stop_lowdiff_boundary: dict[str, list[float]] = {}
        by_stop_lowdiff_non: dict[str, list[float]] = {}

        for r in out_rows:
            pi = float(r.get("pause_index", float("nan")))
            if not np.isfinite(pi):
                continue
            stop = _normalize_rna(str(r.get("stop_codon") or ""))
            if stop == "":
                continue
            a = stop_plus2_anchor(stop, str(r.get("plus4_nt") or ""), str(r.get("after_nt6") or ""))
            if a is None:
                continue
            labels = set(str(x) for x in (r.get("group_labels") or []) if str(x).strip())

            if a.is_boundary:
                all_boundary.append(float(pi))
                by_stop_boundary.setdefault(stop, []).append(float(pi))
                if "low_diff" in labels:
                    lowdiff_boundary.append(float(pi))
                    by_stop_lowdiff_boundary.setdefault(stop, []).append(float(pi))
            else:
                all_non.append(float(pi))
                by_stop_non.setdefault(stop, []).append(float(pi))
                if "low_diff" in labels:
                    lowdiff_non.append(float(pi))
                    by_stop_lowdiff_non.setdefault(stop, []).append(float(pi))

        comps: dict[str, dict[str, float]] = {}
        comps["boundary_anchor_vs_non_overall"] = _compare(all_boundary, all_non)
        comps["low_diff_boundary_anchor_vs_non_overall"] = _compare(lowdiff_boundary, lowdiff_non)
        for stop in stop_codons:
            stop_n = _normalize_rna(stop)
            comps[f"boundary_anchor_vs_non_{stop_n}"] = _compare(by_stop_boundary.get(stop_n, []), by_stop_non.get(stop_n, []))
            comps[f"low_diff_boundary_anchor_vs_non_{stop_n}"] = _compare(
                by_stop_lowdiff_boundary.get(stop_n, []),
                by_stop_lowdiff_non.get(stop_n, []),
            )

        base["pairwise_comparisons"] = dict(base.get("pairwise_comparisons") or {}) | comps
        track_results.append(base)

    meta: dict[str, dict[str, Any]] = {
        "boundary_anchor_vs_non_overall": random_effects_meta(track_results, "boundary_anchor_vs_non_overall"),
        "low_diff_boundary_anchor_vs_non_overall": random_effects_meta(track_results, "low_diff_boundary_anchor_vs_non_overall"),
    }
    for stop in ("UAA", "UAG", "UGA"):
        meta[f"boundary_anchor_vs_non_{stop}"] = random_effects_meta(track_results, f"boundary_anchor_vs_non_{stop}")
        meta[f"low_diff_boundary_anchor_vs_non_{stop}"] = random_effects_meta(track_results, f"low_diff_boundary_anchor_vs_non_{stop}")

    out_obj = {"meta": meta, "tracks": track_results}
    write_json_atomic(out_json, out_obj)

    # Emit LaTeX fragment.
    lines: list[str] = [
        "\\paragraph{ISA-P2: Raw-read Ribo-seq pausing stratified by stop+2nt boundary anchors.}",
        "Using the standardized BAM pausing pipeline, we stratify terminal-stop contexts by whether the stop+2nt microstate (m=10) projects to an $m=6$ boundary anchor ($u\\in\\{100001,100101,101001\\}$).",
        "We report the effect size $d$ comparing boundary-anchored vs non-boundary contexts (boundary minus non-boundary), pooling all stop codons. (Stop-stratified and low-$\\Delta U$-only versions are exported to JSON for audit; many tracks are underpowered for those finer strata.)",
        "",
        "\\begin{center}\\small",
        "\\begin{tabular}{lrrrrr}\\toprule",
        "Track & $n$ & $n_{bdry}$ & $n_{non}$ & $d$ & $p$ \\\\",
        "\\midrule",
    ]

    for s in track_results:
        track_id = str(s.get("track_id", "") or "")
        track_tex = (r"\path{" + track_id + r"}") if track_id else ""
        comp = (s.get("pairwise_comparisons", {}) or {}).get("boundary_anchor_vs_non_overall", {})
        n = int(comp.get("n1", 0)) + int(comp.get("n2", 0))
        lines.append(
            f"{track_tex} & {n} & {int(comp.get('n1', 0))} & {int(comp.get('n2', 0))} & "
            f"{_fmt(comp.get('cohens_d'), nd=2)} & {_p_fmt(comp.get('p'))} \\\\"
        )

    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{center}"])

    mr = meta.get("boundary_anchor_vs_non_overall", {})
    if not mr.get("insufficient_data"):
        lines.append(
            "Meta-analysis (random-effects) for boundary vs non (pooled stops): "
            f"$d={_fmt(mr.get('random_effect'), nd=2)}$ "
            f"[{_fmt(mr.get('ci_95_low'), nd=2)}, {_fmt(mr.get('ci_95_high'), nd=2)}], "
            f"$I^2={_fmt(mr.get('I2_percent'), nd=1)}\\%$ (n={int(mr.get('n_studies', 0))})."
        )

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print(f"Wrote: {out_tex}", flush=True)


if __name__ == "__main__":
    main()
