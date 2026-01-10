# -*- coding: utf-8 -*-
"""
Position-specific matched control for stop-context: downstream 6-nt context stratification (after_nt6).

This is a stricter version of the +4 stratification:
  after_nt6 = the 6 nucleotides immediately downstream of the stop codon
              (positions +4..+9; DNA:+4..+9 == RNA after stop codon, length 6).

Protocol:
  - Human RefSeq mRNA FASTA shards under data/refseq_hsapiens_mrna/human.*.rna.fna.gz
  - Best ORF per transcript (same as exp_refseq_transcriptome.py)
  - For each terminal stop (UAA/UAG/UGA), compute:
      u_before(k): mean Δ over the k codons immediately before the stop
      u_after(k):  mean Δ over the k codons immediately after the stop
      after_nt6:   6-mer after stop (RNA alphabet)
  - Report "matched" stop-class differences across after_nt6 strata using weights
    w_s = min(n_a, n_b) per stratum, optionally filtering to strata with n>=min_n.

Outputs:
  - sections/generated/stop_context_after_nt6_stratified_controls.tex
  - data/_cache/stop_context_after_nt6_stratified_controls_v1.json (+ meta)

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

from cache_manager import cache_hit, cache_key_digest, cache_meta_path, read_json, write_json_atomic
from genetic_code_tools import GENETIC_CODE, STOP_CODONS, iter_fasta
from progress_tools import Heartbeat
from stats_tools import normal_two_sided_p

from exp_refseq_transcriptome import CODON_INFO, best_orf_across_frames


ANALYSIS_VERSION = 1


def root_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def generated_dir() -> Path:
    d = root_dir() / "sections" / "generated"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_dir() -> Path:
    d = root_dir() / "data" / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_dir() -> Path:
    return root_dir() / "data" / "refseq_hsapiens_mrna"


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


@dataclass
class RunningStats:
    n: int = 0
    mean: float = 0.0
    M2: float = 0.0

    def update(self, x: float) -> None:
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        d2 = x - self.mean
        self.M2 += d * d2

    def sample_variance(self) -> float:
        if self.n <= 1:
            return 0.0
        return self.M2 / (self.n - 1)


def _window_mean(seq: str, *, start_base: int, k: int) -> float | None:
    """
    Mean Δ over k in-frame codons starting at start_base.
    """
    if start_base < 0 or start_base + 3 * k > len(seq):
        return None
    total = 0
    for i in range(k):
        codon = seq[start_base + 3 * i : start_base + 3 * i + 3]
        if codon not in GENETIC_CODE:
            return None
        total += int(CODON_INFO[codon]["delta"])
    return float(total) / float(k)


def _matched_diff(
    *,
    stats: dict[str, dict[str, dict[str, RunningStats]]],
    strata: list[str],
    side: str,
    a: str,
    b: str,
    min_n: int,
) -> dict[str, float]:
    """
    Weighted average (matched) difference (b - a) across strata with weights w_s=min(n_a,n_b).
    Uses a normal approximation for an approximate p-value.
    """
    weights = []
    diffs = []
    ses2 = []
    for s in strata:
        ra = stats[a].get(s)
        rb = stats[b].get(s)
        if ra is None or rb is None:
            continue
        r1 = ra[side]
        r2 = rb[side]
        if r1.n < max(2, min_n) or r2.n < max(2, min_n):
            continue
        w = float(min(r1.n, r2.n))
        d = float(r2.mean - r1.mean)
        v = float(r1.sample_variance()) / float(r1.n) + float(r2.sample_variance()) / float(r2.n)
        weights.append(w)
        diffs.append(d)
        ses2.append(v)
    if not weights:
        return {"diff": 0.0, "se": float("nan"), "z": 0.0, "p": 1.0, "W": 0.0, "n_strata": 0.0}
    W = float(sum(weights))
    diff = float(sum(w * d for w, d in zip(weights, diffs)) / W)
    se2 = float(sum(((w / W) ** 2) * v for w, v in zip(weights, ses2)))
    se = math.sqrt(se2) if se2 > 0 else float("nan")
    z = float(diff / se) if (se and math.isfinite(se) and se > 0) else 0.0
    p = float(normal_two_sided_p(z)) if (se and math.isfinite(se) and se > 0) else 1.0
    return {"diff": diff, "se": se, "z": z, "p": p, "W": W, "n_strata": float(len(weights))}


def main() -> None:
    ap = argparse.ArgumentParser(description="after_nt6-stratified stop-context controls (RefSeq).")
    ap.add_argument("--k", type=int, default=10, help="Window radius k (codons) for u_before/u_after.")
    ap.add_argument("--min-n", type=int, default=50, help="Minimum count per stop class within a stratum to include it.")
    ap.add_argument("--top-n", type=int, default=10, help="Show the top-N after_nt6 strata by total count.")
    ap.add_argument("--heartbeat-s", type=float, default=60.0, help="Progress heartbeat interval.")
    ap.add_argument("--max-records", type=int, default=0, help="Optional cap on FASTA records scanned (0=all).")
    ap.add_argument("--force", action="store_true", help="Force recomputation even if cache exists.")
    args = ap.parse_args()

    k = int(args.k)
    min_n = int(args.min_n)
    top_n = int(args.top_n)
    max_records = int(args.max_records)

    out_json = cache_dir() / "stop_context_after_nt6_stratified_controls_v1.json"
    out_tex = generated_dir() / "stop_context_after_nt6_stratified_controls.tex"

    cache_key = {
        "analysis": "stop_context_after_nt6_stratified_controls",
        "analysis_version": ANALYSIS_VERSION,
        "k": k,
        "min_n": min_n,
        "top_n": top_n,
        "max_records": max_records,
    }
    expected_meta = {"cache_key": cache_key, "cache_key_digest": cache_key_digest(cache_key), "schema_version": 1}

    if (not args.force) and cache_hit(out_json, expected_meta=expected_meta, require_meta=True):
        obj = read_json(out_json)
        write_text(out_tex, str(obj["latex"]) + "\n")
        return

    shards = sorted(data_dir().glob("human.*.rna.fna.gz"))
    if not shards:
        raise FileNotFoundError("No RefSeq FASTA shards found under data/refseq_hsapiens_mrna/. Run with --download.")

    hb = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress] after_nt6_controls")

    bases = ("A", "C", "G", "U")
    # stats[stop][stratum]["before"/"after"]
    stats: dict[str, dict[str, dict[str, RunningStats]]] = {s: {} for s in STOP_CODONS}
    # counts for ranking strata by total count across stops
    total_counts: dict[str, int] = {}

    n_scanned = 0
    n_with_orf = 0
    n_with_stop = 0
    n_with_windows = 0
    n_with_stratum = 0

    for fp in shards:
        for rid, seq in iter_fasta(str(fp)):
            n_scanned += 1
            if max_records > 0 and n_scanned > max_records:
                break
            hb.maybe(
                f"scan={n_scanned} file={fp.name} with_orf={n_with_orf} with_stop={n_with_stop} "
                f"with_windows={n_with_windows} with_stratum={n_with_stratum}"
            )

            best = best_orf_across_frames(seq)
            if best is None:
                continue
            n_with_orf += 1
            start_base = int(best.start_base)
            stop_base = int(best.stop_base)
            stop = seq[stop_base : stop_base + 3]
            if stop not in STOP_CODONS:
                continue
            n_with_stop += 1

            # after_nt6 = +4..+9 (6 nt) downstream of stop codon
            if stop_base + 9 > len(seq):
                continue
            after_nt6 = seq[stop_base + 3 : stop_base + 9]
            if len(after_nt6) != 6 or any(ch not in bases for ch in after_nt6):
                continue
            n_with_stratum += 1

            # Windows
            if stop_base - 3 * k < start_base:
                continue
            before = _window_mean(seq, start_base=stop_base - 3 * k, k=k)
            after = _window_mean(seq, start_base=stop_base + 3, k=k)
            if before is None or after is None:
                continue
            n_with_windows += 1

            m = stats[stop].get(after_nt6)
            if m is None:
                m = {"before": RunningStats(), "after": RunningStats()}
                stats[stop][after_nt6] = m
            m["before"].update(float(before))
            m["after"].update(float(after))
            total_counts[after_nt6] = int(total_counts.get(after_nt6, 0) + 1)

        if max_records > 0 and n_scanned > max_records:
            break

    strata_sorted = sorted(total_counts.keys(), key=lambda s: int(total_counts.get(s, 0)), reverse=True)
    top_strata = strata_sorted[: max(0, int(top_n))]

    pairs = [("UAA", "UAG"), ("UAA", "UGA"), ("UAG", "UGA")]
    comp = {"before": {}, "after": {}}
    for side in ("before", "after"):
        for a, b in pairs:
            comp[side][f"{a}_vs_{b}"] = _matched_diff(stats=stats, strata=strata_sorted, side=side, a=a, b=b, min_n=min_n)

    # LaTeX fragment
    tex: list[str] = []
    tex.append(
        f"after\\_nt6-stratified stop-context controls (RefSeq terminal stops; best ORF per transcript; k={k}; min\\_n={min_n} per stop class per stratum)."
        f" Records scanned={n_scanned}, with ORF={n_with_orf}, with stop={n_with_stop}, with after\\_nt6={n_with_stratum}, with complete windows={n_with_windows}."
        f" Total distinct after\\_nt6 strata observed: {len(strata_sorted)}."
    )

    if top_strata:
        tex.append(r"\begin{center}")
        tex.append(r"\small")
        tex.append(r"\setlength{\tabcolsep}{6pt}")
        tex.append(r"\renewcommand{\arraystretch}{1.15}")
        tex.append(r"\begin{tabular}{lrrrr}")
        tex.append(r"\toprule")
        tex.append(r"after\_nt6 & total & UAA & UAG & UGA \\")
        tex.append(r"\midrule")
        for s in top_strata:
            n_tot = int(total_counts.get(s, 0))
            n_uaa = int(stats["UAA"].get(s, {"before": RunningStats()})["before"].n) if stats.get("UAA") else 0
            n_uag = int(stats["UAG"].get(s, {"before": RunningStats()})["before"].n) if stats.get("UAG") else 0
            n_uga = int(stats["UGA"].get(s, {"before": RunningStats()})["before"].n) if stats.get("UGA") else 0
            tex.append(f"\\texttt{{{s}}} & {n_tot} & {n_uaa} & {n_uag} & {n_uga} \\\\")
        tex.append(r"\bottomrule")
        tex.append(r"\end{tabular}")
        tex.append(r"\end{center}")

    for side in ("before", "after"):
        tex.append(f"\\noindent Matched differences across after\\_nt6 strata ({side}-window; weights $w_s=\\min(n_a,n_b)$):")
        for a, b in pairs:
            r = comp[side][f"{a}_vs_{b}"]
            tex.append(
                f" {b}-{a} diff={float(r['diff']):+.4f} (SE={float(r['se']):.4f}, p={float(r['p']):.3g}; matched W={int(r['W'])}, strata={int(r['n_strata'])})."
            )

    latex = "\n".join(tex)

    obj = {
        "ok": True,
        "analysis_version": ANALYSIS_VERSION,
        "k": k,
        "min_n": min_n,
        "top_n": top_n,
        "max_records": max_records,
        "n_scanned": n_scanned,
        "n_with_orf": n_with_orf,
        "n_with_stop": n_with_stop,
        "n_with_after_nt6": n_with_stratum,
        "n_with_windows": n_with_windows,
        "n_strata": len(strata_sorted),
        "top_strata": top_strata,
        "comparisons": comp,
        "latex": latex,
    }
    write_json_atomic(out_json, obj)
    write_json_atomic(cache_meta_path(out_json), expected_meta)
    write_text(out_tex, latex + "\n")
    print(f"Wrote: {out_tex}")
    print(f"Wrote: {out_json}")


if __name__ == "__main__":
    main()

