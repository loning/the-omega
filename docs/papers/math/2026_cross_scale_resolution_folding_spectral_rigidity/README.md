# 2026_cross_scale_resolution_folding_spectral_rigidity 工作追踪

## 定位（这篇解决什么）

以固定 $m=6$ 的折叠核作为可枚举基例，向上组织“跨尺度分辨率”的图与算子对象：从无损编码到单图覆盖，再到 Ihara 型 $\zeta$ 字典、谱隙/混合时间与复杂性之间的不等式链条，并给出可复现实验产物。

本稿包含一段**条件性桥接**（HTF）用于讨论“条件临界线刚性”；主干结构与实验尽量保持在闭层内可审计。

## 核心对象（最小集合）

- **折叠核（基例）**：$m=6$，微观 $2^6=64$，稳定态计数为 $F_{8}=21$。
- **无损编码**：把稳定态与离散 uplift 组合成可逆的块级编码（用于构造统一的图对象）。
- **单图覆盖与跨尺度接口**：用编码后的节点/边构造可验证的覆盖图，并输出统计摘要与图谱量。
- **谱与 $\zeta$ 字典**：把图的谱对象与 Ihara 型生成函数组织到同一套记号与不等式链中。

## 当前进展（以生成物为准）

- **折叠核全表/退化直方图**：见 `sections/generated/fold6_full_table*.tex`、`fold6_preimage_histogram_table.tex`
- **边界态预像对**：见 `sections/generated/fold6_boundary_preimages_table.tex`
- **单图覆盖统计摘要**：见 `sections/generated/cover_graph_summary.tex`
- **产物哈希登记**：见 `sections/generated/artifact_hash_registry.json` 与 `artifact_hash_registry_summary.tex`

## 下一步（建议按优先级）

- **跨尺度接口的“可证不等式”化**
  - 把实验中出现的谱隙/混合时间现象转写成可证明的上下界链条
  - 明确常数、条件与适用范围（避免叙事性跳跃）
- **条件桥接（HTF）与主干解耦**
  - 进一步压缩条件段的依赖面：主干结果不依赖 HTF 仍成立
  - HTF 仅作为“若满足某可审计桥接，则推出某结论”的独立模块
- **覆盖图构造的鲁棒性**
  - 检查不同随机种子/参数下的稳定性
  - 增加一致性检查（边界情形、对称性、已知特例复现）

## 一键复现

在本论文目录执行：

```bash
python3 -m pip install -r requirements.txt
python3 scripts/run_all.py
```

## 关键产物位置

- **正文直接引用的生成片段**：`sections/generated/`
- **实验产物目录**：`artifacts/`（包含内容寻址子目录与 `manifest.json`）
- **实验脚本入口**：`scripts/run_all.py`
- **可复现性说明**：`sections/10_reproducibility.tex`

