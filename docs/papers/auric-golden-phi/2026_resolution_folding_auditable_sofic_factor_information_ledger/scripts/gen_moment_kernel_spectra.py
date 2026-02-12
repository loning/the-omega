#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compile moment-kernel spectra from the delay-3 online transducer.

This script builds the parallel k-fold kernel on the transducer state space,
enforcing equal emitted outputs. It then estimates the Perron root rho(A_k)
via power iteration and exports a small auditable table.

Outputs:
- artifacts/export/moment_kernel_spectra.csv
- sections/generated/tab_moment_kernel_spectra.tex
"""

from __future__ import annotations

import argparse
import csv
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

from common_paths import export_dir, generated_dir


@dataclass
class Progress:
    interval_s: float = 20.0
    t0: float = time.time()
    t_last: float = 0.0

    def log(self, msg: str) -> None:
        now = time.time()
        if (now - self.t_last) >= self.interval_s:
            dt = now - self.t0
            print(f"[progress] t={dt:.1f}s {msg}", flush=True)
            self.t_last = now


State = Tuple[int, int, int]


def transducer_states() -> List[State]:
    m1 = -1
    return [
        (0, 0, 0),
        (0, 0, 1),
        (0, 0, 2),
        (0, 1, 0),
        (1, 0, 0),
        (1, 0, 1),
        (0, m1, 2),
        (1, m1, 2),
        (0, 1, m1),
        (1, 1, m1),
    ]


def transducer_transitions() -> Dict[Tuple[State, int], Tuple[State, int]]:
    """Return (next_state, output_bit) for each (state, input_digit)."""
    m1 = -1
    Q = transducer_states()
    s000, s001, s002, s010, s100, s101, s0m12, s1m12, s01m1, s11m1 = Q

    T: Dict[Tuple[State, int], Tuple[State, int]] = {}

    # 000 -> 00d (d=0,1,2), output 0
    for d in (0, 1, 2):
        T[(s000, d)] = ((0, 0, d), 0)
        T[(s100, d)] = ((0, 0, d), 1)

    # 001
    T[(s001, 0)] = (s010, 0)
    T[(s001, 1)] = (s100, 0)
    T[(s001, 2)] = (s101, 0)

    # 002
    T[(s002, 0)] = (s11m1, 0)
    T[(s002, 1)] = (s000, 1)
    T[(s002, 2)] = (s001, 1)

    # 010
    T[(s010, 0)] = (s100, 0)
    T[(s010, 1)] = (s101, 0)
    T[(s010, 2)] = (s0m12, 1)

    # 101
    T[(s101, 0)] = (s010, 1)
    T[(s101, 1)] = (s100, 1)
    T[(s101, 2)] = (s101, 1)

    # 0\bar{1}2
    T[(s0m12, 0)] = (s01m1, 0)
    T[(s0m12, 1)] = (s010, 0)
    T[(s0m12, 2)] = (s100, 0)

    # 1\bar{1}2
    T[(s1m12, 0)] = (s01m1, 1)
    T[(s1m12, 1)] = (s010, 1)
    T[(s1m12, 2)] = (s100, 1)

    # 01\bar{1}
    T[(s01m1, 0)] = (s001, 0)
    T[(s01m1, 1)] = (s002, 0)
    T[(s01m1, 2)] = (s1m12, 0)

    # 11\bar{1}
    T[(s11m1, 0)] = (s001, 1)
    T[(s11m1, 1)] = (s002, 1)
    T[(s11m1, 2)] = (s1m12, 1)

    return T


def iter_input_tuples(alphabet: Sequence[int], k: int) -> Iterable[Tuple[int, ...]]:
    if k <= 0:
        yield tuple()
        return
    if k == 1:
        for a in alphabet:
            yield (a,)
        return
    # small k only
    if k == 2:
        for a in alphabet:
            for b in alphabet:
                yield (a, b)
        return
    if k == 3:
        for a in alphabet:
            for b in alphabet:
                for c in alphabet:
                    yield (a, b, c)
        return
    raise ValueError("k too large for explicit enumeration")


def build_parallel_kernel(k: int, prog: Progress, input_alphabet: Sequence[int]) -> Tuple[List[List[Tuple[int, int]]], int]:
    Q = transducer_states()
    qi = {q: i for i, q in enumerate(Q)}
    T = transducer_transitions()
    base = len(Q)
    n_states = base**k

    # Precompute tuple decompositions for speed.
    tuples: List[Tuple[int, ...]] = []
    for idx in range(n_states):
        x = idx
        parts = [0] * k
        for j in range(k - 1, -1, -1):
            parts[j] = x % base
            x //= base
        tuples.append(tuple(parts))

    edges: List[List[Tuple[int, int]]] = [[] for _ in range(n_states)]
    for idx, parts in enumerate(tuples):
        if (idx & 0x3FFF) == 0:
            prog.log(f"build k={k} state={idx}/{n_states}")
        acc: Dict[int, int] = {}
        for inp in iter_input_tuples(input_alphabet, k):
            outs: List[int] = []
            nxt: List[int] = []
            ok = True
            for j in range(k):
                q = Q[parts[j]]
                d = int(inp[j])
                qn, e = T[(q, d)]
                nxt.append(qi[qn])
                outs.append(e)
            if any(o != outs[0] for o in outs[1:]):
                ok = False
            if not ok:
                continue
            # Flatten next tuple.
            flat = 0
            for j in range(k):
                flat = flat * base + nxt[j]
            acc[flat] = acc.get(flat, 0) + 1
        edges[idx] = sorted(acc.items())

    return edges, n_states


def power_iteration_rho(edges: List[List[Tuple[int, int]]], prog: Progress, max_iter: int = 5000, tol: float = 1e-12) -> float:
    n = len(edges)
    x = np.full((n,), 1.0 / n, dtype=np.float64)
    rho_prev = 0.0
    for it in range(max_iter):
        y = np.zeros_like(x)
        for i, outs in enumerate(edges):
            xi = x[i]
            if xi == 0.0:
                continue
            for j, w in outs:
                y[j] += xi * float(w)
        s = float(y.sum())
        if s <= 0.0:
            return 0.0
        rho = s  # because x has sum 1, and y ~ rho * x at convergence
        y /= s
        x = y
        if it % 200 == 0:
            prog.log(f"power iter={it} rho~{rho:.12f}")
        if it > 20 and abs(rho - rho_prev) <= tol * max(1.0, abs(rho_prev)):
            return rho
        rho_prev = rho
    return rho_prev


def write_csv(rows: List[Dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else ["k", "dim_full", "dim_sym_bound", "rho"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_latex_table(rows: List[Dict[str, object]], path: Path) -> None:
    from pylatex import Tabular, NoEscape  # type: ignore

    tab = Tabular("r|rrr")
    tab.add_hline()
    tab.add_row(
        [
            NoEscape("$k$"),
            NoEscape("$\\dim(A_k)$"),
            NoEscape("$\\binom{k+|Q|-1}{|Q|-1}$"),
            NoEscape("$\\rho(A_k)$ (est.)"),
        ]
    )
    tab.add_hline()
    for r in rows:
        tab.add_row([str(r["k"]), str(r["dim_full"]), str(r["dim_sym_bound"]), f'{r["rho"]:.10f}'])
    tab.add_hline()

    path.parent.mkdir(parents=True, exist_ok=True)
    frag = "\n".join(
        [
            "% auto-generated by scripts/gen_moment_kernel_spectra.py",
            "\\begin{table}[t]",
            "\\centering",
            "\\caption{Compiled moment-kernel sizes and Perron radii from the delay-$3$ online transducer (Appendix~\\ref{app:online-normalization}).}",
            "\\label{tab:moment-kernel-spectra}",
            tab.dumps(),
            "\\end{table}",
            "",
        ]
    )
    path.write_text(frag, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, action="append", default=[2, 3], help="Orders k>=2 (repeatable).")
    ap.add_argument("--input-alphabet", type=str, default="01", help="Input alphabet subset of {0,1,2}, e.g. '01' or '012'.")
    args = ap.parse_args()

    k_list = sorted({int(k) for k in args.k})
    if not k_list or any(k < 2 for k in k_list):
        raise SystemExit("k must be >= 2")
    if any(k > 3 for k in k_list):
        raise SystemExit("This script supports k <= 3 by default (state explosion).")

    alphabet = [int(ch) for ch in args.input_alphabet.strip()]
    if not alphabet or any(ch not in (0, 1, 2) for ch in alphabet):
        raise SystemExit("Invalid input alphabet")

    Q = transducer_states()
    prog = Progress()
    rows: List[Dict[str, object]] = []
    for k in k_list:
        prog.log(f"start build kernel k={k}")
        edges, n_states = build_parallel_kernel(k, prog, input_alphabet=alphabet)
        prog.log(f"start power iteration k={k} n_states={n_states}")
        rho = power_iteration_rho(edges, prog)
        dim_sym_bound = math.comb(k + len(Q) - 1, len(Q) - 1)
        rows.append(
            {
                "k": k,
                "dim_full": n_states,
                "dim_sym_bound": dim_sym_bound,
                "rho": rho,
                "log_rho": math.log(rho) if rho > 0 else float("-inf"),
            }
        )
        prog.log(f"done k={k} rho~{rho:.12f}")

    csv_path = export_dir() / "moment_kernel_spectra.csv"
    write_csv(rows, csv_path)
    print(f"[gen] wrote {csv_path}", flush=True)

    tex_path = generated_dir() / "tab_moment_kernel_spectra.tex"
    write_latex_table(rows, tex_path)
    print(f"[gen] wrote {tex_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

