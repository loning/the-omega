#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate dyadic counting artifacts (cached, reproducible).

Artifacts:
  artifacts/dyadic_counting/<run_id>/
    - dyadic_counting_m100_2000.csv
    - manifest.json

LaTeX fragments:
  sections/generated/dyadic_counting_summary.tex
  sections/generated/dyadic_counting_selected_table.tex
  sections/generated/dyadic_counting_stats_table.tex
"""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal, getcontext
from pathlib import Path
from typing import List

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir
from common_progress import Progress
from common_tex_pylatex import write_tabular_fragment
from pylatex import Command
from zeckendorf import V_m, count_leq_with_fixed_digit, fibs_up_to_index, fold_prefix, zeckendorf_digits


def _write_csv(path: Path, header: List[str], rows: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def _read_csv(path: Path) -> List[List[str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        return [row for row in r]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m_min", type=int, default=100)
    ap.add_argument("--m_max", type=int, default=2000)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    script_path = Path(__file__).resolve()
    params = {"m_min": args.m_min, "m_max": args.m_max}

    required = ["dyadic_counting_m100_2000.csv"]
    run = prepare_run("dyadic_counting", params=params, script_path=script_path, required_files=required, force=args.force)

    if not run.cached:
        # Decimal arithmetic to avoid float overflow/underflow at m ~ 2000.
        # Precision is chosen for stable bounded E_m-like quantities.
        getcontext().prec = 80

        fib = fibs_up_to_index(2 * args.m_max + 10)
        sqrt5 = Decimal(5).sqrt()
        phi = (Decimal(1) + sqrt5) / Decimal(2)
        p = Decimal(1) / (phi * phi + Decimal(1))

        rows: List[List[str]] = []
        prog = Progress("dyadic_counting", every_seconds=20.0)

        B = 0
        pow2 = Decimal(1)
        powphi = Decimal(1)
        for m in range(1, args.m_min):
            B = (B << 1) | 1
            pow2 *= Decimal(2)
            powphi *= phi

        for m in range(args.m_min, args.m_max + 1):
            B = (B << 1) | 1  # B_m = 2^m-1
            pow2 *= Decimal(2)
            powphi *= phi
            _, cB = zeckendorf_digits(B, fib)

            # bF = F_{m+1}
            bF = fib[m + 1]
            pm = fold_prefix(cB, m)
            vmax = V_m(pm, fib)
            bQ = vmax + 1
            split_side = 1 if (bQ > bF) else 0
            cm = cB[m] if m < len(cB) else 0

            # C1(m) = #{N <= B_m : c_m(N) = 1}
            C1 = count_leq_with_fixed_digit(cB, fixed_k=m, fixed_val=1)

            # Scaled error E_m = (C1 - p 2^m)/phi^m (Decimal).
            target = p * pow2
            Em = (Decimal(C1) - target) / powphi
            delta = (Decimal(bQ) / Decimal(bF)) - Decimal(1)

            rows.append(
                [
                    str(m),
                    str(C1),
                    str(B.bit_length()),
                    str(bF),
                    str(bQ),
                    str(split_side),
                    str(cm),
                    f"{delta:.16E}",
                    f"{Em:.16E}",
                ]
            )
            prog.tick(f"m={m}/{args.m_max}  C1={C1}  delta={delta:.3E}  E={Em:.3E}")

        _write_csv(
            run.run_dir / "dyadic_counting_m100_2000.csv",
            header=["m", "C1", "B_bitlen", "bF", "bQ", "split_side", "c_m(B_m)", "delta", "E_m"],
            rows=rows,
        )

        manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
        manifest = add_output_hashes(manifest, run.run_dir, rel_paths=required)
        write_manifest(run.run_dir, manifest)

    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)
    write_tabular_fragment(
        gen / "dyadic_counting_summary.tex",
        column_spec="ll",
        header=[r"\textbf{key}", r"\textbf{value}"],
        rows=[
            [r"experiment", Command("texttt", run.experiment)],
            [r"run\_id", Command("texttt", run.run_id)],
            [r"artifacts", Command("texttt", f"artifacts/{run.experiment}/{run.run_id}/".replace("_", r"\_"))],
        ],
        booktabs=True,
    )

    # Emit data tables (from artifacts) as TeX fragments.
    # Columns: m, C1, B_bitlen, bF, bQ, split_side, c_m(B_m), delta, E_m
    rows = _read_csv(run.run_dir / "dyadic_counting_m100_2000.csv")
    header = rows[0]
    data = rows[1:]
    idx = {name: i for i, name in enumerate(header)}

    want_m = {100, 200, 500, 1000, 1500, 2000}
    selected = [r for r in data if int(r[idx["m"]]) in want_m]

    def _brief_int(x: str) -> str:
        # Avoid overfull boxes: show prefix + digit length; full value lives in CSV artifact.
        pref = x[:12]
        return f"{pref}... ({len(x)}d)"

    write_tabular_fragment(
        gen / "dyadic_counting_selected_table.tex",
        column_spec="rlllrrll",
        header=[
            r"$m$",
            r"$C_1(m)$ (brief)",
            r"$b_F$ (brief)",
            r"$b_Q$ (brief)",
            r"\textbf{split}",
            r"$c_m(B_m)$",
            r"$\delta_m$",
            r"$E_m$",
        ],
        rows=[
            [
                r[idx["m"]],
                Command("texttt", _brief_int(r[idx["C1"]])),
                Command("texttt", _brief_int(r[idx["bF"]])),
                Command("texttt", _brief_int(r[idx["bQ"]])),
                r[idx["split_side"]],
                r[idx["c_m(B_m)"]],
                Command("texttt", r[idx["delta"]]),
                Command("texttt", r[idx["E_m"]]),
            ]
            for r in selected
        ],
        booktabs=True,
    )

    # Stats table for delta and E_m on the full range.
    deltas = [Decimal(r[idx["delta"]]) for r in data]
    Es = [Decimal(r[idx["E_m"]]) for r in data]
    delta_min, delta_max = min(deltas), max(deltas)
    E_min, E_max = min(Es), max(Es)

    write_tabular_fragment(
        gen / "dyadic_counting_stats_table.tex",
        column_spec="lll",
        header=[r"\textbf{quantity}", r"\textbf{min}", r"\textbf{max}"],
        rows=[
            [r"$\delta_m$", Command("texttt", f"{delta_min:.16E}"), Command("texttt", f"{delta_max:.16E}")],
            [r"$E_m$", Command("texttt", f"{E_min:.16E}"), Command("texttt", f"{E_max:.16E}")],
        ],
        booktabs=True,
    )


if __name__ == "__main__":
    main()

