#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the m=6 fold6 + Hilbert 2D/3D mapping table CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

from hilbertcurve.hilbertcurve import HilbertCurve

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import export_dir, paper_root
from common_zeckendorf import (
    bin_m_high_to_low_str,
    fib_zeckendorf_upto,
    fold_f_m,
    word_bits_high_to_low_str,
    word_bits_low_to_high_str,
    zeckendorf_digits_low_to_high,
)


def _V_of_word(w: int, m: int) -> int:
    F = fib_zeckendorf_upto(m)
    s = 0
    for i in range(m):
        if (w >> i) & 1:
            s += F[i]
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    m = 6
    out_name = "m6_fold6_hilbert2d3d_table.csv"
    script_path = Path(__file__).resolve()
    params = {"m": m}

    run = prepare_run(
        experiment="m6_fold6_hilbert_table",
        params=params,
        script_path=script_path,
        required_files=[out_name],
        force=args.force,
    )

    if run.cached:
        print(f"[exp_m6_fold6_hilbert_table] cached: {run.run_dir.name}", flush=True)
        copy_atomic(run.run_dir / out_name, export_dir() / out_name)
        return

    hc2 = HilbertCurve(p=3, n=2)  # 8x8
    hc3 = HilbertCurve(p=2, n=3)  # 4x4x4

    rows: List[Dict[str, object]] = []
    for N in range(1 << m):
        w = fold_f_m(N, m=m)  # int bits c1..c6
        fold_digits_low = word_bits_low_to_high_str(w, m=m)
        fold_w = word_bits_high_to_low_str(w, m=m)
        Vw = _V_of_word(w, m=m)
        delta = N - Vw

        zeck9 = zeckendorf_digits_low_to_high(N, max_k=9)
        tail = "".join(str(zeck9[i]) for i in range(6, 9))  # c7c8c9
        zeck9s = "".join(str(b) for b in zeck9)

        x2, y2 = [int(v) for v in hc2.point_from_distance(N)]
        x3, y3, z3 = [int(v) for v in hc3.point_from_distance(N)]

        rows.append(
            {
                "N": N,
                "bin6": bin_m_high_to_low_str(N, m=m),
                "fold6_w": fold_w,
                "fold6_digits_low_to_high": fold_digits_low,
                "V(w)": Vw,
                "delta": delta,
                "tail_c7c8c9": tail,
                "zeck_c1..c9_low_to_high": zeck9s,
                "hilbert2d_x": x2,
                "hilbert2d_y": y2,
                "hilbert3d_x": x3,
                "hilbert3d_y": y3,
                "hilbert3d_z": z3,
            }
        )

    out_csv = run.run_dir / out_name
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)

    manifest = build_base_manifest("m6_fold6_hilbert_table", run.run_id, params, script_path)
    manifest = add_output_hashes(manifest, run.run_dir, [out_name])
    write_manifest(run.run_dir, manifest)

    copy_atomic(out_csv, export_dir() / out_name)
    print("[exp_m6_fold6_hilbert_table] done", flush=True)


if __name__ == "__main__":
    main()

