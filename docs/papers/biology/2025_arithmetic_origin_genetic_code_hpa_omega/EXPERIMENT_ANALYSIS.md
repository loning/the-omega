# Computational Validation: Experiment Analysis Report

**Project**: Arithmetic Origin of the Genetic Code  
**Date**: 2026-01-13  
**Status**: Computational validation phase complete

---

## Executive Summary

This document summarizes all computational experiments conducted to validate the core hypotheses of the arithmetic origin framework for the genetic code. The experiments span three layers:

1. **Arithmetic Layer**: Does μ\* emerge as the unique optimal encoding?
2. **Statistical Layer**: Do Uplift signals distinguish biological events?
3. **Mechanistic Layer**: Does Uplift correlate with physical observables?

**Key Finding**: The arithmetic framework is mathematically valid, but the mechanistic bridge to translation dynamics is not supported by current evidence.

---

## Table of Contents

1. [Core Hypotheses](#core-hypotheses)
2. [Experiment Inventory](#experiment-inventory)
3. [Results by Category](#results-by-category)
4. [Detailed Findings](#detailed-findings)
5. [Negative Results Analysis](#negative-results-analysis)
6. [Future Work](#future-work)
7. [Reproducibility](#reproducibility)

---

## Core Hypotheses

### H1: μ\* Uniqueness (Arithmetic)
The 2-bit encoding μ\* = {A→00, C→01, G→10, U→11} is the unique optimum under the boundary-hit objective with control set K = {AUG, UAA, UAG, UGA}.

### H2: Uplift Signal (Statistical)
The Uplift quantity Δ(c) derived from μ\* exhibits systematic differences between:
- Different stop codons (UAA vs UAG vs UGA)
- Terminal stops vs recoding sites
- Before-window vs after-window contexts

### H3: Mechanistic Bridge (Biological)
Uplift correlates with physical/chemical observables that influence translation:
- RNA secondary structure (MFE)
- Translation rate (tAI, Ribo-seq pause scores)
- Ribosome dynamics

---

## Experiment Inventory

### Phase 1: Core Validation (8 Computational Reinforcement Experiments)

| ID | Script | Purpose |
|----|--------|---------|
| CR1 | `exp_encoding_cross_task_validation.py` | 24-encoding cross-task validation |
| CR2 | `exp_control_objective_robustness.py` | Objective function robustness |
| CR3A | `exp_stop_context_null_synonymous_orf.py` | Synonymous permutation null |
| CR3B | `exp_stop_context_null_dicodon_orf.py` | Dicodon-preserving null |
| CR4 | `exp_stop_context_position_curves.py` | Position-decomposed curves |
| CR5 | `exp_out_of_sample_mu_star_ranking.py` | Out-of-sample validation |
| CR6 | `exp_incremental_predictive_power.py` | Incremental explanatory power |
| CR7 | `exp_nonstandard_codes_meta_analysis.py` | Nonstandard codes meta-analysis |
| CR8 | `exp_start_stop_symmetry_statistic.py` | Start-stop symmetry |

### Phase 2: Mechanism Proxy Experiments

| ID | Script | Purpose |
|----|--------|---------|
| MP1 | `exp_uplift_mfe_correlation.py` | Uplift vs RNA MFE (ViennaRNA) |
| MP2 | `exp_uplift_structure_deconfound.py` | Multi-scale de-confounding regression |
| MP3 | `exp_uplift_translation_rate_proxy.py` | Uplift vs tAI correlation |
| MP4 | `exp_riboseq_pause_analysis.py` | Codon-level pause scores |
| MP5 | `exp_nested_models_extended.py` | Extended M0-M5 nested models |

### Phase 3: Control & Sensitivity Experiments

| ID | Script | Purpose |
|----|--------|---------|
| CS1 | `exp_stop_context_window_analysis.py` | Per-window dinucleotide shuffle |
| CS2 | `exp_multi_k_stability.py` | Multi-k stability analysis |
| CS3 | `exp_gene_length_stratification.py` | Gene length confound |
| CS4 | `exp_stop_codon_context_aa.py` | Last amino acid context |
| CS5 | `exp_codon_usage_uplift.py` | Codon usage bias |
| CS6 | `exp_plus4_detailed.py` | +4 base detailed analysis |
| CS7 | `exp_bootstrap_ci.py` | Bootstrap confidence intervals |
| CS8 | `exp_effect_sizes.py` | Cohen's d effect sizes |

### Phase 4: Case Studies

| ID | Script | Purpose |
|----|--------|---------|
| CAS1 | `exp_secis_case_study.py` | Selenocysteine insertion sites |
| CAS2 | `exp_sec_detailed_features.py` | Sec detailed feature analysis |

---

## Results by Category

### ✅ Positive Results (Support Hypothesis)

| Experiment | Key Finding | p-value | Effect Size |
|------------|-------------|---------|-------------|
| CR1 | μ\* unique at m=6 | - | - |
| CR3A | Synonymous null rejected | p<0.001 | - |
| CS1 | Dinuc shuffle null rejected | p<0.001 | - |
| CAS1 | 75% Sec sites show elevated U_before | - | - |
| CAS2 | Sec vs UGA U_before diff | p<0.001 | +3.65 |
| CS7 | 4/6 pairwise CI exclude zero | - | - |
| MP5 | M2-M1 incremental AUC | p=0.01 | +0.17% |
| CR7 | μ\* ranks 2/24 across codes | p=0.08 | - |

### ❌ Negative Results (Do Not Support Hypothesis)

| Experiment | Key Finding | p-value | Interpretation |
|------------|-------------|---------|----------------|
| MP1 | Uplift-MFE partial ρ≈0 | - | GC-mediated |
| MP2 | ΔR² = 0.000 at all scales | - | No unique info |
| MP3 | Uplift-tAI ρ=0.005 | p=0.80 | No correlation |
| MP4 | Uplift-Pause ρ=-0.12 | p=0.35 | No correlation |
| CR3B | Dicodon null not rejected | p>0.29 | Absorbed by codon-pair |
| CS8 | Cohen's d = 0.02-0.08 | - | Negligible effect |

### ± Mixed/Neutral Results

| Experiment | Key Finding | Interpretation |
|------------|-------------|----------------|
| CR1-cross | μ\* ranks 2-8/24 on tasks | Not consistently best |
| CS3 | Long genes higher after-U | Confound to control |
| CS5 | Freq-Uplift ρ=-0.23 | Not significant |
| CS6 | +4 purine vs pyr effect | Context-dependent |

---

## Detailed Findings

### 1. Arithmetic Layer: SUPPORTED ✅

**μ\* Uniqueness**
- Exhaustive search over 24 encodings confirms μ\* is the unique optimum at m=6
- Robustness: μ\* remains optimal under multiple objective variants
- Nonstandard codes: μ\* ranks 2/24 in meta-analysis (Fisher score 59.05)

**14/48 Symmetry**
- AUG and UAA both map to boundary words under μ\*
- This is an arithmetic theorem, not an empirical claim

### 2. Statistical Layer: PARTIALLY SUPPORTED ±

**Stop Codon Differences**
- UAA, UAG, UGA show statistically significant Uplift differences
- Bootstrap CI: 4/6 pairwise comparisons exclude zero
- **BUT**: Effect sizes are negligible (Cohen's d = 0.02-0.08)

**Recoding vs Terminal**
- Sec sites show elevated U_before (+3.65, p<0.001)
- 75% of Sec sites have higher upstream Uplift than terminal UGA
- Effect concentrated at distal positions (j=-10: diff=+11.3)

**Null Model Survival**
- Survives synonymous codon permutation (p<0.001)
- Survives per-window dinucleotide shuffle (p<0.001)
- **FAILS**: Absorbed by ORF-level dicodon structure (p>0.29)

### 3. Mechanistic Layer: NOT SUPPORTED ❌

**RNA Secondary Structure**
```
Raw correlation:        ρ = -0.22 (Uplift-MFE)
Partial (GC-controlled): ρ ≈ 0
ΔR² contribution:       0.000
```
→ Relationship entirely mediated by GC content

**Translation Rate**
```
Uplift-tAI (codon):     ρ = 0.005 (ns)
Uplift-tAI (window):    ρ = 0.18 → 0.00 after GC control
```
→ No independent correlation

**Ribosome Pausing**
```
Uplift-Pause (codon):   ρ = -0.12 (ns)
Within-family:          avg ρ = -0.09
```
→ No correlation with ribosome dynamics

---

## Negative Results Analysis

### Why Did Mechanistic Bridging Fail?

1. **GC Collinearity**
   - Uplift is strongly correlated with GC content
   - All physical quantities (MFE, tAI) are also GC-correlated
   - Once GC is controlled, Uplift adds no information

2. **Scale Mismatch**
   - Uplift is defined at codon level (arithmetic)
   - RNA structure emerges at longer scales (>30nt)
   - Ribosome dynamics involve multi-codon windows

3. **Data Limitations**
   - Ribo-seq data: Only pre-compiled pause scores available
   - Cross-species: Limited to human RefSeq

### Implications

The arithmetic framework is **mathematically elegant but biologically underdetermined**:
- μ\* uniqueness is a theorem about coding structure
- Uplift differences are statistically real but practically small
- The "phase friction" interpretation lacks empirical support

---

## Future Work

### High Priority (Recommended)

1. **Controlled Synthetic Library**
   - Design sequences with matched GC/structure but varying Uplift
   - Measure readthrough directly
   - This is the only way to establish causality

2. **Cross-Domain Corpus Expansion**
   - Add ≥10 species per domain (Bacteria, Archaea, Eukarya)
   - Include extremophiles (thermophiles, halophiles)
   - Test if patterns hold across evolutionary distance

3. **Full Ribo-seq Analysis**
   - Download raw BigWig data (requires Linux/WSL)
   - Compute window-level pause scores
   - Test Uplift-pause correlation at biological scales

### Medium Priority

4. **Cell-Free Translation**
   - Test same constructs in vitro
   - Separate NMD/stability effects from translation

5. **SECIS Element Analysis**
   - Detailed structural analysis of Sec insertion elements
   - Test if Uplift signature is independent of known motifs

### Lower Priority

6. **Alternative Encodings**
   - Test if other high-scoring encodings (rank 1, 3) show similar patterns
   - Strengthen μ\* uniqueness claim

7. **Non-Standard Code Organisms**
   - Obtain sequence data from ciliate, mitochondrial genomes
   - Test framework on "stress cases"

---

## Reproducibility

### Environment

```
Python: 3.11+
Key packages:
  - numpy, scipy, scikit-learn
  - viennarna (for MFE calculation)
  - matplotlib (for figures)
```

### Running All Experiments

```bash
cd docs/papers/biology/2025_arithmetic_origin_genetic_code_hpa_omega
python scripts/run_all.py
```

### Data Requirements

- Human RefSeq mRNA: `data/refseq_hsapiens_mrna/`
- Recoding sites: `data/recoding_genbank/recoding_sites.jsonl`
- Genetic code tables: `data/gc.prt`

### Output

All generated LaTeX fragments: `sections/generated/*.tex`

---

## Commit History (This Session)

| Commit | Description |
|--------|-------------|
| `3a664c0d` | Effect size analysis (Cohen's d) |
| `1fc538c9` | +4 detailed analysis + Bootstrap CI |
| `bf781a63` | Gene length, codon context, usage bias |
| `57d01a78` | Sec detailed features + validation summary |
| `3f815e33` | Multi-scale de-confounding regression |
| `1bb39213` | Codon-level Ribo-seq pause analysis |
| `43953cb3` | Real MFE + Sec case study |
| `97edc25e` | Multi-k stability analysis |
| `9daf2bb3` | Extended models integration |
| `65def710` | Extended nested models M0-M5 |
| `be9c365c` | Uplift vs tAI correlation |
| `83c4300d` | Per-window null + structure correlation |

---

## Conclusion

### What We Proved
- μ\* is mathematically unique under the boundary-hit objective
- Stop codon Uplift differences are statistically significant
- Sec recoding sites have a distinctive upstream Uplift signature

### What We Did Not Prove
- Uplift predicts RNA structure beyond GC
- Uplift correlates with translation rate
- Uplift influences ribosome dynamics

### Honest Assessment
The arithmetic framework provides a novel lens for analyzing genetic code structure, but its biological interpretation as "phase friction affecting translation" remains speculative. The framework is best understood as a **descriptive mathematical characterization** rather than a **mechanistic explanation**.

---

*Document generated: 2026-01-13*  
*Repository: the-omega*  
*Path: `docs/papers/biology/2025_arithmetic_origin_genetic_code_hpa_omega/EXPERIMENT_ANALYSIS.md`*
