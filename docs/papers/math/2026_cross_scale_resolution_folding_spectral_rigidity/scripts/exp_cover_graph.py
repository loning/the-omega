#!/usr/bin/env python3
"""Build the Fold6-labeled covering graph and emit summary LaTeX (cached).

We build nodes as Enc6(N) = (Fold6(N), Delta(N)), which is bijective for N=0..63.
Edges come from the 6-bit shift operator on microstates, relabeled by Enc6.

Artifacts:
  artifacts/cover_graph/<run_id>/
    - summary.json
    - manifest.json

Generated LaTeX:
  sections/generated/cover_graph_summary.tex
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from common_artifacts import add_output_hashes, build_base_manifest, prepare_run, write_manifest
from common_paths import generated_dir
from common_progress import Progress
from common_tex_pylatex import write_tabular_fragment


def _fib_upto(n: int) -> List[int]:
    f = [0, 1]
    while len(f) <= n:
        f.append(f[-1] + f[-2])
    return f


F = _fib_upto(11)


def zeckendorf_digits(N: int, max_k: int = 10) -> List[int]:
    c = [0] * (max_k + 1)
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


def word_str(w: Tuple[int, ...]) -> str:
    return "".join(str(int(x)) for x in w)


def fold6(N: int) -> Tuple[Tuple[int, ...], int, int]:
    c = zeckendorf_digits(N, max_k=10)
    w = tuple(int(x) for x in c[1:7])
    V = sum(w[i] * F[i + 2] for i in range(6))
    delta = int(N) - int(V)
    return w, int(V), int(delta)


def bits6_from_int(N: int) -> Tuple[int, int, int, int, int, int]:
    return tuple((N >> (5 - i)) & 1 for i in range(6))  # type: ignore[return-value]


def int_from_bits6(b: Tuple[int, ...]) -> int:
    x = 0
    for i in range(6):
        x = (x << 1) | int(b[i])
    return int(x)


def shift_word(b: Tuple[int, ...], x: int) -> Tuple[int, ...]:
    return tuple(b[1:] + (int(x),))


def main() -> None:
    prog = Progress("cover_graph", every_seconds=5.0)
    script_path = Path(__file__).resolve()
    params: Dict[str, object] = {"m": 6, "edges": "shift_only_symmetrized"}

    required = ["summary.json"]
    run = prepare_run("cover_graph", params=params, script_path=script_path, required_files=required, force=False)

    if not run.cached:
        # Build node mapping N -> (w,delta) and index
        nodes: List[Tuple[str, int]] = []
        for N in range(64):
            w, _V, delta = fold6(N)
            nodes.append((word_str(w), int(delta)))
        idx = {nodes[i]: i for i in range(64)}

        # Directed shift edges on microstates, then relabel
        directed_edges: List[Tuple[int, int]] = []
        for N in range(64):
            if N % 8 == 0:
                prog.tick(f"edges from N={N}/63")
            b = bits6_from_int(N)
            u = idx[nodes[N]]
            for x in (0, 1):
                b2 = shift_word(b, x)
                N2 = int_from_bits6(b2)
                v = idx[nodes[N2]]
                directed_edges.append((u, v))

        # Symmetrize to undirected simple graph
        undirected = set()
        for (u, v) in directed_edges:
            a, b = (u, v) if u <= v else (v, u)
            if a != b:
                undirected.add((a, b))

        n = 64
        A = np.zeros((n, n), dtype=float)
        for (a, b) in undirected:
            A[a, b] = 1.0
            A[b, a] = 1.0

        deg = A.sum(axis=1)
        d_min = float(deg.min())
        d_max = float(deg.max())
        d_avg = float(deg.mean())

        # Random walk matrix on undirected graph
        # (Graph is connected for this construction; still guard)
        with np.errstate(divide="ignore", invalid="ignore"):
            P = (A.T / deg).T
            P[np.isnan(P)] = 0.0

        eig = np.linalg.eigvals(P)
        eig_real = np.sort(np.real(eig))[::-1]
        lam1 = float(eig_real[0])
        lam2 = float(eig_real[1]) if len(eig_real) >= 2 else float("nan")
        gamma = float(1.0 - lam2)

        # Example lower bound scale for eps=0.1 (up to constants)
        eps = 0.1
        lb_scale = float(np.log(1.0 / eps) / max(gamma, 1e-12))

        summary = {
            "n_vertices": n,
            "n_directed_shift_edges": int(len(directed_edges)),
            "n_undirected_edges_sym": int(len(undirected)),
            "degree_min": d_min,
            "degree_max": d_max,
            "degree_avg": d_avg,
            "lambda1_real": lam1,
            "lambda2_real": lam2,
            "spectral_gap_est": gamma,
            "mixing_lb_scale_logeps_over_gap": lb_scale,
            "eps": eps,
        }
        (run.run_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        manifest = build_base_manifest(run.experiment, run.run_id, params=params, script_path=script_path)
        manifest = add_output_hashes(manifest, run.run_dir, rel_paths=required)
        write_manifest(run.run_dir, manifest)

    # Emit LaTeX fragment
    gen = generated_dir()
    gen.mkdir(parents=True, exist_ok=True)
    summary = json.loads((run.run_dir / "summary.json").read_text(encoding="utf-8"))
    rows = [
        [r"\textbf{run\_id}", f"\\texttt{{{run.run_id}}}"],
        [r"\textbf{$|\widetilde V_6|$}", summary["n_vertices"]],
        [r"\textbf{directed shift edges}", summary["n_directed_shift_edges"]],
        [r"\textbf{undirected edges (sym)}", summary["n_undirected_edges_sym"]],
        [r"\textbf{degree (min/avg/max)}", f"{summary['degree_min']:.0f}/{summary['degree_avg']:.2f}/{summary['degree_max']:.0f}"],
        [r"\textbf{$\lambda_2(P)$ (real)}", f"{summary['lambda2_real']:.6f}"],
        [r"\textbf{gap $\gamma=1-\lambda_2$}", f"{summary['spectral_gap_est']:.6f}"],
        [
            r"\textbf{scale $\log(1/\varepsilon)/\gamma$}",
            f"{summary['mixing_lb_scale_logeps_over_gap']:.3f} ($\\varepsilon={summary['eps']}$)",
        ],
    ]
    write_tabular_fragment(
        gen / "cover_graph_summary.tex",
        column_spec="ll",
        header=[r"\textbf{key}", r"\textbf{value}"],
        rows=rows,
        booktabs=True,
    )

    prog.tick(f"done (run_id={run.run_id})")


if __name__ == "__main__":
    main()

