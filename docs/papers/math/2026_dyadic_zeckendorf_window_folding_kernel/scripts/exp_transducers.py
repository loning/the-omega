#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate transducer artifacts for boundary dynamics (cached, reproducible).

Artifacts:
  artifacts/transducers/<run_id>/
    - deterministic_order_table_L10_30.csv
    - deterministic_pareto_table.csv
    - transducer_L20_order8_mapping.csv
    - transducer_L20_order5_ambiguous.csv
    - variable_length_transducer_L20_K8.csv
    - variable_length_depth_fraction.csv
    - variable_length_depth_fraction.png
    - manifest.json

LaTeX fragments:
  sections/generated/transducers_summary.tex
  sections/generated/transducers_order_table.tex
  sections/generated/transducers_pareto_table.tex
  sections/generated/transducers_depth_fraction_table.tex
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

import matplotlib.pyplot as plt

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir
from common_progress import Progress
from common_tex_pylatex import write_tabular_fragment
from pylatex import Command
from zeckendorf import fibs_up_to_index, sigma_window, zeckendorf_digits


Sigma = Tuple[int, ...]
Context = Tuple[Sigma, ...]


def _sigma_str(s: Sigma) -> str:
    return "".join("1" if x else "0" for x in s)


def _context_str(ctx: Context) -> str:
    return "/".join(_sigma_str(s) for s in ctx)


def _build_sigmas_for_range(m_min: int, m_max: int, L_values: Sequence[int], fib: List[int]) -> Dict[int, List[Sigma]]:
    """Return dict L -> list of sigma_m^(L) for m in [m_min..m_max] (inclusive), indexed by (m-m_min)."""
    if m_min < 1:
        raise ValueError("m_min must be >= 1")
    if m_max < m_min:
        raise ValueError("m_max must be >= m_min")
    if not L_values:
        raise ValueError("L_values must be non-empty")

    sigmas: Dict[int, List[Sigma]] = {L: [] for L in L_values}
    prog = Progress("transducers", every_seconds=20.0)

    B = 0
    for m in range(1, m_min):
        B = (B << 1) | 1

    for m in range(m_min, m_max + 1):
        B = (B << 1) | 1
        _, c = zeckendorf_digits(B, fib)
        for L in L_values:
            sigmas[L].append(sigma_window(c, m=m, L=L))
        prog.tick(f"built sigma windows: m={m}/{m_max}")

    return sigmas


def _context_next_pairs(sigmas: List[Sigma], order: int) -> Iterable[Tuple[Context, Sigma]]:
    # sigmas list is over consecutive m, so index i corresponds to m=m_min+i.
    # For each i >= order-1, context is last 'order' sigmas ending at i, next is i+1.
    for i in range(order - 1, len(sigmas) - 1):
        ctx = tuple(sigmas[i - order + 1 : i + 1])
        nxt = sigmas[i + 1]
        yield ctx, nxt


def _mapping_for_order(sigmas: List[Sigma], order: int) -> Tuple[Dict[Context, Sigma], Dict[Context, Set[Sigma]]]:
    options: Dict[Context, Set[Sigma]] = defaultdict(set)
    for ctx, nxt in _context_next_pairs(sigmas, order=order):
        options[ctx].add(nxt)
    mapping: Dict[Context, Sigma] = {}
    ambiguous: Dict[Context, Set[Sigma]] = {}
    for ctx, sset in options.items():
        if len(sset) == 1:
            mapping[ctx] = next(iter(sset))
        else:
            ambiguous[ctx] = sset
    return mapping, ambiguous


def _min_deterministic_order(sigmas: List[Sigma], k_max: int) -> Tuple[int, int]:
    """Return (k_min, num_contexts_at_kmin). If no deterministic found, returns (0,0)."""
    for k in range(1, k_max + 1):
        mapping, ambiguous = _mapping_for_order(sigmas, order=k)
        if not ambiguous:
            return k, len(mapping)
    return 0, 0


def _variable_length_rules(sigmas: List[Sigma], K: int) -> Tuple[Dict[Context, Sigma], Counter]:
    """Build variable-length determinizing rules up to depth K.

    Returns:
      - rules: dict context (length d) -> next sigma
      - usage: counter over chosen depth per time step (shortest determinizing suffix)
    """
    # Precompute next options for all depths 1..K for suffix contexts.
    opts_by_depth: Dict[int, Dict[Context, Set[Sigma]]] = {}
    for d in range(1, K + 1):
        opts: Dict[Context, Set[Sigma]] = defaultdict(set)
        for ctx, nxt in _context_next_pairs(sigmas, order=d):
            opts[ctx].add(nxt)
        opts_by_depth[d] = opts

    rules: Dict[Context, Sigma] = {}
    for d in range(1, K + 1):
        for ctx, sset in opts_by_depth[d].items():
            if len(sset) == 1:
                rules[ctx] = next(iter(sset))

    # Verify every step can be resolved by some depth <=K, and record usage.
    usage: Counter = Counter()
    for i in range(0, len(sigmas) - 1):
        found = False
        for d in range(1, K + 1):
            if i - d + 1 < 0:
                continue
            ctx = tuple(sigmas[i - d + 1 : i + 1])
            if ctx in rules:
                usage[d] += 1
                found = True
                break
        if not found:
            raise RuntimeError(f"variable-length transducer failed to resolve step at index={i}")
    return rules, usage


def _write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(list(header))
        for r in rows:
            w.writerow(list(r))


def _read_csv(path: Path) -> List[List[str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        return [row for row in r]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m_min", type=int, default=100)
    ap.add_argument("--m_max", type=int, default=2000)
    ap.add_argument("--L_min", type=int, default=10)
    ap.add_argument("--L_max", type=int, default=30)
    ap.add_argument("--k_max", type=int, default=12)
    ap.add_argument("--L_focus", type=int, default=20)
    ap.add_argument("--order_focus", type=int, default=8)
    ap.add_argument("--order_ambiguous", type=int, default=5)
    ap.add_argument("--K_var", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    script_path = Path(__file__).resolve()
    params = {
        "m_min": args.m_min,
        "m_max": args.m_max,
        "L_min": args.L_min,
        "L_max": args.L_max,
        "k_max": args.k_max,
        "L_focus": args.L_focus,
        "order_focus": args.order_focus,
        "order_ambiguous": args.order_ambiguous,
        "K_var": args.K_var,
    }

    required = [
        "deterministic_order_table_L10_30.csv",
        "deterministic_pareto_table.csv",
        "transducer_L20_order8_mapping.csv",
        "transducer_L20_order5_ambiguous.csv",
        "variable_length_transducer_L20_K8.csv",
        "variable_length_depth_fraction.csv",
        "variable_length_depth_fraction.png",
    ]
    run = prepare_run("transducers", params=params, script_path=script_path, required_files=required, force=args.force)

    if not run.cached:
        # Build Fibonacci table large enough for Zeckendorf on B_m up to m_max.
        fib = fibs_up_to_index(2 * args.m_max + 10)
        L_values = list(range(args.L_min, args.L_max + 1))
        if args.L_focus not in L_values:
            L_values.append(args.L_focus)
        L_values = sorted(set(L_values))

        sigmas_by_L = _build_sigmas_for_range(args.m_min, args.m_max + 1, L_values=L_values, fib=fib)

        # Minimal deterministic order scan.
        order_rows: List[List[str]] = []
        pareto_rows: List[List[str]] = []
        for L in range(args.L_min, args.L_max + 1):
            k_min, num_ctx = _min_deterministic_order(sigmas_by_L[L], k_max=args.k_max)
            order_rows.append([str(L), str(k_min), str(num_ctx)])
            if k_min > 0:
                pareto_rows.append([str(L), str(k_min), str(num_ctx)])

        _write_csv(
            run.run_dir / "deterministic_order_table_L10_30.csv",
            header=["L", "k_min", "num_contexts_at_k_min"],
            rows=order_rows,
        )
        _write_csv(
            run.run_dir / "deterministic_pareto_table.csv",
            header=["L", "k", "num_contexts"],
            rows=pareto_rows,
        )

        # Focus mapping for L_focus, order_focus.
        sig_focus = sigmas_by_L[args.L_focus]
        mapping8, ambiguous8 = _mapping_for_order(sig_focus, order=args.order_focus)
        if ambiguous8:
            raise RuntimeError(f"expected deterministic mapping for L={args.L_focus}, order={args.order_focus}, got ambiguous={len(ambiguous8)}")

        mapping_rows = [[_context_str(ctx), _sigma_str(nxt)] for ctx, nxt in sorted(mapping8.items(), key=lambda x: _context_str(x[0]))]
        _write_csv(
            run.run_dir / f"transducer_L{args.L_focus}_order{args.order_focus}_mapping.csv",
            header=["context", "next_sigma"],
            rows=mapping_rows,
        )

        # Ambiguous contexts for order_ambiguous.
        _, ambiguous5 = _mapping_for_order(sig_focus, order=args.order_ambiguous)
        amb_rows = []
        for ctx, opts in sorted(ambiguous5.items(), key=lambda x: _context_str(x[0])):
            amb_rows.append([_context_str(ctx), str(len(opts)), "|".join(sorted(_sigma_str(s) for s in opts))])
        _write_csv(
            run.run_dir / f"transducer_L{args.L_focus}_order{args.order_ambiguous}_ambiguous.csv",
            header=["context", "num_next_options", "next_options"],
            rows=amb_rows,
        )

        # Variable-length rules up to K_var.
        rules, usage = _variable_length_rules(sig_focus, K=args.K_var)
        var_rows = []
        for ctx, nxt in sorted(rules.items(), key=lambda x: (len(x[0]), _context_str(x[0]))):
            var_rows.append([str(len(ctx)), _context_str(ctx), _sigma_str(nxt)])
        _write_csv(
            run.run_dir / f"variable_length_transducer_L{args.L_focus}_K{args.K_var}.csv",
            header=["depth", "context", "next_sigma"],
            rows=var_rows,
        )

        # Depth fraction.
        total = sum(usage.values())
        depth_rows = []
        for d in range(1, args.K_var + 1):
            c = int(usage.get(d, 0))
            frac = (c / total) if total > 0 else 0.0
            depth_rows.append([str(d), str(c), f"{frac:.10f}"])
        _write_csv(
            run.run_dir / "variable_length_depth_fraction.csv",
            header=["depth", "count", "fraction"],
            rows=depth_rows,
        )

        # Plot depth distribution.
        xs = [int(r[0]) for r in depth_rows]
        ys = [float(r[2]) for r in depth_rows]
        plt.figure(figsize=(6, 3))
        plt.bar(xs, ys, color="#1976D2")
        plt.xlabel("Depth")
        plt.ylabel("Fraction")
        plt.title("Variable-length transducer depth distribution (L=20, K=8)")
        plt.xticks(xs)
        plt.tight_layout()
        plt.savefig(run.run_dir / "variable_length_depth_fraction.png", dpi=200)
        plt.close()

        manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
        manifest = add_output_hashes(manifest, run.run_dir, rel_paths=required)
        write_manifest(run.run_dir, manifest)

    # Always (re-)emit a small LaTeX summary fragment.
    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)
    write_tabular_fragment(
        gen / "transducers_summary.tex",
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
    order_rows = _read_csv(run.run_dir / "deterministic_order_table_L10_30.csv")
    pareto_rows = _read_csv(run.run_dir / "deterministic_pareto_table.csv")
    depth_rows = _read_csv(run.run_dir / "variable_length_depth_fraction.csv")

    # deterministic_order_table_L10_30.csv: header + rows (L, k_min, num_contexts_at_k_min)
    write_tabular_fragment(
        gen / "transducers_order_table.tex",
        column_spec="rrr",
        header=[r"$L$", r"$k_{\min}$", r"\#contexts"],
        rows=[[r[0], r[1], r[2]] for r in order_rows[1:]],
        booktabs=True,
    )

    # deterministic_pareto_table.csv: header + rows (L, k, num_contexts)
    write_tabular_fragment(
        gen / "transducers_pareto_table.tex",
        column_spec="rrr",
        header=[r"$L$", r"$k$", r"\#contexts"],
        rows=[[r[0], r[1], r[2]] for r in pareto_rows[1:]],
        booktabs=True,
    )

    # variable_length_depth_fraction.csv: header + rows (depth, count, fraction)
    write_tabular_fragment(
        gen / "transducers_depth_fraction_table.tex",
        column_spec="rrr",
        header=[r"\textbf{depth}", r"\textbf{count}", r"\textbf{fraction}"],
        rows=[[r[0], r[1], r[2]] for r in depth_rows[1:]],
        booktabs=True,
    )


if __name__ == "__main__":
    main()

