# 2026_fold64_fiber_ca_m6

本文目录为论文《基于 Zeckendorf 折叠核的有限分辨率代数与可视化元胞自动机：(m=6) 情形的 (64→21) 纤维化与局域重写实现》的源文件与复现实验脚手架。

## 构建 PDF

在本目录下执行（任选其一）：

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

或（不使用 latexmk 时，需要额外跑 bibtex）：

```bash
xelatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

## 复现实验（可选）

在本目录下生成规则表并做全对验证：

```bash
python3 scripts/generate_fold64_ca_rules.py
python3 scripts/fold64_ca.py artifacts/fold64_ca_rules_phase90.json
```

生成三层时空图（输出到 `artifacts/`）：

```bash
python3 scripts/visualize_fold_unfold_ca.py
```

## 实时可视化（运行中观看演化）

打开一个实时滚动时空窗（默认三层同屏：micro/w/u）：

```bash
python3 scripts/live_ca_viewer.py
```

常用参数示例：

```bash
# 更慢、更清晰：每 2 步刷新一次，20 FPS
python3 scripts/live_ca_viewer.py --fps 20 --every 2

# 仅看微态层
python3 scripts/live_ca_viewer.py --panels micro

# 更大环、更长历史窗口
python3 scripts/live_ca_viewer.py --L 512 --history 512 --seed random
```

