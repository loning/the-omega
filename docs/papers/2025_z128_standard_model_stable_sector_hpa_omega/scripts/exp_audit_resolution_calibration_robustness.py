# -*- coding: utf-8 -*-
"""
Uncertainty-robustness audit for the r_step calibration minimizer.

We test whether the selected minimizer (k=2 in r_step = k*pi) is stable under
perturbations of the reference anchors.

Two calibration problems are audited:
  - single-anchor: m=10 anchored to m_Z
  - two-anchor:    (m=10 -> m_Z) and (m=8 -> mu_QCD)

Sampling is deterministic (fixed RNG seed) and is an audit stress test.

Outputs (LaTeX fragment):
  - sections/generated/audit_resolution_calibration_robustness_rows.tex

Only the Python standard library is used.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from common_constants import M_E_GEV, M_Z_GEV, PHI
from common_tex import write_lines


def mu_threshold(m: int, r_step: float) -> float:
    r_th = float(m - 6) * r_step
    return M_E_GEV * (PHI ** r_th)


def best_k_single(muZ_ref: float, K: int = 10) -> int:
    best: Tuple[float, int] | None = None  # (abs log mismatch, k)
    for k in range(1, K + 1):
        r_step = float(k) * math.pi
        mu = mu_threshold(10, r_step=r_step)
        e = abs(math.log(mu / muZ_ref))
        cand = (e, k)
        if best is None or cand < best:
            best = cand
    if best is None:
        raise AssertionError("No candidates enumerated.")
    return best[1]


def best_k_double(muZ_ref: float, muQ_ref: float, K: int = 10) -> int:
    best: Tuple[float, float, int] | None = None  # (Einf,E1,k)
    for k in range(1, K + 1):
        r_step = float(k) * math.pi
        eZ = math.log(mu_threshold(10, r_step=r_step) / muZ_ref)
        eQ = math.log(mu_threshold(8, r_step=r_step) / muQ_ref)
        Einf = max(abs(eZ), abs(eQ))
        E1 = abs(eZ) + abs(eQ)
        cand = (Einf, E1, k)
        if best is None or cand < best:
            best = cand
    if best is None:
        raise AssertionError("No candidates enumerated.")
    return best[2]


@dataclass(frozen=True)
class Row:
    model_tex: str
    sigma_tex: str
    samples: int
    baseline: str
    stability: float


def truncated_normal(rng: random.Random, mu: float, sigma: float, lo: float, hi: float) -> float:
    for _ in range(10000):
        x = rng.gauss(mu, sigma)
        if lo <= x <= hi:
            return x
    return max(lo, min(hi, mu))


def main() -> None:
    rng = random.Random(0)
    N = 500

    # Anchor uncertainties (audit choices):
    # - mZ: use a small absolute sigma (few MeV scale would be too tiny to matter here);
    #   we choose 0.1 GeV as a stress-test width.
    # - mu_QCD: heuristic 0.05 GeV around 0.2 GeV.
    sigma_Z = 0.1
    muQ0 = 0.2
    sigma_Q = 0.05

    rows: List[Row] = []

    # Single-anchor stability.
    base_k = best_k_single(M_Z_GEV)
    stable = 0
    for _ in range(N):
        muZ = truncated_normal(rng, M_Z_GEV, sigma_Z, lo=1e-6, hi=1e6)
        if best_k_single(muZ_ref=muZ) == base_k:
            stable += 1
    rows.append(
        Row(
            model_tex=r"single anchor ($m=10\to m_Z$)",
            sigma_tex=rf"$\sigma_Z={sigma_Z}$ GeV",
            samples=N,
            baseline=f"$k={base_k}$",
            stability=float(stable) / float(N),
        )
    )

    # Two-anchor stability.
    base_k2 = best_k_double(M_Z_GEV, muQ0)
    stable = 0
    for _ in range(N):
        muZ = truncated_normal(rng, M_Z_GEV, sigma_Z, lo=1e-6, hi=1e6)
        muQ = truncated_normal(rng, muQ0, sigma_Q, lo=1e-6, hi=1e6)
        if best_k_double(muZ_ref=muZ, muQ_ref=muQ) == base_k2:
            stable += 1
    rows.append(
        Row(
            model_tex=r"two anchors ($m=10\to m_Z$, $m=8\to \mu_{\mathrm{QCD}}$)",
            sigma_tex=rf"$(\sigma_Z,\sigma_Q)=({sigma_Z},{sigma_Q})$ GeV",
            samples=N,
            baseline=f"$k={base_k2}$",
            stability=float(stable) / float(N),
        )
    )

    out_lines: List[str] = []
    for r in rows:
        out_lines.append(
            f"{r.model_tex} & {r.sigma_tex} & {r.samples} & {r.baseline} & {r.stability:.3f} \\\\"
        )
    out_lines.append("\\bottomrule")

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "sections" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_lines(out_dir / "audit_resolution_calibration_robustness_rows.tex", out_lines)
    print("Wrote sections/generated/audit_resolution_calibration_robustness_rows.tex")


if __name__ == "__main__":
    main()


