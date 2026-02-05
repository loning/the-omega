#!/usr/bin/env python3
"""
One-click reproduction entry point for this paper.

Caching:
  - This runner skips expensive scripts if the LaTeX-consumed outputs already
    exist under sections/generated/.
  - Use --force to recompute everything.

Paper asset policy:
  - All paper-referenced stable images must live under sections/generated/assets/.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from common_paths import generated_assets_dir, generated_dir


def _run(script: str, args: list[str]) -> None:
    cmd = [sys.executable, str(Path(__file__).resolve().parent / script), *args]
    print(f"[run_all] running: {' '.join(cmd)}", flush=True)
    subprocess.check_call(cmd)


def _have_all(paths: list[Path]) -> bool:
    return all(p.is_file() for p in paths)


def _sync_legacy_exports(force: bool) -> None:
    """
    Migration helper:
      - old stable export dir: artifacts/export/
      - new stable export dir: sections/generated/assets/
    Copy *.png if missing (or force=True).
    """
    root = Path(__file__).resolve().parents[1]
    old = root / "artifacts" / "export"
    new = generated_assets_dir()
    new.mkdir(parents=True, exist_ok=True)
    if not old.is_dir():
        return
    # Only keep assets that the paper actually references.
    needed = {
        "emergence_space_holonomy_rate.png",
        "emergence_space_holonomy_compare.png",
        "emergence_space_holonomy_rate_dynamic_m.png",
        "emergence_space_holonomy_induced_dynamic_m_compare.png",
    }
    for src in old.glob("*.png"):
        if src.name not in needed:
            continue
        dst = new / src.name
        if (not dst.is_file()) or force:
            shutil.copyfile(src, dst)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="Recompute everything (ignore caches).")
    args = ap.parse_args()

    force = bool(args.force)

    # Truncation families to run for truncation-dependent experiments.
    truncations = ["zeck_window", "dirac_dyadic"]

    # Ensure LaTeX-referenced assets live under sections/generated/assets/.
    _sync_legacy_exports(force=force)

    # Fixed reproduction configuration (paper defaults)
    seed = 0
    m_max = 16
    fiber_m = 16
    loop_m = 12
    loop_l = 6
    fourier_ms = "12,14,16,18,20,22,24,26"
    fourier_topk = 10
    scale_m_from = 12
    scale_m_to = 6
    scale_seeds = "0,1,2,3,4,5,6,7"
    blockcmp_seeds = "0,1,2,3,4,5,6,7"

    dyn_m = 10
    dyn_steps = 80
    dyn_threshold = 0.50
    dyn_beta = 6.0
    dyn_coupling = 1.0
    dyn_noise = 0.02
    dyn_defect_rate = 0.006
    dyn_r_diffusion = 0.25

    cap_ms = "6,9,12,15"
    cap_d_max = 4

    want_counts = [generated_dir() / "counts_check.tex"]
    if force or (not _have_all(want_counts)):
        _run("exp_counts_check.py", ["--m-max", str(m_max), *([] if not force else ["--force"])])
    else:
        print("[run_all] cached: exp_counts_check.py", flush=True)

    # Fiber spectrum depends on truncation: run for all truncations, then write a compare fragment.
    fiber_tex = [generated_dir() / f"fiber_entropy_summary_{t}.tex" for t in truncations]
    fiber_json = [generated_dir() / f"fiber_entropy_summary_{t}.json" for t in truncations]
    want_fiber = fiber_tex + fiber_json
    if force or (not _have_all(want_fiber)):
        for t in truncations:
            _run(
                "exp_fiber_spectrum.py",
                ["--m", str(fiber_m), "--truncation", t, *([] if not force else ["--force"])],
            )
    else:
        print("[run_all] cached: exp_fiber_spectrum.py (all truncations)", flush=True)

    # Build a compact comparison table for fiber entropy/residual stats.
    fiber_compare = generated_dir() / "fiber_entropy_summary_compare.tex"
    def _tt(s: str) -> str:
        # Minimal LaTeX escaping for \texttt{...}
        return str(s).replace("\\", r"\textbackslash{}").replace("_", r"\_")

    rows = []
    m0 = None
    for t in truncations:
        p = generated_dir() / f"fiber_entropy_summary_{t}.json"
        data = json.loads(p.read_text(encoding="utf-8"))
        stats = data.get("stats", {})
        m0 = int(data.get("params", {}).get("m", fiber_m))
        rows.append(
            (
                t,
                float(stats.get("H_X", 0.0)),
                float(stats.get("H_cond", 0.0)),
                float(stats.get("H_U", 0.0)),
                float(stats.get("H_U_given_X", 0.0)),
                float(stats.get("u_support_mean_px", 0.0)),
            )
        )
    lines = []
    lines.append(r"\paragraph{第一层纤维谱：截断族对照（自动生成）}")
    lines.append(r"\AuditTag 本片段由 \texttt{scripts/run\_all.py} 汇总生成。$U_m$ 表示截断协议输出的时间残差标签。")
    lines.append(r"\begin{center}")
    lines.append(r"\small")
    lines.append(r"\begin{tabular}{l r r r r r}")
    lines.append(r"\toprule")
    lines.append(r"truncation & $H(X_m)$ & $H(\Omega_m\mid X_m)$ & $H(U_m)$ & $H(U_m\mid X_m)$ & $\mathbb{E}[\#\mathrm{supp}(U_m\mid x)]$\\")
    lines.append(r"\midrule")
    for t, hx, hcond, hu, hugx, usupp in rows:
        lines.append(rf"\texttt{{{_tt(t)}}} & {hx:.6f} & {hcond:.6f} & {hu:.6f} & {hugx:.6f} & {usupp:.4f}\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{center}")
    fiber_compare.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Fold collision moment Fourier scan (no Omega_m enumeration).
    want_fourier = [
        generated_dir() / "fold_collision_fourier_scan_summary.tex",
        generated_dir() / "fold_collision_fourier_scan_summary.json",
    ]
    if force or (not _have_all(want_fourier)):
        _run(
            "exp_fold_collision_fourier_scan.py",
            ["--ms", str(fourier_ms), "--topk", str(fourier_topk), *([] if not force else ["--force"])],
        )
    else:
        print("[run_all] cached: exp_fold_collision_fourier_scan.py", flush=True)

    # Hilbert recursive scale truncation (m_from -> m_to), comparing 2D/3D/2D∧3D constraint families.
    want_scale = [generated_dir() / f"hilbert_scale_truncation_m{scale_m_from}_to_m{scale_m_to}_compare.tex"]
    if force or (not _have_all(want_scale)):
        _run(
            "exp_hilbert_scale_truncation.py",
            [
                "--m-from",
                str(scale_m_from),
                "--m-to",
                str(scale_m_to),
                "--seeds",
                str(scale_seeds),
                *([] if not force else ["--force"]),
            ],
        )
    else:
        print("[run_all] cached: exp_hilbert_scale_truncation.py", flush=True)

    # Hilbert partition locality sanity check (value-free): compare 1D/2D/3D partitions for adjacency retention.
    want_partloc = [generated_dir() / f"hilbert_partition_locality_m{scale_m_from}_to_m{scale_m_to}.tex"]
    if force or (not _have_all(want_partloc)):
        _run(
            "exp_hilbert_partition_locality.py",
            ["--m-from", str(scale_m_from), "--m-to", str(scale_m_to), *([] if not force else ["--force"])],
        )
    else:
        print("[run_all] cached: exp_hilbert_partition_locality.py", flush=True)

    # Hilbert block-level compression compare (data-driven): compare several Agg rules under 2D vs 3D layouts.
    want_blockcmp = [generated_dir() / f"hilbert_block_compress_compare_m{scale_m_from}_to_m{scale_m_to}.tex"]
    if force or (not _have_all(want_blockcmp)):
        _run(
            "exp_hilbert_block_compress_compare.py",
            [
                "--m-from",
                str(scale_m_from),
                "--m-to",
                str(scale_m_to),
                "--seeds",
                blockcmp_seeds,
                *([] if not force else ["--force"]),
            ],
        )
    else:
        print("[run_all] cached: exp_hilbert_block_compress_compare.py", flush=True)

    want_holo = [generated_dir() / "holonomy_interface_vs_bulk.tex"]
    if force or (not _have_all(want_holo)):
        _run(
            "exp_holonomy_spectrum.py",
            ["--m", str(loop_m), "--ell", str(loop_l), "--seed", str(seed), *([] if not force else ["--force"])],
        )
    else:
        print("[run_all] cached: exp_holonomy_spectrum.py", flush=True)

    want_space = [
        generated_dir() / "emergence_space_holonomy_summary.tex",
        generated_assets_dir() / "emergence_space_holonomy_rate.png",
    ]
    if force or (not _have_all(want_space)):
        _run(
            "exp_emergence_space_holonomy.py",
            [
                "--m",
                str(dyn_m),
                "--steps",
                str(dyn_steps),
                "--threshold",
                str(dyn_threshold),
                "--beta",
                str(dyn_beta),
                "--coupling",
                str(dyn_coupling),
                "--noise",
                str(dyn_noise),
                "--defect-rate",
                str(dyn_defect_rate),
                "--r-diffusion",
                str(dyn_r_diffusion),
                "--seed",
                str(seed),
                *([] if not force else ["--force"]),
            ],
        )
    else:
        print("[run_all] cached: exp_emergence_space_holonomy.py", flush=True)

    # Dynamic resolution (per-site m) variant for the same experiment.
    want_space_dyn = [
        generated_dir() / "emergence_space_holonomy_dynamic_m_summary.tex",
        generated_assets_dir() / "emergence_space_holonomy_rate_dynamic_m.png",
        generated_assets_dir() / "emergence_space_holonomy_error_terms_dynamic_m.png",
    ]
    if force or (not _have_all(want_space_dyn)):
        _run(
            "exp_emergence_space_holonomy.py",
            [
                "--dynamic-m",
                "--m-min",
                "6",
                "--m-max",
                "14",
                "--delta-m",
                "2",
                "--m-update-every",
                "4",
                "--m",
                str(dyn_m),
                "--steps",
                str(dyn_steps),
                "--threshold",
                str(dyn_threshold),
                "--beta",
                str(dyn_beta),
                "--coupling",
                str(dyn_coupling),
                "--noise",
                str(dyn_noise),
                "--defect-rate",
                str(dyn_defect_rate),
                "--r-diffusion",
                str(dyn_r_diffusion),
                "--seed",
                str(seed),
                *([] if not force else ["--force"]),
            ],
        )
    else:
        print("[run_all] cached: exp_emergence_space_holonomy.py (dynamic m)", flush=True)

    want_space_induced = [
        generated_dir() / "emergence_space_holonomy_induced_summary.tex",
        generated_assets_dir() / "emergence_space_holonomy_compare.png",
    ]
    if force or (not _have_all(want_space_induced)):
        _run(
            "exp_emergence_space_holonomy_induced.py",
            [
                "--m",
                str(dyn_m),
                "--steps",
                str(dyn_steps),
                "--threshold",
                str(dyn_threshold),
                "--beta",
                str(dyn_beta),
                "--coupling",
                str(dyn_coupling),
                "--noise",
                str(dyn_noise),
                "--defect-rate",
                str(dyn_defect_rate),
                "--r-diffusion",
                str(dyn_r_diffusion),
                "--seed",
                str(seed),
                *([] if not force else ["--force"]),
            ],
        )
    else:
        print("[run_all] cached: exp_emergence_space_holonomy_induced.py", flush=True)

    # Dynamic resolution (per-site m) variant for induced-connection comparison.
    want_space_induced_dyn = [
        generated_dir() / "emergence_space_holonomy_induced_dynamic_m_summary.tex",
        generated_assets_dir() / "emergence_space_holonomy_induced_dynamic_m_compare.png",
        generated_assets_dir() / "emergence_space_holonomy_induced_error_terms_dynamic_m.png",
    ]
    if force or (not _have_all(want_space_induced_dyn)):
        _run(
            "exp_emergence_space_holonomy_induced.py",
            [
                "--dynamic-m",
                "--m-min",
                "6",
                "--m-max",
                "14",
                "--delta-m",
                "2",
                "--m-update-every",
                "4",
                "--m",
                str(dyn_m),
                "--steps",
                str(dyn_steps),
                "--threshold",
                str(dyn_threshold),
                "--beta",
                str(dyn_beta),
                "--coupling",
                str(dyn_coupling),
                "--noise",
                str(dyn_noise),
                "--defect-rate",
                str(dyn_defect_rate),
                "--r-diffusion",
                str(dyn_r_diffusion),
                "--seed",
                str(seed),
                *([] if not force else ["--force"]),
            ],
        )
    else:
        print("[run_all] cached: exp_emergence_space_holonomy_induced.py (dynamic m)", flush=True)

    # CAP display scan depends on truncation: run for all truncations, then write a compare fragment.
    cap_want = []
    for t in truncations:
        cap_want.extend(
            [
                generated_dir() / f"cap_display_dim_scan_table_{t}.tex",
                generated_dir() / f"cap_display_dim_scan_summary_{t}.tex",
                generated_dir() / f"fig_cap_display_resolve_vs_dim_{t}.tex",
                generated_dir() / f"fig_cap_display_unresolved_vs_dim_{t}.tex",
                generated_dir() / f"cap_display_dim_key_table_{t}.tex",
                generated_assets_dir() / f"cap_display_resolve_vs_dim_{t}.png",
                generated_assets_dir() / f"cap_display_unresolved_vs_dim_{t}.png",
            ]
        )
    cap_compare = generated_dir() / "cap_display_dim_scan_compare.tex"
    want_cap_dim = cap_want + [cap_compare]
    if force or (not _have_all(cap_want)):
        for t in truncations:
            _run(
                "exp_cap_display_dim_scan.py",
                [
                    "--ms",
                    str(cap_ms),
                    "--d-max",
                    str(cap_d_max),
                    "--max-iter",
                    "200",
                    "--truncation",
                    t,
                    *([] if not force else ["--force"]),
                ],
            )
    else:
        print("[run_all] cached: exp_cap_display_dim_scan.py (all truncations)", flush=True)

    # Compare fragment (inputs per-truncation outputs).
    cap_lines = []
    cap_lines.append(r"\paragraph{显示维数扫描：截断族对照（自动生成）}")
    cap_lines.append(r"\AuditTag 本片段由 \texttt{scripts/run\_all.py} 汇总生成。每个截断族对应一组闭包图与 WL1 指标。")
    for t in truncations:
        cap_lines.append(rf"\subparagraph{{截断族 \texttt{{{_tt(t)}}}}}")
        cap_lines.append(rf"\input{{sections/generated/cap_display_dim_scan_summary_{t}}}")
        cap_lines.append(r"\begin{center}\scriptsize")
        cap_lines.append(rf"\input{{sections/generated/cap_display_dim_key_table_{t}}}")
        cap_lines.append(r"\end{center}")
        cap_lines.append(rf"\input{{sections/generated/fig_cap_display_resolve_vs_dim_{t}}}")
        cap_lines.append(rf"\input{{sections/generated/fig_cap_display_unresolved_vs_dim_{t}}}")
    cap_compare.write_text("\n".join(cap_lines) + "\n", encoding="utf-8")

    _sync_legacy_exports(force=False)

    print("[run_all] all experiments completed.", flush=True)


if __name__ == "__main__":
    main()

