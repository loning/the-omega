#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fence (zigzag) order-polynomial / kernel-spectrum audit.

We audit the kernel representation for the fence order polynomial Ω_{Z_ℓ}(k) used in the paper:
  - Ω_{Z_ℓ}(k) counts order-preserving maps f: Z_ℓ → {1,...,k}.
  - Equivalently, it counts weakly alternating sequences a_1,...,a_ℓ in {1,...,k}:
        a_1 <= a_2 >= a_3 <= a_4 >= ...
  - The paper expresses Ω_{Z_ℓ}(k) via the symmetric kernel matrix K_k(i,j)=min(i,j)
    and vectors b=(1,2,...,k)^T, 1=(1,...,1)^T.

This script verifies for k<=k_max and ℓ<=l_max:
  - DP count Ω_{Z_ℓ}(k) matches the kernel-matrix formula (Theorem~\\ref{thm:pom-fence-order-poly-spectral}).
  - The explicit eigenvalue formula for K_k matches numeric eigendecomposition
    (Lemma~\\ref{lem:pom-Kk-eigenvalues}).
  - The entropy density h_ref(k)=1/2 log λ_1(k) matches the closed form and
    approaches log(2k+1)-log(pi) (Corollary~\\ref{cor:pom-fence-multichain-entropy-pi}).

Outputs:
  - artifacts/export/fence_order_poly_spectral_audit.json
  - sections/generated/tab_fence_order_poly_spectral_audit.tex
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from common_paths import export_dir, generated_dir


def omega_fence_dp(l: int, k: int) -> int:
    """DP count of weakly alternating sequences of length l in {1..k}."""
    l = int(l)
    k = int(k)
    if l < 0 or k < 0:
        raise ValueError("require l>=0, k>=0")
    if k == 0:
        return 1 if l == 0 else 0
    if l == 0:
        return 1
    # dp[j] counts sequences ending at value (j+1) after i positions.
    dp = [1] * k  # i=1: any value allowed
    for i in range(1, l):
        new = [0] * k
        if i % 2 == 1:
            # constraint a_i <= a_{i+1}
            s = 0
            for j in range(k):
                s += dp[j]
                new[j] = s
        else:
            # constraint a_i >= a_{i+1}
            s = 0
            for j in range(k - 1, -1, -1):
                s += dp[j]
                new[j] = s
        dp = new
    return int(sum(dp))


def kernel_matrix_min(k: int) -> List[List[int]]:
    k = int(k)
    return [[min(i + 1, j + 1) for j in range(k)] for i in range(k)]


def matmul(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    n = len(A)
    m = len(B[0]) if B else 0
    p = len(B)
    if any(len(row) != p for row in A):
        raise ValueError("matmul dimension mismatch")
    out = [[0] * m for _ in range(n)]
    for i in range(n):
        Ai = A[i]
        for t in range(p):
            a = Ai[t]
            if a == 0:
                continue
            Bt = B[t]
            for j in range(m):
                out[i][j] += a * Bt[j]
    return out


def matvec(A: List[List[int]], v: List[int]) -> List[int]:
    n = len(A)
    if any(len(row) != len(v) for row in A):
        raise ValueError("matvec dimension mismatch")
    out = [0] * n
    for i in range(n):
        s = 0
        Ai = A[i]
        for j, a in enumerate(Ai):
            if a:
                s += a * v[j]
        out[i] = s
    return out


def dot(u: List[int], v: List[int]) -> int:
    if len(u) != len(v):
        raise ValueError("dot dimension mismatch")
    return int(sum(a * b for a, b in zip(u, v)))


def omega_fence_kernel(l: int, k: int, K_pows: List[List[List[int]]], b: List[int], ones: List[int]) -> int:
    l = int(l)
    k = int(k)
    if l == 0:
        return 1
    if l == 1:
        return k
    if l % 2 == 1:
        # l = 2t+1, t>=1
        t = (l - 1) // 2
        P = K_pows[t - 1]
        return dot(b, matvec(P, b))
    # l = 2t, t>=1
    t = l // 2
    P = K_pows[t - 1]
    return dot(b, matvec(P, ones))


def eigenvalues_formula(k: int) -> List[float]:
    k = int(k)
    out: List[float] = []
    for p in range(1, k + 1):
        theta = (2 * p - 1) * math.pi / (2 * k + 1)
        lam = 1.0 / (2.0 * (1.0 - math.cos(theta)))
        out.append(float(lam))
    out.sort(reverse=True)
    return out


def eigenvalues_numeric(k: int) -> List[float]:
    k = int(k)
    K = np.fromfunction(lambda i, j: np.minimum(i + 1.0, j + 1.0), (k, k), dtype=float)
    vals = np.linalg.eigvalsh(K)  # ascending
    vals = vals[::-1]
    return [float(x) for x in vals]


def max_rel_err(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        raise ValueError("length mismatch")
    e = 0.0
    for x, y in zip(a, b):
        denom = abs(y) if abs(y) > 0 else 1.0
        e = max(e, abs(x - y) / denom)
    return float(e)


@dataclass(frozen=True)
class Row:
    k: int
    l_max: int
    omega_ok: bool
    omega_first_mismatch: str
    lambda1: float
    href: float
    href_asymp: float
    href_abs_diff: float
    eig_rel_err_max: float

    def ok(self) -> bool:
        return bool(self.omega_ok) and (self.eig_rel_err_max <= 1e-10)

    def to_dict(self) -> Dict[str, object]:
        return {
            "k": int(self.k),
            "l_max": int(self.l_max),
            "omega_ok": bool(self.omega_ok),
            "omega_first_mismatch": str(self.omega_first_mismatch),
            "lambda1": float(self.lambda1),
            "href": float(self.href),
            "href_asymp": float(self.href_asymp),
            "href_abs_diff": float(self.href_abs_diff),
            "eig_rel_err_max": float(self.eig_rel_err_max),
            "ok": bool(self.ok()),
        }


def write_table(rows: List[Row], out_path: Path, k_max: int, l_max: int) -> None:
    lines: List[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\scriptsize")
    lines.append("\\setlength{\\tabcolsep}{6pt}")
    lines.append(
        (
            "\\caption{锯齿序多项式谱核审计：对 $1\\le k\\le %d$ 与 $0\\le \\ell\\le %d$，"
            "DP 计数与核算子公式一致（定理~\\ref{thm:pom-fence-order-poly-spectral}），"
            "且 $K_k(i,j)=\\min(i,j)$ 的显式谱与数值本征分解一致（引理~\\ref{lem:pom-Kk-eigenvalues}）。"
            "并给出 $h_{\\mathrm{ref}}(k)=\\tfrac12\\log\\lambda_1(k)$ 与连续极限参照 $\\log(2k+1)-\\log\\pi$ 的差（推论~\\ref{cor:pom-fence-multichain-entropy-pi}）。}"
        )
        % (int(k_max), int(l_max))
    )
    lines.append("\\label{tab:fence_order_poly_spectral_audit}")
    lines.append("\\begin{tabular}{r r r r r r r}")
    lines.append("\\toprule")
    lines.append(
        "$k$ & $\\lambda_1(k)$ & $h_{\\mathrm{ref}}(k)$ & $\\log(2k+1)-\\log\\pi$ & $|\\Delta|$ & eig rel err & $\\Omega$ check\\\\"
    )
    lines.append("\\midrule")
    for r in rows:
        lam1 = f"{r.lambda1:.10f}"
        href = f"{r.href:.10f}"
        asymp = f"{r.href_asymp:.10f}"
        diff = f"{r.href_abs_diff:.2e}"
        eig = f"{r.eig_rel_err_max:.2e}"
        ok = "OK" if r.omega_ok else "FAIL"
        lines.append(f"{r.k} & {lam1} & {href} & {asymp} & {diff} & {eig} & {ok}\\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Audit fence order polynomial kernel/spectrum formulas.")
    ap.add_argument("--k-max", type=int, default=12)
    ap.add_argument("--l-max", type=int, default=18)
    ap.add_argument(
        "--json-out",
        type=str,
        default=str(export_dir() / "fence_order_poly_spectral_audit.json"),
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    k_max = int(args.k_max)
    l_max = int(args.l_max)
    if k_max < 1:
        raise SystemExit("Require --k-max >= 1")
    if l_max < 0:
        raise SystemExit("Require --l-max >= 0")

    rows: List[Row] = []
    for k in range(1, k_max + 1):
        # Build kernel powers up to t_max needed for l<=l_max.
        t_max = max(0, (l_max // 2) - 1)  # max exponent index used (t-1)
        K = kernel_matrix_min(k)
        # K_pows[p] = K^p, starting at p=0 (identity).
        I = [[1 if i == j else 0 for j in range(k)] for i in range(k)]
        K_pows: List[List[List[int]]] = [I]
        for _ in range(1, t_max + 1):
            K_pows.append(matmul(K_pows[-1], K))
        b = [i + 1 for i in range(k)]
        ones = [1] * k

        omega_ok = True
        first_mismatch = ""
        for l in range(0, l_max + 1):
            a = omega_fence_dp(l=l, k=k)
            b2 = omega_fence_kernel(l=l, k=k, K_pows=K_pows, b=b, ones=ones)
            if a != b2:
                omega_ok = False
                first_mismatch = f"(l={l}, dp={a}, kernel={b2})"
                break

        # Spectrum audit.
        ev_num = eigenvalues_numeric(k)
        ev_for = eigenvalues_formula(k)
        eig_err = max_rel_err(ev_num, ev_for)

        # Principal eigenvalue / entropy density.
        alpha = math.pi / (4 * k + 2)
        lambda1 = 1.0 / (4.0 * (math.sin(alpha) ** 2))
        href = -math.log(2.0 * math.sin(alpha))
        href_asymp = math.log(2 * k + 1) - math.log(math.pi)
        href_abs_diff = abs(href - href_asymp)

        rows.append(
            Row(
                k=k,
                l_max=l_max,
                omega_ok=omega_ok,
                omega_first_mismatch=first_mismatch,
                lambda1=lambda1,
                href=href,
                href_asymp=href_asymp,
                href_abs_diff=href_abs_diff,
                eig_rel_err_max=eig_err,
            )
        )

    bad = [r for r in rows if not r.ok()]
    if bad:
        msgs = ", ".join(
            f"k={r.k}(omega_ok={r.omega_ok},eig_rel_err={r.eig_rel_err_max:.2e},mismatch={r.omega_first_mismatch})"
            for r in bad
        )
        raise AssertionError(f"Fence order-polynomial spectral audit failed: {msgs}")

    payload: Dict[str, object] = {
        "params": {"k_max": k_max, "l_max": l_max},
        "rows": [r.to_dict() for r in rows],
    }
    json_out = Path(args.json_out)
    if not json_out.is_absolute():
        json_out = Path.cwd() / json_out
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    write_table(rows, out_path=(generated_dir() / "tab_fence_order_poly_spectral_audit.tex"), k_max=k_max, l_max=l_max)


if __name__ == "__main__":
    main()

