# -*- coding: utf-8 -*-
"""
H3-7: Structure probing track cross-check at stop windows (bedGraph).

Goal: test whether an in vivo RNA-structure proxy (e.g., DMS/SHAPE reactivity)
shows any association with Uplift window endpoints at terminal stops, using the
same stop-context candidates as the Ribo-seq pausing analyses.

Current implementation supports a single bedGraph (genome coordinates) dataset.

Example:
  python scripts/exp_structure_probing_stop_windows.py \
    --study-id GSE95465_DMS \
    --bedgraph data/probing/GSE95465/GSE95465_DMS-treated-ctrl-100-AC-dif.bedgraph.gz \
    --build hg38 --k 10 --force
"""

from __future__ import annotations

import argparse
import bisect
import gzip
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy import stats

from cache_manager import cache_meta_path, write_json_atomic, write_text_atomic
from exp_riboseq_pause_bigwig_window import load_refgene_index, slice_to_genomic_intervals, _resolve_chrom
from stats_tools import cohen_d


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


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


@dataclass
class BedGraphIndex:
    starts: dict[str, list[int]]
    ends: dict[str, list[int]]
    values: dict[str, list[float]]

    @classmethod
    def from_path(cls, path: Path) -> "BedGraphIndex":
        starts: dict[str, list[int]] = {}
        ends: dict[str, list[int]] = {}
        values: dict[str, list[float]] = {}

        opener = gzip.open if path.name.lower().endswith(".gz") else open
        with opener(path, "rt", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith(("#", "track", "browser")):
                    continue
                parts = line.split()
                if len(parts) < 4:
                    continue
                chrom = parts[0]
                try:
                    start = int(parts[1])
                    end = int(parts[2])
                    val = float(parts[3])
                except Exception:
                    continue
                if end <= start:
                    continue
                starts.setdefault(chrom, []).append(start)
                ends.setdefault(chrom, []).append(end)
                values.setdefault(chrom, []).append(val)

        # Ensure per-chrom ordering (bedGraph is typically sorted, but be robust).
        for chrom in list(starts.keys()):
            s = starts[chrom]
            e = ends[chrom]
            v = values[chrom]
            if not s:
                continue
            if any(s[i] > s[i + 1] for i in range(len(s) - 1)):
                idx = sorted(range(len(s)), key=s.__getitem__)
                starts[chrom] = [s[i] for i in idx]
                ends[chrom] = [e[i] for i in idx]
                values[chrom] = [v[i] for i in idx]

        return cls(starts=starts, ends=ends, values=values)

    def chroms(self) -> set[str]:
        return set(self.starts.keys())

    def mean_over_interval(
        self,
        chrom: str,
        start: int,
        end: int,
        *,
        min_covered_frac: float,
        min_covered_bases: int,
    ) -> float:
        if end <= start:
            return float("nan")
        s = self.starts.get(chrom)
        e = self.ends.get(chrom)
        v = self.values.get(chrom)
        if not s or not e or not v:
            return float("nan")

        total_len = int(end - start)
        covered = 0
        acc = 0.0

        # Find the first segment whose end might exceed start.
        i = bisect.bisect_right(e, int(start))
        if i > 0 and e[i - 1] > start:
            i -= 1

        while i < len(s) and s[i] < end:
            seg_start = s[i]
            seg_end = e[i]
            if seg_end <= start:
                i += 1
                continue
            ov0 = max(start, seg_start)
            ov1 = min(end, seg_end)
            if ov0 < ov1:
                ln = int(ov1 - ov0)
                covered += ln
                acc += float(v[i]) * float(ln)
            if seg_end >= end:
                break
            i += 1

        if covered <= 0:
            return float("nan")
        if int(covered) < int(min_covered_bases):
            return float("nan")
        if float(covered) / float(total_len) < float(min_covered_frac):
            return float("nan")
        return float(acc / float(covered))

    def mean_over_intervals(
        self,
        chrom: str,
        intervals: Iterable[tuple[int, int]],
        *,
        min_covered_frac: float,
        min_covered_bases: int,
    ) -> float:
        total = 0
        covered = 0
        acc = 0.0
        for a, b in intervals:
            a_i = int(a)
            b_i = int(b)
            if b_i <= a_i:
                continue
            total += int(b_i - a_i)

            s = self.starts.get(chrom)
            e = self.ends.get(chrom)
            v = self.values.get(chrom)
            if not s or not e or not v:
                continue

            i = bisect.bisect_right(e, a_i)
            if i > 0 and e[i - 1] > a_i:
                i -= 1

            while i < len(s) and s[i] < b_i:
                seg_start = s[i]
                seg_end = e[i]
                if seg_end <= a_i:
                    i += 1
                    continue
                ov0 = max(a_i, seg_start)
                ov1 = min(b_i, seg_end)
                if ov0 < ov1:
                    ln = int(ov1 - ov0)
                    covered += ln
                    acc += float(v[i]) * float(ln)
                if seg_end >= b_i:
                    break
                i += 1

        if total <= 0 or covered <= 0:
            return float("nan")
        if int(covered) < int(min_covered_bases):
            return float("nan")
        if float(covered) / float(total) < float(min_covered_frac):
            return float("nan")
        return float(acc / float(covered))


def _spearman(x: list[float], y: list[float], *, min_n: int) -> dict[str, float]:
    xs = np.array(x, dtype=float)
    ys = np.array(y, dtype=float)
    m = np.isfinite(xs) & np.isfinite(ys)
    n = int(np.sum(m))
    if n < int(min_n):
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


def main() -> None:
    ap = argparse.ArgumentParser(description="H3-7: stop-window structure probing cross-check (bedGraph).")
    ap.add_argument("--study-id", required=True, help="Short dataset ID for table/caching.")
    ap.add_argument("--bedgraph", required=True, help="Path to a genome-coordinate bedGraph(.gz) file.")
    ap.add_argument("--build", choices=["hg19", "hg38"], default="hg38", help="Genome build for UCSC ncbiRefSeq genePred mapping.")
    ap.add_argument("--k", type=int, default=10, help="Window size in codons (must match stop_context_candidates.jsonl).")
    ap.add_argument(
        "--in-jsonl",
        default=str(data_dir() / "refseq_hsapiens_mrna" / "stop_context_candidates.jsonl"),
        help="Input stop-context candidates JSONL.",
    )
    ap.add_argument(
        "--min-covered-frac",
        type=float,
        default=0.0,
        help="Minimum fraction of queried bases that must have bedGraph coverage (per window).",
    )
    ap.add_argument(
        "--min-covered-bases",
        type=int,
        default=10,
        help="Minimum number of covered bases required per window (useful for sparse probing tracks).",
    )
    ap.add_argument(
        "--min-n-corr",
        type=int,
        default=30,
        help="Minimum n required to report Spearman correlations (else shown as '--').",
    )
    ap.add_argument("--force", action="store_true", help="Overwrite existing outputs.")
    args = ap.parse_args()

    in_path = Path(str(args.in_jsonl))
    if not in_path.exists():
        raise SystemExit(f"Missing input: {in_path}")

    bg_path = Path(str(args.bedgraph))
    if not bg_path.exists():
        raise SystemExit(f"Missing bedGraph: {bg_path}")

    out_tex = generated_dir() / "structure_probing_stop_windows.tex"
    out_json = cache_dir() / "structure_probing_stop_windows.json"
    if out_tex.exists() and out_json.exists() and not bool(args.force):
        print(f"Exists: {out_tex} (use --force to overwrite)", flush=True)
        return

    rows = _load_stop_candidates(in_path, k=int(args.k))
    if not rows:
        raise SystemExit(f"No rows with k={args.k} found in {in_path}")

    bg = BedGraphIndex.from_path(bg_path)
    bed_chroms = bg.chroms()

    record_ids = {str(r.get("record_id") or "") for r in rows if str(r.get("record_id") or "").strip()}
    refgene = load_refgene_index(str(args.build), keep_names=record_ids)

    k_nt = 3 * int(args.k)

    out_rows: list[dict[str, Any]] = []
    n_mapped = 0
    n_used = 0

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
        n_mapped += 1

        before_t0 = stop_base_i - k_nt
        before_t1 = stop_base_i
        after_t0 = stop_base_i + 3
        after_t1 = after_t0 + k_nt

        before_iv = slice_to_genomic_intervals(gp, t0=before_t0, t1=before_t1)
        after_iv = slice_to_genomic_intervals(gp, t0=after_t0, t1=after_t1)
        if sum(b - a for a, b in before_iv) != k_nt:
            continue
        if sum(b - a for a, b in after_iv) != k_nt:
            continue

        chrom = _resolve_chrom(gp.chrom, {c: 1 for c in bed_chroms})
        if chrom is None:
            continue

        # Reject windows that cross into pre-start UTR for upstream slice.
        if before_t0 < start_base_i:
            continue

        r_before = bg.mean_over_intervals(
            chrom,
            before_iv,
            min_covered_frac=float(args.min_covered_frac),
            min_covered_bases=int(args.min_covered_bases),
        )
        r_after = bg.mean_over_intervals(
            chrom,
            after_iv,
            min_covered_frac=float(args.min_covered_frac),
            min_covered_bases=int(args.min_covered_bases),
        )
        if not (np.isfinite(r_before) and np.isfinite(r_after)):
            continue

        n_used += 1
        out_rows.append(
            {
                "record_id": rid,
                "stop_codon": str(r.get("stop_codon") or ""),
                "group_label": str(r.get("group_label") or ""),
                "u_before": float(r.get("before_mean_delta")) if r.get("before_mean_delta") is not None else float("nan"),
                "diff": float(r.get("diff")) if r.get("diff") is not None else float("nan"),
                "react_before": float(r_before),
                "react_after": float(r_after),
                "react_diff": float(r_after - r_before),
            }
        )

    corr = {
        "react_before_vs_u_before": _spearman(
            [rr["react_before"] for rr in out_rows],
            [rr["u_before"] for rr in out_rows],
            min_n=int(args.min_n_corr),
        ),
        "react_diff_vs_diff": _spearman(
            [rr["react_diff"] for rr in out_rows],
            [rr["diff"] for rr in out_rows],
            min_n=int(args.min_n_corr),
        ),
    }

    by_group: dict[str, list[float]] = {}
    for rr in out_rows:
        by_group.setdefault(rr["group_label"], []).append(float(rr["react_diff"]))

    comps = {
        "high_diff_vs_low_diff": _compare(by_group.get("high_diff", []), by_group.get("low_diff", [])),
        "matched_after_high_vs_matched_after_low": _compare(by_group.get("matched_after_high", []), by_group.get("matched_after_low", [])),
    }

    out = {
        "study_id": str(args.study_id),
        "bedgraph": str(bg_path),
        "build": str(args.build),
        "k_codons": int(args.k),
        "min_covered_frac": float(args.min_covered_frac),
        "min_covered_bases": int(args.min_covered_bases),
        "min_n_corr": int(args.min_n_corr),
        "n_candidates": int(len(rows)),
        "n_mapped_refgene": int(n_mapped),
        "n_used": int(n_used),
        "correlations": corr,
        "pairwise_comparisons": comps,
        "rows": out_rows,
    }
    write_json_atomic(out_json, out)

    lines: list[str] = [
        "\\paragraph{Structure probing track cross-check (bedGraph).}",
        "We analyzed an in vivo structure probing track (bedGraph signal) and computed the mean signal in the stop-proximal before/after windows (k codons) using RefSeq-to-genome mapping (UCSC ncbiRefSeq genePred).",
        "We report correlations against Uplift window endpoints and a stratified effect size on the probing window difference $\\Delta R = R_{\\mathrm{after}}-R_{\\mathrm{before}}$ (high $\\Delta U$ vs low).",
        "",
        "\\begin{center}\\small",
        "\\begin{tabular}{lrrrrr}\\toprule",
        "Dataset & $n$ & $\\rho(R_{\\mathrm{before}}, U_{\\mathrm{before}})$ & $\\rho(\\Delta R,\\Delta U)$ & $d(\\Delta U\\uparrow\\downarrow;\\Delta R)$ & $p$ \\\\",
        "\\midrule",
    ]

    comp = comps.get("high_diff_vs_low_diff", {})
    lines.append(
        f"\\path{{{str(args.study_id)}}} & {int(n_used)} & "
        f"{_fmt(corr['react_before_vs_u_before'].get('rho'))} & "
        f"{_fmt(corr['react_diff_vs_diff'].get('rho'))} & "
        f"{_fmt(comp.get('cohens_d'), nd=2)} & {_p_fmt(comp.get('p'))} \\\\"
    )

    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{center}",
        ]
    )
    if int(n_used) < int(args.min_n_corr):
        lines.append(
            f"\\emph{{Note:}} Only $n={int(n_used)}$ stop-window candidates overlap this probing track under {str(args.build)} mapping; correlations are omitted by design."
        )

    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(
        cache_meta_path(out_tex),
        {
            "analysis": "structure_probing_stop_windows",
            "study_id": str(args.study_id),
            "k": int(args.k),
            "build": str(args.build),
            "min_covered_frac": float(args.min_covered_frac),
            "min_covered_bases": int(args.min_covered_bases),
            "min_n_corr": int(args.min_n_corr),
            "bedgraph": str(bg_path),
        },
    )

    print(f"Wrote: {out_tex}", flush=True)


if __name__ == "__main__":
    main()
