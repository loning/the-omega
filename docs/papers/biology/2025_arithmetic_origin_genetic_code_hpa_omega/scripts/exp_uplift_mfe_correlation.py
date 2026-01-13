# -*- coding: utf-8 -*-
"""
Uplift vs RNA MFE (Minimum Free Energy) correlation analysis.

Uses ViennaRNA to compute actual MFE for stop-context windows and tests:
1. Does high Uplift correlate with high MFE (less stable structure)?
2. Does this correlation persist after controlling for GC content?

This addresses the critical question: Is "arithmetic friction" physically
manifested as thermodynamic instability?

Output:
  - sections/generated/uplift_mfe_correlation.tex
  - sections/generated/uplift_mfe_scatter.png
"""

from __future__ import annotations
import argparse, gzip, json, sys
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from scipy.stats import spearmanr, pearsonr

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from genetic_code_tools import GENETIC_CODE, find_orfs, fold_codon
from cache_manager import write_text_atomic, write_json_atomic, cache_meta_path

ANALYSIS_VERSION = 2
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

def gc_fraction(seq: str) -> float:
    seq = normalize_seq(seq)
    if not seq: return float("nan")
    return sum(1 for ch in seq if ch in "GC") / len(seq)

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

def compute_mfe(seq: str) -> float:
    """Compute MFE using ViennaRNA."""
    try:
        import RNA
        seq = normalize_seq(seq).replace("U", "T")  # ViennaRNA uses T
        seq = seq.replace("U", "T")
        # Compute MFE
        fc = RNA.fold_compound(seq)
        _, mfe = fc.mfe()
        return float(mfe)
    except Exception as e:
        return float("nan")

def compute_ensemble_energy(seq: str) -> tuple[float, float]:
    """Compute ensemble free energy and MFE using ViennaRNA."""
    try:
        import RNA
        seq = normalize_seq(seq).replace("U", "T")
        fc = RNA.fold_compound(seq)
        _, mfe = fc.mfe()
        ensemble = fc.pf()
        return float(mfe), float(ensemble[1])  # ensemble[1] is the free energy
    except Exception as e:
        return float("nan"), float("nan")

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

def load_and_compute(fasta_dir: Path, k: int, n_per_stop: int, seed: int) -> list[dict]:
    """Load windows and compute MFE for each."""
    rng = np.random.default_rng(seed)
    
    all_data = {stop: [] for stop in STOP_CODONS}
    n_scanned = 0
    
    fasta_files = sorted(fasta_dir.glob("human.*.rna.fna.gz"))
    
    for fasta_path in fasta_files:
        try:
            with gzip.open(fasta_path, "rt") as f:
                for rid, seq in _iter_fasta_handle(f):
                    n_scanned += 1
                    if n_scanned % 5000 == 0:
                        print(f"  scanned {n_scanned}", flush=True)
                    
                    orf = best_orf(seq)
                    if not orf:
                        continue
                    
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
                    
                    all_data[orf.stop_codon].append({
                        "before_seq": before_seq,
                        "after_seq": after_seq,
                    })
        except Exception as e:
            print(f"  [warning] {fasta_path}: {e}", flush=True)
    
    # Sample and compute MFE
    result = []
    for stop, data in all_data.items():
        if len(data) > n_per_stop:
            idx = rng.choice(len(data), size=n_per_stop, replace=False)
            sampled = [data[i] for i in idx]
        else:
            sampled = data
        
        print(f"  {stop}: computing MFE for {len(sampled)} windows...", flush=True)
        
        for i, w in enumerate(sampled):
            if i % 100 == 0:
                print(f"    {stop}: {i}/{len(sampled)}", flush=True)
            
            before_seq = w["before_seq"]
            after_seq = w["after_seq"]
            
            u_before = window_mean_uplift(before_seq)
            u_after = window_mean_uplift(after_seq)
            gc_before = gc_fraction(before_seq)
            gc_after = gc_fraction(after_seq)
            
            # Compute MFE
            mfe_before = compute_mfe(before_seq)
            mfe_after = compute_mfe(after_seq)
            
            if any(np.isnan(x) for x in [u_before, u_after, mfe_before, mfe_after]):
                continue
            
            result.append({
                "stop": stop,
                "u_before": u_before,
                "u_after": u_after,
                "gc_before": gc_before,
                "gc_after": gc_after,
                "mfe_before": mfe_before,
                "mfe_after": mfe_after,
            })
    
    return result

def partial_correlation(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> tuple[float, float]:
    """Compute partial Spearman correlation of x and y controlling for z."""
    from scipy.stats import spearmanr
    
    # Residualize x and y on z using rank regression
    mask = ~(np.isnan(x) | np.isnan(y) | np.isnan(z))
    if mask.sum() < 20:
        return float("nan"), float("nan")
    
    x, y, z = x[mask], y[mask], z[mask]
    
    # Use linear regression to get residuals
    from numpy.linalg import lstsq
    Z = z.reshape(-1, 1)
    cx, _, _, _ = lstsq(Z, x, rcond=None)
    cy, _, _, _ = lstsq(Z, y, rcond=None)
    
    x_resid = x - Z @ cx
    y_resid = y - Z @ cy
    
    r, p = spearmanr(x_resid, y_resid)
    return float(r), float(p)

def analyze(data: list[dict]) -> dict:
    """Analyze Uplift-MFE correlations."""
    
    # Extract arrays
    u_before = np.array([d["u_before"] for d in data])
    u_after = np.array([d["u_after"] for d in data])
    gc_before = np.array([d["gc_before"] for d in data])
    gc_after = np.array([d["gc_after"] for d in data])
    mfe_before = np.array([d["mfe_before"] for d in data])
    mfe_after = np.array([d["mfe_after"] for d in data])
    
    results = {"n": len(data)}
    
    # Raw correlations
    r_b, p_b = spearmanr(u_before, mfe_before)
    r_a, p_a = spearmanr(u_after, mfe_after)
    results["before_raw"] = {"r": float(r_b), "p": float(p_b)}
    results["after_raw"] = {"r": float(r_a), "p": float(p_a)}
    
    # Partial correlations (control for GC)
    rp_b, pp_b = partial_correlation(u_before, mfe_before, gc_before)
    rp_a, pp_a = partial_correlation(u_after, mfe_after, gc_after)
    results["before_partial_gc"] = {"r": rp_b, "p": pp_b}
    results["after_partial_gc"] = {"r": rp_a, "p": pp_a}
    
    # MFE statistics
    results["mfe_before_mean"] = float(np.mean(mfe_before))
    results["mfe_before_std"] = float(np.std(mfe_before))
    results["mfe_after_mean"] = float(np.mean(mfe_after))
    results["mfe_after_std"] = float(np.std(mfe_after))
    
    # GC-MFE correlation (sanity check: should be strongly negative)
    r_gc_mfe, p_gc_mfe = spearmanr(gc_after, mfe_after)
    results["gc_mfe_correlation"] = {"r": float(r_gc_mfe), "p": float(p_gc_mfe)}
    
    # Per-stop analysis
    results["by_stop"] = {}
    for stop in STOP_CODONS:
        stop_data = [d for d in data if d["stop"] == stop]
        if len(stop_data) < 20:
            continue
        
        u_a = np.array([d["u_after"] for d in stop_data])
        mfe_a = np.array([d["mfe_after"] for d in stop_data])
        gc_a = np.array([d["gc_after"] for d in stop_data])
        
        r_raw, p_raw = spearmanr(u_a, mfe_a)
        r_part, p_part = partial_correlation(u_a, mfe_a, gc_a)
        
        results["by_stop"][stop] = {
            "n": len(stop_data),
            "raw": {"r": float(r_raw), "p": float(p_raw)},
            "partial_gc": {"r": r_part, "p": p_part},
            "mfe_mean": float(np.mean(mfe_a)),
            "mfe_std": float(np.std(mfe_a)),
        }
    
    return results

def make_scatter_plot(data: list[dict], out_path: Path):
    """Create scatter plot of Uplift vs MFE."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        colors = {"UAA": "#1f77b4", "UAG": "#ff7f0e", "UGA": "#2ca02c"}
        
        for stop in STOP_CODONS:
            stop_data = [d for d in data if d["stop"] == stop]
            u = [d["u_after"] for d in stop_data]
            mfe = [d["mfe_after"] for d in stop_data]
            axes[0].scatter(u, mfe, c=colors[stop], label=stop, alpha=0.5, s=10)
        
        axes[0].set_xlabel("Mean Uplift $\\bar{U}_{after}$")
        axes[0].set_ylabel("MFE (kcal/mol)")
        axes[0].set_title("Uplift vs MFE (after-window)")
        axes[0].legend()
        
        # GC vs MFE (sanity check)
        for stop in STOP_CODONS:
            stop_data = [d for d in data if d["stop"] == stop]
            gc = [d["gc_after"] for d in stop_data]
            mfe = [d["mfe_after"] for d in stop_data]
            axes[1].scatter(gc, mfe, c=colors[stop], label=stop, alpha=0.5, s=10)
        
        axes[1].set_xlabel("GC content")
        axes[1].set_ylabel("MFE (kcal/mol)")
        axes[1].set_title("GC vs MFE (after-window)")
        axes[1].legend()
        
        plt.tight_layout()
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Wrote: {out_path}")
    except Exception as e:
        print(f"  [warning] Could not create plot: {e}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--n-per-stop", type=int, default=500, help="Samples per stop codon")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    
    out_tex = generated_dir() / "uplift_mfe_correlation.tex"
    out_png = generated_dir() / "uplift_mfe_scatter.png"
    cache_file = cache_dir() / f"uplift_mfe_v{ANALYSIS_VERSION}.json"
    meta = {"v": ANALYSIS_VERSION, "k": args.k, "n": args.n_per_stop}
    
    # Check cache
    if not args.force and cache_file.exists():
        try:
            with open(cache_file) as f:
                cached = json.load(f)
            if cached.get("k") == args.k and cached.get("n") >= args.n_per_stop:
                print("[cache] Using cached results")
                _emit(cached["results"], out_tex, meta, args.k)
                return
        except: pass
    
    # Load and compute
    print(f"[load] Loading windows and computing MFE (k={args.k}, n={args.n_per_stop})...", flush=True)
    data = load_and_compute(data_dir(), args.k, args.n_per_stop, args.seed)
    
    print(f"[analyze] Analyzing {len(data)} samples...", flush=True)
    results = analyze(data)
    
    # Save cache
    write_json_atomic(cache_file, {"k": args.k, "n": args.n_per_stop, "results": results, "data": data})
    
    # Output
    _emit(results, out_tex, meta, args.k)
    make_scatter_plot(data, out_png)

def _emit(results: dict, out_tex: Path, meta: dict, k: int):
    """Generate LaTeX output."""
    def f(x): return f"{x:.3f}" if x is not None and not np.isnan(x) else "--"
    def p_fmt(p):
        if p is None or np.isnan(p): return "--"
        if p < 0.001: return "$<$0.001"
        return f"{p:.3f}"
    
    n = results.get("n", 0)
    
    lines = [
        f"\\paragraph{{Uplift vs RNA MFE correlation ($k={k}$, n={n}).}}",
        "Using ViennaRNA to compute actual minimum free energy (MFE) for stop-context windows:",
    ]
    
    # Raw correlations
    br = results.get("before_raw", {})
    ar = results.get("after_raw", {})
    lines.append(
        f"Before-window: raw $\\rho={f(br.get('r'))}$ ($p={p_fmt(br.get('p'))}$); "
        f"After-window: raw $\\rho={f(ar.get('r'))}$ ($p={p_fmt(ar.get('p'))}$)."
    )
    
    # Partial correlations
    bp = results.get("before_partial_gc", {})
    ap = results.get("after_partial_gc", {})
    lines.append(
        f"Partial (GC-controlled): before $\\rho={f(bp.get('r'))}$ ($p={p_fmt(bp.get('p'))}$); "
        f"after $\\rho={f(ap.get('r'))}$ ($p={p_fmt(ap.get('p'))}$)."
    )
    
    # GC-MFE sanity check
    gc_mfe = results.get("gc_mfe_correlation", {})
    lines.append(
        f"Sanity check: GC--MFE correlation $\\rho={f(gc_mfe.get('r'))}$ "
        f"($p={p_fmt(gc_mfe.get('p'))}$; expected strong negative)."
    )
    
    # Interpretation
    ar_r = ar.get('r', 0)
    ap_r = ap.get('r', 0)
    if ar_r is not None and not np.isnan(ar_r):
        if ar_r > 0.1:
            lines.append(
                "\\textbf{Finding:} High Uplift correlates with \\emph{higher} MFE (less stable structure), "
                "consistent with ``arithmetic friction'' manifesting as thermodynamic instability."
            )
        elif ar_r < -0.1:
            lines.append(
                "\\textbf{Finding:} High Uplift correlates with \\emph{lower} MFE (more stable structure), "
                "\\emph{contrary} to the ``arithmetic friction'' hypothesis."
            )
        else:
            lines.append(
                "\\textbf{Finding:} No strong Uplift--MFE correlation."
            )
    
    if ap_r is not None and not np.isnan(ap_r) and abs(ap_r) < 0.05:
        lines.append(
            "After controlling for GC, the correlation vanishes, indicating that Uplift's "
            "relationship with structure is mediated by composition."
        )
    
    # Per-stop table
    by_stop = results.get("by_stop", {})
    if by_stop:
        lines.append("\\begin{center}\\small\\begin{tabular}{lcccc}\\toprule")
        lines.append("Stop & n & raw $\\rho$ & partial $\\rho$ & mean MFE \\\\\\midrule")
        for stop in ["UAA", "UAG", "UGA"]:
            s = by_stop.get(stop, {})
            raw = s.get("raw", {})
            part = s.get("partial_gc", {})
            lines.append(
                f"{stop} & {s.get('n', 0)} & {f(raw.get('r'))} & {f(part.get('r'))} & {f(s.get('mfe_mean'))} \\\\"
            )
        lines.append("\\bottomrule\\end{tabular}\\end{center}")
    
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    print(f"Wrote: {out_tex}")

if __name__ == "__main__":
    main()
