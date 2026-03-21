# Lean4 无公理形式化实施方案

## 1. 文档目的

本文档给出 `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence` 向 `/lean4` 迁移的完整实施方案，目标不是把整篇论文逐段翻译为 Lean，而是构造一个可以持续生长、可审计、无项目自定义公理的 Lean4 形式化工程。

本文档同时规定：

- 形式化边界
- 工程结构
- 分阶段交付
- 证明策略
- 质量闸门
- 风险与暂停条件

## 2. 核心目标

### 2.1 总目标

构建一个 Lean4 项目，使其在不引入项目自定义公理的前提下，形式化论文中的离散核心，并为后续条件性结果、证书验证器和实验接口提供稳定基座。

### 2.2 “无公理”的工程定义

本项目中的“无公理”定义为：

- 不新增 `axiom`
- 不新增以未证命题充当事实的 `constant`
- 不把猜想、经验规律、实验结论写成无条件 `theorem`
- 核心层定理均通过 `#print axioms` 检查，不依赖项目自定义事实

允许使用：

- Lean4 内核逻辑
- mathlib 的既有定义、定理、类型类和战术
- 条件性定理，即将前提显式写入定理参数

不承诺：

- 完全避免 Lean 基础逻辑或 mathlib
- 在第一阶段形式化所有分析、概率、算子代数、Langlands 或 GRH 相关内容

## 3. 源材料分层

根据当前论文结构，必须先区分“可直接无公理形式化”的内核与“暂不进入核心层”的部分。

### 3.1 第一优先级：离散可计算核心

这些内容适合先落到 Lean 核心层：

- 稳定语法 `X_m = {0,1}^m` 且禁止相邻 `11`
- Fibonacci 序列与计数递推
- Zeckendorf 规范形
- `Fold_m` 的定义
- 局部重写系统
- 终止性、合流性、顺序无关
- 幂等、满射、规范性
- restriction、inverse limit
- 局部缺陷 `κ` 与全局缺陷 `D`
- 离散 Stokes 型望远镜恒等式
- rank/unrank、前缀覆盖数、纤维计数
- 柱集、前缀超度量、有限前缀决定性

对应论文锚点：

- `sections/body/folding/subsec__folding-fibonacci-stable-syntax.tex`
- `sections/body/folding/subsec__folding-map.tex`
- `sections/body/folding/subsec__folding-multiscale.tex`
- `sections/body/spg/sec__spg.tex`

### 3.2 第二优先级：标准数学外延层

这些内容可以在核心层稳定后接入：

- Markov 常数、badly approximable 的基本定义
- 前缀柱代数上的可测事件表达
- 条件概率、误差剖面、Bayes 最优表达
- 有界测度条件下的边界柱估计
- 有限状态系统、sofic 图像、右 Fischer cover

这部分依赖 mathlib 的现成分析/概率/动力系统基础。可以做，但不应阻塞第一阶段。

### 3.3 第三优先级：条件性和前沿层

这些内容不进入第一阶段核心交付：

- POM 大章的统一语言与高阶接口
- 算子代数桥接
- CMV、Peter-Weyl、Artin 因子化
- GRH/Chebotarev 型条件定理
- Langlands、Lee-Yang、谱刚性等高层叙述

这类内容未来可以采用三种形式进入工程：

- 条件性定理
- 证书验证器
- conjecture namespace

## 4. 总体工程原则

### 4.1 先定义，再增殖

项目成功的关键不是“先挑大定理”，而是先把高繁殖率定义做好。高繁殖率定义满足：

- 可计算
- 可判定
- 有规范形
- 有局部重写
- 有有限层截断
- 有逆极限或通用性质

### 4.2 核心层与边界层分离

工程必须从一开始就分成三层：

- `Core`：纯离散、纯构造、无项目公理
- `Derived`：从核心层自然派生的结构定理
- `Frontier`：条件性定理、猜想、证书接口、实验对接

### 4.3 证明优先于叙述

所有进入 Lean 的对象必须先被重写为：

- 精确类型
- 精确输入输出
- 明确前提
- 明确结论
- 明确依赖

任何叙述性、解释性、物理化语言都不得直接进入核心证明对象。

### 4.4 小步闭环

每个阶段都必须闭环到可编译、可检查、可验收的状态，不做“先堆大量草稿，再统一修复”的推进方式。

## 5. 目标工程结构

建议的 Lean4 目录结构如下：

```text
lean4/
  lakefile.lean
  lean-toolchain
  Omega.lean
  IMPLEMENTATION_PLAN.md
  Omega/
    Core/
      Fib.lean
      Word.lean
      No11.lean
      Prefix.lean
      XOR.lean
    Folding/
      StableSyntax.lean
      Zeckendorf.lean
      Weight.lean
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

## 6. 模块职责

### 6.1 `Omega/Core`

职责：

- 提供基础有限对象
- 固定比特词表示
- 定义前缀、截断、拼接、逐位异或
- 建立 `DecidableEq`、`Fintype`、枚举工具

建议约束：

- 尽量仅依赖 `Nat`、`Fin`、`List`、`Vector`、`Finset`
- 避免在核心位词层过早引入测度和拓扑

### 6.2 `Omega/Folding`

职责：

- 形式化稳定语法 `X_m`
- Fibonacci 权重与取值
- Zeckendorf 规范形
- 局部重写系统
- `Fold_m`
- 纤维、rank/unrank
- restriction、inverse limit
- 局部/全局缺陷与望远镜公式

这是整个项目的主发动机。

### 6.3 `Omega/SPG`

职责：

- 柱集
- 前缀决定性
- 前缀超度量
- clopen 性
- 有限前缀决定事件的离散表达
- 离散扫描误差的第一批可计算版本

第一阶段仅做组合层；测度和条件概率延后。

### 6.4 `Omega/Graph`

职责：

- 为后续 `Φ_m` 图像、sofic 表示、右分辨自动机做准备
- 第一批只需要最小图论接口，不做泛化过度

### 6.5 `Omega/Frontier`

职责：

- 记录条件性结果的前提结构
- 存放猜想声明
- 存放实验输出对应的可验证证书接口

规则：

- 这里可以有 `theorem (h : Assumption) : ...`
- 这里不能把假设藏成全局事实

### 6.6 `Omega/Audit`

职责：

- 管理“无公理”审计
- 维护源文档到 Lean 命名的映射
- 维护 theorem inventory

## 7. 数据表示与基础设计

### 7.1 有限词表示

建议统一采用固定长度表示，而不是混用 `List Bool` 与字符串：

- 长度为 `m` 的词：`Fin m -> Bool`
- 或者 `Vector Bool m`

推荐优先用 `Fin m -> Bool`，理由：

- 前缀截断自然
- 点态定义方便
- 逐位异或、拼接、局部模式判断更直接

必要时可提供与 `Vector Bool m` 的等价接口。

### 7.2 稳定语法 `X_m`

定义为带性质的子类型：

```lean
def No11 (w : Fin m -> Bool) : Prop := ...
def X (m : Nat) := { w : Fin m -> Bool // No11 w }
```

这样可以直接获得：

- 幂等性的目标类型
- restriction 的良定义
- inverse limit 的兼容结构

### 7.3 Fibonacci

统一固定一个项目内部 Fibonacci 约定，并全项目只用一种编号。

建议：

- 明确写出项目中的 `Fib 0`, `Fib 1`
- 再给出与论文 `F_1 = F_2 = 1` 记号的桥接引理

不要直接把论文编号原样移植而不做对齐，否则后续全工程会不断出现移位错误。

### 7.4 Zeckendorf

必须把 Zeckendorf 规范形拆成两层：

- 数值层：自然数到数字配置
- 规范层：合法配置的唯一性

不要一开始就把 Zeckendorf 作为黑箱函数使用。应优先证明：

- 合法表示存在
- 合法表示唯一
- 局部重写保持数值
- 不可约项就是合法表示

### 7.5 重写系统

重写系统应显式表示为单步关系：

```lean
inductive Step : Config -> Config -> Prop
```

再分别证明：

- 值保持
- 强终止
- 局部合流
- 合流
- 正规形唯一

不要把“归约后结果”直接写成递归函数而跳过关系层，否则后面很多结构定理会失去复用性。

## 8. 形式化策略

### 8.1 第一原则：先关系，后函数

对于 `Fold_m`，建议顺序：

1. 定义配置空间与值函数
2. 定义单步重写
3. 证明终止与合流
4. 定义正规形
5. 再定义 `Fold_m`
6. 再证明幂等、满射、交换图

### 8.2 第二原则：先有限，再无穷

顺序必须是：

- 先 `X_m`
- 再 `π_{m2→m1}`
- 再兼容族
- 最后 `X_∞ ≅ lim X_m`

不要一开始直接上无穷词空间和极限对象。

### 8.3 第三原则：先组合，再测度

`SPG` 的扫描误差部分必须拆开：

- 第一层：柱集、clopen、前缀决定性、可计算误差函数
- 第二层：在有限分布上定义误差
- 第三层：一般测度、条件期望、鞅表达

如果一开始直接用一般测度空间，会极大拖慢项目。

### 8.4 第四原则：先验证器，再证书生成器

实验相关对象应分为：

- Lean 里的验证器
- 外部脚本里的证书生成器

Lean 负责证明：

- 证书格式正确时结论成立
- 验证器判真时，对应性质确实为真

Python 或脚本只负责：

- 搜索
- 枚举
- 导出证书

## 9. 分阶段计划

### 阶段 0：项目引导与审计框架

目标：

- 初始化 `Lake`
- 接入 `mathlib`
- 建立 `Omega.lean`
- 建立 `Audit/NoAxiom.lean`
- 建立源码映射清单

交付：

- `lake build` 可通过
- 目录结构稳定
- `SourceMap` 可记录论文 label 到 Lean 名称

验收：

- 核心模块可空编译
- CI 命令固定

### 阶段 1：有限词与稳定语法核心

目标：

- 完成 `Core/Word.lean`
- 完成 `Core/No11.lean`
- 完成 `Folding/StableSyntax.lean`

必须证明：

- `X_m` 的良定义
- 尾位分解
- `X_m^(1)` 与 `X_m^(0)` 的递推
- `|X_m|` 的 Fibonacci 计数
- restriction 对 `X_m` 良定义

验收：

- 所有定理不依赖项目自定义公理
- 小规模枚举与理论计数一致

### 阶段 2：Fibonacci 权重与 Zeckendorf 基础

目标：

- 完成 `Core/Fib.lean`
- 完成 `Folding/Weight.lean`
- 完成 `Folding/Zeckendorf.lean`

必须证明：

- Fibonacci 基本恒等式
- 加权值 `N(ω)` 的定义
- 合法 Zeckendorf 配置的值函数
- 合法表示存在与唯一
- 截断映射与有限区间双射

验收：

- 可以在 Lean 中从 `Nat` 恢复规范形
- 可跑小规模 `native_decide` 验证

### 阶段 3：局部重写与 `Fold_m`

目标：

- 完成 `Folding/Rewrite.lean`
- 完成 `Folding/Fold.lean`

必须证明：

- 单步重写值保持
- 强终止
- 局部合流
- 合流
- 正规形唯一
- `Fold_m` 与正规形一致
- `Fold_m` 规范性
- `Fold_m` 幂等
- `Fold_m` 满射

验收：

- 论文 `def:fold-word`、`prop:fold-rewrite-newman`、`prop:fold-basic` 对应的 Lean 版本闭合

### 阶段 4：多尺度一致性与缺陷代数

目标：

- 完成 `Folding/InverseLimit.lean`
- 完成 `Folding/Defect.lean`

必须证明：

- `π_{m2→m1}` 的函子性
- `X_∞ ≅ lim X_m`
- 直接截断不交换的反例
- 折叠感知 restriction 的交换图
- 局部缺陷 `κ`
- 全局缺陷 `D`
- 离散 Stokes 望远镜恒等式
- 并合界或简单误差界

验收：

- 论文 `thm:inverse-limit-golden`、`prop:fold-omega-commute`、`thm:fold-discrete-stokes-defect` 具备 Lean 版本

### 阶段 5：纤维、复杂度与 rank/unrank

目标：

- 完成 `Folding/Fiber.lean`

必须证明：

- 纤维计数上界
- 合法词 `rank/unrank`
- 直积分量的混合进制 rank/unrank
- 线性时间结构的规范陈述

说明：

- 与 Kolmogorov complexity 相关的表述先降级为“可编码长度上界”
- 复杂度常数项不作为第一阶段证明目标

### 阶段 6：SPG 组合层

目标：

- 完成 `SPG/Cylinder.lean`
- 完成 `SPG/PrefixMetric.lean`
- 完成 `SPG/Clopen.lean`

必须证明：

- 柱集定义
- 前缀深度
- 前缀超度量
- 球与柱集对应
- 有限前缀决定性
- `A_m` 中集合可表为长度 `m` 柱集并

验收：

- `prop:spg-decidable-clopen` 的组合版本成立

### 阶段 7：SPG 离散误差层

目标：

- 完成 `SPG/ScanErrorDiscrete.lean`

必须证明：

- 在有限分布上定义扫描误差
- 柱分解的精确表达
- 单调性
- 在可决定事件上的零误差判据

说明：

- 一般测度与条件期望版本放到下一阶段

### 阶段 8：标准分析与概率接入

目标：

- 选择性接入 mathlib 的测度与概率工具

候选任务：

- 条件概率版本的误差表达
- Tanaka-Stokes 公式的测度版本
- 边界柱估计
- badly approximable 与星差异的基本接入

暂停条件：

- 若 mathlib 现成工具不足
- 若为了一个定理需要铺设过重基础设施

则该阶段拆分为更小的目标，绝不倒逼核心层返工。

### 阶段 9：图像、sofic 与自动机

目标：

- 形式化 `Φ_m`
- 构造显式图像
- 右分辨表示与最小化接口

说明：

- 此阶段可能需要额外图论基础
- 只有当前八阶段稳定后再进入

### 阶段 10：条件性与证书层

目标：

- 为 POM、GRH/Chebotarev、实验产物提供统一容器

交付形式：

- `structure Assumption`
- `theorem ... (h : Assumption) : ...`
- `def Certificate`
- `def verifyCertificate`
- `theorem verifyCertificate_sound : ...`

## 10. 里程碑与交付顺序

### M0：工程可编译

完成阶段 0。

### M1：折叠核心闭环

完成阶段 1 到阶段 3。

这是第一批真正有研究价值的可发布核心。

### M2：多尺度闭环

完成阶段 4 和阶段 5。

这是“项目会自然长定理”的关键里程碑。

### M3：SPG 组合闭环

完成阶段 6 和阶段 7。

此时可以开始将论文中的 `spg` 章节稳定映射到 Lean。

### M4：分析接入

完成阶段 8。

### M5：图像与自动机

完成阶段 9。

### M6：前沿层接口

完成阶段 10。

## 11. 每阶段的质量闸门

每个阶段结束前必须满足以下条件：

- `lake build` 全量通过
- 新增核心定理可通过 `#print axioms` 检查
- theorem 名称与 SourceMap 一致
- 无临时 `admit`
- 无注释掉的关键证明
- 小规模计算例由 `#eval` 或 `native_decide` 给出
- 文档中明确标记已完成和未完成范围

## 12. 命名与映射规范

### 12.1 模块命名

Lean 模块名使用英文，保持稳定、可检索。

例如：

- `Omega.Folding.StableSyntax`
- `Omega.Folding.Rewrite`
- `Omega.Folding.Defect`
- `Omega.SPG.Cylinder`

### 12.2 定理命名

定理名采用“模块语义 + 结论”方式，不直接照搬论文长标题。

例如：

- `stableSyntax_terminalRecursion`
- `fold_rewrite_confluent`
- `fold_idempotent`
- `inverseLimit_equiv_XInfinity`
- `defect_telescope`

### 12.3 SourceMap

必须维护一份映射表，字段至少包括：

- 论文 label
- 论文文件路径
- Lean 名称
- 所属模块
- 当前状态
- 依赖阶段

状态建议枚举：

- `planned`
- `formalized`
- `blocked`
- `deferred`
- `frontier`

## 13. 证明工程约定

### 13.1 优先工具

优先使用：

- 结构归纳
- 有限枚举
- `simp`
- `omega`
- `linarith`
- `native_decide`
- `aesop` 作为辅助而非主依赖

### 13.2 限制

限制使用：

- 过度依赖 `simp_all`
- 大段不可维护的 tactic script
- 把核心证明交给不透明自动化

### 13.3 证明风格

建议：

- 定义性引理短小
- 每个关键定理前先准备若干局部 lemma
- 将计算引理与结构引理分开

## 14. 自动化与枚举策略

“自己生长定理”的关键在于把大量有限情形变成机械可判定对象。

建议在核心层准备：

- 有限词枚举器
- 合法词判定器
- `Fold_m` 计算器
- 纤维枚举器
- 缺陷枚举器

这些工具的用途：

- 生成 `#eval` 示例
- 验证小规模猜想
- 支持 `native_decide` 的可判定定理
- 为后续外部证书生成器提供规范接口

## 15. CI 与检查命令

建议固定以下工作流：

```bash
lake build
lake env lean Omega/Audit/NoAxiom.lean
```

建议在 `NoAxiom.lean` 中集中放置对核心定理的 `#print axioms` 检查说明。

后续如接入 CI，至少应包含：

- `lake build`
- 格式检查
- 核心模块无 `axiom` 扫描

## 16. 风险清单

### 风险 1：源论文体量过大

应对：

- 严格按阶段切分
- 只把高繁殖率核心放入前四阶段

### 风险 2：编号和记号漂移

应对：

- 统一 Fibonacci 编号
- 统一位词方向
- 统一前缀截断约定

### 风险 3：过早引入重分析基础

应对：

- 先做离散版
- 测度版单独排期

### 风险 4：把叙述性内容误当定理

应对：

- 所有条目先重写为机器化命题
- 无法重写者直接进入 `Frontier`

### 风险 5：实验与证明边界混淆

应对：

- 证书生成与证书验证分离
- Lean 只证明验证器正确

## 17. 暂不实施清单

以下内容明确不进入第一阶段：

- 全量 POM 形式化
- 全量 `group_unification`
- GRH/Chebotarev 高层桥接
- Langlands、Peter-Weyl、CMV、算子代数大规模铺设
- 所有 conjecture 的证明化

这些内容只有在核心层稳定后才会逐步转入 `Frontier` 或后续阶段。

## 18. 第一批 theorem backlog

建议优先落地以下最小可行定理集：

1. `X_m` 对前缀截断封闭
2. `X_m` 尾位递推
3. `|X_m| = Fibonacci`
4. 局部重写值保持
5. 重写系统强终止
6. 重写系统局部合流
7. 重写系统合流
8. 正规形唯一
9. `Fold_m` 规范性
10. `Fold_m` 幂等
11. `Fold_m` 满射
12. `π` 的函子性
13. `X_∞ ≅ lim X_m`
14. 直接截断不交换的显式反例
15. 折叠感知 restriction 的交换图
16. 局部缺陷与全局缺陷定义
17. 离散 Stokes 望远镜恒等式
18. 合法词 `rank/unrank`
19. 柱集与前缀球对应
20. 有限前缀决定性的 clopen 表达

如果这 20 个条目闭环，项目就已经具备“可持续长出大量定理”的内核。

## 19. 执行顺序建议

建议实际执行时按以下顺序推进：

1. 建项目骨架
2. 固定位词与 Fibonacci 编号
3. 完成 `X_m`
4. 完成 Zeckendorf
5. 完成重写系统
6. 完成 `Fold_m`
7. 完成 inverse limit
8. 完成缺陷望远镜公式
9. 完成 SPG 组合层
10. 再考虑分析和概率

严禁倒序推进。

## 20. 阶段完成的判据

可以认为 Lean4 核心项目“已经起飞”的标志是同时满足以下条件：

- `Fold_m` 主线已闭环
- `X_∞ ≅ lim X_m` 已成立
- 缺陷代数已可计算
- SPG 的前缀组合层已闭环
- 核心层定理无项目自定义公理
- SourceMap 能清楚显示已完成条目与 frontier 条目

满足这些条件后，项目才真正具备“自己生长出很多定理”的能力。

## 21. 结论

本项目不应被理解为“整篇论文的机械翻译”，而应被理解为：

- 先抽取论文的离散生成核
- 再把生成核变成 Lean 中的规范化、可计算、可判定对象
- 再让大量结构定理从这些定义中自然派生
- 最后用条件性定理和证书接口向高层章节扩张

如果严格执行本文档，`lean4` 项目会先形成一个小而硬的无公理核心，然后再向论文更大范围稳态扩展，而不是在一开始就被高层桥接叙述拖垮。
