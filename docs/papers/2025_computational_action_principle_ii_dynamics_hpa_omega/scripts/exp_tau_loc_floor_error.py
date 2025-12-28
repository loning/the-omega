#!/usr/bin/env python3
"""
CAP-II reproducibility script:
Finite-horizon rounding error for cycle counting tau_loc(T;x) = floor(T/kappa) * tau0.

This script generates a LaTeX table-row fragment under sections/generated/.
It is deterministic (no randomness).
"""

from __future__ import annotations

import argparse
from pathlib import Path


def _default_out_path() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent / "sections" / "generated" / "tau_loc_floor_error_rows.tex"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=_default_out_path(),
        help="Output .tex file path for table rows.",
    )
    parser.add_argument(
        "--T",
        type=int,
        nargs="+",
        default=[10, 25, 100, 250, 1000],
        help="List of tick horizons T to include.",
    )
    parser.add_argument(
        "--kappa",
        type=int,
        nargs="+",
        default=[3, 7, 11, 37],
        help="List of kappa values to include.",
    )
    args = parser.parse_args()

    rows: list[str] = []
    for T in args.T:
        for kappa in args.kappa:
            if kappa <= 0:
                raise ValueError("kappa must be positive")
            C = T // kappa
            ratio = T / float(kappa)
            err = abs(C - ratio)
            rows.append(f"{T} & {kappa} & {C} & {ratio:.6g} & {err:.6g} \\\\")

    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()


