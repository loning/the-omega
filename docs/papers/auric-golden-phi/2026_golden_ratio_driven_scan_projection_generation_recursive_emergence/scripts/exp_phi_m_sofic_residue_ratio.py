#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Residue ratio invariant between intrinsic sofic zeta and its cover zeta for Y_m.

We follow the paper's interface:
  - Build a right Fischer cover (determinize + minimize) with state set S_m and label alphabet X_m.
  - Cover zeta: use the cover adjacency A_m on S_m with edge multiplicities:
        #Fix(σ^n|X_{A_m}) = Tr(A_m^n),   ζ_{X_{A_m}}(z) = 1/det(I - z A_m).
  - Intrinsic sofic zeta: build the "transition semigroup automaton" on partial maps τ_w,
    and then restrict to the accepting subgraph (maps with at least one fixed point) as in the manuscript.
    Its 0–1 adjacency is denoted B_m, and we use:
        #Fix(σ^n|Y_m) = Tr(B_m^n),   ζ_{Y_m}(z) = 1/det(I - z B_m).

For each m we restrict to the reachable entropy-carrying SCC and compute:
  - rho = spectral radius (shared on the exponential scale),
  - residues at the leading pole z* = 1/rho:
        ζ(z) ~ R / (1 - rho z),
  - eta_m = R_int / R_cov (dimensionless).

Outputs:
  - artifacts/export/phi_m_sofic_residue_ratio.json
  - sections/generated/tab_phi_m_sofic_residue_ratio.tex

All output is English-only by repository convention.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from common_paths import export_dir, generated_dir
from common_phi_fold import Progress, fold_m


def _int_to_bits(x: int, m: int) -> List[int]:
    return [(x >> (m - 1 - i)) & 1 for i in range(m)]


def _pack_bits_to_int(bits: List[int], m: int) -> int:
    x = 0
    for b in bits:
        x = (x << 1) | (1 if b else 0)
    return x & ((1 << m) - 1)


def build_fold_map(m: int, prog: Progress) -> List[int]:
    size = 1 << m
    out = [0] * size
    for w in range(size):
        bits = _int_to_bits(w, m)
        folded = fold_m(bits)
        out[w] = _pack_bits_to_int(list(folded), m)
        prog.tick(f"build_fold_map m={m} w={w}/{size}")
    return out


def build_Gm_edges(m: int, fold_map: List[int]) -> Tuple[int, Dict[int, Dict[int, int]]]:
    """Return (num_vertices, transitions) for G_m in packed-int form.

    transitions[v][a] is a bitmask of target vertices for label a.
    """
    nV = 1 if (m <= 1) else (1 << (m - 1))
    maskV = nV - 1
    trans: Dict[int, Dict[int, int]] = {v: {} for v in range(nV)}
    for v in range(nV):
        for b in (0, 1):
            if m <= 1:
                window = b
                tgt = 0
            else:
                window = ((v << 1) | b) & ((1 << m) - 1)
                tgt = ((v << 1) | b) & maskV
            a = fold_map[window]
            d = trans[v]
            d[a] = d.get(a, 0) | (1 << tgt)
    return nV, trans


def determinize(nV: int, trans: Dict[int, Dict[int, int]], prog: Progress) -> Tuple[int, List[Dict[int, int]]]:
    """Determinize by subset construction.

    det[sid][label]=sid' where label is packed m-bit in X_m.
    """
    start_mask = (1 << nV) - 1
    q: deque[int] = deque([start_mask])
    id_of: Dict[int, int] = {start_mask: 0}
    masks: List[int] = [start_mask]
    det: List[Dict[int, int]] = []

    while q:
        S = q.popleft()
        sid = id_of[S]
        while len(det) <= sid:
            det.append({})

        next_by_label: Dict[int, int] = {}
        vv = S
        while vv:
            lsb = vv & -vv
            v = (lsb.bit_length() - 1)
            vv -= lsb
            for a, tgt_mask in trans[v].items():
                next_by_label[a] = next_by_label.get(a, 0) | tgt_mask
        for a, T in next_by_label.items():
            if T not in id_of:
                id_of[T] = len(masks)
                masks.append(T)
                q.append(T)
            det[sid][a] = id_of[T]
        prog.tick(f"determinize nV={nV} states={len(masks)} queue={len(q)}")
    return 0, det


def minimize_right_language(det: List[Dict[int, int]]) -> Tuple[int, List[Dict[int, int]]]:
    """Minimize deterministic partial automaton by right-language equivalence."""
    n = len(det)
    dead = n
    cls = [1] * n + [0]

    changed = True
    while changed:
        changed = False
        sig_to_new: Dict[Tuple[int, Tuple[Tuple[int, int], ...]], int] = {}
        new_cls = [0] * (n + 1)
        for i in range(n + 1):
            acc = 1 if i != dead else 0
            if i == dead:
                items: Tuple[Tuple[int, int], ...] = tuple()
            else:
                items = tuple(sorted((a, cls[j]) for a, j in det[i].items()))
            sig = (acc, items)
            if sig not in sig_to_new:
                sig_to_new[sig] = len(sig_to_new)
            new_cls[i] = sig_to_new[sig]
        if new_cls != cls:
            cls = new_cls
            changed = True

    num_classes = max(cls) + 1
    rep = [-1] * num_classes
    for i in range(n + 1):
        c = cls[i]
        if rep[c] == -1:
            rep[c] = i

    out: List[Dict[int, int]] = [defaultdict(int) for _ in range(num_classes)]
    for c in range(num_classes):
        i = rep[c]
        if i == -1 or i == dead:
            continue
        for a, j in det[i].items():
            out[c][a] = cls[j]
    start_class = cls[0]
    out2 = [dict(d) for d in out]
    return start_class, out2


def _scc_kosaraju(adj: List[List[int]]) -> List[List[int]]:
    n = len(adj)
    radj: List[List[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in adj[i]:
            radj[j].append(i)
    seen = [False] * n
    order: List[int] = []

    def dfs1(v: int) -> None:
        seen[v] = True
        for u in adj[v]:
            if not seen[u]:
                dfs1(u)
        order.append(v)

    for v in range(n):
        if not seen[v]:
            dfs1(v)

    comp = [-1] * n
    comps: List[List[int]] = []

    def dfs2(v: int, cid: int) -> None:
        comp[v] = cid
        comps[cid].append(v)
        for u in radj[v]:
            if comp[u] == -1:
                dfs2(u, cid)

    for v in reversed(order):
        if comp[v] == -1:
            comps.append([])
            dfs2(v, len(comps) - 1)
    return comps


def _spectral_radius(M: np.ndarray) -> float:
    vals = np.linalg.eigvals(M.astype(np.complex128, copy=False))
    return float(max(abs(v) for v in vals))


def _residue_leading_pole(M: np.ndarray, rho: float) -> float:
    vals = np.linalg.eigvals(M.astype(np.complex128, copy=False))
    # Identify the eigenvalue at rho (closest by absolute difference).
    idx = int(np.argmin([abs(v - rho) for v in vals]))
    prod = 1.0 + 0.0j
    for k, lam in enumerate(vals):
        if k == idx:
            continue
        prod *= (1.0 - lam / rho)
    # Residue in ζ(z) ~ R/(1 - rho z) is 1/prod.
    R = 1.0 / prod
    if abs(R.imag) > 1e-8:
        raise RuntimeError(f"Residue not real: {R}")
    return float(R.real)


def _essential_component_mult_adj(start: int, det_min: List[Dict[int, int]]) -> Tuple[List[int], np.ndarray]:
    """Return (states_in_best_scc, multiplicity adjacency matrix B)."""
    n = len(det_min)
    adj_mult: List[Dict[int, int]] = [defaultdict(int) for _ in range(n)]
    adj_simple: List[List[int]] = [[] for _ in range(n)]
    for i in range(n):
        for _, j in det_min[i].items():
            adj_mult[i][j] += 1
    for i in range(n):
        adj_simple[i] = list(adj_mult[i].keys())

    reach = [False] * n
    q: deque[int] = deque([start])
    reach[start] = True
    while q:
        v = q.popleft()
        for u in adj_simple[v]:
            if not reach[u]:
                reach[u] = True
                q.append(u)

    inv = [i for i in range(n) if reach[i]]
    idx_map = {i: k for k, i in enumerate(inv)}
    adj_r: List[List[int]] = [[] for _ in inv]
    for i in inv:
        ii = idx_map[i]
        adj_r[ii] = [idx_map[j] for j in adj_simple[i] if reach[j]]
    comps = _scc_kosaraju(adj_r)

    best_rho = 0.0
    best_comp: List[int] = []
    for comp in comps:
        if len(comp) == 1 and (comp[0] not in adj_r[comp[0]]):
            continue
        k = len(comp)
        pos = {comp[i]: i for i in range(k)}
        M = np.zeros((k, k), dtype=np.float64)
        comp_set = set(comp)
        for u in comp:
            iu = pos[u]
            orig_u = inv[u]
            for orig_v, c in adj_mult[orig_u].items():
                if reach[orig_v]:
                    v = idx_map[orig_v]
                    if v in comp_set:
                        iv = pos[v]
                        M[iu, iv] += float(c)
        rho = _spectral_radius(M)
        if rho > best_rho:
            best_rho = rho
            best_comp = comp

    states = [inv[u] for u in best_comp]
    k = len(best_comp)
    pos = {best_comp[i]: i for i in range(k)}
    B = np.zeros((k, k), dtype=np.int64)
    comp_set = set(best_comp)
    for u in best_comp:
        iu = pos[u]
        orig_u = inv[u]
        for orig_v, c in adj_mult[orig_u].items():
            if reach[orig_v]:
                v = idx_map[orig_v]
                if v in comp_set:
                    iv = pos[v]
                    B[iu, iv] += int(c)
    return states, B


def _build_cover_A_on_scc(states: List[int], det_min: List[Dict[int, int]]) -> np.ndarray:
    """Cover adjacency A on the Fischer cover SCC (edge multiplicities)."""
    k = len(states)
    pos = {states[i]: i for i in range(k)}
    state_set = set(states)
    A = np.zeros((k, k), dtype=np.int64)
    for s in states:
        i = pos[s]
        for _, t in det_min[s].items():
            if t in state_set:
                j = pos[t]
                A[i, j] += 1
    return A


def _build_intrinsic_B_transition_semigroup(det_min: List[Dict[int, int]], prog: Progress) -> np.ndarray:
    """Build 0-1 adjacency B on accepting partial maps τ_w (having a fixed point)."""
    S = len(det_min)
    # Alphabet: all labels that appear as outgoing edges.
    alphabet: List[int] = sorted({a for s in range(S) for a in det_min[s].keys()})

    # Generators as partial maps on S, encoded on {0..S} where 0 means undefined, i+1 means i.
    gens: List[np.ndarray] = []
    for a in alphabet:
        g = np.zeros((S + 1,), dtype=np.int32)
        for s in range(S):
            t = det_min[s].get(a, None)
            g[s + 1] = 0 if t is None else (int(t) + 1)
        gens.append(g)

    idx = np.arange(1, S + 1, dtype=np.int32)  # fixed point test vector

    def is_accepting(tau: np.ndarray) -> bool:
        # tau[i] == i+1 indicates tau fixes i and is defined there.
        return bool(np.any(tau == idx))

    def compose(gen: np.ndarray, tau: np.ndarray) -> np.ndarray:
        # (gen ∘ tau)(i) where 0 encodes undefined.
        return gen[tau]

    # BFS on accepting states only.
    tau0 = np.arange(1, S + 1, dtype=np.int32)  # identity (total)
    if not is_accepting(tau0):
        raise RuntimeError("Identity should be accepting.")

    key0 = tau0.tobytes()
    id_of: Dict[bytes, int] = {key0: 0}
    taus: List[np.ndarray] = [tau0]
    q: deque[int] = deque([0])
    edges: List[List[int]] = []

    while q:
        u = q.popleft()
        while len(edges) <= u:
            edges.append([])
        tau = taus[u]

        for gi, g in enumerate(gens):
            nxt = compose(g, tau)
            if not is_accepting(nxt):
                continue
            k = nxt.tobytes()
            v = id_of.get(k)
            if v is None:
                v = len(taus)
                id_of[k] = v
                taus.append(nxt)
                q.append(v)
            edges[u].append(v)

        prog.tick(f"build_B accepting_states={len(taus)} queue={len(q)} S={S} |X|={len(alphabet)}")

    n = len(taus)
    B = np.zeros((n, n), dtype=np.int64)
    for u in range(n):
        for v in edges[u]:
            B[u, v] = 1
    return B


@dataclass(frozen=True)
class Row:
    m: int
    S_states_total: int
    B_dim: int
    A_dim: int
    rho: float
    R_int: float
    R_cov: float
    eta: float
    lower_bound_1_over_S: float


def write_table_tex(path: str, rows: List[Row]) -> None:
    lines: List[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append(
        "\\caption{Residue ratio invariant $\\eta_m=R^{\\mathrm{int}}_m/R^{\\mathrm{cov}}_m$ "
        "between the intrinsic sofic zeta $\\zeta_{Y_m}(z)=1/\\det(I-zB_m)$ and the cover zeta "
        "$\\zeta_{X_{A_m}}(z)=1/\\det(I-zA_m)$. "
        "We restrict to the entropy-carrying SCC and compute the leading pole residue in the form "
        "$\\zeta(z)\\sim R/(1-\\rho z)$ at $z_\\star=1/\\rho$.}"
    )
    lines.append("\\label{tab:phi_m_sofic_residue_ratio}")
    lines.append("\\begin{tabular}{r r r r r r r}")
    lines.append("\\toprule")
    lines.append("$m$ & $|\\mathcal{S}_m|$ & $\\dim B$ & $\\dim A$ & $\\rho$ & $\\eta_m$ & $1/|\\mathcal{S}_m|$\\\\")
    lines.append("\\midrule")
    for r in rows:
        lines.append(
            f"{r.m} & {r.S_states_total} & {r.B_dim} & {r.A_dim} & {r.rho:.12f} & {r.eta:.12f} & {r.lower_bound_1_over_S:.3e}\\\\"
        )
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute residue ratio between intrinsic and cover zetas for Y_m.")
    parser.add_argument("--m-list", type=str, default="2,3,4,5,6,7,8")
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "phi_m_sofic_residue_ratio.json"),
    )
    parser.add_argument(
        "--tex-out",
        type=str,
        default=str(generated_dir() / "tab_phi_m_sofic_residue_ratio.tex"),
    )
    args = parser.parse_args()

    ms = [int(x) for x in str(args.m_list).split(",") if x.strip()]
    prog = Progress("phi-m-residue", every_seconds=20.0)

    rows: List[Row] = []
    for m in ms:
        fold_map = build_fold_map(m, prog)
        nV, trans = build_Gm_edges(m, fold_map)
        _, det = determinize(nV, trans, prog)
        start_min, det_min = minimize_right_language(det)

        # Cover: restrict Fischer cover to its entropy-carrying SCC, then build A on that SCC.
        states_scc, A_scc = _essential_component_mult_adj(start_min, det_min)
        A = _build_cover_A_on_scc(states_scc, det_min)
        # Intrinsic: build transition semigroup automaton adjacency and restrict to its best SCC.
        B_full = _build_intrinsic_B_transition_semigroup(det_min, prog)
        # Extract the best SCC for B_full by reusing the mult-adj SCC picker on a "fake" det list.
        # Here we treat each 1 in B_full as a distinct label-less edge (multiplicity 1).
        B_det: List[Dict[int, int]] = []
        for i in range(int(B_full.shape[0])):
            drow: Dict[int, int] = {}
            for j in np.nonzero(B_full[i, :])[0]:
                # Use j as a unique "label" to ensure multiplicity adjacency matches 0-1 adjacency.
                drow[int(j)] = int(j)
            B_det.append(drow)
        states_B_scc, B = _essential_component_mult_adj(0, B_det)
        # B returned is multiplicity adjacency on SCC of size dim(B); in this construction it matches 0-1.

        rhoA = _spectral_radius(A.astype(np.float64))
        rhoB = _spectral_radius(B.astype(np.float64))
        rho = rhoB
        if abs(rhoA - rhoB) / max(1e-12, rhoB) > 1e-6:
            # The manuscript states the leading pole moduli agree, but for small m there can be
            # reducibility artifacts. We still report both by taking rhoB as intrinsic scale.
            print(f"[phi-m-residue] WARN rho mismatch m={m}: rhoA={rhoA} rhoB={rhoB}", flush=True)

        R_cov = _residue_leading_pole(A.astype(np.float64), rho=rhoA)
        R_int = _residue_leading_pole(B.astype(np.float64), rho=rhoB)
        eta = R_int / R_cov

        S_total = len(det_min)
        rows.append(
            Row(
                m=m,
                S_states_total=S_total,
                B_dim=int(B.shape[0]),
                A_dim=int(A.shape[0]),
                rho=float(rho),
                R_int=R_int,
                R_cov=R_cov,
                eta=eta,
                lower_bound_1_over_S=1.0 / float(S_total) if S_total > 0 else float("nan"),
            )
        )
        print(
            f"[phi-m-residue] m={m} |S|={S_total} dimB={B.shape[0]} dimA={A.shape[0]} rhoB={rhoB:.6g} rhoA={rhoA:.6g} eta={eta:.6g}",
            flush=True,
        )

    jout = export_dir() / "phi_m_sofic_residue_ratio.json"
    Path(jout).parent.mkdir(parents=True, exist_ok=True)
    Path(jout).write_text(
        json.dumps({"rows": [asdict(r) for r in rows]}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"[phi-m-residue] wrote {jout}", flush=True)

    write_table_tex(str(args.tex_out), rows)
    print(f"[phi-m-residue] wrote {args.tex_out}", flush=True)


if __name__ == "__main__":
    main()

