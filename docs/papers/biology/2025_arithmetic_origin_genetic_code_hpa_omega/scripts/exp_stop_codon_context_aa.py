# -*- coding: utf-8 -*-
"""
Stop codon context analysis: amino acid immediately before stop.

Tests whether the amino acid at position -1 (immediately before stop)
influences Uplift patterns.

Output:
  - sections/generated/stop_codon_context_aa.tex
"""

from __future__ import annotations
import argparse, gzip, sys
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.stats import mannwhitneyu, kruskal

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

def codon_to_aa(codon: str) -> str:
    return GENETIC_CODE.get(normalize_seq(codon), "X")

def codon_uplift(codon: str) -> float:
    codon = normalize_seq(codon)
    if codon not in GENETIC_CODE:
        return float("nan")
    try:
        cf = fold_codon(codon, MU_STAR)
        return float(cf.delta)
    except:
        return float("nan")

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
    """Load transcripts and extract context."""
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
                    if not orf or orf["length"] < 20:
                        continue
                    
                    # Get last codon before stop
                    last_codon_start = orf["stop_base"] - 3
                    if last_codon_start < orf["start"]:
                        continue
                    
                    last_codon = seq[last_codon_start:orf["stop_base"]]
                    last_aa = codon_to_aa(last_codon)
                    last_uplift = codon_uplift(last_codon)
                    
                    # Get +4 base
                    plus4_pos = orf["stop_base"] + 3
                    plus4 = seq[plus4_pos] if plus4_pos < len(seq) else "N"
                    
                    data.append({
                        "stop": orf["stop_codon"],
                        "last_codon": normalize_seq(last_codon),
                        "last_aa": last_aa,
                        "last_uplift": last_uplift,
                        "plus4": normalize_seq(plus4),
                    })
        except Exception as e:
            pass
    
    if len(data) > n_samples:
        idx = rng.choice(len(data), size=n_samples, replace=False)
        data = [data[i] for i in idx]
    
    return data

def analyze(data: list[dict]) -> dict:
    """Analyze stop context effects."""
    results = {"n": len(data)}
    
    # Group by stop codon
    by_stop = {}
    for d in data:
        s = d["stop"]
        if s not in by_stop:
            by_stop[s] = []
        by_stop[s].append(d)
    
    results["by_stop"] = {}
    for stop, items in by_stop.items():
        aa_counts = Counter(d["last_aa"] for d in items)
        plus4_counts = Counter(d["last_codon"][-1] for d in items)  # Last base of codon
        p4_counts = Counter(d["plus4"] for d in items)
        results["by_stop"][stop] = {
            "n": len(items),
            "top_aa": dict(aa_counts.most_common(5)),
            "last_base": dict(plus4_counts),
            "plus4": dict(p4_counts),
        }
    
    # Group by last amino acid
    by_aa = {}
    for d in data:
        aa = d["last_aa"]
        if aa not in by_aa:
            by_aa[aa] = []
        by_aa[aa].append(d)
    
    results["by_aa"] = {}
    for aa, items in by_aa.items():
        uplifts = [d["last_uplift"] for d in items if not np.isnan(d["last_uplift"])]
        stop_counts = Counter(d["stop"] for d in items)
        if uplifts:
            results["by_aa"][aa] = {
                "n": len(items),
                "mean_uplift": float(np.mean(uplifts)),
                "std_uplift": float(np.std(uplifts)),
                "stop_dist": dict(stop_counts),
            }
    
    # Kruskal-Wallis test: does last_uplift differ by stop codon?
    groups = []
    for stop in ["UAA", "UAG", "UGA"]:
        items = by_stop.get(stop, [])
        uplifts = [d["last_uplift"] for d in items if not np.isnan(d["last_uplift"])]
        if uplifts:
            groups.append(uplifts)
    
    if len(groups) == 3:
        h_stat, h_p = kruskal(*groups)
        results["kruskal_last_uplift"] = {"H": float(h_stat), "p": float(h_p)}
    
    return results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-samples", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    
    out_tex = generated_dir() / "stop_codon_context_aa.tex"
    meta = {"analysis": "stop_codon_context_aa"}
    
    print("[load] Loading data...", flush=True)
    data = load_data(data_dir(), args.n_samples, args.seed)
    print(f"  Loaded {len(data)} transcripts", flush=True)
    
    print("[analyze] Analyzing context effects...", flush=True)
    results = analyze(data)
    
    _emit(results, out_tex, meta)

def _emit(results: dict, out_tex: Path, meta: dict):
    """Generate LaTeX."""
    def f(x): return f"{x:.2f}" if x is not None and not np.isnan(x) else "--"
    def p_fmt(p):
        if p is None or np.isnan(p): return "--"
        if p < 0.001: return "$<$0.001"
        return f"{p:.3f}"
    
    lines = [
        f"\\paragraph{{Stop codon context: last amino acid analysis (n={results['n']}).}}",
    ]
    
    # By stop codon
    lines.append("\\textbf{By stop codon:}")
    for stop in ["UAA", "UAG", "UGA"]:
        info = results.get("by_stop", {}).get(stop, {})
        if info:
            top_aa = ", ".join(f"{aa}({n})" for aa, n in list(info.get("top_aa", {}).items())[:3])
            p4 = info.get("plus4", {})
            lines.append(
                f"  {stop} (n={info['n']}): top AA = {top_aa}; +4 dist = A:{p4.get('A',0)}, C:{p4.get('C',0)}, G:{p4.get('G',0)}, U:{p4.get('U',0)}."
            )
    
    # Kruskal test
    kt = results.get("kruskal_last_uplift", {})
    if kt:
        lines.append(
            f"Kruskal-Wallis test (last-codon Uplift by stop): $H={f(kt.get('H'))}$, $p$={p_fmt(kt.get('p'))}."
        )
    
    # Top amino acids table
    lines.append("\\begin{center}\\small")
    lines.append("\\begin{tabular}{lrrrl}\\toprule")
    lines.append("AA & n & $\\bar\\Delta$ & $\\sigma$ & Stop preference \\\\\\midrule")
    
    # Sort by count
    sorted_aa = sorted(results.get("by_aa", {}).items(), key=lambda x: -x[1]["n"])[:10]
    for aa, info in sorted_aa:
        stop_pref = max(info.get("stop_dist", {}).items(), key=lambda x: x[1])[0] if info.get("stop_dist") else "--"
        lines.append(
            f"{aa} & {info['n']} & {f(info['mean_uplift'])} & {f(info['std_uplift'])} & {stop_pref} \\\\"
        )
    
    lines.append("\\bottomrule\\end{tabular}\\end{center}")
    
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    print(f"Wrote: {out_tex}")

if __name__ == "__main__":
    main()
