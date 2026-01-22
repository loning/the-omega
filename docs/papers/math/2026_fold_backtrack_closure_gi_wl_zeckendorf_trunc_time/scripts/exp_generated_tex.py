#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate LaTeX fragments under sections/generated/ from experiment outputs."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import export_dir, generated_dir, paper_root
from common_tex_pylatex import write_lines_as_fragment, write_tabular_fragment


@dataclass(frozen=True)
class FigSpec:
    out_tex: str
    image: str
    width: str
    caption: str
    label: str


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        rdr = csv.DictReader(f)
        return [dict(r) for r in rdr]


def _figure_fragment(fig: FigSpec) -> List[str]:
    return [
        r"\begin{figure}[H]",
        r"\centering",
        rf"\includegraphics[width={fig.width}]{{{fig.image}}}",
        rf"\caption{{{fig.caption}}}",
        rf"\label{{{fig.label}}}",
        r"\end{figure}",
    ]


def _fmt_float(x: str) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    if s == "":
        return ""
    try:
        v = float(s)
        if v.is_integer():
            return str(int(v))
        return f"{v:.3g}"
    except Exception:
        return s


def _tex_escape_text(s: str) -> str:
    # Minimal TeX escaping for table text cells.
    out = str(s)
    out = out.replace("\\", r"\textbackslash{}")
    out = out.replace("&", r"\&")
    out = out.replace("%", r"\%")
    out = out.replace("#", r"\#")
    out = out.replace("_", r"\_")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)

    figs: List[FigSpec] = [
        FigSpec(
            out_tex="fig_hypercube_residual_ambiguity.tex",
            image="artifacts/export/hypercube_residual_ambiguity_m3_to_m18.png",
            width=r"0.95\linewidth",
            caption=r"Hypercube 微观邻接下，闭包图上 1-WL 的残余未分解规模随 $m$ 的变化（$m=3$ 至 $18$）。",
            label="fig:hypercube_residual",
        ),
        FigSpec(
            out_tex="fig_resolve_time_vs_dimension.tex",
            image="artifacts/export/resolve_time_vs_dimension_m6_m9_m12_m15.png",
            width=r"0.95\linewidth",
            caption=r"Bit-split（开边界）维数扫描：塌缩时间 $t_{\\mathrm{resolve}}$ 随维数 $d$ 的变化。",
            label="fig:resolve_vs_dim",
        ),
        FigSpec(
            out_tex="fig_unresolved_vs_dimension.tex",
            image="artifacts/export/unresolved_vs_dimension_m6_m9_m12_m15.png",
            width=r"0.95\linewidth",
            caption=r"Bit-split（开边界）维数扫描：稳定后未分解微观点数 $u$ 随维数 $d$ 的变化。",
            label="fig:unresolved_vs_dim",
        ),
        FigSpec(
            out_tex="fig_m6_hilbert_2d_grid.tex",
            image="artifacts/export/m6_2d_hilbert_grid.png",
            width=r"0.55\linewidth",
            caption=r"$m=6$：Hilbert 2D（$8\\times 8$）嵌入示意（索引到格点）。",
            label="fig:m6_hilbert2d",
        ),
        FigSpec(
            out_tex="fig_m6_hilbert_3d_layers.tex",
            image="artifacts/export/m6_3d_hilbert_layers.png",
            width=r"0.75\linewidth",
            caption=r"$m=6$：Hilbert 3D（$4\\times 4\\times 4$）分层示意（按 $z$ 切片）。",
            label="fig:m6_hilbert3d",
        ),
    ]

    # Tabular: m=6 model compare (small)
    m6_models_csv = export_dir() / "m6_wl1_hilbert_vs_bitsplit_vs_hypercube.csv"
    m6_models_rows = _read_csv(m6_models_csv)
    m6_rows: List[Sequence[Any]] = []
    for r in m6_models_rows:
        m6_rows.append(
            [
                _tex_escape_text(r["model"]),
                _fmt_float(r["micro_degree_avg"]),
                r["stable_t"],
                _fmt_float(r["resolve_t"]),
                r["unresolved_micro_final"],
                r["max_micro_class_size_final"],
            ]
        )

    # Tabular: hypercube residual scan (only unresolved>0)
    res_csv = export_dir() / "hypercube_residual_scan_m3_to_m18.csv"
    res_rows = _read_csv(res_csv)
    res_rows2 = [r for r in res_rows if int(r["unresolved_micro_final"]) > 0]
    res_tab_rows: List[Sequence[Any]] = []
    for r in res_rows2:
        res_tab_rows.append(
            [
                r["m"],
                _fmt_float(r["stable_t"]),
                _fmt_float(r["resolve_t"]),
                r["unresolved_micro_final"],
                r["max_micro_class_size_final"],
            ]
        )

    # Tabular: dimension scan (show m=6 and m=9, all d)
    dim_csv = export_dir() / "dim_scan_m6_m9_m12_m15.csv"
    dim_rows = _read_csv(dim_csv)
    dim_rows2 = [r for r in dim_rows if r["m"] in ("6", "9")]
    dim_tab_rows: List[Sequence[Any]] = []
    for r in dim_rows2:
        dim_tab_rows.append(
            [
                r["m"],
                r["d"],
                _tex_escape_text(r["splits"]),
                _fmt_float(r["stable_t"]),
                _fmt_float(r["resolve_t"]),
            ]
        )

    script_path = Path(__file__).resolve()
    params: Dict[str, Any] = {"version": 1}
    required = [
        *(f"sections/generated/{f.out_tex}" for f in figs),
        "sections/generated/tab_m6_models_compare.tex",
        "sections/generated/tab_hypercube_residual_unresolved_only.tex",
        "sections/generated/tab_dim_scan_m6_m9.tex",
    ]
    run = prepare_run(
        experiment="generated_tex",
        params=params,
        script_path=script_path,
        required_files=["manifest.json"],
        force=args.force,
        extra_fingerprint={
            "inputs": {
                "hypercube_residual_scan_m3_to_m18.csv": (export_dir() / "hypercube_residual_scan_m3_to_m18.csv").stat().st_mtime,
                "dim_scan_m6_m9_m12_m15.csv": (export_dir() / "dim_scan_m6_m9_m12_m15.csv").stat().st_mtime,
                "m6_wl1_hilbert_vs_bitsplit_vs_hypercube.csv": (export_dir() / "m6_wl1_hilbert_vs_bitsplit_vs_hypercube.csv").stat().st_mtime,
            }
        },
    )

    # We always regenerate fragments (cheap) unless cached+manifest exists and force not set.
    # prepare_run already gives a deterministic run_dir; we also mirror files into sections/generated.

    # Write figure fragments
    out_rel_paths: List[str] = []
    for f in figs:
        rel = f"sections/generated/{f.out_tex}"
        out_path = run.run_dir / f.out_tex
        write_lines_as_fragment(out_path, _figure_fragment(f))
        write_lines_as_fragment(gen / f.out_tex, _figure_fragment(f))
        out_rel_paths.append(f.out_tex)

    # Write table fragments
    write_tabular_fragment(
        run.run_dir / "tab_m6_models_compare.tex",
        column_spec="lrrrrr",
        header=["model", "deg", "$t_{\\mathrm{stable}}$", "$t_{\\mathrm{resolve}}$", "$u$", "$s_{\\max}$"],
        rows=m6_rows,
        booktabs=True,
    )
    write_tabular_fragment(
        gen / "tab_m6_models_compare.tex",
        column_spec="lrrrrr",
        header=["model", "deg", "$t_{\\mathrm{stable}}$", "$t_{\\mathrm{resolve}}$", "$u$", "$s_{\\max}$"],
        rows=m6_rows,
        booktabs=True,
    )
    out_rel_paths.append("tab_m6_models_compare.tex")

    write_tabular_fragment(
        run.run_dir / "tab_hypercube_residual_unresolved_only.tex",
        column_spec="rrrrr",
        header=["$m$", "$t_{\\mathrm{stable}}$", "$t_{\\mathrm{resolve}}$", "$u$", "$s_{\\max}$"],
        rows=res_tab_rows,
        booktabs=True,
    )
    write_tabular_fragment(
        gen / "tab_hypercube_residual_unresolved_only.tex",
        column_spec="rrrrr",
        header=["$m$", "$t_{\\mathrm{stable}}$", "$t_{\\mathrm{resolve}}$", "$u$", "$s_{\\max}$"],
        rows=res_tab_rows,
        booktabs=True,
    )
    out_rel_paths.append("tab_hypercube_residual_unresolved_only.tex")

    write_tabular_fragment(
        run.run_dir / "tab_dim_scan_m6_m9.tex",
        column_spec="rrlrr",
        header=["$m$", "$d$", "splits", "$t_{\\mathrm{stable}}$", "$t_{\\mathrm{resolve}}$"],
        rows=dim_tab_rows,
        booktabs=True,
    )
    write_tabular_fragment(
        gen / "tab_dim_scan_m6_m9.tex",
        column_spec="rrlrr",
        header=["$m$", "$d$", "splits", "$t_{\\mathrm{stable}}$", "$t_{\\mathrm{resolve}}$"],
        rows=dim_tab_rows,
        booktabs=True,
    )
    out_rel_paths.append("tab_dim_scan_m6_m9.tex")

    manifest = build_base_manifest("generated_tex", run.run_id, params, script_path)
    manifest = add_output_hashes(manifest, run.run_dir, out_rel_paths)
    write_manifest(run.run_dir, manifest)

    # Validate expected generated files exist
    for rel in required:
        p = paper_root() / rel
        if not p.is_file() or p.stat().st_size == 0:
            raise SystemExit(f"[exp_generated_tex] missing/empty: {p}")

    print("[exp_generated_tex] done", flush=True)


if __name__ == "__main__":
    main()

