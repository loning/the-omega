#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""m=6 fiber size distribution and potential energy (64->21).

We enumerate all N in {0,...,63}, compute y = Fold_6(N), and count s_6(y)=|Fold_6^{-1}(y)|.
We then define the (state) potential energy as E_pot(y)=log2 s_6(y) (bits).

Outputs
-------
- artifacts/export/m6_fiber_potential_energy.csv
- artifacts/export/m6_fiber_potential_energy_hist.png
- sections/generated/tab_m6_fiber_potential_energy.tex
- sections/generated/fig_m6_fiber_potential_energy_hist.tex
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import export_dir, generated_dir
from common_tex_pylatex import write_lines_as_fragment, write_tabular_fragment
from common_zeckendorf_uplift import fib_upto, fold_f_m


def _bits(w: int, m: int) -> str:
    # low-to-high bits c1..cm, print high-to-low for readability
    return "".join("1" if (w >> i) & 1 else "0" for i in range(m - 1, -1, -1))


def _V_of_macro(w: int, m: int) -> int:
    # V(w)=sum_{k=1..m} w_k F_{k+1}; with low-to-high bits, w_k is bit (k-1)
    F = fib_upto(m + 2)  # [F1..F_{m+2}]
    out = 0
    for k in range(1, m + 1):
        if (w >> (k - 1)) & 1:
            out += F[k]  # weight F_{k+1} but F list is 1-indexed logically; F[1]=F1, so weight is F[k+1]? see common_zeckendorf_uplift
    return int(out)


@dataclass(frozen=True)
class Row:
    macro_bits: str
    V: int
    s: int
    E_pot_bits: float


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    m = 6
    params: Dict[str, object] = {"m": m}

    out_csv = "m6_fiber_potential_energy.csv"
    out_png = "m6_fiber_potential_energy_hist.png"
    out_tab = "tab_m6_fiber_potential_energy.tex"
    out_fig = "fig_m6_fiber_potential_energy_hist.tex"

    script_path = Path(__file__).resolve()
    run = prepare_run(
        experiment="m6_fiber_potential_energy",
        params=params,
        script_path=script_path,
        required_files=[out_csv, out_png, out_tab, out_fig],
        force=bool(args.force),
        extra_fingerprint=None,
    )

    generated_dir().mkdir(parents=True, exist_ok=True)
    export_dir().mkdir(parents=True, exist_ok=True)

    if run.cached:
        print(f"[exp_m6_fiber_potential_energy] cached: {run.run_dir.name}", flush=True)
        copy_atomic(run.run_dir / out_tab, generated_dir() / out_tab)
        copy_atomic(run.run_dir / out_fig, generated_dir() / out_fig)
        copy_atomic(run.run_dir / out_csv, export_dir() / out_csv)
        copy_atomic(run.run_dir / out_png, export_dir() / out_png)
        return

    # Count fibers by macro word.
    counts: Dict[int, int] = {}
    for N in range(1 << m):
        w = int(fold_f_m(N, m=m))
        counts[w] = counts.get(w, 0) + 1

    # Build per-macro rows.
    rows: List[Row] = []
    for w, s in sorted(counts.items()):
        macro_bits = _bits(w, m=m)
        V = _V_of_macro(w, m=m)
        Epot = math.log2(float(s))
        rows.append(Row(macro_bits=macro_bits, V=int(V), s=int(s), E_pot_bits=float(Epot)))

    # Summary histogram over s in {2,3,4}.
    hist: Dict[int, int] = {}
    for r in rows:
        hist[r.s] = hist.get(r.s, 0) + 1
    for s in sorted(hist.keys()):
        print(f"[exp_m6_fiber_potential_energy] s={s} count={hist[s]}", flush=True)

    # Write CSV.
    out_csv_path = run.run_dir / out_csv
    with out_csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["m", "y_bits", "V", "s", "E_pot_bits"])
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "m": m,
                    "y_bits": r.macro_bits,
                    "V": r.V,
                    "s": r.s,
                    "E_pot_bits": f"{r.E_pot_bits:.6f}",
                }
            )

    # Plot histogram.
    xs = sorted(hist.keys())
    ys = [hist[x] for x in xs]
    labels = [f"s={x}\nE_pot={math.log2(float(x)):.3f} bits" for x in xs]
    out_png_path = run.run_dir / out_png
    plt.figure(figsize=(6.2, 3.6))
    plt.bar(range(len(xs)), ys, color="#1976D2", alpha=0.9)
    plt.xticks(range(len(xs)), labels)
    plt.ylabel("number of macro states  |{y: s_6(y)=s}|")
    plt.title("m=6 (64->21): fiber size distribution and potential energy")
    plt.grid(True, axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(out_png_path, dpi=170)
    plt.close()

    # LaTeX figure fragment.
    out_fig_path = run.run_dir / out_fig
    write_lines_as_fragment(
        out_fig_path,
        [
            r"\centering",
            rf"\includegraphics[width=0.86\linewidth]{{artifacts/export/{out_png}}}",
        ],
    )

    # LaTeX table fragment (21 rows).
    tab_rows: List[List[str]] = []
    for r in rows:
        tab_rows.append([r.macro_bits, str(r.V), str(r.s), f"{r.E_pot_bits:.6f}"])

    out_tab_path = run.run_dir / out_tab
    write_tabular_fragment(
        out_tab_path,
        column_spec="l r r r",
        header=[r"\textbf{$y$ (bits)}", r"$V(y)$", r"$s_6(y)$", r"$\Energy_{\mathrm{pot}}(y)$"],
        rows=tab_rows,
        booktabs=True,
    )

    # Manifest.
    manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, [out_csv, out_png, out_tab, out_fig])
    write_manifest(run.run_dir, manifest)

    # Export/copy.
    copy_atomic(out_tab_path, generated_dir() / out_tab)
    copy_atomic(out_fig_path, generated_dir() / out_fig)
    copy_atomic(out_csv_path, export_dir() / out_csv)
    copy_atomic(out_png_path, export_dir() / out_png)
    print("[exp_m6_fiber_potential_energy] done", flush=True)


if __name__ == "__main__":
    main()

