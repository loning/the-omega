# 2026_zeckendorf_complete_system_energy_uplift

## 定位（这篇解决什么）

把 **Zeckendorf 截断折叠（\(2^m\to F_{m+2}\)）** 作为“空间压缩核”，把 **窗口外 Zeckendorf 尾部** 作为明确的 **uplift/时间纤维**，从而构造一个“信息守恒零总账”的完备系统：

- **本体（ontic）**：静态约束系统 \(\mathcal C\)，包含折叠一致性与时间纤维推进规则（Tail）。
- **空间（space）**：宏观观测 \(y=\mathrm{Fold}_m(N)\in Y_m\)（黄金均值语言，无相邻 1）。
- **时间（time）**：uplift 尾部 \(t=\tau_m(N)\in T_m\)，其推进由 \(\Tail\) 给出；展开过程对应 \(\Tail^{-1}\) 的分支增长。
- **能量（energy）**：观察者并行分支上限 \(E\)（beam width）；超过 \(E\) 必须 commit 丢弃分支，形成主观单线体验。

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

