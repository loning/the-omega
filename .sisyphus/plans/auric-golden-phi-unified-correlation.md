# 黄金比例驱动扫描—投影生成：统一“相关”的一轮推进工作计划

## TL;DR

本轮的可发表新增结论聚焦于一个目前论文中尚未以“定理”方式显式给出的统一点：

> 将有限模轴束（Dirichlet/同余）上的 Chebotarev 型误差指数
> $$\eta_m:=\max_{\chi\neq 1}\frac{\rho(M_{m,\chi})}{\rho(M_{m,1})}$$
> 识别为**提升系统（状态 \(\times\) 同余纤维）中“同余纤维可观测量”的真实时间相关衰减率**，从而把
> “prime-orbit 计数误差的指数尺度”与“时间相关/混合的指数尺度”统一为同一谱半径比。

该结论将以：
1) `sections/08_projection_ontology_mathematics/08_projection_ontology_mathematics_part04.tex` 中新增定义与定理（含证明）；
2) 一个可复现脚本生成的数值证据（自动写入 `sections/generated/*.tex`）
的形式落地，并完全纳入现有 `scripts/run_all.py` 流水线。

---

## Context（已确认的现状）

### 论文工程入口与流水线

- 论文入口：`docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/main.tex`
- 快速编译入口：`docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/main_fast.tex`
- 一键复现：`python3 scripts/run_all.py`（见 `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/README.md`）

### 已存在但尚未“统一成定理”的关键模块

- 状态层时间相关（谱隙口径）：
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections/08_projection_ontology_mathematics/08_projection_ontology_mathematics_part04.tex`
  - 命题 `prop:pom-time-corr-gap` 给出有限维传输算子谱隙 \(\Lambda/\lambda_1\) 控制的相关衰减。
- 同余轴束的 Hilbert/角色块对角化（谱论结构）：
  - 同文件中的命题 `prop:pom-profinite-artin-hilbert` 给出 \(\mathcal{M}_u\) 在 \(\CC^V\otimes L^2(G_\infty)\) 上的角色直和分解，并定义各扭曲块 \(M_\chi(u)\)。
- 同余分层的 Chebotarev 型误差指数 \(\rho/\lambda\) 与混合尺度 \(\tau_{\mathrm{mix}}\)：
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections/09_zeta_finite_part/09_zeta_finite_04_03_subsec_arity-dirichlet-mertens-tensor_a.tex`
  - 注记 `cor:arity-335-collision-mixing-scale` 已将 \(\tau_{\mathrm{mix}}:=1/(-\log(\rho/\lambda))\) 作为“主相关长度尺度”提出，但尚缺一个将其解释为“同余纤维上的真实时间相关”之定理化桥接。
- 实验部分中“差异度→TV/KL 证书”已经存在且不属于本轮新增点：
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections/12_experiments.tex`（定理 `thm:tv-certificate-hist` 等）。

---

## Work Objectives（本轮目标）

### Core Objective

在“有限模同余轴束”口径下，把 **Chebotarev 扭曲误差指数** \(\eta_m\) 与 **提升系统同余纤维可观测量的时间相关指数衰减率** 证明为同一对象，并给出其在 `real-input 40-state kernel` 上的可复现数值核验。

### Concrete Deliverables

- 在 `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections/08_projection_ontology_mathematics/08_projection_ontology_mathematics_part04.tex`：
  - 新增 1 个定义（提升系统的平衡测度/同余纤维可观测量空间）；
  - 新增 1 个定理（\(\eta_m\) 控制同余纤维时间相关的指数衰减；并给出字符分解的显式形式）；
  - 给出完整证明（仅用有限群 Fourier 分解 + Perron–Frobenius/Parry 归一化）。
- 新增 1 个可复现脚本：
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/scripts/exp_real_input_40_lifted_chain_correlation.py`
  - 生成：
    - `artifacts/export/real_input_40_lifted_chain_correlation.json`
    - `sections/generated/tab_real_input_40_lifted_chain_eta_envelope.tex`
- 更新流水线：
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/scripts/run_all.py` 增加该脚本任务。

### Guardrails（必须避免）

- 不扩展到非交换群/非阿贝尔覆盖；不引入新框架。
- 不复述已存在的状态层相关衰减定理（`prop:pom-time-corr-gap`）；必须明确“同余纤维相关”是不同对象。
- 不把数值证据写成“人工目视确认”；全部证据必须可由脚本输出的数值不等式/证书字段审计。

---

## Verification Strategy

所有验收标准均要求执行代理可直接运行命令完成核验。

### Build/Run Commands

```bash
# 在论文目录下
python3 scripts/run_all.py

latexmk -pdfxe -interaction=nonstopmode -halt-on-error -file-line-error main_fast.tex
```

### Evidence Artifacts（新增）

- JSON：`artifacts/export/real_input_40_lifted_chain_correlation.json`
  - 必须包含字段：
    - `modulus_spec`（例如 (3,3,5) 与 third axis 选择）
    - `eta_m`（最坏扭曲比值）
    - `corr_samples`（n→Corr(n) 采样）
    - `envelope_certificate`（max ratio 等审计量）
- TeX：`sections/generated/tab_real_input_40_lifted_chain_eta_envelope.tex`
  - 表格中至少包含：`eta_m`、`max_{1<=n<=N} |Corr(n)|/eta_m^n`、达到位置。

---

## TODOs（按依赖顺序；实现代理执行）

### 1) 定理化：同余纤维的相关衰减率 = 最坏扭曲比值

**What to do**

- 在 `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections/08_projection_ontology_mathematics/08_projection_ontology_mathematics_part04.tex` 中，紧接命题 `prop:pom-profinite-artin-hilbert` 之后插入：
  - 定义：有限层 \(G_m\) 上的提升系统 \(\Sigma\times G_m\)（或 \(V\times G_m\)）与平衡测度 \(\widetilde\mu_m := \mu_{\mathrm{Parry}}\otimes \mathrm{Haar}_{G_m}\)；
  - 定义：同余纤维零均值可观测量空间 \(L^2_0(G_m)\)（嵌入为仅依赖纤维坐标的函数）；
  - 定理（建议名）：
    - **“同余纤维相关统一定理”**：对任意 \(f\in L^2_0(G_m)\)，令 \(C_f(n):=\mathbb{E}_{\widetilde\mu_m}[f(g_0)\,f(g_n)]\)。则存在常数 \(\le \|f\|_2^2\) 使
      $$|C_f(n)|\le \|f\|_2^2\,\eta_m^n,\qquad \eta_m:=\max_{\chi\neq 1}\frac{\rho(M_{m,\chi})}{\rho(M_{m,1})}.$$
    - 并给出字符分解的显式表达（将 \(f\) 展开为角色基，相关函数分解为各 \(\chi\)-块的谱贡献），从而把“Chebotarev 的误差指数”解释为“纤维相关的真实衰减率”。
- 证明要点（强制）：
  - 复用 `prop:pom-profinite-artin-hilbert` 的角色块对角化；
  - 明确指出：状态层相关由 \(\Lambda/\lambda_1\) 控制；纤维层相关由 \(\eta_m\) 控制；两者可相差数量级。

**References（必须在任务中显式引用以避免口径漂移）**

- 结构基座（角色直和/块对角化）：
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections/08_projection_ontology_mathematics/08_projection_ontology_mathematics_part04.tex`（命题 `prop:pom-profinite-artin-hilbert`）
- 状态层相关基座（用于对比，避免混淆）：
  - 同文件（命题 `prop:pom-time-corr-gap`）
- 同余扭曲误差指数口径（与 Chebotarev 主项/误差对齐）：
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections/07_emergent_arithmetic/07_emergent_arithmetic_05_sec_A_kernel_compare_main.tex`（定理 `thm:kernel-chebotarev-exp`）
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections/09_zeta_finite_part/09_zeta_finite_04_03_subsec_arity-dirichlet-mertens-tensor_a.tex`（`tau_mix` 的定义/使用）

**Acceptance Criteria（必须可执行）**

- `latexmk -pdfxe -interaction=nonstopmode -halt-on-error -file-line-error main_fast.tex` 成功
- 新增定理与定义均可被 `\ref{}` 无警告解析（执行代理在编译日志中核验无 “undefined references”）

---

### 2) 证据脚本：提升链同余纤维自相关的 \(\eta_m\) 包络证书

**What to do**

- 新增脚本：`docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/scripts/exp_real_input_40_lifted_chain_correlation.py`
- 功能要求（最小闭环）：
  - 读取/复用真实输入 40 状态核构造（状态集 + kernel_map）：
    - 优先复用 `scripts/exp_sync_kernel_real_input_40.py` 中的构造与 `build_weighted_matrix`；
  - 选择一个已在论文中使用的模轴束配置作为默认：推荐 `((3,3,5))` 且第三轴为 `N2 mod 5`（与 `tau_mix(3,3,5)` 的既有口径一致；脚本需可参数化但默认即为该设置）；
  - 构造提升链的同余纤维可观测量（建议两类至少其一）：
    - 指示函数：`f_r(g)=1_{g=r}-1/|G|`；
    - 或字符函数：`f_\chi(g)=\chi(g)`（零均值通道）
  - 计算 \(C_f(n)\)（建议在平衡分布下以矩阵幂/特征分解精确计算，而非蒙特卡洛；以保证“零随机性可审计”）：
    - 利用角色块对角化：在 \(\chi\)-通道上相当于分析归一化扭曲矩阵 \(M_{m,\chi}/\lambda\) 的幂作用。
  - 输出证书：
    - `eta_m`（由扫描/既有函数直接给出）
    - `max_ratio := max_{1<=n<=N} |C_f(n)| / eta_m^n`
    - 生成 LaTeX 表：`sections/generated/tab_real_input_40_lifted_chain_eta_envelope.tex`

**Implementation References（脚本侧复用点）**

- Parry 平衡测度与 PF 向量工具：
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/scripts/exp_real_input_40_time_correlation.py`（`_pick_pf_eigpair`, `parry_markov`）
- 40 状态核的带权矩阵构造：
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/scripts/exp_sync_kernel_real_input_40.py`（`build_weighted_matrix`）
- 既有 \(\tau_{\mathrm{corr}}\) vs \(\tau_{\mathrm{mix}}\) 对照脚本（可借用输入参数与输出风格）：
  - `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/scripts/exp_real_input_40_tau_corr_vs_tau_mix.py`

**Acceptance Criteria（必须可执行）**

- `python3 scripts/exp_real_input_40_lifted_chain_correlation.py` 退出码为 0
- 生成文件存在：
  - `artifacts/export/real_input_40_lifted_chain_correlation.json`
  - `sections/generated/tab_real_input_40_lifted_chain_eta_envelope.tex`
- JSON 结构可审计：

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path('artifacts/export/real_input_40_lifted_chain_correlation.json')
d = json.loads(p.read_text())
for k in ['eta_m','corr_samples','envelope_certificate','modulus_spec']:
  assert k in d, k
assert d['eta_m'] > 0 and d['eta_m'] < 1.0
PY
```

---

### 3) 将新增证据纳入一键流水线

**What to do**

- 在 `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/scripts/run_all.py` 中新增任务条目：
  - name 建议：`real_input_40_lifted_chain_correlation`
  - outputs：上述 JSON + TeX 片段

**Acceptance Criteria**

- `python3 scripts/run_all.py` 能够完整运行（执行代理以退出码与产物存在性核验）。

---

## Self-Review Checklist（执行前的计划自检）

- 新增定理是否明确区分：状态层相关 `tau_corr` vs 同余纤维相关 `tau_mix`。
- 新增脚本是否避免蒙特卡洛随机性（或显式固定 seed 并输出 seed/版本）。
- 所有新增 LaTeX `\label{}` 是否唯一且命名一致。
- 新增引用是否已在 `sections/99_bibliography` 的 bib 中存在；若缺失，需补齐条目但不引入与定理无关的叙述。
