#!/usr/bin/env python3
"""Scan p×seed and summarize alpha/D with uncertainty (cached).

Artifacts:
  artifacts/hpa_ca_scan_fractal_psd/<run_id>/
    - rows.csv
    - summary.csv
    - manifest.json

Generated LaTeX:
  sections/generated/hpa_ca_scan_fractal_psd_summary.tex
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir
from common_tex_pylatex import write_tabular_fragment
from hpa_ca_lossless import estimate_boxcount_dimension, estimate_psd_slope, evolve


def parse_float_list(s: str) -> List[float]:
    if not s.strip():
        return []
    out: List[float] = []
    for x in s.split(","):
        x = x.strip()
        if not x:
            continue
        out.append(float(x))
    return out


def parse_int_list(s: str) -> List[int]:
    if not s.strip():
        return []
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def mean_ci95(values: Sequence[float]) -> Tuple[float, float, float, int]:
    arr = np.asarray(list(values), dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    n = int(arr.shape[0])
    if n == 0:
        return float("nan"), float("nan"), float("nan"), 0
    mu = float(np.mean(arr))
    if n == 1:
        return mu, float("nan"), float("nan"), 1
    sd = float(np.std(arr, ddof=1))
    se = sd / float(np.sqrt(n))
    half = 1.96 * se
    return mu, mu - half, mu + half, n


@dataclass(frozen=True)
class Row:
    p: float
    seed: int
    final_rho: float
    alpha: float
    alpha_se: float
    alpha_nfit: int
    alpha_r2: float
    D: float
    D_se: float
    D_nfit: int
    D_r2: float


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, default=300)
    ap.add_argument("--T", type=int, default=200)
    ap.add_argument("--ps", type=str, default="0.1,0.3,0.5,0.7,0.9")
    ap.add_argument("--seeds", type=str, default="1,2,3,4,5")
    ap.add_argument("--burn_in", type=int, default=0, help="burn-in time steps for box-counting image")
    ap.add_argument("--f_min", type=float, default=0.0, help="fit band min frequency (0=auto)")
    ap.add_argument("--f_max", type=float, default=0.0, help="fit band max frequency (0=default 0.25)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.L % 6 != 0:
        raise SystemExit("L must be a multiple of 6")
    if args.T < 16:
        raise SystemExit("T must be >= 16")

    ps = parse_float_list(args.ps)
    seeds = parse_int_list(args.seeds)
    if not ps:
        raise SystemExit("No ps provided")
    if not seeds:
        raise SystemExit("No seeds provided")

    script_path = Path(__file__).resolve()
    params: Dict[str, object] = {
        "L": int(args.L),
        "T": int(args.T),
        "ps": ps,
        "seeds": seeds,
        "burn_in": int(args.burn_in),
        "f_min": float(args.f_min),
        "f_max": float(args.f_max),
    }

    required = ["rows.csv", "summary.csv"]
    run = prepare_run(
        "hpa_ca_scan_fractal_psd",
        params=params,
        script_path=script_path,
        required_files=required,
        force=bool(args.force),
    )

    if not run.cached:
        rows: List[Row] = []
        for i_p, p in enumerate(ps):
            for i_s, sd in enumerate(seeds):
                idx = i_p * len(seeds) + i_s + 1
                total = len(ps) * len(seeds)
                print(f"[scan] {idx}/{total} p={p} seed={sd} start", flush=True)

                res = evolve(L=args.L, T=args.T, seed=sd, p=p)
                alpha, alpha_se, alpha_nfit, alpha_r2 = estimate_psd_slope(
                    res.density, f_min=float(args.f_min), f_max=float(args.f_max)
                )

                st = res.states[int(max(0, args.burn_in)) :, :].astype(np.uint8)
                img = st
                max_pow = int(np.log2(min(img.shape)))
                sizes = [2**k for k in range(1, max_pow - 1)]
                D, D_se, D_nfit, D_r2, _eps_all, _Ns_all = estimate_boxcount_dimension(img, sizes)

                rows.append(
                    Row(
                        p=float(p),
                        seed=int(sd),
                        final_rho=float(res.density[-1]),
                        alpha=float(alpha),
                        alpha_se=float(alpha_se),
                        alpha_nfit=int(alpha_nfit),
                        alpha_r2=float(alpha_r2),
                        D=float(D),
                        D_se=float(D_se),
                        D_nfit=int(D_nfit),
                        D_r2=float(D_r2),
                    )
                )
                print(
                    f"[scan] p={p} seed={sd} done rho={float(res.density[-1]):.6f} alpha={float(alpha):.6f} D={float(D):.6f}",
                    flush=True,
                )

        # Write rows.csv
        with open(run.run_dir / "rows.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["p", "seed", "final_rho", "alpha", "alpha_se", "alpha_nfit", "alpha_r2", "D", "D_se", "D_nfit", "D_r2"])
            for r in rows:
                w.writerow(
                    [
                        f"{r.p:.6f}",
                        r.seed,
                        f"{r.final_rho:.6f}",
                        f"{r.alpha:.6f}",
                        f"{r.alpha_se:.6f}",
                        r.alpha_nfit,
                        f"{r.alpha_r2:.6f}",
                        f"{r.D:.6f}",
                        f"{r.D_se:.6f}",
                        r.D_nfit,
                        f"{r.D_r2:.6f}",
                    ]
                )

        # Summarize per p
        summary_rows: List[List[str]] = []
        with open(run.run_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["p", "n", "rho_mean", "rho_ci_lo", "rho_ci_hi", "alpha_mean", "alpha_ci_lo", "alpha_ci_hi", "D_mean", "D_ci_lo", "D_ci_hi"])
            for p in ps:
                rr = [r for r in rows if abs(r.p - float(p)) < 1e-12]
                rho_mu, rho_lo, rho_hi, n = mean_ci95([r.final_rho for r in rr])
                a_mu, a_lo, a_hi, _n2 = mean_ci95([r.alpha for r in rr])
                d_mu, d_lo, d_hi, _n3 = mean_ci95([r.D for r in rr])
                w.writerow(
                    [
                        f"{float(p):.6f}",
                        n,
                        f"{rho_mu:.6f}",
                        f"{rho_lo:.6f}",
                        f"{rho_hi:.6f}",
                        f"{a_mu:.6f}",
                        f"{a_lo:.6f}",
                        f"{a_hi:.6f}",
                        f"{d_mu:.6f}",
                        f"{d_lo:.6f}",
                        f"{d_hi:.6f}",
                    ]
                )
                summary_rows.append(
                    [
                        f"{float(p):.2f}",
                        str(n),
                        f"{rho_mu:.4f}",
                        f"[{rho_lo:.4f},{rho_hi:.4f}]",
                        f"{a_mu:.3f}",
                        f"[{a_lo:.3f},{a_hi:.3f}]",
                        f"{d_mu:.3f}",
                        f"[{d_lo:.3f},{d_hi:.3f}]",
                    ]
                )

        manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
        manifest = add_output_hashes(manifest, run.run_dir, rel_paths=required)
        write_manifest(run.run_dir, manifest)

    # Emit LaTeX from summary.csv
    summary_rows: List[List[str]] = []
    with open(run.run_dir / "summary.csv", "r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        _hdr = next(r)
        for ln in r:
            # columns: p, n, rho_mu, rho_lo, rho_hi, a_mu, a_lo, a_hi, d_mu, d_lo, d_hi
            summary_rows.append(
                [
                    f"{float(ln[0]):.2f}",
                    ln[1],
                    f"{float(ln[2]):.4f}",
                    f"[{float(ln[3]):.4f},{float(ln[4]):.4f}]",
                    f"{float(ln[5]):.3f}",
                    f"[{float(ln[6]):.3f},{float(ln[7]):.3f}]",
                    f"{float(ln[8]):.3f}",
                    f"[{float(ln[9]):.3f},{float(ln[10]):.3f}]",
                ]
            )

    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)
    write_tabular_fragment(
        gen / "hpa_ca_scan_fractal_psd_summary.tex",
        column_spec="r r r l r l r l",
        header=[
            r"$p$",
            r"$n$",
            r"$\bar\rho$",
            r"$95\%\ \mathrm{CI}$",
            r"$\bar\alpha$",
            r"$95\%\ \mathrm{CI}$",
            r"$\bar D$",
            r"$95\%\ \mathrm{CI}$",
        ],
        rows=summary_rows,
        booktabs=True,
    )


if __name__ == "__main__":
    main()

