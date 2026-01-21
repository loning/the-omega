# -*- coding: utf-8 -*-
"""
Wormhole sweep audit (full fusion):
  - Runs the full fusion experiment in "metrics" mode for a grid of wormhole parameters.
  - Aggregates deltas relative to the wormhole-off baseline.
  - Writes LaTeX table fragments and a simple figure.

Outputs:
  - sections/generated/full_fusion_wormhole_sweep_rows.tex
  - sections/generated/full_fusion_wormhole_sweep_summary.tex
  - sections/generated/full_fusion_wormhole_pareto_rows.tex
  - sections/generated/full_fusion_wormhole_pareto_summary.tex
  - sections/generated/full_fusion_wormhole_pareto_delay_rows.tex
  - sections/generated/full_fusion_wormhole_pareto_delaywh_rows.tex
  - sections/generated/full_fusion_wormhole_pareto_emit_rows.tex
  - sections/generated/full_fusion_wormhole_pareto_jump_rows.tex
  - sections/generated/full_fusion_wormhole_pareto_multi_summary.tex
  - figures/full_fusion_wormhole_sweep.png  (optional; requires matplotlib)
  - figures/full_fusion_wormhole_pareto.png (optional; requires matplotlib)
  - figures/full_fusion_wormhole_pareto_multi.png (optional; requires matplotlib)
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Tuple

from common_paths import figures_dir, generated_dir
from common_progress import ProgressEvery
from common_tex import write_lines


def _fmt(x: float, nd: int = 6) -> str:
    return f"{float(x):.{int(nd)}f}"


@dataclass(frozen=True)
class Metrics:
    ptr_eps: float
    ptr_radius: float
    ptr_jump_rate0: float
    e_emit_on: float
    e_emit_off: float
    e_wh_on: float
    delay_trap_on: float
    delay_trap_off: float
    delay_wh_trap_on: float
    delay_wh_trap_off: float
    wh_jump_rate_on: float
    vis_trap_on: float
    dist_trap_on: float


def _run_metrics(
    *,
    ptr_eps: float,
    ptr_radius: float,
    ptr_jump_rate0: float,
    steps: int,
    dt: float,
) -> Metrics:
    env = dict(os.environ)
    env["FULL_FUSION_MODE"] = "metrics"
    env["FULL_FUSION_PTR_EPS"] = str(ptr_eps)
    env["FULL_FUSION_PTR_RADIUS"] = str(ptr_radius)
    env["FULL_FUSION_PTR_JUMP_RATE0"] = str(ptr_jump_rate0)
    env["FULL_FUSION_STEPS"] = str(int(steps))
    env["FULL_FUSION_DT"] = str(float(dt))

    here = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(here, "exp_full_fusion_bh_wormhole_measurement.py")
    out = subprocess.check_output(["python3", script], env=env, text=True)
    payload = json.loads(out.strip().splitlines()[-1])

    return Metrics(
        ptr_eps=float(payload["ptr_eps"]),
        ptr_radius=float(payload["ptr_radius"]),
        ptr_jump_rate0=float(payload["ptr_jump_rate0"]),
        e_emit_on=float(payload["E_emit_on"]),
        e_emit_off=float(payload["E_emit_off"]),
        e_wh_on=float(payload["E_wh_on"]),
        delay_trap_on=float(payload["delay_trap_on"]),
        delay_trap_off=float(payload["delay_trap_off"]),
        delay_wh_trap_on=float(payload["delay_wh_trap_on"]),
        delay_wh_trap_off=float(payload["delay_wh_trap_off"]),
        wh_jump_rate_on=float(payload["wh_jump_rate_on"]),
        vis_trap_on=float(payload["vis_trap_on"]),
        dist_trap_on=float(payload["dist_trap_on"]),
    )


def main() -> None:
    # Sweep budget: keep it moderate (deterministic, no randomness).
    steps = 3000
    dt = 0.02

    eps_list = [0.0, 0.10, 0.20, 0.35]
    radius_list = [2.5, 3.5, 5.0]
    jump_list = [0.10, 0.22, 0.35]

    # Baseline (wormhole off): fixed reference for deltas.
    base = _run_metrics(ptr_eps=0.0, ptr_radius=3.5, ptr_jump_rate0=0.0, steps=steps, dt=dt)

    rows: List[str] = []
    points: List[Tuple[float, float, float]] = []  # (E_wh, gain, eps)
    best = None  # type: Tuple[float, Metrics] | None
    scored: List[Tuple[float, float, Metrics, float, float, float, float]] = []
    # (E_wh, gain, metrics, d_delay_trap, d_delay_wh_trap, d_emit, d_jump)

    total = len(eps_list) * len(radius_list) * len(jump_list)
    prog = ProgressEvery("full_fusion_wormhole_sweep", total=total)
    prog.start()
    k = 0

    for eps in eps_list:
        for rad in radius_list:
            for jr in jump_list:
                k += 1
                prog.maybe(k, extra=f"eps={eps:.3f} r={rad:.2f} jr={jr:.3f}")
                m = _run_metrics(ptr_eps=eps, ptr_radius=rad, ptr_jump_rate0=jr, steps=steps, dt=dt)
                # Use the baseline "off" metrics reported in the same run to form deltas.
                d_delay_trap = m.delay_trap_on - m.delay_trap_off
                d_delay_wh_trap = m.delay_wh_trap_on - m.delay_wh_trap_off
                d_emit = m.e_emit_on - m.e_emit_off
                d_jump = m.wh_jump_rate_on  # off is always 0 in the current contract

                # A simple auditable gain score: delay gain + emission gain, normalized by (1+E_wh).
                gain = (0.6 * d_delay_trap + 0.4 * d_delay_wh_trap + 0.02 * d_emit) / (1.0 + m.e_wh_on)

                points.append((m.e_wh_on, gain, eps))
                if best is None or gain > best[0]:
                    best = (gain, m)
                scored.append((m.e_wh_on, gain, m, d_delay_trap, d_delay_wh_trap, d_emit, d_jump))

                rows.append(
                    " & ".join(
                        [
                            _fmt(eps, 3),
                            _fmt(rad, 2),
                            _fmt(jr, 3),
                            _fmt(m.e_wh_on, 6),
                            _fmt(d_delay_trap, 6),
                            _fmt(d_delay_wh_trap, 6),
                            _fmt(d_emit, 6),
                            _fmt(d_jump, 6),
                            _fmt(m.vis_trap_on, 6),
                            _fmt(m.dist_trap_on, 6),
                            _fmt(gain, 8),
                        ]
                    )
                    + r" \\"
                )

    write_lines(generated_dir() / "full_fusion_wormhole_sweep_rows.tex", rows if rows else ["% (no rows)"])

    # Pareto frontier: maximize gain, minimize E_wh.
    pareto = []
    best_gain_so_far = -1e99
    for (Ew, g, m, dd, dwh, de, dj) in sorted(scored, key=lambda z: (z[0], -z[1])):
        if g > best_gain_so_far + 1e-12:
            pareto.append((Ew, g, m, dd, dwh, de, dj))
            best_gain_so_far = g

    pareto_rows: List[str] = []
    for (Ew, g, m, dd, dwh, de, dj) in pareto:
        pareto_rows.append(
            " & ".join(
                [
                    _fmt(m.ptr_eps, 3),
                    _fmt(m.ptr_radius, 2),
                    _fmt(m.ptr_jump_rate0, 3),
                    _fmt(Ew, 6),
                    _fmt(dd, 6),
                    _fmt(dwh, 6),
                    _fmt(de, 6),
                    _fmt(dj, 6),
                    _fmt(g, 8),
                ]
            )
            + r" \\"
        )
    write_lines(
        generated_dir() / "full_fusion_wormhole_pareto_rows.tex",
        pareto_rows if pareto_rows else ["% (no pareto rows)"],
    )

    def _pareto_1d(obj_index: int) -> List[Tuple[float, float, Metrics, float, float, float, float]]:
        """
        Return points on the cost-vs-objective frontier:
          - cost = E_wh minimized
          - objective maximized (obj_index selects which d_* value is used)
        obj_index in {0:dd,1:dwh,2:de,3:dj}
        """
        frontier = []
        best_so_far = -1e99
        for (Ew, g, m, dd, dwh, de, dj) in sorted(scored, key=lambda z: (z[0], -z[1])):
            vals = [dd, dwh, de, dj]
            v = float(vals[int(obj_index)])
            if v > best_so_far + 1e-12:
                frontier.append((Ew, v, m, dd, dwh, de, dj))
                best_so_far = v
        return frontier

    f_delay = _pareto_1d(0)
    f_delaywh = _pareto_1d(1)
    f_emit = _pareto_1d(2)
    f_jump = _pareto_1d(3)

    def _write_frontier(name: str, frontier: List[Tuple[float, float, Metrics, float, float, float, float]]) -> None:
        out: List[str] = []
        for (Ew, v, m, dd, dwh, de, dj) in frontier:
            out.append(
                " & ".join(
                    [
                        _fmt(m.ptr_eps, 3),
                        _fmt(m.ptr_radius, 2),
                        _fmt(m.ptr_jump_rate0, 3),
                        _fmt(Ew, 6),
                        _fmt(v, 6),
                    ]
                )
                + r" \\"
            )
        write_lines(generated_dir() / f"full_fusion_wormhole_pareto_{name}_rows.tex", out if out else ["% (empty)"])

    _write_frontier("delay", f_delay)
    _write_frontier("delaywh", f_delaywh)
    _write_frontier("emit", f_emit)
    _write_frontier("jump", f_jump)

    if best is None:
        best_line = "none"
    else:
        _, bm = best
        best_line = (
            f"best=(eps={bm.ptr_eps:.3f}, radius={bm.ptr_radius:.2f}, jump_rate0={bm.ptr_jump_rate0:.3f}), "
            f"E_wh={bm.e_wh_on:.6f}"
        )

    summary = [
        r"\paragraph{Audit summary (wormhole parameter sweep on full fusion).} \AuditTag "
        r"We run the full-fusion experiment in a metrics-only mode over a bounded grid of wormhole parameters "
        r"$(\varepsilon_{\mathrm{ptr}}, r_{\mathrm{ptr}}, \lambda_{\mathrm{jump}})$ and report deltas relative to the "
        r"wormhole-off baseline. Columns include $E_{\mathrm{wh}}$ (explicit shortcut cost ledger), delay gains "
        r"(including the separate wormhole-induced component $\tau_{\mathrm{wh}}$), a pointer-jump exit rate "
        r"(wormhole-assisted leakage), and measurement proxies $(V,D)$ with $V^2+D^2\le 1$. "
        + rf"Grid: eps={len(eps_list)}, radius={len(radius_list)}, jump={len(jump_list)}; {best_line}.",
    ]
    write_lines(generated_dir() / "full_fusion_wormhole_sweep_summary.tex", summary)

    pareto_summary = [
        r"\paragraph{Audit summary (wormhole Pareto frontier: gain vs cost).} \AuditTag "
        r"We extract the Pareto frontier over the bounded sweep grid using the two objectives "
        r"(maximize gain score; minimize $E_{\mathrm{wh}}$). "
        + rf"Frontier size: {len(pareto)} points (written to \texttt{{full\_fusion\_wormhole\_pareto\_rows.tex}}).",
    ]
    write_lines(generated_dir() / "full_fusion_wormhole_pareto_summary.tex", pareto_summary)

    multi_summary = [
        r"\paragraph{Audit summary (wormhole multi-objective frontiers vs cost).} \AuditTag "
        r"In addition to the scalar gain score, we report 1D cost frontiers for each observable delta: "
        r"$\Delta\tau_{\mathrm{trap}}$, $\Delta\tau_{\mathrm{wh,trap}}$, $\Delta E_{\mathrm{emit}}$, and the pointer-jump exit rate. "
        + rf"Frontier sizes: delay={len(f_delay)}, delaywh={len(f_delaywh)}, emit={len(f_emit)}, jump={len(f_jump)}.",
    ]
    write_lines(generated_dir() / "full_fusion_wormhole_pareto_multi_summary.tex", multi_summary)

    # Optional figure.
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return

    fig = plt.figure(figsize=(8.2, 5.6))
    ax = fig.add_subplot(1, 1, 1)
    for eps in sorted(set([p[2] for p in points])):
        xs = [p[0] for p in points if p[2] == eps]
        ys = [p[1] for p in points if p[2] == eps]
        ax.scatter(xs, ys, s=18, label=fr"$\varepsilon_{{\mathrm{{ptr}}}}={eps:.2f}$")
    if pareto:
        px = [p[0] for p in pareto]
        py = [p[1] for p in pareto]
        ax.plot(px, py, "k-", linewidth=1.2, alpha=0.8, label="Pareto frontier")
    ax.set_xlabel(r"$E_{\mathrm{wh}}$ (shortcut cost ledger)")
    ax.set_ylabel("gain score (audit)")
    ax.set_title("wormhole sweep: gain vs cost")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, loc="best")
    figures_dir().mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(figures_dir() / "full_fusion_wormhole_sweep.png", dpi=170)
    plt.close(fig)

    fig2 = plt.figure(figsize=(7.8, 5.2))
    ax2 = fig2.add_subplot(1, 1, 1)
    ax2.scatter([p[0] for p in points], [p[1] for p in points], s=14, alpha=0.35)
    if pareto:
        ax2.plot([p[0] for p in pareto], [p[1] for p in pareto], "r-", linewidth=1.8)
        ax2.scatter([p[0] for p in pareto], [p[1] for p in pareto], s=26, color="r", label="Pareto")
    ax2.set_xlabel(r"$E_{\mathrm{wh}}$")
    ax2.set_ylabel("gain score")
    ax2.set_title("wormhole Pareto frontier")
    ax2.grid(True, alpha=0.25)
    ax2.legend(fontsize=9, loc="best")
    fig2.tight_layout()
    fig2.savefig(figures_dir() / "full_fusion_wormhole_pareto.png", dpi=170)
    plt.close(fig2)

    # Multi-objective frontier figure (2x2).
    fig3 = plt.figure(figsize=(11.0, 7.5))
    axes = [
        fig3.add_subplot(2, 2, 1),
        fig3.add_subplot(2, 2, 2),
        fig3.add_subplot(2, 2, 3),
        fig3.add_subplot(2, 2, 4),
    ]
    Ew_all = [s[0] for s in scored]
    dd_all = [s[3] for s in scored]
    dwh_all = [s[4] for s in scored]
    de_all = [s[5] for s in scored]
    dj_all = [s[6] for s in scored]

    panels = [
        (axes[0], r"$\Delta\tau_{\mathrm{trap}}$", dd_all, f_delay),
        (axes[1], r"$\Delta\tau_{\mathrm{wh,trap}}$", dwh_all, f_delaywh),
        (axes[2], r"$\Delta E_{\mathrm{emit}}$", de_all, f_emit),
        (axes[3], r"$\Delta \mathrm{rate}_{\mathrm{jump}}$", dj_all, f_jump),
    ]
    for ax, ylab, y_all, fr in panels:
        ax.scatter(Ew_all, y_all, s=12, alpha=0.25)
        if fr:
            ax.plot([p[0] for p in fr], [p[1] for p in fr], "r-", linewidth=2.0)
            ax.scatter([p[0] for p in fr], [p[1] for p in fr], s=30, color="r")
        ax.set_xlabel(r"$E_{\mathrm{wh}}$")
        ax.set_ylabel(ylab)
        ax.grid(True, alpha=0.25)
    fig3.suptitle("wormhole 1D frontiers vs cost (bounded sweep)")
    fig3.tight_layout(rect=(0, 0, 1, 0.96))
    fig3.savefig(figures_dir() / "full_fusion_wormhole_pareto_multi.png", dpi=170)
    plt.close(fig3)

    prog.done(extra=f"pareto_gain={len(pareto)} pareto_multi=({len(f_delay)},{len(f_delaywh)},{len(f_emit)},{len(f_jump)})")

if __name__ == "__main__":
    main()

