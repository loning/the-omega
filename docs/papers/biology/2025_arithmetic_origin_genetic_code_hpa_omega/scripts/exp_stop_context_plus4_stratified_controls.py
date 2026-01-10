# -*- coding: utf-8 -*-
"""
Position-specific matched control for stop-context: +4 base stratification (Null C).

Motivation (Reinforcement 3C-lite):
  A classic confounder for translation termination/readthrough is the +4 nucleotide
  (the first base immediately after the stop codon). To address the reviewer claim
  "your U-window signal is just +4 / a few-position motif", we report stop-context
  window means stratified by +4 base.

Protocol:
  - Human RefSeq mRNA FASTA shards under data/refseq_hsapiens_mrna/human.*.rna.fna.gz
  - Best ORF per transcript (same as exp_refseq_transcriptome.py)
  - For each terminal stop (UAA/UAG/UGA), compute:
      u_before(k): mean Δ over the k codons immediately before the stop
      u_after(k):  mean Δ over the k codons immediately after the stop
      plus4:       nucleotide at +4 (first nt after stop codon)
  - Report per-(stop,plus4) means and large-n normal-approx tests within each plus4 stratum.
  - Also report an aggregate "matched" difference across plus4 strata using weights w_b=min(n1,n2).

Outputs:
  - sections/generated/stop_context_plus4_stratified_controls.tex
  - data/_cache/stop_context_plus4_stratified_controls_v1.json (+ meta)

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
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


def _z_p_diff(m1: float, v1: float, n1: int, m2: float, v2: float, n2: int) -> tuple[float, float] | None:
    """
    Normal approx for difference in means (m2 - m1).
    """
    if n1 < 2 or n2 < 2:
        return None
    se2 = float(v1) / float(n1) + float(v2) / float(n2)
    if se2 <= 0:
        return None
    z = (float(m2) - float(m1)) / math.sqrt(se2)
    p = normal_two_sided_p(float(z))
    return float(z), float(p)


def main() -> None:
    ap = argparse.ArgumentParser(description="+4-stratified stop-context controls (RefSeq).")
    ap.add_argument("--k", type=int, default=10, help="Window radius k (codons) for u_before/u_after.")
    ap.add_argument("--heartbeat-s", type=float, default=60.0, help="Progress heartbeat interval.")
    ap.add_argument("--max-records", type=int, default=0, help="Optional cap on FASTA records scanned (0=all).")
    ap.add_argument("--force", action="store_true", help="Force recomputation even if cache exists.")
    args = ap.parse_args()

    k = int(args.k)
    max_records = int(args.max_records)

    out_json = cache_dir() / "stop_context_plus4_stratified_controls_v1.json"
    out_tex = generated_dir() / "stop_context_plus4_stratified_controls.tex"

    cache_key = {"analysis": "stop_context_plus4_stratified_controls", "analysis_version": ANALYSIS_VERSION, "k": k, "max_records": max_records}
    expected_meta = {"cache_key": cache_key, "cache_key_digest": cache_key_digest(cache_key), "schema_version": 1}

    if (not args.force) and cache_hit(out_json, expected_meta=expected_meta, require_meta=True):
        obj = read_json(out_json)
        write_text(out_tex, str(obj["latex"]) + "\n")
        return

    shards = sorted(data_dir().glob("human.*.rna.fna.gz"))
    if not shards:
        raise FileNotFoundError("No RefSeq FASTA shards found under data/refseq_hsapiens_mrna/. Run with --download.")

    hb = Heartbeat(every_s=float(args.heartbeat_s), prefix="[progress] plus4_controls")

    bases = ("A", "C", "G", "U")
    # stats[stop][plus4]["before"/"after"] -> RunningStats
    stats: dict[str, dict[str, dict[str, RunningStats]]] = {
        s: {b: {"before": RunningStats(), "after": RunningStats()} for b in bases} for s in STOP_CODONS
    }
    n_scanned = 0
    n_with_orf = 0
    n_with_stop = 0
    n_with_windows = 0

    for fp in shards:
        for rid, seq in iter_fasta(str(fp)):
            n_scanned += 1
            if max_records > 0 and n_scanned > max_records:
                break
            hb.maybe(f"scan={n_scanned} file={fp.name} with_orf={n_with_orf} with_stop={n_with_stop} with_windows={n_with_windows}")

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

            # +4 nt
            if stop_base + 3 >= len(seq):
                continue
            plus4 = seq[stop_base + 3]
            if plus4 not in bases:
                continue

            # Windows
            before = _window_mean(seq, start_base=stop_base - 3 * k, k=k)
            after = _window_mean(seq, start_base=stop_base + 3, k=k)
            if before is None or after is None:
                continue
            if stop_base - 3 * k < start_base:
                continue
            n_with_windows += 1

            stats[stop][plus4]["before"].update(float(before))
            stats[stop][plus4]["after"].update(float(after))

        if max_records > 0 and n_scanned > max_records:
            break

    # Build summary table.
    rows = []
    for b in bases:
        for stop in STOP_CODONS:
            rb = stats[stop][b]["before"]
            ra = stats[stop][b]["after"]
            rows.append(
                {
                    "plus4": b,
                    "stop": stop,
                    "n": int(ra.n),
                    "before_mean": float(rb.mean),
                    "before_var": float(rb.sample_variance()),
                    "after_mean": float(ra.mean),
                    "after_var": float(ra.sample_variance()),
                }
            )

    # Pairwise comparisons within each plus4 stratum and aggregate matched diff across plus4.
    pairs = [("UAA", "UAG"), ("UAA", "UGA"), ("UAG", "UGA")]

    def agg_matched(side: str, a: str, b: str) -> dict[str, float]:
        """
        Weighted average (matched) difference (b - a) across plus4 strata.
        """
        weights = []
        diffs = []
        ses2 = []
        for base in bases:
            ra = stats[a][base][side]
            rb = stats[b][base][side]
            if ra.n < 2 or rb.n < 2:
                continue
            w = float(min(ra.n, rb.n))
            d = float(rb.mean - ra.mean)
            v = float(ra.sample_variance()) / float(ra.n) + float(rb.sample_variance()) / float(rb.n)
            weights.append(w)
            diffs.append(d)
            ses2.append(v)
        if not weights:
            return {"diff": 0.0, "se": float("nan"), "z": 0.0, "p": 1.0, "W": 0.0}
        W = float(sum(weights))
        diff = float(sum(w * d for w, d in zip(weights, diffs)) / W)
        # delta method for weighted mean of independent strata
        se2 = float(sum(((w / W) ** 2) * v for w, v in zip(weights, ses2)))
        se = math.sqrt(se2) if se2 > 0 else float("nan")
        z = float(diff / se) if (se and math.isfinite(se) and se > 0) else 0.0
        p = float(normal_two_sided_p(z)) if (se and math.isfinite(se) and se > 0) else 1.0
        return {"diff": diff, "se": se, "z": z, "p": p, "W": W}

    comp = {"before": {}, "after": {}}
    for side in ("before", "after"):
        for a, b in pairs:
            per_base = {}
            for base in bases:
                ra = stats[a][base][side]
                rb = stats[b][base][side]
                zp = _z_p_diff(ra.mean, ra.sample_variance(), ra.n, rb.mean, rb.sample_variance(), rb.n)
                if zp is None:
                    continue
                z, p = zp
                per_base[base] = {"diff": float(rb.mean - ra.mean), "z": float(z), "p": float(p), "n_a": int(ra.n), "n_b": int(rb.n)}
            comp[side][f"{a}_vs_{b}"] = {
                "per_base": per_base,
                "matched": agg_matched(side, a, b),
            }

    # LaTeX fragment
    tex = []
    tex.append(
        f"+4-stratified stop-context controls (RefSeq terminal stops; best ORF per transcript; k={k}). "
        f"Records scanned={n_scanned}, with ORF={n_with_orf}, with stop={n_with_stop}, with complete windows={n_with_windows}."
    )
    tex.append(r"\begin{center}")
    tex.append(r"\small")
    tex.append(r"\setlength{\tabcolsep}{6pt}")
    tex.append(r"\renewcommand{\arraystretch}{1.15}")
    tex.append(r"\begin{tabular}{llrrrr}")
    tex.append(r"\toprule")
    tex.append(r"+4 & stop & $n$ & $\overline{U}_{before}$ & $\overline{U}_{after}$ & $D=\overline{U}_{after}-\overline{U}_{before}$ \\")
    tex.append(r"\midrule")
    for base in bases:
        for stop in STOP_CODONS:
            rb = stats[stop][base]["before"]
            ra = stats[stop][base]["after"]
            if ra.n <= 0:
                continue
            tex.append(
                f"{base} & {stop} & {int(ra.n)} & {float(rb.mean):.4f} & {float(ra.mean):.4f} & {(float(ra.mean - rb.mean)):+.4f} \\\\"
            )
    tex.append(r"\bottomrule")
    tex.append(r"\end{tabular}")
    tex.append(r"\end{center}")

    # Matched diffs across +4 strata.
    for side in ("before", "after"):
        tex.append(f"\\noindent Matched differences across +4 strata ({side}-window; weights $w_b=\\min(n_a,n_b)$):")
        for a, b in pairs:
            key = f"{a}_vs_{b}"
            m = comp[side][key]["matched"]
            tex.append(
                f" {b}-{a} diff={float(m['diff']):+.4f} (SE={float(m['se']):.4f}, p={float(m['p']):.3g}; matched W={int(m['W'])})."
            )

    latex = "\n".join(tex)

    obj = {
        "ok": True,
        "analysis_version": ANALYSIS_VERSION,
        "k": k,
        "max_records": max_records,
        "n_scanned": n_scanned,
        "n_with_orf": n_with_orf,
        "n_with_stop": n_with_stop,
        "n_with_windows": n_with_windows,
        "rows": rows,
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

