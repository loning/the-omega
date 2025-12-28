#!/usr/bin/env python3
"""
CAP-II reproducibility script:
Explicit microscopic end-to-end demo (interaction graph + task family + scheduler -> kappa -> coarse-grained lapse -> WS recovery).

Microscopic model (toy but explicit):
  - Interaction graph: a weighted undirected graph given by edges (u,v,w) with tick costs w>0.
  - Local task family: for each node i, the "clock task" requires interacting with a reference node u_ref=0.
  - Scheduler/compilation depth: for this toy, the minimal schedule cost is taken to be the weighted shortest-path distance
    from u_ref to i, plus a unit local cost:
        kappa_ratio(i) := 1 + dist(u_ref, i).
    This is auditable and exactly computable from the graph.

Target lapse profile:
  - We compare the graph-induced lapse N_graph(i)=1/kappa_ratio(i) (normalized so N=1 at the reference)
    against the normalized Schwarzschild lapse:
        N_Schw(r)/N_Schw(r_ref) = sqrt(1-2GM/r) / sqrt(1-2GM/r_ref).

Coarse-graining:
  - Given node radii r_i, we form a Gaussian-kernel coarse-grained kappa_ratio_eps(r_i) and lapse N_eps=1/kappa_ratio_eps.

WS interface:
  - For each location, simulate a 1-channel unitary Breit--Wigner scatterer with linewidth chosen so that
        tau_WS(E0) = kappa(i) * tau0
    in the ideal limit, using gamma = 4*hbar/(kappa*tau0).
  - Estimate dS/dE by central difference and compute Q(E0) and kappa_WS=tau_WS/tau0.
  - Report N_WS inferred from kappa_WS ratios.

Outputs:
  - LaTeX table rows and a one-row summary of errors.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import heapq
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Node:
    idx: int
    r: float


@dataclass(frozen=True)
class Edge:
    u: int
    v: int
    w: float


def _default_out_rows() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent / "sections" / "generated" / "demo_microscopic_chain_rows.tex"


def _default_out_metrics() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent / "sections" / "generated" / "demo_microscopic_chain_metrics.tex"


def read_nodes(path: Path) -> list[Node]:
    nodes: list[Node] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        if rd.fieldnames is None:
            raise ValueError("nodes CSV must have a header")
        for rec in rd:
            idx = int(rec.get("idx", "").strip() or rec.get("u", "").strip())
            r = float(rec.get("r", "").strip())
            nodes.append(Node(idx=idx, r=r))
    if not nodes:
        raise ValueError("no nodes read")
    nodes.sort(key=lambda n: n.idx)
    return nodes


def read_edges(path: Path) -> list[Edge]:
    edges: list[Edge] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        if rd.fieldnames is None:
            raise ValueError("edges CSV must have a header")
        for rec in rd:
            u = int(rec["u"])
            v = int(rec["v"])
            w = float(rec["w"])
            if w <= 0.0:
                raise ValueError("edge weight must be positive")
            edges.append(Edge(u=u, v=v, w=w))
    if not edges:
        raise ValueError("no edges read")
    return edges


def build_adj(n_nodes: int, edges: list[Edge]) -> list[list[tuple[int, float]]]:
    adj: list[list[tuple[int, float]]] = [[] for _ in range(n_nodes)]
    for e in edges:
        if e.u < 0 or e.v < 0 or e.u >= n_nodes or e.v >= n_nodes:
            raise ValueError("edge endpoints out of range")
        adj[e.u].append((e.v, e.w))
        adj[e.v].append((e.u, e.w))
    return adj


def dijkstra(adj: list[list[tuple[int, float]]], src: int) -> list[float]:
    n = len(adj)
    dist = [math.inf] * n
    dist[src] = 0.0
    pq: list[tuple[float, int]] = [(0.0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d != dist[u]:
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist


def gaussian_kernel(x: float) -> float:
    return math.exp(-0.5 * x * x)


def coarse_grain(r: list[float], y: list[float], eps: float) -> list[float]:
    if eps <= 0.0:
        raise ValueError("eps must be positive")
    out: list[float] = []
    for i, ri in enumerate(r):
        num = 0.0
        den = 0.0
        for rj, yj in zip(r, y):
            w = gaussian_kernel((ri - rj) / eps)
            num += w * yj
            den += w
        out.append(num / den if den > 0.0 else y[i])
    return out


def S_breit_wigner(E: float, E0: float, gamma: float) -> complex:
    z = E - E0
    a = 0.5 * gamma
    return complex(z, -a) / complex(z, a)


def add_phase_noise(S: complex, rng: random.Random, sigma_phase: float) -> complex:
    if sigma_phase <= 0.0:
        return S
    phi = rng.gauss(0.0, sigma_phase)
    return S * complex(math.cos(phi), math.sin(phi))


def dS_dE_central(E: float, E0: float, gamma: float, dE: float, rng: random.Random, sigma_phase: float) -> complex:
    Sp = add_phase_noise(S_breit_wigner(E + dE, E0, gamma), rng, sigma_phase)
    Sm = add_phase_noise(S_breit_wigner(E - dE, E0, gamma), rng, sigma_phase)
    return (Sp - Sm) / (2.0 * dE)


def rmse(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / float(len(a)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nodes_csv", type=Path, default=Path("data/demo_chain_nodes.csv"))
    parser.add_argument("--edges_csv", type=Path, default=Path("data/demo_chain_edges.csv"))
    parser.add_argument("--out_rows", type=Path, default=_default_out_rows())
    parser.add_argument("--out_metrics", type=Path, default=_default_out_metrics())

    parser.add_argument("--GM", type=float, default=1.0)
    parser.add_argument("--hbar", type=float, default=1.0)
    parser.add_argument("--tau0", type=float, default=1.0)
    parser.add_argument("--E0", type=float, default=0.0)
    parser.add_argument("--dE", type=float, default=1.0e-6)
    parser.add_argument(
        "--ws_mode",
        choices=["linewidth", "derivative"],
        default="linewidth",
        help="WS inference mode: linewidth (robust) or derivative (sensitive to differentiation noise).",
    )
    parser.add_argument(
        "--sigma_rel_gamma",
        type=float,
        default=1.0e-3,
        help="Relative stddev for synthetic linewidth measurement error (gamma_meas = gamma*(1+noise)).",
    )
    parser.add_argument(
        "--sigma_phase",
        type=float,
        default=0.0,
        help="Phase-noise stddev (radians) applied to sampled S(E) points in derivative mode.",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--eps_r", type=float, default=50.0, help="Gaussian coarse-graining width in r-units.")
    args = parser.parse_args()

    nodes = read_nodes(args.nodes_csv)
    edges = read_edges(args.edges_csv)
    n = len(nodes)
    adj = build_adj(n, edges)
    dist = dijkstra(adj, src=0)
    if any(not math.isfinite(d) for d in dist):
        raise ValueError("graph appears disconnected from reference node 0")

    r = [nd.r for nd in nodes]
    r_ref = r[0]
    # Compilation depth proxy (dimensionless ratio), by definition for this toy clock-task family:
    kappa_ratio = [1.0 + d for d in dist]
    N_graph = [1.0 / kr for kr in kappa_ratio]

    # Target normalized Schwarzschild lapse
    def N_schw_norm(ri: float) -> float:
        return math.sqrt(1.0 - 2.0 * args.GM / ri) / math.sqrt(1.0 - 2.0 * args.GM / r_ref)

    N_target = [N_schw_norm(ri) for ri in r]

    # Coarse-grained representative
    kappa_ratio_eps = coarse_grain(r, kappa_ratio, args.eps_r)
    N_eps = [1.0 / kr for kr in kappa_ratio_eps]

    # WS inference
    rng = random.Random(args.seed)
    kappa_ws: list[float] = []
    for kr in kappa_ratio:
        gamma_true = 4.0 * args.hbar / (kr * args.tau0)
        if args.ws_mode == "linewidth":
            # Robust interface: infer kappa from a linewidth measurement with stated relative error.
            if args.sigma_rel_gamma < 0.0:
                raise ValueError("sigma_rel_gamma must be nonnegative")
            gamma_meas = gamma_true * (1.0 + rng.gauss(0.0, args.sigma_rel_gamma))
            if gamma_meas <= 0.0:
                # rare with small sigma; fall back to gamma_true to avoid sign pathologies
                gamma_meas = gamma_true
            tau_ws = 4.0 * args.hbar / gamma_meas
            kappa_ws.append(tau_ws / args.tau0)
        else:
            # Derivative interface (sensitive): infer tau_WS from numerical differentiation of S(E).
            S0 = add_phase_noise(S_breit_wigner(args.E0, args.E0, gamma_true), rng, args.sigma_phase)
            dS = dS_dE_central(args.E0, args.E0, gamma_true, args.dE, rng, args.sigma_phase)
            Q = (-1j) * args.hbar * (S0.conjugate() * dS)
            tau_ws = Q.real
            kappa_ws.append(tau_ws / args.tau0)

    kappa_ws0 = kappa_ws[0]
    kappa_ratio_ws = [kw / kappa_ws0 for kw in kappa_ws]
    N_ws = [1.0 / kr for kr in kappa_ratio_ws]

    rows = []
    rel_err_eps = []
    rel_err_ws = []
    for ri, Nt, Ne, Nws in zip(r, N_target, N_eps, N_ws):
        e_eps = abs(Ne - Nt) / abs(Nt)
        e_ws = abs(Nws - Nt) / abs(Nt)
        rel_err_eps.append(e_eps)
        rel_err_ws.append(e_ws)
        rows.append(f"{ri:.6g} & {Nt:.8f} & {Ne:.8f} & {Nws:.8f} & {e_eps:.2e} & {e_ws:.2e} \\\\")

    rmse_eps = rmse(N_eps, N_target)
    rmse_ws = rmse(N_ws, N_target)
    out_rows: Path = args.out_rows
    out_rows.parent.mkdir(parents=True, exist_ok=True)
    out_rows.write_text("\n".join(rows) + "\n", encoding="utf-8")

    out_metrics: Path = args.out_metrics
    out_metrics.parent.mkdir(parents=True, exist_ok=True)
    out_metrics.write_text(
        f"{n} & {args.eps_r:.6g} & {args.ws_mode} & {args.sigma_rel_gamma:.2e} & {rmse_eps:.3e} & {rmse_ws:.3e} & {max(rel_err_ws):.3e} \\\\\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()


