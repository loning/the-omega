# -*- coding: utf-8 -*-
"""
Deterministic scan: trapping transition versus horizon occupancy (full-fusion, metrics-only).

This script runs the full-fusion interface in FULL_FUSION_MODE=metrics for a small,
auditable grid of (m_window, I_obs, c) settings and records:
  - horizon occupancy fraction f_hor
  - delay proxies (free vs trapped)
  - a transition proxy Δτ := τ_trap - τ_free

Outputs (LaTeX fragments):
  - sections/generated/full_fusion_trapping_transition_scan_rows.tex
  - sections/generated/full_fusion_trapping_transition_scan_summary.tex

Optional figure (requires matplotlib):
  - figures/full_fusion_trapping_transition.png

Design:
  - deterministic; small grid; no timestamps
  - does not modify the manuscript's default full-fusion artifacts (uses metrics-only JSON)
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from common_paths import figures_dir, generated_dir
from common_tex import write_lines


def _fmt(x: float, nd: int = 6) -> str:
    return f"{float(x):.{int(nd)}f}"


@dataclass(frozen=True)
class Case:
    n: int
    m_window: int
    i_obs: int
    c: int
    steps: int


def _cases() -> List[Case]:
    # Keep it small and auditable.
    n = 6
    steps = 2000  # faster than the default 8000; still long enough to see trapping in this toy.
    ms = [4, 6, 8, 10, 12, 16]
    iobs = [64, 1024, 1_000_000]
    c = 16
    return [Case(n=n, m_window=m, i_obs=i, c=c, steps=steps) for m in ms for i in iobs]


def _run_one(cs: Case) -> Dict[str, float]:
    env = dict(os.environ)
    env["FULL_FUSION_MODE"] = "metrics"
    env["FULL_FUSION_N"] = str(cs.n)
    env["FULL_FUSION_M_WINDOW"] = str(cs.m_window)
    env["FULL_FUSION_I_OBS"] = str(cs.i_obs)
    env["FULL_FUSION_MARGIN_C"] = str(cs.c)
    env["FULL_FUSION_STEPS"] = str(cs.steps)
    env["FULL_FUSION_SAMPLE_EVERY"] = str(cs.steps)

    # Paper root is the directory that contains scripts/ and sections/.
    # generated_dir() points to .../sections/generated, so go up twice.
    paper_root = str(generated_dir().parent.parent)
    cmd = ["python3", "scripts/exp_full_fusion_bh_wormhole_measurement.py"]
    out = subprocess.check_output(cmd, cwd=paper_root, env=env, text=True)
    payload = json.loads(out.strip())
    return {k: float(v) for (k, v) in payload.items() if isinstance(v, (int, float))}


def main() -> None:
    rows_tex: List[str] = []
    pts: List[Tuple[float, float]] = []  # (f_hor, delta_tau)

    for cs in _cases():
        p = _run_one(cs)
        f = float(p["horizon_frac_on"])
        tau_free = float(p["delay_free_on"])
        tau_trap = float(p["delay_trap_on"])
        delta_tau = tau_trap - tau_free
        pts.append((f, delta_tau))

        rows_tex.append(
            " & ".join(
                [
                    str(cs.n),
                    str(cs.m_window),
                    str(cs.i_obs),
                    str(cs.c),
                    _fmt(f, 6),
                    _fmt(tau_free, 6),
                    _fmt(tau_trap, 6),
                    _fmt(delta_tau, 6),
                ]
            )
            + r" \\"
        )

    rows_tex.append(r"\bottomrule")
    write_lines(generated_dir() / "full_fusion_trapping_transition_scan_rows.tex", rows_tex)

    summary = (
        r"\paragraph{Audit summary (trapping transition scan).} \AuditTag "
        r"This scan runs the full-fusion interface in \texttt{FULL\_FUSION\_MODE=metrics} "
        r"over a small grid of $(n,m,I_{\mathrm{obs}},c)$ settings and records the horizon occupancy "
        r"$f_{\mathrm{hor}}$ together with delay proxies and the transition proxy "
        r"$\Delta\tau=\tau_{\mathrm{trap}}-\tau_{\mathrm{free}}$. "
        r"Rows are generated deterministically by \texttt{scripts/exp\_full\_fusion\_trapping\_transition\_scan.py}."
    )
    write_lines(generated_dir() / "full_fusion_trapping_transition_scan_summary.tex", [summary])

    # Optional figure.
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return

    pts_sorted = sorted(pts, key=lambda t: t[0])
    fx = [t[0] for t in pts_sorted]
    dy = [t[1] for t in pts_sorted]

    fig, ax = plt.subplots(figsize=(6.8, 4.0), dpi=160)
    ax.plot(fx, dy, marker="o", linewidth=1.5)
    ax.set_xlabel(r"horizon occupancy $f_{\mathrm{hor}}$")
    ax.set_ylabel(r"delay gap $\Delta\tau=\tau_{\mathrm{trap}}-\tau_{\mathrm{free}}$")
    ax.set_title("Full-fusion trapping transition proxy vs occupancy (metrics-only scan)")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    out = figures_dir() / "full_fusion_trapping_transition.png"
    fig.savefig(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

