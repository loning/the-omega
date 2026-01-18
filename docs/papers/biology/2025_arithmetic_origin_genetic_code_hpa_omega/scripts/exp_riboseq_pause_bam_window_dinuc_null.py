# -*- coding: utf-8 -*-
"""
ISA-P3: Dinucleotide-preserving null-of-null for the BAM pausing endpoint.

Motivation:
  The raw-read BAM pausing proxy (pause-index) shows a positive association with
  high-ΔU stop windows across multiple tracks, but ΔU is itself correlated with
  local composition features. This experiment conditions on composition by
  constructing a per-window dinucleotide-preserving shuffle null.

Method:
  For each transcript (terminal stop context, k codons), compute a composition-
  conditioned z-score:
    zΔU = (ΔU_obs - mean(ΔU_shuffled)) / sd(ΔU_shuffled)
  where shuffles preserve the exact dinucleotide multiset within each window
  (Eulerian-trail shuffle), applied separately to the before/after windows.

  Then, for each BAM track, test whether pause-index correlates with zΔU and
  whether pause-index differs between high vs low zΔU quantiles.

Inputs:
  - data/refseq_hsapiens_mrna/stop_context_candidates.jsonl (k=10 by default)
  - config/riboseq_bam_tracks.json (default), or --bam/--track-id overrides

Outputs:
  - sections/generated/riboseq_pause_bam_window_dinuc_null.tex
  - sections/generated/riboseq_pause_bam_window_dinuc_null.tex.meta.json
  - data/_cache/riboseq_pause_bam_window_dinuc_null.json
"""

from __future__ import annotations

import argparse
import hashlib
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
from genetic_code_tools import fold_codon
from stats_tools import cohen_d


SCRIPT_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
NUCS = "ACGU"


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


def _file_fingerprint(path: Path | None) -> dict[str, object]:
    if path is None:
        return {"missing": True}
    if not path.exists():
        return {"name": str(path), "missing": True}
    st = path.stat()
    return {
        "name": str(path),
        "bytes": int(st.st_size),
        "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
    }


def _fmt(x: float | None, *, nd: int = 3) -> str:
    if x is None:
        return "--"
    try:
        v = float(x)
    except Exception:
        return "--"
    if not np.isfinite(v):
        return "--"
    return f"{v:.{nd}f}"


def _p_fmt(p: float | None) -> str:
    if p is None:
        return "--"
    try:
        v = float(p)
    except Exception:
        return "--"
    if not np.isfinite(v):
        return "--"
    if v < 0.001:
        return "$<$0.001"
    return f"{v:.3f}"


def _normalize_rna(seq: str) -> str:
    return str(seq).strip().upper().replace("T", "U")


def _stable_seed_u32(tag: str) -> int:
    h = hashlib.sha256(tag.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def dinuc_shuffle(seq: str, rng: np.random.Generator) -> str:
    """
    Generate a random sequence with the same dinucleotide multiset as seq.
    Uses Hierholzer's algorithm for an Eulerian trail on the dinucleotide graph.
    """
    s = _normalize_rna(seq)
    if len(s) <= 2:
        return s
    if any(ch not in NUCS for ch in s):
        return ""

    edges: dict[str, list[str]] = {b: [] for b in NUCS}
    for i in range(len(s) - 1):
        a = s[i]
        b = s[i + 1]
        edges[a].append(b)
    for a in NUCS:
        rng.shuffle(edges[a])

    start = s[0] if s[0] in NUCS else "A"
    stack = [start]
    path: list[str] = []
    while stack:
        v = stack[-1]
        if edges.get(v):
            stack.append(edges[v].pop())
        else:
            path.append(stack.pop())
    out = "".join(reversed(path))
    return out[: len(s)]


def window_mean_uplift(seq: str) -> float:
    s = _normalize_rna(seq)
    if len(s) % 3 != 0:
        return float("nan")
    total = 0.0
    n = 0
    for i in range(0, len(s), 3):
        c = s[i : i + 3]
        if len(c) != 3 or any(ch not in NUCS for ch in c):
            return float("nan")
        total += float(fold_codon(c, MU_STAR).delta)
        n += 1
    return (total / n) if n else float("nan")


@dataclass(frozen=True)
class DinucNullStats:
    diff_obs: float
    null_mean: float
    null_sd: float
    z: float
    p_emp_two_sided: float


def dinuc_null_zdiff(
    before_seq: str,
    after_seq: str,
    *,
    n_shuffles: int,
    seed: int,
) -> DinucNullStats | None:
    before = _normalize_rna(before_seq)
    after = _normalize_rna(after_seq)
    if not before or not after:
        return None
    if len(before) != len(after) or len(before) % 3 != 0:
        return None
    if any(ch not in NUCS for ch in before) or any(ch not in NUCS for ch in after):
        return None

    diff_obs = float(window_mean_uplift(after) - window_mean_uplift(before))
    if not np.isfinite(diff_obs):
        return None

    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    diffs = np.empty(int(n_shuffles), dtype=float)
    for i in range(int(n_shuffles)):
        b = dinuc_shuffle(before, rng)
        a = dinuc_shuffle(after, rng)
        if not b or not a:
            diffs[i] = float("nan")
            continue
        ub = window_mean_uplift(b)
        ua = window_mean_uplift(a)
        diffs[i] = float(ua - ub) if np.isfinite(ub) and np.isfinite(ua) else float("nan")

    diffs = diffs[np.isfinite(diffs)]
    if diffs.size < max(20, int(n_shuffles) // 2):
        return None

    null_mean = float(np.mean(diffs))
    null_sd = float(np.std(diffs, ddof=1))
    z = float((diff_obs - null_mean) / null_sd) if null_sd > 0 else float("nan")

    centered = np.abs(diffs - null_mean)
    t = float(abs(diff_obs - null_mean))
    p_emp = float((np.sum(centered >= t) + 1.0) / (diffs.size + 1.0))
    return DinucNullStats(
        diff_obs=float(diff_obs),
        null_mean=float(null_mean),
        null_sd=float(null_sd),
        z=float(z),
        p_emp_two_sided=float(p_emp),
    )


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


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="ISA-P3: dinuc-shuffle null-of-null for BAM pausing endpoint.")
    ap.add_argument("--k", type=int, default=10, help="Window size in codons (must match stop_context_candidates.jsonl).")
    ap.add_argument("--n-shuffles", type=int, default=200, help="Dinucleotide shuffles per transcript window.")
    ap.add_argument("--quantile", type=float, default=0.25, help="High/low zΔU quantile cut (e.g., 0.25 -> quartiles).")
    ap.add_argument("--seed", type=int, default=0, help="Global seed (mixed with record_id for deterministic per-transcript seeds).")
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

    out_tex = generated_dir() / "riboseq_pause_bam_window_dinuc_null.tex"
    out_json = cache_dir() / "riboseq_pause_bam_window_dinuc_null.json"

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
            "  python scripts/exp_riboseq_pause_bam_window_dinuc_null.py --bam <path> [--track-id <name>] ...\n"
            "or create a config file at:\n"
            f"  {tracks_json_path or _default_tracks_json()}\n"
        )

    cache_key: dict[str, Any] = {
        "analysis": "riboseq_pause_bam_window_dinuc_null",
        "version": int(SCRIPT_VERSION),
        "k": int(args.k),
        "n_shuffles": int(args.n_shuffles),
        "quantile": float(args.quantile),
        "seed": int(args.seed),
        "body_offset_nt": int(args.body_offset_nt),
        "filters": {
            "min_mapq": int(args.min_mapq),
            "min_align_len": int(args.min_align_len),
            "max_align_len": int(args.max_align_len),
            "read_site": str(args.read_site),
            "psite_offset_nt": int(args.psite_offset_nt),
            "strip_version": bool(args.strip_version),
        },
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

    # ---- Build per-transcript dinuc-conditioned zΔU once (shared across tracks) ----
    base_by_rid: dict[str, dict[str, Any]] = {}
    for r in rows:
        rid = str(r.get("record_id") or "").strip()
        if not rid:
            continue
        base_by_rid.setdefault(rid, r)

    z_by_rid: dict[str, dict[str, float]] = {}
    n_ok = 0
    for rid, r in base_by_rid.items():
        before_seq = str(r.get("before_seq_dna") or "")
        after_seq = str(r.get("after_seq_dna") or "")
        if not before_seq or not after_seq:
            continue
        seed = int(args.seed) ^ _stable_seed_u32(f"dinuc_null:{rid}:k{int(args.k)}")
        st = dinuc_null_zdiff(before_seq, after_seq, n_shuffles=int(args.n_shuffles), seed=seed)
        if st is None:
            continue
        z_by_rid[rid] = {
            "diff_obs": float(st.diff_obs),
            "null_mean": float(st.null_mean),
            "null_sd": float(st.null_sd),
            "z_diff": float(st.z),
            "p_emp_two_sided": float(st.p_emp_two_sided),
        }
        n_ok += 1

    # ---- Per-track pausing overlay against zΔU ----
    track_results: list[dict[str, Any]] = []
    q = float(args.quantile)
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

        pis: list[float] = []
        zds: list[float] = []
        for rr in base.get("rows") or []:
            rid = str(rr.get("record_id") or "").strip()
            if not rid:
                continue
            zrec = z_by_rid.get(rid)
            if not zrec:
                continue
            z = float(zrec.get("z_diff", float("nan")))
            pi = float(rr.get("pause_index", float("nan")))
            if not (np.isfinite(z) and np.isfinite(pi)):
                continue
            pis.append(float(pi))
            zds.append(float(z))

        corr = _spearman(pis, zds)

        # High/low by zΔU quantiles (within-track).
        hi: list[float] = []
        lo: list[float] = []
        if len(zds) >= 20 and 0.0 < q < 0.5:
            zs = np.array(zds, dtype=float)
            lo_thr = float(np.quantile(zs, q))
            hi_thr = float(np.quantile(zs, 1.0 - q))
            for pi, z in zip(pis, zds):
                if z <= lo_thr:
                    lo.append(float(pi))
                elif z >= hi_thr:
                    hi.append(float(pi))
        comp = _compare(hi, lo)

        base["correlations"] = dict(base.get("correlations") or {}) | {"pause_index_vs_z_diff": corr}
        base["pairwise_comparisons"] = dict(base.get("pairwise_comparisons") or {}) | {"z_diff_high_vs_low": comp}
        base["dinuc_null"] = {
            "n_transcripts_total": int(len(base_by_rid)),
            "n_transcripts_with_z": int(n_ok),
            "n_shuffles": int(args.n_shuffles),
            "quantile": float(q),
        }
        track_results.append(base)

    meta = {"z_diff_high_vs_low": random_effects_meta(track_results, "z_diff_high_vs_low")}

    out_obj = {
        "meta": meta,
        "dinuc_null": {
            "k": int(args.k),
            "n_shuffles": int(args.n_shuffles),
            "seed": int(args.seed),
            "n_transcripts_total": int(len(base_by_rid)),
            "n_transcripts_with_z": int(n_ok),
        },
        "z_by_rid": z_by_rid,
        "tracks": track_results,
    }
    write_json_atomic(out_json, out_obj)

    # ---- Emit LaTeX fragment ----
    lines: list[str] = [
        "\\paragraph{ISA-P3: Dinucleotide-shuffle null-of-null for BAM pausing.}",
        "We compute a composition-conditioned $z\\Delta U$ per terminal-stop window by dinucleotide-preserving shuffles (Eulerian trail) and test whether the BAM pause-index remains associated with this residualized endpoint.",
        "",
        "\\begin{center}\\small",
        "\\begin{tabular}{lrrrrr}\\toprule",
        "Track & $n$ & $\\rho(PI, z\\Delta U)$ & $p$ & $d(z\\Delta U\\uparrow\\downarrow)$ & $p$ \\\\",
        "\\midrule",
    ]
    for tr in track_results:
        tid = str(tr.get("track_id", "") or "")
        track_tex = (r"\path{" + tid + r"}") if tid else ""
        corr = (tr.get("correlations") or {}).get("pause_index_vs_z_diff", {})
        comp = (tr.get("pairwise_comparisons") or {}).get("z_diff_high_vs_low", {})
        n = int(corr.get("n") or 0)
        lines.append(
            f"{track_tex} & {n} & {_fmt(corr.get('rho'), nd=3)} & {_p_fmt(corr.get('p'))} & "
            f"{_fmt(comp.get('cohens_d'), nd=2)} & {_p_fmt(comp.get('p'))} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{center}"])

    mr = meta.get("z_diff_high_vs_low", {})
    if not mr.get("insufficient_data"):
        lines.append(
            "Meta-analysis (random-effects) on pause-index $d$ (high $z\\Delta U$ vs low): "
            f"$d={_fmt(mr.get('random_effect'), nd=2)}$ "
            f"[{_fmt(mr.get('ci_95_low'), nd=2)}, {_fmt(mr.get('ci_95_high'), nd=2)}], "
            f"$I^2={_fmt(mr.get('I2_percent'), nd=1)}\\%$ (n={int(mr.get('n_studies', 0))})."
        )

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), cache_meta)
    print(f"Wrote: {out_tex}", flush=True)


if __name__ == "__main__":
    main()

