# -*- coding: utf-8 -*-
"""
Uplift vs Translation Rate Proxy (tAI) correlation analysis.

Tests whether uplift U correlates with translation rate proxies:
1. tRNA Adaptation Index (tAI) - reflects codon translation efficiency
2. Codon usage frequency - proxy for translation speed

This addresses the "mechanistic bridge" question without requiring
full Ribo-seq data processing.

Output:
  - sections/generated/uplift_translation_rate_proxy.tex
"""

from __future__ import annotations
import argparse, gzip, json, sys
from pathlib import Path
from dataclasses import dataclass
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from genetic_code_tools import GENETIC_CODE, iter_fasta, find_orfs, fold_codon
from cache_manager import write_text_atomic, write_json_atomic, cache_meta_path

ANALYSIS_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
STOP_CODONS = {"UAA", "UAG", "UGA"}
NUCS = "ACGU"

def root_dir(): return SCRIPT_DIR.parent
def generated_dir(): return root_dir() / "sections" / "generated"
def data_dir(): return root_dir() / "data" / "refseq_hsapiens_mrna"
def cache_dir():
    d = root_dir() / "data" / "_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d

# ---- tRNA Adaptation Index (tAI) ----
# Human tAI values from dos Reis et al. (2004) and Sharp & Li (1987)
# These are relative adaptiveness values (0-1, higher = faster translation)

# Simplified human tAI based on tRNA gene copy numbers and wobble pairing
# Source: GtRNAdb (http://gtrnadb.ucsc.edu/) human genome
# Higher values indicate more efficient translation (more tRNA available)

HUMAN_TAI = {
    # Phe
    "UUU": 0.52, "UUC": 1.00,
    # Leu
    "UUA": 0.12, "UUG": 0.52, "CUU": 0.28, "CUC": 0.64, "CUA": 0.12, "CUG": 1.00,
    # Ile
    "AUU": 0.48, "AUC": 1.00, "AUA": 0.16,
    # Met
    "AUG": 1.00,
    # Val
    "GUU": 0.36, "GUC": 1.00, "GUA": 0.12, "GUG": 0.52,
    # Ser
    "UCU": 0.28, "UCC": 0.68, "UCA": 0.20, "UCG": 0.12, "AGU": 0.24, "AGC": 1.00,
    # Pro
    "CCU": 0.36, "CCC": 1.00, "CCA": 0.28, "CCG": 0.12,
    # Thr
    "ACU": 0.32, "ACC": 1.00, "ACA": 0.24, "ACG": 0.12,
    # Ala
    "GCU": 0.40, "GCC": 1.00, "GCA": 0.28, "GCG": 0.12,
    # Tyr
    "UAU": 0.44, "UAC": 1.00,
    # His
    "CAU": 0.44, "CAC": 1.00,
    # Gln
    "CAA": 0.32, "CAG": 1.00,
    # Asn
    "AAU": 0.44, "AAC": 1.00,
    # Lys
    "AAA": 0.48, "AAG": 1.00,
    # Asp
    "GAU": 0.48, "GAC": 1.00,
    # Glu
    "GAA": 0.48, "GAG": 1.00,
    # Cys
    "UGU": 0.44, "UGC": 1.00,
    # Trp
    "UGG": 1.00,
    # Arg
    "CGU": 0.16, "CGC": 0.56, "CGA": 0.12, "CGG": 0.20, "AGA": 0.20, "AGG": 0.20,
    # Gly
    "GGU": 0.24, "GGC": 1.00, "GGA": 0.28, "GGG": 0.24,
    # Stop
    "UAA": 0.0, "UAG": 0.0, "UGA": 0.0,
}

def normalize_seq(seq: str) -> str:
    return seq.upper().replace("T", "U")

def gc_fraction(seq: str) -> float:
    seq = normalize_seq(seq)
    if not seq: return float("nan")
    return sum(1 for ch in seq if ch in "GC") / len(seq)

def codon_uplift(codon: str) -> float:
    """Get uplift value for a codon under mu*."""
    codon = normalize_seq(codon)
    if codon not in GENETIC_CODE:
        return float("nan")
    try:
        cf = fold_codon(codon, MU_STAR)
        return float(cf.delta)
    except:
        return float("nan")

def codon_tai(codon: str) -> float:
    """Get tAI value for a codon."""
    codon = normalize_seq(codon)
    return HUMAN_TAI.get(codon, float("nan"))

def window_mean_uplift(seq: str) -> float:
    seq = normalize_seq(seq)
    codons = [seq[i:i+3] for i in range(0, len(seq)-2, 3)]
    vals = [codon_uplift(c) for c in codons if c in GENETIC_CODE]
    return float(np.nanmean(vals)) if vals else float("nan")

def window_mean_tai(seq: str) -> float:
    seq = normalize_seq(seq)
    codons = [seq[i:i+3] for i in range(0, len(seq)-2, 3)]
    vals = [codon_tai(c) for c in codons if c in GENETIC_CODE]
    return float(np.nanmean(vals)) if vals else float("nan")

# ---- Codon-level analysis ----

def codon_level_correlation() -> dict:
    """Compute correlation between Uplift and tAI at the codon level."""
    from scipy.stats import spearmanr, pearsonr
    
    uplifts = []
    tais = []
    codons = []
    
    for codon in GENETIC_CODE:
        if codon in STOP_CODONS:
            continue
        u = codon_uplift(codon)
        t = codon_tai(codon)
        if not np.isnan(u) and not np.isnan(t):
            uplifts.append(u)
            tais.append(t)
            codons.append(codon)
    
    uplifts = np.array(uplifts)
    tais = np.array(tais)
    
    r_spear, p_spear = spearmanr(uplifts, tais)
    r_pear, p_pear = pearsonr(uplifts, tais)
    
    return {
        "n_codons": len(codons),
        "spearman": {"r": float(r_spear), "p": float(p_spear)},
        "pearson": {"r": float(r_pear), "p": float(p_pear)},
        "uplift_mean": float(np.mean(uplifts)),
        "uplift_std": float(np.std(uplifts)),
        "tai_mean": float(np.mean(tais)),
        "tai_std": float(np.std(tais)),
    }

# ---- Window-level analysis ----

@dataclass
class ORFInfo:
    start_base: int
    stop_base: int
    stop_codon: str
    length_codons: int

def best_orf(seq: str) -> ORFInfo | None:
    seq = normalize_seq(seq)
    best = None
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
            if best is None or length > best.length_codons:
                best = ORFInfo(start_base=s, stop_base=stop_base, stop_codon=stop_codon, length_codons=length)
    return best

def _iter_fasta_handle(handle):
    header = None
    seq_parts = []
    for line in handle:
        line = line.strip()
        if line.startswith(">"):
            if header is not None:
                yield header, "".join(seq_parts)
            header = line[1:].split()[0]
            seq_parts = []
        else:
            seq_parts.append(line)
    if header is not None:
        yield header, "".join(seq_parts)

def load_window_data(fasta_files: list[Path], k: int, n_per_stop: int, seed: int) -> dict:
    """Extract stop-context windows with Uplift and tAI."""
    rng = np.random.default_rng(seed)
    
    all_data = {"UAA": [], "UAG": [], "UGA": []}
    n_scanned = 0
    
    for fasta_path in fasta_files:
        opener = gzip.open if str(fasta_path).endswith(".gz") else open
        try:
            with opener(fasta_path, "rt") as f:
                for rid, seq in _iter_fasta_handle(f):
                    n_scanned += 1
                    if n_scanned % 10000 == 0:
                        print(f"  scanned {n_scanned}", flush=True)
                    
                    orf = best_orf(seq)
                    if orf is None:
                        continue
                    
                    stop = orf.stop_codon
                    before_start = orf.stop_base - 3 * k
                    after_start = orf.stop_base + 3
                    
                    if before_start < orf.start_base:
                        continue
                    if after_start + 3 * k > len(seq):
                        continue
                    
                    before_seq = seq[before_start:orf.stop_base]
                    after_seq = seq[after_start:after_start + 3 * k]
                    
                    if len(before_seq) != 3 * k or len(after_seq) != 3 * k:
                        continue
                    
                    u_before = window_mean_uplift(before_seq)
                    u_after = window_mean_uplift(after_seq)
                    tai_before = window_mean_tai(before_seq)
                    tai_after = window_mean_tai(after_seq)
                    gc_before = gc_fraction(before_seq)
                    gc_after = gc_fraction(after_seq)
                    
                    if any(np.isnan(x) for x in [u_before, u_after, tai_before, tai_after]):
                        continue
                    
                    all_data[stop].append({
                        "u_before": u_before, "u_after": u_after,
                        "tai_before": tai_before, "tai_after": tai_after,
                        "gc_before": gc_before, "gc_after": gc_after,
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

def window_level_analysis(data: dict) -> dict:
    """Compute Uplift vs tAI correlation at window level."""
    from scipy.stats import spearmanr
    
    results = {}
    
    # Pooled
    all_u_before, all_u_after = [], []
    all_tai_before, all_tai_after = [], []
    all_gc_before, all_gc_after = [], []
    
    for stop, windows in data.items():
        u_before = np.array([w["u_before"] for w in windows])
        u_after = np.array([w["u_after"] for w in windows])
        tai_before = np.array([w["tai_before"] for w in windows])
        tai_after = np.array([w["tai_after"] for w in windows])
        gc_before = np.array([w["gc_before"] for w in windows])
        gc_after = np.array([w["gc_after"] for w in windows])
        
        all_u_before.extend(u_before)
        all_u_after.extend(u_after)
        all_tai_before.extend(tai_before)
        all_tai_after.extend(tai_after)
        all_gc_before.extend(gc_before)
        all_gc_after.extend(gc_after)
        
        # Raw correlation
        rb, pb = spearmanr(u_before, tai_before)
        ra, pa = spearmanr(u_after, tai_after)
        
        # Partial correlation (control for GC)
        def partial_gc(u, tai, gc):
            mask = ~(np.isnan(u) | np.isnan(tai) | np.isnan(gc))
            if mask.sum() < 20: return float("nan"), float("nan")
            from numpy.linalg import lstsq
            X = gc[mask].reshape(-1, 1)
            cu, _, _, _ = lstsq(X, u[mask], rcond=None)
            ct, _, _, _ = lstsq(X, tai[mask], rcond=None)
            r, p = spearmanr(u[mask] - X @ cu, tai[mask] - X @ ct)
            return float(r), float(p)
        
        rpb, ppb = partial_gc(u_before, tai_before, gc_before)
        rpa, ppa = partial_gc(u_after, tai_after, gc_after)
        
        results[stop] = {
            "n": len(windows),
            "before": {"raw": {"r": float(rb), "p": float(pb)}, "partial_gc": {"r": rpb, "p": ppb}},
            "after": {"raw": {"r": float(ra), "p": float(pa)}, "partial_gc": {"r": rpa, "p": ppa}},
            "tai_before_mean": float(np.mean(tai_before)),
            "tai_after_mean": float(np.mean(tai_after)),
        }
    
    # Pooled
    u_before = np.array(all_u_before)
    u_after = np.array(all_u_after)
    tai_before = np.array(all_tai_before)
    tai_after = np.array(all_tai_after)
    gc_before = np.array(all_gc_before)
    gc_after = np.array(all_gc_after)
    
    rb, pb = spearmanr(u_before, tai_before)
    ra, pa = spearmanr(u_after, tai_after)
    
    def partial_gc(u, tai, gc):
        mask = ~(np.isnan(u) | np.isnan(tai) | np.isnan(gc))
        if mask.sum() < 20: return float("nan"), float("nan")
        from numpy.linalg import lstsq
        X = gc[mask].reshape(-1, 1)
        cu, _, _, _ = lstsq(X, u[mask], rcond=None)
        ct, _, _, _ = lstsq(X, tai[mask], rcond=None)
        r, p = spearmanr(u[mask] - X @ cu, tai[mask] - X @ ct)
        return float(r), float(p)
    
    rpb, ppb = partial_gc(u_before, tai_before, gc_before)
    rpa, ppa = partial_gc(u_after, tai_after, gc_after)
    
    results["pooled"] = {
        "n": len(u_before),
        "before": {"raw": {"r": float(rb), "p": float(pb)}, "partial_gc": {"r": rpb, "p": ppb}},
        "after": {"raw": {"r": float(ra), "p": float(pa)}, "partial_gc": {"r": rpa, "p": ppa}},
        "tai_before_mean": float(np.mean(tai_before)),
        "tai_after_mean": float(np.mean(tai_after)),
    }
    
    return results

# ---- Main ----

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--n-per-stop", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    
    out_file = generated_dir() / "uplift_translation_rate_proxy.tex"
    cache_file = cache_dir() / f"uplift_tai_v{ANALYSIS_VERSION}.json"
    meta = {"v": ANALYSIS_VERSION, "k": args.k, "n": args.n_per_stop}
    
    # Check cache
    if not args.force and cache_file.exists():
        try:
            with open(cache_file) as f:
                cached = json.load(f)
            if cached.get("k") == args.k:
                print("[cache] Using cached results")
                _emit(cached, out_file, meta, args.k)
                return
        except: pass
    
    print("[codon] Computing codon-level Uplift vs tAI correlation...", flush=True)
    codon_corr = codon_level_correlation()
    print(f"  Spearman r={codon_corr['spearman']['r']:.3f}, p={codon_corr['spearman']['p']:.4f}", flush=True)
    
    # Window-level analysis
    fasta_files = sorted(data_dir().glob("human.*.rna.fna.gz"))
    if fasta_files:
        print(f"[window] Loading from {len(fasta_files)} FASTA files...", flush=True)
        window_data = load_window_data(fasta_files, args.k, args.n_per_stop, args.seed)
        print("[window] Computing Uplift vs tAI correlation...", flush=True)
        window_corr = window_level_analysis(window_data)
    else:
        print("[warning] No FASTA files found, skipping window analysis")
        window_corr = {}
    
    output = {
        "k": args.k,
        "n_per_stop": args.n_per_stop,
        "codon_level": codon_corr,
        "window_level": window_corr,
    }
    
    write_json_atomic(cache_file, output)
    _emit(output, out_file, meta, args.k)

def _emit(output: dict, out_file: Path, meta: dict, k: int):
    """Generate LaTeX output."""
    codon = output.get("codon_level", {})
    window = output.get("window_level", {})
    
    def f(x): return f"{x:.3f}" if x and not np.isnan(x) else "--"
    
    lines = [
        "\\paragraph{Uplift vs translation rate (tAI) correlation.}",
        f"At the codon level (n={codon.get('n_codons', 0)} sense codons), "
        f"Uplift $\\Delta$ and tRNA Adaptation Index (tAI) show "
        f"Spearman $\\rho={f(codon.get('spearman', {}).get('r'))}$ "
        f"($p={f(codon.get('spearman', {}).get('p'))}$).",
    ]
    
    pooled = window.get("pooled", {})
    if pooled:
        bb = pooled.get("before", {}).get("raw", {})
        bp = pooled.get("before", {}).get("partial_gc", {})
        ab = pooled.get("after", {}).get("raw", {})
        ap_ = pooled.get("after", {}).get("partial_gc", {})
        
        lines.append(
            f"At the window level ($k={k}$, n={pooled.get('n', 0)}): "
            f"before-window raw $\\rho={f(bb.get('r'))}$ ($p={f(bb.get('p'))}$), "
            f"partial (GC) $\\rho={f(bp.get('r'))}$ ($p={f(bp.get('p'))}$); "
            f"after-window raw $\\rho={f(ab.get('r'))}$ ($p={f(ab.get('p'))}$), "
            f"partial (GC) $\\rho={f(ap_.get('r'))}$ ($p={f(ap_.get('p'))}$)."
        )
        lines.append(
            f"Mean tAI: before={f(pooled.get('tai_before_mean'))}, after={f(pooled.get('tai_after_mean'))}."
        )
    
    # Table
    if window:
        lines.append("\\begin{center}\\small\\begin{tabular}{lccccc}\\toprule")
        lines.append("Stop & n & raw$_b$ & partial$_b$ & raw$_a$ & partial$_a$ \\\\\\midrule")
        for stop in ["UAA", "UAG", "UGA", "pooled"]:
            w = window.get(stop, {})
            bb = w.get("before", {}).get("raw", {})
            bp = w.get("before", {}).get("partial_gc", {})
            ab = w.get("after", {}).get("raw", {})
            ap_ = w.get("after", {}).get("partial_gc", {})
            lbl = stop if stop != "pooled" else "\\textbf{Pooled}"
            lines.append(f"{lbl} & {w.get('n', 0)} & {f(bb.get('r'))} & {f(bp.get('r'))} & {f(ab.get('r'))} & {f(ap_.get('r'))} \\\\")
        lines.append("\\bottomrule\\end{tabular}\\end{center}")
    
    write_text_atomic(out_file, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_file), meta)
    print(f"Wrote: {out_file}")

if __name__ == "__main__":
    main()
