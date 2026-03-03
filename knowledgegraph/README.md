# Atom-First KnowledgeGraph（统一 Atom 模型）

当前模型统一为：
- **脚本是 Atom**。
- **脚本生成的代码/tex/data 也是 Atom**。
- 章节/专著组织不是知识真相，只是动态索引（Index View）。

即：所有可追溯单元都进 `atoms/`，按类型区分，而不是拆成“知识层 + 证据层”两套真相。

---

## 1. 核心原则

1. Atom-first：图谱真相层只有 `atoms/`。
2. Append-only：Atom 只新增，不删除、不覆写。
3. Inference-only：关系只表达“由谁推得谁”（`from` DAG）。
4. Typed Atom：每个 Atom 必须有类型（定义/定理/脚本/产物/纠错等）。
5. Dynamic Index：书/章/专题是索引视图，可重建可重排。
6. DAG Constraint：推理边必须无环。

---

## 2. 目录结构

```text
knowledgegraph/
  README.md
  schema/
    kg-macros.tex
    kg-node-template.tex
  atoms/                             # 真相层（统一 Atom，append-only）
    KG-20260303-0001__lbl-scan-axiom-hf1a2b3c4d5e6__tp-def__h-a1b2c3d4e5f6.tex
    KG-20260303-0001__lbl-scan-axiom-hf1a2b3c4d5e6__tp-def__h-a1b2c3d4e5f6.tex.meta.json
    KG-20260303-0101__lbl-fold-method-v1-hc3d4e5f6a1b2__tp-method__h-c3d4e5f6a1b2.py
    KG-20260303-0101__lbl-fold-method-v1-hc3d4e5f6a1b2__tp-method__h-c3d4e5f6a1b2.py.meta.json
  index_specs/                       # 索引规则（可改）
    book_grg.idx
    chapter_folding.idx
  index_nodes/                       # 索引视图生成物（可覆盖）
    book_grg/
      idx_book_grg_main.tex
  source_specs/                      # 源目录监测配置
    auric_sections.src
    auric_scripts.src
  scripts/
    kg_scan_atoms.py
    kg_check_dag.py
    kg_watch_sources.py
    kg_emit_llm_tasks.py
    kg_ingest_atoms.py
    kg_build_index.py
    kg_compile.py
    kg_analyze_build_log.py
  .kgcache/                          # 临时缓存，可忽略提交
```

说明：
- `atoms/` 是唯一真相层。
- `index_nodes/` 仅用于展示与编译，不承载知识真相。
- `source_specs/` 定义需要持续监测 hash 的源目录。

---

## 3. Atom 文件名语法（标识+类型+哈希）

```text
<ID>__lbl-<SELF>__tp-<TYPE>__h-<SHA12>.<ext>
```

字段：
1. `<ID>`：`KG-YYYYMMDD-NNNN`，全局唯一。
2. `<SELF>`：Atom label slug（建议 `[a-z0-9-]`）。
3. `<TYPE>`：Atom 类型。
4. `<SHA12>`：内容 `sha256` 前 12 位（用于不可变校验）。
5. `<ext>`：载荷格式（`.tex/.py/.sh/.json/.csv/.md` 等）。

关系字段迁移到 sidecar JSON：

```text
<payload_filename>.meta.json
```

示例：

```json
{
  "kg_id": "KG-20260303-0002",
  "label": "thm-main-hdf363889c236",
  "atom_type": "tp-thm",
  "parents": ["lem-base-h3123dca2ca16"],
  "source_path": ".../sections/body/xxx.tex"
}
```

约束：
- 默认不按年份分目录；必要时仅做无语义分片（如按 ID 前缀）。
- 单文件名建议 <= 220 字符。
- `from` 父节点建议 <= 6，超出可加桥接 Atom。

---

## 4. Atom 类型系统

最小类型集：
- `tp-def`：定义
- `tp-axiom`：公理
- `tp-lemma`：引理
- `tp-thm`：定理
- `tp-proof`：证明
- `tp-claim`：主张
- `tp-exp`：实验结论
- `tp-data`：数据事实
- `tp-method`：脚本/方法（`.py/.sh/...`）
- `tp-artifact`：脚本生成产物（`.tex/.csv/.json/...`）
- `tp-errata`：纠错
- `tp-retract`：撤回

说明：
- 脚本与脚本产物是第一类 Atom，不是附属对象。
- 类型用于检索、编排、编译过滤和审计。

---

## 5. Atom 载荷规范

### 5.1 `.tex` Atom（可编译类）

```tex
% KG_ID: KG-20260303-0003
% KG_LABEL: main-theorem
% KG_TYPE: thm
% KG_PARENTS: fold-map,scan-axiom
% KG_HASH: f1a2b3c4d5e6

\begin{theorem}[Main Theorem]
\label{thm:main-theorem}
...
\end{theorem}
```

规则：
1. `.tex` Atom 建议保留原始 `\label{...}`（如 theorem/proof 内 label）。
2. ingest 会自动注入短锚点（`kgid:<12hex>`）与 `% kg-label:<SELF>` 注释，供审计与编译兼容。
3. 文件名是主数据源；头注释用于审计。

### 5.2 非 `.tex` Atom（脚本/产物类）

示例：`.py/.csv/.json` Atom 不要求 `\label`，但必须满足：
1. 文件名遵循统一语法（含 `tp/from/h`）。
2. `h-<SHA12>` 与内容 hash 一致。
3. 可被索引与审计流程追踪。

---

## 6. Index View（章节/专著）

索引是可变投影，不是知识真相。

### 6.1 索引规则

例：`index_specs/chapter_folding.idx`

```text
name: chapter_folding
roots: main-theorem
include_types: tp-def,tp-lemma,tp-thm,tp-proof,tp-exp,tp-artifact
auto_include_methods: false
order: topo
```

### 6.2 索引生成

`kg_build_index.py` 根据 `.idx` 生成 `index_nodes/*`，只做：
1. 章节标题结构。
2. `\input{}` 相关 `.tex` Atom。
3. 可选附录里列出 `tp-method/tp-artifact` 的清单。

---

## 7. DAG 扫描与校验

`kg_scan_atoms.py`：
1. 扫描 `atoms/*`（不限扩展名）。
2. 从文件名解析 `id/lbl/tp/hash/ext`。
3. 从 `*.meta.json` 读取 `parents`，构造推理边 `self -> parent`。
4. 校验：
   - ID 唯一
   - label 唯一
   - parent 存在（root 除外）
   - 无环
   - 文件名 hash 与内容 hash 一致

`kg_check_dag.py`：
- 基于扫描结果做门禁。
- 不依赖手工 JSON 边表。

---

## 8. 源目录哈希监测与 LLM 增量入图

目标：当源目录文件 hash 变化时，自动产出 LLM 任务，最终以“新增 Atom”方式入图。

### 8.1 跟踪配置

例：`source_specs/auric_sections.src`

```text
name: auric_sections
root: docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/sections
include: *.tex,**/*.tex
exclude: generated/*.tex,**/generated/**
hash: sha256
```

例：`source_specs/auric_scripts.src`

```text
name: auric_scripts
root: docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/scripts
include: *.py,**/*.py
hash: sha256
```

### 8.2 监测流程

1. `kg_watch_sources.py --spec source_specs/*.src`
2. 计算内容 hash，与上次快照比较。
3. 产出 `added/modified/deleted/renamed`。
4. 写入 `.kgcache/source/<name>/delta_<timestamp>.jsonl`。
5. `kg_emit_llm_tasks.py` 生成 `.kgcache/llm_queue/`。
6. `kg_ingest_atoms.py`（LLM 结果落地）只新增 Atom 文件。

### 8.3 脚本与脚本产物入图规则

1. 脚本变更：新增 `tp-method` Atom（载荷可直接是脚本副本）。
2. 脚本生成 `.tex/.csv/.json`：新增 `tp-artifact` Atom。
3. 源 `.tex`（非 generated）使用 `pylatexenc` 做 AST 解析，按 `definition/lemma/theorem/corollary/proof/...` 环境切分为知识最小单元（每个单元一个 task -> 一个 atom）。
4. 每个 `.tex` 知识单元从 `\ref/\eqref/\autoref/\cref` 提取依赖，映射到父 atom，写入 sidecar JSON 的 `parents`。
5. `proof` 单元必须绑定声明节点（定义/定理/引理/命题等）；无可解析父节点时不入图（跳过 orphan proof atom）。
6. 为兼容原文 label 未统一改写，ingest 会使用 sidecar 中 `source_tex_label` 作为别名映射来解析 `source_refs`。
7. 若产物形成新结论：再新增 `tp-exp/tp-claim/tp-thm` Atom。
8. 源文件删除：不删 Atom，新增 `tp-errata/tp-retract` 候选任务。

---

## 9. 编译流程

### 9.1 知识审计编译（脱离章节）

`kg_compile.py --mode audit --root <label>`

行为：
1. 取 root 的推理闭包。
2. 过滤可编译类型（默认 `.tex` + `tp-def/lemma/thm/proof/exp/...`）。
3. 拓扑排序生成临时 `main.tex`。
4. 产出知识链 PDF。

### 9.2 索引编译（书/章）

`kg_compile.py --mode index --spec chapter_folding`

行为：
1. 由 `.idx` 生成 `index_nodes`。
2. `index_nodes/<spec>/atoms/` 自动生成短名软链（避免超长 `\input` 路径导致 TeX pool 超限）。
3. 编译索引 PDF。
4. 可选 `--index-ref-mode stable|strict`：
   - `stable`（默认）：保留可解析的 `\ref/\eqref`；未解析标签回退为文本占位；`\cite` 回退为文本占位，优先保证超大图可编译。
   - `strict`：保留原始引用语义（含引用告警），可能更慢或在超大图上失败。
5. 默认复用固定构建目录（例如 `knowledgegraph/.kgcache/build/index_book_grg/`），可复用 `.aux/.fdb_latexmk`，重复编译更快。
6. 默认将 LaTeX 详细输出写入 `latexmk.stdout.log`（减少终端 I/O 开销）；调试时可加 `--verbose-latex`。
7. 若需要冷启动全新构建目录，使用 `--fresh-build`。

### 9.3 局部编译

`kg_compile.py --mode partial --label fold-map`

行为：
- 编译目标与必要依赖，用于快速核查。

---

## 10. LaTeX 工具链（固定）

固定工具链：
1. `latexmk`（统一入口）
2. `XeLaTeX`（中文/Unicode）
3. `subfiles`（局部编译）
4. `xr-hyper`（跨文档引用）
5. `BibTeX`（默认）
6. `pylatexenc`（知识单元抽取：LaTeX AST 解析）

推荐命令：

```bash
latexmk -pdfxe -interaction=nonstopmode -halt-on-error -file-line-error main.tex
```

全量索引编译（推荐默认复用缓存）：

```bash
python3 knowledgegraph/scripts/kg_compile.py \
  --kg-root knowledgegraph \
  --mode index \
  --spec book_grg \
  --index-ref-mode stable
```

冷启动（不复用旧 build 目录）：

```bash
python3 knowledgegraph/scripts/kg_compile.py \
  --kg-root knowledgegraph \
  --mode index \
  --spec book_grg \
  --index-ref-mode stable \
  --fresh-build
```

日志体检（统计 warning/error）：

```bash
python3 knowledgegraph/scripts/kg_analyze_build_log.py \
  --kg-root knowledgegraph \
  --build-tag index_book_grg \
  --top 30
```

说明：日志分析默认优先选择“最近一次成功完成”的 build（有 `main.pdf` 且 `latexmk` 完成标记），避免误读中断构建日志。

安装 `pylatexenc`（macOS/Homebrew Python）：

```bash
python3 -m pip install --user --break-system-packages pylatexenc
# 或
python3 -m pip install --user --break-system-packages -r knowledgegraph/requirements.txt
```

---

## 11. 引用策略

1. 原始数学引用优先保留源标签：`\ref{thm:...}` / `\eqref{eq:...}`。
2. 系统锚点使用短标签 `\label{kgid:<12hex>}`，并在注释保留 `% kg-label:<SELF>` 映射。
3. 非 `.tex` Atom：用 `\texttt{KG-...}` 或自定义宏显示引用。

---

## 12. 演化与纠错（严格 append-only）

1. 不回写旧 Atom。
2. 新增 `tp-errata/tp-retract` 指向被纠正节点。
3. 若有替代结论，再新增 `v2` Atom 并连接旧节点 + errata 节点。

---

## 13. 迁移策略（针对当前源目录）

源目录：
- `docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence`

步骤：
1. 从 `sections/body` 提取声明类 `.tex`，生成 `tp-def/tp-thm/...` Atom。
2. 从 `scripts` 导入方法类，生成 `tp-method` Atom。
3. 从 `sections/generated` 与产物目录导入 `tp-artifact` Atom。
4. 跑 `kg_check_dag.py` 修复环和缺失父节点。
5. 建立 `index_specs/*.idx` 生成专著/章节视图。

---

## 14. 第一批最小落地

1. `schema/kg-macros.tex`
2. `schema/kg-node-template.tex`
3. `scripts/kg_scan_atoms.py`
4. `scripts/kg_check_dag.py`
5. `scripts/kg_watch_sources.py`
6. `scripts/kg_emit_llm_tasks.py`
7. `scripts/kg_ingest_atoms.py`
8. `scripts/kg_build_index.py`
9. `scripts/kg_compile.py`
10. `index_specs/book_grg.idx`
11. `source_specs/auric_sections.src`
12. `source_specs/auric_scripts.src`

这套闭环满足：
- 脚本与脚本产物都是 Atom（第一类节点）。
- 章节只是动态索引视图。
- 任何变化都通过新增 Atom 演化。
