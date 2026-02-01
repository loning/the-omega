#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compute 3D arity-charge / negative-carry / arity-2 trigger spectrum (real-input 40-state kernel).

Outputs:
- artifacts/export/sync_kernel_real_input_40_arity_3d.json (default)
- sections/generated/tab_real_input_40_arity_dirichlet_mertens_333.tex (3x3x3 summary)
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from common_paths import export_dir
from common_phi_fold import Progress

from common_paths import generated_dir

@dataclass(frozen=True)
class KernelEdge:
    src: str
    dst: str
    d: int
    e: int


KERNEL_STATES = [
    "000",
    "001",
    "002",
    "010",
    "100",
    "101",
    "0-12",
    "1-12",
    "01-1",
    "11-1",
]


def build_kernel_edges() -> List[KernelEdge]:
    edges: List[KernelEdge] = []
    for d in (0, 1, 2):
        edges.append(KernelEdge("000", f"00{d}", d, 0))
    for d in (0, 1, 2):
        edges.append(KernelEdge("100", f"00{d}", d, 1))
    edges += [
        KernelEdge("001", "010", 0, 0),
        KernelEdge("001", "100", 1, 0),
        KernelEdge("001", "101", 2, 0),
        KernelEdge("002", "11-1", 0, 0),
        KernelEdge("002", "000", 1, 1),
        KernelEdge("002", "001", 2, 1),
        KernelEdge("010", "100", 0, 0),
        KernelEdge("010", "101", 1, 0),
        KernelEdge("010", "0-12", 2, 1),
        KernelEdge("101", "010", 0, 1),
        KernelEdge("101", "100", 1, 1),
        KernelEdge("101", "101", 2, 1),
        KernelEdge("0-12", "01-1", 0, 0),
        KernelEdge("0-12", "010", 1, 0),
        KernelEdge("0-12", "100", 2, 0),
        KernelEdge("1-12", "01-1", 0, 1),
        KernelEdge("1-12", "010", 1, 1),
        KernelEdge("1-12", "100", 2, 1),
        KernelEdge("01-1", "001", 0, 0),
        KernelEdge("01-1", "002", 1, 0),
        KernelEdge("01-1", "1-12", 2, 0),
        KernelEdge("11-1", "001", 0, 1),
        KernelEdge("11-1", "002", 1, 1),
        KernelEdge("11-1", "1-12", 2, 1),
    ]
    return edges


def build_kernel_map(edges: List[KernelEdge]) -> Dict[Tuple[str, int], Tuple[str, int]]:
    return {(edge.src, edge.d): (edge.dst, edge.e) for edge in edges}


def build_real_input_states() -> List[Tuple[str, int, int]]:
    states: List[Tuple[str, int, int]] = []
    for s in KERNEL_STATES:
        for px in (0, 1):
            for py in (0, 1):
                states.append((s, px, py))
    return states


def parse_triple_values(text: str) -> List[Tuple[int, int, int]]:
    raw = [chunk.strip() for chunk in text.split(",")] if text else []
    triples: List[Tuple[int, int, int]] = []
    for chunk in raw:
        if not chunk:
            continue
        parts = [p.strip() for p in chunk.split("x")]
        if len(parts) != 3:
            raise SystemExit(f"[arity-3d] invalid triple (use axbxc): {chunk}")
        try:
            m1, m2, m3 = (int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError as exc:
            raise SystemExit(f"[arity-3d] invalid triple value: {chunk}") from exc
        if m1 < 2 or m2 < 2 or m3 < 2:
            raise SystemExit(f"[arity-3d] triple entries must be >=2, got {chunk}")
        triples.append((m1, m2, m3))
    if not triples:
        triples = [(3, 3, 3)]
    seen = set()
    out: List[Tuple[int, int, int]] = []
    for t in triples:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def build_weighted_matrix_numeric(
    q: complex,
    r: complex,
    u: complex,
    states: List[Tuple[str, int, int]],
    kernel_map: Dict[Tuple[str, int], Tuple[str, int]],
) -> np.ndarray:
    idx = {state: i for i, state in enumerate(states)}
    n = len(states)
    M = np.zeros((n, n), dtype=complex)
    for s, px, py in states:
        for x in (0, 1):
            if px == 1 and x == 1:
                continue
            for y in (0, 1):
                if py == 1 and y == 1:
                    continue
                d = x + y
                dst_state, e = kernel_map[(s, d)]
                chi = e - (1 if d == 2 else 0)
                nu = 1 if "-" in dst_state else 0
                xi = 1 if d == 2 else 0
                i = idx[(s, px, py)]
                j = idx[(dst_state, x, y)]
                M[i, j] += (q**chi) * (r**nu) * (u**xi)
    return M


def traces_for_qru(
    q: complex,
    r: complex,
    u: complex,
    max_n: int,
    prog: Progress,
    states: List[Tuple[str, int, int]],
    kernel_map: Dict[Tuple[str, int], Tuple[str, int]],
    label: str,
) -> List[complex]:
    M = build_weighted_matrix_numeric(q, r, u, states, kernel_map)
    A = M.copy()
    traces: List[complex] = []
    for n in range(1, max_n + 1):
        if n > 1:
            A = A @ M
        traces.append(np.trace(A))
        prog.tick(f"{label} trace n={n}/{max_n}")
    return traces


def pvals_from_traces(traces: List[complex]) -> List[complex]:
    max_n = len(traces)
    pvals: List[complex] = []
    for n in range(1, max_n + 1):
        s = 0.0 + 0.0j
        for d in range(1, n + 1):
            if n % d == 0:
                s += mobius(d) * traces[n // d - 1]
        pvals.append(s / float(n))
    return pvals


def spectral_radius(B: np.ndarray) -> float:
    vals = np.linalg.eigvals(B)
    return float(np.max(np.abs(vals)))


def mobius(n: int) -> int:
    if n == 1:
        return 1
    mu = 1
    p = 2
    nn = n
    while p * p <= nn:
        if nn % p == 0:
            nn //= p
            if nn % p == 0:
                return 0
            mu = -mu
        p += 1
    if nn > 1:
        mu = -mu
    return mu


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="3D arity/negative/output Dirichlet–Mertens constants")
    parser.add_argument("--mertens-n", type=int, default=200, help="Max n for constants")
    parser.add_argument(
        "--triple-values",
        type=str,
        default="3x3x3,5x5x5",
        help="Comma-separated m1xm2xm3 triples for Dirichlet–Mertens constants",
    )
    parser.add_argument("--no-output", action="store_true", help="Skip writing JSON output")
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Output JSON path (default: artifacts/export/sync_kernel_real_input_40_arity_3d.json)",
    )
    args = parser.parse_args()

    prog = Progress(label="sync-kernel-real-input-arity-3d", every_seconds=20.0)
    edges = build_kernel_edges()
    kernel_map = build_kernel_map(edges)
    states = build_real_input_states()

    phi = (1.0 + 5.0**0.5) / 2.0
    lam = phi * phi
    gamma = 0.5772156649015329
    mertens_n = args.mertens_n

    traces_one = traces_for_qru(1.0 + 0.0j, 1.0 + 0.0j, 1.0 + 0.0j, mertens_n, prog, states, kernel_map, "q=r=u=1")
    p_one = pvals_from_traces(traces_one)
    logM = 0.0
    for n, pn in enumerate(p_one, start=1):
        logM += (pn.real / (lam**n)) - 1.0 / n
    mathsf_M = logM + gamma

    triples = parse_triple_values(args.triple_values)
    triple_keys = [f"{m1}x{m2}x{m3}" for m1, m2, m3 in triples]
    triple_twist_C: Dict[str, Dict[str, Dict[str, float]]] = {}
    triple_class_C: Dict[str, Dict[str, float]] = {}
    triple_rho: Dict[str, Dict[str, float]] = {}
    triple_rho_max: Dict[str, float] = {}

    for m1, m2, m3 in triples:
        omega1 = np.exp(2j * math.pi / m1)
        omega2 = np.exp(2j * math.pi / m2)
        omega3 = np.exp(2j * math.pi / m3)
        twist_constants: Dict[str, Dict[str, float]] = {}
        rho_vals: Dict[str, float] = {}
        for j1 in range(m1):
            q = omega1**j1
            for j2 in range(m2):
                r = omega2**j2
                for j3 in range(m3):
                    if j1 == 0 and j2 == 0 and j3 == 0:
                        continue
                    u = omega3**j3
                    label = f"m={m1}x{m2}x{m3} j={j1},{j2},{j3}"
                    traces = traces_for_qru(q, r, u, mertens_n, prog, states, kernel_map, label)
                    pvals = pvals_from_traces(traces)
                    C = sum(p / (lam**(i + 1)) for i, p in enumerate(pvals))
                    key = f"{j1},{j2},{j3}"
                    twist_constants[key] = {"re": float(C.real), "im": float(C.imag)}
                    rho = spectral_radius(build_weighted_matrix_numeric(q, r, u, states, kernel_map))
                    rho_vals[key] = rho

        denom = float(m1 * m2 * m3)
        class_constants: Dict[str, float] = {}
        for r1 in range(m1):
            for r2 in range(m2):
                for r3 in range(m3):
                    acc = mathsf_M / denom
                    for j1 in range(m1):
                        q = omega1**j1
                        for j2 in range(m2):
                            r = omega2**j2
                            for j3 in range(m3):
                                if j1 == 0 and j2 == 0 and j3 == 0:
                                    continue
                                u = omega3**j3
                                key = f"{j1},{j2},{j3}"
                                phase = (q ** (-r1)) * (r ** (-r2)) * (u ** (-r3))
                                acc += (phase * complex(twist_constants[key]["re"], twist_constants[key]["im"])) / denom
                    class_constants[f"{r1},{r2},{r3}"] = float(acc.real)

        key_triple = f"{m1}x{m2}x{m3}"
        triple_twist_C[key_triple] = twist_constants
        triple_class_C[key_triple] = class_constants
        triple_rho[key_triple] = rho_vals
        triple_rho_max[key_triple] = max(rho_vals.values()) if rho_vals else 0.0

    payload: Dict[str, object] = {
        "chi_def": "chi = e - 1_{d=2}",
        "nu_def": "nu = 1_{t in Q_-}",
        "xi_def": "xi = 1_{d=2}",
        "mertens_n": mertens_n,
        "mathsf_M": mathsf_M,
        "triple_values": triple_keys,
        "triple_twist_C": triple_twist_C,
        "triple_class_C": triple_class_C,
        "triple_rho": triple_rho,
        "triple_rho_max": triple_rho_max,
        "triple_rho_max_ratio": {k: v / lam for k, v in triple_rho_max.items()},
    }

    if not args.no_output:
        out_path = (
            Path(args.output)
            if args.output
            else export_dir() / "sync_kernel_real_input_40_arity_3d.json"
        )
        write_json(out_path, payload)
        print(f"[sync-kernel-real-input-arity-3d] wrote {out_path}", flush=True)

        # Write a LaTeX summary snippet for the (3,3,3) tensor.
        if "3x3x3" in triple_class_C and "3x3x3" in triple_rho_max:
            C = triple_class_C["3x3x3"]
            rho_max = float(triple_rho_max["3x3x3"])
            rho_ratio = float(triple_rho_max["3x3x3"] / lam)

            # Find all twist indices attaining the maximum spectral radius.
            rho_map = triple_rho.get("3x3x3", {})
            if rho_map:
                mx = max(rho_map.values())
                argmax = sorted([k for k, v in rho_map.items() if abs(v - mx) <= 1e-12])
            else:
                argmax = []

            # Marginalize over (b,c) to get chi mod 3 constants.
            marg = []
            for a in range(3):
                s = 0.0
                for b in range(3):
                    for c in range(3):
                        s += float(C[f"{a},{b},{c}"])
                marg.append(s)

            def fmt(x: float) -> str:
                # Stable, reviewer-friendly precision for constants.
                return f"{x:+.8f}".replace("+", "\\phantom{-}")

            def entry(a: int, b: int, c: int) -> str:
                return fmt(float(C[f"{a},{b},{c}"]))

            lines = []
            lines.append("% AUTO-GENERATED by scripts/exp_sync_kernel_real_input_40_arity_3d.py")
            lines.append("% (3,3,3) Dirichlet--Mertens constants tensor for (chi mod 3, N_- mod 3, N_2 mod 3).")
            lines.append("\\paragraph{$((3,3,3))$：三维 Dirichlet--Mertens 常数张量（可复现输出）}")
            lines.append("按 $a=\\chi(\\gamma)\\bmod 3$ 分三张 $3\\times 3$ 切片（行 $b=N_-(\\gamma)\\bmod 3$，列 $c=N_2(\\gamma)\\bmod 3$），常数项为：")
            for a in range(3):
                lines.append("$$")
                lines.append(f"a={a}:\\quad")
                lines.append("\\begin{pmatrix}")
                for b in range(3):
                    row = " & ".join(entry(a, b, c) for c in range(3))
                    if b < 2:
                        lines.append(f"{row}\\\\")
                    else:
                        lines.append(f"{row}")
                lines.append("\\end{pmatrix}")
                lines.append("$$")
            lines.append("\\paragraph{指数级误差：最坏扭曲谱半径比（可复现输出）}")
            lines.append("数值上")
            lines.append("$$")
            lines.append(f"\\rho_{{3,3,3}}\\approx {rho_max:.12f},\\qquad \\frac{{\\rho_{{3,3,3}}}}{{\\lambda}}\\approx {rho_ratio:.12f}.")
            lines.append("$$")
            if argmax:
                joined = ",\\ ".join([f"({t})" for t in argmax])
                lines.append("达到最坏谱半径的非平凡角色索引（$j=(j_1,j_2,j_3)$）为：")
                lines.append("$$")
                lines.append(joined)
                lines.append("$$")
            lines.append("\\paragraph{一维边际：只看 $\\chi\\bmod 3$ 的 Dirichlet--Mertens 常数}")
            lines.append("对 $b,c$ 求和得到 $C_a^{(3)}:=\\sum_{b,c} C^{(3,3,3)}_{a,b,c}$：")
            lines.append("$$")
            lines.append(
                "\\bigl(C_0^{(3)},C_1^{(3)},C_2^{(3)}\\bigr)"
                + f"\\approx\\bigl({marg[0]:+.8f},{marg[1]:+.8f},{marg[2]:+.8f}\\bigr)."
            )
            lines.append("$$")

            tex_path = generated_dir() / "tab_real_input_40_arity_dirichlet_mertens_333.tex"
            tex_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"[sync-kernel-real-input-arity-3d] wrote {tex_path}", flush=True)

    print("[sync-kernel-real-input-arity-3d] done", flush=True)


if __name__ == "__main__":
    main()
