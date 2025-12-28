#!/usr/bin/env python3
"""
CAP-II reproducibility script:
Synthetic weak-field Schwarzschild regression with an explicit noise model and uncertainty.

We generate noisy data for the weak-field linear model
  y = (GM) * (1/r) + epsilon,
with y = kappa/kappa0 - 1 and epsilon ~ N(0, sigma_y^2).

We then compute the weighted least-squares estimator through the origin:
  GM_hat = sum(w*x*y)/sum(w*x^2), with w = 1/sigma_y^2,
and report its standard error sqrt(Var(GM_hat)) = 1/sqrt(sum(w*x^2)).

Output:
  - a single LaTeX table row.

This script is deterministic given --seed.
"""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path


def _default_out_path() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent / "sections" / "generated" / "schw_weakfield_synth_wls_row.tex"


def wls_fit_through_origin(x: list[float], y: list[float], w: list[float]) -> float:
    num = sum(wi * xi * yi for xi, yi, wi in zip(x, y, w))
    den = sum(wi * xi * xi for xi, wi in zip(x, w))
    if den == 0.0:
        raise ValueError("degenerate design")
    return num / den


def rmse(y: list[float], yhat: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(y, yhat)) / float(len(y)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--GM", type=float, default=1.0)
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--r_min", type=float, default=50.0)
    parser.add_argument("--r_max", type=float, default=800.0)
    parser.add_argument("--sigma_y", type=float, default=1.0e-4)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=_default_out_path())
    args = parser.parse_args()

    if args.n <= 2:
        raise ValueError("n must be >= 3")
    if args.r_min <= 0.0 or args.r_max <= 0.0 or args.r_max <= args.r_min:
        raise ValueError("invalid r range")
    if args.sigma_y <= 0.0:
        raise ValueError("sigma_y must be positive")

    rng = random.Random(args.seed)
    rs = [args.r_min + (args.r_max - args.r_min) * i / float(args.n - 1) for i in range(args.n)]
    x = [1.0 / r for r in rs]
    # y_true = (GM)/r
    y_true = [args.GM * xi for xi in x]
    y = [yt + rng.gauss(0.0, args.sigma_y) for yt in y_true]
    w = [1.0 / (args.sigma_y * args.sigma_y) for _ in rs]

    GM_hat = wls_fit_through_origin(x, y, w)
    yhat = [GM_hat * xi for xi in x]
    e = rmse(y, yhat)
    se = 1.0 / math.sqrt(sum(wi * xi * xi for xi, wi in zip(x, w)))
    z = (GM_hat - args.GM) / se

    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        f"{args.n} & {args.r_min:.6g} & {args.r_max:.6g} & {args.sigma_y:.1e} & {args.GM:.6g} & {GM_hat:.6g} & {se:.2e} & {e:.2e} & {z:.2f} \\\\\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()


