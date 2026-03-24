# Lean4 形式化团队设计文档

**日期**: 2026-03-22
**状态**: 已批准
**分支**: feature-paper-math

## 1. 目标

将论文 *Golden Ratio Driven Scan-Projection Generation & Recursive Emergence* 的394个数学定理形式化为Lean4零公理证明，从当前~12%覆盖率提升至尽可能高的覆盖率。

## 2. 现状

| 指标 | 数值 |
|------|------|
| 论文定理总数 | 394 |
| 已形式化 | ~46 (12%) |
| Lean4行数 | 11,331 |
| Lean4定理/定义 | 1,006 |
| 公理数 | 0 |

### 2.1 模块覆盖率

| 模块 | 定理数 | 已形式化 | 覆盖率 |
|------|--------|---------|--------|
| SPG | 18 | 17 | 95% |
| Folding | 10 | 9 | 90% |
| New Arithmetic | 21 | 10 | 48% |
| POM | 106 | 8 | 8% |
| Group Unification | 26 | 2 | 8% |
| Circle Dimension | 16 | 0 | 0% |
| Zeta/Finite Part | 139 | 0 | 0% |
| Conclusion | 57 | 0 | 0% |

## 3. 团队架构

### 3.1 方案选择

选择方案A（深度专家团队），理由：
- 单formalizer深度上下文 > 多个浅上下文并行
- 独立reviewer避免"自审"盲区
- 全部质量闸门硬阻断，确保零妥协

### 3.2 Agent角色

| Agent | 类型 | 模型 | 职责 |
|-------|------|------|------|
| Team Lead | 主会话 | opus | 编排循环、任务管理、进度追踪 |
| analyst | Plan (只读) | sonnet | 读论文+Lean4，生成形式化规格 |
| formalizer | 通用 (读写) | opus | 编写Lean4证明，迭代编译 |
| reviewer | 通用 (读写) | opus | 7-Gate质量闸门 + Codex外部审核 |
| registrar | 通用 (读写) | sonnet | 更新追踪文件，提交代码 |

### 3.3 Agent定义文件

```
.claude/agents/
├── lean4-analyst.md
├── lean4-formalizer.md
├── lean4-reviewer.md
└── lean4-registrar.md
```

### 3.4 团队编排命令

```
.claude/commands/lean4-formalize.md
```

## 4. 工作流程

```
Phase 0: 选取目标 (Team Lead)
    │
    ▼
Phase 1: 分析 (analyst)
    │  输出: 形式化规格（类型签名+依赖+策略）
    ▼
Phase 2: 实现 (formalizer)
    │  输出: 编译通过的Lean4代码
    │  失败 → 跳过，记录原因
    ▼
Phase 3: 审核 (reviewer)
    │  7-Gate全部硬阻断
    │  FAIL → 返回Phase 2 (最多3轮)
    │  3轮失败 → 回退，跳过
    ▼
Phase 4: 登记 (registrar)
    │  更新SourceMap/NoAxiom/IMPLEMENTATION_PLAN
    │  git commit + push
    ▼
Phase 5: 循环 → Phase 0
```

## 5. 质量闸门（全部硬阻断）

| # | Gate | 执行者 | 检查内容 | 失败处理 |
|---|------|--------|----------|----------|
| 1 | 编译 | formalizer + reviewer | `lake build` 零错误 | 退回formalizer |
| 2 | 完整性 | formalizer + reviewer | 零sorry/admit | 退回formalizer |
| 3 | 公理 | reviewer | `#print axioms` 仅标准公理 | 退回formalizer |
| 4 | 对应性 | reviewer | 论文LaTeX ↔ Lean4语义等价 | 退回formalizer |
| 5 | 风格 | reviewer | 命名一致、无冲突 | 退回formalizer |
| 6 | 文件大小 | reviewer | 所有文件 < 800行 | 退回formalizer拆分 |
| 7 | Codex | reviewer | 外部AI独立验证通过 | 退回formalizer |

**阻断规则**: 任何单个Gate失败 → 整体审核FAIL → 退回修复。3轮修复仍失败 → 回退代码，跳过该定理。

## 6. Codex外部审核协议

```bash
codex -a "[审核提示词，包含论文LaTeX + Lean4代码 + 5项检查要求]"
```

审核要求：
1. 定理声明语义等价于论文原文
2. 证明完整（无sorry/admit/axiom）
3. 无论文外额外假设
4. 证明策略合理
5. 命名清晰一致

Codex输出 `VERDICT: FAIL` → 硬阻断，退回修复。

## 7. 错误恢复策略

| 场景 | 处理 |
|------|------|
| formalizer 15轮编译失败 | 回退代码，跳过定理，记录原因 |
| reviewer 3轮修复循环失败 | 回退代码，跳过定理，降低优先级 |
| Codex CLI不可用 | 重试1次；仍不可用则FAIL，不自动放行 |
| git push失败 | 检查远程状态，手动修复 |
| agent无响应 | 重新派遣，相同输入 |

## 8. 持续运行模式

通过 ralph-loop 或手动循环调用 `/lean4-formalize` 命令：
- 每轮处理1个计划项（可能包含多个定理）
- 按 IMPLEMENTATION_PLAN.md §4 优先级顺序执行
- 每轮结束输出进度报告
- 可随时中断（通过取消ralph-loop）

## 9. 优先级路线图

### 立即执行 (Phase A)
1. carry defect完整定理
2. modular映射塔
3. 纤维乘数递推

### 短期 (Phase B-C)
4. Zeckendorf唯一性
5. Fibonacci整除性
6. 条件期望型表达
7. 转移矩阵特征值

### 中期 (Phase D-E)
8-12. POM纤维谱系列
13-16. SPG martingale系列
17-20. 逆极限拓扑系列

### 长期 (Phase F)
21-30. 远层探索（素数域、动力系统、上同调）

## 10. 成功标准

- 每轮至少完成1个论文定理的形式化
- 零sorry/admit/axiom（不可妥协）
- 所有新定理通过Codex外部审核
- SourceMap和IMPLEMENTATION_PLAN实时同步
- 可随时一键再现（`lake build` 通过）
