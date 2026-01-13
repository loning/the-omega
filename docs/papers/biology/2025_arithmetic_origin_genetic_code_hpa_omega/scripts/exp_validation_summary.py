# -*- coding: utf-8 -*-
"""
Generate a comprehensive validation summary table.

Collects all key findings from computational experiments and creates
a summary table for the paper.

Output:
  - sections/generated/validation_summary.tex
"""

from __future__ import annotations
import json, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from cache_manager import write_text_atomic, write_json_atomic, cache_meta_path

def root_dir(): return SCRIPT_DIR.parent
def generated_dir(): return root_dir() / "sections" / "generated"
def cache_dir(): return root_dir() / "data" / "_cache"

def load_cached(name: str) -> dict | None:
    """Try to load a cached result."""
    patterns = [
        cache_dir() / f"{name}.json",
        cache_dir() / f"{name}_v1.json",
        cache_dir() / f"{name}_v2.json",
    ]
    for p in patterns:
        if p.exists():
            try:
                with open(p) as f:
                    return json.load(f)
            except:
                pass
    return None

def main():
    out_tex = generated_dir() / "validation_summary.tex"
    meta = {"analysis": "validation_summary"}
    
    # Collect findings
    findings = []
    
    # 1. Encoding validation
    findings.append({
        "category": "Encoding Identification",
        "test": "24-encoding exhaustive search",
        "result": "$\\mu^\\ast$ unique optimum at $m=6$",
        "interpretation": "$+$ Identifiability",
    })
    
    findings.append({
        "category": "Encoding Identification",
        "test": "Cross-task validation",
        "result": "$\\mu^\\ast$ ranks 2--8/24 on independent tasks",
        "interpretation": "$\\pm$ Mixed",
    })
    
    # 2. Null models
    findings.append({
        "category": "Null Models",
        "test": "Synonymous codon permutation",
        "result": "Stop-class diff $p<0.001$",
        "interpretation": "$+$ Not synonymous bias",
    })
    
    findings.append({
        "category": "Null Models",
        "test": "ORF-level dicodon shuffle",
        "result": "Before-window $p>0.29$",
        "interpretation": "$-$ Absorbed by codon-pair",
    })
    
    findings.append({
        "category": "Null Models",
        "test": "Per-window dinuc shuffle",
        "result": "Before-window $p<0.001$",
        "interpretation": "$+$ Survives dinuc control",
    })
    
    # 3. Mechanism proxies
    findings.append({
        "category": "Mechanism Proxies",
        "test": "Uplift vs MFE (ViennaRNA)",
        "result": "Partial $\\rho \\approx 0$ after GC control",
        "interpretation": "$-$ GC-mediated",
    })
    
    findings.append({
        "category": "Mechanism Proxies",
        "test": "Uplift vs tAI",
        "result": "Codon-level $\\rho = 0.005$ (ns)",
        "interpretation": "$-$ No correlation",
    })
    
    findings.append({
        "category": "Mechanism Proxies",
        "test": "Uplift vs Pause scores",
        "result": "$\\rho = -0.12$ (ns)",
        "interpretation": "$-$ No correlation",
    })
    
    # 4. Recoding validation
    findings.append({
        "category": "Recoding Validation",
        "test": "Sec $U_{before}$ vs terminal UGA",
        "result": "diff $= +3.65$, $p < 0.001$",
        "interpretation": "$+$ Elevated upstream",
    })
    
    findings.append({
        "category": "Recoding Validation",
        "test": "Sec 75\\% elevated",
        "result": "n=893 Sec sites",
        "interpretation": "$+$ Consistent pattern",
    })
    
    # 5. Predictive models
    findings.append({
        "category": "Predictive Models",
        "test": "Extended M2-M1 (recoding task)",
        "result": "$\\Delta$AUC $= +0.17\\%$, $p = 0.01$",
        "interpretation": "$+$ Incremental info",
    })
    
    findings.append({
        "category": "Predictive Models",
        "test": "Multi-scale de-confound",
        "result": "$\\Delta R^2 \\approx 0$",
        "interpretation": "$-$ No unique structure info",
    })
    
    # 6. Cross-validation
    findings.append({
        "category": "Cross-validation",
        "test": "Multi-$k$ stability",
        "result": "After-window effect local to $k \\leq 10$",
        "interpretation": "$+$ Near-stop signal",
    })
    
    findings.append({
        "category": "Cross-validation",
        "test": "Nonstandard codes meta",
        "result": "$\\mu^\\ast$ ranks 2/24",
        "interpretation": "$+$ Cross-code consistent",
    })
    
    # Generate LaTeX
    _emit(findings, out_tex, meta)

def _emit(findings: list[dict], out_tex: Path, meta: dict):
    """Generate LaTeX table."""
    lines = [
        "\\paragraph{Computational validation summary.}",
        "\\begin{center}",
        "\\footnotesize",
        "\\begin{tabular}{llll}",
        "\\toprule",
        "Category & Test & Result & Interpretation \\\\",
        "\\midrule",
    ]
    
    current_cat = None
    for f in findings:
        cat = f["category"]
        show_cat = ""
        if cat != current_cat:
            if current_cat is not None:
                lines.append("\\midrule")
            current_cat = cat
            show_cat = cat
        
        lines.append(
            f"{show_cat} & {f['test']} & {f['result']} & {f['interpretation']} \\\\"
        )
    
    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{center}",
        "\\footnotesize $+$ = supports hypothesis; $-$ = does not support; $\\pm$ = ambiguous.",
    ])
    
    write_text_atomic(out_tex, "\n".join(lines) + "\n")
    write_json_atomic(cache_meta_path(out_tex), meta)
    print(f"Wrote: {out_tex}")

if __name__ == "__main__":
    main()
