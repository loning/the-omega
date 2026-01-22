# 2026_zeckendorf_complete_system_energy_uplift

## 定位（这篇解决什么）

把 **Zeckendorf 截断折叠（\(2^m\to F_{m+2}\)）** 作为“空间压缩核”，把 **窗口外 Zeckendorf 尾部** 作为明确的 **uplift/时间纤维**，从而构造一个“信息守恒零总账”的完备系统：

- **本体（ontic）**：静态约束系统 \(\mathcal C\)，包含折叠一致性与时间纤维推进规则（Tail）。
- **空间（space）**：空间状态 \(y=\mathrm{Fold}_m(N)\in Y_m\)（黄金均值语言，无相邻 1）。
- **时间（time）**：时间纤维（uplift 坐标）为窗口外尾部比特串 \(t=\tau_m(N)\in T_m\)。为保证展开/折叠互为逆操作，观察者维护路径 trace \(\mathsf{tr}\in\{0,1\}^\ast\) 记录每一步展开的选择。
- **能量（energy）**：能量是内生的能量胶带 \(\mathsf{E}\in\{0,1\}^\ast\)。展开每推进一步消耗 1 单位能量并产生新的时间纤维/空间候选，同时在 \(s_m(y)>2\) 的状态上采掘额外能量；折叠作为逆操作湮灭时间纤维与空间候选并回收能量，从而保持守恒。并行可追踪分支上限由 \(\Energy(\mathsf{E})=2^{|\mathsf{E}|}\) 给出。

该折叠与 uplift 约定与 `docs/papers/2025_resolution_folding_phi_pi_e_hpa_omega` 的窗口折叠定义一致（Fibonacci 约定与 Fold\_m 的窗口投影）。

## 一键复现

在本论文目录执行：

```bash
python3 -m pip install -r requirements.txt
python3 scripts/run_all.py --force
latexmk -xelatex -interaction=nonstopmode main.tex
```

## 关键产物位置

- **正文直接引用的生成片段**：`sections/generated/`
- **稳定导出图/表**：`artifacts/export/`
- **实验脚本入口**：`scripts/run_all.py`

