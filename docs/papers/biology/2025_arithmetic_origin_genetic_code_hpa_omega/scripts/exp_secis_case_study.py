# -*- coding: utf-8 -*-
"""
SECIS element case study: Uplift patterns at selenocysteine insertion sites.

Performs a qualitative analysis of well-characterized Sec insertion sites
to demonstrate that the arithmetic model can identify these rare recoding events.

Output:
  - sections/generated/secis_case_study.tex
  - sections/generated/secis_case_study_table.tex
"""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np

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

def window_mean_uplift(seq: str) -> float:
    seq = normalize_seq(seq)
    codons = [seq[i:i+3] for i in range(0, len(seq)-2, 3)]
    vals = [codon_uplift(c) for c in codons if c in GENETIC_CODE]
    return float(np.mean(vals)) if vals else float("nan")

def load_sec_sites():
    """Load selenocysteine insertion sites from recoding data."""
    jsonl_path = data_dir() / "recoding_genbank" / "recoding_sites.jsonl"
    sec_sites = []
    
    with open(jsonl_path) as f:
        for line in f:
            rec = json.loads(line.strip())
            aa = rec.get("aa", "")
            if "Sec" in aa:
                sec_sites.append(rec)
    
    return sec_sites

def analyze_sec_sites(sites: list[dict]) -> dict:
    """Analyze Sec sites for Uplift patterns."""
    results = {
        "n_total": len(sites),
        "by_organism": {},
        "by_gene": {},
        "case_studies": [],
    }
    
    # Group by organism domain
    domain_counts = {}
    for s in sites:
        domain = s.get("domain", "Unknown")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    results["by_domain"] = domain_counts
    
    # Analyze individual sites
    for s in sites:
        gene = s.get("gene", "Unknown")
        organism = s.get("organism", "Unknown")
        
        # Get uplift values (handle None)
        def safe_float(x):
            if x is None: return float("nan")
            try: return float(x)
            except: return float("nan")
        
        delta = safe_float(s.get("delta"))
        before_mean = safe_float(s.get("before_mean_delta"))
        after_mean = safe_float(s.get("after_mean_delta"))
        terminal_before = safe_float(s.get("terminal_before_mean_delta"))
        terminal_after = safe_float(s.get("terminal_after_mean_delta"))
        plus4 = s.get("plus4_nt", "N") or "N"
        
        # Compute contrasts
        before_diff = before_mean - terminal_before if not (np.isnan(before_mean) or np.isnan(terminal_before)) else float("nan")
        after_diff = after_mean - terminal_after if not (np.isnan(after_mean) or np.isnan(terminal_after)) else float("nan")
        
        site_info = {
            "gene": gene,
            "organism": organism[:50] if organism else "Unknown",
            "domain": s.get("domain", "Unknown"),
            "codon": s.get("codon_rna", "UGA"),
            "delta": delta,
            "before_mean": before_mean,
            "after_mean": after_mean,
            "terminal_before": terminal_before,
            "terminal_after": terminal_after,
            "before_diff": before_diff,
            "after_diff": after_diff,
            "plus4": plus4,
        }
        
        # Track by gene
        if gene not in results["by_gene"]:
            results["by_gene"][gene] = []
        results["by_gene"][gene].append(site_info)
    
    # Select interesting case studies
    # 1. Classic selenoproteins - one representative per gene
    classic_genes = ["GPX1", "GPX2", "GPX3", "GPX4", "TXNRD1", "TXNRD2", "DIO1", "DIO2", "SELENOP", "SEPHS2"]
    seen_genes = set()
    for gene in classic_genes:
        if gene in results["by_gene"] and gene not in seen_genes:
            # Pick the first human one, or first one
            gene_sites = results["by_gene"][gene]
            human_sites = [s for s in gene_sites if "Homo sapiens" in s.get("organism", "")]
            pick = human_sites[0] if human_sites else gene_sites[0]
            pick["case_type"] = "classic_selenoprotein"
            results["case_studies"].append(pick)
            seen_genes.add(gene)
    
    # 2. Sites with extreme uplift contrasts
    all_sites = []
    for gene, site_list in results["by_gene"].items():
        all_sites.extend(site_list)
    
    # Sort by before_diff
    valid_sites = [s for s in all_sites if not np.isnan(s.get("before_diff", float("nan")))]
    if valid_sites:
        sorted_by_before = sorted(valid_sites, key=lambda x: x["before_diff"], reverse=True)
        for site in sorted_by_before[:5]:
            if site not in results["case_studies"]:
                site["case_type"] = "extreme_before_contrast"
                results["case_studies"].append(site)
    
    # Statistics
    before_diffs = [s["before_diff"] for s in valid_sites if not np.isnan(s["before_diff"])]
    after_diffs = [s["after_diff"] for s in valid_sites if not np.isnan(s.get("after_diff", float("nan")))]
    
    results["stats"] = {
        "n_valid": len(valid_sites),
        "before_diff_mean": float(np.mean(before_diffs)) if before_diffs else float("nan"),
        "before_diff_std": float(np.std(before_diffs)) if before_diffs else float("nan"),
        "after_diff_mean": float(np.mean(after_diffs)) if after_diffs else float("nan"),
        "after_diff_std": float(np.std(after_diffs)) if after_diffs else float("nan"),
        "frac_before_positive": sum(1 for d in before_diffs if d > 0) / len(before_diffs) if before_diffs else float("nan"),
        "frac_after_positive": sum(1 for d in after_diffs if d > 0) / len(after_diffs) if after_diffs else float("nan"),
    }
    
    return results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    
    out_tex = generated_dir() / "secis_case_study.tex"
    out_table = generated_dir() / "secis_case_study_table.tex"
    meta = {"analysis": "secis_case_study"}
    
    print("[load] Loading Sec insertion sites...", flush=True)
    sites = load_sec_sites()
    print(f"  Found {len(sites)} Sec sites", flush=True)
    
    print("[analyze] Analyzing Uplift patterns...", flush=True)
    results = analyze_sec_sites(sites)
    
    _emit(results, out_tex, out_table, meta)

def _emit(results: dict, out_tex: Path, out_table: Path, meta: dict):
    """Generate LaTeX output."""
    def f(x): return f"{x:.2f}" if x is not None and not np.isnan(x) else "--"
    
    stats = results.get("stats", {})
    domains = results.get("by_domain", {})
    
    lines = [
        "\\paragraph{Selenocysteine insertion site case study.}",
        f"Analyzed {results['n_total']} Sec (UGA$\\to$Sec) recoding sites from GenBank.",
        f"Domain distribution: {', '.join(f'{k}: {v}' for k, v in sorted(domains.items()))}.",
    ]
    
    # Key finding
    frac_before = stats.get("frac_before_positive", 0)
    mean_before = stats.get("before_diff_mean", 0)
    
    if frac_before > 0.6:
        lines.append(
            f"\\textbf{{Finding:}} {frac_before*100:.0f}\\% of Sec sites show higher $\\overline{{U}}_{{\\mathrm{{before}}}}$ "
            f"than their corresponding terminal stops (mean diff = {f(mean_before)}), "
            f"consistent with elevated ``arithmetic friction'' upstream of recoding sites."
        )
    elif frac_before < 0.4:
        lines.append(
            f"\\textbf{{Finding:}} Only {frac_before*100:.0f}\\% of Sec sites show higher $\\overline{{U}}_{{\\mathrm{{before}}}}$ "
            f"than terminal stops, indicating no consistent elevated upstream signal."
        )
    else:
        lines.append(
            f"\\textbf{{Finding:}} Sec sites show mixed patterns; {frac_before*100:.0f}\\% have higher "
            f"$\\overline{{U}}_{{\\mathrm{{before}}}}$ than terminal stops."
        )
    
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    print(f"Wrote: {out_tex}")
    
    # Case study table
    cases = results.get("case_studies", [])[:10]  # Top 10
    
    table_lines = [
        "\\begin{center}\\footnotesize",
        "\\begin{tabular}{llccccc}\\toprule",
        "Gene & Organism & $\\Delta$ & $\\bar{U}_b$ & $\\bar{U}_a$ & $d_b$ & +4 \\\\\\midrule",
    ]
    
    for c in cases:
        gene = c.get("gene", "?")[:10]
        org = c.get("organism", "?")[:20]
        table_lines.append(
            f"{gene} & {org} & {f(c.get('delta'))} & {f(c.get('before_mean'))} & "
            f"{f(c.get('after_mean'))} & {f(c.get('before_diff'))} & {c.get('plus4', '?')} \\\\"
        )
    
    table_lines.extend([
        "\\bottomrule",
        "\\multicolumn{7}{l}{\\footnotesize $\\Delta$=codon uplift; $\\bar{U}_{b/a}$=before/after mean; $d_b$=Sec$-$terminal before diff.} \\\\",
        "\\end{tabular}",
        "\\end{center}",
    ])
    
    write_text_atomic(out_table, "\n".join(table_lines) + "\n")
    write_json_atomic(cache_meta_path(out_table), meta)
    print(f"Wrote: {out_table}")

if __name__ == "__main__":
    main()
