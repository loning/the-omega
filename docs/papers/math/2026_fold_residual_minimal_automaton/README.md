# 2026\_fold\_residual\_minimal\_automaton

本文目录为论文《Fold-with-residual 的最小有限状态实现：基于 Zeckendorf 规范化的残差最小化框架》的源文件与复现实验脚手架。

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

## 复现实验（生成 `sections/generated/`）

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/run_all.py
```

产物会写入 `sections/generated/`，并在 LaTeX 中被自动包含。

