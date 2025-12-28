#!/usr/bin/env python3
"""
CAP-II reproducibility script:
Synthetic end-to-end demo (graph/scheduler -> kappa(x) -> WS delay -> inferred lapse).

Data source:
  - A toy "physical interaction graph" is represented by per-location primitive edge costs,
    provided as a CSV with columns: r,kappa.
  - Interpreting each row as a localized two-site primitive with tick cost kappa,
    the compilation depth for the corresponding local task is kappa by definition.

Scattering interface:
  - For each location, we simulate a single-channel unitary Breit--Wigner scatterer
    whose linewidth is set so that tau_WS(E0) = kappa * tau0 in the ideal limit:
        gamma = 4*hbar / (kappa*tau0)
  - We then estimate dS/dE by a central difference and compute
        Q(E) = -i*hbar * S(E)^* * dS/dE
    so tau_WS(E0)=Q(E0) in the 1-channel convention.

Outputs:
  - LaTeX table rows for per-radius comparisons.
  - A one-row LaTeX summary of RMSE/max errors.

This script is deterministic given --seed.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Point:
    r: float
    kappa: float


def _default_out_rows() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent / "sections" / "generated" / "demo_end_to_end_rows.tex"


def _default_out_metrics() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent / "sections" / "generated" / "demo_end_to_end_metrics.tex"


def read_points(path: Path) -> list[Point]:
    pts: list[Point] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV must have a header row")
        field_map = {name.strip().lower(): name for name in reader.fieldnames}
        r_key = field_map.get("r") or field_map.get("radius")
        k_key = field_map.get("kappa") or field_map.get("weight") or field_map.get("tick_cost")
        if r_key is None or k_key is None:
            raise ValueError("CSV must contain columns r (or radius) and kappa (or weight/tick_cost)")
        for rec in reader:
            r = float(rec[r_key])
            kappa = float(rec[k_key])
            if kappa <= 0.0:
                raise ValueError("kappa must be positive")
            pts.append(Point(r=r, kappa=kappa))
    if not pts:
        raise ValueError("No data rows found")
    pts.sort(key=lambda p: p.r)
    return pts


def S_breit_wigner(E: float, E0: float, gamma: float) -> complex:
    if gamma <= 0.0:
        raise ValueError("gamma must be positive")
    z = E - E0
    a = 0.5 * gamma
    return complex(z, -a) / complex(z, a)


def add_phase_noise(S: complex, rng: random.Random, sigma_phase: float) -> complex:
    if sigma_phase <= 0.0:
        return S
    phi = rng.gauss(0.0, sigma_phase)
    return S * complex(math.cos(phi), math.sin(phi))


def dS_dE_central(E: float, E0: float, gamma: float, dE: float, rng: random.Random, sigma_phase: float) -> complex:
    if dE <= 0.0:
        raise ValueError("dE must be positive")
    Sp = add_phase_noise(S_breit_wigner(E + dE, E0, gamma), rng, sigma_phase)
    Sm = add_phase_noise(S_breit_wigner(E - dE, E0, gamma), rng, sigma_phase)
    return (Sp - Sm) / (2.0 * dE)


def rmse(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("length mismatch")
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / float(len(a)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--in_csv",
        type=Path,
        default=Path("data/demo_graph_edges.csv"),
        help="Input CSV with columns r,kappa representing per-location primitive edge tick cost.",
    )
    parser.add_argument("--out_rows", type=Path, default=_default_out_rows())
    parser.add_argument("--out_metrics", type=Path, default=_default_out_metrics())
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--E0", type=float, default=0.0)
    parser.add_argument("--hbar", type=float, default=1.0)
    parser.add_argument("--tau0", type=float, default=1.0)
    parser.add_argument("--dE", type=float, default=1.0e-6)
    parser.add_argument(
        "--sigma_phase",
        type=float,
        default=0.0,
        help="Stddev of added phase noise to each sampled S(E) point (radians). 0 disables noise.",
    )
    parser.add_argument(
        "--r_ref",
        type=float,
        default=None,
        help="Reference radius for normalization. If omitted, uses the largest radius in the CSV.",
    )
    args = parser.parse_args()

    pts = read_points(args.in_csv)
    rng = random.Random(args.seed)

    # reference point
    r_ref: float
    if args.r_ref is None:
        r_ref = pts[-1].r
    else:
        r_ref = float(args.r_ref)

    def _find_ref(points: list[Point], r: float) -> Point:
        # exact match preferred; otherwise nearest
        best = points[0]
        best_d = abs(points[0].r - r)
        for p in points[1:]:
            d = abs(p.r - r)
            if d < best_d:
                best, best_d = p, d
        return best

    p_ref = _find_ref(pts, r_ref)
    kappa0_true = p_ref.kappa

    # simulate WS inference
    kappa_ws: list[float] = []
    for p in pts:
        gamma = 4.0 * args.hbar / (p.kappa * args.tau0)
        S0 = add_phase_noise(S_breit_wigner(args.E0, args.E0, gamma), rng, args.sigma_phase)
        dS = dS_dE_central(args.E0, args.E0, gamma, args.dE, rng, args.sigma_phase)
        Q = (-1j) * args.hbar * (S0.conjugate() * dS)
        tau_ws = Q.real
        kappa_ws.append(tau_ws / args.tau0)

    # reference normalization for WS-inferred kappa
    # (same nearest-point rule as above)
    i_ref = min(range(len(pts)), key=lambda i: abs(pts[i].r - p_ref.r))
    kappa0_ws = kappa_ws[i_ref]
    if kappa0_ws <= 0.0:
        raise ValueError("nonpositive inferred kappa0_ws; check dE/sigma_phase settings")

    # build rows
    rows: list[str] = []
    kappa_ratio_true_list: list[float] = []
    kappa_ratio_ws_list: list[float] = []
    lapse_true_list: list[float] = []
    lapse_ws_list: list[float] = []
    rel_lapse_err_list: list[float] = []

    for p, kw in zip(pts, kappa_ws):
        kappa_ratio_true = p.kappa / kappa0_true
        kappa_ratio_ws = kw / kappa0_ws
        lapse_true = 1.0 / kappa_ratio_true
        lapse_ws = 1.0 / kappa_ratio_ws
        rel_lapse_err = abs(lapse_ws - lapse_true) / abs(lapse_true)

        kappa_ratio_true_list.append(kappa_ratio_true)
        kappa_ratio_ws_list.append(kappa_ratio_ws)
        lapse_true_list.append(lapse_true)
        lapse_ws_list.append(lapse_ws)
        rel_lapse_err_list.append(rel_lapse_err)

        rows.append(
            f"{p.r:.6g} & {kappa_ratio_true:.8f} & {kappa_ratio_ws:.8f} & {lapse_true:.8f} & {lapse_ws:.8f} & {rel_lapse_err:.2e} \\\\"
        )

    # metrics
    rmse_kappa_ratio = rmse(kappa_ratio_true_list, kappa_ratio_ws_list)
    rmse_lapse = rmse(lapse_true_list, lapse_ws_list)
    max_rel_lapse = max(rel_lapse_err_list) if rel_lapse_err_list else 0.0

    out_rows: Path = args.out_rows
    out_rows.parent.mkdir(parents=True, exist_ok=True)
    out_rows.write_text("\n".join(rows) + "\n", encoding="utf-8")

    out_metrics: Path = args.out_metrics
    out_metrics.parent.mkdir(parents=True, exist_ok=True)
    out_metrics.write_text(
        f"{len(pts)} & {args.dE:.2e} & {args.sigma_phase:.2e} & {rmse_kappa_ratio:.3e} & {rmse_lapse:.3e} & {max_rel_lapse:.3e} \\\\\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()


