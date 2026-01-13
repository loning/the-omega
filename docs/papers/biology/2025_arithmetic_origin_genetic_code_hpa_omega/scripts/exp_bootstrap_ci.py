# -*- coding: utf-8 -*-
"""
Bootstrap confidence intervals for key Uplift statistics.

Provides non-parametric confidence intervals for the main findings.

Output:
  - sections/generated/bootstrap_ci.tex
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

def load_data(data_dir: Path, n_samples: int, seed: int):
    """Load stop-context windows."""
    rng = np.random.default_rng(seed)
    data = {stop: {"before": [], "after": []} for stop in STOP_CODONS}
    n_scanned = 0
    
    fasta_files = sorted(data_dir.glob("human.*.rna.fna.gz"))
    total_needed = n_samples * 3
    
    for fasta_path in fasta_files:
        if sum(len(data[s]["before"]) for s in STOP_CODONS) >= total_needed:
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
                    
                    before_u = window_mean_uplift(before_seq)
                    after_u = window_mean_uplift(after_seq)
                    
                    if not np.isnan(before_u) and not np.isnan(after_u):
                        data[orf["stop_codon"]]["before"].append(before_u)
                        data[orf["stop_codon"]]["after"].append(after_u)
        except Exception as e:
            pass
    
    # Sample to target size
    for stop in STOP_CODONS:
        if len(data[stop]["before"]) > n_samples:
            idx = rng.choice(len(data[stop]["before"]), size=n_samples, replace=False)
            data[stop]["before"] = [data[stop]["before"][i] for i in idx]
            data[stop]["after"] = [data[stop]["after"][i] for i in idx]
    
    return data

def bootstrap_ci(values: list, stat_func, n_boot: int = 2000, ci: float = 0.95, seed: int = 0) -> dict:
    """Compute bootstrap confidence interval."""
    rng = np.random.default_rng(seed)
    values = np.array(values)
    n = len(values)
    
    if n < 10:
        return {"est": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}
    
    observed = stat_func(values)
    
    boot_stats = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boot_sample = values[idx]
        boot_stats.append(stat_func(boot_sample))
    
    boot_stats = np.array(boot_stats)
    alpha = (1 - ci) / 2
    ci_low = np.percentile(boot_stats, alpha * 100)
    ci_high = np.percentile(boot_stats, (1 - alpha) * 100)
    
    return {
        "est": float(observed),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "se": float(np.std(boot_stats)),
    }

def bootstrap_diff_ci(a: list, b: list, n_boot: int = 2000, ci: float = 0.95, seed: int = 0) -> dict:
    """Bootstrap CI for difference of means."""
    rng = np.random.default_rng(seed)
    a = np.array(a)
    b = np.array(b)
    
    if len(a) < 10 or len(b) < 10:
        return {"est": float("nan"), "ci_low": float("nan"), "ci_high": float("nan")}
    
    observed = np.mean(a) - np.mean(b)
    
    boot_diffs = []
    for _ in range(n_boot):
        a_boot = a[rng.integers(0, len(a), size=len(a))]
        b_boot = b[rng.integers(0, len(b), size=len(b))]
        boot_diffs.append(np.mean(a_boot) - np.mean(b_boot))
    
    boot_diffs = np.array(boot_diffs)
    alpha = (1 - ci) / 2
    
    return {
        "est": float(observed),
        "ci_low": float(np.percentile(boot_diffs, alpha * 100)),
        "ci_high": float(np.percentile(boot_diffs, (1 - alpha) * 100)),
        "se": float(np.std(boot_diffs)),
    }

def main():
    out_tex = generated_dir() / "bootstrap_ci.tex"
    meta = {"analysis": "bootstrap_ci"}
    
    print("[load] Loading data...", flush=True)
    data = load_data(data_dir(), n_samples=5000, seed=42)
    for s in STOP_CODONS:
        print(f"  {s}: n={len(data[s]['before'])}", flush=True)
    
    print("[bootstrap] Computing CIs...", flush=True)
    results = {}
    
    # Mean Uplift per stop codon
    for stop in ["UAA", "UAG", "UGA"]:
        results[stop] = {
            "before": bootstrap_ci(data[stop]["before"], np.mean, n_boot=2000),
            "after": bootstrap_ci(data[stop]["after"], np.mean, n_boot=2000),
        }
    
    # Pairwise differences
    results["diffs"] = {}
    for s1, s2 in [("UAA", "UAG"), ("UAA", "UGA"), ("UAG", "UGA")]:
        key = f"{s1}_vs_{s2}"
        results["diffs"][key] = {
            "before": bootstrap_diff_ci(data[s1]["before"], data[s2]["before"]),
            "after": bootstrap_diff_ci(data[s1]["after"], data[s2]["after"]),
        }
    
    _emit(results, out_tex, meta)

def _emit(results: dict, out_tex: Path, meta: dict):
    """Generate LaTeX."""
    def f(x): return f"{x:.2f}" if x is not None and not np.isnan(x) else "--"
    
    lines = [
        "\\paragraph{Bootstrap 95\\% confidence intervals (n=2000 resamples).}",
        "\\begin{center}\\small",
        "\\begin{tabular}{llrrr}\\toprule",
        "Stop & Window & Mean & 95\\% CI & SE \\\\\\midrule",
    ]
    
    for stop in ["UAA", "UAG", "UGA"]:
        for window in ["before", "after"]:
            ci = results.get(stop, {}).get(window, {})
            lines.append(
                f"{stop} & {window} & {f(ci.get('est'))} & [{f(ci.get('ci_low'))}, {f(ci.get('ci_high'))}] & {f(ci.get('se'))} \\\\"
            )
    
    lines.extend([
        "\\midrule",
        "\\multicolumn{5}{c}{\\textit{Pairwise differences}} \\\\\\midrule",
    ])
    
    for key, label in [("UAA_vs_UAG", "UAA--UAG"), ("UAA_vs_UGA", "UAA--UGA"), ("UAG_vs_UGA", "UAG--UGA")]:
        for window in ["before", "after"]:
            ci = results.get("diffs", {}).get(key, {}).get(window, {})
            sig = "*" if ci.get("ci_low", 0) > 0 or ci.get("ci_high", 0) < 0 else ""
            lines.append(
                f"{label} & {window} & {f(ci.get('est'))} & [{f(ci.get('ci_low'))}, {f(ci.get('ci_high'))}]{sig} & {f(ci.get('se'))} \\\\"
            )
    
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{center}",
        "\\footnotesize $*$ indicates CI excludes zero (significant difference).",
    ])
    
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    print(f"Wrote: {out_tex}")

if __name__ == "__main__":
    main()
