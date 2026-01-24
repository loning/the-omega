# 2026_observer_spacetime_hilbert_measure 工作追踪

## 定位（这篇解决什么）

以“**本体是静态约束系统**”为第一性起点，构造一个以观察者为中心的统一框架：

- **本体（ontic）**：给定一个静态约束系统 \(\mathcal C\)（可理解为因子图/闭包图上的一致性约束）。本体不要求先“算出”一条历史轨迹。
- **观察者（epistemic）**：观察者 \(O=(\pi,\mathcal A,\mathcal G)\) 由
  - 投影/可见化 \(\pi\)（遗忘哪些信息）
  - lifting/一致性搜索算法 \(\mathcal A\)
  - “尺子/几何” \(\mathcal G\)（用 Hilbert 1D/2D/3D 的局部性与多尺度组织来定义扫描顺序与约束传播形态）
  共同确定。
- **时空（observer spacetime）**：定义为观察者在 \(\mathcal C\) 上进行 lifting 与回溯搜索时生成的搜索图（或其闭包对象）。
- **时间与成本**：
  - 负信息时间 \(\tau\)：uplift/历史胶带的编码长度（以比特计），作为时间轴的本体成分；
  - 观察者时间/成本 \(\kappa_{\mathcal A}\)：以搜索成本（节点/迭代等）刻画，并在最小假设下与 \(\tau\) 同阶等价。

本论文把 Hilbert 曲线从“画图/嵌入”提升为“观察者的尺子”：固定几何对比 + 自适应维度切换策略。

## 一键复现

在本论文目录执行：

```bash
python3 -m pip install -r requirements.txt
python3 scripts/run_all.py
```

## 关键产物位置

- **正文直接引用的生成片段**：`sections/generated/`
- **可复现实验脚本入口**：`scripts/run_all.py`
- **稳定导出图/表（若有）**：`artifacts/export/`

