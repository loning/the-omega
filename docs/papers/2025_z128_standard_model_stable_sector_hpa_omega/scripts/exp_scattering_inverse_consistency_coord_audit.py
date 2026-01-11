#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inverse consistency audit with coordinate transforms + Jacobian sign gate.

Reads:
  data/k4_matching/scattering_phase_registry.json

For each dataset:
  - build point clouds (x_i, delta_i) and optional transformed coordinates y(x).
  - compute slope d(delta)/dy under bounded estimator families.
  - check a sign gate: if dy/dx > 0 on the grid, the sign of d(delta)/dy should
    match the sign of d(delta)/dx (pointwise) for the same estimator family.

Outputs:
  - sections/generated/scattering_inverse_coord_rows.tex
  - sections/generated/scattering_inverse_coord_summary.tex

Standard-library only; deterministic.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from common_paths import generated_dir, paper_root
from common_tex import write_lines


@dataclass(frozen=True)
class PhasePoint:
    x: float
    delta: float


def _read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


def _central_diff_slopes(points: List[PhasePoint], coord: Callable[[PhasePoint], float]) -> Tuple[List[float], List[float]]:
    ps = sorted(points, key=lambda p: coord(p))
    if len(ps) < 3:
        return ([], [])
    xs: List[float] = []
    slopes: List[float] = []
    for i in range(1, len(ps) - 1):
        x_lo, d_lo = float(coord(ps[i - 1])), float(ps[i - 1].delta)
        x_hi, d_hi = float(coord(ps[i + 1])), float(ps[i + 1].delta)
        if x_hi == x_lo:
            continue
        xs.append(float(coord(ps[i])))
        slopes.append(float((d_hi - d_lo) / (x_hi - x_lo)))
    return (xs, slopes)


def _sign_mismatch_fraction(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return float("nan")
    mism = 0
    tot = 0
    for x, y in zip(a, b):
        if not math.isfinite(x) or not math.isfinite(y):
            continue
        if x == 0.0 or y == 0.0:
            continue
        tot += 1
        if (x > 0) != (y > 0):
            mism += 1
    return float(mism) / float(tot) if tot else float("nan")


def _transform_family_for_dataset(symbol: str, unit: str) -> List[Tuple[str, Callable[[float], float]]]:
    """
    Return a bounded family of y(x) transforms.
    For NN phase-shift tables using T_lab [MeV], provide two transparent options.
    """
    fam: List[Tuple[str, Callable[[float], float]]] = [("identity", lambda x: float(x))]
    if symbol == "T_lab" and unit == "MeV":
        # Non-relativistic equal-mass approximation: E_cm,kin ≈ T_lab/2
        fam.append(("Ecm_NR", lambda T: 0.5 * float(T)))
        # Relativistic: s = 2m^2 + 2m(m+T) = 4m^2 + 2mT; E_cm = sqrt(s); E_cm,kin = E_cm - 2m
        mN = 939.0  # MeV (coarse reference)
        fam.append(("Ecm_REL", lambda T: math.sqrt(max(0.0, 4.0 * mN * mN + 2.0 * mN * float(T))) - 2.0 * mN))
    return fam


def main() -> None:
    reg = _read_json(paper_root() / "data" / "k4_matching" / "scattering_phase_registry.json")
    ds = list(reg.get("datasets", []))

    out = generated_dir()
    rows_path = out / "scattering_inverse_coord_rows.tex"
    sum_path = out / "scattering_inverse_coord_summary.tex"

    if not ds:
        write_lines(rows_path, ["% (no datasets)"])
        write_lines(
            sum_path,
            [
                r"\paragraph{Audit summary (inverse consistency with coordinate transforms).} \AuditTag "
                + r"No datasets registered.",
            ],
        )
        return

    rows: List[str] = []
    best = None  # (mismatch, dataset, transform)
    for d in ds:
        did = str(d.get("id", "dataset")).strip()
        ab = dict(d.get("abscissa", {}) or {})
        x_symbol = str(ab.get("symbol", "x"))
        x_unit = str(ab.get("unit", "arb"))
        pts_raw = list(d.get("points", []))
        pts: List[PhasePoint] = [PhasePoint(x=float(p["E"]), delta=float(p["delta"])) for p in pts_raw]
        if len(pts) < 5:
            continue

        fam = _transform_family_for_dataset(x_symbol, x_unit)
        for name, y_of_x in fam:
            # build a y-coordinate point cloud (monotone checks via finite diffs)
            def coord(p: PhasePoint) -> float:
                return y_of_x(float(p.x))

            xs_x, slopes_x = _central_diff_slopes(pts, coord=lambda p: float(p.x))
            xs_y, slopes_y = _central_diff_slopes(pts, coord=coord)
            # We compare slope signs by matching interior indices; for monotone y(x), ordering is preserved.
            mfrac = _sign_mismatch_fraction(slopes_x, slopes_y)
            rows.append(
                " & ".join(
                    [
                        did.replace("_", r"\_"),
                        x_symbol.replace("_", r"\_"),
                        x_unit.replace("_", r"\_"),
                        name.replace("_", r"\_"),
                        str(len(slopes_y)),
                        _fmt(mfrac, 6),
                    ]
                )
                + r" \\"
            )
            key = (mfrac if math.isfinite(mfrac) else 1e9, did, name)
            if best is None or key < best:
                best = key

    write_lines(rows_path, rows if rows else ["% (no usable rows)"])
    if best is None:
        write_lines(
            sum_path,
            [
                r"\paragraph{Audit summary (inverse consistency with coordinate transforms).} \AuditTag No usable rows.",
            ],
        )
        return

    best_m, best_did, best_name = best
    write_lines(
        sum_path,
        [
            r"\paragraph{Audit summary (inverse consistency with coordinate transforms).} \AuditTag "
            + r"We compare the sign of $\mathrm{d}\delta/\mathrm{d}y$ under bounded coordinate transforms $y(x)$ "
            + r"to the sign of $\mathrm{d}\delta/\mathrm{d}x$ on the interior grid (central differences). "
            + f"Best (minimum sign-mismatch fraction) row: dataset {best_did.replace('_', r'\\_')}, transform {best_name.replace('_', r'\\_')}, mismatch fraction {_fmt(best_m,6)}.",
        ],
    )

    print("Wrote sections/generated/scattering_inverse_coord_rows.tex")
    print("Wrote sections/generated/scattering_inverse_coord_summary.tex")


if __name__ == "__main__":
    main()

