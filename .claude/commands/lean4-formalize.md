# Lean4 形式化团队编排

你是 lean4-formalization 团队的 Team Lead。执行一轮完整的论文→Lean4形式化循环。

## 环境

- 论文目录：`docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/`
- Lean4目录：`lean4/`
- 实施方案：`lean4/IMPLEMENTATION_PLAN.md`

## 每轮循环流程

### Phase 0：选取目标

1. 读取 `lean4/IMPLEMENTATION_PLAN.md` 的 §4 执行优先级
2. 选取最高优先级的未完成计划项
3. 确定该计划项涉及的具体论文定理（标签、章节、LaTeX文件路径）

### Phase 1：分析（analyst）

派遣 `lean4-analyst` agent（Plan型，只读）：

```
分析以下论文定理的Lean4形式化规格：

目标计划项：[计划编号和名称]
论文定理标签：[thm:xxx, prop:yyy, ...]
论文LaTeX路径：[sections/body/.../xxx.tex]
现有Lean4代码：lean4/Omega/

请生成精确的形式化规格，包括：
- Lean4类型签名
- 依赖链（已有定理 + mathlib引理）
- 目标文件位置
- 推荐证明策略
```

收到规格后检查：依赖链中是否有未形式化的前置条件？如果有，先形式化前置条件。

### Phase 2：实现（formalizer）

派遣 `lean4-formalizer` agent（通用型，读写）：

```
按照以下规格实现Lean4形式化：

[粘贴analyst的完整规格]

硬约束：
- 零sorry、零admit、零axiom
- lake build必须通过
- 文件不超过800行
- 最多15轮编译循环
```

收到结果后检查：formalizer报告成功还是失败？
- 成功 → 进入Phase 3
- 失败 → 记录失败原因，跳过该定理，选取下一个目标

### Phase 3：审核（reviewer）

派遣 `lean4-reviewer` agent（通用型，读写）：

```
审核formalizer的最新修改：

新增定理：[列表]
修改文件：[列表]
对应论文定理：[标签和LaTeX原文]
analyst规格：[规格摘要]

执行全部7个Gate检查（全部硬阻断）：
1. 编译通过
2. 零sorry/admit
3. 零新增axiom
4. 论文对应性
5. 命名风格
6. 文件大小
7. Codex外部审核
```

收到结果后检查：
- 全部PASS → 进入Phase 4
- 有FAIL → 将修复指令发回formalizer，回到Phase 2（最多3轮）
- 3轮修复仍失败 → 回退代码，跳过该定理

### Phase 4：登记（registrar）

派遣 `lean4-registrar` agent（通用型，读写）：

```
审核已通过，执行登记和提交：

新增定理清单：[从reviewer报告中提取]
对应论文标签：[列表]
修改文件：[列表]

更新以下文件：
1. Audit/SourceMap.lean
2. Audit/NoAxiom.lean
3. IMPLEMENTATION_PLAN.md
4. Omega.lean（如需要）

然后 git commit + push。
```

### Phase 5：循环控制

1. 记录本轮结果（成功/失败/跳过）
2. 检查总覆盖率进展
3. 如果仍有未完成项 → 回到 Phase 0
4. 如果全部完成 → 报告总结

## 错误恢复

- formalizer失败：跳过当前定理，记录原因，继续下一个
- reviewer反复失败（3轮）：回退代码到本轮开始状态，跳过
- registrar失败：手动检查git状态，修复后重试
- 任何agent无响应：重新派遣，使用相同输入

## 进度报告

每轮结束后输出：
```
═══ 第N轮形式化完成 ═══
目标：[计划项]
状态：成功/失败/跳过
新增定理：[数量]
覆盖率变化：[章节 X% → Y%]
总覆盖率：~Z%
下一目标：[计划项]
═══════════════════════
```
