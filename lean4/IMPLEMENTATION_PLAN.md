# Lean4 无公理形式化实施方案（2026-03-22 状态重建版）

## 1. 文档目的

本文档是
`docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence`
向 `lean4/` 迁移的现行执行计划。

它不再描述“准备怎么开始”，而是描述：

- 当前已经形式化到哪里
- 哪些结果已经稳定纳入 `lean4/`
- 哪些结果仍未完成
- 从现在起最合理的继续推进顺序

本版文档以当前代码库真实状态为准，而不是早期骨架状态。

## 2. 核心工程约束

### 2.1 “无公理”的工程定义

本项目中的“无公理”含义保持不变：

- 不新增 `axiom`
- 不新增把未证命题伪装成事实的 `constant`
- 不把猜想、实验规律、条件性结论写成无条件 `theorem`
- 核心层结果可通过 `#print axioms` 审计

允许使用：

- Lean4 内核逻辑
- mathlib 的既有定义、定理、类型类和战术
- 条件性定理，即把假设显式放入参数

### 2.2 工作方式约束

从当前阶段开始，项目遵守以下推进规则：

- 只继续形式化论文中“能稳定收敛”的部分
- 一旦某条线短时间内不能形成可编译定理，就退回到上一个全绿状态
- 不把半成品证明留在主分支
- 优先做“现有基线的自然延伸”，避免过早引入重型远层理论

## 3. 当前工程快照

截至本版文档生成时，`lean4/` 已达到以下状态：

- `Lake + mathlib` 工程稳定
- `Omega.lean` 已接入所有当前稳定模块
- `Audit/SourceMap.lean`、`Audit/Inventory.lean`、`Audit/NoAxiom.lean` 已形成真实索引
- `cd lean4 && lake build` 可全量通过

当前工程已不再是“初始化阶段”，而是一个已经具备离散内核、重写系统、逆极限、缺陷代数、SPG 组合与测度层、显式 sofic 表示、以及前沿包装/证书接口的项目。

## 4. 已完成工作总览

### 4.1 阶段状态总表

| 阶段 | 内容 | 当前状态 |
|---|---|---|
| 0 | Lake / mathlib / 审计基线 | 已完成 |
| 1 | `Word` / `No11` / `X m` / 计数递推 | 已完成 |
| 2 | `Weight` / `Value` / Zeckendorf 桥接 | 已完成 |
| 3 | `Rewrite` / `Fold` / fiber / rank-unrank | 已完成 |
| 4 | inverse limit / defect / telescope | 已完成 |
| 5 | cylinder / prefix metric / clopen | 已完成 |
| 6 | 离散 scan error / 测度 scan error / prefix specialization | 已完成当前范围 |
| 7 | 显式 golden-mean sofic 表示 | 已完成当前范围 |
| 8 | assumptions / conditional / conjectures / certificates | 已完成当前范围 |
| 9 | 补全对称性 / 单元界 / fiber 分割 / Word 基数 | 已完成当前范围 |

“已完成当前范围”表示：本阶段在实施文档中承诺的直接 Lean 可落地部分已经有稳定实现，但论文更远层的扩写仍可继续。

### 4.2 已完成模块清单

当前稳定模块为：

```text
Omega/Core/Fib.lean
Omega/Core/Word.lean
Omega/Core/No11.lean
Omega/Folding/StableSyntax.lean
Omega/Folding/Weight.lean
Omega/Folding/Value.lean
Omega/Folding/Zeckendorf.lean
Omega/Folding/Fold.lean
Omega/Folding/Fiber.lean
Omega/Folding/InverseLimit.lean
Omega/Folding/Rewrite.lean
Omega/Folding/Defect.lean
Omega/Graph/LabeledGraph.lean
Omega/Graph/Sofic.lean
Omega/SPG/Cylinder.lean
Omega/SPG/PrefixMetric.lean
Omega/SPG/Clopen.lean
Omega/SPG/ScanErrorDiscrete.lean
Omega/SPG/ScanErrorMeasure.lean
Omega/Frontier/Assumptions.lean
Omega/Frontier/Conditional.lean
Omega/Frontier/Conjectures.lean
Omega/Frontier/Certificates.lean
Omega/Audit/SourceMap.lean
Omega/Audit/Inventory.lean
Omega/Audit/NoAxiom.lean
```

### 4.3 已完成结果族

#### A. 有限稳定语法核心

已完成：

- 固定长度位词 `Word`
- 截断、拼接、末位与访问
- `No11`
- 稳定语法空间 `X m`
- `restrict` / `appendFalse` / `appendTrue`
- `|X m| = Fibonacci` 的当前编码桥接

#### B. Zeckendorf 与值函数

已完成：

- `weight`
- `stableValue`
- 稳定词到 `List.IsZeckendorfRep` 的桥接
- `Nat.zeckendorf` 回到稳定词的构造
- 与 mathlib `Nat.zeckendorfEquiv` 的项目级桥接

#### C. `Fold`、重写系统与正规形主线

已完成：

- `DigitCfg`
- `Step`
- 值保持
- 强终止
- 局部合流
- 全局合流
- 终端不可约存在
- 终端不可约唯一
- `Fold` 与终端正规形的桥接
- `Fold` 幂等
- `Fold` 满射

当前 `Rewrite` 线已经不只是“局部规则”，而是具备正式可编译的终止与合流闭环。

#### D. fiber 与 rank/unrank

已完成：

- `X.fiber`
- `fiber_nonempty`
- `choosePreimage`
- `FiberElem`
- `rank` / `unrank`
- `unrankWord`
- `Fold_unrankWord`
- `rankOfFoldEq`

也就是说，有限 fiber 不仅存在，而且已经具备有限枚举接口。

#### E. inverse limit 与 defect

已完成：

- 具体兼容族 `CompatibleFamily`
- `XInfinity`
- `inverseLimitEquiv`
- `localDefect`
- `globalDefect`
- defect 递归关系
- 离散 telescope / Stokes 型恒等式

#### F. `SPG` 组合层

已完成：

- cylinder
- prefix determined events
- prefix ultrametric
- ball / cylinder correspondence
- clopen 表达

#### G. `SPG` 离散与测度扫描误差

已完成：

- 离散 `scanError`
- 边界分解
- 边界质量/边界基数上界
- prefix observable 专门化
- 一般测度版 `scanErrorMeasure`
- `ObservablePureMeasure`
- “纯性 ↔ 边界为空”
- “纯性 ⇒ 扫描误差为零”
- PMF 与 measure 的桥接

#### H. graph / sofic

已完成：

- 显式标记图接口
- two-state golden-mean graph
- stable language 与该显式 sofic 表示的双向对应

#### I. frontier / certificates

已完成：

- assumptions 层骨架
- conditional theorem 包装层
- conjectures 作为 `Prop` 接口
- defect / rewrite / fold / scan-error 证书验证器
- 多条直接贴论文语义的 conditional wrappers

#### J. Phase 9: 补全对称性 / 单元界 / fiber 分割

已完成：

- `Word_card`: |Word m| = 2^m
- `fiber_card_sum`: ∑_x |fiber(x)| = |Word m| (fiber 分割恒等式)
- `fiber_card_sum_eq_pow`: ∑_x |fiber(x)| = 2^m
- 离散 observable purity 补对称: `observablePure_compl`
- 离散 boundary cells 补对称: `boundaryCells_compl`
- 离散 prefix boundary cells 补对称: `prefixBoundaryCells_compl`
- 测度 cell event mass 单调界: `cellEventMeasure_le_cellMeasure`
- 测度 cell complement mass 单调界: `cellComplMeasure_le_cellMeasure`
- 测度 cell 分割恒等式 (MeasurableSet): `cellEventMeasure_add_cellComplMeasure_eq_cellMeasure`
- 测度 observable purity 补对称: `observablePureMeasure_compl`
- 测度 boundary cells 补对称: `boundaryCellsMeasure_compl`
- 测度 boundary cylinder count 补对称: `boundaryCylinderCount_compl`
- 测度 prefix boundary cells 补对称: `prefixBoundaryCellsMeasure_compl`
- 测度 prefix boundary cylinder count 补对称: `prefixBoundaryCylinderCount_compl`
- 全部上述结果的 `Frontier/Conditional` 论文接口包装

## 5. 现成可复用与已复用边界

以下内容已经确认复用，不再从零重证：

- `Nat.fib`
- `Nat.zeckendorf`
- `Nat.zeckendorfEquiv`
- `List.IsZeckendorfRep`
- `Relation.ReflTransGen`
- `Relation.Join`
- `Relation.church_rosser` 相关通用 machinery
- `IsClopen`
- Cantor 空间与超度量基础
- `MeasurableSpace` 与 `Measure` 基础
- `PMF.toMeasure`

因此，后续继续工作时，原则保持不变：

- mathlib 已有 theorem 本体，只做桥接和专用包装
- 论文专用对象与专用交换图，继续由项目自行证明

## 6. 当前剩余工作

### 6.1 当前最值得继续推进的部分

从当前工程状态看，下一阶段最自然的增量不再是基础离散内核，而是：

1. 更强的 `SPG` 测度表达
2. 更多贴论文叙述的 `Frontier/Conditional` 定理
3. 在不引入重型远层理论的前提下，向论文后半段继续推进

### 6.2 仍未完成的主块

以下内容仍然没有稳定落地：

#### A. 更强的 `SPG` 条件期望 / Tanaka-Stokes 叙述

当前已有：

- boundary decomposition
- purity (discrete `ObservablePure` + measure `ObservablePureMeasure`)
- zero-error criteria (discrete + measure, both directions)
- zero-iff-pure 等价 (discrete + measure)
- zero-iff-boundary-empty 等价 (discrete + measure)
- complement symmetry (`scanError_compl` + `scanErrorMeasure_compl`)
- trivial event zero-error (`scanError_empty/univ` + `scanErrorMeasure_empty/univ`)
- PMF/measure bridge
- PMF/measure purity bridge (`observablePureMeasure_toMeasure_iff_observablePure`)
- 代数不等式 `sum_min_le_min_sum` (∑ min ≤ min ∑)
- 观测细化单调性 (`scanError_antitone_of_refines`)
- 前缀扫描误差单调性 (`prefixScanError_antitone`: m₁ ≤ m₂ → SE(m₂) ≤ SE(m₁))
- 单元质量纤维分解 (`cellEventMass_refines_sum`, `cellComplMass_refines_sum`)
- 边界柱计数 `boundaryCylinderCount` / `prefixBoundaryCylinderCount` (论文 Definition 3.5 N_m(∂P))
- 边界柱计数 ↔ 可观测纯性等价 (`boundaryCylinderCount_eq_zero_iff_observablePure`)
- 扫描误差为零 ↔ 边界柱计数为零 (`scanErrorMeasure_eq_zero_iff_boundaryCylinderCount_eq_zero`)
- 边界柱计数 PMF 桥接 (`boundaryCylinderCount_toMeasure_eq`)
- 测度级观测细化单调性（经 PMF 桥接）(`scanError_measure_antitone_via_bridge`)
- 测度级前缀扫描误差单调性（经 PMF 桥接）(`prefixScanError_measure_antitone_via_bridge`)

仍缺：

- 更接近论文后段的条件期望型表达
- 若论文需要的 martingale / Tanaka-Stokes 形式
- 更强的测度级结构化重述（条件概率因式分解形式）

#### B. 更远层的 frontier 条件定理

当前 `Frontier/Conditional.lean` 已经能包装大量核心结果，但仍偏“当前基线的直接重述”。

新增：

- 论文 Section 4 稳定语法基数包装 (`stableSyntax_card_eq_fibonacci`, `stableSyntax_card_recurrence`)
- 论文 Section 4 Zeckendorf 桥接包装 (`stableWord_zeckendorf_valid`, `stableValue_eq_fibonacci_weighted_sum`)
- 论文 Section 4 fiber 基数包装 (`fold_fiber_card_pos`)
- 论文 Definition 3.5 边界柱计数条件层包装（完整的 zero-iff 链、PMF 桥接、observable event 消失）
- 测度级观测细化单调性条件层包装（经 PMF 桥接）

仍缺：

- 更靠近论文后半段组织方式的条件定理簇
- 更系统的 assumptions-to-results 映射
- 更明确的”哪一组假设推出哪一层结果”的编排

#### C. 论文远层主题

以下方向仍然基本未开始，且默认应视为下一阶段探索对象，而不是当前已经完成的内容：

- `POM`
- `CMV`
- `Peter-Weyl`
- `Langlands`
- 任何依赖明显更重分析/代数/表示论 machinery 的章节

这些部分不应在没有稳定短路径的情况下强行进入主线。

## 7. 当前推荐推进顺序

从现在起，推荐顺序改为：

1. 继续扩 `Frontier/Conditional.lean`
2. 继续扩 `SPG/ScanErrorMeasure.lean`
3. 继续补能直接贴论文措辞的 certificates wrappers
4. 只在前三项没有短路径时，才进入更远层章节

理由：

- 当前内核已经足够稳定
- 当前最容易高产的是“用现有内核重述论文结果”
- 远层主题一旦进入，失败风险和维护成本都明显更高

## 8. 当前阶段的模块职责

### 8.1 `Omega.Folding`

当前职责已经从“建基础”升级为：

- 维护离散规范形主线
- 提供 `Fold` / `Rewrite` / `Fiber` / `Defect` 的稳定接口
- 为 `Frontier` 提供可重述的核心 theorem

后续原则：

- 除非论文明确需要新的离散对象，否则不要继续在 `Folding` 层大规模增设新基础对象

### 8.2 `Omega.SPG`

当前职责：

- 维护组合层
- 维护离散扫描误差层
- 维护一般测度扫描误差层
- 继续向条件期望型表达扩展

后续应优先扩在这个模块，而不是直接跳到更远的条件层。

### 8.3 `Omega.Graph`

当前职责：

- 提供显式 sofic 接口
- 为论文中的语言/图像叙述提供桥接

后续只在有明确论文对应对象时继续扩。

### 8.4 `Omega.Frontier`

当前职责：

- assumptions
- conditional wrappers
- conjectures
- certificates

当前项目最有产出的继续方向之一就是这个目录。

## 9. 延期与非目标

以下事项仍然明确延期：

- 为了一个具体远层 theorem 先铺一整套重型 category theory
- 为了一个条件定理先从零建设完整算子代数层
- 在没有收敛路径时硬推 `POM` / `CMV` / `Peter-Weyl` / `Langlands`
- 把猜想或实验现象塞进核心层作为既证结论

## 10. 质量闸门

后续每一轮推进仍必须满足：

- `cd lean4 && lake build` 全量通过
- 不留下 `admit`
- 不留下未接线半成品模块
- `Audit/SourceMap.lean` 与 `Audit/NoAxiom.lean` 同步更新
- 新 theorem 若属于核心层或稳定前沿接口，应进入审计清单

## 11. 当前 backlog 重排

### 11.1 已闭环 backlog

以下大项已可视为闭环：

1. `X m` 有限稳定语法主线
2. Zeckendorf 桥接
3. `Fold` 主线
4. `Rewrite` 的终止/合流/正规形唯一
5. fiber 与 rank/unrank
6. inverse limit
7. defect telescope
8. `SPG` 组合层
9. `SPG` 离散扫描误差
10. `SPG` 测度扫描误差当前范围
11. 显式 golden-mean sofic 表示
12. frontier 当前范围下的 assumptions / conditional / conjectures / certificates

### 11.2 已闭环新增 (Phase 9–10)

13. Word 基数 `Word_card`: |Word m| = 2^m
14. fiber 分割 `fiber_card_sum`: Σ|fiber(x)| = |Word m|
15. fiber 基数等式 `fiber_card_sum_eq_pow`: Σ|fiber(x)| = 2^m
16. 离散/测度补对称（purity, boundary cells, boundary cylinder count, prefix 版本）
17. 测度 cell 单调界（cellEventMeasure ≤ cellMeasure, cellComplMeasure ≤ cellMeasure）
18. 测度 cell 分割恒等式（MeasurableSet 条件下 event + compl = total）
19. stableValue Fibonacci 界 `stableValue_lt_paperFib_succ`
20. stableValueFin 与 stableValueFin_injective
21. 稳定加法定义与交换律 `stableAdd`, `stableAdd_comm`
22. Fibonacci 基础设施（paperFib_pos, paperFib_mono, paperFib_le_succ 等）
23. 离散质量分割 `setMass_add_setMass_compl`

### 11.3 当前活跃 backlog：12 条未来计划

以下 12 条为按优先级排列的下一步具体工作，每条均应在单轮内完成并通过 `lake build`。

#### 计划 1：PMF 总质量与 Bayes 半界

- 证明 `∑ x, (μ x : ENNReal) = 1`（使用 `PMF.tsum_coe` 与 `tsum_fintype`）
- 证明 `two_mul_scanError_le_one`：2 · ε(P; μ) ≤ 1
- 对应论文 Proposition 3.x Bayes 最优界

#### 计划 2：stableValue 满射性与 ofNat 逆

- 证明 `stableValue (X.ofNat m n) = n` 当 `n < paperFib(m+1)`
- 建立 stableValue 与 Fin(paperFib(m+1)) 的等价
- 对应论文 Theorem 6.1 双射性

#### 计划 3：稳定加法代数结构

- 证明 `stableAdd_assoc`（结合律）
- 证明 `stableAdd_zero_left` / `stableAdd_zero_right`（零元）
- 证明 `stableAdd_cancel`（消去律，若成立）
- 对应论文 Section 6 有限稳定算术

#### 计划 4：直接测度级观测细化单调性

- 添加 `Measurable obs₂` 和 `MeasurableSet P` 假设
- 证明 `scanErrorMeasure_antitone_of_refines`（直接测度版，非 PMF 桥接）
- 证明 `prefixScanErrorMeasure_antitone`（前缀版本）
- 对应论文 Corollary 3.1

#### 计划 5：测度 cell 质量求和恒等式

- 证明 `cellEventMeasure_sum_eq_measure_event`（MeasurableSet + Measurable obs 假设下）
- 证明 `cellComplMeasure_sum_eq_measure_compl`
- 证明 `cellMeasure_sum_eq_measure_univ`
- 对应论文 Proposition 3.2 分割恒等式的测度推广

#### 计划 6：POM fiber 乘数显式公式

- 定义 `fiberMultiplicity x : Nat := (X.fiber x).card`
- 证明 fiber 乘数与 Zeckendorf 表示的关系
- 证明 fiber 乘数对称/递推关系（若论文有明确结论）
- 对应论文 POM Section fiber 谱

#### 计划 7：stable 值等价与 Fin 同构

- 构造 `stableValueEquiv : X m ≃ Fin (paperFib (m + 1))`（使用 stableValue 界 + 注入性 + 基数）
- 使用 `Fintype.equivFinOfCardEq`
- 对应论文 Theorem 4.1 / Theorem 6.1 核心编码结论

#### 计划 8：golden-mean 转移矩阵与特征值

- 定义 `transferMatrix : Matrix (Fin 2) (Fin 2) ℕ`
- 证明其特征多项式为 `x² - x - 1`
- 证明 Perron-Frobenius 维度为 φ
- 对应论文 subsec__folding-fibonacci-stable-syntax 中的 fusion ring 结论

#### 计划 9：Rewrite 步数上界

- 证明从任意 `DigitCfg` 出发到达不可约终端的 Rewrite 步数的显式上界
- 证明 `moment` 或 `mass` 在每一步严格下降
- 对应论文 Fold Section 的终止复杂度分析

#### 计划 10：scan error 子模性 / 格结构

- 证明 `scanError μ obs (P ∩ Q) + scanError μ obs (P ∪ Q) ≤ scanError μ obs P + scanError μ obs Q`
  （子模性，若成立——需验证）
- 或证明等价的格单调性结论
- 对应论文 SPG Section 的误差格结构

#### 计划 11：Defect 的 Fibonacci 周期性

- 证明 `localDefect` 在特定 Fibonacci 分辨率下的周期性或重现性
- 建立 defect 与 Zeckendorf 进位的联系
- 对应论文 Defect Section 的递推关系

#### 计划 12：前缀 σ-代数非扩张

- 定义 `prefixSigmaAlgebra m` 作为前缀可测集
- 证明 `prefixSigmaAlgebra (m+1) ⊆ prefixSigmaAlgebra m`（非扩张 / 单调递减）
- 对应论文 sec__recursive-addressing 中的 Proposition

## 12. 直接执行顺序

如果现在继续推进，建议严格按下列顺序：

1. 先执行计划 1（PMF 总质量与 Bayes 半界）和计划 2（stableValue 满射性）
2. 再执行计划 3（稳定加法代数结构）和计划 7（Fin 同构）
3. 再执行计划 4-5（测度级单调性与求和恒等式）
4. 每一轮都先验收 `lake build`
5. 计划 6-12 可按可行性灵活调整顺序

## 13. 结论

本项目已经从”是否能建起无公理 Lean 基线”转入”如何持续吸收原论文结果”的阶段。

当前阶段的关键进展：

- 离散核心已经稳定（Word, No11, X_m, Fold, Rewrite, Fiber, Defect, InverseLimit）
- 重写与正规形主线已经稳定（终止、合流、唯一性闭环）
- `SPG` 的组合与当前测度层已经稳定（含补对称性、cell 界、分割恒等式）
- `Frontier` 包装层已经成为论文叙述的真实接口层
- **新增**：stableValue Fibonacci 界与稳定加法为有限算术打开入口
- **新增**：fiber 分割恒等式 Σ|fiber(x)| = 2^m 建立纤维组合基线

下一阶段应围绕 12 条具体计划持续推进。
