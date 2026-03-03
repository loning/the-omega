# Atom-First KnowledgeGraph（知识原子 + 动态索引）

你提的方向是对的：
- **知识节点不应绑定章节结构**。
- 知识图谱的真相层只维护“什么知识由什么知识推出来”。
- 专著/章节只是“索引投影”，应作为可动态变化的索引节点。

本方案据此重构为两层：
1. **KNode（Knowledge Atom Node）**：不可变、可追溯、仅表达知识与推理关系。
2. **INode（Index Node）**：可变、可重建、仅负责组织展示（书/章/专题/讲义）。

---

## 1. 核心原则

1. Atom-first：知识最小单元是原子 `.tex` 节点，不包含章节语义。
2. Inference-only：知识层只维护推理边（from/dependence），无目录结构边。
3. Append-only：KNode 只新增，不删除、不覆写历史内容。
4. Typed node：每个 KNode 必须有明确类型（def/thm/proof/exp/...）。
5. Dynamic index：INode 不是真相源，可随时按查询规则重建。
6. DAG constraint：KNode 推理图必须是有向无环图。

---

## 2. 目录结构（分层）

```text
knowledgegraph/
  README.md
  schema/
    kg-macros.tex
    kg-node-template.tex
  atoms/                             # 真相层（append-only）
    KG-20260303-0001__lbl-scan-axiom__tp-def__from-root.tex
    KG-20260303-0002__lbl-fold-map__tp-def__from-scan-axiom.tex
    KG-20260303-0003__lbl-main-theorem__tp-thm__from-fold-map+scan-axiom.tex
    KG-20260304-0001__lbl-main-theorem-errata__tp-errata__from-main-theorem.tex
    KG-20260304-0002__lbl-main-theorem-v2__tp-thm__from-main-theorem+main-theorem-errata.tex
  index_specs/                       # 索引定义（可改、可重建）
    book_grg.idx
    chapter_folding.idx
  source_specs/                      # 源目录追踪配置（可改）
    auric_grg.src
  index_nodes/                       # 由 index_specs 生成（可覆盖）
    book_grg/
      idx_book_grg_main.tex
      idx_book_grg_ch01.tex
      idx_book_grg_ch02.tex
  scripts/
    kg_scan_atoms.py
    kg_check_dag.py
    kg_watch_sources.py
    kg_emit_llm_tasks.py
    kg_build_index.py
    kg_compile.py
    kg_migrate_from_sections.py
  .kgcache/                          # 临时缓存，可忽略提交
```

说明：
- `atoms/` 是长期真相资产。
- `index_nodes/` 是展示层产物，允许重排和覆盖。
- `source_specs/` 定义要跟踪的源目录（如 `docs/papers/...`）。
- 将来若接图数据库，`index_specs` 对应 query，`index_nodes` 对应 materialized view。

---

## 3. KNode 文件名语法（关系在文件名）

KNode 文件名：

```text
<ID>__lbl-<SELF>__tp-<TYPE>__from-<PARENTS>.tex
```

字段：
1. `<ID>`：`KG-YYYYMMDD-NNNN`（全局唯一）。
2. `<SELF>`：本节点 label slug（canonical label = `kg:<SELF>`）。
3. `<TYPE>`：节点类型（见下节）。
4. `<PARENTS>`：父知识 label，用 `+` 分隔；根节点写 `root`。

示例：
- `KG-20260303-0003__lbl-main-theorem__tp-thm__from-fold-map+scan-axiom.tex`

约束：
- slug 字符集：`[a-z0-9-]`
- 单文件名长度建议 <= 180
- `from` 父节点数建议 <= 6（超出就加桥接节点）
- `atoms/` 默认不按年份分目录；如文件数过大，仅做“无语义分片”（例如按 ID 前缀）。

---

## 4. KNode 类型系统（必须）

建议最小类型集：
- `tp-def`：定义
- `tp-axiom`：公理
- `tp-lemma`：引理
- `tp-thm`：定理
- `tp-proof`：证明
- `tp-claim`：主张
- `tp-exp`：实验结论
- `tp-data`：数据事实
- `tp-alg`：算法构件
- `tp-errata`：纠错节点
- `tp-retract`：撤回节点

说明：
- 类型是知识语义的一部分，不是排版标签。
- 编译器可以按类型过滤，生成不同视图（仅定理链、仅实验链等）。

---

## 5. KNode 正文规范

```tex
% KG_ID: KG-20260303-0003
% KG_LABEL: main-theorem
% KG_TYPE: thm
% KG_FROM: fold-map+scan-axiom

\begin{theorem}[Main Theorem]
\label{kg:main-theorem}
...
\end{theorem}
```

规则：
1. 文件名是主数据源，头注释用于审计。
2. 正文必须包含 `\label{kg:<SELF>}`。
3. 历史 KNode 不改写；纠错靠新增 `tp-errata/tp-retract` 节点。

---

## 6. INode（索引节点）模型

INode 用于书/章/专题组织，不引入新知识断言，只做 include。

### 6.1 索引定义（index_specs）

例：`index_specs/chapter_folding.idx`

```text
name: chapter_folding
mode: query
roots: main-theorem-v2
types: def,lemma,thm,proof,exp
tags_any: folding,scan-projection
order: topo
```

### 6.2 生成节点（index_nodes）

`kg_build_index.py` 根据 `.idx` 生成：
- `index_nodes/chapter_folding/idx_chapter_folding_main.tex`

该文件只做：
- `\section{...}` / `\subsection{...}`
- `\input{.../atoms/...tex}`

结论：
- INode 可随时重建、重排、删改。
- KNode 保持稳定，图谱知识真相不受章节调整影响。

---

## 7. DAG 扫描与校验（只看 atoms 文件名）

`kg_scan_atoms.py`：
1. 扫描 `atoms/**/*.tex`
2. 解析 `lbl/tp/from`
3. 构造推理边 `self -> parent`
4. 校验：
   - ID 唯一
   - label 唯一
   - parent 存在（root 除外）
   - 无环

`kg_check_dag.py`：
- 仅基于扫描结果判断是否可构建。
- 不依赖手工 JSON 关系表。

---

## 8. 源目录哈希监测与 LLM 增量入图

目标：源目录文件一旦内容 hash 变化，就自动探测并产出 LLM 处理任务，最终只通过“新增 KNode”入图。

### 8.1 跟踪配置（source_specs）

示例：`source_specs/auric_grg.src`

```text
name: auric_grg
root: docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections
include: **/*.tex
exclude: **/generated/**
hash: sha256
```

说明：
- 可按需要追加多个 `source_specs/*.src`。
- `exclude` 用于过滤自动生成片段或临时文件。

### 8.2 监测流程

1. `kg_watch_sources.py --spec source_specs/auric_grg.src`
2. 对匹配文件计算 `sha256(content)`。
3. 与上一次快照比较，得到 `added/modified/deleted/renamed`（rename 可由同 hash 推断）。
4. 写入 `.kgcache/source/auric_grg/delta_<timestamp>.jsonl`（自动产物）。
5. `kg_emit_llm_tasks.py` 把 `added/modified` 生成到 `.kgcache/llm_queue/`。
6. LLM 基于任务产出新 KNode；旧 KNode 不改写。
7. `deleted` 不删除 KNode，而是生成 `tp-errata/tp-retract` 候选任务。

### 8.3 LLM 任务最小字段

每个任务至少包含：
1. `source_path`
2. `old_hash`
3. `new_hash`
4. `change_type`
5. `diff_excerpt`
6. `candidate_parent_labels`（由现有 KNode 图谱检索）
7. `suggested_node_type`

---

## 9. 编译流程

### 9.1 知识审计编译（不看章节）

`kg_compile.py --mode audit --root main-theorem-v2`

行为：
- 取 root 的推理闭包。
- 按拓扑顺序生成临时 `main.tex`。
- 输出“知识链 PDF”。

### 9.2 专著/章节编译（看索引）

`kg_compile.py --mode index --spec chapter_folding`

行为：
- 先由 `.idx` 生成 INode。
- 再编译 INode 对应 PDF。

### 9.3 局部编译

`kg_compile.py --mode partial --label fold-map`

行为：
- 编译该节点及其必要依赖，用于快速检查。

---

## 10. LaTeX 工具链（固定）

本项目建议固定以下工具链（优先保证可复现）：

1. 引擎与编排：
   - `latexmk`（统一编译入口）
   - `XeLaTeX`（中文与 Unicode 友好）
2. 结构化拆分：
   - `subfiles`（支持节点/索引文件局部编译）
3. 跨文档引用：
   - `xr-hyper`（全量与局部文档互引）
4. 参考文献：
   - 默认 `BibTeX`（若未来切 `biblatex+biber`，需在全仓统一切换）

推荐编译命令（与现有论文目录一致）：

```bash
latexmk -pdfxe -interaction=nonstopmode -halt-on-error -file-line-error main.tex
```

局部/快速编译：

```bash
latexmk -pdfxe -interaction=nonstopmode -halt-on-error -file-line-error main_fast.tex
```

说明：
- `kg_compile.py` 仅负责生成临时 `main.tex`（full/partial/index）。
- 实际 PDF 构建统一交给 `latexmk`，避免多套编译逻辑。

---

## 11. 引用策略（兼容局部编译）

1. 统一引用宏：`\kgref{main-theorem}` -> `\ref{kg:main-theorem}`。
2. 全量编译产生真实 `.aux`。
3. 局部编译时自动生成临时 `labels_stub.tex` 到 `.kgcache/` 做兜底（自动生成，不手工维护）。

---

## 12. 演化与纠错（严格 append-only）

当节点错误时：
1. 新增 `tp-errata` 或 `tp-retract` 节点，`from` 指向旧节点。
2. 如有替代，再新增 `tp-thm/tp-claim` 的 v2 节点，`from` 包含旧节点 + errata 节点。
3. 旧节点保留不动。

这样可以完整保留知识演化轨迹。

---

## 13. 从当前论文迁移（与章节解耦）

源目录：
- `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence`

迁移步骤：
1. 从 `sections/body/**/*.tex` 提取原子知识单元，落到 `atoms/`。
2. 仅写入 KNode 类型和 `from` 依赖，不写章节信息。
3. 跑 `kg_check_dag.py`，修复环和缺失父节点。
4. 另建 `index_specs/*.idx` 来表达书/章节结构。
5. 生成 `index_nodes/` 并编译专著视图。

---

## 14. 第一批最小落地

1. `schema/kg-macros.tex`
2. `schema/kg-node-template.tex`
3. `scripts/kg_scan_atoms.py`
4. `scripts/kg_check_dag.py`
5. `scripts/kg_watch_sources.py`
6. `scripts/kg_emit_llm_tasks.py`
7. `scripts/kg_build_index.py`
8. `scripts/kg_compile.py`
9. `index_specs/book_grg.idx`
10. `source_specs/auric_grg.src`

这套闭环满足：
- 知识真相层只关心“由谁推理出谁”。
- 展示层（章节/专著）完全动态可重建。
