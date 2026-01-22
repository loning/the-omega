#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate LaTeX runlog table fragments for the genesis process (m=6, y=0^6).

This script produces:
- sections/generated/tab_runlog_m6_y0.tex
- sections/generated/tab_runlog_m6_y0_fold.tex

The table is a deterministic, auditable trace of n unfold steps under a fixed policy:
- Macro observation is fixed to y=0^6 (macro word w=0).
- Energy tape pop consumes the last bit b_i.
- Next tail-head t_{i+1} is chosen from admissible candidates in Tail^{-1}(t_i):
    - filter by no-adjacent-ones on tail bits
    - filter by micro bound N<2^m and Fold_m(N)=y
    - if there are >=2 candidates, pick index b_i in sorted order; else pick the only one
- Reconstruct micro N_{i+1} from (y, t_{i+1}), then code c_i=Code_y(N_{i+1}) is appended to energy tape.

Note:
This is a reproducible illustration for the paper; it is not the only possible policy.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_export import copy_atomic
from common_paths import generated_dir
from common_tex_pylatex import write_tabular_fragment
from common_zeckendorf_uplift import (
    fold_f_m,
    micro_N_from_macro_and_tail,
    tail_shift_word,
    tail_inverse_step_candidates,
    tail_length,
    tail_word_of_N,
)


def _bits_str_fixed_width_low_to_high(x: int, width: int) -> str:
    return "".join("1" if (x >> i) & 1 else "0" for i in range(width))


def _t_c7c8c9_str(t: int, L: int) -> str:
    # Print tail bits as c_{m+1}..c_K = low-to-high bits. For m=6, that's c7c8c9.
    return _bits_str_fixed_width_low_to_high(t, width=L)


def _pop_last_bit(bits: str) -> Tuple[str, int]:
    if bits == "":
        raise ValueError("cannot pop from empty bitstring")
    b = int(bits[-1])
    return bits[:-1], b


@dataclass(frozen=True)
class Row:
    i: int
    t_i: str
    b_i: int
    t_ip1: str
    N_ip1: int
    c_i: str
    tr_ip1: str
    E_ip1: str


@dataclass(frozen=True)
class FoldRow:
    i: int
    t_ip1: str
    b_i: int
    t_i: str
    N_ip1: int
    c_i: str
    tr_i: str
    E_i: str


def _pop_suffix(bits: str, k: int) -> Tuple[str, str]:
    if k < 0:
        raise ValueError("k must be nonnegative")
    if k == 0:
        return bits, ""
    if len(bits) < k:
        raise ValueError("not enough bits to pop suffix")
    return bits[:-k], bits[-k:]


def _latex_eps(bits: str) -> str:
    # Use TeX epsilon instead of Unicode ε to avoid font issues.
    return bits if bits != "" else r"\(\epsilon\)"


def _build_code_map_for_y(m: int, y_w: int) -> Tuple[Dict[int, str], int]:
    pre: List[int] = []
    for N in range(1 << m):
        if int(fold_f_m(N, m=m)) == int(y_w):
            pre.append(int(N))
    pre.sort()
    s = len(pre)
    if s <= 0:
        raise ValueError("empty fiber for given macro y")
    k = int(math.ceil(math.log2(float(s))))
    code: Dict[int, str] = {}
    for idx, N in enumerate(pre):
        code[N] = format(idx, f"0{k}b")
    return code, k


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=3)
    ap.add_argument("--E0", type=str, default="1", help="initial energy tape bits, last bit is popped first")
    ap.add_argument("--t0", type=int, default=0, help="initial tail-head word as int (packed low-to-high)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    m = 6
    y_w = 0  # y=0^6 in low-to-high packed bits
    L = int(tail_length(m))
    if L != 3:
        raise SystemExit(f"expected tail length L=3 for m=6, got L={L}")

    steps = int(args.steps)
    if steps < 1:
        raise SystemExit("--steps must be >=1")

    E = str(args.E0).strip()
    if any(ch not in "01" for ch in E):
        raise SystemExit("--E0 must be a bitstring of 0/1")
    t = int(args.t0)
    if t < 0 or t >= (1 << L):
        raise SystemExit(f"--t0 out of range for L={L}")

    out_tab = "tab_runlog_m6_y0.tex"
    out_tab_fold = "tab_runlog_m6_y0_fold.tex"
    params: Dict[str, object] = {"m": m, "y": "0^6", "steps": steps, "E0": E, "t0": t}

    script_path = Path(__file__).resolve()
    run = prepare_run(
        experiment="runlog_m6_y0",
        params=params,
        script_path=script_path,
        required_files=[out_tab, out_tab_fold],
        force=bool(args.force),
        extra_fingerprint=None,
    )

    if run.cached:
        print(f"[gen_runlog_m6_y0] cached: {run.run_dir.name}", flush=True)
        copy_atomic(run.run_dir / out_tab, generated_dir() / out_tab)
        copy_atomic(run.run_dir / out_tab_fold, generated_dir() / out_tab_fold)
        return

    code_map, k = _build_code_map_for_y(m=m, y_w=y_w)
    inv_code_map: Dict[str, int] = {c: N for (N, c) in code_map.items()}

    # Quick consistency check: ensure Code_y is consistent with tail_word_of_N on this fiber.
    fiber_N = sorted(code_map.keys())
    for N in fiber_N:
        tail, LL = tail_word_of_N(N, m=m)
        if int(LL) != int(L):
            raise SystemExit(f"inconsistent tail length for N={N}: got L={LL}, expected {L}")
        N2 = int(micro_N_from_macro_and_tail(y_w, tail, m=m))
        if N2 != int(N):
            raise SystemExit(f"reconstruction mismatch for N={N}: reconstructed {N2} from (y,tail)")

    # Record full audited states to verify folding is exact inverse.
    # states[i] = (t_i, tr_i, E_i), and after n steps we have states[n].
    states: List[Tuple[int, str, str]] = []
    tr = ""
    rows: List[Row] = []
    states.append((int(t), str(tr), str(E)))
    for i in range(steps):
        if E == "":
            raise SystemExit(f"energy tape empty at step {i}, cannot pop b_i")
        E_minus, b = _pop_last_bit(E)

        # Candidates t' in Tail^{-1}(t), filtered by macro compatibility and micro bound.
        cands = tail_inverse_step_candidates(t, L=L)
        good: List[int] = []
        for tp in cands:
            Np = int(micro_N_from_macro_and_tail(y_w, tp, m=m))
            if not (0 <= Np < (1 << m)):
                continue
            if int(fold_f_m(Np, m=m)) != int(y_w):
                continue
            good.append(int(tp))
        good.sort()
        if len(good) <= 0:
            raise SystemExit(f"no admissible Tail^(-1) candidates from t={t} at step {i}")

        idx = b if len(good) >= 2 else 0
        if idx >= len(good):
            idx = 0
        tp = int(good[idx])

        Np = int(micro_N_from_macro_and_tail(y_w, tp, m=m))
        if Np not in code_map:
            raise SystemExit(f"micro N={Np} not in fiber Fold^{-1}(y) (unexpected)")
        c = code_map[Np]

        E = E_minus + c
        tr = tr + str(b)

        rows.append(
            Row(
                i=i,
                t_i=_t_c7c8c9_str(t, L=L),
                b_i=int(b),
                t_ip1=_t_c7c8c9_str(tp, L=L),
                N_ip1=int(Np),
                c_i=str(c),
                tr_ip1=_latex_eps(str(tr)),
                E_ip1=_latex_eps(str(E)),
            )
        )
        t = tp
        states.append((int(t), str(tr), str(E)))

    out_tab_path = run.run_dir / out_tab
    write_tabular_fragment(
        out_tab_path,
        column_spec="r l r l r l l l",
        header=[
            r"\textbf{$i$}",
            r"\textbf{$t_i$}",
            r"\textbf{$b_i$}",
            r"\textbf{$t_{i+1}$}",
            r"\textbf{$N_{i+1}$}",
            r"\textbf{$c_i$}",
            r"\textbf{$\mathsf{tr}_{i+1}$}",
            r"\textbf{$\mathsf{E}_{i+1}$}",
        ],
        rows=[[r.i, r.t_i, r.b_i, r.t_ip1, r.N_ip1, r.c_i, r.tr_ip1, r.E_ip1] for r in rows],
        booktabs=True,
    )

    # Fold (reverse) runlog: verify step-by-step inverse and generate table.
    fold_rows: List[FoldRow] = []
    t_cur, tr_cur, E_cur = states[-1]
    for i in range(steps - 1, -1, -1):
        t_prev_expected, tr_prev_expected, E_prev_expected = states[i]

        # Pop trace bit b_i.
        if tr_cur == "":
            raise SystemExit(f"trace empty at fold step i={i}")
        tr_prev, b = tr_cur[:-1], int(tr_cur[-1])

        # Pop energy suffix c_i of length k and decode N_{i+1}.
        E_minus, c = _pop_suffix(E_cur, k=k)
        if c not in inv_code_map:
            raise SystemExit(f"unknown code suffix c={c!r} at fold step i={i}")
        N_ip1 = int(inv_code_map[c])

        # Tail rollback.
        t_prev = int(tail_shift_word(t_cur))

        # Refund the consumed branch bit b back to energy.
        E_prev = E_minus + str(b)

        # Verify we exactly recover the audited previous state.
        if t_prev != int(t_prev_expected):
            raise SystemExit(f"t mismatch at fold step i={i}: got {t_prev}, expected {t_prev_expected}")
        if tr_prev != str(tr_prev_expected):
            raise SystemExit(f"tr mismatch at fold step i={i}: got {tr_prev!r}, expected {tr_prev_expected!r}")
        if E_prev != str(E_prev_expected):
            raise SystemExit(f"E mismatch at fold step i={i}: got {E_prev!r}, expected {E_prev_expected!r}")

        fold_rows.append(
            FoldRow(
                i=i,
                t_ip1=_t_c7c8c9_str(t_cur, L=L),
                b_i=int(b),
                t_i=_t_c7c8c9_str(t_prev, L=L),
                N_ip1=int(N_ip1),
                c_i=str(c),
                tr_i=_latex_eps(str(tr_prev)),
                E_i=_latex_eps(str(E_prev)),
            )
        )
        t_cur, tr_cur, E_cur = t_prev, tr_prev, E_prev

    # Present folding in natural (forward) row order i=0..n-1.
    fold_rows = list(reversed(fold_rows))
    out_tab_fold_path = run.run_dir / out_tab_fold
    write_tabular_fragment(
        out_tab_fold_path,
        column_spec="r l r l r l l l",
        header=[
            r"\textbf{$i$}",
            r"\textbf{$t_{i+1}$}",
            r"\textbf{$b_i$}",
            r"\textbf{$t_i$}",
            r"\textbf{$N_{i+1}$}",
            r"\textbf{$c_i$}",
            r"\textbf{$\mathsf{tr}_i$}",
            r"\textbf{$\mathsf{E}_i$}",
        ],
        rows=[[r.i, r.t_ip1, r.b_i, r.t_i, r.N_ip1, r.c_i, r.tr_i, r.E_i] for r in fold_rows],
        booktabs=True,
    )

    manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
    manifest = add_output_hashes(manifest, run.run_dir, [out_tab, out_tab_fold])
    write_manifest(run.run_dir, manifest)

    copy_atomic(out_tab_path, generated_dir() / out_tab)
    copy_atomic(out_tab_fold_path, generated_dir() / out_tab_fold)
    print("[gen_runlog_m6_y0] done", flush=True)


if __name__ == "__main__":
    main()

