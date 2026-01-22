# 2026 Zeckendorf spacetime GI/WL framework

本文给出一个以 Zeckendorf 截断折叠为规范的“时空结构图”统一接口，并把该接口与 Babai 的 \WL{} / 相干配置框架对齐；实验部分给出 Zeckendorf 规范体系下的可复现指标与扫描结果。

## 编译

在本目录下运行 LaTeX（XeLaTeX，推荐，与仓库内其他 ctex 论文一致）：

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

- `sections/generated/*.tex`：可直接 `\input{}` 的图表/表格片段
- `artifacts/export/*`：CSV/PNG 等人类可读导出

