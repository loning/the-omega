# -*- coding: utf-8 -*-
"""
Soft-transport connection: beta sweep for mixing/CP diagnostics (robustness diagnostic).

The deterministic S4 edge transport uses a single minimum-cost matching between
padded fibers. To introduce a continuous control parameter (while staying finite
and auditable), we instead build a *soft* complex transport matrix from the full
4x4 cost matrix between padded fibers, then orthonormalize its columns to obtain
a 4x4 unitary edge transport.

For an undirected edge {a,b} with fibers fa (at a) and fb (at b), define:
  M_{j,i} = exp(-beta * C_{i,j}) * exp(i * theta_{i,j}),
where C_{i,j} is the Hamming distance between m-bit microstate words and
theta_{i,j} is a discrete phase difference (phase register) with denom=64.

We compute edge unitaries by deterministic Gram-Schmidt on the columns of M.
Reverse orientations use the Hermitian adjoint to enforce unitarity.

For each beta in a small sweep, we compute 4x4 plaquette holonomies, project
to the 3D sum-zero subspace, renormalize to a 3x3 unitary, and extract
PDG-style sines (s12,s23,s13) and the CP-odd J invariant.

We report a permutation-robust fit (global S3xS3 relabeling) to PMNS and CKM
target sines at each beta, as a diagnostic for whether the softening can produce
hierarchical mixing patterns.

Outputs (LaTeX fragments):
  - sections/generated/holonomy_soft_transport_pmns_rows.tex
  - sections/generated/holonomy_soft_transport_ckm_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path
from typing import Dict, List, Tuple

import exp_holonomy_loops as holo
import exp_holonomy_phase_lift_angles as ang
import exp_holonomy_phase_lift_cp_invariant as ph
from common_tex import write_lines


Coord = Tuple[int, int]
Perm3 = Tuple[int, int, int]


def matmul(A: List[List[complex]], B: List[List[complex]]) -> List[List[complex]]:
    ra = len(A)
    ca = len(A[0]) if A else 0
    rb = len(B)
    cb = len(B[0]) if B else 0
    if ca != rb:
        raise ValueError("Incompatible matrix shapes.")
    out = [[0j] * cb for _ in range(ra)]
    for i in range(ra):
        for k in range(ca):
            aik = A[i][k]
            if aik == 0j:
                continue
            for j in range(cb):
                out[i][j] += aik * B[k][j]
    return out


def adjoint(U: List[List[complex]]) -> List[List[complex]]:
    n = len(U)
    return [[U[j][i].conjugate() for j in range(n)] for i in range(n)]


def gram_schmidt_unitary_4x4(M: List[List[complex]], eps: float = 1e-12) -> List[List[complex]] | None:
    """
    Orthonormalize columns of a 4x4 matrix to obtain a 4x4 unitary.
    Return None on rank deficiency.
    """
    cols = [[M[i][j] for i in range(4)] for j in range(4)]
    Qcols: List[List[complex]] = []

    def inner(u: List[complex], v: List[complex]) -> complex:
        return sum(u[i].conjugate() * v[i] for i in range(4))

    def norm(v: List[complex]) -> float:
        return math.sqrt(float(inner(v, v).real))

    for v in cols:
        w = list(v)
        for q in Qcols:
            proj = inner(q, w)
            for i in range(4):
                w[i] -= proj * q[i]
        nrm = norm(w)
        if nrm < eps:
            return None
        for i in range(4):
            w[i] /= nrm
        Qcols.append(w)

    return [[Qcols[j][i] for j in range(4)] for i in range(4)]


def edge_unitary_soft(a: Coord, b: Coord, labels: Dict[Coord, str], pre: Dict[str, List[int]], beta: float, denom: int = 64) -> List[List[complex]] | None:
    """
    Build a soft transport unitary from a->b.
    """
    wa = labels[a]
    wb = labels[b]
    # IMPORTANT: the original sharp connection pads fibers by repeating the last element.
    # For unitary construction via Gram-Schmidt, repeated microstates create duplicate
    # columns and rank deficiency. Here we pad with distinct dummy basis tags.

    def fiber4_distinct(w: str) -> List[int]:
        xs = list(pre[w])
        if not xs:
            raise AssertionError("Empty fiber.")
        xs = sorted(xs)
        if len(xs) > 4:
            xs = xs[:4]
        # Pad with distinct negative sentinels.
        k = 1
        while len(xs) < 4:
            xs.append(-k)
            k += 1
        return xs

    fa = fiber4_distinct(wa)
    fb = fiber4_distinct(wb)

    # Build the raw complex matrix M (rows j at b, cols i at a).
    M: List[List[complex]] = [[0j] * 4 for _ in range(4)]
    def bits_or_empty(x: int) -> str:
        return holo.bits6(x) if x >= 0 else ""

    a_bits = [bits_or_empty(x) for x in fa]
    b_bits = [bits_or_empty(x) for x in fb]

    def cost(xi: int, yj: int, i: int, j: int) -> int:
        # Real-real cost: Hamming distance.
        if xi >= 0 and yj >= 0:
            return holo.hamming(a_bits[i], b_bits[j])
        # Dummy involvement: assign a deterministic large cost with a small offset
        # to break column degeneracies.
        base = 6
        if xi < 0 and yj < 0:
            return base + abs(xi) + abs(yj)
        if xi < 0:
            return base + abs(xi)
        return base + abs(yj)

    def pair_phase(xi: int, yj: int) -> float:
        """
        Pair-dependent phase to avoid rank-1 separability at beta=0.
        Use XOR on 6-bit indices as a minimal relative-phase surrogate.
        """
        if xi < 0 or yj < 0:
            return 0.0
        return ph.phase_with_denom((xi ^ yj) & 63, denom=denom, map_name="id", bits=6)
    for i in range(4):
        for j in range(4):
            cij = cost(fa[i], fb[j], i=i, j=j)
            amp = math.exp(-beta * float(cij))
            theta = pair_phase(fa[i], fb[j])
            phase = complex(math.cos(theta), math.sin(theta))
            M[j][i] = complex(amp, 0.0) * phase

    return gram_schmidt_unitary_4x4(M)


def permute_3x3(Q: List[List[complex]], r: Perm3, c: Perm3) -> List[List[complex]]:
    return [[Q[r[i]][c[j]] for j in range(3)] for i in range(3)]


def abs_log_ratio(pred: float, ref: float) -> float:
    if pred <= 0.0 or ref <= 0.0:
        return float("inf")
    return abs(math.log(pred / ref))


def mean(xs: List[float]) -> float:
    return sum(xs) / float(len(xs)) if xs else float("nan")


def compute_Q3_plaquettes(beta: float) -> Tuple[List[List[List[complex]]], int]:
    """
    Return (list of 3x3 unitaries for plaquettes, failure_count).
    """
    labels = holo.grid_labels(n_bits=3)
    pre = holo.preimages()

    # Build unitary cache for undirected edges with enforced inverse by adjoint.
    U_edge: Dict[Tuple[Coord, Coord], List[List[complex]]] = {}
    failures = 0

    def key(a: Coord, b: Coord) -> Tuple[Coord, Coord]:
        return (a, b) if a < b else (b, a)

    # Enumerate undirected neighbor edges on 8x8 grid.
    for x in range(8):
        for y in range(8):
            a = (x, y)
            for dx, dy in [(1, 0), (0, 1)]:
                nx, ny = x + dx, y + dy
                if nx >= 8 or ny >= 8:
                    continue
                b = (nx, ny)
                ka, kb = key(a, b)
                if (ka, kb) in U_edge:
                    continue
                U = edge_unitary_soft(ka, kb, labels, pre, beta=beta, denom=64)
                if U is None:
                    failures += 1
                    continue
                U_edge[(ka, kb)] = U

    # Helper to get oriented unitary.
    def U_oriented(a: Coord, b: Coord) -> List[List[complex]] | None:
        ka, kb = key(a, b)
        U = U_edge.get((ka, kb))
        if U is None:
            return None
        return U if (a, b) == (ka, kb) else adjoint(U)

    # Plaquette holonomies.
    B = ph.basis_B()
    Qs: List[List[List[complex]]] = []
    for x in range(7):
        for y in range(7):
            a = (x, y)
            b = (x + 1, y)
            c = (x + 1, y + 1)
            d = (x, y + 1)
            U_ab = U_oriented(a, b)
            U_bc = U_oriented(b, c)
            U_cd = U_oriented(c, d)
            U_da = U_oriented(d, a)
            if U_ab is None or U_bc is None or U_cd is None or U_da is None:
                failures += 1
                continue
            H = matmul(U_da, matmul(U_cd, matmul(U_bc, U_ab)))
            M3 = ph.project_3x3(H, B=B)
            Q3 = ph.gram_schmidt_unitary(M3)
            if Q3 is None:
                failures += 1
                continue
            Qs.append(Q3)
    return Qs, failures


def best_perm_fit(Qs: List[List[List[complex]]], ref: Tuple[float, float, float]) -> Tuple[float, float, Perm3, Perm3, float, float, float]:
    perms = list(itertools.permutations((0, 1, 2), 3))
    best = None  # (Einf,E1,r,c)
    best_pred = (float("nan"), float("nan"), float("nan"))
    for r in perms:
        for c in perms:
            s12s: List[float] = []
            s23s: List[float] = []
            s13s: List[float] = []
            for Q in Qs:
                Qp = permute_3x3(Q, r=r, c=c)
                s12, s23, s13, _delta_deg, _J = ang.extract_angles(Qp)
                if math.isnan(s12) or math.isnan(s23) or math.isnan(s13):
                    continue
                s12s.append(s12)
                s23s.append(s23)
                s13s.append(s13)
            s12 = mean(s12s)
            s23 = mean(s23s)
            s13 = mean(s13s)
            e12 = abs_log_ratio(s12, ref[0])
            e23 = abs_log_ratio(s23, ref[1])
            e13 = abs_log_ratio(s13, ref[2])
            Einf = max(e12, e23, e13)
            E1 = e12 + e23 + e13
            cand = (Einf, E1, r, c)
            if best is None or cand < best:
                best = cand
                best_pred = (s12, s23, s13)
    if best is None:
        raise AssertionError("No permutations enumerated.")
    Einf, E1, r, c = best
    s12, s23, s13 = best_pred
    return Einf, E1, r, c, s12, s23, s13


def mean_absJ(Qs: List[List[List[complex]]]) -> float:
    Js = [abs(ph.jarlskog_invariant(Q)) for Q in Qs]
    return mean(Js)


def emit(beta_list: List[float], out_path: Path, ref: Tuple[float, float, float]) -> None:
    scored = []
    cache = {}
    for beta in beta_list:
        Qs, failures = compute_Q3_plaquettes(beta=beta)
        Einf, E1, r, c, s12, s23, s13 = best_perm_fit(Qs, ref=ref)
        Jm = mean_absJ(Qs)
        cache[beta] = (Einf, E1, r, c, s12, s23, s13, Jm, failures, len(Qs))
        scored.append((Einf, E1, beta))
    scored.sort()
    best_beta = scored[0][2]

    lines: List[str] = []
    for beta in beta_list:
        Einf, E1, r, c, s12, s23, s13, Jm, failures, nQ = cache[beta]
        beta_tex = f"{beta:.3g}"
        Einf_tex = f"{Einf:.3f}"
        E1_tex = f"{E1:.3f}"
        if beta == best_beta:
            beta_tex = rf"\textbf{{{beta_tex}}}"
            Einf_tex = rf"\textbf{{{Einf_tex}}}"
            E1_tex = rf"\textbf{{{E1_tex}}}"
        lines.append(
            f"{beta_tex} & {nQ} & \\texttt{{{r}}}/\\texttt{{{c}}} & {s12:.4f} & {s23:.4f} & {s13:.4f} & {Einf_tex} & {E1_tex} & {Jm:.6g} & {failures} \\\\"
        )
    lines.append("\\bottomrule")
    write_lines(out_path, lines)


def main() -> None:
    beta_list = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]
    pmns = (math.sqrt(0.307), math.sqrt(0.545), math.sqrt(0.0218))
    ckm = (0.2243, 0.0422, 0.00394)

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    emit(beta_list, out_dir / "holonomy_soft_transport_pmns_rows.tex", ref=pmns)
    print("Wrote sections/generated/holonomy_soft_transport_pmns_rows.tex")
    emit(beta_list, out_dir / "holonomy_soft_transport_ckm_rows.tex", ref=ckm)
    print("Wrote sections/generated/holonomy_soft_transport_ckm_rows.tex")


if __name__ == "__main__":
    main()


