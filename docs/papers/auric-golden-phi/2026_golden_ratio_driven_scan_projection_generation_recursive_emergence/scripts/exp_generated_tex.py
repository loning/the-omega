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
    model: str
    alpha_name: str
    alpha: float
    beta: float
    x0: float
    m: int
    N: int
    tv: float
    kl: float
    unique_types: int
    golden_DN_star_upper_bound: float | None


def read_rows(csv_path: Path) -> List[Row]:
    out: List[Row] = []
    with csv_path.open("r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            out.append(
                Row(
                    model=r["model"],
                    alpha_name=r["alpha_name"],
                    alpha=float(r["alpha"]),
                    beta=float(r["beta"]),
                    x0=float(r["x0"]),
                    m=int(r["m"]),
                    N=int(r["N"]),
                    tv=float(r["tv"]),
                    kl=float(r["kl"]),
                    unique_types=int(r["unique_types"]),
                    golden_DN_star_upper_bound=float(r["golden_DN_star_upper_bound"])
                    if r["golden_DN_star_upper_bound"].strip()
                    else None,
                )
            )
    return out


def mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else 0.0


def group_mean(rows: List[Row]) -> Dict[Tuple[str, int, int], Tuple[float, float]]:
    """Key: (alpha_name, m, N) -> (mean_tv, mean_kl) averaged over (beta,x0)."""
    buckets: Dict[Tuple[str, int, int], List[Row]] = {}
    for r in rows:
        k = (r.alpha_name, r.m, r.N)
        buckets.setdefault(k, []).append(r)
    out: Dict[Tuple[str, int, int], Tuple[float, float]] = {}
    for k, rs in buckets.items():
        out[k] = (mean([x.tv for x in rs]), mean([x.kl for x in rs]))
    return out


def latex_escape_text(s: str) -> str:
    """Escape minimal LaTeX special chars for plain text fields."""
    return s.replace("_", "\\_")


def write_fig_tex(fig_name: str, png_rel: str, caption: str, label: str) -> None:
    p = generated_dir() / f"{fig_name}.tex"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "\\begin{figure}[H]\n"
        "\\centering\n"
        f"\\includegraphics[width=0.92\\linewidth]{{{png_rel}}}\n"
        f"\\caption{{{caption}}}\n"
        f"\\label{{{label}}}\n"
        "\\end{figure}\n",
        encoding="utf-8",
    )


def write_table_summary(rows: List[Row], out_name: str, N_pick: int) -> None:
    ms = sorted({r.m for r in rows})
    alpha_names = sorted({r.alpha_name for r in rows})
    gm = group_mean(rows)

    lines: List[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\caption{旋转扫描模型：折叠后稳定类型直方图与 Parry(PF) 基准的偏差（对 $\\beta,x_0$ 取平均）。}")
    lines.append("\\label{tab:rotation_fold_vs_parry_summary}")
    lines.append("\\begin{tabular}{lrr" + "rr" * len(alpha_names) + "}")
    lines.append("\\toprule")

    hdr = ["$m$", "$N$", "golden $D_N^*$ upper"]
    for a in alpha_names:
        a_tex = latex_escape_text(a)
        hdr.extend([f"{a_tex} $D_\\mathrm{{TV}}$", f"{a_tex} $D_\\mathrm{{KL}}$"])
    lines.append(" & ".join(hdr) + "\\\\")
    lines.append("\\midrule")

    for m in ms:
        # Use golden bound from any golden row, if present.
        golden_bound = None
        for r in rows:
            if r.alpha_name == "golden" and r.m == m and r.N == N_pick and r.golden_DN_star_upper_bound is not None:
                golden_bound = r.golden_DN_star_upper_bound
                break
        gb_str = f"{golden_bound:.3g}" if golden_bound is not None else "--"

        row_cells = [str(m), str(N_pick), gb_str]
        for a in alpha_names:
            tv, kl = gm.get((a, m, N_pick), (0.0, 0.0))
            row_cells.append(f"{tv:.3g}")
            row_cells.append(f"{kl:.3g}")
        lines.append(" & ".join(row_cells) + "\\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    (generated_dir() / f"{out_name}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_tv_vs_m(rows: List[Row], N_pick: int, out_png: Path) -> None:
    gm = group_mean(rows)
    ms = sorted({r.m for r in rows})
    alpha_names = sorted({r.alpha_name for r in rows})

    plt.figure(figsize=(7.2, 4.2))
    for a in alpha_names:
        ys = [gm[(a, m, N_pick)][0] for m in ms if (a, m, N_pick) in gm]
        xs = [m for m in ms if (a, m, N_pick) in gm]
        plt.plot(xs, ys, marker="o", label=a)
    plt.xlabel("m")
    plt.ylabel("TV distance to Parry baseline")
    plt.title(f"Rotation scan: $D_{{TV}}(\\hat{{\\pi}}_m,\\pi_m)$ vs m (N={N_pick})")
    plt.grid(True, alpha=0.3)
    plt.legend()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def plot_kl_vs_m(rows: List[Row], N_pick: int, out_png: Path) -> None:
    gm = group_mean(rows)
    ms = sorted({r.m for r in rows})
    alpha_names = sorted({r.alpha_name for r in rows})

    plt.figure(figsize=(7.2, 4.2))
    for a in alpha_names:
        ys = [gm[(a, m, N_pick)][1] for m in ms if (a, m, N_pick) in gm]
        xs = [m for m in ms if (a, m, N_pick) in gm]
        plt.plot(xs, ys, marker="o", label=a)
    plt.xlabel("m")
    plt.ylabel("KL divergence to Parry baseline")
    plt.title(f"Rotation scan: $D_{{KL}}(\\hat{{\\pi}}_m\\|\\pi_m)$ vs m (N={N_pick})")
    plt.grid(True, alpha=0.3)
    plt.legend()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def main() -> None:
    csv_in = export_dir() / "rotation_fold_vs_parry.csv"
    rows = read_rows(csv_in)
    if not rows:
        raise SystemExit("[exp_generated_tex] empty input")

    Ns = sorted({r.N for r in rows})
    N_pick = Ns[-1]

    png_tv = export_dir() / "rotation_tv_vs_m.png"
    png_kl = export_dir() / "rotation_kl_vs_m.png"
    plot_tv_vs_m(rows, N_pick=N_pick, out_png=png_tv)
    plot_kl_vs_m(rows, N_pick=N_pick, out_png=png_kl)

    write_fig_tex(
        fig_name="fig_rotation_tv_vs_m",
        png_rel="artifacts/export/rotation_tv_vs_m.png",
        caption="旋转扫描模型下，折叠后稳定类型直方图与 Parry(PF) 基准柱分布的总变差距离随 $m$ 的变化（对 $\\beta,x_0$ 取平均）。",
        label="fig:rotation_tv_vs_m",
    )
    write_fig_tex(
        fig_name="fig_rotation_kl_vs_m",
        png_rel="artifacts/export/rotation_kl_vs_m.png",
        caption="旋转扫描模型下，折叠后稳定类型直方图与 Parry(PF) 基准柱分布的相对熵随 $m$ 的变化（对 $\\beta,x_0$ 取平均）。",
        label="fig:rotation_kl_vs_m",
    )

    write_table_summary(rows, out_name="tab_rotation_fold_vs_parry_summary", N_pick=N_pick)

    print("[exp_generated_tex] OK", flush=True)


if __name__ == "__main__":
    main()

