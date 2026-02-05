#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Closed-form package for the arity-charge weighting on the real-input 40-state kernel.

We implement an auditable certificate for:
  (A) A 0/1 coboundary normal form on the essential 20-state core:
        g(e) := chi(e) + V(dst) - V(src) in {0,1} for every allowed edge in the core.
  (B) The zero-charge subgraph zeta/determinant closed form for the g=0 edges.
  (C) A fully explicit two-variable determinant factorization:
        det(I - z M(q)) = (1+z)(1-q z^2) Q7(z,q),
      with Q7 given explicitly, hence an algebraic pressure curve of degree 7.
  (D) Closed-form cumulants at q=1 (theta=0): mean and variance in Q(sqrt(5)).
  (E) A residue constant formula:
        C(q) = lambda(q)^9 / ((lambda(q)+1)(lambda(q)^2-q) * d/dLambda P7(lambda(q),q)).

Outputs (default):
  - artifacts/export/sync_kernel_real_input_40_arity_charge_closed_form.json
  - sections/generated/eq_real_input_40_arity_charge_det_closed.tex
  - sections/generated/eq_real_input_40_arity_charge_zero_charge_zeta.tex
  - sections/generated/eq_real_input_40_arity_charge_cumulants_closed.tex

All code is English-only by repository convention.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import sympy as sp

from common_paths import export_dir, generated_dir
from common_phi_fold import Progress
from exp_sync_kernel_real_input_40 import (
    build_kernel_edges,
    build_kernel_map,
    build_real_input_matrix_int,
    build_real_input_states,
)


State = Tuple[str, int, int]  # (sync_state, px, py)


def _adj_list_from_matrix(M: List[List[int]]) -> List[List[int]]:
    n = len(M)
    adj: List[List[int]] = [[] for _ in range(n)]
    for i in range(n):
        row = M[i]
        outs: List[int] = []
        for j in range(n):
            if row[j] != 0:
                outs.append(j)
        adj[i] = outs
    return adj


def _scc_kosaraju(adj: List[List[int]]) -> List[List[int]]:
    n = len(adj)
    radj: List[List[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in adj[i]:
            radj[j].append(i)

    seen = [False] * n
    order: List[int] = []

    def dfs1(v: int) -> None:
        stack = [(v, 0)]
        seen[v] = True
        while stack:
            x, it = stack[-1]
            if it < len(adj[x]):
                y = adj[x][it]
                stack[-1] = (x, it + 1)
                if not seen[y]:
                    seen[y] = True
                    stack.append((y, 0))
            else:
                order.append(x)
                stack.pop()

    for v in range(n):
        if not seen[v]:
            dfs1(v)

    comp_id = [-1] * n
    comps: List[List[int]] = []

    def dfs2(v: int, cid: int) -> None:
        stack = [v]
        comp_id[v] = cid
        cur: List[int] = []
        while stack:
            x = stack.pop()
            cur.append(x)
            for y in radj[x]:
                if comp_id[y] == -1:
                    comp_id[y] = cid
                    stack.append(y)
        comps.append(cur)

    for v in reversed(order):
        if comp_id[v] == -1:
            dfs2(v, len(comps))

    return comps


def _essential_scc(adj: List[List[int]]) -> List[int]:
    comps = _scc_kosaraju(adj)
    n = len(adj)
    comp_of = [-1] * n
    for cid, vs in enumerate(comps):
        for v in vs:
            comp_of[v] = cid

    out_to_other = [False] * len(comps)
    for v in range(n):
        c = comp_of[v]
        for w in adj[v]:
            if comp_of[w] != c:
                out_to_other[c] = True
                break

    essential = [
        cid for cid in range(len(comps)) if not out_to_other[cid] and len(comps[cid]) > 1
    ]
    if len(essential) != 1:
        raise RuntimeError(
            f"expected unique essential SCC, got {[(cid, len(comps[cid])) for cid in essential]}"
        )
    return sorted(comps[essential[0]])


def _submatrix(M: List[List[int]], idx: List[int]) -> List[List[int]]:
    return [[M[i][j] for j in idx] for i in idx]


def _V_certificate(core_states: Sequence[State]) -> Dict[State, int]:
    # V=1 on four explicit essential-core states, else 0.
    V: Dict[State, int] = {st: 0 for st in core_states}
    ones = [
        ("1-12", 1, 1),  # 1 \bar{1} 2
        ("101", 1, 1),
        ("002", 1, 1),
        ("11-1", 0, 0),  # 11 \bar{1}
    ]
    for st in ones:
        if st not in V:
            raise RuntimeError(f"V-certificate state not in essential core: {st}")
        V[st] = 1
    return V


@dataclass(frozen=True)
class CoboundaryAudit:
    essential_core_size: int
    edges_in_core: int
    edges_g0: int
    edges_g1: int
    g_min: int
    g_max: int
    chi_min: int
    chi_max: int
    V_ones: List[State]


def _build_g_matrices_and_audit(
    *,
    core_states: List[State],
    kernel_map: Dict[Tuple[str, int], Tuple[str, int]],
    prog: Progress,
) -> Tuple[List[List[int]], List[List[int]], CoboundaryAudit]:
    n = len(core_states)
    core_idx = {st: i for i, st in enumerate(core_states)}
    V = _V_certificate(core_states)

    M0 = [[0] * n for _ in range(n)]  # g=0 edges
    M1 = [[0] * n for _ in range(n)]  # g=1 edges

    edges = 0
    edges_g0 = 0
    edges_g1 = 0
    g_min = 10
    g_max = -10
    chi_min = 10
    chi_max = -10

    for k, (s, px, py) in enumerate(core_states, start=1):
        i = core_idx[(s, px, py)]
        for x in (0, 1):
            if px == 1 and x == 1:
                continue
            for y in (0, 1):
                if py == 1 and y == 1:
                    continue
                d = x + y
                dst_s, e = kernel_map[(s, d)]
                dst_state = (dst_s, x, y)
                if dst_state not in core_idx:
                    raise RuntimeError(
                        f"edge from core leaves core (unexpected): {(s,px,py)} -> {dst_state}"
                    )
                j = core_idx[dst_state]
                chi = int(e) - (1 if d == 2 else 0)
                g = int(chi + V[dst_state] - V[(s, px, py)])
                edges += 1
                g_min = min(g_min, g)
                g_max = max(g_max, g)
                chi_min = min(chi_min, chi)
                chi_max = max(chi_max, chi)
                if g not in (0, 1):
                    raise RuntimeError(
                        f"coboundary certificate failed: g={g} for edge {(s,px,py)} -> {dst_state} "
                        f"(d={d}, e={e}, chi={chi}, Vsrc={V[(s,px,py)]}, Vdst={V[dst_state]})"
                    )
                if g == 0:
                    M0[i][j] += 1
                    edges_g0 += 1
                else:
                    M1[i][j] += 1
                    edges_g1 += 1
        prog.tick(f"core edge audit {k}/{n}")

    V_ones = [st for st in core_states if V[st] == 1]
    audit = CoboundaryAudit(
        essential_core_size=n,
        edges_in_core=edges,
        edges_g0=edges_g0,
        edges_g1=edges_g1,
        g_min=g_min,
        g_max=g_max,
        chi_min=chi_min,
        chi_max=chi_max,
        V_ones=V_ones,
    )
    return M0, M1, audit


def _Q7(z: sp.Symbol, q: sp.Symbol) -> sp.Expr:
    # Q7(z,q) as in the closed form package.
    return sp.expand(
        1
        - 2 * z
        + (1 - 5 * q) * z**2
        + 6 * q * z**3
        + (-1 - 3 * q + 6 * q**2) * z**4
        + (1 - q - 4 * q**2) * z**5
        + (-3 * q + 4 * q**2) * z**6
        + (q - q**2) * z**7
    )


def _P7(L: sp.Symbol, q: sp.Symbol) -> sp.Expr:
    # P7(L,q) = L^7 Q7(1/L,q)
    z = sp.Symbol("z")
    Q = _Q7(z, q)
    return sp.expand(L**7 * Q.subs(z, 1 / L))


def _delta_closed(z: sp.Symbol, q: sp.Symbol) -> sp.Expr:
    return sp.expand((1 + z) * (1 - q * z**2) * _Q7(z, q))


def _det_poly_z(M: sp.Matrix, z: sp.Symbol) -> sp.Expr:
    return sp.expand((sp.eye(M.rows) - z * M).det())


def _write_tex_det_closed(path: Path) -> None:
    z, q, L = sp.symbols("z q Lambda")
    Q7 = sp.expand(_Q7(z, q))
    P7 = sp.expand(_P7(L, q))

    def poly_in_var(expr: sp.Expr, var: sp.Symbol, deg: int) -> str:
        poly = sp.Poly(sp.expand(expr), var)
        terms: List[str] = []

        def monomial(k: int) -> str:
            if k == 1:
                return sp.latex(var)
            return sp.latex(var) + f"^{{{k}}}"

        def coeff_times_monomial(coeff: sp.Expr, k: int) -> str:
            if k == 0:
                return sp.latex(coeff)
            m = monomial(k)
            if coeff == 1:
                return m
            if coeff == -1:
                return "-" + m
            ctex = sp.latex(coeff)
            if isinstance(coeff, sp.Add):
                ctex = f"\\left({ctex}\\right)"
            return ctex + "\\," + m

        for k in range(0, deg + 1):
            coeff = sp.simplify(poly.coeff_monomial(var**k))
            if coeff == 0:
                continue
            terms.append(coeff_times_monomial(coeff, k))
        # Ensure constant-first order in display:
        return " + ".join(terms).replace("+ -", "- ")

    lines: List[str] = []
    lines.append("% AUTO-GENERATED by scripts/exp_sync_kernel_real_input_40_arity_charge_closed_form.py")
    lines.append("\\[")
    lines.append("\\begin{aligned}")
    lines.append(
        "\\det(I-zM(q))"
        "=(1+z)(1-qz^2)\\,Q_7(z,q),"
    )
    lines.append("\\\\")
    lines.append("Q_7(z,q)&=" + poly_in_var(Q7, z, 7) + ".")
    lines.append("\\\\[2pt]")
    lines.append(
        "\\det(\\Lambda I-M(q))"
        "=\\Lambda^{10}(\\Lambda+1)(\\Lambda^2-q)\\,P_7(\\Lambda,q),"
    )
    lines.append("\\\\")
    lines.append("P_7(\\Lambda,q)&=" + poly_in_var(P7, L, 7) + ".")
    lines.append("\\end{aligned}")
    lines.append("\\]")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_tex_zero_charge(path: Path, det0: sp.Expr, kappa: float) -> None:
    z = sp.Symbol("z")
    lines: List[str] = []
    lines.append("% AUTO-GENERATED by scripts/exp_sync_kernel_real_input_40_arity_charge_closed_form.py")
    lines.append("\\[")
    lines.append("\\begin{aligned}")
    lines.append("\\det(I-zM_0)&=" + sp.latex(sp.factor(det0)) + ",")
    lines.append("\\\\")
    lines.append("\\zeta_0(z)&=\\det(I-zM_0)^{-1}")
    lines.append(
        "=\\frac{1}{(1-z^2)(1-z-z^4)},"
    )
    lines.append("\\\\")
    lines.append(
        "\\kappa&\\approx "
        + f"{kappa:.12g}"
        + "\\quad\\text{(the Perron root of }\\kappa^4-\\kappa^3-1=0\\text{).}"
    )
    lines.append("\\end{aligned}")
    lines.append("\\]")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_tex_cumulants(path: Path, P1: sp.Expr, P2: sp.Expr) -> None:
    P1_s = sp.simplify(P1)
    P2_s = sp.simplify(P2)
    lines: List[str] = []
    lines.append("% AUTO-GENERATED by scripts/exp_sync_kernel_real_input_40_arity_charge_closed_form.py")
    lines.append("\\[")
    lines.append("\\begin{aligned}")
    lines.append("\\mathbb{E}[\\chi]&=" + sp.latex(P1_s) + f"\\approx {float(sp.N(P1_s, 20)):.12g},")
    lines.append("\\\\")
    lines.append(
        "\\mathrm{Var}_\\infty(\\chi)&="
        + sp.latex(P2_s)
        + f"\\approx {float(sp.N(P2_s, 20)):.12g}."
    )
    lines.append("\\end{aligned}")
    lines.append("\\]")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _chi_cumulants_closed_form(*, prog: Progress) -> Tuple[sp.Expr, sp.Expr]:
    # Compute P'(0), P''(0) for P(theta)=log lambda(e^theta), where lambda(q) is the PF root of P7(L,q)=0.
    theta = sp.Symbol("theta")
    q = sp.exp(theta)
    L = sp.Symbol("L")

    sqrt5 = sp.sqrt(5)
    lam0 = (sp.Integer(3) + sqrt5) / 2  # phi^2

    c1, c2 = sp.symbols("c1 c2")
    lam_series = lam0 + c1 * theta + c2 * theta**2

    P7 = _P7(L, sp.Symbol("q"))
    expr = sp.expand(P7.subs({L: lam_series, sp.Symbol("q"): q}))
    ser = sp.series(expr, theta, 0, 3).removeO()
    ser = sp.expand(ser)

    e0 = sp.simplify(ser.coeff(theta, 0))
    if e0 != 0:
        raise RuntimeError("P7(lam0,1) != 0; incorrect base point for series.")

    e1 = sp.simplify(ser.coeff(theta, 1))
    e2 = sp.simplify(ser.coeff(theta, 2))

    prog.tick("solving chi cumulants: c1")
    s1 = sp.solve(e1, c1, dict=True)
    if not s1:
        raise RuntimeError("no solution for c1")
    sol1 = s1[0]

    prog.tick("solving chi cumulants: c2")
    e2s = sp.simplify(e2.subs(sol1))
    s2 = sp.solve(e2s, c2, dict=True)
    if not s2:
        raise RuntimeError("no solution for c2")
    sol2 = {**sol1, **s2[0]}

    lam_series = sp.expand(lam_series.subs(sol2))
    P_series = sp.series(sp.log(lam_series), theta, 0, 3).removeO()
    P1 = sp.simplify(sp.diff(P_series, theta, 1).subs(theta, 0))
    P2 = sp.simplify(sp.diff(P_series, theta, 2).subs(theta, 0))
    return P1, P2


def main() -> None:
    parser = argparse.ArgumentParser(description="Closed-form package for arity-charge on real-input-40 kernel.")
    parser.add_argument(
        "--no-output",
        action="store_true",
        help="Skip writing JSON and TeX outputs (still runs audits).",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "sync_kernel_real_input_40_arity_charge_closed_form.json"),
    )
    parser.add_argument(
        "--tex-det-out",
        type=str,
        default=str(generated_dir() / "eq_real_input_40_arity_charge_det_closed.tex"),
    )
    parser.add_argument(
        "--tex-zero-out",
        type=str,
        default=str(generated_dir() / "eq_real_input_40_arity_charge_zero_charge_zeta.tex"),
    )
    parser.add_argument(
        "--tex-cumulants-out",
        type=str,
        default=str(generated_dir() / "eq_real_input_40_arity_charge_cumulants_closed.tex"),
    )
    args = parser.parse_args()

    prog = Progress(label="real-input-40-arity-charge", every_seconds=10.0)
    print("[real-input-40-arity-charge] start", flush=True)

    edges = build_kernel_edges()
    kernel_map = build_kernel_map(edges)
    states = build_real_input_states()
    M_full = build_real_input_matrix_int(states, kernel_map)

    adj = _adj_list_from_matrix(M_full)
    ess_idx_full = _essential_scc(adj)
    core_states = [states[i] for i in ess_idx_full]
    if len(core_states) != 20:
        raise RuntimeError(f"unexpected essential core size: {len(core_states)}")
    prog.tick("essential core extracted")

    M0, M1, audit = _build_g_matrices_and_audit(
        core_states=core_states,
        kernel_map=kernel_map,
        prog=prog,
    )
    prog.tick(
        f"coboundary OK: edges={audit.edges_in_core} g0={audit.edges_g0} g1={audit.edges_g1}"
    )

    # Zero-charge subgraph determinant (exact, in z only).
    z = sp.Symbol("z")
    det0 = _det_poly_z(sp.Matrix(M0), z)
    det0_fact = sp.factor(det0)
    det0_target = sp.expand((1 - z**2) * (1 - z - z**4))
    if sp.expand(det0 - det0_target) != 0:
        raise RuntimeError(f"det(I-zM0) mismatch: got={det0_fact}, target={sp.factor(det0_target)}")
    # Perron root kappa from x^4-x^3-1=0.
    x = sp.Symbol("x")
    kappa_roots = [r for r in sp.nroots(x**4 - x**3 - 1) if abs(sp.im(r)) < 1e-20]
    if not kappa_roots:
        raise RuntimeError("failed to locate real root for kappa")
    kappa = float(max(float(sp.re(r)) for r in kappa_roots))
    prog.tick(f"zero-charge det OK, kappa~{kappa:.6g}")

    # Closed-form determinant identity check at several integer q values (exact polynomial in z).
    q_sym = sp.Symbol("q")
    Delta_closed = _delta_closed(z, q_sym)
    for idx, qv in enumerate([1, 2, 3, 4, 5], start=1):
        A = sp.Matrix(M0) + int(qv) * sp.Matrix(M1)
        det_q = _det_poly_z(A, z)
        diff = sp.expand(det_q - Delta_closed.subs(q_sym, int(qv)))
        if diff != 0:
            raise RuntimeError(f"Delta closed-form mismatch at q={qv}")
        prog.tick(f"Delta(z,q) exact check {idx}/5 (q={qv})")

    # Closed-form cumulants at theta=0.
    P1, P2 = _chi_cumulants_closed_form(prog=prog)

    # Residue constant sanity check at q=1: C = (47+21*sqrt5)/100.
    sqrt5 = sp.sqrt(5)
    lam0 = (sp.Integer(3) + sqrt5) / 2
    L = sp.Symbol("Lambda")
    q = sp.Symbol("q")
    P7 = _P7(L, q)
    dP7 = sp.diff(P7, L)
    C_expr = sp.simplify(
        (lam0**9) / ((lam0 + 1) * (lam0**2 - 1) * dP7.subs({L: lam0, q: 1}))
    )
    C_target = (sp.Integer(47) + sp.Integer(21) * sqrt5) / sp.Integer(100)
    if sp.simplify(C_expr - C_target) != 0:
        raise RuntimeError("Residue constant check at q=1 failed.")
    prog.tick("residue constant check OK at q=1")

    payload: Dict[str, object] = {
        "coboundary_audit": asdict(audit),
        "det_zero_charge_factored": str(det0_fact),
        "kappa_approx": kappa,
        "Q7": str(_Q7(sp.Symbol("z"), sp.Symbol("q"))),
        "P7": str(_P7(sp.Symbol("Lambda"), sp.Symbol("q"))),
        "E_chi_closed": str(sp.simplify(P1)),
        "Var_chi_closed": str(sp.simplify(P2)),
        "C_q1_exact": str(C_target),
    }

    if not args.no_output:
        # JSON
        jout = Path(args.json_out)
        jout.parent.mkdir(parents=True, exist_ok=True)
        jout.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"[real-input-40-arity-charge] wrote {jout}", flush=True)

        # TeX snippets
        _write_tex_det_closed(Path(args.tex_det_out))
        _write_tex_zero_charge(Path(args.tex_zero_out), det0=det0_fact, kappa=kappa)
        _write_tex_cumulants(Path(args.tex_cumulants_out), P1=P1, P2=P2)
        print(f"[real-input-40-arity-charge] wrote {args.tex_det_out}", flush=True)
        print(f"[real-input-40-arity-charge] wrote {args.tex_zero_out}", flush=True)
        print(f"[real-input-40-arity-charge] wrote {args.tex_cumulants_out}", flush=True)

    print(
        f"[real-input-40-arity-charge] E[chi]={float(sp.N(P1, 18)):.12g} Var={float(sp.N(P2, 18)):.12g}",
        flush=True,
    )
    print("[real-input-40-arity-charge] done", flush=True)


if __name__ == "__main__":
    main()

