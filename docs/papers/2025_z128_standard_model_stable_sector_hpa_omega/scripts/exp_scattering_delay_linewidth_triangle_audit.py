#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Triangle audit: phase -> delay proxy vs linewidth proxy (and inverse-consistency context).

We use the vendored scattering phase registry:
  data/k4_matching/scattering_phase_registry.json

For datasets that provide a resonance gamma metadata:
  - Estimate tau_phase at/near E0 by bounded window slopes (k=1..3) on delta(E).
    Use tau_phase := 2 d(delta)/dE (proxy convention).
  - Compute linewidth proxy tau_gamma := 4/gamma (as documented in the registry note).
  - Report abs-log mismatch on magnitudes, plus the sign of tau_phase.

This produces a deterministic, bounded-family comparison that ties together:
  - phase->delay derivative interface
  - linewidth proxy interface

Outputs:
  - sections/generated/scattering_delay_linewidth_triangle_rows.tex
  - sections/generated/scattering_delay_linewidth_triangle_summary.tex
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from common_paths import generated_dir, paper_root
from common_tex import write_lines


@dataclass(frozen=True)
class PhasePoint:
    E: float
    delta: float


def _read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


def _local_linear_slope(ps: List[PhasePoint], E0: float, k: int) -> Optional[float]:
    if len(ps) < 2 * k + 1:
        return None
    pts = sorted(ps, key=lambda p: p.E)
    j = min(range(len(pts)), key=lambda i: abs(pts[i].E - E0))
    lo = j - int(k)
    hi = j + int(k)
    if lo < 0 or hi >= len(pts):
        return None
    xs = [float(pts[i].E) for i in range(lo, hi + 1)]
    ys = [float(pts[i].delta) for i in range(lo, hi + 1)]
    xbar = sum(xs) / float(len(xs))
    ybar = sum(ys) / float(len(ys))
    num = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
    den = sum((x - xbar) * (x - xbar) for x in xs)
    if den == 0.0:
        return None
    return float(num / den)


def main() -> None:
    reg = _read_json(paper_root() / "data" / "k4_matching" / "scattering_phase_registry.json")
    ds = list(reg.get("datasets", []))

    out = generated_dir()
    rows_path = out / "scattering_delay_linewidth_triangle_rows.tex"
    sum_path = out / "scattering_delay_linewidth_triangle_summary.tex"

    rows: List[str] = []
    best = None  # (abslog, dataset_id, k)
    eps = 1e-12

    for d in ds:
        did = str(d.get("id", "dataset")).strip()
        res = list(d.get("resonances", []) or [])
        if not res:
            continue
        pts_raw = list(d.get("points", []))
        pts: List[PhasePoint] = [PhasePoint(E=float(p["E"]), delta=float(p["delta"])) for p in pts_raw]
        if len(pts) < 7:
            continue

        # Use first resonance for this audit row family.
        r0 = dict(res[0])
        E0 = float(r0.get("E0", 0.0))
        gamma = float(r0.get("gamma", float("nan")))
        if not math.isfinite(gamma) or gamma <= 0.0:
            continue
        tau_gamma = 4.0 / float(gamma)

        for k in (1, 2, 3):
            slope = _local_linear_slope(pts, E0=E0, k=int(k))
            if slope is None:
                continue
            tau_phase = 2.0 * float(slope)
            abslog = abs(math.log((abs(tau_phase) + eps) / (abs(tau_gamma) + eps)))
            rows.append(
                " & ".join(
                    [
                        did.replace("_", r"\_"),
                        _fmt(E0, 6),
                        _fmt(gamma, 6),
                        str(int(k)),
                        _fmt(tau_phase, 6),
                        _fmt(tau_gamma, 6),
                        _fmt(abslog, 6),
                    ]
                )
                + r" \\"
            )
            key = (abslog, did, int(k))
            if best is None or key < best:
                best = key

    write_lines(rows_path, rows if rows else ["% (no resonance-tagged datasets)"])
    if best is None:
        write_lines(
            sum_path,
            [
                r"\paragraph{Audit summary (triangle: phase$\to$delay vs linewidth proxy).} \AuditTag "
                + r"No resonance-tagged datasets available in the registry.",
            ],
        )
        return

    best_abslog, best_did, best_k = best
    write_lines(
        sum_path,
        [
            r"\paragraph{Audit summary (triangle: phase$\to$delay vs linewidth proxy).} \AuditTag "
            + r"For datasets with a coarse resonance linewidth proxy $\gamma$, we compare "
            + r"$\tau_{\mathrm{phase}}\approx 2\,\mathrm{d}\delta/\mathrm{d}E$ to $\tau_\gamma\approx 4/\gamma$ "
            + r"under a bounded local-linear window family $k\in\{1,2,3\}$. "
            + f"Best abs-log mismatch row: dataset {best_did.replace('_', r'\_')}, k={int(best_k)}, abs-log mismatch {_fmt(best_abslog,6)}.",
        ],
    )

    print("Wrote sections/generated/scattering_delay_linewidth_triangle_rows.tex")
    print("Wrote sections/generated/scattering_delay_linewidth_triangle_summary.tex")


if __name__ == "__main__":
    main()

