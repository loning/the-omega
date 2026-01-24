#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resource-cap-limited unfolding (upward) process on Zeckendorf uplift (time fiber).

This experiment instantiates the "complete conservative system" viewpoint:
- Space = macro stable observation y in golden-mean language Y_m (size F_{m+2})
- Time = explicit uplift tail bits (Zeckendorf digits beyond window)
- Observer unfolding process = inverse tail step (branching)
- Resource cap W = beam width cap (max concurrent branches)

We fix the macro observation to y = 0^m (maximal folding degeneracy) and start from
the "void" tail t=0 at depth 0. We then run an unfolding process that inverts the
tail shift (Tail^{-1}) for a finite number of steps and keeps at most W branches.

Outputs
-------
- artifacts/export/zeckendorf_energy_beam_uplift.csv
- artifacts/export/zeckendorf_energy_beam_uplift_curve.png
- sections/generated/tab_zeckendorf_energy_beam_uplift.tex
- sections/generated/fig_zeckendorf_energy_beam_uplift_curve.tex
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import export_dir, generated_dir
from common_tex_pylatex import write_lines_as_fragment, write_tabular_fragment
from common_zeckendorf_uplift import (
    FoldDomain,
    build_fold_domain,
    fold_f_m,
    micro_N_from_macro_and_tail,
    tail_inverse_step_candidates,
    tail_length,
)


@dataclass(frozen=True)
class BeamStep:
    depth: int
    n_candidates: int
    truncated: int
    min_N: int
    max_N: int


def _beam_upward_search(
    m: int,
    W: int,
    depth_max: int,
    macro_w: int,
    domain: FoldDomain,
) -> List[BeamStep]:
    # Candidates are tail-words (int).
    L = int(domain.L)
    tails: List[int] = [0]
    steps: List[BeamStep] = []

    def score(t: int) -> int:
        # Deterministic score: smaller micro integer N first.
        N = micro_N_from_macro_and_tail(macro_w=macro_w, tail=t, m=m)
        return int(N)

    for d in range(0, depth_max + 1):
        Ns = [score(t) for t in tails]
        steps.append(
            BeamStep(
                depth=d,
                n_candidates=len(tails),
                truncated=0,
                min_N=int(min(Ns)) if Ns else -1,
                max_N=int(max(Ns)) if Ns else -1,
            )
        )
        if d == depth_max:
            break

        # Unfold (upward): invert the tail shift.
        nxt: List[int] = []
        seen = set()
        for t in tails:
            for tp in tail_inverse_step_candidates(t, L=L):
                if tp in seen:
                    continue
                # Sanity: must still map to the fixed macro.
                Np = micro_N_from_macro_and_tail(macro_w=macro_w, tail=tp, m=m)
                if not (0 <= Np < (1 << m)):
                    continue
                if int(fold_f_m(Np, m)) != int(macro_w):
                    continue
                seen.add(tp)
                nxt.append(tp)

        # Apply resource cap by score.
        if W > 0 and len(nxt) > W:
            nxt.sort(key=score)
            nxt = nxt[:W]
            steps[-1] = BeamStep(
                depth=steps[-1].depth,
                n_candidates=steps[-1].n_candidates,
                truncated=1,
                min_N=steps[-1].min_N,
                max_N=steps[-1].max_N,
            )
        tails = nxt

    return steps


def _ensure_dirs() -> None:
    generated_dir().mkdir(parents=True, exist_ok=True)
    export_dir().mkdir(parents=True, exist_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", type=str, default="6,9,12,15", help="comma-separated m values")
    ap.add_argument("--Es", type=str, default="", help="(deprecated) comma-separated energy values; use --Ws")
    ap.add_argument("--Ws", type=str, default="1,2,4,8,16,32,64", help="comma-separated resource caps W (beam width cap)")
    ap.add_argument("--depth_max", type=int, default=-1, help="max unfolding depth (default: tail length L(m))")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    ms = [int(x.strip()) for x in str(args.ms).split(",") if x.strip()]
    Ws_arg = str(args.Ws).strip() if str(args.Ws).strip() else str(args.Es).strip()
    Ws = [int(x.strip()) for x in Ws_arg.split(",") if x.strip()]
    if not ms or not Ws:
        raise SystemExit("Empty ms/Ws")

    params: Dict[str, object] = {"ms": ms, "Ws": Ws, "depth_max": int(args.depth_max)}

    out_csv = "zeckendorf_energy_beam_uplift.csv"
    out_png = "zeckendorf_energy_beam_uplift_curve.png"
    out_tab = "tab_zeckendorf_energy_beam_uplift.tex"
    out_fig = "fig_zeckendorf_energy_beam_uplift_curve.tex"

    script_path = Path(__file__).resolve()
    run = prepare_run(
        experiment="zeckendorf_energy_beam_uplift",
        params=params,
        script_path=script_path,
        required_files=[out_csv, out_png, out_tab, out_fig],
        force=bool(args.force),
        extra_fingerprint=None,
    )

    _ensure_dirs()

    if run.cached:
        print(f"[exp_zeckendorf_energy_beam_uplift] cached: {run.run_dir.name}", flush=True)
        copy_atomic(run.run_dir / out_tab, generated_dir() / out_tab)
        copy_atomic(run.run_dir / out_fig, generated_dir() / out_fig)
        copy_atomic(run.run_dir / out_csv, export_dir() / out_csv)
        copy_atomic(run.run_dir / out_png, export_dir() / out_png)
        return

    rows: List[Dict[str, object]] = []

    # Curves: for each (m,W) store candidate count vs depth.
    curves: Dict[Tuple[int, int], List[int]] = {}

    for m in ms:
        dom = build_fold_domain(m)
        macro_w = 0  # y = 0^m
        Lm = int(tail_length(m))
        depth_max = Lm if int(args.depth_max) < 0 else int(args.depth_max)
        depth_max = min(depth_max, Lm)

        for W in Ws:
            steps = _beam_upward_search(m=m, W=int(W), depth_max=depth_max, macro_w=macro_w, domain=dom)
            counts = [st.n_candidates for st in steps]
            curves[(m, int(W))] = counts

            final = steps[-1]
            rows.append(
                {
                    "m": m,
                    "L_tail": int(dom.L),
                    "depth_max": int(depth_max),
                    "W": int(W),
                    "B0": int(steps[0].n_candidates),
                    "B_final": int(final.n_candidates),
                    "truncated": int(any(st.truncated for st in steps)),
                    "min_N_final": int(final.min_N),
                    "max_N_final": int(final.max_N),
                }
            )

    # Write CSV
    out_csv_path = run.run_dir / out_csv
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with out_csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["m", "L_tail", "depth_max", "W", "B0", "B_final", "truncated", "min_N_final", "max_N_final"],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Plot: for each m, show curves for selected W values.
    out_png_path = run.run_dir / out_png
    plt.figure(figsize=(7.6, 4.4))
    for m in ms:
        for W in Ws:
            ys = curves[(m, int(W))]
            xs = list(range(len(ys)))
            plt.plot(xs, ys, linewidth=1.2, label=f"m={m},W={W}")
    plt.xlabel("unfold depth  d")
    plt.ylabel("branch count  B_d (after resource cap)")
    plt.title("Zeckendorf uplift: resource-cap-limited unfolding from y=0^m")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8, ncol=2)
    plt.tight_layout()
    plt.savefig(out_png_path, dpi=170)
    plt.close()

    # LaTeX figure fragment
    out_fig_path = run.run_dir / out_fig
    write_lines_as_fragment(
        out_fig_path,
        [
            r"\centering",
            rf"\includegraphics[width=0.92\linewidth]{{artifacts/export/{out_png}}}",
        ],
    )

    # Summary table (one row per m, select W=max to show unconstrained cap)
    # We also report the theoretical maximum |T_m| = F_{L+2} implicitly via B_final when W is large enough.
    tab_rows: List[List[str]] = []
    for m in ms:
        Lm = int(tail_length(m))
        # Use the largest W.
        Wmax = max(Ws)
        rec = next(r for r in rows if int(r["m"]) == m and int(r["W"]) == int(Wmax))
        tab_rows.append(
            [
                str(m),
                str(Lm),
                str(Wmax),
                str(rec["B_final"]),
                str(rec["truncated"]),
            ]
        )

    out_tab_path = run.run_dir / out_tab
    write_tabular_fragment(
        out_tab_path,
        column_spec="r r r r r",
        header=[
            r"$m$",
            r"\textbf{tail length $L(m)$}",
            r"\textbf{resource cap $W$}",
            r"\textbf{$B_{d_{\max}}$}",
            r"\textbf{truncated}",
        ],
        rows=tab_rows,
        booktabs=True,
    )

    # Manifest
    manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, [out_csv, out_png, out_tab, out_fig])
    write_manifest(run.run_dir, manifest)

    # Export/copy
    copy_atomic(out_tab_path, generated_dir() / out_tab)
    copy_atomic(out_fig_path, generated_dir() / out_fig)
    copy_atomic(out_csv_path, export_dir() / out_csv)
    copy_atomic(out_png_path, export_dir() / out_png)
    print("[exp_zeckendorf_energy_beam_uplift] done", flush=True)


if __name__ == "__main__":
    main()

