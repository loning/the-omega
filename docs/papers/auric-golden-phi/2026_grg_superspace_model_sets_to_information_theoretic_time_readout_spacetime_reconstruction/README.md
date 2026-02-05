# 2026 GRG superspace model sets → information-theoretic time (spacetime reconstruction)

本目录包含英文论文源文件 `main_en.tex` 及其可复现实验流水线（生成 `sections/generated/` 下的图与 `artifacts/` 下的审计数据）。

## 编译

在本目录下运行：

```bash
latexmk -pdf -interaction=nonstopmode main_en.tex
```

## 复现实验（生成图与审计数据）

安装 Python 依赖：

```bash
python3 -m pip install -r requirements.txt
```

一键生成全部演示输出：

```bash
python3 scripts/run_all.py
```

脚本将生成：

- `sections/generated/*.png`：论文中引用的图像
- `sections/generated/*.tex`：可直接 `\input{}` 的数值摘要片段
- `artifacts/*.json`：参数快照、运行日志与指纹/检查结果（用于审计与复核）

