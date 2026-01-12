# -*- coding: utf-8 -*-
"""
Multi-k stability analysis for stop-context effects.

Tests whether the stop-class differences in U_before and U_after are stable
across different window sizes k = {3, 5, 10, 20}.

This addresses the concern that effects might be specific to a particular k.

Output:
  - sections/generated/multi_k_stability_summary.tex
  - sections/generated/multi_k_stability_table.tex
"""

from __future__ import annotations
import argparse, gzip, json, sys
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from scipy.stats import mannwhitneyu

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from genetic_code_tools import GENETIC_CODE, find_orfs, fold_codon
from cache_manager import write_text_atomic, write_json_atomic, cache_meta_path

ANALYSIS_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
STOP_CODONS = {"UAA", "UAG", "UGA"}

def root_dir(): return SCRIPT_DIR.parent
def generated_dir(): return root_dir() / "sections" / "generated"
def data_dir(): return root_dir() / "data" / "refseq_hsapiens_mrna"
def cache_dir():
    d = root_dir() / "data" / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d

def normalize_seq(seq: str) -> str:
    return seq.upper().replace("T", "U")

def window_mean_uplift(seq: str) -> float:
    seq = normalize_seq(seq)
    codons = [seq[i:i+3] for i in range(0, len(seq)-2, 3)]
    vals = []
    for c in codons:
        if c in GENETIC_CODE:
            try:
                cf = fold_codon(c, MU_STAR)
                vals.append(float(cf.delta))
            except: pass
    return float(np.mean(vals)) if vals else float("nan")

@dataclass
class ORFInfo:
    start_base: int
    stop_base: int
    stop_codon: str

def best_orf(seq: str) -> ORFInfo | None:
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
                best = ORFInfo(start_base=s, stop_base=stop_base, stop_codon=stop_codon)
                best_len = length
    return best

def _iter_fasta_handle(handle):
    header = None
    seq_parts = []
    for line in handle:
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

def load_windows(fasta_dir: Path, k_values: list[int], n_per_stop: int, seed: int) -> dict:
    """Load stop-context windows for multiple k values."""
    rng = np.random.default_rng(seed)
    k_max = max(k_values)
    
    all_data = {stop: [] for stop in STOP_CODONS}
    n_scanned = 0
    
    fasta_files = sorted(fasta_dir.glob("human.*.rna.fna.gz"))
    for fasta_path in fasta_files:
        try:
            with gzip.open(fasta_path, "rt") as f:
                for rid, seq in _iter_fasta_handle(f):
                    n_scanned += 1
                    if n_scanned % 10000 == 0:
                        print(f"  scanned {n_scanned}", flush=True)
                    
                    orf = best_orf(seq)
                    if not orf:
                        continue
                    
                    before_start = orf.stop_base - 3 * k_max
                    after_start = orf.stop_base + 3
                    
                    if before_start < orf.start_base:
                        continue
                    if after_start + 3 * k_max > len(seq):
                        continue
                    
                    # Store full windows, compute for each k later
                    before_seq = seq[before_start:orf.stop_base]
                    after_seq = seq[after_start:after_start + 3 * k_max]
                    
                    all_data[orf.stop_codon].append({
                        "before_seq": before_seq,
                        "after_seq": after_seq,
                    })
        except Exception as e:
            print(f"  [warning] {fasta_path}: {e}", flush=True)
    
    # Sample
    result = {}
    for stop, data in all_data.items():
        if len(data) > n_per_stop:
            idx = rng.choice(len(data), size=n_per_stop, replace=False)
            result[stop] = [data[i] for i in idx]
        else:
            result[stop] = data
        print(f"  {stop}: {len(result[stop])} windows", flush=True)
    
    return result

def compute_multi_k(data: dict, k_values: list[int]) -> dict:
    """Compute U_before and U_after for each k and stop codon."""
    results = {k: {} for k in k_values}
    k_max = max(k_values)
    
    for k in k_values:
        for stop, windows in data.items():
            before_vals = []
            after_vals = []
            
            for w in windows:
                before_seq = w["before_seq"]
                after_seq = w["after_seq"]
                
                # Extract the last k codons for before
                before_k = before_seq[-(3*k):]
                # Extract the first k codons for after
                after_k = after_seq[:3*k]
                
                u_before = window_mean_uplift(before_k)
                u_after = window_mean_uplift(after_k)
                
                if not np.isnan(u_before) and not np.isnan(u_after):
                    before_vals.append(u_before)
                    after_vals.append(u_after)
            
            results[k][stop] = {
                "u_before": np.array(before_vals),
                "u_after": np.array(after_vals),
                "n": len(before_vals),
            }
    
    return results

def pairwise_tests(results: dict, k_values: list[int]) -> dict:
    """Compute Mann-Whitney U tests for pairwise stop comparisons."""
    tests = {}
    
    pairs = [("UAA", "UAG"), ("UAA", "UGA"), ("UAG", "UGA")]
    
    for k in k_values:
        tests[k] = {}
        for s1, s2 in pairs:
            pair_key = f"{s1}_vs_{s2}"
            d1 = results[k][s1]
            d2 = results[k][s2]
            
            # Before
            u_b, p_b = mannwhitneyu(d1["u_before"], d2["u_before"], alternative="two-sided")
            # After
            u_a, p_a = mannwhitneyu(d1["u_after"], d2["u_after"], alternative="two-sided")
            
            tests[k][pair_key] = {
                "before": {"u_stat": float(u_b), "p": float(p_b)},
                "after": {"u_stat": float(u_a), "p": float(p_a)},
                "before_diff": float(np.mean(d1["u_before"]) - np.mean(d2["u_before"])),
                "after_diff": float(np.mean(d1["u_after"]) - np.mean(d2["u_after"])),
            }
    
    return tests

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k-values", type=str, default="3,5,10,20", help="Comma-separated k values")
    ap.add_argument("--n-per-stop", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    
    k_values = [int(x) for x in args.k_values.split(",")]
    
    out_summary = generated_dir() / "multi_k_stability_summary.tex"
    out_table = generated_dir() / "multi_k_stability_table.tex"
    cache_file = cache_dir() / f"multi_k_stability_v{ANALYSIS_VERSION}.json"
    meta = {"v": ANALYSIS_VERSION, "k_values": k_values}
    
    # Check cache
    if not args.force and cache_file.exists():
        try:
            with open(cache_file) as f:
                cached = json.load(f)
            if cached.get("k_values") == k_values:
                print("[cache] Using cached results")
                _emit(cached, out_summary, out_table, meta, k_values)
                return
        except: pass
    
    # Load data
    print(f"[load] Loading windows for k={k_values}...", flush=True)
    data = load_windows(data_dir(), k_values, args.n_per_stop, args.seed)
    
    # Compute multi-k statistics
    print("[compute] Computing U for each k...", flush=True)
    results = compute_multi_k(data, k_values)
    
    # Compute pairwise tests
    print("[tests] Running pairwise Mann-Whitney tests...", flush=True)
    tests = pairwise_tests(results, k_values)
    
    # Summarize
    summary = {
        "k_values": k_values,
        "n_per_stop": args.n_per_stop,
        "results": {},
        "tests": tests,
    }
    
    for k in k_values:
        summary["results"][k] = {}
        for stop in STOP_CODONS:
            r = results[k][stop]
            summary["results"][k][stop] = {
                "n": r["n"],
                "u_before_mean": float(np.mean(r["u_before"])),
                "u_before_std": float(np.std(r["u_before"])),
                "u_after_mean": float(np.mean(r["u_after"])),
                "u_after_std": float(np.std(r["u_after"])),
            }
    
    write_json_atomic(cache_file, summary)
    _emit(summary, out_summary, out_table, meta, k_values)

def _emit(summary: dict, out_summary: Path, out_table: Path, meta: dict, k_values: list[int]):
    """Generate LaTeX output."""
    
    def f(x): return f"{x:.3f}" if x and not np.isnan(x) else "--"
    def p_stars(p):
        if p < 0.001: return "***"
        if p < 0.01: return "**"
        if p < 0.05: return "*"
        return ""
    
    # Summary
    lines = [
        f"\\paragraph{{Multi-$k$ stability (k={','.join(map(str, k_values))}).}}",
        "Stop-class differences in $\\overline{U}_{\\mathrm{before/after}}$ across window sizes:",
    ]
    
    # Check consistency
    tests = summary.get("tests", {})
    consistent_before = True
    consistent_after = True
    
    for k in k_values:
        kt = tests.get(str(k) if isinstance(list(tests.keys())[0], str) else k, {})
        for pair in ["UAA_vs_UAG", "UAA_vs_UGA"]:
            pt = kt.get(pair, {})
            if pt.get("before", {}).get("p", 1) > 0.05:
                consistent_before = False
            if pt.get("after", {}).get("p", 1) > 0.05:
                consistent_after = False
    
    if consistent_before:
        lines.append("Before-window: effects are consistent across all $k$ ($p<0.05$ for UAA vs UAG/UGA).")
    else:
        lines.append("Before-window: effects vary with $k$.")
    
    if consistent_after:
        lines.append("After-window: effects are consistent across all $k$.")
    else:
        lines.append("After-window: effects vary with $k$ (some pairs lose significance).")
    
    write_text_atomic(out_summary, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_summary), meta)
    print(f"Wrote: {out_summary}")
    
    # Table
    table = [
        "\\begin{center}\\small",
        "\\begin{tabular}{lcccccc}\\toprule",
        " & \\multicolumn{3}{c}{Before-window} & \\multicolumn{3}{c}{After-window} \\\\",
        "\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}",
        "$k$ & UAA--UAG & UAA--UGA & UAG--UGA & UAA--UAG & UAA--UGA & UAG--UGA \\\\\\midrule",
    ]
    
    for k in k_values:
        kt = tests.get(str(k) if isinstance(list(tests.keys())[0], str) else k, {})
        
        row = [f"{k}"]
        for pair in ["UAA_vs_UAG", "UAA_vs_UGA", "UAG_vs_UGA"]:
            pt = kt.get(pair, {})
            p_b = pt.get("before", {}).get("p", 1)
            d_b = pt.get("before_diff", 0)
            row.append(f"{f(d_b)}{p_stars(p_b)}")
        
        for pair in ["UAA_vs_UAG", "UAA_vs_UGA", "UAG_vs_UGA"]:
            pt = kt.get(pair, {})
            p_a = pt.get("after", {}).get("p", 1)
            d_a = pt.get("after_diff", 0)
            row.append(f"{f(d_a)}{p_stars(p_a)}")
        
        table.append(" & ".join(row) + " \\\\")
    
    table.extend([
        "\\bottomrule",
        "\\multicolumn{7}{l}{\\footnotesize Difference in mean $\\overline{U}$; *$p<0.05$, **$p<0.01$, ***$p<0.001$.} \\\\",
        "\\end{tabular}",
        "\\end{center}",
    ])
    
    write_text_atomic(out_table, "\n".join(table) + "\n")
    write_json_atomic(cache_meta_path(out_table), meta)
    print(f"Wrote: {out_table}")

if __name__ == "__main__":
    main()
