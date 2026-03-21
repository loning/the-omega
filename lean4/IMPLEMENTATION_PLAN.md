# Lean4 无公理形式化实施方案（重构版）

## 1. 文档目的

本文档给出
`docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence`
向 `lean4/` 迁移的最新实施方案。

本次重构的核心变化只有一条：

- 不再把 “重证 mathlib 已有基础定理” 当成项目目标

项目目标不是机械翻译整篇论文，而是：

- 复用 Lean4 + mathlib 的现成基础
- 只形式化论文专用的离散核心对象与专用交换图
- 保持项目无项目自定义公理
- 为后续条件性结果、证书验证器和实验接口提供稳定基座

## 2. “无公理”的工程定义

本项目中的“无公理”定义为：

- 不新增 `axiom`
- 不新增用未证命题充当事实的 `constant`
- 不把猜想、经验规律、实验结论写成无条件 `theorem`
- 核心层定理可通过 `#print axioms` 审计，不依赖项目自定义事实

允许使用：

- Lean4 内核逻辑
- mathlib 的既有定义、定理、类型类和战术
- 条件性定理，即把假设显式写入参数

不承诺：

- 完全脱离 mathlib
- 第一阶段覆盖概率、算子代数、Langlands、GRH 等高层内容

## 3. 当前工程基线

截至当前，`lean4/` 已经具备以下基线：

- `Lake + mathlib` 工程已初始化并可编译
- 固定长度位词 `Word`
- `No11`
- 稳定语法子类型 `X m`
- `restrict` / `appendFalse` / `appendTrue`
- 基础权重函数和 `stableValue`
- `Audit/SourceMap`、`Audit/Inventory`、`Audit/NoAxiom`

这意味着：

- 第 0 阶段已完成
- 第 1 阶段已完成前半
- 后续文档应聚焦于“如何避免重复形式化”

## 4. 现成可复用清单

这一节是新版文档的核心。凡在这里列出的对象，默认不从零重证，只做桥接、封装或适配。

### 4.1 可直接复用的 mathlib 成果

#### A. Fibonacci 基础

mathlib 已提供：

- `Nat.fib`
- Fibonacci 递推
- 单调性
- 常用恒等式

来源：

- `Mathlib/Data/Nat/Fib/Basic.lean`

工程决策：

- `Omega/Core/Fib.lean` 不再维护自制 Fibonacci 理论
- 该模块只保留“论文编号约定 <-> `Nat.fib`”的桥接

#### B. Zeckendorf 定理本体

mathlib 已提供：

- `List.IsZeckendorfRep`
- `Nat.greatestFib`
- `Nat.zeckendorf`
- `Nat.zeckendorfEquiv`

来源：

- `Mathlib/Data/Nat/Fib/Zeckendorf.lean`

工程决策：

- 不再重证 “每个自然数有唯一 Zeckendorf 表示”
- `Omega/Folding/Zeckendorf.lean` 只负责论文配置与 `Nat.zeckendorfEquiv` 的桥接

#### C. 重写系统通用基础

mathlib 已提供：

- `Relation.TransGen`
- `Relation.ReflTransGen`
- `Relation.Join`
- `Relation.church_rosser`

来源：

- `Mathlib/Logic/Relation.lean`

工程决策：

- 不再自造关系闭包理论
- 我们只需为论文的单步重写 `Step` 证明局部条件和良基性

#### D. clopen、零维、超度量 uniformity

mathlib 已提供：

- `IsClopen`
- `Clopens`
- ultrametric uniformity 的基础接口
- clopen basis 结果

来源：

- `Mathlib/Topology/Defs/Basic.lean`
- `Mathlib/Topology/Sets/Closeds.lean`
- `Mathlib/Topology/UniformSpace/Ultra/Basic.lean`

工程决策：

- `SPG/Clopen.lean` 不再自己定义一套 clopen 抽象
- 只把论文中的柱集和前缀球嵌入现有拓扑 API

#### E. Cantor 空间基础

mathlib 已提供：

- Cantor set
- Cantor set 与 `ℕ -> Bool` 的等价
- Cantor 空间与其可数乘积的同胚

来源：

- `Mathlib/Topology/Instances/CantorSet.lean`

工程决策：

- 无穷二进制流空间的标准拓扑模型可直接复用
- 我们只需证明论文的 `X_infty` 与该标准模型之间的专用对应

#### F. 逆极限和兼容族的现成模板

mathlib 已提供：

- `DiscreteQuotient.eq_of_forall_proj_eq`
- `DiscreteQuotient.exists_of_compat`
- profinite 作为有限离散对象极限的现成构造

来源：

- `Mathlib/Topology/DiscreteQuotient.lean`
- `Mathlib/Topology/Category/Profinite/AsLimit.lean`

工程决策：

- 不需要自己从零铺设“兼容族存在唯一元”的一般拓扑理论
- 但论文里具体的 `X_infty = lim X_m` 仍需我们自己构造并证明

#### G. 可测空间、乘积测度、条件概率基础

mathlib 已提供：

- `MeasurableSpace` 的 `Pi` / `Prod` / `Quotient` 构造
- 乘积测度
- 有限乘积积分
- 条件概率和相关概率接口

来源：

- `Mathlib/MeasureTheory/MeasurableSpace/Constructions.lean`
- `Mathlib/MeasureTheory/Measure/Prod.lean`
- `Mathlib/MeasureTheory/Integral/Pi.lean`
- `Mathlib/Dynamics/Ergodic/Extreme.lean`

工程决策：

- `SPG` 的测度层不从零建设 measure API
- 后续只做论文事件、柱集和误差表达的接入

### 4.2 只有基础设施可复用，不代表论文结果现成

以下方向虽然 mathlib 有基础件，但论文结论本身并不现成：

- continued fractions 的一般工具
- category-theoretic limits
- CStar 基础类型类
- profinite / light profinite 的一般范畴结果

工程决策：

- 只在需要时局部接入
- 不把这些大基础当作当前关键路径

### 4.3 当前未发现现成替代的部分

以下内容默认仍需项目自行形式化：

- `X_m` 的论文专用编码
- `No11` 与按位操作的专用引理
- `|X_m| = Fibonacci` 针对当前编码的计数桥接
- `Fold_m`
- 论文专用局部 rewrite 规则
- 值保持、终止、局部合流、合流、幂等、满射
- 折叠感知 restriction 和相关交换图
- 论文定义的局部缺陷 `kappa`、全局缺陷 `D`
- 离散 Stokes 型望远镜恒等式
- SPG 的柱集、前缀超度量、扫描误差分解
- `Phi_m`、sofic 图像、右 Fischer cover
- POM、GRH/Chebotarev、CMV、Peter-Weyl、Langlands 等前沿层

## 5. 总体工程原则

### 5.1 复用优先

先问四个问题，再写任何新定义：

1. mathlib 是否已有同义对象？
2. 如果已有，论文是否只需要一个桥接层？
3. 如果已有通用定理，论文是否只需验证专用前提？
4. 如果只是命名不同，是否可以通过 wrapper 解决？

只有四问之后仍无现成替代，才新增本项目定义。

### 5.2 先关系，后函数

对 `Fold_m` 的推进顺序固定为：

1. 定义配置空间与值函数
2. 定义单步重写 `Step`
3. 证明值保持
4. 证明终止和局部合流
5. 借助现成闭包理论得到规范形唯一
6. 再定义 `Fold_m`
7. 再证明幂等、满射和交换图

### 5.3 先有限，再无穷

推进顺序固定为：

- 先 `X m`
- 再 `restrict`
- 再兼容族
- 最后 `X_infty`

不直接从无穷流空间开工。

### 5.4 先组合，再测度

`SPG` 拆成三层：

- 组合层：柱集、前缀决定性、前缀球、clopen
- 离散误差层：有限分布上的误差公式
- 测度层：一般乘积测度、条件概率、边界柱估计

### 5.5 先验证器，再生成器

实验相关对象拆分为：

- Lean 中的证书验证器
- 外部脚本中的证书生成器

Lean 只证明验证器 sound，不负责黑箱搜索。

## 6. 目标工程结构

建议使用如下结构：

```text
lean4/
  lakefile.lean
  lean-toolchain
  Omega.lean
  IMPLEMENTATION_PLAN.md
  Omega/
    Core/
      Fib.lean            -- 只做 Nat.fib 编号桥接
      Word.lean
      No11.lean
      Prefix.lean
      XOR.lean
    Folding/
      StableSyntax.lean
      Weight.lean
      Value.lean
      Zeckendorf.lean     -- 只做桥接，不重证 theorem 本体
      Rewrite.lean
      Fold.lean
      Fiber.lean
      InverseLimit.lean
      Defect.lean
    SPG/
      Cylinder.lean
      PrefixMetric.lean
      Clopen.lean
      ScanErrorDiscrete.lean
      ScanErrorMeasure.lean
    Graph/
      LabeledGraph.lean
      Sofic.lean
    Frontier/
      Assumptions.lean
      Conditional.lean
      Conjectures.lean
      Certificates.lean
    Audit/
      NoAxiom.lean
      Inventory.lean
      SourceMap.lean
```

## 7. 模块职责

### 7.1 `Omega.Core`

职责：

- 固定长度位词
- 截断、拼接、末位、前缀
- `No11`
- 论文编号与 `Nat.fib` 的桥接

禁止：

- 在 `Core` 中重证 Fibonacci 主体理论
- 在 `Core` 中引入拓扑和测度层

### 7.2 `Omega.Folding`

职责：

- `X m`
- Fibonacci 加权值
- 与 `Nat.zeckendorfEquiv` 的桥接
- 专用重写系统
- `Fold_m`
- 纤维、rank/unrank
- 具体逆系统
- 缺陷与望远镜恒等式

### 7.3 `Omega.SPG`

职责：

- 柱集
- 前缀球
- 前缀超度量
- clopen 表达
- 有限前缀决定性
- 扫描误差的离散与测度版本

### 7.4 `Omega.Graph`

职责：

- 为 `Phi_m`、sofic 图像和自动机接口做准备

### 7.5 `Omega.Frontier`

职责：

- 条件性结果
- 猜想声明
- 证书接口

规则：

- 允许 `theorem ... (h : Assumption) : ...`
- 不允许把假设藏成全局事实

### 7.6 `Omega.Audit`

职责：

- `#print axioms` 审计
- theorem inventory
- 论文 label 到 Lean 名称的稳定映射

## 8. 数据表示与桥接策略

### 8.1 固定位词

统一表示为：

```lean
abbrev Word (m : Nat) := Fin m -> Bool
```

理由：

- `truncate` 自然
- 局部模式判断直接
- 有利于 `get`、`snoc`、前缀操作

### 8.2 稳定语法

使用子类型：

```lean
def No11 (w : Word m) : Prop := ...
def X (m : Nat) := { w : Word m // No11 w }
```

### 8.3 Fibonacci 编号

统一工程约定：

- 数值层一律以 `Nat.fib` 为准
- 论文的 `F_1 = F_2 = 1` 记法通过单独桥接处理

这意味着：

- 后续不再扩充自制递推定理库
- `Omega.paperFib` 只应是薄别名

### 8.4 Zeckendorf 桥接

`Folding/Zeckendorf.lean` 的任务不是证明 Zeckendorf theorem，而是证明：

- 论文合法位词如何转为 `List.IsZeckendorfRep`
- `Nat.zeckendorf` 如何回到论文合法位词
- 两套取值函数一致

### 8.5 逆极限策略

对当前项目，优先采用“具体兼容族”方式，而不是一开始重型范畴化。

优先顺序：

1. 先定义 `restrict`
2. 定义兼容族
3. 证明唯一决定无限对象
4. 必要时再与 `DiscreteQuotient` / `Profinite` 的一般理论对接

## 9. 分阶段计划

### 阶段 0：项目引导与审计框架

状态：

- 已完成

交付：

- `Lake + mathlib`
- `Audit/NoAxiom.lean`
- `Audit/SourceMap.lean`
- `lake build`

### 阶段 1：有限词与稳定语法核心

目标：

- 完成 `Word`
- 完成 `No11`
- 完成 `X m`
- 完成 `restrict` / `appendFalse` / `appendTrue`

必须证明：

- `X m` 的良定义
- 末位分解
- restriction 的良定义
- `X (m + 1)` 的递推分解
- `|X m| = paperFib m` 的计数桥接

复用：

- `Fintype`
- `Fin`
- `Nat.fib`

不做：

- 重证一般 Fibonacci 理论

### 阶段 2：权重与 Zeckendorf 桥接

目标：

- 完成 `Weight.lean`
- 完成 `Value.lean`
- 完成 `Zeckendorf.lean`

必须证明：

- 权重函数的定义与递推
- 稳定词取值函数
- 稳定词到 `List.IsZeckendorfRep` 的转换
- `Nat.zeckendorf` 回到稳定词的构造
- 两套表示和值的一致性

复用：

- `Nat.zeckendorf`
- `Nat.zeckendorfEquiv`

不做：

- 重证存在唯一性 theorem 本体

### 阶段 3：局部重写与 `Fold_m`

目标：

- 完成 `Rewrite.lean`
- 完成 `Fold.lean`

必须证明：

- 单步重写值保持
- 强终止
- 局部合流
- 由现成闭包理论得到合流
- 正规形唯一
- `Fold_m` 与正规形一致
- `Fold_m` 幂等
- `Fold_m` 满射

复用：

- `Relation.TransGen`
- `Relation.ReflTransGen`
- `Relation.church_rosser`

### 阶段 4：多尺度一致性与缺陷代数

目标：

- 完成 `InverseLimit.lean`
- 完成 `Defect.lean`

必须证明：

- `restrict` 的函子性
- 具体兼容族的存在唯一性
- 论文中的折叠感知交换图
- 局部缺陷 `kappa`
- 全局缺陷 `D`
- 离散 Stokes 型望远镜恒等式

复用：

- `DiscreteQuotient.exists_of_compat`
- profinite / limit 现成模板，仅在需要时接入

### 阶段 5：SPG 组合层

目标：

- 完成 `Cylinder.lean`
- 完成 `PrefixMetric.lean`
- 完成 `Clopen.lean`

必须证明：

- 柱集定义
- 柱集与前缀球对应
- 有限前缀决定性
- clopen 表达

复用：

- `IsClopen`
- `Clopens`
- Cantor 空间现成拓扑基础
- ultrametric uniformity 基础

### 阶段 6：SPG 离散误差层与测度接入

目标：

- 完成 `ScanErrorDiscrete.lean`
- 视情况增加 `ScanErrorMeasure.lean`

必须证明：

- 有限分布上的扫描误差
- 柱分解公式
- 单调性和零误差判据
- 必要时接入一般乘积测度版本

复用：

- `MeasurableSpace` `Pi` / `Prod`
- product measure
- 条件概率基础

### 阶段 7：图像、sofic 与自动机

目标：

- 完成 `Graph/LabeledGraph.lean`
- 完成 `Graph/Sofic.lean`

说明：

- 本阶段目前没有本地现成库可直接代替
- 只有前六阶段稳定后才进入

### 阶段 8：条件性与证书层

目标：

- `Assumptions`
- `Conditional`
- `Conjectures`
- `Certificates`

说明：

- POM、GRH/Chebotarev、实验结果全部放在此层

## 10. 明确不再做的事情

以下事项从新版计划中明确移除：

- 自己重证 `Nat.fib` 的一般理论
- 自己重证 Zeckendorf theorem 本体
- 为了一个具体结论先铺一整套 category theory limits
- 在核心层提前引入完整测度论或算子代数
- 把前沿叙述层伪装成已证核心定理

## 11. 第一批必须闭环的 theorem backlog

新版 backlog 聚焦于“论文专用不可替代内容”：

1. `X m` 对截断封闭
2. `X (m + 1)` 的末位递推分解
3. `|X m| = paperFib m`
4. 稳定词权重递推
5. 稳定词表示到 `List.IsZeckendorfRep` 的桥接
6. `Nat.zeckendorf` 到稳定词的回译
7. 两套表示的值一致
8. 单步重写值保持
9. 重写系统强终止
10. 重写系统局部合流
11. 重写系统合流
12. 正规形唯一
13. `Fold_m` 幂等
14. `Fold_m` 满射
15. `restrict` 的函子性
16. 具体兼容族存在唯一元
17. 折叠感知 restriction 交换图
18. 局部缺陷与全局缺陷定义
19. 离散 Stokes 型望远镜恒等式
20. 柱集与前缀球对应
21. 有限前缀决定性的 clopen 表达
22. 有限分布上的扫描误差分解

## 12. 质量闸门

每个阶段结束前必须满足：

- `lake build` 全量通过
- 核心层无 `admit`
- 核心定理可做 `#print axioms`
- theorem 名称与 `SourceMap` 一致
- 小规模例子可由 `#eval` 或 `native_decide` 验证
- 文档明确标记“复用项”和“项目自证项”

## 13. 命名与映射规范

### 13.1 模块命名

使用英文稳定模块名，例如：

- `Omega.Folding.StableSyntax`
- `Omega.Folding.Zeckendorf`
- `Omega.Folding.Rewrite`
- `Omega.SPG.PrefixMetric`

### 13.2 theorem 命名

采用 “对象 + 结论” 风格，例如：

- `stableSyntax_card`
- `zeckendorfBridge_sound`
- `fold_rewrite_confluent`
- `fold_idempotent`
- `defect_telescope`

### 13.3 SourceMap 状态

建议状态值：

- `planned`
- `bridged`
- `formalized`
- `blocked`
- `deferred`
- `frontier`

其中：

- `bridged` 表示 theorem 本体来自 mathlib，本项目只完成桥接

## 14. 风险清单

### 风险 1：继续重复造轮子

应对：

- 开工前先查 mathlib
- 未确认缺失前不新增基础定义

### 风险 2：论文编号与 mathlib 编号漂移

应对：

- 一律以 `Nat.fib` 为数值真源
- 论文编号只保留桥接层

### 风险 3：把通用 machinery 当成论文结果

应对：

- 文档中明确区分 “通用基础” 和 “论文专用结论”

### 风险 4：过早范畴化

应对：

- 先做具体逆系统
- 只有需要复用一般极限理论时再接入

### 风险 5：过早测度化

应对：

- 先完成组合层和离散误差层
- 测度层延后

## 15. 下一步的直接执行顺序

从当前状态继续推进时，顺序应为：

1. 把 `Omega/Core/Fib.lean` 改成 `Nat.fib` 的薄桥接
2. 完成 `X m` 的计数递推和 `|X m| = paperFib m`
3. 新建 `Folding/Zeckendorf.lean`，只做桥接层
4. 进入 `Rewrite.lean`
5. 再进入 `Fold.lean`
6. 然后做 `InverseLimit.lean` 与 `Defect.lean`
7. 最后做 `SPG` 组合层

严禁倒序推进。

## 16. 结论

新版实施方案的核心思想是：

- mathlib 已有的，直接复用
- 论文专用的，集中火力证明
- 通用基础和专用结论严格分层

这样推进后，`lean4/` 项目会形成一个小而硬的无公理核心，而不是继续在 Fibonacci、Zeckendorf、一般闭包理论这些已现成的基础轮子上消耗时间。
