#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Toy trace-fixed-point demo on the m=6, y=0^6 uplift protocol.

This script produces a tiny, program-auditable witness that fixed-point equations
of the form

    tr == Encode(Run(tr))

can have solutions inside a concrete, fully specified protocol.

Here we use the same local admissibility checks as `exp_m6_confluence_trace_needed.py`
for the base kernel m=6 with y=0^6:
- tail head t is a 3-bit word (c7,c8,c9) with no adjacent ones,
- the induced micro integer is N=21*c7 + 34*c8 + 55*c9, and we require N <= 63.

We define:
- Run(tr): starting from t=000, interpret tr as a sequence of branch labels b in {0,1}
  and update t by a shift-register Tail^{-1} step with validity checks.
- Encode(t): return the 3-bit string c7c8c9.

We then brute-force all 3-bit traces tr and list those satisfying tr == Encode(Run(tr)).

Outputs
-------
- sections/generated/tab_m6_trace_fixedpoint_demo.tex
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import generated_dir
from common_tex_pylatex import write_tabular_fragment


def _no_adjacent_ones(x: int) -> bool:
    return (x & (x << 1)) == 0


def _bits_c7c8c9(t: int) -> str:
    c7 = (t >> 0) & 1
    c8 = (t >> 1) & 1
    c9 = (t >> 2) & 1
    return f"{c7}{c8}{c9}"


def _micro_N_for_y0_m6(t: int) -> int:
    c7 = (t >> 0) & 1
    c8 = (t >> 1) & 1
    c9 = (t >> 2) & 1
    return 21 * int(c7) + 34 * int(c8) + 55 * int(c9)


def _step_tail_inverse(t: int, b: int) -> Optional[int]:
    mask = 0b111  # L=3 for m=6
    tp = ((t << 1) & mask) | int(b)
    if not _no_adjacent_ones(tp):
        return None
    Np = _micro_N_for_y0_m6(tp)
    if not (0 <= Np <= 63):
        return None
    return int(tp)


def _run(tr_bits: str) -> Optional[int]:
    t = 0
    for ch in tr_bits:
        b = 1 if ch == "1" else 0
        tp = _step_tail_inverse(t, b=b)
        if tp is None:
            return None
        t = tp
    return int(t)


def _encode(t: int) -> str:
    return _bits_c7c8c9(t)


def _all_bitstrings(n: int) -> List[str]:
    out: List[str] = []
    for x in range(1 << n):
        out.append("".join("1" if (x >> i) & 1 else "0" for i in range(n - 1, -1, -1)))
    return out


def _find_fixed_points(n: int) -> List[Tuple[str, str, int]]:
    fps: List[Tuple[str, str, int]] = []
    for tr in _all_bitstrings(n):
        t = _run(tr)
        if t is None:
            continue
        code = _encode(int(t))
        if tr == code:
            fps.append((tr, code, _micro_N_for_y0_m6(int(t))))
    return fps


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    n = 3
    params: Dict[str, object] = {"m": 6, "y": "0^6", "trace_len": n}
    out_tab = "tab_m6_trace_fixedpoint_demo.tex"

    script_path = Path(__file__).resolve()
    run = prepare_run(
        experiment="m6_trace_fixedpoint_demo",
        params=params,
        script_path=script_path,
        required_files=[out_tab],
        force=bool(args.force),
        extra_fingerprint=None,
    )

    generated_dir().mkdir(parents=True, exist_ok=True)

    if run.cached:
        print(f"[exp_m6_trace_fixedpoint_demo] cached: {run.run_dir.name}", flush=True)
        copy_atomic(run.run_dir / out_tab, generated_dir() / out_tab)
        return

    fps = _find_fixed_points(n=n)
    print(f"[exp_m6_trace_fixedpoint_demo] candidates=2^{n} fixed_points={len(fps)}", flush=True)
    for tr, code, N in fps:
        print(f"[exp_m6_trace_fixedpoint_demo] fp: tr={tr} Encode(Run(tr))={code} N={N}", flush=True)

    rows: List[List[str]] = []
    if not fps:
        rows = [["-", "-", "-"]]
    else:
        for tr, code, N in fps:
            rows.append([tr, code, str(N)])

    out_tab_path = run.run_dir / out_tab
    write_tabular_fragment(
        out_tab_path,
        column_spec="l l r",
        header=[r"\textbf{$\mathsf{tr}$}", r"\textbf{$\mathrm{Encode}(\mathrm{Run}(\mathsf{tr}))$}", r"\textbf{$N$}"],
        rows=rows,
        booktabs=True,
    )

    manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, [out_tab])
    write_manifest(run.run_dir, manifest)

    copy_atomic(out_tab_path, generated_dir() / out_tab)
    print("[exp_m6_trace_fixedpoint_demo] done", flush=True)


if __name__ == "__main__":
    main()

