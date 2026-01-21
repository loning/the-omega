## 目标

给定两类对象：

- **物理侧对象**：标准模型的可测约束（弱手性、双重态、颜色三重、反常消除、自旋与质量生成等）。
- **几何侧对象**：2D/3D 自适应 Hilbert 曲线诱导的“中心图”（节点=中心点，边=中心直连，附带 \(m\) 抬升/下降、局部取向族等）。

本文件记录一个可审计的桥接路线：把“物理约束”翻译为“图不变量/几何不变量”，将“排布规则”形式化为带标签图的**规范化标号（canonical labeling）**问题，从而把自由度压缩到唯一或有限等价类。

## 一、对象与分层（定义/假设/推论）

### 1.1 定义：中心图 \(G^{(d)}(m)\)

固定显示维度 \(d\in\{2,3\}\) 与锚定 Hilbert 屏：

- 2D：\(n=3\) 的 \(8\times 8\) Hilbert 屏（64 点）。
- 3D：\(p=2\) 的 \(4\times 4\times 4\) Hilbert 立方屏（64 点）。

给定局部分辨率场 \(m_by_k\)（以 coarse 扫描索引 \(k\in\{0,\dots,63\}\) 为坐标，取值 \(m\in\{6,8,10,\dots\}\)），构造中心图：

- **节点**：
  - 若 \(m(k)=6\)：节点为该 coarse cell 的中心；
  - 若 \(m(k)>6\)：节点为该 cell 的子格中心（2D 为 \(S\times S\)，3D 为 \(S^3\) 的 Hilbert 前缀稀疏占据，\(S\) 由 \(m-6\) 决定）。
- **边（严格）**：仅允许中心—中心直线边；不存在中间折点或绕线。
  - **同级**（同一 \(m\)）：边必须轴对齐（2D: 水平/竖直；3D: 沿坐标轴方向）。
  - **跨级**（不同 \(m\)）：边必须为斜线（至少两轴变化）。
- **曲线**：要求存在一条覆盖节点序列的单一连通扫描曲线（one-stroke），且在指定显示投影中不自交（端点相接触允许）。

> 注：在论文主线中，Hilbert 屏的“显示图” \(G_n=(V_n,E_n)\) 用于局部性、holonomy 等诊断；本处中心图用于表达“自适应几何（由 \(m\) 升降控制）”对可行布线与可实现标签的约束。

**测度分层（关键约定）**：

- **type-layer（coarse）**：以 coarse cell \(k\) 为基本单位；\(m=8\) 只表示该 \(k\) 内部出现 \(2^2=4\) 个子中心（2×2），\(m=10\) 类似；但它们共享同一稳定前缀 \(u_6\)，因此 **18+3 类型层不因细化复制而改变**。
- **micro-layer（refined）**：以所有子中心为单位；这是“微态测度”，只有在明确采用“细化改变有效权重”的假说时才进入常数/匹配层计算。

### 1.2 定义：标签图与同构

把中心图扩充为带标签图 \(\widetilde G\)，其节点/边携带以下可计算标签（颜色）：

- **协议标签**：\(m\)、门控事件（uplift/downlift）、局部端口型（进入/退出方向）；
- **稳定前缀标签**：\(u_6\in X_6\) 与其闭包/边界标签 \(D_\\pi\)；
- **SM 标签**：通过闭合映射 \(\mathcal L_{SM}:X_6\to\mathcal F_{SM}\sqcup\mathcal G_{SM}\) 给出 \((SU(3),SU(2))_Y\) 与场名；
- **取向/手性标签**：2D 的 \(D_4\) 取向类与 \(\chi_H\)；3D 的有向体元符号 \(\chi_{3D}\)（见下）。

两张标签图“对应”可表述为：存在保持标签的图同构（或更弱的图同态），并在剩余等价类中通过确定性 tie-break 选出唯一规范代表元。

### 1.3 桥接假设（bridge hypotheses）

以下桥接不把“直觉”当证明，而是作为可检验的接口假设：

- **H1（几何—带宽假设）**：几何由 \(m\) 的抬升/下降分布决定；payload 不改变中心图的节点集合与允许边型。
- **H2（手性筛选）**：弱相互作用门控/耦合只允许发生在固定手性类（例如 \(\chi=-1\)）的局部取向上；反射/反向导致 \(\chi\) 翻号对应宇称破缺的协议选择。
- **H3（配对/三重结构）**：SU(2) 双重态、SU(3) 三重态对应到图上的可计算局部 motif 与全局计数/holonomy 约束。
- **H4（反常消除闭包）**：可实现的标签必须满足标准模型反常消除的整数算术检查（在图上体现为全局加权恒等式或 holonomy 兼容性约束）。

这些假设的作用是把可行排布空间从“所有 \(D_4/O_h\) 取向组合”压缩为有限候选，最终由 canonical labeling 选唯一。

## 二、核心不变量与物理约束的对应（可计算）

### 2.1 2D 手性：Hilbert chirality index \(\chi_H\)

沿扫描路径 \(p_0,\dots,p_{N-1}\in\mathbb Z^2\) 定义（论文已给出）：

$$
\\chi_H:=\\sum_{k=1}^{N-2}\\mathrm{sgn}((p_k-p_{k-1})\\times(p_{k+1}-p_k)).
$$

性质：反射与遍历反向翻号；旋转保持（与 \(D_4\) 分裂一致）。把弱手性对应为对 \(\chi\) 的筛选即可将 \(D_4\) 的自由度减半。

### 2.2 3D 手性：离散体元符号 \(\chi_{3D}\)

用连续三段方向向量定义：

$$
\\chi_{3D}:=\\sum_i \\mathrm{sgn}((\\Delta p_i\\times\\Delta p_{i+1})\\cdot \\Delta p_{i+2}),
$$

其非零贡献需要真正三维的转向序列，因此更自然地承载 Weyl 手性与“粒子侧”结构。

### 2.3 SU(3) 代理：S4→SO(3) 的 holonomy 角分布

在锚定 \(m=6\) 的 \(8\times 8\) 屏上，论文用 S4 置换作为有限补偿联络，并对 plaquette holonomy 做 cycle type 统计；进一步通过标准表示的 sign-twist 映射到 SO(3) 旋转角分布（见脚本 `scripts/exp_holonomy_su3_representation.py`）。

这给出一个可审计的不变量族：按 cycle type 分类的角分布与 Wilson-loop 标量。

### 2.4 反常消除：整数算术门禁

对单代 chiral 内容（含 \(\\nu_R\)）的四类反常和为 0（脚本 `scripts/exp_sm_labeling_solver.py` 已给出整数检查）。这提供“物理侧硬约束”的可计算门禁：任何候选标签赋值若破坏这些和，直接淘汰。

### 2.5 Higgs/质量：m=10 uplift 的标量双重态构造

论文已经给出一个确定性标量双重态代表元：把 \(m=10\) 的后缀位通道 \(b_j\) 经 coarse-grain 后捆绑为 \(H\\in\\mathbb C^2\)，并由 CAP 在有限族内闭合其量子数为 \((1,2)_{1/2}\)。

这提供了“m=10 uplift 与电弱标量扇区”的直接几何—信息对应。

## 三、从约束到“唯一排布规则”：canonical labeling

把“唯一规则”写成三步：

1. **硬可行性**：中心图存在非自交的一笔画扫描路径（在指定显示投影下），且边型满足同级轴对齐、跨级斜边。
2. **物理门禁**：\(\chi\) 筛选、反常消除、SU(2)/SU(3) 的 motif/holonomy 约束。
3. **确定性 tie-break**：对剩余等价类做 WL-refinement 与字典序/最小 action 选取，得到规范代表元（canonical signature）。

这一步把“排布规则”从人为选择变成可复现的“规范化标号算法输出”。

## 四、原型代码与复现入口

原型实现位于：

- `scripts/hilbert_sm_center_graph.py`：2D/3D 中心图构造与一笔画扫描路径（含取向候选与增量回溯）。
- `scripts/hilbert_sm_invariants.py`：\(\chi\)、SU(3) holonomy 代理、反常检查等不变量计算。
- `scripts/hilbert_sm_canonical.py`：WL-refinement + tie-break 的 canonical signature 原型。
- `scripts/exp_hilbert_sm_gi_search_bestcurve.py`：搜索 2D/3D **全中心图**严格同构（`sig_equal`），输出候选的 `m_schedule_by_k + choice2/choice3` 与报告 JSON。
- `scripts/fig_hilbert_sm_wiring_fold_geometry_full_gi.py`：将“全图严格同构”的候选落地为具体布线/折叠几何（SVG + `wiring_geometry.json`）。
- `scripts/exp_hilbert_sm_search_holonomy_gi.py`：在“类型层同构（18⊕3）”门禁下，进一步搜索使 2D/3D 的 holonomy-by-representation 主通道（120°/180°）对齐的候选。
- `scripts/fig_hilbert_sm_wiring_fold_geometry_holonomy_gi.py`：将 holonomy-GI 候选落地为具体布线/折叠几何（SVG + `wiring_geometry.json`）。
- `scripts/exp_hilbert_sm_holonomy_on_wiring.py`：对指定 `wiring_geometry.json` 做 plaquette holonomy 诊断（支持 `--wiring-dir`）。
- `scripts/exp_hilbert_sm_holonomy_aggregate_by_rep.py`：将 holonomy 按 \((SU3,SU2)_Y\) 表示类聚合（支持 `--wiring-dir`）。
- `scripts/exp_hilbert_sm_holonomy_rep_strengths.py`：从聚合结果导出紧凑的 SU(3)/SU(2) 代理强度（支持 `--wiring-dir`）。

产物示例：

- `figures/adaptive/sm_hilbert_isomorphism/data/sm_hilbert_gi_search_bestcurve_report.json`
- `figures/adaptive/sm_hilbert_isomorphism/data/sm_hilbert_holonomy_gi_search_report.json`
- `figures/adaptive/sm_hilbert_isomorphism/wiring_fold_geometry_full_gi/wiring_geometry.json`
- `figures/adaptive/sm_hilbert_isomorphism/wiring_fold_geometry_holonomy_gi/wiring_geometry.json`

## 五、可证伪点（最小清单）

- 若在给定的 \(m\) 升降日程与严格边型规则下，中心图无法产生无交叉一笔画，则该日程不满足“几何由带宽分布闭包”的接口假设（H1 在该规则集下失败），需要修正日程或边型规则。
- 若在通过 \(\chi\) 筛选后仍无法闭合 SU(2)/SU(3) 的 holonomy/计数约束，则 H2/H3 对应需要调整（或需要提升到 3D 承载）。
- 若任何候选标签破坏反常消除的整数检查，则可直接排除该候选映射（硬门禁）。

