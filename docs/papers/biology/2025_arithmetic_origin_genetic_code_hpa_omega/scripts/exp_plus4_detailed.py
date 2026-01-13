# -*- coding: utf-8 -*-
"""
Detailed +4 base analysis.

The +4 position (first nucleotide after stop codon) is known to strongly
influence termination efficiency. This script analyzes how +4 interacts
with Uplift patterns.

Output:
  - sections/generated/plus4_detailed.tex
"""

from __future__ import annotations
import gzip, sys
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.stats import mannwhitneyu, chi2_contingency

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from genetic_code_tools import GENETIC_CODE, find_orfs, fold_codon
from cache_manager import write_text_atomic, write_json_atomic, cache_meta_path

MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
STOP_CODONS = {"UAA", "UAG", "UGA"}
NUCS = ["A", "C", "G", "U"]

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

def window_mean_uplift(seq: str, k: int = 10) -> float:
    seq = normalize_seq(seq)
    codons = [seq[i:i+3] for i in range(0, min(len(seq), k*3), 3)]
    vals = [codon_uplift(c) for c in codons if len(c) == 3]
    vals = [v for v in vals if not np.isnan(v)]
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
                best = {"start": s, "stop_base": stop_base, "stop_codon": stop_codon, "length": length}
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
    """Load transcripts and extract +4 context."""
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
                    
                    k = 10
                    before_start = orf["stop_base"] - 3 * k
                    after_start = orf["stop_base"] + 3
                    
                    if before_start < orf["start"]:
                        continue
                    if after_start + 30 > len(seq):
                        continue
                    
                    before_seq = seq[before_start:orf["stop_base"]]
                    after_seq = seq[after_start:after_start + 30]
                    
                    plus4 = normalize_seq(seq[after_start]) if after_start < len(seq) else "N"
                    
                    data.append({
                        "stop": orf["stop_codon"],
                        "plus4": plus4,
                        "before_uplift": window_mean_uplift(before_seq),
                        "after_uplift": window_mean_uplift(after_seq),
                    })
        except Exception as e:
            pass
    
    if len(data) > n_samples:
        idx = rng.choice(len(data), size=n_samples, replace=False)
        data = [data[i] for i in idx]
    
    return data

def analyze(data: list[dict]) -> dict:
    """Analyze +4 effects on Uplift."""
    results = {"n": len(data)}
    
    # Group by stop and +4
    groups = {}
    for d in data:
        key = (d["stop"], d["plus4"])
        if key not in groups:
            groups[key] = []
        groups[key].append(d)
    
    # Contingency table: stop x +4
    contingency = np.zeros((3, 4), dtype=int)
    stops_order = ["UAA", "UAG", "UGA"]
    for i, stop in enumerate(stops_order):
        for j, nuc in enumerate(NUCS):
            contingency[i, j] = len(groups.get((stop, nuc), []))
    
    chi2, p_chi2, dof, expected = chi2_contingency(contingency)
    results["chi2_stop_plus4"] = {"chi2": float(chi2), "p": float(p_chi2), "dof": int(dof)}
    results["contingency"] = contingency.tolist()
    
    # Mean Uplift by stop x +4
    results["mean_uplift"] = {}
    for stop in stops_order:
        results["mean_uplift"][stop] = {}
        for nuc in NUCS:
            items = groups.get((stop, nuc), [])
            before = [d["before_uplift"] for d in items if not np.isnan(d["before_uplift"])]
            after = [d["after_uplift"] for d in items if not np.isnan(d["after_uplift"])]
            results["mean_uplift"][stop][nuc] = {
                "n": len(items),
                "before": float(np.mean(before)) if before else float("nan"),
                "after": float(np.mean(after)) if after else float("nan"),
            }
    
    # Effect of +4 within each stop codon
    results["plus4_effect"] = {}
    for stop in stops_order:
        stop_items = [d for d in data if d["stop"] == stop]
        
        # Compare purine (+4=A or G) vs pyrimidine (+4=C or U)
        purine = [d for d in stop_items if d["plus4"] in "AG"]
        pyrimidine = [d for d in stop_items if d["plus4"] in "CU"]
        
        if len(purine) >= 10 and len(pyrimidine) >= 10:
            pur_before = [d["before_uplift"] for d in purine if not np.isnan(d["before_uplift"])]
            pyr_before = [d["before_uplift"] for d in pyrimidine if not np.isnan(d["before_uplift"])]
            pur_after = [d["after_uplift"] for d in purine if not np.isnan(d["after_uplift"])]
            pyr_after = [d["after_uplift"] for d in pyrimidine if not np.isnan(d["after_uplift"])]
            
            u_before, p_before = mannwhitneyu(pur_before, pyr_before, alternative="two-sided")
            u_after, p_after = mannwhitneyu(pur_after, pyr_after, alternative="two-sided")
            
            results["plus4_effect"][stop] = {
                "purine_n": len(purine),
                "pyrimidine_n": len(pyrimidine),
                "purine_before": float(np.mean(pur_before)),
                "pyrimidine_before": float(np.mean(pyr_before)),
                "before_diff": float(np.mean(pur_before) - np.mean(pyr_before)),
                "before_p": float(p_before),
                "purine_after": float(np.mean(pur_after)),
                "pyrimidine_after": float(np.mean(pyr_after)),
                "after_diff": float(np.mean(pur_after) - np.mean(pyr_after)),
                "after_p": float(p_after),
            }
    
    return results

def main():
    out_tex = generated_dir() / "plus4_detailed.tex"
    meta = {"analysis": "plus4_detailed"}
    
    print("[load] Loading data...", flush=True)
    data = load_data(data_dir(), n_samples=15000, seed=42)
    print(f"  Loaded {len(data)} transcripts", flush=True)
    
    print("[analyze] Analyzing +4 effects...", flush=True)
    results = analyze(data)
    
    _emit(results, out_tex, meta)

def _emit(results: dict, out_tex: Path, meta: dict):
    """Generate LaTeX."""
    def f(x): return f"{x:.2f}" if x is not None and not np.isnan(x) else "--"
    def p_fmt(p):
        if p is None or np.isnan(p): return "--"
        if p < 0.001: return "$<$0.001"
        return f"{p:.3f}"
    
    chi2 = results.get("chi2_stop_plus4", {})
    
    lines = [
        f"\\paragraph{{+4 base detailed analysis (n={results['n']}).}}",
        f"Stop$\\times$+4 independence test: $\\chi^2={f(chi2.get('chi2'))}$, $p$={p_fmt(chi2.get('p'))} (df={chi2.get('dof', '--')}).",
    ]
    
    # Contingency table
    lines.append("\\begin{center}\\small")
    lines.append("\\begin{tabular}{lrrrr}\\toprule")
    lines.append("Stop & +4=A & +4=C & +4=G & +4=U \\\\\\midrule")
    
    cont = results.get("contingency", [[0]*4]*3)
    for i, stop in enumerate(["UAA", "UAG", "UGA"]):
        lines.append(f"{stop} & {cont[i][0]} & {cont[i][1]} & {cont[i][2]} & {cont[i][3]} \\\\")
    
    lines.append("\\bottomrule\\end{tabular}\\end{center}")
    
    # Purine vs pyrimidine effect
    lines.append("Purine (+4=A/G) vs Pyrimidine (+4=C/U) effect on Uplift:")
    for stop in ["UAA", "UAG", "UGA"]:
        eff = results.get("plus4_effect", {}).get(stop, {})
        if eff:
            lines.append(
                f"  {stop}: before diff={f(eff.get('before_diff'))}, $p$={p_fmt(eff.get('before_p'))}; "
                f"after diff={f(eff.get('after_diff'))}, $p$={p_fmt(eff.get('after_p'))}."
            )
    
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    print(f"Wrote: {out_tex}")

if __name__ == "__main__":
    main()
