#!/usr/bin/env python3
"""Enumerate Fold6 tables and emit LaTeX fragments (cached, reproducible).

Artifacts:
  artifacts/fold6_tables/<run_id>/
    - fold6_rows.csv
    - preimages.json
    - manifest.json

Generated LaTeX:
  sections/generated/fold6_preimage_histogram_table.tex
  sections/generated/fold6_boundary_preimages_table.tex
  sections/generated/fold6_full_table_part1.tex
  sections/generated/fold6_full_table_part2.tex
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir
from common_progress import Progress
from common_tex_pylatex import write_tabular_fragment


def _fib_upto(n: int) -> List[int]:
    # F0=0, F1=1
    f = [0, 1]
    while len(f) <= n:
        f.append(f[-1] + f[-2])
    return f


F = _fib_upto(11)  # need up to F11


def zeckendorf_digits(N: int, max_k: int = 10) -> List[int]:
    # digits c_k for weights F_{k+1}, k>=1, greedy and forbids adjacent 1
    c = [0] * (max_k + 1)  # 0..max_k
    n = int(N)
    k = int(max_k)
    while k >= 1:
        w = F[k + 1]
        if w <= n:
            c[k] = 1
            n -= w
            k -= 2
        else:
            k -= 1
    return c


def bits6_from_int(N: int) -> Tuple[int, int, int, int, int, int]:
    # b1..b6, b1 is MSB
    return tuple((N >> (5 - i)) & 1 for i in range(6))  # type: ignore[return-value]


def word_str(w: Tuple[int, ...]) -> str:
    return "".join(str(int(x)) for x in w)


def fold6(N: int) -> Tuple[Tuple[int, ...], int, int]:
    c = zeckendorf_digits(N, max_k=10)
    w = tuple(int(x) for x in c[1:7])  # c1..c6
    V = sum(w[i] * F[i + 2] for i in range(6))  # w1*F2 + ... + w6*F7
    delta = int(N) - int(V)
    return w, int(V), int(delta)


def main() -> None:
    prog = Progress("fold6_tables", every_seconds=5.0)
    script_path = Path(__file__).resolve()
    params: Dict[str, object] = {"m": 6, "N_max": 63}

    required = ["fold6_rows.csv", "preimages.json"]
    run = prepare_run("fold6_tables", params=params, script_path=script_path, required_files=required, force=False)

    if not run.cached:
        rows_csv = run.run_dir / "fold6_rows.csv"
        preimages: Dict[str, List[int]] = {}

        with open(rows_csv, "w", newline="", encoding="utf-8") as f:
            wcsv = csv.writer(f)
            wcsv.writerow(["N", "bits6", "fold6", "V", "delta"])
            for N in range(64):
                if N % 8 == 0:
                    prog.tick(f"enumerating N={N}/63")
                bits6 = bits6_from_int(N)
                w, V, delta = fold6(N)
                ws = word_str(w)
                preimages.setdefault(ws, []).append(int(N))
                wcsv.writerow([N, word_str(bits6), ws, V, delta])

        (run.run_dir / "preimages.json").write_text(
            json.dumps(preimages, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
        manifest = add_output_hashes(manifest, run.run_dir, rel_paths=required)
        write_manifest(run.run_dir, manifest)

    # Emit LaTeX fragments deterministically from artifacts
    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)

    preimages = json.loads((run.run_dir / "preimages.json").read_text(encoding="utf-8"))
    # histogram
    hist: Dict[int, int] = {}
    for ws, ns in preimages.items():
        hist[len(ns)] = hist.get(len(ns), 0) + 1
    rows_hist = [[k, hist.get(k, 0)] for k in [2, 3, 4]]
    write_tabular_fragment(
        gen / "fold6_preimage_histogram_table.tex",
        column_spec="rr",
        header=[r"\textbf{$|\mathrm{Fold}_6^{-1}(w)|$}", r"\textbf{count}"],
        rows=rows_hist,
        booktabs=True,
    )

    # boundary preimages
    bdry = ["100001", "100101", "101001"]
    rows_bdry = [[f"\\texttt{{{b}}}", "\\texttt{" + ",".join(str(int(x)) for x in preimages.get(b, [])) + "}"] for b in bdry]
    write_tabular_fragment(
        gen / "fold6_boundary_preimages_table.tex",
        column_spec="ll",
        header=[r"\textbf{boundary word}", r"\textbf{preimages}"],
        rows=rows_bdry,
        booktabs=True,
    )

    # full table
    table_rows: List[List[object]] = []
    with open(run.run_dir / "fold6_rows.csv", "r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        _hdr = next(r)
        for line in r:
            N, bits6, ws, V, delta = line
            table_rows.append(
                [
                    int(N),
                    f"\\texttt{{{bits6}}}",
                    f"\\texttt{{{ws}}}",
                    int(V),
                    int(delta),
                ]
            )
    header_full = [r"\textbf{$N$}", r"\textbf{bits}", r"\textbf{$\Fold_6(N)$}", r"\textbf{$V$}", r"\textbf{$\Delta$}"]
    mid = len(table_rows) // 2
    write_tabular_fragment(
        gen / "fold6_full_table_part1.tex",
        column_spec="rcccc",
        header=header_full,
        rows=table_rows[:mid],
        booktabs=True,
    )
    write_tabular_fragment(
        gen / "fold6_full_table_part2.tex",
        column_spec="rcccc",
        header=header_full,
        rows=table_rows[mid:],
        booktabs=True,
    )

    prog.tick(f"done (run_id={run.run_id})")


if __name__ == "__main__":
    main()

