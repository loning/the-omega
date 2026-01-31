# 2026 Golden ratio driven scan–projection generation (recursive emergence)

本目录包含论文 `main.tex` 及其可复现实验流水线。

## 编译

在本目录下运行（与仓库内其他 `ctex` 论文一致）：

```bash
latexmk -xelatex -interaction=nonstopmode main.tex
```

## 复现实验

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

运行一键流水线：

```bash
python3 scripts/run_all.py
```

脚本将生成：

- `sections/generated/*.tex`：可直接 `\input{}` 的图/表 LaTeX 片段
- `artifacts/export/*`：CSV/PNG 等导出（用于审计与复核）

