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
    partial_quotients_prefix: str
    beta: float
    x0: float
    m: int
    N: int
    tv: float
    kl: float
    unique_types: int
    DN_star_upper_bound: float | None


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
                    partial_quotients_prefix=r.get("partial_quotients_prefix", ""),
                    beta=float(r["beta"]),
                    x0=float(r["x0"]),
                    m=int(r["m"]),
                    N=int(r["N"]),
                    tv=float(r["tv"]),
                    kl=float(r["kl"]),
                    unique_types=int(r["unique_types"]),
                    DN_star_upper_bound=float(r["DN_star_upper_bound"])
                    if r.get("DN_star_upper_bound", "").strip()
                    else None,
                )
            )
    return out


def mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else 0.0


def std(xs: List[float]) -> float:
    if not xs:
        return 0.0
    if len(xs) == 1:
        return 0.0
    mu = mean(xs)
    v = sum((x - mu) ** 2 for x in xs) / float(len(xs) - 1)
    return v**0.5


def group_stats(rows: List[Row]) -> Dict[Tuple[str, int, int], Tuple[float, float, float, float]]:
    """Key: (alpha_name, m, N) -> (mean_tv, std_tv, mean_kl, std_kl) over (beta,x0)."""
    buckets: Dict[Tuple[str, int, int], List[Row]] = {}
    for r in rows:
        k = (r.alpha_name, r.m, r.N)
        buckets.setdefault(k, []).append(r)
    out: Dict[Tuple[str, int, int], Tuple[float, float, float, float]] = {}
    for k, rs in buckets.items():
        tvs = [x.tv for x in rs]
        kls = [x.kl for x in rs]
        out[k] = (mean(tvs), std(tvs), mean(kls), std(kls))
    return out


def group_dn_star_upper(rows: List[Row]) -> Dict[Tuple[str, int, int], float]:
    """Key: (alpha_name, m, N) -> a representative D_N^* upper bound."""
    out: Dict[Tuple[str, int, int], float] = {}
    for r in rows:
        if r.DN_star_upper_bound is None:
            continue
        k = (r.alpha_name, r.m, r.N)
        if k not in out:
            out[k] = r.DN_star_upper_bound
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
    gs = group_stats(rows)

    lines: List[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{3pt}")
    lines.append("\\caption{旋转扫描模型：折叠后稳定类型直方图与 Parry(PF) 基准的偏差（对 $\\beta,x_0$ 取平均）。}")
    lines.append("\\label{tab:rotation_fold_vs_parry_summary}")
    lines.append("\\resizebox{\\linewidth}{!}{%")
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
            if r.alpha_name == "golden" and r.m == m and r.N == N_pick and r.DN_star_upper_bound is not None:
                golden_bound = r.DN_star_upper_bound
                break
        gb_str = f"{golden_bound:.3g}" if golden_bound is not None else "--"

        row_cells = [str(m), str(N_pick), gb_str]
        for a in alpha_names:
            tv_mu, _, kl_mu, _ = gs.get((a, m, N_pick), (0.0, 0.0, 0.0, 0.0))
            row_cells.append(f"{tv_mu:.3g}")
            row_cells.append(f"{kl_mu:.3g}")
        lines.append(" & ".join(row_cells) + "\\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("}%")
    lines.append("\\end{table}")
    (generated_dir() / f"{out_name}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_tv_vs_m(rows: List[Row], N_pick: int, out_png: Path) -> None:
    gs = group_stats(rows)
    ms = sorted({r.m for r in rows})
    alpha_names = sorted({r.alpha_name for r in rows})

    plt.figure(figsize=(7.2, 4.2))
    for a in alpha_names:
        xs = [m for m in ms if (a, m, N_pick) in gs]
        ys = [gs[(a, m, N_pick)][0] for m in xs]
        yerr = [gs[(a, m, N_pick)][1] for m in xs]
        plt.errorbar(xs, ys, yerr=yerr, marker="o", capsize=3, linewidth=1.5, label=a)
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
    gs = group_stats(rows)
    ms = sorted({r.m for r in rows})
    alpha_names = sorted({r.alpha_name for r in rows})

    plt.figure(figsize=(7.2, 4.2))
    for a in alpha_names:
        xs = [m for m in ms if (a, m, N_pick) in gs]
        ys = [gs[(a, m, N_pick)][2] for m in xs]
        yerr = [gs[(a, m, N_pick)][3] for m in xs]
        plt.errorbar(xs, ys, yerr=yerr, marker="o", capsize=3, linewidth=1.5, label=a)
    plt.xlabel("m")
    plt.ylabel("KL divergence to Parry baseline")
    plt.title(f"Rotation scan: $D_{{KL}}(\\hat{{\\pi}}_m\\|\\pi_m)$ vs m (N={N_pick})")
    plt.grid(True, alpha=0.3)
    plt.legend()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def plot_tv_vs_n(rows: List[Row], m_pick: int, out_png: Path) -> None:
    gs = group_stats(rows)
    gb = group_dn_star_upper(rows)
    Ns = sorted({r.N for r in rows})
    alpha_names = sorted({r.alpha_name for r in rows})

    plt.figure(figsize=(7.2, 4.2))
    for a in alpha_names:
        xs = [N for N in Ns if (a, m_pick, N) in gs]
        ys = [gs[(a, m_pick, N)][0] for N in xs]
        yerr = [gs[(a, m_pick, N)][1] for N in xs]
        plt.errorbar(xs, ys, yerr=yerr, marker="o", capsize=3, linewidth=1.5, label=a)

        # Theory envelope (finite-sample term): (m+1) * D_N^* upper bound.
        bx = [N for N in xs if (a, m_pick, N) in gb]
        if bx:
            by = [(m_pick + 1) * gb[(a, m_pick, N)] for N in bx]
            # Avoid legend explosion: don't add these envelopes to the legend.
            plt.plot(bx, by, linestyle="--", linewidth=1.0, alpha=0.6, label="_nolegend_")
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("N (log)")
    plt.ylabel("TV distance to Parry baseline (log)")
    plt.title(f"Rotation scan: $D_{{TV}}(\\hat{{\\pi}}_m,\\pi_m)$ vs N (m={m_pick})")
    plt.grid(True, which="both", alpha=0.25)
    plt.legend()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def plot_kl_vs_n(rows: List[Row], m_pick: int, out_png: Path) -> None:
    gs = group_stats(rows)
    Ns = sorted({r.N for r in rows})
    alpha_names = sorted({r.alpha_name for r in rows})

    plt.figure(figsize=(7.2, 4.2))
    for a in alpha_names:
        xs = [N for N in Ns if (a, m_pick, N) in gs]
        ys = [gs[(a, m_pick, N)][2] for N in xs]
        yerr = [gs[(a, m_pick, N)][3] for N in xs]
        plt.errorbar(xs, ys, yerr=yerr, marker="o", capsize=3, linewidth=1.5, label=a)
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("N (log)")
    plt.ylabel("KL divergence to Parry baseline (log)")
    plt.title(f"Rotation scan: $D_{{KL}}(\\hat{{\\pi}}_m\\|\\pi_m)$ vs N (m={m_pick})")
    plt.grid(True, which="both", alpha=0.25)
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
    ms = sorted({r.m for r in rows})
    m_pick = 12 if 12 in ms else ms[len(ms) // 2]

    png_tv = export_dir() / "rotation_tv_vs_m.png"
    png_kl = export_dir() / "rotation_kl_vs_m.png"
    png_tv_n = export_dir() / "rotation_tv_vs_n.png"
    png_kl_n = export_dir() / "rotation_kl_vs_n.png"
    plot_tv_vs_m(rows, N_pick=N_pick, out_png=png_tv)
    plot_kl_vs_m(rows, N_pick=N_pick, out_png=png_kl)
    plot_tv_vs_n(rows, m_pick=m_pick, out_png=png_tv_n)
    plot_kl_vs_n(rows, m_pick=m_pick, out_png=png_kl_n)

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

    write_fig_tex(
        fig_name="fig_rotation_tv_vs_n",
        png_rel="artifacts/export/rotation_tv_vs_n.png",
        caption=f"旋转扫描模型下，固定分辨率 $m={m_pick}$ 时，折叠后稳定类型直方图与 Parry(PF) 基准柱分布的总变差距离随样本量 $N$ 的收敛（对 $\\beta,x_0$ 取平均；误差线为样本标准差；虚线为 $(m+1)D_N^*$ 的差异度上界络线；双对数坐标）。",
        label="fig:rotation_tv_vs_n",
    )
    write_fig_tex(
        fig_name="fig_rotation_kl_vs_n",
        png_rel="artifacts/export/rotation_kl_vs_n.png",
        caption=f"旋转扫描模型下，固定分辨率 $m={m_pick}$ 时，折叠后稳定类型直方图与 Parry(PF) 基准柱分布的相对熵随样本量 $N$ 的收敛（对 $\\beta,x_0$ 取平均；误差线为样本标准差；双对数坐标）。",
        label="fig:rotation_kl_vs_n",
    )

    write_table_summary(rows, out_name="tab_rotation_fold_vs_parry_summary", N_pick=N_pick)

    print("[exp_generated_tex] OK", flush=True)


if __name__ == "__main__":
    main()

