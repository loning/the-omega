#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compute arity-charge primitive spectrum for real-input 40-state kernel.

Outputs:
- artifacts/export/sync_kernel_real_input_40_arity.json (default)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from common_paths import export_dir
from common_phi_fold import Progress


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


def poly_add(a: Dict[int, int], b: Dict[int, int]) -> Dict[int, int]:
    out = dict(a)
    for exp, coeff in b.items():
        out[exp] = out.get(exp, 0) + coeff
        if out[exp] == 0:
            del out[exp]
    return out


def poly_mul(a: Dict[int, int], b: Dict[int, int]) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for exp_a, coeff_a in a.items():
        for exp_b, coeff_b in b.items():
            exp = exp_a + exp_b
            out[exp] = out.get(exp, 0) + coeff_a * coeff_b
    return out


def poly_scale_exponent(a: Dict[int, int], factor: int) -> Dict[int, int]:
    return {exp * factor: coeff for exp, coeff in a.items()}


def poly_to_string(poly: Dict[int, int]) -> str:
    if not poly:
        return "0"
    terms: List[str] = []
    for exp in sorted(poly.keys(), reverse=True):
        coeff = poly[exp]
        if exp == 0:
            term = str(coeff)
        elif exp == 1:
            term = "q" if coeff == 1 else f"{coeff}q"
        else:
            term = f"q^{exp}" if coeff == 1 else f"{coeff}q^{exp}"
        terms.append(term)
    return " + ".join(terms)


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


def build_weighted_matrix(
    states: List[Tuple[str, int, int]],
    kernel_map: Dict[Tuple[str, int], Tuple[str, int]],
) -> List[List[Dict[int, int]]]:
    idx = {state: i for i, state in enumerate(states)}
    n = len(states)
    M: List[List[Dict[int, int]]] = [[{} for _ in range(n)] for _ in range(n)]
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
                i = idx[(s, px, py)]
                j = idx[(dst_state, x, y)]
                M[i][j] = poly_add(M[i][j], {chi: 1})
    return M


def mat_mul(
    A: List[List[Dict[int, int]]],
    B: List[List[Dict[int, int]]],
) -> List[List[Dict[int, int]]]:
    n = len(A)
    res: List[List[Dict[int, int]]] = [[{} for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for k in range(n):
            if not A[i][k]:
                continue
            for j in range(n):
                if not B[k][j]:
                    continue
                res[i][j] = poly_add(res[i][j], poly_mul(A[i][k], B[k][j]))
    return res


def mat_trace(A: List[List[Dict[int, int]]]) -> Dict[int, int]:
    poly: Dict[int, int] = {}
    for i in range(len(A)):
        poly = poly_add(poly, A[i][i])
    return poly


def compute_c_and_P(
    max_n: int,
    prog: Progress,
    states: List[Tuple[str, int, int]],
    kernel_map: Dict[Tuple[str, int], Tuple[str, int]],
) -> Tuple[List[Dict[int, int]], List[Dict[int, int]]]:
    M = build_weighted_matrix(states, kernel_map)
    c: List[Dict[int, int]] = [None] * (max_n + 1)  # type: ignore[assignment]
    A = M
    for n in range(1, max_n + 1):
        if n > 1:
            A = mat_mul(A, M)
        c[n] = mat_trace(A)
        prog.tick(f"trace n={n}/{max_n}")

    P: List[Dict[int, int]] = [None] * (max_n + 1)  # type: ignore[assignment]
    for n in range(1, max_n + 1):
        poly: Dict[int, int] = {}
        for d in range(1, n + 1):
            if n % d != 0:
                continue
            mu = mobius(d)
            cd = poly_scale_exponent(c[n // d], d)
            if mu == 1:
                poly = poly_add(poly, cd)
            elif mu == -1:
                poly = poly_add(poly, {exp: -coeff for exp, coeff in cd.items()})
        # divide by n
        for exp, coeff in list(poly.items()):
            if coeff % n != 0:
                raise ValueError(f"Non-integer P_n coefficient at n={n}, exp={exp}")
            poly[exp] = coeff // n
            if poly[exp] == 0:
                del poly[exp]
        P[n] = poly
    return c, P


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Arity-charge primitive spectrum for real-input kernel")
    parser.add_argument("--max-n", type=int, default=10, help="Max n for c_n and P_n")
    parser.add_argument("--no-output", action="store_true", help="Skip writing JSON output")
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Output JSON path (default: artifacts/export/sync_kernel_real_input_40_arity.json)",
    )
    args = parser.parse_args()

    prog = Progress(label="sync-kernel-real-input-arity", every_seconds=20.0)
    edges = build_kernel_edges()
    kernel_map = build_kernel_map(edges)
    states = build_real_input_states()

    c, P = compute_c_and_P(args.max_n, prog, states, kernel_map)

    c_polys = [poly_to_string(c[n]) for n in range(1, args.max_n + 1)]
    P_polys = [poly_to_string(P[n]) for n in range(1, args.max_n + 1)]

    # p_n = P_n(1)
    p_vals = [sum(P[n].values()) for n in range(1, args.max_n + 1)]

    payload: Dict[str, object] = {
        "chi_def": "chi = e - 1_{d=2}",
        "max_n": args.max_n,
        "c_n_polys": c_polys,
        "P_n_polys": P_polys,
        "P_n_coeffs": [
            {str(exp): coeff for exp, coeff in P[n].items()} for n in range(1, args.max_n + 1)
        ],
        "p_n": p_vals,
    }

    if not args.no_output:
        out_path = (
            Path(args.output)
            if args.output
            else export_dir() / "sync_kernel_real_input_40_arity.json"
        )
        write_json(out_path, payload)
        print(f"[sync-kernel-real-input-arity] wrote {out_path}", flush=True)

    print(f"[sync-kernel-real-input-arity] P_1(q)={P_polys[0]}", flush=True)
    print(f"[sync-kernel-real-input-arity] P_2(q)={P_polys[1]}", flush=True)
    print("[sync-kernel-real-input-arity] done", flush=True)


if __name__ == "__main__":
    main()
