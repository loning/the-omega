# -*- coding: utf-8 -*-
"""
Curvature-bridge audit tables (deterministic).

This script generates two small reproducible tables:
  1) A weak-field curvature proxy scaling check for the discrete Laplacian:
     Δ_h χ_hat vs Δχ on a smooth test field with an optional bounded noise level.
     This mirrors the truncation and noise-amplification bounds used in
     Appendix 33 and the weak-field curvature bridge in Appendix 60.

  2) A Wilson small-loop residual scaling check in a commuting SU(2) toy model:
     1 - (1/N) Re Tr(U_square) vs (a^4/(2N)) Tr(F^2), with O(a^6) residual scaling.

Only the Python standard library is used.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from common_paths import generated_dir
from common_tex import write_lines


def _tex_sci(x: float, sig: int = 3) -> str:
    if x == 0.0:
        return r"\ensuremath{0}"
    ax = abs(x)
    exp = int(math.floor(math.log10(ax)))
    mant = x / (10**exp)
    fmt = f"{{:.{max(sig - 1, 0)}f}}"
    mant_s = fmt.format(mant)
    if exp == 0:
        return r"\ensuremath{" + mant_s + "}"
    return r"\ensuremath{" + mant_s + r"\times 10^{" + str(exp) + "}" + "}"


@dataclass(frozen=True)
class WeakFieldRow:
    n: int
    h: float
    eps: float
    max_err_noiseless: float
    max_err_noisy: float
    trunc_bound: float
    noise_bound: float
    total_bound: float
    ratio: float


def _periodic_laplacian(grid: List[List[float]], h: float) -> List[List[float]]:
    n = len(grid)
    out = [[0.0 for _ in range(n)] for _ in range(n)]
    inv_h2 = 1.0 / (h * h)
    for i in range(n):
        im = (i - 1) % n
        ip = (i + 1) % n
        row = grid[i]
        row_im = grid[im]
        row_ip = grid[ip]
        for j in range(n):
            jm = (j - 1) % n
            jp = (j + 1) % n
            out[i][j] = (
                row_ip[j]
                + row_im[j]
                + row[jp]
                + row[jm]
                - 4.0 * row[j]
            ) * inv_h2
    return out


def _max_abs_diff(a: List[List[float]], b: List[List[float]]) -> float:
    n = len(a)
    m = 0.0
    for i in range(n):
        for j in range(n):
            d = abs(a[i][j] - b[i][j])
            if d > m:
                m = d
    return m


def _weak_field_rows() -> List[WeakFieldRow]:
    rows: List[WeakFieldRow] = []

    # Smooth test field on the 2-torus: chi(x,y) = sin(2πx) sin(2πy)
    # Exact Laplacian: Δchi = -8π^2 chi.
    # Truncation bound constant from Appendix 33 (central Laplacian):
    # C = (1/12) * sum_k sup |∂_k^4 chi| = (1/12) * 2 * (2π)^4 = (2π)^4 / 6.
    c_trunc = (2.0 * math.pi) ** 4 / 6.0
    d = 2

    eps = 1e-6
    rng = random.Random(0)

    for n_order in [3, 4, 5, 6, 7, 8]:
        N = 2**n_order
        h = 1.0 / N

        chi = [[0.0 for _ in range(N)] for _ in range(N)]
        for i in range(N):
            x = i * h
            sx = math.sin(2.0 * math.pi * x)
            for j in range(N):
                y = j * h
                sy = math.sin(2.0 * math.pi * y)
                chi[i][j] = sx * sy

        lap_exact = [[-8.0 * (math.pi**2) * chi[i][j] for j in range(N)] for i in range(N)]
        lap_noiseless = _periodic_laplacian(chi, h)
        max_err_noiseless = _max_abs_diff(lap_noiseless, lap_exact)

        # Bounded additive noise (deterministic seed), |eta| <= eps.
        chi_noisy = [[chi[i][j] + rng.uniform(-eps, eps) for j in range(N)] for i in range(N)]
        lap_noisy = _periodic_laplacian(chi_noisy, h)
        max_err_noisy = _max_abs_diff(lap_noisy, lap_exact)

        trunc_bound = c_trunc * (h * h)
        noise_bound = (4.0 * d / (h * h)) * eps
        total = trunc_bound + noise_bound
        ratio = max_err_noisy / total if total > 0 else 0.0

        rows.append(
            WeakFieldRow(
                n=n_order,
                h=h,
                eps=eps,
                max_err_noiseless=max_err_noiseless,
                max_err_noisy=max_err_noisy,
                trunc_bound=trunc_bound,
                noise_bound=noise_bound,
                total_bound=total,
                ratio=ratio,
            )
        )

    return rows


@dataclass(frozen=True)
class WilsonRow:
    k: int
    a: float
    lhs: float
    rhs: float
    residual: float
    residual_over_a6: float


def _wilson_rows() -> List[WilsonRow]:
    # SU(2) commuting toy:
    # F = f * sigma_3 / 2, so Tr(F^2) = f^2/2.
    # U = exp(i a^2 F) = diag(exp(iθ), exp(-iθ)), θ = a^2 f / 2.
    # LHS = 1 - (1/2) Re Tr(U) = 1 - cos θ.
    # RHS leading term from the standard expansion: (a^4/(2N)) Tr(F^2) with N=2.
    f = 1.0
    N = 2.0
    tr_f2 = (f * f) / 2.0

    rows: List[WilsonRow] = []
    for k in range(1, 11):
        a = 2.0 ** (-k)
        theta = (a * a) * f / 2.0
        lhs = 1.0 - math.cos(theta)
        rhs = (a**4) * tr_f2 / (2.0 * N)
        residual = abs(lhs - rhs)
        denom = a**6
        rows.append(
            WilsonRow(
                k=k,
                a=a,
                lhs=lhs,
                rhs=rhs,
                residual=residual,
                residual_over_a6=(residual / denom) if denom > 0 else 0.0,
            )
        )
    return rows


def _write_weak_field(rows: Iterable[WeakFieldRow]) -> None:
    out_rows = generated_dir() / "curvature_bridge_weak_field_rows.tex"
    out_summary = generated_dir() / "curvature_bridge_weak_field_summary.tex"

    lines: List[str] = []
    for r in rows:
        lines.append(
            " & ".join(
                [
                    str(r.n),
                    _tex_sci(r.h),
                    _tex_sci(r.eps),
                    _tex_sci(r.max_err_noiseless),
                    _tex_sci(r.max_err_noisy),
                    _tex_sci(r.trunc_bound),
                    _tex_sci(r.noise_bound),
                    _tex_sci(r.total_bound),
                    _tex_sci(r.ratio),
                ]
            )
            + r" \\"
        )
    write_lines(out_rows, lines)

    summary_lines = [
        r"\noindent\AuditTag Weak-field Laplacian scaling check on the periodic unit square: "
        r"$\chi(x,y)=\sin(2\pi x)\sin(2\pi y)$ so $\Delta\chi=-8\pi^2\chi$. "
        r"We compare the periodic central-difference Laplacian $\Delta_h$ to the exact $\Delta$ under "
        r"a deterministic bounded additive noise $|\eta|\le \epsilon$ (fixed RNG seed). "
        r"The truncation-bound constant uses the explicit $C h^2$ form from Theorem~\ref{thm:laplacian_truncation}, "
        r"and the noise term uses Corollary~\ref{cor:laplacian_noise_amplification} with $d=2$.",
    ]
    write_lines(out_summary, summary_lines)


def _write_wilson(rows: Iterable[WilsonRow]) -> None:
    out_rows = generated_dir() / "curvature_bridge_wilson_rows.tex"
    out_summary = generated_dir() / "curvature_bridge_wilson_summary.tex"

    lines: List[str] = []
    for r in rows:
        lines.append(
            " & ".join(
                [
                    str(r.k),
                    _tex_sci(r.a),
                    _tex_sci(r.lhs),
                    _tex_sci(r.rhs),
                    _tex_sci(r.residual),
                    _tex_sci(r.residual_over_a6),
                ]
            )
            + r" \\"
        )
    write_lines(out_rows, lines)

    summary_lines = [
        r"\noindent\AuditTag Wilson small-loop residual scaling check in a commuting $SU(2)$ toy model "
        r"($F=f\,\sigma_3/2$ so $U_\square=\exp(i a^2 F)$ is diagonal and exact). "
        r"We compare $1-\frac{1}{N}\Re\Tr(U_\square)$ to the leading-order term "
        r"$\frac{a^4}{2N}\Tr(F^2)$ and report the residual and residual$/a^6$ across $a=2^{-k}$. "
        r"This is a sanity check for the $O(a^6)$ remainder scaling in Theorem~\ref{thm:wilson_small_plaquette_expansion}.",
    ]
    write_lines(out_summary, summary_lines)


def main() -> None:
    wf = _weak_field_rows()
    _write_weak_field(wf)
    wr = _wilson_rows()
    _write_wilson(wr)


if __name__ == "__main__":
    main()

