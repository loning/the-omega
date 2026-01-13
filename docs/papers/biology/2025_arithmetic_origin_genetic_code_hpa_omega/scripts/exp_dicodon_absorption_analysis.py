#!/usr/bin/env python3
"""
exp_dicodon_absorption_analysis.py - M2: Quantify dicodon absorption of Uplift signal

This script addresses the key negative finding from CR3B: "Uplift signal absorbed by 
ORF-level dicodon structure". We quantify exactly how much of the stop-context Uplift 
signal can be explained by dicodon (codon-pair) frequencies.

Approach:
1. For each ORF, compute dicodon frequency profile
2. Build a model: E[U | dicodon profile]
3. Compute residual Uplift: U_resid = U - E[U | dicodon]
4. Re-run stop-context analysis on U_resid
5. Report: "% of signal explained by dicodon structure"
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

# Local imports
sys.path.insert(0, str(Path(__file__).parent))
from genetic_code_tools import fold_codon
from stats_tools import cohen_d
from cache_manager import write_json_atomic

# μ* encoding: A→00, C→01, G→10, U→11
MU_STAR = {"A": "00", "C": "01", "G": "10", "U": "11"}
MU_STAR_INT = {"A": 0, "C": 1, "G": 2, "U": 3}


def data_root() -> Path:
    """Return the data directory path."""
    return Path(__file__).resolve().parent.parent / "data"


def parse_orf_from_cds(seq: str) -> list[str]:
    """Parse a CDS sequence into codons (RNA alphabet, uppercase)."""
    seq = seq.upper().replace("T", "U")
    # Remove any non-standard bases
    seq = "".join(c for c in seq if c in "ACGU")
    if len(seq) % 3 != 0:
        seq = seq[:-(len(seq) % 3)]  # Truncate to multiple of 3
    return [seq[i:i+3] for i in range(0, len(seq), 3)]


@dataclass
class DicodonModel:
    """Linear model for E[U | dicodon frequencies]"""
    dicodon_coefs: dict[str, float]  # dicodon -> coefficient
    intercept: float
    r_squared: float
    n_samples: int


def compute_uplift(codon: str) -> int:
    """Compute Uplift value for a codon using μ* encoding."""
    val = 0
    for base in codon:
        val = (val << 2) | MU_STAR_INT.get(base, 0)
    return val


def extract_dicodon_features(codons: list[str]) -> Counter[str]:
    """Extract dicodon (codon-pair) frequencies from codon sequence."""
    dicodons: Counter[str] = Counter()
    for i in range(len(codons) - 1):
        dicodon = codons[i] + "_" + codons[i + 1]
        dicodons[dicodon] += 1
    return dicodons


def compute_window_uplift(codons: list[str], k: int, position: str = "before") -> float:
    """Compute mean Uplift for k codons before or after stop."""
    if position == "before":
        # Last k codons before stop (excluding stop)
        window = codons[-(k + 1):-1] if len(codons) > k else codons[:-1]
    else:  # after - not applicable for CDS-only data
        return np.nan
    
    if not window:
        return np.nan
    return np.mean([compute_uplift(c) for c in window])


def build_dicodon_regression_model(
    orf_data: list[dict[str, Any]],
    k: int,
) -> tuple[DicodonModel, np.ndarray]:
    """
    Build linear regression: U_before ~ dicodon frequencies
    Returns model and residuals.
    """
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    
    # Collect all unique dicodons
    all_dicodons: set[str] = set()
    for orf in orf_data:
        all_dicodons.update(orf["dicodon_counts"].keys())
    
    dicodon_list = sorted(all_dicodons)
    dicodon_idx = {d: i for i, d in enumerate(dicodon_list)}
    
    # Build feature matrix
    n_samples = len(orf_data)
    n_features = len(dicodon_list)
    X = np.zeros((n_samples, n_features), dtype=np.float32)
    y = np.zeros(n_samples, dtype=np.float32)
    
    for i, orf in enumerate(orf_data):
        # Normalize by ORF length
        total_dicodons = sum(orf["dicodon_counts"].values())
        if total_dicodons > 0:
            for dicodon, count in orf["dicodon_counts"].items():
                if dicodon in dicodon_idx:
                    X[i, dicodon_idx[dicodon]] = count / total_dicodons
        y[i] = orf["u_before"]
    
    # Filter valid samples
    valid_mask = ~np.isnan(y) & (np.sum(X, axis=1) > 0)
    X_valid = X[valid_mask]
    y_valid = y[valid_mask]
    
    if len(y_valid) < 100:
        raise ValueError(f"Insufficient samples for regression: {len(y_valid)}")
    
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_valid)
    
    # Ridge regression (regularized to handle collinearity)
    model = Ridge(alpha=1.0)
    model.fit(X_scaled, y_valid)
    
    # Predictions and residuals
    y_pred = model.predict(X_scaled)
    residuals_valid = y_valid - y_pred
    
    # R² computation
    ss_res = np.sum(residuals_valid ** 2)
    ss_tot = np.sum((y_valid - np.mean(y_valid)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    
    # Map coefficients back
    coefs = {}
    for dicodon, idx in dicodon_idx.items():
        coefs[dicodon] = float(model.coef_[idx] * scaler.scale_[idx]) if scaler.scale_[idx] > 0 else 0.0
    
    # Full residuals (NaN for invalid)
    residuals = np.full(n_samples, np.nan)
    residuals[valid_mask] = residuals_valid
    
    return DicodonModel(
        dicodon_coefs=coefs,
        intercept=float(model.intercept_),
        r_squared=r_squared,
        n_samples=int(np.sum(valid_mask)),
    ), residuals


def analyze_species_dicodon_absorption(
    species_dir: Path,
    k: int,
    max_records: int = 0,
) -> dict[str, Any] | None:
    """Analyze dicodon absorption for a single species."""
    metadata_path = species_dir / "metadata.json"
    # Try both possible CDS file names
    cds_path = species_dir / "cds_from_genomic.fna.gz"
    if not cds_path.exists():
        cds_path = species_dir / "cds.fasta.gz"
    
    if not metadata_path.exists() or not cds_path.exists():
        return None
    
    with open(metadata_path) as f:
        metadata = json.load(f)
    
    # Parse ORFs
    orf_data: list[dict[str, Any]] = []
    count = 0
    
    import gzip
    with gzip.open(cds_path, "rt") as f:
        current_header = ""
        current_seq = []
        
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if current_seq and current_header:
                    seq = "".join(current_seq).upper().replace("T", "U")
                    codons = parse_orf_from_cds(seq)
                    if codons and len(codons) >= k + 2:
                        # Get stop codon
                        stop_codon = codons[-1] if codons[-1] in ("UAA", "UAG", "UGA") else None
                        if stop_codon:
                            dicodon_counts = dict(extract_dicodon_features(codons))
                            u_before = compute_window_uplift(codons, k, "before")
                            
                            orf_data.append({
                                "stop_codon": stop_codon,
                                "dicodon_counts": dicodon_counts,
                                "u_before": u_before,
                                "n_codons": len(codons),
                            })
                            count += 1
                            
                            if max_records > 0 and count >= max_records:
                                break
                
                current_header = line[1:]
                current_seq = []
            else:
                current_seq.append(line)
        
        # Process last sequence
        if current_seq and current_header and (max_records == 0 or count < max_records):
            seq = "".join(current_seq).upper().replace("T", "U")
            codons = parse_orf_from_cds(seq)
            if codons and len(codons) >= k + 2:
                stop_codon = codons[-1] if codons[-1] in ("UAA", "UAG", "UGA") else None
                if stop_codon:
                    dicodon_counts = dict(extract_dicodon_features(codons))
                    u_before = compute_window_uplift(codons, k, "before")
                    
                    orf_data.append({
                        "stop_codon": stop_codon,
                        "dicodon_counts": dicodon_counts,
                        "u_before": u_before,
                        "n_codons": len(codons),
                    })
    
    if len(orf_data) < 500:
        return None
    
    # Build dicodon regression model
    try:
        dicodon_model, residuals = build_dicodon_regression_model(orf_data, k)
    except Exception as e:
        print(f"    [warn] Regression failed: {e}")
        return None
    
    # Add residuals to orf_data
    for i, resid in enumerate(residuals):
        orf_data[i]["u_resid"] = float(resid) if not np.isnan(resid) else None
    
    # Compute effect sizes for raw U and residual U
    results_by_stop: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"u_before": [], "u_resid": []})
    
    for orf in orf_data:
        stop = orf["stop_codon"]
        results_by_stop[stop]["u_before"].append(orf["u_before"])
        if orf["u_resid"] is not None:
            results_by_stop[stop]["u_resid"].append(orf["u_resid"])
    
    # Pairwise comparisons (UAA vs UGA)
    uaa_raw = np.array([x for x in results_by_stop["UAA"]["u_before"] if not np.isnan(x)])
    uga_raw = np.array([x for x in results_by_stop["UGA"]["u_before"] if not np.isnan(x)])
    uaa_resid = np.array(results_by_stop["UAA"]["u_resid"])
    uga_resid = np.array(results_by_stop["UGA"]["u_resid"])
    
    if len(uaa_raw) < 50 or len(uga_raw) < 50:
        return None
    
    # Effect sizes
    d_raw = cohen_d(list(uaa_raw), list(uga_raw)) or np.nan
    d_resid = cohen_d(list(uaa_resid), list(uga_resid)) if len(uaa_resid) >= 50 and len(uga_resid) >= 50 else np.nan
    
    # P-values (Welch's t-test)
    _, p_raw = stats.ttest_ind(uaa_raw, uga_raw, equal_var=False)
    _, p_resid = stats.ttest_ind(uaa_resid, uga_resid, equal_var=False) if len(uaa_resid) >= 50 and len(uga_resid) >= 50 else (np.nan, np.nan)
    
    # Percent signal explained
    if not np.isnan(d_resid) and abs(d_raw) > 0.001:
        pct_explained = max(0, 1 - abs(d_resid) / abs(d_raw)) * 100
    else:
        pct_explained = np.nan
    
    return {
        "species": species_dir.name,
        "domain": species_dir.parent.name,
        "n_orfs": len(orf_data),
        "n_uaa": len(uaa_raw),
        "n_uga": len(uga_raw),
        "dicodon_model": {
            "r_squared": dicodon_model.r_squared,
            "n_samples": dicodon_model.n_samples,
            "intercept": dicodon_model.intercept,
            "top_dicodons": sorted(
                dicodon_model.dicodon_coefs.items(),
                key=lambda x: abs(x[1]),
                reverse=True,
            )[:10],
        },
        "raw_signal": {
            "d_uaa_vs_uga": float(d_raw),
            "p_value": float(p_raw),
            "mean_uaa": float(np.mean(uaa_raw)),
            "mean_uga": float(np.mean(uga_raw)),
        },
        "residual_signal": {
            "d_uaa_vs_uga": float(d_resid) if not np.isnan(d_resid) else None,
            "p_value": float(p_resid) if not np.isnan(p_resid) else None,
            "mean_uaa": float(np.mean(uaa_resid)) if len(uaa_resid) > 0 else None,
            "mean_uga": float(np.mean(uga_resid)) if len(uga_resid) > 0 else None,
        },
        "pct_signal_explained_by_dicodon": float(pct_explained) if not np.isnan(pct_explained) else None,
    }


def generate_latex_table(results: list[dict[str, Any]], k: int) -> str:
    """Generate LaTeX table summarizing dicodon absorption."""
    lines = [
        f"% Dicodon absorption analysis (k={k})",
        "% Generated by exp_dicodon_absorption_analysis.py",
        "",
        "\\begin{table}[htbp]",
        "\\centering",
        f"\\caption{{Dicodon absorption of stop-context Uplift signal (k={k})}}",
        "\\label{tab:dicodon_absorption}",
        "\\begin{tabular}{llrrrrr}",
        "\\toprule",
        "Species & Domain & $R^2_{\\mathrm{dic}}$ & $d_{\\mathrm{raw}}$ & $d_{\\mathrm{resid}}$ & \\% Absorbed \\\\",
        "\\midrule",
    ]
    
    # Sort by domain then species
    sorted_results = sorted(results, key=lambda x: (x["domain"], x["species"]))
    
    total_absorbed = []
    for r in sorted_results:
        domain_abbr = {"archaea": "Arc", "bacteria": "Bac", "eukarya": "Euk"}.get(r["domain"], r["domain"][:3])
        r2 = r["dicodon_model"]["r_squared"]
        d_raw = r["raw_signal"]["d_uaa_vs_uga"]
        d_resid = r["residual_signal"]["d_uaa_vs_uga"]
        pct = r["pct_signal_explained_by_dicodon"]
        
        d_resid_str = f"{d_resid:+.2f}" if d_resid is not None else "--"
        pct_str = f"{pct:.0f}\\%" if pct is not None else "--"
        
        if pct is not None:
            total_absorbed.append(pct)
        
        lines.append(
            f"{r['species'][:12]} & {domain_abbr} & {r2:.2f} & {d_raw:+.2f} & {d_resid_str} & {pct_str} \\\\"
        )
    
    # Summary row
    if total_absorbed:
        mean_absorbed = np.mean(total_absorbed)
        lines.append("\\midrule")
        lines.append(f"\\textbf{{Mean}} & ({len(sorted_results)}) & -- & -- & -- & {mean_absorbed:.0f}\\% \\\\")
    
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ])
    
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="M2: Dicodon absorption analysis")
    p.add_argument("--k", type=int, default=10, help="Window size (codons)")
    p.add_argument("--max-records", type=int, default=0, help="Max records per species (0=all)")
    p.add_argument("--force", action="store_true", help="Force re-run")
    args = p.parse_args()
    
    k = args.k
    
    # Find all species with data
    corpora_dir = data_root() / "corpora"
    species_dirs: list[Path] = []
    
    for domain in ["archaea", "bacteria", "eukarya"]:
        domain_dir = corpora_dir / domain
        if domain_dir.exists():
            for sp_dir in domain_dir.iterdir():
                if sp_dir.is_dir() and (sp_dir / "metadata.json").exists():
                    species_dirs.append(sp_dir)
    
    print(f"Analyzing dicodon absorption for {len(species_dirs)} species (k={k})...")
    
    results: list[dict[str, Any]] = []
    for sp_dir in sorted(species_dirs):
        domain = sp_dir.parent.name
        species = sp_dir.name
        print(f"  [{domain}/{species}]", end=" ", flush=True)
        
        try:
            result = analyze_species_dicodon_absorption(sp_dir, k, args.max_records)
            if result:
                results.append(result)
                pct = result.get("pct_signal_explained_by_dicodon")
                pct_str = f"{pct:.0f}%" if pct is not None else "N/A"
                print(f"R²={result['dicodon_model']['r_squared']:.2f}, absorbed={pct_str}")
            else:
                print("skipped (insufficient data)")
        except Exception as e:
            print(f"error: {e}")
    
    # Convert numpy types for JSON serialization
    def convert_numpy(obj: Any) -> Any:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(v) for v in obj]
        elif isinstance(obj, tuple):
            return tuple(convert_numpy(v) for v in obj)
        return obj
    
    # Save results
    cache_dir = data_root() / "_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = cache_dir / f"dicodon_absorption_k{k}.json"
    serializable_results = convert_numpy(results)
    write_json_atomic(output_path, {
        "k": k,
        "n_species": len(results),
        "results": serializable_results,
    })
    print(f"\nWrote: {output_path}")
    
    # Generate LaTeX
    gen_dir = Path(__file__).parent.parent / "sections" / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    
    tex_path = gen_dir / f"dicodon_absorption_k{k}.tex"
    tex_content = generate_latex_table(results, k)
    tex_path.write_text(tex_content)
    print(f"Wrote: {tex_path}")
    
    # Summary
    if results:
        absorbed_pcts = [r["pct_signal_explained_by_dicodon"] for r in results if r.get("pct_signal_explained_by_dicodon") is not None]
        if absorbed_pcts:
            print(f"\n=== Summary (k={k}) ===")
            print(f"  Species analyzed: {len(results)}")
            print(f"  Mean % absorbed by dicodon: {np.mean(absorbed_pcts):.1f}%")
            print(f"  Range: {np.min(absorbed_pcts):.0f}% - {np.max(absorbed_pcts):.0f}%")


if __name__ == "__main__":
    main()
