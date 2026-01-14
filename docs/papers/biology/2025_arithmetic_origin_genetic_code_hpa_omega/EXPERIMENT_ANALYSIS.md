# Computational Validation: Experiment Analysis & Next-Phase Development Plan

**Project**: Arithmetic Origin of the Genetic Code  
**Date**: 2026-01-14  
**Status**: Phase 2 active; systematic validation in progress (living document)

---

## 项目目标（一句人话）

我们提出一个最小接口层，把 64 个密码子通过稳定语言规则压缩为 21 类，并得到唯一编码解。我们将用**大规模跨物种语料**、**强 null 对照**、以及 **RNA 结构与 Ribo-seq 暂停**这两个中介量验证：这个折叠规则不是统计换皮，而是翻译系统稳定读取语言的一部分。

### 我们要证明的三件事

1. **64→21 不是随便压缩的**：在一个非常小的候选空间里，我们的规则能产生"唯一且刚性"的结构解。
2. **这个规则不是坐标系装饰**：它在真实生物数据里对应到翻译过程的可观测差异，且在强控制后仍然站得住。
3. **它在多个系统可复现**：跨物种、跨数据库、跨实验数据都能复现。

---

## 三绿灯成功判据

### 🟢 绿灯 A：唯一性与不可替代性

在 24 种核苷酸 2-bit 编码里，μ\* 不仅在"识别目标"上最好，还要在一组**独立任务**上表现为极值或接近极值。换句话说，不是"我们挑出来的 μ\*"，而是"μ\* 在独立任务里也最像自然界用的那把尺"。

**验证任务**：
- A1: 终止位点附近 stop 类别的 U_before/U_after 差异强度
- A2: Recoding vs terminal stop 的可分性（AUC / effect size）
- A3: 跨物种一致性（效应方向在多少物种里一致）
- A4: Readthrough/PRF 预测性能

**通过标准**：μ\* 在多个任务里稳定靠前（rank ≤ 3/24），而不是只在一个任务赢。

### 🟢 绿灯 B：不是 GC 换皮

在控制 GC、二核苷酸、已知局部规则后，Uplift 相关效应仍然存在；或者 Uplift 至少能稳定对应一个中介量（如 RNA 局部结构或核糖体暂停）。

**null 层级**：
- B1: 成分匹配 null（GC + dinucleotide matched controls）
- B2: 生成式 dinucleotide shuffle（Eulerian trail 保持）
- B3: 保持阅读框的 codon/dicodon shuffle

**通过标准**：在 B2 或 B3 强 null 下，效应仍比随机显著大。

### 🟢 绿灯 C：跨系统复现

不只在人类 RefSeq 上有效，跨真核、细菌、古菌以及多个数据库版本都能看到同向效应。

**通过标准**：
- 效应方向在 ≥60% 物种中一致
- Meta-analysis 汇总效应 CI 不含零
- 异质性 I² < 80% 或可解释的分层结构

---

## Executive Summary

This document summarizes all computational experiments conducted to validate the core hypotheses of the arithmetic origin framework for the genetic code. The experiments span three layers:

1. **Arithmetic Layer**: Does μ\* emerge as the unique optimal encoding?
2. **Statistical Layer**: Do Uplift signals distinguish biological events?
3. **Mechanistic Layer**: Does Uplift correlate with physical observables?

**Key Finding**: The arithmetic framework is mathematically valid, but the mechanistic bridge to translation dynamics is not supported by current evidence.

**Living doc note (主开发文档说明)**: Sections above are the consolidated computational validation record; **Next Steps** below is the active development roadmap for systematic validation.

---

## Table of Contents

1. [Core Hypotheses](#core-hypotheses)
2. [Experiment Inventory](#experiment-inventory)
3. [Results by Category](#results-by-category)
4. [Detailed Findings](#detailed-findings)
5. [Negative Results Analysis](#negative-results-analysis)
6. [Next Steps (A100 Migration)](#next-steps-a100-migration)
7. [Reproducibility & Acceptance Tests](#reproducibility--acceptance-tests)

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

## Next Steps (A100 Migration)

This section is the **main development plan** for scaling the project on an A100 machine (Linux preferred) and for tightening H2/H3 with more data and stronger tests.

---

### Task Claims

- 2026-01-14 — **COMPLETED**: 模块 E（Ribo-seq 暂停桥接）窗口级 pause score + 按 `U_after` 分位数分层比较（先做可复现的 window-level proxy；raw Ribo-seq 多数据集复现仍待做）。产物：`exp_riboseq_pause_window_proxy.py` + `sections/generated/riboseq_pause_window_proxy.tex`. Branch: `paper-bio`.
- 2026-01-14 — **CLAIMED**: 模块 E（Ribo-seq 暂停桥接）多数据集复现（≥3 独立 Ribo-seq bigWig 数据集；先做人类 hg* bigWig 窗口 pausing 与 Uplift 关联/分层，再汇总跨数据集一致性）。目标数据集（GEO）：GSE148965 / GSE199387 / GSE211536. Branch: `paper-bio`.

## 核心计算实验模块（7 模块系统验证计划）

以下模块按优先级排序，可并行执行。每个模块都有明确的"反驳点"和"堵回去的实验"。

### 模块 A：24 编码全对照的独立验证

**目的**：堵住"μ\* 是你们用同一套信息挑出来的"这种反驳。

**状态**：🔄 部分完成

**做法**：
1. 识别阶段固定，永远只用识别规则选出 μ\*，不再动
2. 设计 3-5 个独立验证任务，全部不包含识别时用的目标量

**验证任务**：
| 任务 | 描述 | 脚本 | 状态 |
|------|------|------|------|
| A1 | 终止位点 U_before/U_after 差异强度 | `exp_encoding_cross_task_validation.py` | ✅ |
| A2 | Recoding vs terminal AUC | `exp_out_of_sample_mu_star_ranking.py` | ✅ |
| A3 | 跨物种一致性 | `exp_loso_generalization.py` | ✅ (50%) |
| A4 | Readthrough/PRF 预测 | (pending) | ⏳ |

**当前结果**：
- μ\* ranks 2/24 in meta-analysis (Fisher score 59.05)
- LOSO sign consistency: 50% (at chance level)
- **结论**：绿灯 A 部分亮起，但跨物种一致性不足

---

### 模块 B：强 null 攻击（证明不是换皮统计）

**目的**：堵住"你这就是 GC 或 motif"这种反驳。

**状态**：🔄 进行中

**三类 null**：

#### B1：成分匹配 null
| 实验 | 脚本 | 状态 | 结果 |
|------|------|------|------|
| GC+dinuc 匹配对照 | `exp_stop_context_window_analysis.py` | ✅ | p<0.001 survives |

#### B2：生成式 dinucleotide shuffle
| 实验 | 脚本 | 状态 | 结果 |
|------|------|------|------|
| 窗口级 dinuc shuffle | `exp_stop_context_dinuc_shuffle_window.py` | ✅ | p<0.001 survives |

#### B3：保持阅读框的 codon/dicodon shuffle
| 实验 | 脚本 | 状态 | 结果 |
|------|------|------|------|
| ORF-level dicodon null | `exp_stop_context_null_dicodon_orf.py` | ✅ | **FAILS** p>0.29 |
| Dicodon 吸收量化 | `exp_dicodon_absorption_analysis.py` | ✅ | 33% absorbed (k=10) |

**当前结果**：
- B1/B2 通过，B3 失败
- Dicodon 结构解释 33% 信号（k=10）
- **结论**：绿灯 B 部分亮起，但 dicodon 吸收是主要问题

---

### 模块 C：m 与 k 的鲁棒性扫描

**目的**：堵住"你们只在一个参数上成立"的反驳。

**状态**：✅ 完成

**做法**：
- k 扫描：k ∈ {3, 5, 10, 20}
- m 扫描：m ∈ {6, 7, 8, 9}

**当前结果**：
| k | Meta d (UAA vs UGA) | 95% CI | I² |
|---|---------------------|--------|-----|
| 3 | -0.035 | [-0.066, -0.004] | 93.2% |
| 5 | -0.006 | [-0.034, 0.021] | 90.9% |
| 10 | -0.030 | [-0.065, 0.004] | 94.8% |
| 20 | -0.036 | [-0.076, 0.004] | 96.3% |

**结论**：只有 k=3 边界显著，高异质性在所有 k 值持续

---

### 模块 D：RNAfold 结构桥接

**目的**：把 Uplift 从"抽象张力"接到"可观测物理代理"。

**状态**：❌ 未通过

**三层证据要求**：
1. 描述性：U_after 与 MFE 相关性 → ρ = -0.22 (raw), ≈0 (GC-controlled)
2. 控制后：ΔR² = 0.000 (Uplift 无独立解释力)
3. 独立解释力：嵌套模型无增益

**当前结果**：
```
Raw correlation:        ρ = -0.22 (Uplift-MFE)
Partial (GC-controlled): ρ ≈ 0
ΔR² contribution:       0.000
```

**结论**：绿灯 D 未亮。关系完全由 GC 中介。需要 zMFE（成分匹配 shuffle）重新测试。

---

### 模块 E：Ribo-seq 暂停桥接

**目的**：直接把 Uplift 接到"核糖体是否卡住"。

**状态**：❌ 未通过

**当前结果**：
```
Uplift-Pause (codon):   ρ = -0.12 (ns)
Within-family:          avg ρ = -0.09
Window proxy (k=10):    ρ(U_before, pause_before) = -0.36 (p<0.001)
                         high U_after vs low U_after: d=-0.06 (p=0.66), matched d=-0.03 (p=0.80)
```

**待做**：
- [x] 窗口级 pause score（不是 codon 级；先做可复现的 window-level proxy）
- [ ] 多数据集复现（≥3 独立 Ribo-seq 数据集）
- [x] 按 U_after 分位数分层比较（含成分匹配对照）

---

### 模块 F：非标准遗传密码表压力测试

**目的**：堵住"你们只解释标准遗传码"的反驳。

**状态**：🔄 部分完成

**当前结果**：
- μ\* ranks 2/24 across nonstandard codes (meta-analysis)
- 边界对齐在多数非标准码中保持

**待做**：
- [ ] 系统收集所有 NCBI 遗传密码表
- [ ] 对每个代码计算边界对齐统计
- [ ] 测试"语义迁移但边界角色保留"现象

---

### 模块 G：Sec/Pyl 分层策略

**目的**：扩展 recoding 分析到更多事件类型。

**状态**：✅ Sec 完成，⏳ Pyl 待扩展

**当前结果（Sec）**：
- 75% Sec sites show elevated U_before
- Effect concentrated at distal positions (j=-10: diff=+11.3)

**策略**：
- Sec：统计主战场，按域/SECIS类型分层
- Pyl：案例库模式，输出极端候选作为湿实验目标

---

## 优先级与执行计划

推荐执行顺序（最快把 64→21 从"结构"变成"强生物学证据"）：

1. ✅ 模块 A：24 编码独立验证 → 部分完成
2. ✅ 模块 B：强 null 攻击 → 部分完成，dicodon 问题已量化
3. ⏳ 模块 D：RNAfold 桥接 → 需用 zMFE 重测
4. ✅ 模块 C：鲁棒性扫描 → 完成
5. ⏳ 模块 E：Ribo-seq 桥接 → 需窗口级分析
6. ⏳ 模块 F：非标准遗传码压力测试
7. ⏳ 模块 G：Sec/Pyl 分层扩展

**前 3 个模块能把最大反驳点基本堵死。**

---

### 0) Goalposts (what “proving H2/H3” means operationally)

**H2 (“Uplift signal”) should be treated as a replication claim, not a p-value claim.** For the next phase we treat H2 as supported only if we can show, on **held-out datasets**, that at least one pre-registered stop/recoding endpoint:

- reproduces across domains/species (meta-analysis with heterogeneity reported);
- survives stronger confound controls (GC + dinucleotide + dicodon / codon-pair structure);
- has a practically non-negligible effect size (report both effect size and CI, not just p).

**H3 (“mechanistic bridge”) should be tested with metrics that reduce GC mediation.** Raw MFE/tAI are too GC-coupled; the next phase should prioritize *composition-conditioned* structure/translation metrics (e.g., MFE z-scores vs composition-matched shuffles; window-scale pause scores from raw Ribo-seq).

### 0.1) Evidence ladder (how to “prove” H2/H3 without fooling ourselves)

This is the recommended evidence ladder (stronger ⇒ harder, but more convincing):

- **E0 (in-sample signal)**: significant stop/recoding contrasts in one corpus with basic controls.
- **E1 (replication)**: same endpoint reproduces in independent corpora/species; report heterogeneity.
- **E2 (confound-tight replication)**: endpoint persists under composition controls and stronger null families (especially dicodon/codon-pair).
- **E3 (mechanistic association)**: endpoint correlates with a mechanistic observable *after* confound conditioning (e.g., zMFE, window pausing), and replicates across studies.
- **E4 (causality)**: manipulating Uplift (or residual-Uplift) in matched constructs changes readthrough/recoding in a reporter/cell-free assay.

Target state:
- H2 can be considered “supported” at **E1–E2**.
- H3 requires **E3** at minimum, and only becomes high-impact with **E4**.

### 0.2) Statistical contract (pre-registration for the next phase)

To avoid “p-hacking by data expansion”, we should pre-register (in a small JSON/YAML spec in-repo) before large A100 runs:

- **Primary endpoints** (choose 1–2, keep them stable):
  - stop-context window means: `U_before(s;k)` and/or `U_after(s;k)` at a fixed k (e.g. k=10),
  - net contrast: `D(s;k)=U_after(s;k)-U_before(s;k)`,
  - recoding vs terminal: AUC using `(u_before, u_after, u_after-u_before)` as predictors.
- **Primary comparison(s)**: which stop pairs (UAA vs UGA, etc.) and which event classes (terminal vs recoding).
- **Train/test protocol**: e.g., leave-one-species-out; or hold out entire studies for Ribo-seq.
- **Effect size thresholds**: define “not negligible” (e.g., Cohen’s d ≥ 0.2, or AUC uplift ≥ 0.01 with CI).
- **Multiple-testing policy**: which tests are confirmatory vs exploratory; BH-FDR on exploratory families.

Reference: the test-statistic definitions already exist in `sections/appendices/05_statistical_tests.tex` (stop/start windows, composition matching, effect sizes, multi-k).

### 0.3) Data model (what we store for large-scale H2/H3 runs)

For large corpora and cross-study analyses, the safest pattern is:

- **Event-level records** (JSONL/Parquet): one row per stop (terminal) / start / recoding site.
  - Required fields: `dataset`, `species`, `code_table_id`, `record_id`, `frame`, `pos`, `stop_codon`, `k`, `u_before`, `u_after`, `gc_before`, `gc_after`, `dinuc_before`, `dinuc_after`, plus any stratifiers (+4, after_nt6, last_aa, gene_length, etc.).
- **Per-record provenance**: `analysis_version`, `script`, `seed`, `manifest_digest`, input file digests.
- **Derived summaries**: Welford stats per class and per-k, effect sizes + CI, and meta-analysis outputs.

This project already has most of the schema machinery (summary JSON + `.meta.json` digests; optional Supabase import). The next phase should extend it across new datasets rather than inventing a parallel format.

### 0.4) Where “how to prove it” is already written (local retrieval / protocol index)

This repo already contains two protocol appendices that are essentially “how to prove H2/H3”:

- **Statistical protocols**: `sections/appendices/05_statistical_tests.tex`
  - defines stop/start windows, composition-matched controls, effect sizes, multi-k sensitivity, and response-curve fits.
- **Biological/assay protocols**: `sections/appendices/07_biological_validation.tex`
  - reporter readthrough design, cell-free concordance test, Sec/Pyl mechanistic controls (SECIS disruption/rescue; factor dependency; MS confirmation), and mechanistic bridge rationale.

The A100 phase is mainly about making these protocols scale (more datasets, stronger null families, and better mechanistic observables).

### 1) Milestone M0 — A100 migration & reproducibility hardening (first priority)

**Status**: ✅ COMPLETED (2026-01-13)

**Completion Notes**:
- Environment validated: Python 3.12.11 with numpy, scipy, pandas, matplotlib, scikit-learn
- Data bundle restored from GitHub Release `genetic-code-data-v1.1` (220.8 MiB)
- All smoke tests passed: `exp_genetic_code_decompiler.py`, `exp_random_code_monte_carlo.py`, `exp_recoding_sites.py`, `exp_out_of_sample_mu_star_ranking.py`
- Full `run_all.py --no-download --force` completed (151 LaTeX fragments generated)
- ViennaRNA not available (requires Conda); MFE experiments use cached results
- Missing: `corpus_panel_v2` (deferred to M1 for multi-species expansion)

**Objective**: From a clean checkout on the A100 box, reproduce *all* claims already present in the paper and in this report (including mechanistic-proxy negatives), with a fast smoke path and a full path.

**Tasks (repo-side)**
- Make dependency tiers explicit:
  - `requirements.txt` = core scientific stack used by most experiments.
  - Add/define an “extras” tier for: `scikit-learn` (nested models), `ViennaRNA` (true MFE), and any Ribo-seq tooling.
- Unify orchestration:
  - Ensure `scripts/run_all.py` covers every script needed to regenerate `sections/generated/validation_summary.tex` and the mechanistic-proxy fragments (`uplift_mfe_correlation`, `uplift_structure_deconfound`, `uplift_translation_rate_proxy`, `riboseq_pause_correlation`, `nested_models_extended`).
  - Add a **smoke mode** (small `--n` for Monte Carlo, small record limits for transcriptomes/recoding) that finishes in minutes and validates the pipeline end-to-end.
- Determinism:
  - Standardize RNG seeds across scripts; ensure caches record seed + analysis version in `.meta.json`.

**Tasks (machine-side / ops)**
- Prefer Linux on the A100 host (ViennaRNA, Ribo-seq tooling, and batch processing are smoother than Windows).
- Environment bootstrap (example strategy; adapt to your infra):
  - Create a clean Python env and install `requirements.txt`.
  - Install extras needed by mechanistic proxies:
    - `scikit-learn` (for `exp_nested_models_extended.py`, `exp_uplift_structure_deconfound.py`)
    - ViennaRNA Python bindings (`RNA` module) for `exp_uplift_mfe_correlation.py` / structure features
  - Optional: TeX toolchain (`latexmk` + TeX Live) if you want to build `main.pdf` on the server.
- Data staging:
  - Copy the full `data/` bundle to **local NVMe / scratch** (avoid network FS bottlenecks).
  - If needed, use a symlink so the repo still sees `./data`.
  - Validate checksums against `data/manifest.json` before running full jobs.

**Data required (minimum to reproduce current results)**
- `data/gc.prt` (NCBI translation tables)
- `data/refseq_hsapiens_mrna/` (human RefSeq mRNA bundle)
- `data/recoding_genbank/` (recoding GenBank bundle + derived `recoding_sites.jsonl`)
- `data/boundary_enrichment/` (if boundary-enrichment figures are part of the current paper build)

**Acceptance tests (must-pass on A100)**
- Smoke (fast, not paper-grade): run in a scratch clone or expect `sections/generated/` to be overwritten with quick outputs.
  - `python scripts/exp_genetic_code_decompiler.py --force`
  - `python scripts/exp_random_code_monte_carlo.py --n 20000 --seed 0 --chunk 2000 --force`
  - `mkdir -p data/_quick/smoke && python scripts/exp_recoding_sites.py --k 10 --max-files 20 --no-latex --out-jsonl data/_quick/smoke/recoding_sites.jsonl --out-summary-json data/_quick/smoke/recoding_sites_summary.json --force`
  - `python scripts/exp_out_of_sample_mu_star_ranking.py --k 10 --refseq-max-shards 1 --refseq-max-records 2000 --force`
- Full: one command that reproduces the full PDF and all generated fragments (exact command to be finalized once `run_all.py` is aligned).

**Acceptance tests (validation scripts)**
- Dataset presence (offline): `python scripts/validate_manifest_local_files.py`
- Generated fragments sanity: `python scripts/validate_generated_fragments.py --require-meta`
- Artifacts needed for DB/import pipelines: `python scripts/validate_artifacts.py`

### 2) Milestone M1 — Data expansion to make H2 a real replication claim

**Status**: ✅ COMPLETED (2026-01-13)

**Completion Notes**:
- Created `fetch_multispecies_cds.py` for downloading Tier-1 species from NCBI RefSeq
- Created `exp_cross_species_stop_context.py` for H2-1 cross-domain replication
- Downloaded 18/19 Tier-1 species (all except rice)
- **Meta-analysis results (UAA vs UGA)**:
  - k=3: d = -0.035 [-0.066, -0.004], I² = 93.2% (marginally significant)
  - k=5: d = -0.006 [-0.034, 0.021], I² = 90.9% (non-significant)
  - k=10: d = -0.030 [-0.065, 0.004], I² = 94.8% (non-significant)
  - k=20: d = -0.036 [-0.076, 0.004], I² = 96.3% (non-significant)
- High heterogeneity (I² > 90%) indicates species-specific effects; Uplift signal does not replicate uniformly across domains

**Objective**: Move from "human-only + small special cases" to "cross-domain replication with strict out-of-sample validation".

**Data to add (minimum useful set)**

| Dataset | Why we need it | Format (recommended) | Proposed location |
|---|---|---|---|
| Multi-species coding corpus (≥10 species per domain) | H2 replication + heterogeneity | FASTA(.gz) + minimal metadata JSON | `data/corpora/<domain>/<species>/` |
| Species translation tables (nonstandard codes) | stress-test μ\* + stop fine structure | `gc.prt` subset or per-species table JSON | `data/nonstandard/` |
| Curated recoding/readthrough events across taxa | increase positive-class n for “recoding vs terminal” | JSONL (site records + sequences) | `data/recoding_curated/` |
| tRNA gene sets per species (for tAI) | mechanism proxy at scale | GtRNAdb/tRNAscan outputs | `data/trna/<species>/` |
| Ribo-seq raw coverage (BigWig/BAM/FASTQ) for ≥2 studies | window-scale pausing tests | BigWig preferred for throughput | `data/riboseq/<study_id>/` |

**Practical sourcing notes (可操作建议)**
- For cross-domain coding corpora, prefer **annotated CDS FASTA** (not “longest ORF from mRNA”) for Bacteria/Archaea to avoid start-codon variability (GUG/UUG etc.) and ORF-calling artifacts.
- Start with code-1 species (standard code) to reduce translation-table confounds; record translation table IDs explicitly per dataset.
- “Curated recoding/readthrough” JSONL should minimally include: `species`, `event_type` (Sec/Pyl/readthrough/frameshift), `stop_codon`, `context_seq` (at least ±k window), coordinate/provenance fields, and any confidence label.

**Suggested Tier-1 species list (first pass; adjust as needed)**
- Eukarya: human, mouse, yeast, fly, worm, arabidopsis (choose those with good CDS annotations and (ideally) available Ribo-seq).
- Bacteria: *E. coli*, *B. subtilis*, plus 8–10 diverse phyla representatives with high-quality RefSeq annotations.
- Archaea: include at least one halophile, one methanogen, one thermophile (quality > novelty for the first replication pass).

**Data QA gates (must satisfy before entering analysis)**
- Sequence normalization: strict alphabet handling (DNA `T→U`), remove/flag ambiguous bases.
- ORF definition policy: document whether we use “longest ORF across frames” vs annotated CDS; keep consistent per dataset.
- Provenance: every dataset must have a version string + checksum recorded in `data/manifest.json` (or a new `data/manifest_v2.json` if schema changes).

**H2 replication experiments to run once data is in place**
- Cross-domain stop-context replication:
  - pre-register 1–2 primary endpoints (e.g., pairwise Δ of `U_after(k=10)` between stop classes) and run per species;
  - report effect sizes + CIs + heterogeneity (random-effects meta).
- Recoding vs terminal replication:
  - expand beyond human Sec to multi-taxa Sec (and Pyl/readthrough if curated);
  - evaluate out-of-sample AUC (train on subset of species, test on held-out species).

**Concrete experiment list (H2 workstream; “do even if it fails”)**

- **H2-1: Cross-domain stop-context replication at scale**
  - Data: multi-species CDS corpora (+ translation table id per species).
  - Endpoint: `U_after(s;k)` and `D(s;k)` for s∈{UAA,UAG,UGA}, k∈{3,5,10,20}.
  - Controls: composition matching (GC+dinuc); report both raw and matched.
  - Output: per-species JSON summary + meta-analysis fragment (extend `exp_corpus_panel.py` / manifest schema).
  - Failure mode: high heterogeneity or vanishing effect sizes → still publishable as “non-universality”.

- **H2-2: Leave-one-species-out (LOSO) generalization**
  - Data: same as H2-1.
  - Endpoint: sign-consistency + held-out effect size CI for the primary stop-pair contrast.
  - Failure mode: effect is domain-specific; still clarifies scope conditions.

- **H2-3: ORF policy sensitivity**
  - Compare: annotated CDS vs “best ORF across frames” (for datasets where both are available).
  - Goal: show H2 is not an ORF-calling artifact.

- **H2-4: Dicodon/codon-pair absorption quantified (turn the negative into a result)**
  - Null: dicodon-preserving shuffles at ORF scale (already exists as CR3B for a focused setting).
  - Deliverable: a table: “% of H2 signal explained by dicodon structure” per dataset/species.

- **H2-5: Position-shape replication (beyond mean windows)**
  - Use per-position curves (like CR4) across species to see if shape is conserved.
  - Failure mode: shape is not conserved → tells us window means are a lossy summary.

- **H2-6: Recoding expansion beyond human Sec**
  - Data: curated Sec/Pyl/readthrough events across taxa; ensure true positives with provenance.
  - Endpoint: out-of-sample AUC for recoding vs terminal using only pre-registered features.
  - Failure mode: no AUC gain → suggests current recoding dataset is special-case or confounded.

- **H2-7: Nonstandard code stress tests**
  - Data: organisms with alternative stop assignments (mitochondria/ciliates, etc.).
  - Endpoint: boundary-hit enrichment and stop fine-structure predictions under μ\*.
  - Failure mode: inconsistent mapping → sharp boundary conditions for the theory.

- **H2-8: Multi-resolution Fold_m sensitivity for H2 endpoints**
  - Recompute key endpoints for m∈{6,7,8,9}.
  - Goal: separate m=6-specific artifacts from stable effects.
  - Failure mode: only m=6 shows signal → still informative (but lowers biological generality).

- **H2-9: Negative controls that must stay null**
  - Random in-frame positions matched by codon identity/composition should not reproduce stop-specific contrasts.
  - A “null-of-null” suite is essential before trusting new big-data results.

- **H2-10: Stop-context response curves (k→∞ shape)**
  - Fit the saturating response model from `sections/appendices/05_statistical_tests.tex` (the `D(s;k)` curve).
  - Goal: compress multi-k behavior into interpretable parameters `(D_∞, κ)` and test cross-species stability.
  - Failure mode: unstable fits / species-specific κ → suggests window choice is biology-dependent.

- **H2-11: Hierarchical models with blocking (gene/study as random effects)**
  - Replace per-stop i.i.d. tests with mixed-effects models that block by gene and study.
  - Goal: ensure significance is not driven by a few long/highly expressed genes.

**Acceptance criteria (H2 “supported” at next checkpoint)**
- At least one endpoint meets: consistent direction in ≥2 domains, meta-analytic CI excludes 0, and effect size is not negligible (threshold to be pre-registered).
- Confound-controlled robustness: endpoint remains when conditioning on GC+dinuc and when adding dicodon/codon-pair controls (either via matched nulls or regression residualization).

### 3) Milestone M2 — Stronger null families (address the dicodon absorption directly)

**Status**: ✅ COMPLETED (2026-01-13)

**Completion Notes**:
- Created `exp_dicodon_absorption_analysis.py` for quantifying dicodon absorption
- Analyzed 18 species with Ridge regression: E[U | dicodon frequencies]
- **Key Results**:
  - Dicodon R² ranges from 0.27 (arabidopsis) to 1.00 (several prokaryotes)
  - Mean signal absorbed: 33% across all species
  - Prokaryotes: higher R² (0.58–1.00), higher absorption (0–98%)
  - Eukaryotes: lower R² (0.27–0.72), lower absorption (0–52%)
  - Residual effect sizes (d_resid) are smaller but non-zero in several species

**Objective**: Turn the current failure mode ("absorbed by ORF-level dicodon structure") into a first-class analysis result rather than a post-hoc caveat.

**Experiments**
- Dicodon-preserving controls at the right scale:
  - keep ORF-level dicodon counts fixed while shuffling within constraints;
  - re-evaluate stop-context and recoding contrasts under this null.
- Residual-Uplift analysis:
  - compute `U_resid = U - E[U | GC, dinuc, dicodon]` (model choice pre-registered);
  - re-run H2 endpoints on `U_resid` to test whether any signal remains.

**Acceptance tests**
- The dicodon-preserving null pipeline runs deterministically and reproduces identical summaries given fixed seeds.
- The report clearly separates "signal explained by dicodon structure" vs "signal beyond dicodon".

### 4) Milestone M3 — Mechanistic bridge v2 (if we still want to pursue H3)

**Objective**: Replace GC-mediated proxies with composition-conditioned mechanistic measurements, and test at biologically relevant window scales.

**Data required**
- ViennaRNA enabled environment for large-scale structure computation (CPU-parallel).
- Raw Ribo-seq coverage with known P-site offsets (or a standardized pipeline to infer them).

**Experiments**
- Structure:
  - move from raw MFE to **MFE z-score** (real window MFE vs composition-matched shuffled windows) to reduce GC mediation;
  - test whether `U` or `U_resid` predicts zMFE at 30–120nt windows.
- Translation dynamics:
  - compute window-level pause metrics from raw Ribo-seq (not only precompiled codon-level scores);
  - test whether `U`/`U_resid` predicts pausing after controlling for GC/dinuc/codon identity and expression proxies.

**Concrete experiment list (H3 workstream; “do even if it fails”)**

- **H3-1: zMFE and ensemble features (composition-conditioned structure)**
  - Replace raw MFE correlation with:
    - zMFE (real MFE vs matched-shuffle MFE distribution),
    - ensemble diversity, pairing probability summaries, local accessibility (ViennaRNA).
  - Endpoint: partial correlation / ΔR² of these features predicted by `U` or `U_resid`.

- **H3-2: Structure at the right scale**
  - Evaluate 30–120nt windows (and align to biological features: stop + downstream).
  - Failure mode: still null after z-scoring → strong evidence against “structure mediation”.

- **H3-3: Ribo-seq from raw coverage (window-scale pausing)**
  - Data: at least 2 independent human studies (BigWig/BAM); ideally add yeast/bacteria.
  - Compute: window pause indices around stops; replicate across studies.
  - Endpoint: association of pausing with `U_after` / zMFE / composition controls.

- **H3-4: Termination-specific pausing signature**
  - Focus on windows centered at terminal stop; compare stop classes.
  - Ask: does `U_after` predict the *shape* or *magnitude* of the stop-proximal occupancy peak?

- **H3-5: Expanded translation-rate proxies**
  - Beyond tAI: CAI/ncCAI, codon-pair bias, species-specific tRNA supply models.
  - Endpoint: does `U_resid` add predictive power beyond known codon-usage metrics?
  - Failure mode: `U` collapses to known metrics → reposition as reparameterization/feature.

- **H3-6: Mechanistic mediation analysis (if any association appears)**
  - If we see `U → zMFE` and `zMFE → pausing/readthrough`, test mediation models.
  - This is exploratory unless pre-registered.

- **H3-7: Structure probing (SHAPE/DMS) cross-check (high value if data exists)**
  - Data: public in vivo probing tracks (DMS/SHAPE-MaP) aligned to transcripts.
  - Endpoint: does `U`/`U_resid` correlate with measured accessibility/reactivity beyond composition?
  - Failure mode: null result strengthens the claim that uplift is not a structural proxy.

- **H3-8: GPU-optional deep model probes (high-risk / exploratory)**
  - Use an A100 host to run pretrained nucleotide language models / structure predictors on windows.
  - Test whether `U` predicts model-derived structure/translation embeddings, and whether `U` adds predictive power for pausing/readthrough beyond embeddings.
  - Failure mode: redundancy (U adds nothing) is still informative: uplift behaves like a reparameterization of common sequence features.

**Compute note**
- Even on an A100 host, most of the above is **CPU/IO-bound** (FASTA scanning, ViennaRNA folding, BigWig processing). The main advantage of the A100 box is typically: more cores, more RAM, and faster local storage; GPU becomes relevant only if we add deep-learning structure/translation predictors later.

**Decision rule**
- If H3 remains null after these upgraded tests, freeze H3 as “not supported” and keep the framework positioned as descriptive/structural (avoid mechanism over-claiming).

### 5) Milestone M4 — Causal test design (wet-lab or cell-free; parallel track)

**Objective**: If we want a mechanistic/causal story, the only clean route is a controlled synthetic library where GC/structure are matched and Uplift is the manipulated variable.

**Design sketch**
- Construct sets of sequences with:
  - matched amino-acid sequence (synonymous design) or matched composition + predicted structure;
  - stratified Uplift bins (≥5 strata across a wide dynamic range).
- Assay: direct readthrough/recoding measurement (reporter or cell-free translation), with SECIS dependence as a control for Sec.

**Acceptance criteria**
- Causal separation: changing Uplift while holding GC/structure fixed produces a reproducible change in readthrough/recoding rate.

**Executable construct-library support (already in repo)**
- Candidate contexts are produced by the RefSeq merge pipeline as JSONL:
  - `data/refseq_hsapiens_mrna/stop_context_candidates.jsonl` (includes composition-matched pairs)
- Convert candidate contexts to assay-ready construct JSONL:
  - `python scripts/exp_assay_construct_library.py --candidate-set reporter_v1 --group-labels matched_after_high,matched_after_low --k 10 --max-per-stop 10`
- Output (default): `data/assays/readthrough_constructs.jsonl` (idempotent construct_key suitable for DB upserts)

---

## Reproducibility & Acceptance Tests

### Environment

```
Python: 3.11+
Key packages:
  - core: numpy, scipy, pandas, matplotlib
  - extras: scikit-learn (nested models), viennarna (true MFE), pg8000 (optional DB)
```

### Setup (fresh machine)

Core Python deps:

```bash
cd docs/papers/biology/2025_arithmetic_origin_genetic_code_hpa_omega
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Extras (mechanistic proxy scripts):
- `scikit-learn`: install via `pip install scikit-learn`
- ViennaRNA Python bindings (`import RNA`):
  - recommended: install via Conda (e.g., `conda install -c bioconda viennarna`)
  - fallback: system packages / local build (cluster-dependent)

Optional (build PDF on server):
- `latexmk` + TeX Live toolchain (or use a container with TeX preinstalled)

### Minimal “smoke” run (recommended on a fresh A100 box)

Goal: validate Python env + data layout + caching + LaTeX fragment generation in minutes.
Note: this run is **not paper-grade** (reduced compute / subset scans) and may overwrite `sections/generated/`; run it in a scratch clone/worktree if you need to preserve current fragments.

```bash
cd docs/papers/biology/2025_arithmetic_origin_genetic_code_hpa_omega
python scripts/exp_genetic_code_decompiler.py --force
python scripts/exp_control_objective_robustness.py --force
python scripts/exp_random_code_monte_carlo.py --n 20000 --seed 0 --chunk 2000 --force
mkdir -p data/_quick/smoke
python scripts/exp_recoding_sites.py --k 10 --max-files 20 --no-latex --out-jsonl data/_quick/smoke/recoding_sites.jsonl --out-summary-json data/_quick/smoke/recoding_sites_summary.json --force
python scripts/exp_out_of_sample_mu_star_ranking.py --k 10 --refseq-max-shards 1 --refseq-max-records 2000 --force
```

Optional: validate “extras” dependencies (ViennaRNA + scikit-learn) are actually usable:

```bash
python scripts/exp_riboseq_pause_analysis.py
python scripts/exp_uplift_translation_rate_proxy.py --k 10 --n-per-stop 100 --seed 0 --force
python scripts/exp_uplift_mfe_correlation.py --k 10 --n-per-stop 50 --seed 0 --force
python scripts/exp_uplift_structure_deconfound.py --window-sizes 30,60 --n-samples 120 --seed 0 --force
python scripts/exp_nested_models_extended.py --k 10 --n-perm 10 --seed 0 --force
```

### Full reproduction (current baseline)

```bash
cd docs/papers/biology/2025_arithmetic_origin_genetic_code_hpa_omega
python scripts/run_all.py --no-download --force
```

Optional: build `main.pdf` (requires TeX toolchain):

```bash
python scripts/run_all.py --no-download --force --pdf
```

### Expected artifacts (sanity checklist)

After a full run, the following should exist (non-empty) in `sections/generated/`.
Note: until Milestone M0 aligns `scripts/run_all.py` with all mechanistic scripts, some items may require running the corresponding scripts directly (see the optional “extras” block above).
- `control_objective_brief.tex`, `control_objective_robustness.tex`
- `random_code_monte_carlo_summary.tex`
- `validation_summary.tex`
- `uplift_translation_rate_proxy.tex`, `uplift_mfe_correlation.tex`, `uplift_structure_deconfound.tex`, `riboseq_pause_correlation.tex`, `nested_models_extended_summary.tex`

### Data Requirements

- Genetic code tables: `data/gc.prt`
- Human RefSeq mRNA: `data/refseq_hsapiens_mrna/`
- Recoding GenBank bundle + derived sites: `data/recoding_genbank/`
- Release manifest/checksums: `data/manifest.json`

If you need to rehydrate the full data bundle (network required):

```bash
python scripts/fetch_datasets.py --dataset all
```

If the host has TLS certificate issues (rare on Linux; common on Windows):

```bash
python scripts/fetch_datasets.py --dataset all --insecure
```

### Output

All generated LaTeX fragments: `sections/generated/*.tex`

---

## Commit History (This Session)

| Commit | Description |
|--------|-------------|
| `4f0c2a9a` | H2-5 Position-shape replication (weak cross-species r=0.14) |
| `5143951c` | H2-2 LOSO generalization test (50% sign consistency) |
| `f062f32f` | M2 dicodon absorption analysis + 18-species H2 replication |
| `068c0253` | M1 cross-species meta-analysis methodology in paper |
| `0fca1ea3` | M1 multi-species infrastructure + preliminary analysis |
| `a43e59cc` | M0 baseline reproduction on A100 cluster (2026-01-13) |
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

*Last updated: 2026-01-14 (M1+M2 completed)*  
*Repository: the-omega*  
*Path: `docs/papers/biology/2025_arithmetic_origin_genetic_code_hpa_omega/EXPERIMENT_ANALYSIS.md`*
