#!/usr/bin/env python3
"""
CAP-II reproducibility script:
Weighted least-squares fit of the weak-field Schwarzschild target
  kappa/kappa0 - 1 ≈ (GM) * (1/r)
or, equivalently via the Wigner--Smith linewidth proxy,
  1 - gamma/gamma0 ≈ (GM) * (1/r).

Input: CSV with header and at least two columns: r,value[,sigma].
  - r: radius (same units across rows)
  - value: either kappa_ratio (=kappa/kappa0) or gamma_ratio (=gamma/gamma0)
  - sigma (optional): 1-sigma uncertainty for the dependent variable (in same units as y)

Output: a single LaTeX table row under sections/generated/.

This script is deterministic and performs no simulation.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Row:
    r: float
    value: float
    sigma: Optional[float]


def read_rows(path: Path) -> list[Row]:
    rows: list[Row] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV must have a header row")
        # Normalize common header variants
        field_map = {name.strip().lower(): name for name in reader.fieldnames}
        r_key = field_map.get("r") or field_map.get("radius")
        v_key = field_map.get("value") or field_map.get("kappa_ratio") or field_map.get("gamma_ratio")
        s_key = field_map.get("sigma") or field_map.get("std") or field_map.get("stderr")
        if r_key is None or v_key is None:
            raise ValueError("CSV must contain columns r (or radius) and value (or kappa_ratio/gamma_ratio)")
        for rec in reader:
            r = float(rec[r_key])
            v = float(rec[v_key])
            s = float(rec[s_key]) if (s_key is not None and rec.get(s_key, "").strip() != "") else None
            rows.append(Row(r=r, value=v, sigma=s))
    if not rows:
        raise ValueError("No data rows found")
    return rows


def wls_fit_through_origin(x: list[float], y: list[float], w: list[float]) -> float:
    num = sum(wi * xi * yi for xi, yi, wi in zip(x, y, w))
    den = sum(wi * xi * xi for xi, wi in zip(x, w))
    if den == 0.0:
        raise ValueError("Degenerate design: sum(w*x^2)=0")
    return num / den


def rmse(y: list[float], yhat: list[float]) -> float:
    if len(y) != len(yhat):
        raise ValueError("length mismatch")
    return (sum((a - b) ** 2 for a, b in zip(y, yhat)) / float(len(y))) ** 0.5


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in_csv", type=Path, required=True, help="Input CSV with columns r,value[,sigma].")
    parser.add_argument(
        "--mode",
        choices=["kappa_ratio", "gamma_ratio"],
        required=True,
        help="Interpretation of the CSV 'value' column.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("sections/generated/schw_weakfield_fit_rows.tex"),
        help="Output .tex file for a single table row.",
    )
    args = parser.parse_args()

    data = read_rows(args.in_csv)
    x = [1.0 / row.r for row in data]

    if args.mode == "kappa_ratio":
        # y = kappa/kappa0 - 1
        y = [row.value - 1.0 for row in data]
    else:
        # y = 1 - gamma/gamma0
        y = [1.0 - row.value for row in data]

    # weights: inverse-variance if provided, otherwise 1
    w = []
    for row, yi in zip(data, y):
        if row.sigma is None or row.sigma <= 0.0:
            w.append(1.0)
        else:
            w.append(1.0 / (row.sigma * row.sigma))

    gm_hat = wls_fit_through_origin(x, y, w)
    yhat = [gm_hat * xi for xi in x]
    e = rmse(y, yhat)

    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mode_tex = args.mode.replace("_", "\\_")
    out_path.write_text(f"{mode_tex} & {len(data)} & {gm_hat:.6g} & {e:.3e} \\\\\n", encoding="utf-8")


if __name__ == "__main__":
    main()


