# 2026_infinite_dimensional_ontology_finite_time_fiber_zeckendorf_folding 工作追踪

## 定位（这篇解决什么）

在三维基空间上建立“无限维本体—有限观测—有限预测状态”的分层结构：以 Zeckendorf 分辨率折叠给出第一层时间纤维，并以残差充分性公理引入第二层时间纤维丛与截面表述，同时完成稳定语言的 Fibonacci/Lucas 计数与最小核锚点。

## 核心对象（最小集合）

- **观测投影**：$\pi_m:\mathcal H\to X_m$ 与稳定语言 $X_m$。
- **折叠算子**：$\Fold_m:\Omega_m\twoheadrightarrow X_m$ 与原像纤维 $\mathcal F_m(x)$。
- **残差纤维**：$R_m(x)$ 与离散丛 $E_m=\bigsqcup_{x\in X_m}(\{x\}\times R_m(x))$。
- **组合计数**：$\abs{X_m}=F_{m+2}$、$\abs{C_m}=L_m$、$\abs{B_m}=F_{m-2}$。

## 当前进展（以正文为准）

- 已按最终目录重排完成第 0--17 节，并加入附录框架（A--F）。
- 参考文献条目已整理到 `references.bib`。

## 下一步（建议按优先级）

- **补充可复现实验脚本**：枚举 $X_m$、纤维谱与 holonomy 回路统计。
- **细化定量不等式**：时间成本与 holonomy 复杂度的显式界。

## 一键复现

本阶段已补齐可复现实验脚本。运行方式：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/run_all.py
```

如需额外生成“涌现相图（参数扫描）”，运行：

```bash
python3 scripts/run_all.py --scan
```

如需额外生成“对象/运动统计 + 空间holonomy”两组涌现实验，运行：

```bash
python3 scripts/run_all.py --extended
```

如需额外生成“对象周期/准周期 + 诱导连接holonomy 对照”，运行：

```bash
python3 scripts/run_all.py --extended2
```

如需额外生成“方向驱动输运（运动相）+ 参数扫描相图”，运行：

```bash
python3 scripts/run_all.py --extended3
```

如需额外生成“行走/准行走对象检测 + 二缺陷相互作用（散射型）”，运行：

```bash
python3 scripts/run_all.py --extended4
```

生成物位置：

- `sections/generated/`：正文可直接 `\\input{}` 的表格/数值片段（禁止手工改动）
- `artifacts/<experiment>/<run_id>/`：内容寻址产物（PNG/JSON/manifest）
- `artifacts/export/`：稳定文件名导出（供 LaTeX 图引用）

## 关键产物位置

- **正文主入口**：`main.tex`
- **分节内容**：`sections/`
- **参考文献**：`references.bib`
