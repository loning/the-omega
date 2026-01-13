# -*- coding: utf-8 -*-
"""
Gene length stratification analysis.

Tests whether Uplift patterns depend on gene length - a potential confound
since longer genes may have different codon usage patterns.

Output:
  - sections/generated/gene_length_stratification.tex
"""

from __future__ import annotations
import argparse, gzip, sys
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr, mannwhitneyu

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

def gc_fraction(seq: str) -> float:
    seq = normalize_seq(seq)
    if not seq: return float("nan")
    return sum(1 for ch in seq if ch in "GC") / len(seq)

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
                best = {
                    "start": s,
                    "stop_base": stop_base,
                    "stop_codon": stop_codon,
                    "length": length,
                }
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
    """Load transcripts and compute features."""
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
                    if n_scanned % 10000 == 0:
                        print(f"  scanned {n_scanned}, collected {len(data)}", flush=True)
                    
                    orf = best_orf(seq)
                    if not orf or orf["length"] < 20:
                        continue
                    
                    k = 10
                    before_start = orf["stop_base"] - 3 * k
                    after_start = orf["stop_base"] + 3
                    after_end = after_start + 3 * k
                    
                    if before_start < orf["start"] or after_end > len(seq):
                        continue
                    
                    before_seq = seq[before_start:orf["stop_base"]]
                    after_seq = seq[after_start:after_end]
                    
                    data.append({
                        "gene_length": orf["length"],
                        "stop": orf["stop_codon"],
                        "before_uplift": window_mean_uplift(before_seq),
                        "after_uplift": window_mean_uplift(after_seq),
                        "before_gc": gc_fraction(before_seq),
                        "after_gc": gc_fraction(after_seq),
                    })
        except Exception as e:
            print(f"  [warning] {fasta_path}: {e}", flush=True)
    
    if len(data) > n_samples:
        idx = rng.choice(len(data), size=n_samples, replace=False)
        data = [data[i] for i in idx]
    
    return data

def analyze(data: list[dict]) -> dict:
    """Analyze gene length effects."""
    lengths = np.array([d["gene_length"] for d in data])
    before_u = np.array([d["before_uplift"] for d in data])
    after_u = np.array([d["after_uplift"] for d in data])
    before_gc = np.array([d["before_gc"] for d in data])
    after_gc = np.array([d["after_gc"] for d in data])
    
    # Remove NaN
    valid = ~(np.isnan(before_u) | np.isnan(after_u) | np.isnan(lengths))
    lengths = lengths[valid]
    before_u = before_u[valid]
    after_u = after_u[valid]
    before_gc = before_gc[valid]
    after_gc = after_gc[valid]
    
    results = {"n": len(lengths)}
    
    # Length-Uplift correlation
    r_before, p_before = spearmanr(lengths, before_u)
    r_after, p_after = spearmanr(lengths, after_u)
    results["length_before"] = {"r": float(r_before), "p": float(p_before)}
    results["length_after"] = {"r": float(r_after), "p": float(p_after)}
    
    # Length-GC correlation
    r_gc_b, p_gc_b = spearmanr(lengths, before_gc)
    r_gc_a, p_gc_a = spearmanr(lengths, after_gc)
    results["length_gc_before"] = {"r": float(r_gc_b), "p": float(p_gc_b)}
    results["length_gc_after"] = {"r": float(r_gc_a), "p": float(p_gc_a)}
    
    # Partial correlation (control for GC)
    from numpy.linalg import lstsq
    G = before_gc.reshape(-1, 1)
    cl, _, _, _ = lstsq(G, lengths, rcond=None)
    cu, _, _, _ = lstsq(G, before_u, rcond=None)
    r_partial_b, p_partial_b = spearmanr(lengths - G @ cl, before_u - G @ cu)
    results["partial_before"] = {"r": float(r_partial_b), "p": float(p_partial_b)}
    
    G = after_gc.reshape(-1, 1)
    cl, _, _, _ = lstsq(G, lengths, rcond=None)
    cu, _, _, _ = lstsq(G, after_u, rcond=None)
    r_partial_a, p_partial_a = spearmanr(lengths - G @ cl, after_u - G @ cu)
    results["partial_after"] = {"r": float(r_partial_a), "p": float(p_partial_a)}
    
    # Stratify by length quartiles
    q1, q2, q3 = np.percentile(lengths, [25, 50, 75])
    results["quartiles"] = {}
    
    for label, mask in [
        ("Q1 (short)", lengths <= q1),
        ("Q2", (lengths > q1) & (lengths <= q2)),
        ("Q3", (lengths > q2) & (lengths <= q3)),
        ("Q4 (long)", lengths > q3),
    ]:
        if mask.sum() > 0:
            results["quartiles"][label] = {
                "n": int(mask.sum()),
                "mean_length": float(np.mean(lengths[mask])),
                "before_uplift": float(np.mean(before_u[mask])),
                "after_uplift": float(np.mean(after_u[mask])),
            }
    
    # Compare short vs long
    short = lengths <= q1
    long = lengths > q3
    if short.sum() > 0 and long.sum() > 0:
        u_b, p_b = mannwhitneyu(before_u[short], before_u[long], alternative="two-sided")
        u_a, p_a = mannwhitneyu(after_u[short], after_u[long], alternative="two-sided")
        results["short_vs_long"] = {
            "before_p": float(p_b),
            "after_p": float(p_a),
            "before_diff": float(np.mean(before_u[short]) - np.mean(before_u[long])),
            "after_diff": float(np.mean(after_u[short]) - np.mean(after_u[long])),
        }
    
    return results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-samples", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    
    out_tex = generated_dir() / "gene_length_stratification.tex"
    meta = {"analysis": "gene_length_stratification"}
    
    print("[load] Loading data...", flush=True)
    data = load_data(data_dir(), args.n_samples, args.seed)
    print(f"  Loaded {len(data)} transcripts", flush=True)
    
    print("[analyze] Analyzing length effects...", flush=True)
    results = analyze(data)
    
    _emit(results, out_tex, meta)

def _emit(results: dict, out_tex: Path, meta: dict):
    """Generate LaTeX."""
    def f(x): return f"{x:.3f}" if x is not None and not np.isnan(x) else "--"
    def p_fmt(p):
        if p is None or np.isnan(p): return "--"
        if p < 0.001: return "$<$0.001"
        return f"{p:.3f}"
    
    lines = [
        f"\\paragraph{{Gene length stratification (n={results['n']}).}}",
        f"Length--Uplift correlations: before $\\rho={f(results['length_before']['r'])}$ ($p$={p_fmt(results['length_before']['p'])}), "
        f"after $\\rho={f(results['length_after']['r'])}$ ($p$={p_fmt(results['length_after']['p'])}).",
        f"Partial (GC-controlled): before $\\rho={f(results['partial_before']['r'])}$, after $\\rho={f(results['partial_after']['r'])}$.",
    ]
    
    # Quartile table
    lines.append("\\begin{center}\\small")
    lines.append("\\begin{tabular}{lrrrr}\\toprule")
    lines.append("Quartile & n & Mean length & $\\bar U_{before}$ & $\\bar U_{after}$ \\\\\\midrule")
    
    for label, vals in results.get("quartiles", {}).items():
        lines.append(
            f"{label} & {vals['n']} & {vals['mean_length']:.0f} & "
            f"{f(vals['before_uplift'])} & {f(vals['after_uplift'])} \\\\"
        )
    
    lines.append("\\bottomrule\\end{tabular}\\end{center}")
    
    # Short vs long comparison
    svl = results.get("short_vs_long", {})
    if svl:
        lines.append(
            f"Short vs long: before diff={f(svl.get('before_diff'))}, $p$={p_fmt(svl.get('before_p'))}; "
            f"after diff={f(svl.get('after_diff'))}, $p$={p_fmt(svl.get('after_p'))}."
        )
    
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    print(f"Wrote: {out_tex}")

if __name__ == "__main__":
    main()
