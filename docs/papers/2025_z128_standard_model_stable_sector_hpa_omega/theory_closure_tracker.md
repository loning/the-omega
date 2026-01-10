# z128 理论闭合追踪（Tick+CAP，自包含）

本文件用于追踪 `docs/papers/2025_z128_standard_model_stable_sector_hpa_omega` 内部的“理论闭合”进度：哪些概念已在 **数学层（Tick+CAP）** 与 **物理层（可操作定义/接口）** 之间完成一致的对应，哪些仍处于部分闭合或待闭合状态。

## 使用约定

- **闭合状态（建议维护）**
  - `[x]`：已闭合（给出定义/闭合输出 + 关键方程/命题 + 指向明确位置）
  - `[~]`：部分闭合（定义明确但推导/审计/匹配仍缺）
  - `[ ]`：待闭合（缺定义或缺闭合输出/接口）
- **四层一致性（建议每项都标注）**
  - **Iface**：可操作/接口层（实验/协议可观测）
  - **CAP**：在有限候选族上的 CAP 闭合（选择/最小化/词典）
  - **Math**：数学层推导（不变性/定理/变分）
  - **Audit/Prot**：审计/复现实验/数据协议

## 跨论文模板对齐清单（Phase 0）

本节记录在进行结构重排/术语对齐时应优先参考的“模板文件”，用于确保层纪律与符号写法与仓库内其它论文一致；它不引入额外公理，也不改变 z128 的最小输入集（tick + CAP）。

- **层纪律与 not used in proofs 写法**
  - `docs/papers/2025_motive_at_infinity_holographic_scanning_principle/sections/02_audit_layers.tex`
  - `docs/papers/2025_stairway_to_infinity_holographic_renormalization_flow/sections/02_layers_axioms.tex`
  - `docs/papers/2025_ramanujan_holographic_scanning_principle_hpa_omega/sections/02_layers_axioms.tex`
- **Wish / Motive 的定义与目标函数模板**
  - `docs/papers/2025_protocol_stable_period_data_computational_teleology/sections/03_wish_protocol_stable_period_data.tex`
  - `docs/papers/2025_protocol_stable_period_data_computational_teleology/sections/05_selection_principle.tex`
  - `docs/papers/2025_protocol_stable_period_data_computational_teleology/sections/06_variational_dynamics.tex`
  - `docs/papers/2025_motive_at_infinity_holographic_scanning_principle/sections/03_periods_motives_wishes.tex`
  - `docs/papers/2025_motive_at_infinity_holographic_scanning_principle/sections/07_selection_principle.tex`
- **$\varphi$-$\pi$-$\mathrm{e}$ 折叠总论与极点障碍模板**
  - `docs/papers/2025_resolution_folding_phi_pi_e_hpa_omega/sections/06_resolution_folding_map.tex`
  - `docs/papers/2025_resolution_folding_phi_pi_e_hpa_omega/sections/04_pi_constraint_discrete_monodromy.tex`
  - `docs/papers/2025_resolution_folding_phi_pi_e_hpa_omega/sections/05_e_constraint_abel_zeta_pole_barrier.tex`
- **Abel / finite part / trace-formula 刚性模板（用于 e-通道与解析稳定的统一口径）**
  - `docs/papers/2025_holographic_hilbert_universe_hpa_omega/sections/appendices/03_abel_finite_part_notes.tex`
  - `docs/papers/2025_riemann_ground_state_hpa_omega/sections/appendices/03_orbit_calculus_abel_fp.tex`
  - `docs/papers/2025_riemann_ground_state_hpa_omega/sections/05_trace_formula_rigidity.tex`
  - `docs/papers/2025_holographic_hilbert_universe_hpa_omega/sections/09_trace_formula_rigidity.tex`

## 闭合依赖图（模块级）

```mermaid
flowchart TD
  A["Tick + 协议原语"] --> B["等价语义与不变性词典"]
  B --> C["CAP-闭合的连续代表作用量"]
  C --> D["变分场方程（Einstein/YM/chi）"]
  B --> E["热力学词典（熵/温度/自由能）"]
  D --> F["overhead/chi -> lapse -> g00 -> 弱场/Poisson"]
  F --> G["chi 重建协议（从数据到 chi(x)）"]
  G --> K["协议→连续场误差控制（收敛界/误差预算）"]
  F --> K
  B --> H0["状态泛函/GNS 背景（记号对齐）"]
  H0 --> H["量子测量接口（POVM/仪器/Born）"]
  H --> H2["波粒二象性/延迟选择（读出接口解释）"]
  B --> I["RG：分辨率坐标 r 的耦合流"]
  I --> J["宇宙学：分辨率流/容量增长/能量预算拟合"]
```

说明：上图是**依赖关系**而非叙事顺序；叙事可从 `B`（等价语义+频率优先词典）开始，也可从 `A`（协议/读出）开始。

## 已引入的“自包含闭合模块”（Part F 主文 + 附录）

- [x] **时间箭头（指数半群/Abel-first）**：`Part F.0`  
  - 位置：`sections/F_00_arrow_of_time_semigroup.tex`（`\label{app:arrow_of_time_semigroup_notes}`）
  - 要点：指数半群骨架、遗忘常数、与 Abel-first/pole-barrier 语言对齐；连续半群的 Cauchy 方程解采用标准结果并给出引用；作为后续单调性与不可逆证书的最小数学核。
- [x] **等价语义与频率优先词典**：`Part F.1`  
  - 位置：`sections/F_10_equivalence_semantics.tex`（`\label{app:equivalence_semantics}`）
  - 要点：物理对象=等价类；物理量=不变泛函；频率作为优先派生量；力/曲率/熵等作为不变性或闭合输出。
- [x] **CAP-闭合连续代表作用量**：`Part F.2`  
  - 位置：`sections/F_20_cap_continuum_action_closure.tex`（`\label{app:cap_continuum_action_closure}`）
  - 要点：在有限候选族上闭合局域协变不变量项，输出最小骨架 `S_eff`。
- [x] **变分场方程（Einstein/YM/chi）**：`Part F.2`  
  - 位置：`sections/F_21_variational_field_equations.tex`（`\label{app:variational_field_equations}`）
  - 要点：由 `S_eff` 推出场方程、守恒与弱场模板。
- [x] **热力学（从等价/粗粒化到熵/温度/自由能）**：`appendix 27`  
  - 位置：`sections/appendices/27_thermodynamics_from_equivalence.tex`（`\label{app:thermodynamics_from_equivalence}`）
  - 要点：熵=计数；温度=频率共轭尺度；CAP=自由能原则；三定律；熵力与引力词典对齐。
- [x] **overhead/chi -> 引力闭合链**：`Part F.4`  
  - 位置：`sections/F_40_overhead_to_gravity_closure.tex`（`\label{app:overhead_to_gravity_closure}`）
  - 要点：$\kappa \to \chi \to N \to g_{00} \to \Phi$；弱场下 $\rho_{\mathrm{eff}} \propto -\Delta \chi$；$\gamma$ 拟合模板。
- [x] **chi 重建协议**：`Part F.4`  
  - 位置：`sections/F_41_chi_reconstruction_protocol.tex`（`\label{app:chi_reconstruction_protocol}`）
  - 要点：Hilbert 分箱→窗口词→折叠统计→$\chi(x)$ 重建→测试与拟合。
- [x] **协议层→连续场误差控制**：`appendix 33`  
  - 位置：`sections/appendices/33_protocol_to_continuum_error_control.tex`（`\label{app:protocol_to_continuum_error_control}`）
  - 要点：误差度量与分解；集中界→log 误差传播；差分算子截断误差与噪声放大；$\gamma$ 的 WLS 方差与 $\rho_{\mathrm{eff}}/\Phi$ 的误差预算。
- [x] **量子测量与 Born 闭合**：`appendix 30`  
  - 位置：`sections/appendices/30_quantum_measurement_born.tex`（`\label{app:quantum_measurement_born}`）
  - 要点：POVM/仪器；Born 规则两条闭合路线（计数模板与 Gleason–Busch 唯一性）。
- [x] **状态泛函/GNS 背景（记号对齐；不计为新增原语）**：`appendix 30c`  
  - 位置：`sections/appendices/30c_state_gns_background.tex`（`\label{app:state_gns_background}`）
  - 要点：状态 $\omega$ 作为正且归一的线性泛函；GNS 表示给出 $\omega(A)=\langle\Omega|\pi(A)\Omega\rangle$；并将 $P(E)=\omega(E)$ 与 $P=\Tr(\rho E)$ 的等价关系写成纯数学口径，用于与本论文的 POVM/Born 写法对齐。
- [x] **波粒二象性/延迟选择/量子擦除（接口解释）**：`appendix 30b`  
  - 位置：`sections/appendices/30b_wave_particle_delayed_choice.tex`（`\label{app:wave_particle_delayed_choice}`）
  - 要点：以 Born 概率的交叉项/去相干混合（`lem:z128_interference_vs_mixture`）为最小代数核，给出互补性界 $V^2+D^2\le 1$、Mach–Zehnder delayed-choice、delayed-choice quantum eraser 与 Wheeler “Great Smoky Dragon” 的可审计口径，并与 Q 输入包对齐（`prop:qcomp_implies_qwave_weak`）。
- [x] **RG：分辨率坐标 r 的耦合流**：`appendix 31`  
  - 位置：`sections/appendices/31_running_couplings_resolution_flow.tex`（`\label{app:running_couplings_resolution_flow}`）
  - 要点：$\mu(r)=\mu_0\varphi^r$ 与链式法则；QED/QCD 一环；阈值匹配的离散解释；并把“$\Lambda$ 方案缩放 $\Leftrightarrow r$ 平移”提升为自包含引理（`\label{lem:lambda_rescaling_shift_r}`）。
- [x] **宇宙学：分辨率流与能量预算接口**：`appendix 32`  
  - 位置：`sections/appendices/32_cosmology_resolution_flow.tex`（`\label{app:cosmology_resolution_flow}`，`\label{ass:occupancy_energy_z128}`）
  - 要点：big bang 作为分辨率初始化；inflation=稳定容量增长；隐藏/稳定份额；能量预算部分以显式接口假设（占据计数）给出，使用 Planck-2018 的 $\Omega_{\mathrm{b},0}$ 作为紧凑目标，并提供可复现拟合脚本与图；离散匹配采用 log-mismatch 且 Voronoi 边界为几何均值（`\label{lem:log_voronoi_geometric_mean}`）；脚本同时生成 summary/stability 片段用于审计与敏感性口径统一。
- [x] **散射时间延迟的统一闭合（相位/频率/WS/红移/GR 参考）**：`appendix 34`  
  - 位置：`sections/appendices/34_unified_delay_closure.tex`（`\label{app:time_mass_delay}`，`\label{app:time_mass_delay_reference}`）
  - 要点：相位-频率-延迟统一接口；Wigner--Smith 延迟（含 trace/logdet 与校准/损耗处理）；delay→$\kappa$→lapse→redshift/Shapiro 的一致词典；相移/截面与时延同源的接口注记。

## 概念级闭合矩阵（频率优先）

下表只做“定位与状态”追踪；具体定义/公式以对应附录/章节为准。

| 概念/物理量 | 数学对象/闭合输出（概要） | 主依赖 | 位置（LaTeX label） | 状态 |
|---|---|---|---|---|
| 时间（time） | tick 差分 $\Delta t$ | Iface/Math | `sec:tick_calculus`（主文） | [x] |
| 相位/频率（phase/frequency） | $\omega=\Delta\theta/\Delta t$ 等价定义族 | Iface/Math | `def:frequency_from_phase`, `rem:frequency_alt_definitions` | [x] |
| 等价语义（objects/observables） | 物理对象=等价类；可观测=不变泛函 | Math | `subsec:equivalence_physical_objects`, `subsec:equivalence_relations_minimal` | [x] |
| 曲率（curvature） | 回路/holonomy 的不变响应 | Math | `subsec:curvature_as_loops` | [x] |
| 力（force） | 响应/梯度/变分（不变性下） | Math/CAP | `subsec:force_as_response` | [x] |
| 连续代表作用量 $S_{\mathrm{eff}}$ | CAP 在候选族中选最小骨架 | CAP/Math | `prop:cap_minimal_action_skeleton` | [x] |
| Einstein 方程 | $G_{\mu\nu}=8\pi G\,T^{\mathrm{tot}}_{\mu\nu}$ | Math | `thm:einstein_equation_total_stress` | [x] |
| Yang–Mills 方程 | $D_\mu F^{\mu\nu}=J^\nu$（模板） | Math | `prop:ym_equation` | [x] |
| $\chi$ 方程 | 标量/信息项的 EOM（模板） | Math | `prop:chi_eom` | [x] |
| 守恒/红移 | $\nabla_\mu T^{\mu\nu}_{\mathrm{tot}}=0$ + 频率词典 | Math/Iface | `eq:total_stress_conservation`, `subsec:conservation_redshift` | [x] |
| 弱场 Poisson | $\Delta\Phi \propto \rho_{\mathrm{eff}}$ | Math | `subsec:weak_field_poisson`, `subsec:z128_poisson_template` | [x] |
| overhead→引力 | $\chi\to N\to g_{00}\to\Phi$ | CAP/Math/Iface | `app:overhead_to_gravity_closure` | [x] |
| $\rho_{\mathrm{eff}}$ | $\rho_{\mathrm{eff}}\propto-\Delta\chi$ | Math/Iface | `eq:z128_rho_eff_from_chi` | [x] |
| 误差控制（协议→连续场） | 误差分解 + 收敛/稳定性界 + 误差传播预算 | Iface/Math/Audit/Prot | `app:protocol_to_continuum_error_control` | [x] |
| 熵（entropy） | 粗粒化计数/通道容量 | Math/CAP | `eq:counting_entropy` | [x] |
| 温度（temperature） | 频率共轭尺度 | Iface/Math | `def:temperature_conjugate` | [x] |
| CAP 自由能原则 | 以自由能形式重述 CAP 选择 | CAP | `prop:cap_free_energy_closure` | [x] |
| Born 概率 | $P_k=\mathrm{Tr}(\rho E_k)$ | Iface/Math | `eq:z128_born_povm` | [x] |
| 波粒二象性/延迟选择 | 相干交叉项 vs 事件化/去相干混合；互补性界 $V^2+D^2\le 1$；delayed-choice/eraser | Iface/Audit | `app:wave_particle_delayed_choice` | [x] |
| RG 运行 | $\mathrm{d}g/\mathrm{d}r=(\log\varphi)\beta(g)$ | Math | `eq:rg_in_r` | [x] |
| 稳定扇区计数（grammar/counts） | $X_m\subset\Omega_m$；$|X_m|=F_{m+2}$ | Math | `lem:xm_fib` | [x] |
| $\pi$-split（$18\oplus 3$） | $X_m=X_m^{\mathrm{cyc}}\sqcup X_m^{\mathrm{bdry}}$；$m=6$ 时 $21=18\oplus 3$ | Math | `prop:cyc_bdry_size`, `prop:cyc_bdry_6` | [x] |
| Fold 映射（离散折叠） | $\mathrm{Fold}_m:\{0,\dots,2^m-1\}\twoheadrightarrow X_m$；退化度统计/全表 | Math/Audit/Prot | `prop:foldm_surjective`, `thm:fold6_stats`, `app:fold6_full_table` | [x] |
| 协议 RG 内核（Kernel view） | 语言核（golden-mean shift）+折叠核（Fold$_m$/纤维退化）+uplift/coarse-graining 的可迭代算子视角；跨尺度计算入口 | Math/Iface/Audit | `sec:kernel_view`, `tab:fractal_kernel_sweep`, `tab:kernel_mu_r_bridge` | [x] |
| Hilbert 手性指标（chirality index） | $\chi$ 的反射/反向翻转律（符号律） | Math/Audit/Prot | `prop:chi_flip` | [x] |
| 规范补偿（gauge as compensation） | 纤维非平凡 $\Rightarrow$ 需要 transport；局部重标记 $\Rightarrow$ gauge 冗余 | Iface | `prop:gauge_compensation` | [x] |
| 三因子 gauge 闭合（holonomy 接口规则内） | 由 holonomy/phase-lift 诊断供给候选族来源，在有界紧致候选族内 CAP 最小闭合 $U(1)\times SU(2)\times SU(3)$（up to quotient） | Iface/CAP/Audit | `prop:channel_to_gauge`, `app:gauge3_holonomy_candidate_closure` | [x] |
| SM 标号闭合（$21\to$SM labeling） | $\mathcal{L}_{\mathrm{SM}}$ 的唯一闭合（给定排序键/语义约定） | Iface/CAP/Math | `sec:sm_labeling_closure`, `thm:labeling_unique` | [x] |
| Higgs/标量扇区（uplift 依赖） | $21$ 稳定类型不包含 Higgs；标量作为 uplift/coarse-graining 依赖的接口闭合/审计 | Iface/CAP/Audit | `rem:higgs_not_in_21`, `app:scalar_interface_audits` | [x] |
|| 质量谱/深度刚性（mass-depth rigidity） | 有界整数 ansatz 下系数 $(2,5,1)$ 的刚性闭合；并在主线把 $\Delta r$ 明确读作 matching-layer 的时间/尺度接口缝隙（clock-ratio / Compton-clock dictionary），不作为拟合误差项 | CAP/Audit | `sec:mass_spectrum_closure`, `prop:rhat_rigidity` | [x] |
|| 质量流（uplift mass-flow; CAP vs free-energy） | 在 lift 纤维 Ext$_m(u)$ 上用内生不变量池化，输出 $\widehat r_{\mathrm{CAP}}(u;m)$ 与 $\widehat r_{\mathrm{FE}}(u;m)$（审计窗口 $m\in\{6,8,10,12,14,16\}$） | Audit/Prot | `app:mass_flow_under_uplift`, `tab:mass_flow_uplift` | [x] |
|| 中微子质量机制候选族注册表（审计） | 并行推演 C1--C4 桥接假设（ghost repair cost / ξ 可见性 / uplift dilution / parity overhead），给出 CAP 最优与外部审计可行最优，并输出失败原因计分板 | Audit/Iface | `app:neutrino_mass_mechanism_candidates`, `tab:neutrino_mechanism_candidates`, `tab:neutrino_mechanism_scoreboard` | [x] |
|| Majorana 相位闭合（审计） | 在有界相位候选族（有界分母的 $\pi$ 有理倍数）内，结合 $m_{\beta\beta}$ 外部上界作为可行性过滤，给出确定性选择（CAP/tie-break）与输出表 | Audit/Iface | `app:neutrino_majorana_phase_closure`, `tab:neutrino_majorana_phase_closure` | [x] |
|| 中微子分裂（$\Delta m^2$）的有界有理 $r$-offset 尝试（审计） | 在 $q\le 12$ 的有界有理偏移族 $\Delta r=k/q$ 内，分别给出 protocol-only 的 CAP 最小者（通常被振荡数据排除）与 match-minimizer（对记录的 $\Delta m^2$ 压缩为低复杂度偏移） | Audit/Iface | `app:neutrino_splitting_depth_closure`, `tab:neutrino_splitting_depth_closure` | [x] |
|| Weinberg 维五算符尺度（审计/接口） | 采用标准 EFT Weinberg 算符，给出由 $m_{\nu,\max}$ 推出的 $\Lambda_W$ 尺度估计，并对照分辨率阶梯阈值 $\mu_{\mathrm{th}}(m)$ 的最近邻 | Audit/Iface | `app:neutrino_weinberg_operator_closure`, `tab:neutrino_weinberg_scale` | [x] |
|| Type-I seesaw 尺度（审计/接口） | 采用标准 Type-I seesaw，给出 $M_R=v^2y_{\nu,\mathrm{eff}}^2/(2m_{\nu,\max})$ 的尺度估计；并以 \texttt{cap}（协议侧复杂度）与 \texttt{match}（阈值对齐）两种模式展示最小不定性 | Audit/Iface | `app:neutrino_typeI_seesaw_closure`, `tab:neutrino_seesaw_scale` | [x] |
| 夸克参考质量（scheme 依赖；matching layer） | 夸克参考值作为重整化方案/尺度约定，仅用于报告 $\Delta r$ 与 $\mu/\mu_{\mathrm{pred}}=\varphi^{\Delta r}$ 的匹配层偏移 | Match/Audit | `app:quark_mass_scheme_notes`, `tab:mass_spectrum_quark_refs` | [x] |
| 耦合/CP/混合闭合（rigidity targets） | 规范化词典与有界复杂度闭合（含审计表）；中微子绝对质量仅作最小尺度接口（nearest-integer depth），并追加一段显式标注的接口假说解释“为何微小”（不进入 theorem 前提） | Iface/CAP/Match/Audit | `sec:couplings_cp`, `sec:pmns_neutrino_closure`, `subsec:neutrino_mass_interface`, `subsec:neutrino_interface_hypothesis` | [x] |
| 分辨率阶梯标定 | 在有界族内闭合 $r_{\mathrm{step}}=2\pi$（匹配层锚点仅作对比输入） | CAP/Match/Audit | `prop:r_step_2pi` | [x] |
| 宇宙学接口 | 分辨率初始化/容量增长/能量预算拟合 | Iface/CAP | `app:cosmology_resolution_flow`, `ass:occupancy_energy_z128` | [x] |
| $\gamma$ 跨观测审计（proxy/direct 分离） | $\gamma_{\mathrm{proxy}}$ 的代理通道压缩一致性检验 + $\gamma_{\mathrm{dict}}$ 的旋转曲线直接标定（两套内部一致性诊断与稳定性扫掠） | Iface/Audit/Prot | `app:gamma_crossobs_consistency` | [x] |

## “待闭合/高风险”清单（建议后续继续追踪）

- [x] **从协议层到连续场的误差控制**：离散→连续代表的收敛界/稳定性与误差预算（见 `sections/appendices/33_protocol_to_continuum_error_control.tex`，`\label{app:protocol_to_continuum_error_control}`）。
- [x] **散射时间延迟的统一闭合**：已在 `appendix 34` 统一为单一接口模块（`app:time_mass_delay` / `app:time_mass_delay_reference`），把“相位延迟/频率红移/散射相移”与 delay→lapse→GR 参考的匹配层词典集中闭合。
- [x] **$\gamma$ 审计（proxy 与 direct 分离）**：弱场代理通道的 $\gamma_{\mathrm{proxy}}$ 压缩一致性检验 + 旋转曲线通道的 $\gamma_{\mathrm{dict}}$ 直接标定（含数据协议与脚本/表格/图）。
  - 位置（接口附录）：`sections/appendices/35_gamma_cross_observation_consistency.tex`（`\label{app:gamma_crossobs_consistency}`）
  - 生成脚本：`scripts/exp_gamma_cross_observation.py`（已接入 `scripts/run_all.py`）
  - 数据协议/小体量数据：`data/gamma_crossobs/`（`solar_system/`, `sparc/`, `strong_lensing/`, `weak_lensing/`）
  - 生成物：
    - `sections/generated/gamma_crossobs_proxy_rows.tex`
    - `sections/generated/gamma_crossobs_proxy_diagnostics.tex`
    - `sections/generated/gamma_crossobs_proxy_stability_rows.tex`
    - `figures/gamma_crossobs_proxy.png`
    - `sections/generated/gamma_crossobs_direct_rows.tex`
    - `sections/generated/gamma_crossobs_direct_diagnostics.tex`
    - `sections/generated/gamma_crossobs_direct_stability_rows.tex`
    - `figures/gamma_crossobs_direct.png`
- [x] **宇宙学能量预算拟合的可复现脚本**：生成器 `scripts/exp_cosmology_energy_budget_fit.py`（已接入 `scripts/run_all.py`）
  - 入口：`sections/appendices/32_cosmology_resolution_flow.tex`（`app:cosmology_resolution_flow` / `ass:occupancy_energy_z128`，图 `fig:cosmology_energy_budget_fit`）
  - 生成物：
    - `sections/generated/cosmology_energy_budget_fit_equation.tex`
    - `sections/generated/cosmology_energy_budget_fit_summary.tex`
    - `sections/generated/cosmology_energy_budget_fit_stability.tex`
    - `figures/cosmology_energy_budget_fit.png`
- [~] **宇宙学能量预算的占据假设（Iface）**：`Assumption~\ref{ass:occupancy_energy_z128}` 将"能量份额"与读出微态集合的长期占据率做比例对应；该假设已被显式标注为接口假设并给出可证伪路径，但不属于 tick+CAP 的数学闭合输出（见 `app:cosmology_resolution_flow` / `subsec:cosmo_energy_budget_fit`）。
  - 备注：离散匹配采用 log-mismatch，Voronoi 分界为几何均值（`lem:log_voronoi_geometric_mean`）；暗/可见比值的可证伪口径以 $d_{m_\ast}-1$ 的 log-mismatch 形式写明（见 `app:cosmology_resolution_flow` 的 "Status and falsifiability" 段）。

- [x] **有限连接 transport rule 的反事实稳定性（look-elsewhere 审计）**：padding/truncation/tie-break 的有界反事实族对 gauge-invariant holonomy cycle-type 统计的影响包络（TV 距离、3/4-cycle 分数、边代价分位）。
  - 位置（补充附录）：`sections/appendices/15_holonomy_sweeps_extended.tex`（`subsec:holonomy_transport_rule_sensitivity`，表 `tab:holonomy_transport_rule_sensitivity`）
  - 生成脚本：`scripts/exp_holonomy_transport_rule_sensitivity.py`（已接入 `scripts/run_all.py`）
  - 生成物：`sections/generated/holonomy_transport_rule_sensitivity_rows.tex`

- [x] **（OP1）规范群候选族来源与三因子字典（holonomy 接口规则内闭合）**：在有限 holonomy/phase-lift 诊断的审计输出之上，候选族来源以接口规则方式内生化，并在有界紧致候选族内用确定性 CAP/tie-break 给出 $U(1)\times SU(2)\times SU(3)$ 的最小闭合（`prop:channel_to_gauge`；`app:gauge3_holonomy_candidate_closure`，`def:holonomy_to_candidate_family_rule`）。入口：`subsec:ledger_open_problems`，讨论：`subsec:open_problems_audit_tagged`（`sec:limitations_related_work`）。
  - 生成证书：`sections/generated/gauge3_holonomy_candidate_closure_rows.tex`（脚本 `scripts/exp_gauge3_holonomy_candidate_closure.py`）。
  - 可选 corroboration：物理共识输入（`app:physics_consensus_inputs`，`ass:consensus_three_factor_gauge`）与内部纤维微观路线（`app:internal_fiber_g2_optional` + `app:quantum_measurement_born`）可作为替代 underwrite，但不与本接口规则互推。
- [x] **（OP2）Fold 家族的唯一性/不可避免性（协议局部口径闭合）**：在“value-consistency + dyadic uplift 下的无回写局部性”这一最小可实现性契约下，Fold 家族被唯一强迫为 Zeckendorf-truncation `\mathrm{Fold}_m`（Theorem `thm:fold_family_uniqueness`）。  
  - 位置：`sections/appendices/44_fold_family_uniqueness.tex`（`\label{app:fold_family_uniqueness}`）  
  - 主依赖：折叠定义 `eq:foldm_def`；value-consistency `def:value_consistency_m`；前缀投影/可函子 uplift（`app:functorial_refinement`）；反事实族审计 `app:fold_family_sensitivity`。
- [x] **（OP3）有限连接→连续 Yang--Mills/EFT 的代表闭合**：已在本文以“代表闭合”的口径完成：从有限 holonomy/loop 不变量出发给出曲率与局域 gauge 动能项的接口字典，并在 CAP-候选族内选出连续 Yang--Mills/EFT 的最小代表。  
  - 位置：`sections/appendices/36_continuum_yang_mills_from_holonomy.tex`（`\label{app:continuum_yang_mills_from_holonomy}`，表 `tab:holonomy_balanced_chain_wilson`）  
  - 主依赖：有限 holonomy 诊断 `sec:protocol_connections_holonomy`；扩展 sweep `app:holonomy_sweeps_extended`（含 `tab:holonomy_wilson_loop`）；曲率语义 `subsec:curvature_as_loops`；连续代表作用量 `app:cap_continuum_action_closure`；场方程 `app:variational_field_equations`。
  - 生成脚本：`scripts/exp_holonomy_balanced_chain_sweep.py`（已接入 `scripts/run_all.py`）
  - 生成物：`sections/generated/holonomy_balanced_chain_wilson_rows.tex`
- [x] **（OP4）跨家族的全局模型选择（MDL / prefix-code；registry 内闭合）**：已在“声明家族注册表（主线候选族 + 已审计 baselines）”的口径内闭合：用前缀码/MDL 为家族分配显式权重，并把家族内的 $N_{\le\epsilon}/|\Theta|$ 升级为跨家族的加权 look-elsewhere 上界。  
  - 位置：`sections/appendices/42_global_model_selection_mdl.tex`（`\label{app:global_model_selection_mdl}`，表 `tab:audit_global_mdl_family_registry`）  
  - 生成脚本：`scripts/exp_audit_global_model_selection_mdl.py`（已接入 `scripts/run_all.py`）  
  - 生成物：`sections/generated/audit_global_mdl_family_rows.tex`，`sections/generated/audit_global_mdl_summary.tex`  
  - 主依赖：家族内审计表 `app:generated_tables`（含 `tab:audit_closure_metrics` / `tab:audit_counterfactual` / `tab:audit_pi_poly_null`）与 CAP 审计模板 `app:cap_audit_template`。
- [x] **（OP5）标量/Yukawa 与 RG running 的闭合（在声明接口假设内）**：标量在本论文中作为 uplift/coarse-graining 依赖接口处理（`app:scalar_interface_audits`；并明确 $21$ 类型不含 Higgs：`rem:higgs_not_in_21`）。Yukawa 可观测量（本征谱与混合矩阵）及 SM $\beta$-函数系数已在接口假设内闭合（`app:yukawa_beta_protocol_closure`）：本征值由深度模板给出，混合矩阵由 holonomy 机制固定，$\beta$-系数由闭合标号上的表示计数导出。VEV（或 $y_e$）与右手旋转作为接口校准/不可观测参数处理。入口：`subsec:ledger_open_problems`，讨论：`subsec:open_problems_audit_tagged`。

### 经典未决问题：本文覆盖范围对照（建议单列追踪）

#### 已在本文给出自包含闭合/可复现审计路径（在本文声明口径内）

- [x] **SM 稳定扇区与 $21$ 类型标号闭合（含最小手性内容与 $\nu_R$）**：锚点 $64\to 21$ 与 $18\oplus 3$ 之上闭合 $\mathcal{L}_{\mathrm{SM}}$（`sec:folding_core`，`sec:sm_labeling_closure`，`thm:labeling_unique`，`prop:anomaly_nur`）。
- [x] **手性/反物质/CPT 的协议几何字典**：orientation class、conjugation-as-reversal、antimatter dual（`sec:chirality_antimatter`）。
- [x] **CP 破坏与混合（CKM/PMNS）作为有限 holonomy 的有界闭合与审计**：`sec:couplings_cp`，`sec:pmns_neutrino_closure`（配套 `app:closure_audit_details` 生成表）。
- [x] **质量谱/尺度（mass-as-latency）接口闭合**：`sec:mass_latency_coordinate`，`sec:mass_spectrum_closure`（含刚性证书与审计表；并把 $\Delta r$ 作为 matching-layer 的 clock-ratio 接口量而非拟合误差显式入主线）。
- [x] **时间箭头与热力学接口闭合**：指数半群模板与 CAP 自由能模板（`app:arrow_of_time_semigroup_notes`，`app:thermodynamics_from_equivalence`）。
- [x] **量子测量与 Born 概率规则（POVM/instrument + 两条闭合路线）**：计数模板与 Gleason–Busch 唯一性（`app:quantum_measurement_born`）。
- [x] **波粒二象性/延迟选择/量子擦除（接口解释）**：以 Born 概率的交叉项/去相干混合为最小核（`lem:z128_interference_vs_mixture`），并用 readout-interface 语言给出 delayed-choice/eraser 与 Wheeler “Great Smoky Dragon” 的审计口径（`app:wave_particle_delayed_choice`）。
- [x] **弱场引力可检验接口链（overhead→lapse→potential + 反演与误差预算）**：`app:overhead_to_gravity_closure`，`app:chi_reconstruction_protocol`，`app:protocol_to_continuum_error_control`，`app:gamma_crossobs_consistency`。
- [x] **宇宙学接口（分辨率初始化/容量增长/隐藏分数骨架）**：`app:cosmology_resolution_flow`（其中能量预算拟合条目见下方“部分闭合/接口假设”）。

#### 已提及但未在当前闭合链内完成（显式假设/外部输入/指针/仅匹配层口径）

- [x] **可选：内部纤维微观路线（相对 Q 扩展输入包）**：以 Hurwitz 分类与三通道最小记录为核心，给出候选族来源的另一条 underwrite（见 `app:internal_fiber_g2_optional` 与 `app:quantum_measurement_born`）；该路线在本论文中作为可选 corroboration，不进入主闭合链的必要输入。
- [~] **标量/Higgs/Yukawa 与 RG $\beta$-函数**：标量作为 uplift/coarse-graining 依赖接口处理；Yukawa 与 $\beta$-函数闭合为 OP5（`app:scalar_interface_audits`；`subsec:ledger_open_problems`）。
- [~] **暗部门能量预算（暗物质/暗能量口径）**：以占据计数假设把 $f_{\mathrm{stab}}(m),f_{\mathrm{hid}}(m)$ 映射到 $\Omega_{\mathrm{vis},0},\Omega_{\mathrm{dark},0}$；该条被显式标注为接口假设并提供可复现拟合（`ass:occupancy_energy_z128`；离散匹配采用 log-mismatch，Voronoi 边界为几何均值见 `lem:log_voronoi_geometric_mean`；并在生成摘要中区分 “dark=DM-only vs dark=total hidden” 的匹配口径）。
- [x] **宇宙学常数/真空能密度（$\Lambda$；e-通道 pressure 审计闭合）**：以 e-通道 pressure 常数构造有限候选族 $\Omega_{\Lambda,0}\in\{s_k,\,1-s_k:\ k\in\{0,1,\dots,8\}\}$（$s_k=\log_2\lambda_k$，$\lambda_k=(1+\sqrt{1+4\cdot 2^{-k}})/2$），并按有限族的复杂度优先规则选取最小 $k$ 的 share 候选（$\widehat\Omega_{\Lambda,0}=s_{k_\ast}$，$k_\ast=\min\{0,1,\dots,8\}=0$；其余候选作为有界反事实基线）。数值审计层面：用 Planck-2018 的 $\Omega_{\Lambda,0},\Omega_{m,0},\Omega_{b,0}$ 做 mismatch 报告（含 mismatch-minimizer 的 $\pm1\sigma$ 稳健性诊断与 MDL 惩罚诊断）；$H_0$ 由有限候选族（Planck/H0LiCOW/SH0ES）按最小相对不确定度 $\sigma_{H_0}/H_0$ 的确定性规则选出 $\widehat H_0$（`data/cosmology_lambda/h0_candidates.json`），再由 $\Lambda=\frac{3\widehat H_0^2}{c^2}\widehat\Omega_{\Lambda,0}$ 定标输出，并在 $H_0$ 家族内给出敏感性对照；DM split 诊断使用 Z128 固定 $m_b^\ast=2p+1$（$p=7$）得到 $\widehat\Omega_{b,0}=f_{\mathrm{stab}}(m_b^\ast)$ 并对比 $\Omega_{\mathrm{DM}}/\Omega_b$ 的参考值（`app:lambda_pressure_closure`；脚本 `scripts/exp_lambda_pressure_closure.py` 生成片段，Planck 目标来自 `data/cosmology_lambda/planck2018_targets.json`）。
- [~] **黑洞面积律/虫洞类通道的指针性结构**：以标准外部输入与接口指针记录（面积律、ER throat、pointer-jump 模型），不作为 tick+CAP 证明链前提；并在附录中显式写明“指针模块/不进入证明链”的审计边界（`app:bh_wormholes_pointer`）。
- [x] **中微子质量机制与 Majorana 相位（条件闭合：审计/接口）**：本文以振荡可观测为主；Majorana 相位不进入振荡概率（见 `lem:majorana_phases_cancel`），因此以显式候选族 + 可行性过滤的方式在接口层给出确定性输出。
  - 外部审计通道（Match/Audit）：0$\nu\beta\beta$、$\Sigma m_\nu$、$m_\beta$、sterile/N$_\mathrm{eff}$ 约束已在 `app:neutrino_external_audit_channels` 给出定义/失败条件，并由脚本生成外部输入账本（`tab:neutrino_external_audit_ledger`）。
  - 机制候选族注册表（Audit）：并行推演的桥接假设与失败点计分板见 `app:neutrino_mass_mechanism_candidates`（表 `tab:neutrino_mechanism_candidates` / `tab:neutrino_mechanism_scoreboard`）。
  - Majorana 相位闭合（Audit）：有界分母相位族 + $m_{\beta\beta}$ 上界可行性过滤 + 确定性 tie-break 见 `app:neutrino_majorana_phase_closure`（表 `tab:neutrino_majorana_phase_closure`）。
  - $\Delta m^2$ 偏移压缩（Audit）：有界有理 $r$-offset 的 protocol-only vs match 对照见 `app:neutrino_splitting_depth_closure`（表 `tab:neutrino_splitting_depth_closure`）。
  - Weinberg 维五算符尺度（Audit）：由 $m_{\nu,\max}$ 给出 $\Lambda_W$ 并对照分辨率阶梯阈值，见 `app:neutrino_weinberg_operator_closure`（表 `tab:neutrino_weinberg_scale`）。
  - Type-I seesaw 尺度（Audit）：给出 $M_R$ 的 \texttt{cap} vs \texttt{match} 两种模式，见 `app:neutrino_typeI_seesaw_closure`（表 `tab:neutrino_seesaw_scale`）。
- [~] **QCD 禁闭/质量隙相关的严格问题**：本文只在分辨率阶梯上给出 QCD/hadronic 尺度的匹配层 benchmark 与阈值预测条目，并在多处显式声明“不触及 Yang–Mills 质量隙/禁闭机制”（`sec:introduction` 的分辨率谱；`sec:falsifiability` 的阈值预测；`app:continuum_yang_mills_from_holonomy` 的范围声明与内部指针到 `app:quark_mass_scheme_notes` / `app:running_couplings_resolution_flow`；以及 `sec:limitations_related_work` 的 OP3 讨论）。
- [~] **大统一/质子衰变等高能结构**：仅作为 benchmark 口径提及（如 $SU(5)$ 的 $\sin^2\theta_W=3/8$），未进入闭合链或可证伪审计；并在限制章节交叉指向 benchmark 的尺度/匹配层边界（`rem:gutsin2_benchmark`）。

#### 本文未覆盖（未进入正文论证与审计链路）

- [ ] **重子不对称/重子生成（Sakharov 条件、$\Delta B\neq 0$）**：未讨论出平衡、$\Delta B$ 机制与对观测 $\eta_B$ 的闭合/拟合；建议参考与入口：Sakharov 条件 \cite{Sakharov1967ViolationCAndBaryogenesis}，电弱鞍点与 $B+L$ 非守恒 \cite{KuzminRubakovShaposhnikov1985AnomalousBNonconservation}；本文对应范围边界与引用指针已集中放在 `sec:limitations_related_work` 的 `subsec:open_problems_audit_tagged`。
- [ ] **强 CP 问题与 $\theta_{\mathrm{QCD}}$（Peccei–Quinn/轴子）**：未建立 $\theta_{\mathrm{QCD}}$ 的协议变量与选择机制；亦未纳入 EDM 约束链路；建议参考与入口：PQ 机制与轴子原始文献 \cite{PecceiQuinn1977CPConservationPseudoparticles,PecceiQuinn1977ConstraintsCPConservation,Weinberg1978NewLightBoson,Wilczek1978StrongPTInstantons}，精密 EDM 约束（电子/中子/原子）\cite{ACME2018ElectronEDM,AbelEtAl2020NeutronEDM,GranerChenLindahlHeckel2016HgEDM}；本文对应范围边界与引用指针已集中放在 `sec:limitations_related_work` 的 `subsec:open_problems_audit_tagged`。
- [ ] **黑洞信息悖论（蒸发、信息回收、Page 曲线等）**：未处理蒸发动力学与信息一致性条件；建议参考与入口：Page 曲线与典型纠缠结果 \cite{Page1993AverageEntropySubsystem,Page1993InformationInRadiation}，islands/QES/replica wormholes 的综述与核心工作 \cite{AlmheiriHartmanMaldacenaShaghoulianTajdini2021EntropyHawkingRadiation,Penington2020EntanglementWedgeReconstruction,AlmheiriHartmanMaldacenaShaghoulianTajdini2020ReplicaWormholes}；本文对应范围边界与引用指针已集中放在 `sec:limitations_related_work` 的 `subsec:open_problems_audit_tagged`，而黑洞/虫洞仅在 `app:bh_wormholes_pointer` 给出“外部目标+接口指针”。
- [ ] **量子引力（普朗克尺度闭合）**：未给出普朗克尺度的统一闭合动力学与可计算的普适检验。
- [ ] **现代宇宙学张力（$H_0$ tension、$S_8/\sigma_8$ tension）**：未讨论相关张力问题及其数据/系统误差模型；建议参考与入口：Planck-2018 参数 \cite{Planck2018Parameters2020AandA}，SH0ES 距离梯 \cite{RiessEtAl2022SH0ESApJL}，弱透镜/多探针基准 \cite{AsgariEtAl2021KiDS1000CosmicShear,DESY3Cosmo2022PRD}，综述 \cite{VerdeTreuRiess2019TensionsReview}；本文对应范围边界与引用指针已集中放在 `sec:limitations_related_work` 的 `subsec:open_problems_audit_tagged`。
- [ ] **更高能 BSM 框架（SUSY/弦论等）与质子衰变**：未进入闭合推导链或审计化可证伪预测。

## 快速入口（给维护者）

- **“概念→定义/闭合输出”总入口**：`tab:concept_index`（`app:equivalence_semantics` 内）
- **“推导脊柱（Tick+CAP）”入口**：`sections/appendices/19_tick_cap_derivation.tex`
- **“推断账本（哪些是 Iface/CAP/Math）”入口**：`sections/appendices/11_inference_ledger.tex`
- **“外部 matching 输入清单”入口**：`subsec:external_inputs_inventory` / `tab:external_inputs_inventory`（位于 `sections/appendices/11_inference_ledger.tex`）
- **“Open problems 清单”入口**：`subsec:ledger_open_problems`（并在 `sec:limitations_related_work` 的 `subsec:open_problems_audit_tagged` 提供更详细讨论）
- **“协议→连续场误差控制”入口**：`sections/appendices/33_protocol_to_continuum_error_control.tex`

