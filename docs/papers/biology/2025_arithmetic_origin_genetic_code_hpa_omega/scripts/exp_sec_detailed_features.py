# -*- coding: utf-8 -*-
"""
Detailed feature analysis for selenocysteine (Sec) insertion sites.

Analyzes:
1. Position-decomposed Uplift curves around Sec sites
2. +4 base composition comparison
3. GC content stratification
4. Distance to gene end
5. Comparison with terminal UGA stops

Output:
  - sections/generated/sec_detailed_features.tex
  - sections/generated/sec_position_curve.png
"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.stats import mannwhitneyu, spearmanr

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from genetic_code_tools import GENETIC_CODE, fold_codon
from cache_manager import write_text_atomic, write_json_atomic, cache_meta_path

MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
STOP_CODONS = {"UAA", "UAG", "UGA"}

def root_dir(): return SCRIPT_DIR.parent
def generated_dir(): return root_dir() / "sections" / "generated"
def data_dir(): return root_dir() / "data"

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

def seq_to_codon_uplifts(seq: str) -> list[float]:
    """Convert sequence to list of per-codon uplift values."""
    seq = normalize_seq(seq)
    codons = [seq[i:i+3] for i in range(0, len(seq)-2, 3)]
    return [codon_uplift(c) for c in codons]

def load_sec_data():
    """Load Sec sites from recoding data."""
    jsonl_path = data_dir() / "recoding_genbank" / "recoding_sites.jsonl"
    sec_sites = []
    uga_terminals = []
    
    seen_cds = set()
    
    with open(jsonl_path) as f:
        for line in f:
            rec = json.loads(line.strip())
            aa = rec.get("aa", "")
            
            if "Sec" in aa:
                k = rec.get("k", 10)
                
                # Sec site
                before_seq = (rec.get("before_seq_dna") or "").upper().replace("T", "U")
                after_seq = (rec.get("after_seq_dna") or "").upper().replace("T", "U")
                
                if before_seq and after_seq and len(before_seq) >= 3*k and len(after_seq) >= 3*k:
                    sec_sites.append({
                        "type": "sec",
                        "gene": rec.get("gene", "Unknown"),
                        "organism": rec.get("organism", "Unknown"),
                        "before_seq": before_seq,
                        "after_seq": after_seq,
                        "plus4": rec.get("plus4_nt", "N"),
                        "before_gc": rec.get("before_gc", 0),
                        "after_gc": rec.get("after_gc", 0),
                        "before_mean_delta": rec.get("before_mean_delta"),
                        "after_mean_delta": rec.get("after_mean_delta"),
                        "k": k,
                    })
                
                # Corresponding terminal UGA (one per CDS)
                cds_id = f"{rec.get('gene', '')}_{rec.get('organism', '')}"
                if cds_id not in seen_cds and rec.get("terminal_stop") == "UGA":
                    term_before = (rec.get("terminal_before_seq_dna") or "").upper().replace("T", "U")
                    term_after = (rec.get("terminal_after_seq_dna") or "").upper().replace("T", "U")
                    
                    if term_before and term_after:
                        uga_terminals.append({
                            "type": "terminal_uga",
                            "gene": rec.get("gene", "Unknown"),
                            "organism": rec.get("organism", "Unknown"),
                            "before_seq": term_before,
                            "after_seq": term_after,
                            "plus4": term_after[0] if term_after else "N",
                            "before_gc": rec.get("terminal_before_gc", 0),
                            "after_gc": rec.get("terminal_after_gc", 0),
                            "before_mean_delta": rec.get("terminal_before_mean_delta"),
                            "after_mean_delta": rec.get("terminal_after_mean_delta"),
                            "k": k,
                        })
                        seen_cds.add(cds_id)
    
    return sec_sites, uga_terminals

def compute_position_curves(sites: list[dict], max_j: int = 20) -> dict:
    """Compute position-decomposed Uplift curves."""
    before_curves = {j: [] for j in range(1, max_j + 1)}
    after_curves = {j: [] for j in range(1, max_j + 1)}
    
    for site in sites:
        before_seq = site.get("before_seq", "")
        after_seq = site.get("after_seq", "")
        
        before_uplifts = seq_to_codon_uplifts(before_seq)
        after_uplifts = seq_to_codon_uplifts(after_seq)
        
        # Before: position -j (j=1 is immediately before stop)
        for j in range(1, min(max_j + 1, len(before_uplifts) + 1)):
            idx = len(before_uplifts) - j
            if idx >= 0 and not np.isnan(before_uplifts[idx]):
                before_curves[j].append(before_uplifts[idx])
        
        # After: position +j (j=1 is immediately after stop)
        for j in range(1, min(max_j + 1, len(after_uplifts) + 1)):
            if j - 1 < len(after_uplifts) and not np.isnan(after_uplifts[j - 1]):
                after_curves[j].append(after_uplifts[j - 1])
    
    # Compute means and CIs
    results = {"before": {}, "after": {}}
    
    for j in range(1, max_j + 1):
        if before_curves[j]:
            vals = np.array(before_curves[j])
            results["before"][j] = {
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
                "n": len(vals),
            }
        if after_curves[j]:
            vals = np.array(after_curves[j])
            results["after"][j] = {
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
                "n": len(vals),
            }
    
    return results

def compare_features(sec_sites: list, uga_terminals: list) -> dict:
    """Compare Sec sites with terminal UGA stops."""
    results = {}
    
    # +4 base composition
    sec_plus4 = Counter(s.get("plus4", "N") for s in sec_sites)
    uga_plus4 = Counter(s.get("plus4", "N") for s in uga_terminals)
    results["plus4"] = {
        "sec": dict(sec_plus4),
        "terminal_uga": dict(uga_plus4),
    }
    
    # GC content
    sec_gc_before = [s.get("before_gc", 0) for s in sec_sites if s.get("before_gc")]
    sec_gc_after = [s.get("after_gc", 0) for s in sec_sites if s.get("after_gc")]
    uga_gc_before = [s.get("before_gc", 0) for s in uga_terminals if s.get("before_gc")]
    uga_gc_after = [s.get("after_gc", 0) for s in uga_terminals if s.get("after_gc")]
    
    results["gc"] = {
        "sec_before": float(np.mean(sec_gc_before)) if sec_gc_before else float("nan"),
        "sec_after": float(np.mean(sec_gc_after)) if sec_gc_after else float("nan"),
        "uga_before": float(np.mean(uga_gc_before)) if uga_gc_before else float("nan"),
        "uga_after": float(np.mean(uga_gc_after)) if uga_gc_after else float("nan"),
    }
    
    # Uplift comparison
    def safe_float(x):
        if x is None: return float("nan")
        try: return float(x)
        except: return float("nan")
    
    sec_before_u = [safe_float(s.get("before_mean_delta")) for s in sec_sites]
    sec_after_u = [safe_float(s.get("after_mean_delta")) for s in sec_sites]
    uga_before_u = [safe_float(s.get("before_mean_delta")) for s in uga_terminals]
    uga_after_u = [safe_float(s.get("after_mean_delta")) for s in uga_terminals]
    
    sec_before_u = [x for x in sec_before_u if not np.isnan(x)]
    sec_after_u = [x for x in sec_after_u if not np.isnan(x)]
    uga_before_u = [x for x in uga_before_u if not np.isnan(x)]
    uga_after_u = [x for x in uga_after_u if not np.isnan(x)]
    
    # Mann-Whitney tests
    if sec_before_u and uga_before_u:
        u, p = mannwhitneyu(sec_before_u, uga_before_u, alternative="two-sided")
        results["before_test"] = {
            "sec_mean": float(np.mean(sec_before_u)),
            "uga_mean": float(np.mean(uga_before_u)),
            "diff": float(np.mean(sec_before_u) - np.mean(uga_before_u)),
            "u_stat": float(u),
            "p": float(p),
        }
    
    if sec_after_u and uga_after_u:
        u, p = mannwhitneyu(sec_after_u, uga_after_u, alternative="two-sided")
        results["after_test"] = {
            "sec_mean": float(np.mean(sec_after_u)),
            "uga_mean": float(np.mean(uga_after_u)),
            "diff": float(np.mean(sec_after_u) - np.mean(uga_after_u)),
            "u_stat": float(u),
            "p": float(p),
        }
    
    return results

def make_position_plot(sec_curves: dict, uga_curves: dict, out_path: Path):
    """Create position-decomposed curves plot."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        max_j = 15
        
        # Before curves
        ax = axes[0]
        js = list(range(1, max_j + 1))
        
        sec_before = [sec_curves["before"].get(j, {}).get("mean", np.nan) for j in js]
        uga_before = [uga_curves["before"].get(j, {}).get("mean", np.nan) for j in js]
        
        ax.plot([-j for j in js], sec_before, 'o-', label="Sec sites", color="#e41a1c", markersize=4)
        ax.plot([-j for j in js], uga_before, 's-', label="Terminal UGA", color="#377eb8", markersize=4)
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=0, color='gray', linestyle='-', alpha=0.3)
        ax.set_xlabel("Position relative to UGA (codons)")
        ax.set_ylabel("Mean Uplift $\\Delta$")
        ax.set_title("Before-window: Sec vs Terminal UGA")
        ax.legend()
        ax.set_xlim(-max_j - 1, 0)
        
        # After curves
        ax = axes[1]
        sec_after = [sec_curves["after"].get(j, {}).get("mean", np.nan) for j in js]
        uga_after = [uga_curves["after"].get(j, {}).get("mean", np.nan) for j in js]
        
        ax.plot(js, sec_after, 'o-', label="Sec sites", color="#e41a1c", markersize=4)
        ax.plot(js, uga_after, 's-', label="Terminal UGA", color="#377eb8", markersize=4)
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=0, color='gray', linestyle='-', alpha=0.3)
        ax.set_xlabel("Position relative to UGA (codons)")
        ax.set_ylabel("Mean Uplift $\\Delta$")
        ax.set_title("After-window: Sec vs Terminal UGA")
        ax.legend()
        ax.set_xlim(0, max_j + 1)
        
        plt.tight_layout()
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Wrote: {out_path}")
    except Exception as e:
        print(f"  [warning] Could not create plot: {e}")

def main():
    ap = argparse.ArgumentParser()
    args = ap.parse_args()
    
    out_tex = generated_dir() / "sec_detailed_features.tex"
    out_png = generated_dir() / "sec_position_curve.png"
    meta = {"analysis": "sec_detailed"}
    
    print("[load] Loading Sec sites and terminal UGA...", flush=True)
    sec_sites, uga_terminals = load_sec_data()
    print(f"  Sec sites: {len(sec_sites)}", flush=True)
    print(f"  Terminal UGA: {len(uga_terminals)}", flush=True)
    
    print("[analyze] Computing position curves...", flush=True)
    sec_curves = compute_position_curves(sec_sites)
    uga_curves = compute_position_curves(uga_terminals)
    
    print("[analyze] Comparing features...", flush=True)
    comparison = compare_features(sec_sites, uga_terminals)
    
    # Plot
    make_position_plot(sec_curves, uga_curves, out_png)
    
    # Output
    _emit(sec_sites, uga_terminals, sec_curves, uga_curves, comparison, out_tex, meta)

def _emit(sec_sites, uga_terminals, sec_curves, uga_curves, comparison, out_tex, meta):
    """Generate LaTeX output."""
    def f(x): return f"{x:.2f}" if x is not None and not np.isnan(x) else "--"
    def p_fmt(p):
        if p is None or np.isnan(p): return "--"
        if p < 0.001: return "$<$0.001"
        return f"{p:.3f}"
    
    lines = [
        f"\\paragraph{{Sec insertion site detailed analysis (n={len(sec_sites)} Sec, n={len(uga_terminals)} terminal UGA).}}",
    ]
    
    # +4 base composition
    plus4 = comparison.get("plus4", {})
    sec_p4 = plus4.get("sec", {})
    uga_p4 = plus4.get("terminal_uga", {})
    lines.append(
        f"+4 base: Sec sites {sec_p4}, terminal UGA {uga_p4}."
    )
    
    # GC comparison
    gc = comparison.get("gc", {})
    lines.append(
        f"Mean GC: Sec before={f(gc.get('sec_before'))}, after={f(gc.get('sec_after'))}; "
        f"UGA before={f(gc.get('uga_before'))}, after={f(gc.get('uga_after'))}."
    )
    
    # Uplift comparison
    bt = comparison.get("before_test", {})
    at = comparison.get("after_test", {})
    
    if bt:
        lines.append(
            f"Before-window $\\overline{{U}}$: Sec={f(bt.get('sec_mean'))}, UGA={f(bt.get('uga_mean'))}, "
            f"diff={f(bt.get('diff'))}, $p$={p_fmt(bt.get('p'))}."
        )
    
    if at:
        lines.append(
            f"After-window $\\overline{{U}}$: Sec={f(at.get('sec_mean'))}, UGA={f(at.get('uga_mean'))}, "
            f"diff={f(at.get('diff'))}, $p$={p_fmt(at.get('p'))}."
        )
    
    # Position curves (show key positions)
    lines.append("Position-specific Uplift (see Figure):")
    for j in [1, 3, 5, 10]:
        sb = sec_curves.get("before", {}).get(j, {})
        ub = uga_curves.get("before", {}).get(j, {})
        if sb and ub:
            diff = sb.get("mean", 0) - ub.get("mean", 0)
            lines.append(f"  $j=-{j}$: Sec={f(sb.get('mean'))}, UGA={f(ub.get('mean'))}, diff={f(diff)};")
    
    # Figure reference
    lines.append("\\begin{center}")
    lines.append("\\includegraphics[width=0.95\\textwidth]{sections/generated/sec_position_curve.png}")
    lines.append("\\end{center}")
    
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    print(f"Wrote: {out_tex}")

if __name__ == "__main__":
    main()
