#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit max-entropy Markov kernel and symmetrized spectrum for diagonal-rate couplings.

This script is English-only by repository convention.

We consider the optimization defining R_w(delta):
  R_w(delta) = inf { I_P(X;Y) : P_X=P_Y=w, P(X=Y) >= 1-delta }.
For delta < 1 - sum_x w(x)^2, the unique optimizer has the exponential-family form
  P*(x,y) = u_x u_y (1 + kappa 1_{x=y}) / Z,
with kappa > 0 and u_x > 0. The induced Markov kernel is K*(y|x)=P*(x,y)/w(x).

This audit script numerically (finite-dimensional, no black-box solvers) verifies:
  - The coupling constraints, diagonal mass, and KL / entropy identities.
  - The symmetrization S = D^{-1/2} P* D^{-1/2} is symmetric PSD and shares spectrum with K*.
  - The "diagonal + rank-one" secular determinant identity for S.
  - The small-distortion (delta -> 0) slope of 1-lambda_2(delta) matches the
    predicted coefficient nu_2(w) / (A_{1/2}(w)^2 - 1), where nu_2(w) is the
    smallest positive eigenvalue of L_{1/2}(w)=A_{1/2}(w)diag(w^{-1/2})-11^T.

Outputs:
  - artifacts/export/pom_diagonal_rate_maxent_markov_spectrum_audit.json
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


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _safe_normalize_prob(w: np.ndarray) -> np.ndarray:
    w = np.asarray(w, dtype=float)
    if np.any(w <= 0):
        raise ValueError("w must be strictly positive.")
    s = float(w.sum())
    if not (s > 0):
        raise ValueError("w sum must be positive.")
    return w / s


def _entropy(p: np.ndarray) -> float:
    p = np.asarray(p, dtype=float)
    p = p[p > 0]
    return float(-(p * np.log(p)).sum())


def _mutual_information(P: np.ndarray, w: np.ndarray) -> float:
    # I(P)=sum_{x,y} P(x,y) log(P(x,y)/(w(x)w(y))).
    w = np.asarray(w, dtype=float)
    P = np.asarray(P, dtype=float)
    denom = w[:, None] * w[None, :]
    mask = P > 0
    return float((P[mask] * np.log(P[mask] / denom[mask])).sum())


@dataclass(frozen=True)
class OptimalCoupling:
    w: np.ndarray
    delta: float
    kappa: float
    u: np.ndarray
    Z: float
    P: np.ndarray
    K: np.ndarray
    S: np.ndarray


def _u_from_kappa_Z(w: np.ndarray, kappa: float, Z: float) -> np.ndarray:
    # Solve u_x(1 + kappa u_x) = Z w_x with positive root.
    # Stable form: u = (2 Z w) / (sqrt(1 + 4 kappa Z w) + 1).
    t = np.sqrt(1.0 + 4.0 * kappa * Z * w)
    u = (2.0 * Z * w) / (t + 1.0)
    return u


def _solve_Z_sum_u_equals_one(w: np.ndarray, kappa: float, *, rtol: float = 1e-14) -> Tuple[float, np.ndarray]:
    # Fix scale by enforcing A = sum_x u_x = 1.
    if not (kappa >= 0):
        raise ValueError("kappa must be >= 0.")
    if kappa == 0.0:
        # u = w, Z=1
        return 1.0, w.copy()

    def sum_u(Z: float) -> float:
        u = _u_from_kappa_Z(w, kappa, Z)
        return float(u.sum())

    lo = 0.0
    hi = 1.0
    # Expand hi until sum_u(hi) >= 1.
    for _ in range(200):
        if sum_u(hi) >= 1.0:
            break
        hi *= 2.0
    else:
        raise RuntimeError("Failed to bracket Z for sum_u(Z)=1.")

    # Bisection.
    for _ in range(400):
        mid = 0.5 * (lo + hi)
        sm = sum_u(mid)
        if sm < 1.0:
            lo = mid
        else:
            hi = mid
        if hi - lo <= rtol * max(1.0, hi):
            break

    Z = hi
    u = _u_from_kappa_Z(w, kappa, Z)
    # Sanity: sum u close to 1.
    if not math.isfinite(float(u.sum())):
        raise RuntimeError("Non-finite u sum.")
    return float(Z), u


def _diag_mass_from_kappa(w: np.ndarray, kappa: float) -> float:
    Z, u = _solve_Z_sum_u_equals_one(w, kappa)
    P_diag = (1.0 + kappa) * (u**2) / Z
    return float(P_diag.sum())


def _solve_kappa_for_delta(w: np.ndarray, delta: float, *, rtol: float = 1e-12) -> float:
    # Solve diag_mass(kappa) = 1 - delta for delta in (0, 1-p2(w)).
    if not (0.0 < delta < 1.0):
        raise ValueError("delta must be in (0,1).")
    p2 = float((w * w).sum())
    delta0 = 1.0 - p2
    if not (delta < delta0):
        raise ValueError("Need delta < 1 - sum w^2 for active diagonal constraint.")

    target = 1.0 - delta

    # Bracket kappa.
    lo = 0.0
    hi = 1.0
    for _ in range(200):
        if _diag_mass_from_kappa(w, hi) >= target:
            break
        hi *= 2.0
    else:
        raise RuntimeError("Failed to bracket kappa.")

    # Bisection on kappa.
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        pmid = _diag_mass_from_kappa(w, mid)
        if pmid < target:
            lo = mid
        else:
            hi = mid
        if hi - lo <= rtol * max(1.0, hi):
            break

    return float(hi)


def compute_optimal_coupling(w: np.ndarray, delta: float) -> OptimalCoupling:
    w = _safe_normalize_prob(w)
    kappa = _solve_kappa_for_delta(w, delta)
    Z, u = _solve_Z_sum_u_equals_one(w, kappa)

    # Build P*(x,y) = u_x u_y (1 + kappa 1_{x=y}) / Z.
    P = np.outer(u, u) / Z
    P[np.diag_indices_from(P)] = (1.0 + kappa) * (u**2) / Z

    # Markov kernel K(y|x) = P(x,y) / w(x).
    K = P / w[:, None]

    # Symmetrized operator on Euclidean space: S = D^{-1/2} P D^{-1/2}.
    inv_sqrt_w = 1.0 / np.sqrt(w)
    S = (inv_sqrt_w[:, None] * P) * inv_sqrt_w[None, :]

    return OptimalCoupling(w=w, delta=float(delta), kappa=float(kappa), u=u, Z=float(Z), P=P, K=K, S=S)


def _secular_det_identity_error(S: np.ndarray, a: np.ndarray, d: np.ndarray, lam: float) -> float:
    # Compare det(S - lam I) to prod(d-lam) * (1 + sum a^2/(d-lam)).
    n = S.shape[0]
    left = float(np.linalg.det(S - lam * np.eye(n)))
    prod = float(np.prod(d - lam))
    right = prod * float(1.0 + np.sum((a * a) / (d - lam)))
    denom = max(1.0, abs(left), abs(right))
    return abs(left - right) / denom


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit diagonal-rate maxent Markov kernel spectrum")
    parser.add_argument("--no-output", action="store_true", help="Skip writing outputs")
    args = parser.parse_args()

    # Test cases (fixed, deterministic).
    test_ws = [
        np.array([0.5, 0.3, 0.2]),
        np.array([0.25, 0.25, 0.25, 0.25]),
        np.array([0.4, 0.35, 0.15, 0.10]),
    ]
    # Use very small deltas to probe the delta->0 slope.
    test_deltas = [1e-6, 5e-7, 2e-7]

    cases: List[Dict[str, object]] = []
    all_ok = True

    for w in test_ws:
        w = _safe_normalize_prob(w)
        n = int(w.size)
        p2 = float((w * w).sum())
        delta0 = 1.0 - p2

        A = float(np.sqrt(w).sum())
        C12 = float(A * A - 1.0)
        ones = np.ones(n)
        L = A * np.diag(1.0 / np.sqrt(w)) - np.outer(ones, ones)
        # L is PSD with one zero eigenvalue.
        nu = np.linalg.eigvalsh(L)
        # Smallest positive eigenvalue (tolerate numerical noise).
        nu_pos = [float(x) for x in nu if x > 1e-12]
        nu2 = min(nu_pos) if nu_pos else 0.0
        slope_th = nu2 / C12

        case_entry: Dict[str, object] = {
            "w": [float(x) for x in w],
            "n": n,
            "p2": p2,
            "delta0": delta0,
            "A12": A,
            "C12": C12,
            "nu2": nu2,
            "slope_th": slope_th,
            "deltas": [],
        }

        # Pick deltas safely inside (0,delta0).
        deltas = [d for d in test_deltas if d < 0.2 * delta0]
        if not deltas:
            deltas = [min(1e-5, 0.1 * delta0)]

        for delta in deltas:
            oc = compute_optimal_coupling(w, delta)

            # Basic coupling checks.
            PX = oc.P.sum(axis=1)
            PY = oc.P.sum(axis=0)
            diag_mass = float(np.trace(oc.P))
            coupling_ok = (
                np.allclose(PX, oc.w, rtol=0, atol=5e-11)
                and np.allclose(PY, oc.w, rtol=0, atol=5e-11)
                and abs(diag_mass - (1.0 - delta)) <= 5e-10
                and abs(float(oc.P.sum()) - 1.0) <= 5e-11
            )

            # Entropy-rate / mutual-information identity: H(w)-h(K)=I_P.
            Hw = _entropy(oc.w)
            row_ent = float(sum(oc.w[i] * _entropy(oc.K[i, :]) for i in range(n)))
            I = _mutual_information(oc.P, oc.w)
            info_ok = abs((Hw - row_ent) - I) <= 5e-10

            # Symmetrization similarity: spectra of S and K match (within tol).
            eigS = np.linalg.eigvalsh(oc.S)
            eigK = np.linalg.eigvals(oc.K)  # K is similar to S, so should be real.
            eigK = np.sort(np.real_if_close(eigK, tol=1e3).real)
            eigS_sorted = np.sort(eigS)
            spec_ok = np.allclose(eigK, eigS_sorted, rtol=0, atol=5e-9)

            # Nonnegativity / Markov bounds.
            bounds_ok = (eigS.min() >= -5e-10) and (eigS.max() <= 1.0 + 5e-10)

            # Secular determinant identity for a few lambda values.
            a = oc.u / np.sqrt(oc.w) / math.sqrt(oc.Z)  # normalize so S = a a^T + kappa diag(a^2)
            # With our P = outer(u,u)/Z + kappa diag(u^2)/Z, S = outer(a,a) + kappa diag(a^2).
            d = oc.kappa * (a * a)
            det_errs = []
            for lam in (0.0, 0.123, 0.777):
                # Avoid poles.
                if np.min(np.abs(d - lam)) < 1e-10:
                    continue
                det_errs.append(_secular_det_identity_error(oc.S, a, d, lam))
            det_ok = (max(det_errs) if det_errs else 0.0) <= 5e-8

            # Small-distortion slope estimate for lambda2.
            eig_desc = np.sort(eigS)[::-1]
            lam2 = float(eig_desc[1]) if n >= 2 else 1.0
            slope_est = (1.0 - lam2) / delta
            slope_rel_err = abs(slope_est - slope_th) / max(1e-12, abs(slope_th))
            # Numerical slope check (asymptotic, so allow a modest tolerance).
            slope_ok = slope_rel_err <= 5e-2

            this_ok = coupling_ok and info_ok and spec_ok and bounds_ok and det_ok and slope_ok
            all_ok = all_ok and this_ok

            case_entry["deltas"].append(
                {
                    "delta": float(delta),
                    "kappa": float(oc.kappa),
                    "Z": float(oc.Z),
                    "diag_mass": float(diag_mass),
                    "H_w": float(Hw),
                    "h_K": float(row_ent),
                    "I": float(I),
                    "lambda2": float(lam2),
                    "slope_est": float(slope_est),
                    "slope_rel_err": float(slope_rel_err),
                    "slope_ok": bool(slope_ok),
                    "det_err_max": float(max(det_errs) if det_errs else 0.0),
                    "ok": bool(this_ok),
                }
            )

        cases.append(case_entry)

    payload: Dict[str, object] = {
        "ok": bool(all_ok),
        "cases": cases,
    }

    if not args.no_output:
        _write_json(export_dir() / "pom_diagonal_rate_maxent_markov_spectrum_audit.json", payload)

    if not all_ok:
        raise SystemExit("Audit failed: some checks did not pass.")


if __name__ == "__main__":
    main()

