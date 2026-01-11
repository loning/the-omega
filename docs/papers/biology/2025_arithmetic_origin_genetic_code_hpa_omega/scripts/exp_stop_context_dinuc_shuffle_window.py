# -*- coding: utf-8 -*-
"""
Dinucleotide-preserving window-level shuffle null for stop-context uplift.

This implements the "generative null" that preserves the exact dinucleotide
multiset within each window, using Eulerian-trail shuffling.

Unlike the ORF-level dicodon null (exp_stop_context_null_dicodon_orf.py),
this operates at the window level and preserves dinucleotide (not dicodon)
frequencies, providing a complementary null model.

Output:
  - sections/generated/stop_context_dinuc_shuffle_window_summary.tex
  - sections/generated/stop_context_dinuc_shuffle_window_hist.png
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np

# ---- path setup ----
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from genetic_code_tools import fold_codon

MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
from cache_manager import write_text_atomic, write_json_atomic, cache_meta_path

ANALYSIS_VERSION = 1
NUCS = "ACGU"
DINUCS = [a + b for a in NUCS for b in NUCS]
DINUC_INDEX = {d: i for i, d in enumerate(DINUCS)}


def root_dir() -> Path:
    return SCRIPT_DIR.parent


def generated_dir() -> Path:
    return root_dir() / "sections" / "generated"


def data_dir() -> Path:
    return root_dir() / "data"


def cache_dir() -> Path:
    d = data_dir() / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---- dinucleotide shuffle (Eulerian trail) ----

def dinuc_shuffle(seq: str, rng: np.random.Generator) -> str:
    """
    Generate a random sequence with the same dinucleotide multiset as seq.
    Uses Hierholzer's algorithm for Eulerian trail.
    """
    s = seq.upper().replace("T", "U")
    if len(s) <= 2:
        return s

    # build directed multigraph on nucleotides
    edges: dict[str, list[str]] = {b: [] for b in NUCS}
    for i in range(len(s) - 1):
        a, b = s[i], s[i + 1]
        if a in NUCS and b in NUCS:
            edges[a].append(b)

    # randomize outgoing edge order
    for a in NUCS:
        rng.shuffle(edges[a])

    # Hierholzer algorithm for Eulerian trail
    start = s[0] if s[0] in NUCS else "A"
    stack = [start]
    path: list[str] = []
    while stack:
        v = stack[-1]
        if edges.get(v):
            u = edges[v].pop()
            stack.append(u)
        else:
            path.append(stack.pop())

    out = "".join(reversed(path))
    return out[: len(s)]


# ---- sequence to uplift ----

def seq_to_codons(seq: str) -> list[str]:
    """Convert nucleotide sequence to list of codons (RNA)."""
    s = seq.upper().replace("T", "U")
    return [s[i : i + 3] for i in range(0, len(s) - 2, 3) if len(s[i : i + 3]) == 3]


def window_mean_uplift(seq: str) -> float:
    """Compute mean uplift for a codon window sequence."""
    codons = seq_to_codons(seq)
    if not codons:
        return float("nan")
    uplifts = []
    for c in codons:
        try:
            cf = fold_codon(c, MU_STAR)
            uplifts.append(float(cf.delta))
        except (KeyError, ValueError):
            pass
    return float(np.mean(uplifts)) if uplifts else float("nan")


# ---- main analysis ----

@dataclass
class WindowRecord:
    stop_codon: str
    before_seq: str
    after_seq: str
    u_before: float
    u_after: float


def parse_refseq_shards(
    shards_dir: Path,
    k: int,
    n_per_stop: int,
    seed: int,
) -> dict[str, list[WindowRecord]]:
    """
    Parse RefSeq shard JSONs and extract terminal stop windows.
    Returns dict[stop_codon -> list of WindowRecord].
    """
    rng = np.random.default_rng(seed)
    
    shard_files = sorted(shards_dir.glob("*.json"))
    if not shard_files:
        raise FileNotFoundError(f"No shard JSON files in {shards_dir}")

    # Collect all records first
    all_records: dict[str, list[WindowRecord]] = {"UAA": [], "UAG": [], "UGA": []}
    
    for sf in shard_files:
        with open(sf) as f:
            data = json.load(f)
        
        items = data.get("items") or []
        for item in items:
            stop = item.get("stop_codon")
            if stop not in all_records:
                continue
            
            # Get window sequences
            sc = item.get("stop_context") or {}
            k_data = sc.get(str(k)) or {}
            before_seq = k_data.get("before_seq") or ""
            after_seq = k_data.get("after_seq") or ""
            
            if not before_seq or not after_seq:
                continue
            if len(before_seq) < 3 * k or len(after_seq) < 3 * k:
                continue
            
            u_before = float(k_data.get("u_before", float("nan")))
            u_after = float(k_data.get("u_after", float("nan")))
            
            if np.isnan(u_before) or np.isnan(u_after):
                continue
            
            all_records[stop].append(WindowRecord(
                stop_codon=stop,
                before_seq=before_seq,
                after_seq=after_seq,
                u_before=u_before,
                u_after=u_after,
            ))
    
    # Sample n_per_stop from each
    result: dict[str, list[WindowRecord]] = {}
    for stop, recs in all_records.items():
        if len(recs) <= n_per_stop:
            result[stop] = recs
        else:
            idx = rng.choice(len(recs), size=n_per_stop, replace=False)
            result[stop] = [recs[i] for i in idx]
    
    return result


def run_dinuc_shuffle_null(
    records: dict[str, list[WindowRecord]],
    n_perm: int,
    seed: int,
    window: str,  # "before" or "after"
) -> dict[str, Any]:
    """
    For each stop class, compute observed mean U and null distribution
    from dinucleotide-shuffled windows.
    """
    rng = np.random.default_rng(seed)
    
    results: dict[str, Any] = {}
    
    for stop, recs in records.items():
        if not recs:
            continue
        
        # Observed mean
        if window == "before":
            obs_values = [r.u_before for r in recs]
            seqs = [r.before_seq for r in recs]
        else:
            obs_values = [r.u_after for r in recs]
            seqs = [r.after_seq for r in recs]
        
        obs_mean = float(np.mean(obs_values))
        
        # Null distribution: shuffle each window, recompute U
        null_means: list[float] = []
        for _ in range(n_perm):
            perm_values = []
            for seq in seqs:
                shuffled = dinuc_shuffle(seq, rng)
                u_shuffled = window_mean_uplift(shuffled)
                if not np.isnan(u_shuffled):
                    perm_values.append(u_shuffled)
            if perm_values:
                null_means.append(float(np.mean(perm_values)))
        
        null_mean = float(np.mean(null_means)) if null_means else float("nan")
        null_std = float(np.std(null_means)) if null_means else float("nan")
        
        results[stop] = {
            "n": len(recs),
            "obs_mean": obs_mean,
            "null_mean": null_mean,
            "null_std": null_std,
            "null_values": null_means,
        }
    
    return results


def compute_pairwise_contrasts(
    results: dict[str, Any],
    n_perm: int,
    seed: int,
) -> list[dict[str, Any]]:
    """
    Compute pairwise stop-class contrasts and test against null.
    """
    rng = np.random.default_rng(seed)
    pairs = [("UAG", "UAA"), ("UGA", "UAA"), ("UGA", "UAG")]
    contrasts = []
    
    for s1, s2 in pairs:
        if s1 not in results or s2 not in results:
            continue
        
        r1, r2 = results[s1], results[s2]
        obs_diff = r1["obs_mean"] - r2["obs_mean"]
        
        # Null differences
        null1 = r1.get("null_values") or []
        null2 = r2.get("null_values") or []
        
        if null1 and null2:
            min_len = min(len(null1), len(null2))
            null_diffs = [null1[i] - null2[i] for i in range(min_len)]
            null_diff_mean = float(np.mean(null_diffs))
            null_diff_std = float(np.std(null_diffs))
            
            # Two-sided p-value
            n_ge = sum(1 for d in null_diffs if d >= obs_diff)
            n_le = sum(1 for d in null_diffs if d <= obs_diff)
            p_val = 2 * min(n_ge, n_le) / len(null_diffs) if null_diffs else 1.0
            p_val = min(p_val, 1.0)
        else:
            null_diff_mean = float("nan")
            null_diff_std = float("nan")
            p_val = float("nan")
        
        contrasts.append({
            "pair": f"{s1}-{s2}",
            "obs_diff": obs_diff,
            "null_diff_mean": null_diff_mean,
            "null_diff_std": null_diff_std,
            "p": p_val,
        })
    
    return contrasts


def main() -> None:
    parser = argparse.ArgumentParser(description="Dinucleotide shuffle window-level null for stop-context")
    parser.add_argument("--k", type=int, default=10, help="Window radius in codons")
    parser.add_argument("--n-per-stop", type=int, default=1000, help="Sample size per stop class")
    parser.add_argument("--n-perm", type=int, default=100, help="Number of permutations")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    parser.add_argument("--force", action="store_true", help="Force recomputation")
    args = parser.parse_args()

    out_summary = generated_dir() / "stop_context_dinuc_shuffle_window_summary.tex"
    out_png = generated_dir() / "stop_context_dinuc_shuffle_window_hist.png"
    cache_file = cache_dir() / f"stop_context_dinuc_shuffle_window_v{ANALYSIS_VERSION}.json"

    cache_meta = {
        "analysis_version": ANALYSIS_VERSION,
        "k": args.k,
        "n_per_stop": args.n_per_stop,
        "n_perm": args.n_perm,
        "seed": args.seed,
    }

    # Check cache
    if not args.force and cache_file.exists():
        try:
            with open(cache_file) as f:
                cached = json.load(f)
            if (
                cached.get("analysis_version") == ANALYSIS_VERSION
                and cached.get("k") == args.k
                and cached.get("n_per_stop") == args.n_per_stop
                and cached.get("n_perm") == args.n_perm
            ):
                print(f"[cache] Using cached results from {cache_file}")
                # Regenerate outputs from cache
                _emit_outputs(cached, out_summary, out_png, cache_meta)
                return
        except Exception:
            pass

    # Find RefSeq shards
    shards_dir = data_dir() / "refseq_hsapiens_mrna" / "shards" / f"k{args.k}_v4"
    if not shards_dir.exists():
        # Try alternative version
        for v in [3, 2, 1]:
            alt = data_dir() / "refseq_hsapiens_mrna" / "shards" / f"k{args.k}_v{v}"
            if alt.exists():
                shards_dir = alt
                break
    
    if not shards_dir.exists():
        print(f"[error] No RefSeq shards found at {shards_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"[progress] Loading RefSeq windows from {shards_dir}", flush=True)
    records = parse_refseq_shards(shards_dir, args.k, args.n_per_stop, args.seed)
    
    for stop, recs in records.items():
        print(f"  {stop}: {len(recs)} windows", flush=True)

    # Run null analysis for before window
    print(f"[progress] Running dinuc shuffle null (before-window, n_perm={args.n_perm})", flush=True)
    results_before = run_dinuc_shuffle_null(records, args.n_perm, args.seed, "before")
    contrasts_before = compute_pairwise_contrasts(results_before, args.n_perm, args.seed)

    # Run null analysis for after window
    print(f"[progress] Running dinuc shuffle null (after-window, n_perm={args.n_perm})", flush=True)
    results_after = run_dinuc_shuffle_null(records, args.n_perm, args.seed + 1, "after")
    contrasts_after = compute_pairwise_contrasts(results_after, args.n_perm, args.seed + 1)

    # Build output
    output = {
        "analysis_version": ANALYSIS_VERSION,
        "k": args.k,
        "n_per_stop": args.n_per_stop,
        "n_perm": args.n_perm,
        "seed": args.seed,
        "before": {
            "results": {k: {kk: vv for kk, vv in v.items() if kk != "null_values"} for k, v in results_before.items()},
            "contrasts": contrasts_before,
        },
        "after": {
            "results": {k: {kk: vv for kk, vv in v.items() if kk != "null_values"} for k, v in results_after.items()},
            "contrasts": contrasts_after,
        },
    }

    # Save cache
    write_json_atomic(cache_file, output)
    
    # Emit outputs
    _emit_outputs(output, out_summary, out_png, cache_meta)


def _emit_outputs(output: dict, out_summary: Path, out_png: Path, cache_meta: dict) -> None:
    """Generate LaTeX summary and histogram plot."""
    k = output["k"]
    n_per_stop = output["n_per_stop"]
    n_perm = output["n_perm"]
    
    lines = [
        f"Dinucleotide-preserving window-level shuffle null for terminal-stop "
        f"$\\overline{{U}}_{{\\mathrm{{before}}}}(k={k})$ and $\\overline{{U}}_{{\\mathrm{{after}}}}(k={k})$ "
        f"in Human RefSeq mRNA. "
        f"Sample: n={n_per_stop} per stop class. Null perms: n={n_perm}.",
    ]
    
    # Before window results
    before = output.get("before") or {}
    before_res = before.get("results") or {}
    before_con = before.get("contrasts") or []
    
    obs_strs = []
    for stop in ["UAA", "UAG", "UGA"]:
        r = before_res.get(stop) or {}
        obs_strs.append(f"{stop}={r.get('obs_mean', float('nan')):.4f}")
    lines.append(f" Before-window observed means: {', '.join(obs_strs)}.")
    
    con_strs = []
    for c in before_con:
        pair = c["pair"]
        obs = c["obs_diff"]
        null_m = c["null_diff_mean"]
        null_s = c["null_diff_std"]
        p = c["p"]
        con_strs.append(
            f"{pair}={obs:+.4f} (null {null_m:+.4f}$\\pm${null_s:.4f}, p={p:.4f})"
        )
    lines.append(f" Contrasts vs null: {'; '.join(con_strs)}.")
    
    # After window results
    after = output.get("after") or {}
    after_res = after.get("results") or {}
    after_con = after.get("contrasts") or []
    
    obs_strs = []
    for stop in ["UAA", "UAG", "UGA"]:
        r = after_res.get(stop) or {}
        obs_strs.append(f"{stop}={r.get('obs_mean', float('nan')):.4f}")
    lines.append(f" After-window observed means: {', '.join(obs_strs)}.")
    
    con_strs = []
    for c in after_con:
        pair = c["pair"]
        obs = c["obs_diff"]
        null_m = c["null_diff_mean"]
        null_s = c["null_diff_std"]
        p = c["p"]
        con_strs.append(
            f"{pair}={obs:+.4f} (null {null_m:+.4f}$\\pm${null_s:.4f}, p={p:.4f})"
        )
    lines.append(f" Contrasts vs null: {'; '.join(con_strs)}.")
    
    write_text_atomic(out_summary, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_summary), cache_meta)
    print(f"Wrote: {out_summary}")
    
    # Generate histogram plot
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        
        for ax, (window, res, con) in zip(
            axes,
            [("before", before_res, before_con), ("after", after_res, after_con)],
        ):
            # Plot observed values as vertical lines
            colors = {"UAA": "tab:blue", "UAG": "tab:orange", "UGA": "tab:green"}
            for stop in ["UAA", "UAG", "UGA"]:
                r = res.get(stop) or {}
                obs = r.get("obs_mean", float("nan"))
                null_m = r.get("null_mean", float("nan"))
                null_s = r.get("null_std", float("nan"))
                
                if not np.isnan(obs):
                    ax.axvline(obs, color=colors[stop], linestyle="-", linewidth=2, label=f"{stop} obs")
                if not np.isnan(null_m):
                    ax.axvline(null_m, color=colors[stop], linestyle="--", linewidth=1, alpha=0.7)
                    if not np.isnan(null_s):
                        ax.axvspan(null_m - 2*null_s, null_m + 2*null_s, color=colors[stop], alpha=0.1)
            
            ax.set_xlabel(f"Mean $U_{{{window}}}$")
            ax.set_ylabel("Density")
            ax.set_title(f"{window.capitalize()}-window")
            ax.legend(loc="upper right", fontsize=8)
        
        plt.tight_layout()
        plt.savefig(out_png, dpi=150)
        plt.close(fig)
        print(f"Wrote: {out_png}")
    except ImportError:
        print("[warning] matplotlib not available, skipping histogram plot")


if __name__ == "__main__":
    main()
