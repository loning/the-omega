# -*- coding: utf-8 -*-
"""
Effect size summary for key comparisons.

Computes Cohen's d for all major Uplift comparisons to provide
standardized effect sizes beyond p-values.

Output:
  - sections/generated/effect_sizes.tex
"""

from __future__ import annotations
import gzip, sys
from pathlib import Path
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from genetic_code_tools import GENETIC_CODE, find_orfs, fold_codon
from cache_manager import write_text_atomic, write_json_atomic, cache_meta_path

MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
STOP_CODONS = {"UAA", "UAG", "UGA"}

def root_dir(): return SCRIPT_DIR.parent
def generated_dir(): return root_dir() / "sections" / "generated"
def data_dir(): return root_dir() / "data" / "refseq_hsapiens_mrna"

def normalize_seq(seq: str) -> str:
    return seq.upper().replace("T", "U")

def window_mean_uplift(seq: str, k: int = 10) -> float:
    seq = normalize_seq(seq)
    codons = [seq[i:i+3] for i in range(0, min(len(seq), k*3), 3)]
    vals = []
    for c in codons:
        if c in GENETIC_CODE:
            try:
                cf = fold_codon(c, MU_STAR)
                vals.append(float(cf.delta))
            except: pass
    return float(np.mean(vals)) if vals else float("nan")

def cohens_d(group1: list, group2: list) -> float:
    """Compute Cohen's d effect size."""
    g1 = np.array([x for x in group1 if not np.isnan(x)])
    g2 = np.array([x for x in group2 if not np.isnan(x)])
    
    if len(g1) < 2 or len(g2) < 2:
        return float("nan")
    
    n1, n2 = len(g1), len(g2)
    var1, var2 = np.var(g1, ddof=1), np.var(g2, ddof=1)
    
    # Pooled standard deviation
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    
    if pooled_std == 0:
        return float("nan")
    
    return (np.mean(g1) - np.mean(g2)) / pooled_std

def interpret_d(d: float) -> str:
    """Interpret Cohen's d magnitude."""
    d = abs(d)
    if np.isnan(d): return "--"
    if d < 0.2: return "negligible"
    if d < 0.5: return "small"
    if d < 0.8: return "medium"
    return "large"

def best_orf(seq: str):
    seq = normalize_seq(seq)
    best = None
    best_len = 0
    for frame in range(3):
        orfs = find_orfs(seq, frame=frame, min_codons=10)
        for (s, e) in orfs:
            length = (e - s) // 3
            stop_base = s + length * 3
            if stop_base + 3 > len(seq):
                continue
            stop_codon = seq[stop_base:stop_base+3]
            if stop_codon not in STOP_CODONS:
                continue
            if length > best_len:
                best = {"start": s, "stop_base": stop_base, "stop_codon": stop_codon}
                best_len = length
    return best

def _iter_fasta(fh):
    header = None
    seq_parts = []
    for line in fh:
        line = line.strip()
        if line.startswith(">"):
            if header:
                yield header, "".join(seq_parts)
            header = line[1:].split()[0]
            seq_parts = []
        else:
            seq_parts.append(line)
    if header:
        yield header, "".join(seq_parts)

def load_data(data_dir: Path, n_samples: int = 10000, seed: int = 42):
    """Load stop-context data."""
    rng = np.random.default_rng(seed)
    data = []
    n_scanned = 0
    
    fasta_files = sorted(data_dir.glob("human.*.rna.fna.gz"))
    
    for fasta_path in fasta_files:
        if len(data) >= n_samples * 3:
            break
        try:
            with gzip.open(fasta_path, "rt") as f:
                for rid, seq in _iter_fasta(f):
                    n_scanned += 1
                    
                    orf = best_orf(seq)
                    if not orf:
                        continue
                    
                    k = 10
                    before_start = orf["stop_base"] - 3 * k
                    after_start = orf["stop_base"] + 3
                    after_end = after_start + 3 * k
                    
                    if before_start < orf["start"] or after_end > len(seq):
                        continue
                    
                    before_seq = seq[before_start:orf["stop_base"]]
                    after_seq = seq[after_start:after_end]
                    plus4 = normalize_seq(seq[after_start]) if after_start < len(seq) else "N"
                    
                    data.append({
                        "stop": orf["stop_codon"],
                        "plus4": plus4,
                        "before": window_mean_uplift(before_seq),
                        "after": window_mean_uplift(after_seq),
                    })
        except Exception as e:
            pass
    
    if len(data) > n_samples:
        idx = rng.choice(len(data), size=n_samples, replace=False)
        data = [data[i] for i in idx]
    
    return data

def compute_effect_sizes(data: list[dict]) -> dict:
    """Compute effect sizes for all comparisons."""
    results = {"n": len(data)}
    
    # Group by stop
    by_stop = {s: [] for s in STOP_CODONS}
    for d in data:
        by_stop[d["stop"]].append(d)
    
    # 1. Stop codon pairwise comparisons
    results["stop_pairs"] = {}
    for s1, s2 in [("UAA", "UAG"), ("UAA", "UGA"), ("UAG", "UGA")]:
        g1_before = [d["before"] for d in by_stop[s1]]
        g2_before = [d["before"] for d in by_stop[s2]]
        g1_after = [d["after"] for d in by_stop[s1]]
        g2_after = [d["after"] for d in by_stop[s2]]
        
        results["stop_pairs"][f"{s1}_vs_{s2}"] = {
            "before_d": cohens_d(g1_before, g2_before),
            "after_d": cohens_d(g1_after, g2_after),
            "n1": len(by_stop[s1]),
            "n2": len(by_stop[s2]),
        }
    
    # 2. Before vs After within each stop
    results["before_vs_after"] = {}
    for stop in STOP_CODONS:
        before = [d["before"] for d in by_stop[stop]]
        after = [d["after"] for d in by_stop[stop]]
        results["before_vs_after"][stop] = {
            "d": cohens_d(after, before),
            "n": len(by_stop[stop]),
        }
    
    # 3. +4 purine vs pyrimidine
    results["plus4_effect"] = {}
    for stop in STOP_CODONS:
        purine = [d for d in by_stop[stop] if d["plus4"] in "AG"]
        pyrimidine = [d for d in by_stop[stop] if d["plus4"] in "CU"]
        
        if len(purine) >= 50 and len(pyrimidine) >= 50:
            results["plus4_effect"][stop] = {
                "before_d": cohens_d([d["before"] for d in purine], [d["before"] for d in pyrimidine]),
                "after_d": cohens_d([d["after"] for d in purine], [d["after"] for d in pyrimidine]),
            }
    
    return results

def main():
    out_tex = generated_dir() / "effect_sizes.tex"
    meta = {"analysis": "effect_sizes"}
    
    print("[load] Loading data...", flush=True)
    data = load_data(data_dir(), n_samples=15000)
    print(f"  Loaded {len(data)} transcripts", flush=True)
    
    print("[analyze] Computing effect sizes...", flush=True)
    results = compute_effect_sizes(data)
    
    _emit(results, out_tex, meta)

def _emit(results: dict, out_tex: Path, meta: dict):
    """Generate LaTeX."""
    def f(d): 
        if d is None or np.isnan(d): return "--"
        return f"{d:+.3f}"
    
    lines = [
        f"\\paragraph{{Effect sizes (Cohen's $d$) for key comparisons (n={results['n']}).}}",
        "\\begin{center}\\small",
        "\\begin{tabular}{llrrl}\\toprule",
        "Comparison & Window & Cohen's $d$ & n & Magnitude \\\\\\midrule",
    ]
    
    # Stop pairs
    for pair, vals in results.get("stop_pairs", {}).items():
        s1, s2 = pair.split("_vs_")
        lines.append(
            f"{s1}--{s2} & before & {f(vals['before_d'])} & {vals['n1']}+{vals['n2']} & {interpret_d(vals['before_d'])} \\\\"
        )
        lines.append(
            f" & after & {f(vals['after_d'])} & & {interpret_d(vals['after_d'])} \\\\"
        )
    
    lines.append("\\midrule")
    
    # Before vs After
    for stop, vals in results.get("before_vs_after", {}).items():
        lines.append(
            f"{stop} after--before & -- & {f(vals['d'])} & {vals['n']} & {interpret_d(vals['d'])} \\\\"
        )
    
    lines.append("\\midrule")
    
    # +4 effect
    lines.append("\\multicolumn{5}{c}{\\textit{+4 Purine vs Pyrimidine}} \\\\")
    for stop, vals in results.get("plus4_effect", {}).items():
        lines.append(
            f"{stop} & before & {f(vals['before_d'])} & -- & {interpret_d(vals['before_d'])} \\\\"
        )
        lines.append(
            f" & after & {f(vals['after_d'])} & -- & {interpret_d(vals['after_d'])} \\\\"
        )
    
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{center}",
        "\\footnotesize Magnitude: $|d|<0.2$ negligible, $0.2{-}0.5$ small, $0.5{-}0.8$ medium, $>0.8$ large.",
    ])
    
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    print(f"Wrote: {out_tex}")

if __name__ == "__main__":
    main()
