# -*- coding: utf-8 -*-
"""
Codon usage bias vs Uplift analysis.

Tests whether commonly used codons have systematically different Uplift values.
If evolution optimizes codon usage, there may be a signature in Uplift.

Output:
  - sections/generated/codon_usage_uplift.tex
"""

from __future__ import annotations
import gzip, sys
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.stats import spearmanr

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

def codon_uplift(codon: str) -> float:
    codon = normalize_seq(codon)
    if codon not in GENETIC_CODE:
        return float("nan")
    try:
        cf = fold_codon(codon, MU_STAR)
        return float(cf.delta)
    except:
        return float("nan")

def gc3(codon: str) -> int:
    """Return 1 if third position is G or C, 0 otherwise."""
    codon = normalize_seq(codon)
    return 1 if codon[2] in "GC" else 0

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
                best = {"start": s, "stop_base": stop_base, "length": length}
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

def count_codons(data_dir: Path, max_records: int = 50000) -> Counter:
    """Count codon usage across transcriptome."""
    codon_counts = Counter()
    n_records = 0
    
    fasta_files = sorted(data_dir.glob("human.*.rna.fna.gz"))
    
    for fasta_path in fasta_files:
        if n_records >= max_records:
            break
        try:
            with gzip.open(fasta_path, "rt") as f:
                for rid, seq in _iter_fasta(f):
                    n_records += 1
                    if n_records % 10000 == 0:
                        print(f"  processed {n_records}", flush=True)
                    
                    orf = best_orf(seq)
                    if not orf:
                        continue
                    
                    # Count codons in CDS
                    for i in range(orf["start"], orf["stop_base"], 3):
                        codon = normalize_seq(seq[i:i+3])
                        if len(codon) == 3 and codon in GENETIC_CODE:
                            codon_counts[codon] += 1
        except Exception as e:
            pass
    
    return codon_counts

def analyze(codon_counts: Counter) -> dict:
    """Analyze codon usage vs Uplift."""
    # Get all sense codons
    sense_codons = [c for c in GENETIC_CODE if GENETIC_CODE[c] != "*"]
    
    # Compute frequencies and Uplift
    total = sum(codon_counts[c] for c in sense_codons)
    
    data = []
    for codon in sense_codons:
        count = codon_counts[codon]
        freq = count / total if total > 0 else 0
        uplift = codon_uplift(codon)
        aa = GENETIC_CODE[codon]
        
        data.append({
            "codon": codon,
            "aa": aa,
            "count": count,
            "freq": freq,
            "uplift": uplift,
            "gc3": gc3(codon),
        })
    
    # Sort by frequency
    data.sort(key=lambda x: -x["freq"])
    
    # Correlations
    freqs = np.array([d["freq"] for d in data])
    uplifts = np.array([d["uplift"] for d in data])
    gc3s = np.array([d["gc3"] for d in data])
    
    r_freq_uplift, p_freq_uplift = spearmanr(freqs, uplifts)
    r_freq_gc3, p_freq_gc3 = spearmanr(freqs, gc3s)
    r_uplift_gc3, p_uplift_gc3 = spearmanr(uplifts, gc3s)
    
    # Within-family analysis: for each amino acid, correlate freq with uplift
    aa_to_codons = {}
    for d in data:
        aa = d["aa"]
        if aa not in aa_to_codons:
            aa_to_codons[aa] = []
        aa_to_codons[aa].append(d)
    
    within_family = {}
    for aa, codons in aa_to_codons.items():
        if len(codons) >= 2:
            freqs_aa = np.array([c["freq"] for c in codons])
            uplifts_aa = np.array([c["uplift"] for c in codons])
            if len(set(uplifts_aa)) > 1:  # Need variance
                r, p = spearmanr(freqs_aa, uplifts_aa)
                within_family[aa] = {"r": float(r), "p": float(p), "n": len(codons)}
    
    return {
        "codon_data": data[:20],  # Top 20
        "correlations": {
            "freq_uplift": {"r": float(r_freq_uplift), "p": float(p_freq_uplift)},
            "freq_gc3": {"r": float(r_freq_gc3), "p": float(p_freq_gc3)},
            "uplift_gc3": {"r": float(r_uplift_gc3), "p": float(p_uplift_gc3)},
        },
        "within_family": within_family,
        "total_codons": total,
        "n_sense": len(sense_codons),
    }

def main():
    out_tex = generated_dir() / "codon_usage_uplift.tex"
    meta = {"analysis": "codon_usage_uplift"}
    
    print("[count] Counting codons...", flush=True)
    codon_counts = count_codons(data_dir(), max_records=30000)
    print(f"  Total codons: {sum(codon_counts.values())}", flush=True)
    
    print("[analyze] Analyzing...", flush=True)
    results = analyze(codon_counts)
    
    _emit(results, out_tex, meta)

def _emit(results: dict, out_tex: Path, meta: dict):
    """Generate LaTeX."""
    def f(x): return f"{x:.3f}" if x is not None and not np.isnan(x) else "--"
    def p_fmt(p):
        if p is None or np.isnan(p): return "--"
        if p < 0.001: return "$<$0.001"
        return f"{p:.3f}"
    
    corr = results.get("correlations", {})
    
    lines = [
        f"\\paragraph{{Codon usage vs Uplift (n={results['total_codons']:,} codons, {results['n_sense']} sense codons).}}",
        f"Global correlations: Freq--Uplift $\\rho={f(corr['freq_uplift']['r'])}$ ($p$={p_fmt(corr['freq_uplift']['p'])}), "
        f"Freq--GC3 $\\rho={f(corr['freq_gc3']['r'])}$ ($p$={p_fmt(corr['freq_gc3']['p'])}), "
        f"Uplift--GC3 $\\rho={f(corr['uplift_gc3']['r'])}$ ($p$={p_fmt(corr['uplift_gc3']['p'])}).",
    ]
    
    # Top codons table
    lines.append("\\begin{center}\\small")
    lines.append("\\begin{tabular}{llrrr}\\toprule")
    lines.append("Codon & AA & Freq (\\%) & Uplift & GC3 \\\\\\midrule")
    
    for d in results.get("codon_data", [])[:10]:
        lines.append(
            f"{d['codon']} & {d['aa']} & {d['freq']*100:.2f} & {d['uplift']:.0f} & {d['gc3']} \\\\"
        )
    
    lines.append("\\bottomrule\\end{tabular}\\end{center}")
    
    # Within-family analysis
    wf = results.get("within_family", {})
    if wf:
        # Count positive and negative correlations
        pos = sum(1 for v in wf.values() if v["r"] > 0)
        neg = sum(1 for v in wf.values() if v["r"] < 0)
        sig = sum(1 for v in wf.values() if v["p"] < 0.05)
        lines.append(
            f"Within-family (synonymous): {pos}/{len(wf)} positive correlations, {neg}/{len(wf)} negative; {sig} significant ($p<0.05$)."
        )
    
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    print(f"Wrote: {out_tex}")

if __name__ == "__main__":
    main()
