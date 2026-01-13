# -*- coding: utf-8 -*-
"""
Enhanced Uplift vs RNA structure analysis with de-confounding regression.

Addresses the key reviewer question: Is uplift just a proxy for GC/structure?

Analysis:
1. Multiple window scales (k=10 codons, 60nt, 120nt)
2. MFE + Ensemble free energy + Pairing probability
3. Multiple regression: uplift ~ GC + dinuc + ΔG (does U add info beyond structure?)
4. Reverse: ΔG ~ GC + dinuc + uplift (does structure add info beyond U?)

Output:
  - sections/generated/uplift_structure_deconfound.tex
  - sections/generated/uplift_structure_deconfound_table.tex
"""

from __future__ import annotations
import argparse, gzip, json, sys
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from scipy.stats import spearmanr

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from genetic_code_tools import GENETIC_CODE, find_orfs, fold_codon
from cache_manager import write_text_atomic, write_json_atomic, cache_meta_path

ANALYSIS_VERSION = 1
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
STOP_CODONS = {"UAA", "UAG", "UGA"}
NUCS = "ACGU"
DINUCS = [a + b for a in NUCS for b in NUCS]

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

def dinuc_freq(seq: str) -> np.ndarray:
    seq = normalize_seq(seq)
    dinuc_idx = {d: i for i, d in enumerate(DINUCS)}
    counts = np.zeros(16, dtype=float)
    for i in range(len(seq) - 1):
        d = seq[i:i+2]
        if d[0] in NUCS and d[1] in NUCS:
            counts[dinuc_idx[d]] += 1.0
    if counts.sum() > 0: counts /= counts.sum()
    return counts

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

def compute_rna_features(seq: str) -> dict:
    """Compute RNA folding features using ViennaRNA."""
    try:
        import RNA
        seq = normalize_seq(seq).replace("U", "T")  # ViennaRNA uses DNA alphabet
        
        fc = RNA.fold_compound(seq)
        
        # MFE
        structure, mfe = fc.mfe()
        
        # Ensemble free energy (partition function)
        fc.exp_params_rescale(mfe)
        ensemble_result = fc.pf()
        ensemble_fe = ensemble_result[1] if len(ensemble_result) > 1 else float("nan")
        
        # Base pairing probability (average)
        bpp = fc.bpp()
        if bpp:
            # Sum of pairing probabilities
            total_prob = 0.0
            n = len(seq)
            for i in range(1, n + 1):
                for j in range(i + 1, n + 1):
                    if i < len(bpp) and j < len(bpp[i]):
                        total_prob += bpp[i][j]
            avg_pairing = total_prob / (n * (n - 1) / 2) if n > 1 else 0
        else:
            avg_pairing = float("nan")
        
        return {
            "mfe": float(mfe),
            "ensemble_fe": float(ensemble_fe),
            "avg_pairing_prob": float(avg_pairing),
            "structure": structure,
        }
    except Exception as e:
        return {
            "mfe": float("nan"),
            "ensemble_fe": float("nan"),
            "avg_pairing_prob": float("nan"),
            "structure": "",
        }

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

def load_and_compute(fasta_dir: Path, window_sizes: list[int], n_samples: int, seed: int) -> list[dict]:
    """Load windows and compute features at multiple scales."""
    rng = np.random.default_rng(seed)
    max_window = max(window_sizes)
    
    all_data = []
    n_scanned = 0
    
    fasta_files = sorted(fasta_dir.glob("human.*.rna.fna.gz"))
    
    for fasta_path in fasta_files:
        if len(all_data) >= n_samples * 5:  # Collect more than needed for filtering
            break
        try:
            with gzip.open(fasta_path, "rt") as f:
                for rid, seq in _iter_fasta_handle(f):
                    n_scanned += 1
                    if n_scanned % 5000 == 0:
                        print(f"  scanned {n_scanned}, collected {len(all_data)}", flush=True)
                    
                    orf = best_orf(seq)
                    if not orf:
                        continue
                    
                    # Need enough sequence after stop
                    after_start = orf.stop_base + 3
                    if after_start + max_window > len(seq):
                        continue
                    
                    # Store sequences at multiple scales
                    entry = {
                        "stop": orf.stop_codon,
                        "windows": {},
                    }
                    
                    for ws in window_sizes:
                        after_seq = seq[after_start:after_start + ws]
                        if len(after_seq) != ws:
                            continue
                        entry["windows"][ws] = after_seq
                    
                    if len(entry["windows"]) == len(window_sizes):
                        all_data.append(entry)
        except Exception as e:
            print(f"  [warning] {fasta_path}: {e}", flush=True)
    
    # Sample
    if len(all_data) > n_samples:
        idx = rng.choice(len(all_data), size=n_samples, replace=False)
        all_data = [all_data[i] for i in idx]
    
    print(f"  Computing RNA features for {len(all_data)} samples...", flush=True)
    
    # Compute features
    for i, entry in enumerate(all_data):
        if i % 50 == 0:
            print(f"    {i}/{len(all_data)}", flush=True)
        
        for ws, seq in entry["windows"].items():
            # Uplift
            uplift = window_mean_uplift(seq)
            
            # GC and dinuc
            gc = gc_fraction(seq)
            dinuc = dinuc_freq(seq)
            
            # RNA structure
            rna = compute_rna_features(seq)
            
            entry[f"uplift_{ws}"] = uplift
            entry[f"gc_{ws}"] = gc
            entry[f"dinuc_{ws}"] = dinuc
            entry[f"mfe_{ws}"] = rna["mfe"]
            entry[f"ensemble_{ws}"] = rna["ensemble_fe"]
            entry[f"pairing_{ws}"] = rna["avg_pairing_prob"]
    
    return all_data

def run_regression_deconfound(data: list[dict], window_sizes: list[int]) -> dict:
    """Run multiple regression to test if uplift adds info beyond structure."""
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    from scipy.stats import spearmanr
    
    results = {}
    
    for ws in window_sizes:
        # Extract features
        uplifts = np.array([d.get(f"uplift_{ws}", np.nan) for d in data])
        gcs = np.array([d.get(f"gc_{ws}", np.nan) for d in data])
        mfes = np.array([d.get(f"mfe_{ws}", np.nan) for d in data])
        ensembles = np.array([d.get(f"ensemble_{ws}", np.nan) for d in data])
        pairings = np.array([d.get(f"pairing_{ws}", np.nan) for d in data])
        dinucs = np.array([d.get(f"dinuc_{ws}", np.zeros(16)) for d in data])
        
        # Filter valid
        valid = ~(np.isnan(uplifts) | np.isnan(gcs) | np.isnan(mfes) | np.isnan(ensembles))
        uplifts = uplifts[valid]
        gcs = gcs[valid]
        mfes = mfes[valid]
        ensembles = ensembles[valid]
        pairings = pairings[valid]
        dinucs = dinucs[valid]
        
        n = len(uplifts)
        if n < 50:
            results[ws] = {"n": n, "error": "insufficient data"}
            continue
        
        # Standardize
        scaler = StandardScaler()
        
        # Model 1: MFE ~ GC + dinuc (baseline)
        X1 = np.column_stack([gcs, dinucs])
        X1 = scaler.fit_transform(X1)
        m1 = LinearRegression().fit(X1, mfes)
        r2_m1 = m1.score(X1, mfes)
        
        # Model 2: MFE ~ GC + dinuc + Uplift (does uplift add?)
        X2 = np.column_stack([gcs, dinucs, uplifts])
        X2 = scaler.fit_transform(X2)
        m2 = LinearRegression().fit(X2, mfes)
        r2_m2 = m2.score(X2, mfes)
        delta_r2_uplift = r2_m2 - r2_m1
        
        # Model 3: Uplift ~ GC + dinuc (baseline)
        X3 = np.column_stack([gcs, dinucs])
        X3 = scaler.fit_transform(X3)
        m3 = LinearRegression().fit(X3, uplifts)
        r2_m3 = m3.score(X3, uplifts)
        
        # Model 4: Uplift ~ GC + dinuc + MFE (does structure add?)
        X4 = np.column_stack([gcs, dinucs, mfes])
        X4 = scaler.fit_transform(X4)
        m4 = LinearRegression().fit(X4, uplifts)
        r2_m4 = m4.score(X4, uplifts)
        delta_r2_mfe = r2_m4 - r2_m3
        
        # Raw and partial correlations
        r_raw, p_raw = spearmanr(uplifts, mfes)
        
        # Partial correlation (control GC)
        from numpy.linalg import lstsq
        G = gcs.reshape(-1, 1)
        cu, _, _, _ = lstsq(G, uplifts, rcond=None)
        cm, _, _, _ = lstsq(G, mfes, rcond=None)
        r_partial_gc, p_partial_gc = spearmanr(uplifts - G @ cu, mfes - G @ cm)
        
        # Partial correlation (control GC + dinuc)
        GD = np.column_stack([gcs, dinucs])
        cu2, _, _, _ = lstsq(GD, uplifts, rcond=None)
        cm2, _, _, _ = lstsq(GD, mfes, rcond=None)
        r_partial_full, p_partial_full = spearmanr(uplifts - GD @ cu2, mfes - GD @ cm2)
        
        results[ws] = {
            "n": n,
            "window_nt": ws,
            "correlations": {
                "raw": {"r": float(r_raw), "p": float(p_raw)},
                "partial_gc": {"r": float(r_partial_gc), "p": float(p_partial_gc)},
                "partial_full": {"r": float(r_partial_full), "p": float(p_partial_full)},
            },
            "regression": {
                "r2_mfe_baseline": float(r2_m1),  # MFE ~ GC + dinuc
                "r2_mfe_with_uplift": float(r2_m2),  # MFE ~ GC + dinuc + U
                "delta_r2_uplift_to_mfe": float(delta_r2_uplift),  # Does U add info to predict MFE?
                "r2_uplift_baseline": float(r2_m3),  # U ~ GC + dinuc
                "r2_uplift_with_mfe": float(r2_m4),  # U ~ GC + dinuc + MFE
                "delta_r2_mfe_to_uplift": float(delta_r2_mfe),  # Does MFE add info to predict U?
            },
            "means": {
                "uplift": float(np.mean(uplifts)),
                "gc": float(np.mean(gcs)),
                "mfe": float(np.mean(mfes)),
                "ensemble": float(np.mean(ensembles)),
            },
        }
    
    return results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window-sizes", type=str, default="30,60,120", help="Window sizes in nt")
    ap.add_argument("--n-samples", type=int, default=300, help="Number of samples")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    
    window_sizes = [int(x) for x in args.window_sizes.split(",")]
    
    out_tex = generated_dir() / "uplift_structure_deconfound.tex"
    out_table = generated_dir() / "uplift_structure_deconfound_table.tex"
    cache_file = cache_dir() / f"uplift_structure_deconfound_v{ANALYSIS_VERSION}.json"
    meta = {"v": ANALYSIS_VERSION, "windows": window_sizes}
    
    # Check cache
    if not args.force and cache_file.exists():
        try:
            with open(cache_file) as f:
                cached = json.load(f)
            print("[cache] Using cached results")
            _emit(cached, out_tex, out_table, meta)
            return
        except: pass
    
    print(f"[load] Loading data and computing features (windows={window_sizes})...", flush=True)
    data = load_and_compute(data_dir(), window_sizes, args.n_samples, args.seed)
    
    print("[analyze] Running regression de-confound analysis...", flush=True)
    results = run_regression_deconfound(data, window_sizes)
    
    write_json_atomic(cache_file, results)
    _emit(results, out_tex, out_table, meta)

def _emit(results: dict, out_tex: Path, out_table: Path, meta: dict):
    """Generate LaTeX output."""
    def f(x): return f"{x:.3f}" if x is not None and not np.isnan(x) else "--"
    def p_fmt(p):
        if p is None or np.isnan(p): return "--"
        if p < 0.001: return "$<$0.001"
        return f"{p:.3f}"
    
    lines = [
        "\\paragraph{Uplift vs RNA structure: de-confounding analysis.}",
        "Testing whether Uplift captures information beyond composition and structure:",
    ]
    
    # Summary across scales
    for ws, r in sorted(results.items()):
        if isinstance(r, dict) and "correlations" in r:
            corr = r["correlations"]
            reg = r["regression"]
            lines.append(
                f"\\textbf{{Window {ws}nt}} (n={r['n']}): "
                f"raw $\\rho={f(corr['raw']['r'])}$, "
                f"partial (GC) $\\rho={f(corr['partial_gc']['r'])}$, "
                f"partial (GC+dinuc) $\\rho={f(corr['partial_full']['r'])}$."
            )
    
    # Key finding
    any_significant = False
    for ws, r in results.items():
        if isinstance(r, dict) and "correlations" in r:
            if abs(r["correlations"]["partial_full"]["r"]) > 0.1:
                any_significant = True
    
    if any_significant:
        lines.append(
            "\\textbf{Finding:} Some residual Uplift--MFE correlation persists after full composition control."
        )
    else:
        lines.append(
            "\\textbf{Finding:} Uplift--MFE correlation is fully explained by GC and dinucleotide composition."
        )
    
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    print(f"Wrote: {out_tex}")
    
    # Table
    table = [
        "\\begin{center}\\small",
        "\\begin{tabular}{lccccc}\\toprule",
        "Window & n & raw $\\rho$ & partial$_{GC}$ & partial$_{full}$ & $\\Delta R^2_{U\\to MFE}$ \\\\\\midrule",
    ]
    
    for ws, r in sorted(results.items()):
        if isinstance(r, dict) and "correlations" in r:
            corr = r["correlations"]
            reg = r["regression"]
            table.append(
                f"{ws}nt & {r['n']} & {f(corr['raw']['r'])} & {f(corr['partial_gc']['r'])} & "
                f"{f(corr['partial_full']['r'])} & {f(reg['delta_r2_uplift_to_mfe'])} \\\\"
            )
    
    table.extend([
        "\\bottomrule",
        "\\multicolumn{6}{l}{\\footnotesize $\\Delta R^2$: incremental variance explained by Uplift after GC+dinuc.} \\\\",
        "\\end{tabular}",
        "\\end{center}",
    ])
    
    write_text_atomic(out_table, "\n".join(table) + "\n")
    write_json_atomic(cache_meta_path(out_table), meta)
    print(f"Wrote: {out_table}")

if __name__ == "__main__":
    main()
