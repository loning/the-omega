#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate LaTeX fragments (figures/tables) from exported CSV/PNGs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt

from common_paths import export_dir, generated_dir


@dataclass(frozen=True)
class Row:
    m: int
    stable_t: int
    resolve_t: int
    unresolved: int
    max_cls: int
    max_fiber: int
    avg_fiber: float


def read_rows(csv_path: Path) -> List[Row]:
    rows: List[Row] = []
    with csv_path.open("r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            rows.append(
                Row(
                    m=int(r["m"]),
                    stable_t=int(r["stable_t"]),
                    resolve_t=int(r["resolve_t"]),
                    unresolved=int(r["unresolved_micro_final"]),
                    max_cls=int(r["max_micro_class_size_final"]),
                    max_fiber=int(r["max_fiber_size"]),
                    avg_fiber=float(r["avg_fiber_size"]),
                )
            )
    return rows


def _sorted(rows: List[Row]) -> List[Row]:
    return sorted(rows, key=lambda x: x.m)


def plot_resolve_time(rows: List[Row], out_png: Path) -> None:
    plt.figure(figsize=(7, 4.2))
    ms = [r.m for r in rows]
    ys = [r.resolve_t for r in rows]
    plt.plot(ms, ys, marker="o")
    plt.xlabel("m")
    plt.ylabel("resolve_t (WL-1 iterations; 0 means not resolved)")
    plt.title("WL-1 resolve time vs m")
    plt.grid(True, alpha=0.3)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def plot_unresolved(rows: List[Row], out_png: Path) -> None:
    plt.figure(figsize=(7, 4.2))
    ms = [r.m for r in rows]
    frac = [r.unresolved / (1 << r.m) for r in rows]
    plt.plot(ms, frac, marker="o")
    plt.xlabel("m")
    plt.ylabel("unresolved fraction (micro)")
    plt.title("WL-1 unresolved fraction vs m")
    plt.grid(True, alpha=0.3)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def write_fig_tex(fig_name: str, png_rel: str, caption: str, label: str) -> None:
    p = generated_dir() / f"{fig_name}.tex"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "\\begin{figure}[H]\n"
        "\\centering\n"
        f"\\includegraphics[width=0.90\\linewidth]{{{png_rel}}}\n"
        f"\\caption{{{caption}}}\n"
        f"\\label{{{label}}}\n"
        "\\end{figure}\n",
        encoding="utf-8",
    )


def write_table_tex(rows: List[Row], out_name: str) -> None:
    rows = _sorted(rows)

    lines: List[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\caption{Zeckendorf 规范体系下的扫描结果（\\WL{}-1，含时间结构）。}")
    lines.append("\\label{tab:zeckendorf_scan_m}")
    lines.append("\\begin{tabular}{lrrrrr}")
    lines.append("\\toprule")
    lines.append("$m$ & stable\\_t & resolve\\_t & unresolved & max\\_fiber & avg\\_fiber\\\\")
    lines.append("\\midrule")
    for r in rows:
        lines.append(f"{r.m} & {r.stable_t} & {r.resolve_t} & {r.unresolved} & {r.max_fiber} & {r.avg_fiber:.3f}\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    (generated_dir() / f"{out_name}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    csv_in = export_dir() / "zeckendorf_scan_m3_to_m18.csv"
    rows = read_rows(csv_in)
    rows = _sorted(rows)

    png1 = export_dir() / "resolve_time_vs_m.png"
    png2 = export_dir() / "unresolved_vs_m.png"
    plot_resolve_time(rows, png1)
    plot_unresolved(rows, png2)

    write_fig_tex(
        "fig_resolve_time_vs_m",
        "artifacts/export/resolve_time_vs_m.png",
        "解析时间（\\WL{}-1 完全分解微观层所需迭代数）随 $m$ 的变化。0 表示在最大迭代步内未完全分解。",
        "fig:resolve_time_vs_m",
    )
    write_fig_tex(
        "fig_unresolved_vs_m",
        "artifacts/export/unresolved_vs_m.png",
        "残余未分解比例随 $m$ 的变化（稳定后微观层未分解点数除以 $2^m$）。",
        "fig:unresolved_vs_m",
    )
    write_table_tex(rows, "tab_zeckendorf_scan_m")

    # Dimension scan figures (bit-split open)
    write_fig_tex(
        "fig_resolve_time_vs_dimension",
        "artifacts/export/resolve_time_vs_dimension_m6_m9_m12_m15.png",
        "解析时间随维数 $d$ 的变化（bit-split open，$m\\in\\{6,9,12,15\\}$，Zeckendorf）。",
        "fig:resolve_time_vs_dimension",
    )
    write_fig_tex(
        "fig_unresolved_vs_dimension",
        "artifacts/export/unresolved_vs_dimension_m6_m9_m12_m15.png",
        "残余未分解规模随维数 $d$ 的变化（bit-split open，$m\\in\\{6,9,12,15\\}$，Zeckendorf）。",
        "fig:unresolved_vs_dimension",
    )

    print("[exp_generated_tex] OK", flush=True)


if __name__ == "__main__":
    main()

