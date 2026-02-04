#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare intrinsic correlation time vs twisted mixing time (real-input 40-state kernel).

We compare two time scales:
- tau_corr(0): correlation time from the Parry equilibrium chain at theta(t)=(t,0,-t), t=0,
  based on r_corr := Lambda/lambda1 (spectral gap ratio of the weighted matrix).
- tau_mix(3,3,5): worst twisted spectral radius ratio r_mix := rho_{3,3,5}/lambda from the
  (3,3,5) Dirichlet--Mertens character tensor with third axis N2 mod 5.

Inputs:
- artifacts/export/real_input_40_time_correlation.json
- artifacts/export/sync_kernel_real_input_40_arity_3d_N2_335.json

Outputs:
- artifacts/export/real_input_40_tau_corr_vs_tau_mix.csv
- sections/generated/tab_real_input_40_tau_corr_vs_tau_mix.tex
- artifacts/export/real_input_40_tau_corr_vs_tau_mix.png
- sections/generated/fig_real_input_40_tau_corr_vs_tau_mix.tex
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt

from common_paths import export_dir, generated_dir, paper_root


def _load_json(rel: str) -> Dict[str, Any]:
    return json.loads((paper_root() / rel).read_text(encoding="utf-8"))


def _gap_tau_half(r: float) -> Tuple[float, float, float]:
    r = float(r)
    if not (0.0 < r < 1.0):
        return (float("inf"), float("inf"), float("inf"))
    gap = -math.log(r)
    if gap <= 0.0:
        return (float("inf"), float("inf"), float("inf"))
    tau = 1.0 / gap
    half = math.log(2.0) / gap
    return (gap, tau, half)


def _find_nearest_grid_entry(grid: List[Dict[str, Any]], t0: float) -> Dict[str, Any]:
    if not grid:
        raise RuntimeError("empty grid")
    best = min(grid, key=lambda g: abs(float(g.get("t", 0.0)) - float(t0)))
    return best


def _write_fig_tex(fig_name: str, png_rel: str, caption: str, label: str) -> None:
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


def _lin_interp_root(t0: float, y0: float, t1: float, y1: float) -> float:
    """Return linear-interpolated root for y(t)=0 on [t0,t1]."""
    if not (
        math.isfinite(t0)
        and math.isfinite(t1)
        and math.isfinite(y0)
        and math.isfinite(y1)
    ):
        return float("nan")
    if t1 == t0:
        return float(t0)
    if y1 == y0:
        return 0.5 * (t0 + t1)
    return t0 + (0.0 - y0) * (t1 - t0) / (y1 - y0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare tau_corr(0) vs tau_mix from (3,3,5) twisted ratio"
    )
    parser.add_argument(
        "--time-corr-json",
        type=str,
        default="artifacts/export/real_input_40_time_correlation.json",
    )
    parser.add_argument(
        "--arity-json",
        type=str,
        default="artifacts/export/sync_kernel_real_input_40_arity_3d_N2_335.json",
    )
    parser.add_argument(
        "--triple",
        type=str,
        default="3x3x5",
        help="Triple key inside arity JSON (default: 3x3x5)",
    )
    parser.add_argument(
        "--csv-out",
        type=str,
        default=str(export_dir() / "real_input_40_tau_corr_vs_tau_mix.csv"),
    )
    parser.add_argument(
        "--tex-out",
        type=str,
        default=str(generated_dir() / "tab_real_input_40_tau_corr_vs_tau_mix.tex"),
    )
    parser.add_argument(
        "--png-out",
        type=str,
        default=str(export_dir() / "real_input_40_tau_corr_vs_tau_mix.png"),
    )
    parser.add_argument(
        "--fig-tex-out",
        type=str,
        default=str(generated_dir() / "fig_real_input_40_tau_corr_vs_tau_mix.tex"),
    )
    args = parser.parse_args()

    tc = _load_json(str(args.time_corr_json))
    ar = _load_json(str(args.arity_json))

    grid = tc.get("grid")
    if not isinstance(grid, list):
        raise RuntimeError("time correlation json: missing 'grid' list")
    g0 = _find_nearest_grid_entry(grid, t0=0.0)

    r_corr_grid = float(g0.get("r", 0.0))
    r_corr_payload = float(tc.get("corr", {}).get("r", r_corr_grid))  # type: ignore[union-attr]
    r_corr = r_corr_payload if r_corr_payload > 0.0 else r_corr_grid
    gap_corr, tau_corr, half_corr = _gap_tau_half(r_corr)

    triple = str(args.triple)
    ratios = ar.get("triple_rho_max_ratio")
    if not isinstance(ratios, dict) or triple not in ratios:
        raise RuntimeError(f"arity json: missing triple_rho_max_ratio['{triple}']")
    r_mix = float(ratios[triple])
    gap_mix, tau_mix, half_mix = _gap_tau_half(r_mix)

    # Nearest point (on the discrete t grid) where tau_corr(t) is closest to tau_mix.
    t_star = float("nan")
    tau_star = float("nan")
    r_star = float("nan")
    delta_tau_star = float("nan")
    # Bracket and linear-interpolated crossing estimate for y(t)=tau_corr(t)-tau_mix.
    t_left = float("nan")
    t_right = float("nan")
    tau_left = float("nan")
    tau_right = float("nan")
    y_left = float("nan")
    y_right = float("nan")
    dt_local = float("nan")
    t_root_lin = float("nan")
    if math.isfinite(tau_mix):
        finite: List[Tuple[float, float, float]] = []
        for g in grid:
            try:
                tt = float(g.get("t", float("nan")))
                tau_t = float(g.get("tau", float("nan")))
                rr = float(g.get("r", float("nan")))
            except Exception:
                continue
            if math.isfinite(tt) and math.isfinite(tau_t):
                finite.append((tt, tau_t, rr))
        if finite:
            finite.sort(key=lambda x: x[0])
            idx = min(
                range(len(finite)),
                key=lambda k: abs(float(finite[k][1]) - float(tau_mix)),
            )
            t_star, tau_star, r_star = finite[idx]
            delta_tau_star = float(tau_star - tau_mix)

            # Local grid spacing.
            dt_candidates: List[float] = []
            if idx - 1 >= 0:
                dt_candidates.append(abs(finite[idx][0] - finite[idx - 1][0]))
            if idx + 1 < len(finite):
                dt_candidates.append(abs(finite[idx + 1][0] - finite[idx][0]))
            dt_local = min(dt_candidates) if dt_candidates else float("nan")

            # Choose a bracket segment for linear root estimation.
            cand_pairs: List[Tuple[int, int]] = []
            if idx - 1 >= 0:
                cand_pairs.append((idx - 1, idx))
            if idx + 1 < len(finite):
                cand_pairs.append((idx, idx + 1))

            chosen: Tuple[int, int] | None = None
            for a, b in cand_pairs:
                ya = float(finite[a][1] - tau_mix)
                yb = float(finite[b][1] - tau_mix)
                if ya == 0.0 or yb == 0.0 or (ya > 0.0) != (yb > 0.0):
                    chosen = (a, b)
                    break

            if chosen is None:
                best_pair: Tuple[int, int] | None = None
                best_score = float("inf")
                for k in range(len(finite) - 1):
                    ya = float(finite[k][1] - tau_mix)
                    yb = float(finite[k + 1][1] - tau_mix)
                    if ya == 0.0 or yb == 0.0 or (ya > 0.0) != (yb > 0.0):
                        score = min(abs(ya), abs(yb))
                        if score < best_score:
                            best_score = score
                            best_pair = (k, k + 1)
                chosen = best_pair

            if chosen is None:
                chosen = (max(0, idx - 1), min(len(finite) - 1, idx + 1))

            a, b = chosen
            t_left, tau_left, _ = finite[a]
            t_right, tau_right, _ = finite[b]
            y_left = float(tau_left - tau_mix)
            y_right = float(tau_right - tau_mix)
            t_root_lin = _lin_interp_root(t_left, y_left, t_right, y_right)
            lo = min(t_left, t_right)
            hi = max(t_left, t_right)
            if math.isfinite(t_root_lin):
                t_root_lin = min(max(t_root_lin, lo), hi)

    tau_ratio = (
        (tau_mix / tau_corr)
        if (math.isfinite(tau_mix) and math.isfinite(tau_corr) and tau_corr > 0)
        else float("inf")
    )
    r_ratio = (r_mix / r_corr) if (r_corr > 0.0) else float("nan")
    log_sus_mix = math.log(1.0 / (1.0 - r_mix)) if (0.0 < r_mix < 1.0) else float("nan")

    # CSV (single-row audit record).
    csv_path = Path(args.csv_out)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "time_corr_json",
            "arity_json",
            "triple",
            "r_corr",
            "r_corr_grid",
            "r_corr_payload",
            "gap_corr",
            "tau_corr",
            "half_corr",
            "r_mix",
            "gap_mix",
            "tau_mix",
            "half_mix",
            "tau_ratio",
            "r_ratio",
            "log_sus_mix",
            "t_star",
            "tau_star",
            "r_star",
            "delta_tau_star",
            "t_left",
            "t_right",
            "tau_left",
            "tau_right",
            "y_left",
            "y_right",
            "dt_local",
            "t_root_lin",
        ]
        wr = csv.DictWriter(f, fieldnames=fieldnames)
        wr.writeheader()
        wr.writerow(
            {
                "time_corr_json": str(args.time_corr_json),
                "arity_json": str(args.arity_json),
                "triple": triple,
                "r_corr": r_corr,
                "r_corr_grid": r_corr_grid,
                "r_corr_payload": r_corr_payload,
                "gap_corr": gap_corr,
                "tau_corr": tau_corr,
                "half_corr": half_corr,
                "r_mix": r_mix,
                "gap_mix": gap_mix,
                "tau_mix": tau_mix,
                "half_mix": half_mix,
                "tau_ratio": tau_ratio,
                "r_ratio": r_ratio,
                "log_sus_mix": log_sus_mix,
                "t_star": t_star,
                "tau_star": tau_star,
                "r_star": r_star,
                "delta_tau_star": delta_tau_star,
                "t_left": t_left,
                "t_right": t_right,
                "tau_left": tau_left,
                "tau_right": tau_right,
                "y_left": y_left,
                "y_right": y_right,
                "dt_local": dt_local,
                "t_root_lin": t_root_lin,
            }
        )

    # LaTeX table fragment.
    tex_path = Path(args.tex_out)
    tex_path.parent.mkdir(parents=True, exist_ok=True)

    def fmt(x: float) -> str:
        if not math.isfinite(x):
            return "\\infty"
        return f"{x:.12f}"

    lines: List[str] = []
    lines.append("% AUTO-GENERATED by scripts/exp_real_input_40_tau_corr_vs_tau_mix.py")
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\small")
    lines.append("\\setlength{\\tabcolsep}{8pt}")
    lines.append("\\renewcommand{\\arraystretch}{1.15}")
    lines.append(
        "\\caption{真实输入 40 状态核的时间尺度分离：平衡态内生相关时间 $\\tau_{\\mathrm{corr}}(0)$（$\\chi$ 切片 $t=0$）与角色扭曲的混合时间 $\\tau_{\\mathrm{mix}}(3,3,5)$（由 $((3,3,5))$ 最坏谱半径比 $\\rho_{3,3,5}/\\lambda$ 导出）。}"
    )
    lines.append("\\label{tab:real-input-40-tau-corr-vs-tau-mix}")
    lines.append("\\begin{tabular}{l r r r r}")
    lines.append("\\toprule")
    lines.append(
        "尺度 & $r$ & $-\\log r$ & $\\tau:=1/(-\\log r)$ & $t_{1/2}:=\\log 2/(-\\log r)$\\\\"
    )
    lines.append("\\midrule")
    lines.append(
        "\\, $\\tau_{\\mathrm{corr}}(0)$（$r=\\Lambda/\\lambda_1$）"
        f" & {fmt(r_corr)} & {fmt(gap_corr)} & {fmt(tau_corr)} & {fmt(half_corr)}\\\\"
    )
    lines.append(
        "\\, $\\tau_{\\mathrm{mix}}(3,3,5)$（$r=\\rho_{3,3,5}/\\lambda$）"
        f" & {fmt(r_mix)} & {fmt(gap_mix)} & {fmt(tau_mix)} & {fmt(half_mix)}\\\\"
    )
    lines.append("\\midrule")
    lines.append(
        f"$\\tau_{{\\mathrm{{mix}}}}/\\tau_{{\\mathrm{{corr}}}}(0)$ & \\multicolumn{{4}}{{l}}{{{fmt(tau_ratio)}}}\\\\"
    )
    lines.append(
        f"$(\\rho_{{3,3,5}}/\\lambda)/(\\Lambda/\\lambda_1)$ & \\multicolumn{{4}}{{l}}{{{fmt(r_ratio)}}}\\\\"
    )
    lines.append(
        f"$\\log\\bigl(1/(1-\\rho_{{3,3,5}}/\\lambda)\\bigr)$ & \\multicolumn{{4}}{{l}}{{{fmt(log_sus_mix)}}}\\\\"
    )
    lines.append("\\midrule")
    lines.append(f"$t_\\star$ (grid) & \\multicolumn{{4}}{{l}}{{{fmt(t_star)}}}\\\\")
    lines.append(
        f"$\\tau_{{\\mathrm{{corr}}}}(t_\\star)$ & \\multicolumn{{4}}{{l}}{{{fmt(tau_star)}}}\\\\"
    )
    lines.append(
        f"$\\tau_{{\\mathrm{{corr}}}}(t_\\star)-\\tau_{{\\mathrm{{mix}}}}(3,3,5)$ & \\multicolumn{{4}}{{l}}{{{fmt(delta_tau_star)}}}\\\\"
    )
    lines.append(
        f"$[t_-,t_+]$ (grid bracket) & \\multicolumn{{4}}{{l}}{{[{fmt(t_left)},{fmt(t_right)}]}}\\\\"
    )
    lines.append(
        f"$t_0$ (linear root in $[t_-,t_+]$) & \\multicolumn{{4}}{{l}}{{{fmt(t_root_lin)}}}\\\\"
    )
    lines.append(
        f"$\\Delta t$ (local grid) & \\multicolumn{{4}}{{l}}{{{fmt(dt_local)}}}\\\\"
    )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    tex_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Figure: tau_corr(t) curve with tau_mix horizontal line.
    ts = [float(g["t"]) for g in grid if "t" in g]
    taus = [float(g.get("tau", float("inf"))) for g in grid]
    out_png = Path(args.png_out)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(1, 1, figsize=(7.8, 4.2))
    ax.plot(ts, taus, lw=2.0, label=r"$\tau_{\mathrm{corr}}(t)$")
    if math.isfinite(tau_mix):
        ax.axhline(tau_mix, lw=1.8, ls="--", label=r"$\tau_{\mathrm{mix}}(3,3,5)$")
    ax.scatter([0.0], [tau_corr], s=28.0, zorder=3)
    if math.isfinite(t_star) and math.isfinite(tau_star):
        ax.scatter([t_star], [tau_star], s=36.0, zorder=4)
    if math.isfinite(t_root_lin) and math.isfinite(tau_mix):
        ax.scatter([t_root_lin], [tau_mix], s=36.0, zorder=4)
    ax.set_xlabel(r"$t$")
    ax.set_ylabel(r"time scale")
    ax.set_title("real-input-40: tau_corr(t) vs tau_mix")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close(fig)

    fig_tex_path = Path(args.fig_tex_out)
    fig_tex_path.parent.mkdir(parents=True, exist_ok=True)
    _write_fig_tex(
        fig_name=fig_tex_path.stem,
        png_rel="artifacts/export/real_input_40_tau_corr_vs_tau_mix.png",
        caption=(
            "时间尺度分离的可视化对比：$\\chi$ 切片上的内生相关时间曲线 $\\tau_{\\mathrm{corr}}(t)$ "
            "与由 $((3,3,5))$ 最坏角色扭曲给出的混合时间 $\\tau_{\\mathrm{mix}}(3,3,5)$（水平虚线）。"
        ),
        label="fig:real-input-40-tau-corr-vs-tau-mix",
    )

    print(f"[tau-compare] wrote {csv_path}", flush=True)
    print(f"[tau-compare] wrote {tex_path}", flush=True)
    print(f"[tau-compare] wrote {out_png}", flush=True)
    print(f"[tau-compare] wrote {fig_tex_path}", flush=True)
    print("[tau-compare] done", flush=True)


if __name__ == "__main__":
    main()
