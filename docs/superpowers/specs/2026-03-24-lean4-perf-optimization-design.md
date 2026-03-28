# Lean4 编译性能自动优化设计

## 问题

Lean4 项目（23K+ 行）编译缓慢，主要瓶颈是 ~380 处 `native_decide` 调用。Top 5 文件：FiberSpectrum(60), MomentSum(51), ZeckendorfSignature(50), CollisionZeta(50), CollisionZetaOperator(32)。每次 `native_decide` 需要 Lean 编译器生成并执行原生代码验证命题，对有限集枚举尤其昂贵。

## 方案：混合式自动优化

采用 formalizer 每轮轻量自检 + 每5轮深度优化 agent 的混合方案。

---

## 一、Formalizer 轻量自检（每轮内嵌）

### 变更位置

`lean4-formalizer.md` 工作流程，在"完整性检查"（第4步）之后、"文件大小检查"（第5步）之前插入。

### 步骤 4.5：native_decide 轻量优化

1. 统计本轮新增的 `native_decide` 调用数
2. 如果 ≥ 3 个且为**纯数值等式验证**（形如 `X = Y` 其中 X、Y 可归约为具体数值），则：
   - 将每个 native_decide 结果提取为独立的 `@[simp]` 引理（命名格式：`原定理名_val_N`）
   - 原定理中的 `native_decide` 替换为 `simp [原定理名_val_0, ...]`
   - 重新 `lake build` 确认通过
3. 如果 < 3 个或非纯数值类型 → 跳过，留给深度优化处理

### 不做的事

- 不触碰本轮以外的文件
- 不重构已有代码

---

## 二、lean4-optimizer Agent（每5轮深度优化）

### 角色定义

新建 `.claude/agents/lean4-optimizer.md`，按需 spawn，短生命周期。

### 触发条件

每5轮自动触发（team lead 在 Phase 5 循环控制中计数，轮次 % 5 == 0 时触发）。

### 工作流程

1. **扫描**：遍历所有 `.lean` 文件，按 native_decide 数量降序排列，选取 top 3 文件
2. **分类**：将每个 native_decide 分为：
   - **可缓存**：纯数值等式（`X = Y`）、布尔判定（`X == true`）→ 提取为 `@[simp]` 引理
   - **不可缓存**：interval_cases 内的分支消解、复合 tactic 链中的一环 → 保留
3. **生成缓存引理**：在原文件中就地添加（紧邻被优化定理之前），命名格式 `cached_[原定理名]_[序号]`
4. **替换**：将原 `native_decide` 替换为 `simp [cached_...]` 或 `exact cached_...`
5. **编译验证**：`lake build` 通过
6. **报告**：输出优化了多少处、预计编译提速比例

### 不做的事

- 不修改定理语义
- 不拆分文件（文件拆分由 formalizer 每轮步骤5处理）
- 不触碰 `lakefile.lean` 或 `lean-toolchain`

### 硬约束

- 零 sorry、零 admit、零 axiom
- `lake build` 必须通过
- 不删除已有定理

---

## 三、流程集成（lean4-formalize 编排变更）

### Phase 4.5（新增）：性能优化

插入在 Phase 4（登记）和 Phase 5（循环控制）之间。

```
触发判断：round_count % 5 == 0 ?
  ├─ 否 → 跳过，直接进入 Phase 5
  └─ 是 → spawn lean4-optimizer
```

### Team Lead 职责

1. 维护 `round_count` 计数器
2. 每5轮在 Phase 4 登记完成后 spawn optimizer：
   ```
   Agent(
     name = "optimizer",
     subagent_type = "lean4-optimizer",
     team_name = "lean4-formalization",
     description = "编译性能深度优化（按需）",
     mode = "bypassPermissions",
     prompt = "请对 lean4/ 项目执行深度 native_decide 缓存优化。
     扫描 native_decide 数量 top 3 文件，提取可缓存项为 @[simp] 引理，
     替换原 native_decide，lake build 验证通过后报告。"
   )
   ```
3. 等待 optimizer 回复 → shutdown optimizer → 进入 Phase 5

### Teammate 生命周期表更新

| 角色 | agent 定义 | 生命周期 | 说明 |
|------|-----------|----------|------|
| analyst | lean4-analyst | 持久 | 全程保留 |
| formalizer | lean4-formalizer | 持久 | 全程保留 |
| reviewer | lean4-reviewer | 按需 | Phase 3 |
| optimizer | lean4-optimizer | 按需（每5轮） | Phase 4.5 |
| codex-consultant | lean4-codex-consultant | 按需 | Phase 2 阻塞时 |
| registrar | lean4-registrar | 按需 | Phase 4 |
| milestone-reviewer | lean4-codex-reviewer | 按需 | Phase 6 |

---

## 实施清单

1. 修改 `.claude/agents/lean4-formalizer.md`：插入步骤 4.5
2. 新建 `.claude/agents/lean4-optimizer.md`：optimizer agent 定义
3. 修改 `.claude/agents/lean4-formalize` 技能：添加 Phase 4.5 和 round_count 逻辑
