# PDF 差距分析与改进计划（对比 `main_2026-3-2.pdf`）

## 1) 对比对象
- 知识图谱编译产物：`knowledgegraph/.kgcache/build/index_book_grg/main.pdf`
- 源基线 PDF：`docs/papers/auric-golden-phi/2026_golden_ratio_driven_scan_projection_generation_recursive_emergence/main_2026-3-2.pdf`

## 2) 关键差异（定量）

| 指标 | KG 编译 PDF | 源 PDF (`main_2026-3-2.pdf`) | 结论 |
|---|---:|---:|---|
| 文件大小 | 13,284,829 | 24,687,762 | KG 明显更小 |
| 页数 | 2711 | 4570 | KG 仅约 59.3% 页数 |
| 提取文本字符数 | 2,493,760 | 4,129,005 | KG 内容覆盖不足 |
| `label-like` 串（`eq:.../thm:...`） | 1989 | 0 | KG 中大量原始标签外露 |
| `??` 次数（提取文本） | 8484 | 26 | KG 远高于源（强烈异常信号） |
| 文献 key 样式串（`LindMarcus1995` 等） | 86 | 0 | KG 引用未正常数字化/格式化 |

说明：
- `??` 在中文 PDF 文本提取中可能有少量噪声，但“KG 8484 vs 源 26”差距量级过大，仍可判定为严重引用解析问题。

## 3) 直接根因证据

### 3.1 引用目标缺失（最核心）
在当前 `book_grg.idx` 选择规则下，多个关键类型被完全排除：
- `tp-prop`: `0 / 1991`（selected / total）
- `tp-cor`: `0 / 1819`
- `tp-note`: `0 / 1121`
- `tp-conj`: `0 / 290`

这会导致 proof/claim 中大量 `\ref/\eqref` 指向的目标节点不在编译集内。

### 3.2 已定义标签 vs 被引用标签存在大缺口
在当前 index 选中 TeX 集合内统计：
- `defined_labels = 15984`
- `unique_ref_labels = 4906`
- `missing_unique = 1997`
- `missing_calls_total = 4299`

高频缺失目标（节选）：
- `con:xi-terminal-zm-discriminant-leyang`
- `prop:xi-endpoint-absorption-coefficient`
- `prop:xi-pick-poisson-det-factorization`
- `cor:witt-dwork-congruence`
- `subsec:unit-disk-inner-outer`

### 3.3 标签前缀覆盖失衡（对比源 tex label 分布）
源 tex vs KG index 已定义标签（部分前缀）：
- `prop`: `2060 vs 10`
- `cor`: `1998 vs 4`
- `con`: `1020 vs 36`
- `rem`: `1131 vs 1`
- `subsec`: `416 vs 17`
- `tab`: `247 vs 1`
- `app`: `67 vs 4`

结论：KG 编译集对“可被引用的声明/章节/表格锚点”覆盖严重不足。

### 3.4 引用与文献处理策略不对齐源文档
- KG `stable` 模式为避免炸编译，已对 `\cite` 做降级；这会保留可编译性，但不能达到源 PDF 的文献呈现质量。
- 目前 bibliography 未按源论文的多 `.bib` 管线重建，导致引用语义与展示差异明显。

## 4) 现状判定

当前 KG PDF 在“可编译性”上已稳定（`missing_input=0`, `latex_error=0`），但在“文档语义等价性（尤其引用）”上不达标：
- 主要不是 TeX 崩溃问题，而是**索引选取与引用闭包不完整**问题。

## 5) 改进计划（按优先级）

## Phase P0（当天可落地，先止血）
1. 扩大 `book_grg.idx` 的 `include_types`：
   - 加入：`tp-prop,tp-cor,tp-note,tp-conj`
   - 目标：先补齐最主要被引用类型。
2. 全量重建 index 并统计缺失引用：
   - 目标：`missing_calls_total` 明显下降（至少下降 70%）。

## Phase P1（引用闭包正确性）
1. 在 `kg_build_index.py` 增加“引用闭包补全”开关（推荐默认开）：
   - 从选中 atom 扫描 `\ref/\eqref/...`；
   - 反查定义该 `\label` 的 atom；
   - 自动加入索引集合，迭代直到闭包稳定。
2. 输出 `reference_closure_report.json`：
   - 包含：新增补入节点、仍未解析标签清单、按前缀统计。
3. 验收：
   - `missing_unique <= 50`
   - `missing_calls_total <= 100`

## Phase P2（文献系统恢复）
1. 为 index 编译补齐 bibliography 管线：
   - 收集源工程使用的 `.bib` 列表（含 `references*.bib`）。
   - 在 index `main.tex` 注入 `\bibliography{...}` 与样式。
2. `stable` 模式分离策略：
   - `\ref` 保持原生；
   - `\cite` 默认原生（新增 `--degrade-cite` 才降级）。
3. 验收：
   - `undefined_cite = 0`
   - PDF 不再出现裸露文献 key（如 `LindMarcus1995`）。

## Phase P3（结构对齐源 PDF）
1. 新增“结构锚点 atom”机制：
   - 为 `sec/subsec/tab/fig/app` 标签建立轻量索引节点（可由源 tex 自动抽取）。
2. 章节级索引模板恢复：
   - 将源 `frontmatter/body/appendix/backmatter` 结构映射到 index nodes。
3. 验收：
   - `sec/subsec/tab/fig` 缺失显著下降；
   - 页数与源 PDF 比例提升（目标 >85%，最终趋近）。

## Phase P4（质量门禁）
1. 新增脚本：`kg_compare_pdf_quality.py`（建议）
   - 输入两个 PDF（KG vs 源）；
   - 输出：页数、引用缺口、文献缺口、标签外露、结构锚点覆盖。
2. CI 阈值（建议）：
   - `missing_input=0`
   - `latex_error=0`
   - `missing_calls_total <= 阈值`
   - `label_like_refs <= 阈值`

## 6) 立即执行建议（下一步）

1. 先实施 P0：调整 `book_grg.idx` 类型覆盖并重编译。  
2. 紧接实施 P1：做自动“引用闭包补全”，这是从“能编译”走向“引用正确”的关键。  
3. 再做 P2：恢复 bibliography，解决引用格式与源 PDF 的核心差距。  

---

该计划优先保证：**引用正确性 > 文献正确性 > 结构相似度**。  
如果只做美化而不先做闭包补全，标签问题会持续反复出现。
