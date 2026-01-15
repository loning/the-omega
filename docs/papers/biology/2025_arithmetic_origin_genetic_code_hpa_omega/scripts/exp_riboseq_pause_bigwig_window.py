# -*- coding: utf-8 -*-
"""
Window-level Ribo-seq pausing from GEO bigWig tracks (multi-dataset replication).

This script implements Module E (Ribo-seq mechanistic bridge) using preprocessed
bigWig coverage tracks from independent Ribo-seq studies, and tests whether
stop-proximal pausing correlates with the arithmetic Uplift windows.

Pipeline:
  1) Load RefSeq stop-context candidates (k=10) with U_before/U_after/diff.
  2) Map transcript coordinates to genome via UCSC refGene (hg19/hg38 inferred
     from bigWig chrom sizes).
  3) For each transcript stop, compute a pausing metric from bigWig coverage:
       - pause_before: mean coverage on [stop-30nt, stop)
       - pause_body:   mean coverage on [stop-330nt, stop-300nt) (within CDS)
       - pause_index:  pause_before / pause_body
  4) Report per-study correlations and stratified effect sizes, plus a simple
     random-effects meta-analysis across studies.

Dependencies:
  - numpy, scipy
  - pyBigWig (pip install pybigwig)
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

try:
    import pyBigWig  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    pyBigWig = None  # type: ignore[assignment]

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


def riboseq_dir() -> Path:
    d = data_dir() / "riboseq"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _infer_ucsc_build(chrom_sizes: dict[str, int]) -> str | None:
    # Use chr1 length as a robust assembly fingerprint.
    l = chrom_sizes.get("chr1")
    if l is None and "1" in chrom_sizes:
        l = chrom_sizes.get("1")
    if l is None:
        return None
    if int(l) == 248_956_422:
        return "hg38"
    if int(l) == 249_250_621:
        return "hg19"
    return None


def _ucsc_genepred_url(build: str) -> str:
    # Use the broad NCBI RefSeq genePred table to cover NM/NR/XM/XR accessions.
    return f"https://hgdownload.soe.ucsc.edu/goldenPath/{build}/database/ncbiRefSeq.txt.gz"


def _ensure_refgene(build: str) -> Path:
    out = cache_dir() / f"ucsc_ncbiRefSeq_{build}.txt.gz"
    if out.exists():
        return out
    url = _ucsc_genepred_url(build)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_bytes(_fetch(url))
    tmp.replace(out)
    return out


@dataclass(frozen=True)
class GenePred:
    name: str
    chrom: str
    strand: str
    exon_starts: tuple[int, ...]
    exon_ends: tuple[int, ...]

    def tx_len(self) -> int:
        return int(sum(e - s for s, e in zip(self.exon_starts, self.exon_ends)))


def _parse_int_list(s: str) -> tuple[int, ...]:
    s = s.strip().strip(",")
    if not s:
        return ()
    return tuple(int(x) for x in s.split(",") if x)


def load_refgene_index(build: str, *, keep_names: set[str]) -> dict[str, GenePred]:
    """
    Load a minimal NCBI RefSeq genePred index for the target transcript IDs.

    Note: GEO/RefSeq record IDs are often versioned (NM_... .2); UCSC refGene
    may store without version. We index both raw and version-stripped names.
    """
    path = _ensure_refgene(build)
    idx: dict[str, GenePred] = {}

    # keep both full and base IDs
    keep_bases = {n.split(".", 1)[0] for n in keep_names}

    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 11:
                continue
            name = parts[1]
            base = name.split(".", 1)[0]
            if name not in keep_names and base not in keep_bases:
                continue
            chrom = parts[2]
            strand = parts[3]
            exon_starts = _parse_int_list(parts[9])
            exon_ends = _parse_int_list(parts[10])
            if len(exon_starts) != len(exon_ends) or not exon_starts:
                continue
            gp = GenePred(
                name=name,
                chrom=chrom,
                strand=strand,
                exon_starts=exon_starts,
                exon_ends=exon_ends,
            )
            idx[name] = gp
            idx[base] = gp

    return idx


def slice_to_genomic_intervals(gp: GenePred, *, t0: int, t1: int) -> list[tuple[int, int]]:
    """
    Map transcript slice [t0,t1) to a list of genomic intervals [start,end).
    Intervals are returned on the reference (+) coordinate system (start<end).
    """
    if t0 < 0 or t1 < 0 or t1 <= t0:
        return []

    exons = list(zip(gp.exon_starts, gp.exon_ends))
    out: list[tuple[int, int]] = []

    if gp.strand == "+":
        offset = 0
        for start, end in exons:
            exon_len = end - start
            exon_t0 = offset
            exon_t1 = offset + exon_len
            a = max(t0, exon_t0)
            b = min(t1, exon_t1)
            if a < b:
                g0 = start + (a - exon_t0)
                g1 = start + (b - exon_t0)
                out.append((int(g0), int(g1)))
            offset += exon_len
        return out

    if gp.strand == "-":
        offset = 0
        for start, end in reversed(exons):
            exon_len = end - start
            exon_t0 = offset
            exon_t1 = offset + exon_len
            a = max(t0, exon_t0)
            b = min(t1, exon_t1)
            if a < b:
                g1 = end - (a - exon_t0)
                g0 = end - (b - exon_t0)
                out.append((int(g0), int(g1)))
            offset += exon_len
        return out

    return []


def _resolve_chrom(chrom: str, chrom_sizes: dict[str, int]) -> str | None:
    if chrom in chrom_sizes:
        return chrom
    if chrom.startswith("chr") and chrom[3:] in chrom_sizes:
        return chrom[3:]
    if ("chr" + chrom) in chrom_sizes:
        return "chr" + chrom
    return None


def bw_mean(bw: Any, *, chrom: str, intervals: list[tuple[int, int]]) -> float:
    vals: list[np.ndarray] = []
    for start, end in intervals:
        start_i = int(start)
        end_i = int(end)
        if start_i < 0:
            start_i = 0
        if end_i <= start_i:
            continue
        try:
            a = bw.values(chrom, start_i, end_i, numpy=True)
        except RuntimeError:
            continue
        if a is None:
            continue
        vals.append(np.array(a, dtype=float))
    if not vals:
        return float("nan")
    v = np.concatenate(vals)
    if v.size == 0:
        return float("nan")
    if not np.isfinite(v).any():
        return float("nan")
    return float(np.nanmean(v))


def bw_mean_multi(bws: list[Any], *, chrom: str, intervals: list[tuple[int, int]]) -> float:
    """
    Average the per-track window means across multiple bigWig tracks (replicates).
    """
    if not bws:
        return float("nan")
    means = [bw_mean(bw, chrom=chrom, intervals=intervals) for bw in bws]
    arr = np.array(means, dtype=float)
    return float(np.nanmean(arr)) if np.isfinite(arr).any() else float("nan")


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


def _pick_bigwig_file(study_dir: Path, *, prefer_regex: re.Pattern[str] | None) -> Path | None:
    cands = [p for p in study_dir.glob("*.bigWig")] + [p for p in study_dir.glob("*.bw")] + [p for p in study_dir.glob("*.bigwig")]
    if not cands:
        return None
    if prefer_regex is not None:
        rx = [p for p in cands if prefer_regex.search(p.name)]
        if rx:
            cands = rx
    # Prefer the largest file (often the union/coverage track).
    cands.sort(key=lambda p: p.stat().st_size, reverse=True)
    return cands[0]


def _pick_bigwig_tracks(study_dir: Path, *, prefer_regex: re.Pattern[str] | None) -> tuple[list[Path], list[Path]]:
    """
    Return (plus_tracks, minus_tracks).

    If the directory contains separate forward/reverse tracks (common in GEO tar bundles),
    use them; otherwise, treat it as unstranded and return the same single track for both.
    """
    fw = sorted([p for p in study_dir.glob("*FW*.bigwig")])
    rev = sorted([p for p in study_dir.glob("*Rev*.bigwig")])
    if fw and rev:
        return fw, rev

    single = _pick_bigwig_file(study_dir, prefer_regex=prefer_regex)
    if single is None:
        return [], []
    return [single], [single]


def analyze_one_bigwig(
    *,
    study_id: str,
    bw_plus_paths: list[Path],
    bw_minus_paths: list[Path],
    rows: list[dict[str, Any]],
    k_codons: int,
    body_offset_nt: int,
) -> dict[str, Any]:
    if pyBigWig is None:
        raise SystemExit("Missing dependency: pyBigWig. Install via `python -m pip install pybigwig`.")
    if not bw_plus_paths or not bw_minus_paths:
        raise SystemExit(f"Missing bigWig tracks for study: {study_id}")

    bw_plus = [pyBigWig.open(str(p)) for p in bw_plus_paths]
    bw_minus = [pyBigWig.open(str(p)) for p in bw_minus_paths]

    chrom_sizes = {k: int(v) for k, v in ((bw_plus[0] if bw_plus else bw_minus[0]).chroms() or {}).items()}
    build = _infer_ucsc_build(chrom_sizes) or "unknown"

    record_ids = {str(r.get("record_id") or "") for r in rows if str(r.get("record_id") or "").strip()}
    refgene = load_refgene_index(build, keep_names=record_ids) if build in ("hg19", "hg38") else {}

    out_rows: list[dict[str, Any]] = []
    n_mapped = 0
    n_used = 0

    k_nt = 3 * int(k_codons)
    body_w = 3 * int(k_codons)

    for r in rows:
        rid = str(r.get("record_id") or "")
        if not rid:
            continue
        gp = refgene.get(rid) or refgene.get(rid.split(".", 1)[0])
        if gp is None:
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

        chrom = _resolve_chrom(gp.chrom, chrom_sizes)
        if chrom is None:
            continue

        # stop-proximal upstream window
        before_t0 = stop_base_i - k_nt
        before_t1 = stop_base_i
        before_iv = slice_to_genomic_intervals(gp, t0=before_t0, t1=before_t1)

        # body baseline window (same length) at fixed offset upstream of stop
        body_t1 = stop_base_i - int(body_offset_nt)
        body_t0 = body_t1 - body_w
        if body_t0 < start_base_i:
            # don't cross the start codon / UTR; skip pause_index for this record
            body_iv: list[tuple[int, int]] = []
        else:
            body_iv = slice_to_genomic_intervals(gp, t0=body_t0, t1=body_t1)

        strand_bws = bw_plus if gp.strand == "+" else bw_minus
        pause_before = bw_mean_multi(strand_bws, chrom=chrom, intervals=before_iv)
        pause_body = bw_mean_multi(strand_bws, chrom=chrom, intervals=body_iv) if body_iv else float("nan")
        pause_index = float(pause_before / pause_body) if np.isfinite(pause_before) and np.isfinite(pause_body) and pause_body > 0 else float("nan")

        n_mapped += 1
        if not np.isfinite(pause_before):
            continue

        n_used += 1
        out_rows.append(
            {
                "record_id": rid,
                "stop_codon": str(r.get("stop_codon") or ""),
                "group_label": str(r.get("group_label") or ""),
                "u_before": float(r.get("before_mean_delta")) if r.get("before_mean_delta") is not None else float("nan"),
                "u_after": float(r.get("after_mean_delta")) if r.get("after_mean_delta") is not None else float("nan"),
                "diff": float(r.get("diff")) if r.get("diff") is not None else float("nan"),
                "pause_before": float(pause_before),
                "pause_body": float(pause_body),
                "pause_index": float(pause_index),
            }
        )

    for bw in bw_plus + bw_minus:
        try:
            bw.close()
        except Exception:
            pass

    # Per-study correlations (pause_index is the expression-normalized metric).
    corr = {
        "pause_before_vs_u_before": _spearman([rr["pause_before"] for rr in out_rows], [rr["u_before"] for rr in out_rows]),
        "pause_before_vs_diff": _spearman([rr["pause_before"] for rr in out_rows], [rr["diff"] for rr in out_rows]),
        "pause_index_vs_u_before": _spearman([rr["pause_index"] for rr in out_rows], [rr["u_before"] for rr in out_rows]),
        "pause_index_vs_diff": _spearman([rr["pause_index"] for rr in out_rows], [rr["diff"] for rr in out_rows]),
    }

    # Stratified comparisons on pause_index (proxy quantile groups from candidate builder).
    by_group: dict[str, list[float]] = {}
    for rr in out_rows:
        by_group.setdefault(rr["group_label"], []).append(float(rr["pause_index"]))

    comps = {
        "high_after_vs_low_after": _compare(by_group.get("high_after", []), by_group.get("low_after", [])),
        "matched_after_high_vs_matched_after_low": _compare(by_group.get("matched_after_high", []), by_group.get("matched_after_low", [])),
        "high_diff_vs_low_diff": _compare(by_group.get("high_diff", []), by_group.get("low_diff", [])),
    }

    return {
        "species": study_id,  # for meta-analysis helper (treat each study as one "species")
        "study_id": study_id,
        "bigwig_plus": [str(p) for p in bw_plus_paths],
        "bigwig_minus": [str(p) for p in bw_minus_paths],
        "build": build,
        "k_codons": int(k_codons),
        "body_offset_nt": int(body_offset_nt),
        "n_candidates": int(len(rows)),
        "n_mapped_refgene": int(n_mapped),
        "n_used_pause": int(n_used),
        "correlations": corr,
        "pairwise_comparisons": comps,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Module E: multi-study bigWig pausing vs Uplift (human RefSeq).")
    ap.add_argument("--k", type=int, default=10, help="Window size in codons (must match stop_context_candidates.jsonl).")
    ap.add_argument("--body-offset-nt", type=int, default=300, help="Offset upstream of stop for body baseline window (nt).")
    ap.add_argument(
        "--in-jsonl",
        default=str(data_dir() / "refseq_hsapiens_mrna" / "stop_context_candidates.jsonl"),
        help="Input stop-context candidates JSONL.",
    )
    ap.add_argument("--force", action="store_true", help="Force recomputation (ignore cached outputs).")
    args = ap.parse_args()

    in_path = Path(args.in_jsonl)
    if not in_path.exists():
        raise SystemExit(f"Missing input: {in_path}")

    rows = _load_stop_candidates(in_path, k=int(args.k))
    if not rows:
        raise SystemExit(f"No rows with k={args.k} found in {in_path}")

    studies = [
        {
            "study_id": "GSE148965_HelaS3_WT_RP",
            "dir": riboseq_dir() / "GSE148965",
            "prefer": re.compile(r"WT.*_RP\.bigWig$", re.I),
        },
        {
            "study_id": "GSE199387_H9_WT_RP",
            "dir": riboseq_dir() / "GSE199387",
            "prefer": re.compile(r"WT.*_RP\.bigWig$", re.I),
        },
        {
            "study_id": "GSE211536_LS180_Ribo",
            "dir": riboseq_dir() / "GSE211536",
            "prefer": re.compile(r"ribo|rpf|rp", re.I),
        },
    ]

    missing_dirs = [s["dir"] for s in studies if not Path(s["dir"]).exists()]
    if missing_dirs:
        raise SystemExit(
            "Missing staged bigWig directories. Download via:\n"
            "  python scripts/fetch_geo_riboseq_bigwig.py --gse GSE148965 --regex '_RP\\\\.bigWig$'\n"
            "  python scripts/fetch_geo_riboseq_bigwig.py --gse GSE199387 --regex '_RP\\\\.bigWig$'\n"
            "  python scripts/fetch_geo_riboseq_bigwig.py --gse GSE211536 --extract\n"
        )

    study_results: list[dict[str, Any]] = []
    for s in studies:
        d = Path(s["dir"])
        bw_plus_paths, bw_minus_paths = _pick_bigwig_tracks(d, prefer_regex=s["prefer"])
        if not bw_plus_paths or not bw_minus_paths:
            raise SystemExit(f"No bigWig found under {d} (did you run fetch+extract?)")
        shown = Path(bw_plus_paths[0]).name if bw_plus_paths else "?"
        print(f"[run] {s['study_id']} -> {shown}", flush=True)
        study_results.append(
            analyze_one_bigwig(
                study_id=str(s["study_id"]),
                bw_plus_paths=bw_plus_paths,
                bw_minus_paths=bw_minus_paths,
                rows=rows,
                k_codons=int(args.k),
                body_offset_nt=int(args.body_offset_nt),
            )
        )

    # Meta-analysis across studies on the key stratified endpoint (pause_index, high_diff vs low_diff).
    meta = random_effects_meta(study_results, "high_diff_vs_low_diff")
    out = {"meta": meta, "studies": study_results}

    write_json_atomic(cache_dir() / "riboseq_pause_bigwig_window.json", out)

    out_tex = generated_dir() / "riboseq_pause_bigwig_window.tex"
    meta_line = ""
    if not meta.get("insufficient_data"):
        meta_line = (
            f"Meta-analysis (random-effects) on pause-index $d$ (high $\\Delta U$ vs low): "
            f"$d={_fmt(meta.get('random_effect'), nd=2)}$ "
            f"[{_fmt(meta.get('ci_95_low'), nd=2)}, {_fmt(meta.get('ci_95_high'), nd=2)}], "
            f"$I^2={_fmt(meta.get('I2_percent'), nd=1)}\\%$."
        )

    lines: list[str] = [
        "\\paragraph{Ribo-seq pausing from bigWig tracks (multi-study replication).}",
        "We analyzed independent Ribo-seq bigWig coverage tracks and computed a stop-proximal pause index per transcript, defined as the mean coverage in the $k$-codon window immediately upstream of the terminal stop divided by a same-length baseline window 300 nt upstream (within CDS when available).",
        "",
        "\\begin{center}\\small",
        "\\begin{tabular}{lrrrrr}\\toprule",
        "Study & $n$ & $\\rho(PI, U_{\\mathrm{before}})$ & $\\rho(PI,\\Delta U)$ & $d(\\Delta U\\uparrow\\downarrow)$ & $p$ \\\\",
        "\\midrule",
    ]

    for s in study_results:
        study_id = str(s.get("study_id", "") or "")[:24]
        study_tex = (r"\path{" + study_id + r"}") if study_id else ""
        corr = s.get("correlations", {}).get("pause_index_vs_u_before", {})
        corr_d = s.get("correlations", {}).get("pause_index_vs_diff", {})
        comp = s.get("pairwise_comparisons", {}).get("high_diff_vs_low_diff", {})
        lines.append(
            f"{study_tex} & {int(s.get('n_used_pause',0))} & "
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

    meta_out = {
        "analysis": "riboseq_pause_bigwig_window",
        "k": int(args.k),
        "body_offset_nt": int(args.body_offset_nt),
        "n_studies": int(len(study_results)),
    }
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta_out)
    print(f"Wrote: {out_tex}")


if __name__ == "__main__":
    main()
