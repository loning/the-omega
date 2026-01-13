# -*- coding: utf-8 -*-
"""
Adaptive wormhole parameter search (deterministic, audit-facing):
  - Uses full-fusion metrics-only mode as an oracle.
  - Searches within a bounded parameter box under an E_wh budget.
  - Produces recommended configurations for two objectives:
      (A) maximize Δdelay_trap
      (B) maximize ΔE_emit
  - Then runs full (non-metrics) full-fusion for each recommended config with tagged outputs
    to produce complete tables/figures without overwriting defaults.

Outputs:
  - sections/generated/full_fusion_wormhole_adaptive_rows.tex
  - sections/generated/full_fusion_wormhole_adaptive_summary.tex
  - sections/generated/full_fusion_opt_delay_rows.tex (+ nowh/compare/summary)
  - sections/generated/full_fusion_opt_emit_rows.tex (+ nowh/compare/summary)
  - figures/full_fusion_opt_delay.png
  - figures/full_fusion_opt_emit.png
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Tuple

from common_paths import generated_dir
from common_progress import ProgressEvery
from common_tex import write_lines


def _fmt(x: float, nd: int = 6) -> str:
    return f"{float(x):.{int(nd)}f}"


@dataclass(frozen=True)
class Oracle:
    e_wh: float
    d_delay_trap: float
    d_emit: float
    d_delaywh_trap: float
    jump_rate: float


def _run_metrics(
    *,
    ptr_eps: float,
    ptr_radius: float,
    ptr_jump_rate0: float,
    steps: int,
    dt: float,
) -> Oracle:
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

    d_delay_trap = float(payload["delay_trap_on"]) - float(payload["delay_trap_off"])
    d_emit = float(payload["E_emit_on"]) - float(payload["E_emit_off"])
    d_delaywh_trap = float(payload["delay_wh_trap_on"]) - float(payload["delay_wh_trap_off"])
    return Oracle(
        e_wh=float(payload["E_wh_on"]),
        d_delay_trap=d_delay_trap,
        d_emit=d_emit,
        d_delaywh_trap=d_delaywh_trap,
        jump_rate=float(payload["wh_jump_rate_on"]),
    )


def _run_full(*, tag: str, ptr_eps: float, ptr_radius: float, ptr_jump_rate0: float) -> None:
    env = dict(os.environ)
    env.pop("FULL_FUSION_MODE", None)
    env["FULL_FUSION_TAG"] = tag
    env["FULL_FUSION_PTR_EPS"] = str(ptr_eps)
    env["FULL_FUSION_PTR_RADIUS"] = str(ptr_radius)
    env["FULL_FUSION_PTR_JUMP_RATE0"] = str(ptr_jump_rate0)
    here = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(here, "exp_full_fusion_bh_wormhole_measurement.py")
    subprocess.check_call(["python3", script], env=env)


def main() -> None:
    # Budget + oracle budget (smaller by default; override via env if needed).
    steps = int(os.environ.get("FULL_FUSION_ADAPTIVE_STEPS", "1400"))
    dt = float(os.environ.get("FULL_FUSION_ADAPTIVE_DT", "0.02"))
    ewh_budget = float(os.environ.get("FULL_FUSION_EWH_BUDGET", "2.0"))
    max_candidates = int(os.environ.get("FULL_FUSION_ADAPTIVE_MAX", "64"))

    # Seed from the sweep/Pareto artifacts (fast) and refine locally.
    # This is a deterministic pruning: we never explore the full cartesian box.
    seed_files = [
        generated_dir() / "full_fusion_wormhole_pareto_rows.tex",
        generated_dir() / "full_fusion_wormhole_pareto_emit_rows.tex",
        generated_dir() / "full_fusion_wormhole_pareto_delay_rows.tex",
    ]

    def _parse_seed_rows(path) -> List[Tuple[float, float, float]]:
        if not path.is_file():
            return []
        out: List[Tuple[float, float, float]] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            s = raw.strip()
            if not s or s.startswith("%"):
                continue
            # Format: eps & radius & jump & ... \\
            parts = [p.strip() for p in s.split("&")]
            if len(parts) < 3:
                continue
            try:
                e = float(parts[0])
                r = float(parts[1])
                j = float(parts[2])
            except Exception:
                continue
            out.append((e, r, j))
        return out

    seeds: List[Tuple[float, float, float]] = []
    for p in seed_files:
        seeds.extend(_parse_seed_rows(p))

    # Conservative fallback if sweep artifacts are missing.
    if not seeds:
        seeds = [
            (0.0, 3.5, 0.0),
            (0.10, 2.5, 0.22),
            (0.20, 2.5, 0.22),
            (0.35, 2.5, 0.22),
        ]

    # Local refinement neighborhood around seeds.
    de_list = [0.0, 0.05, -0.05, 0.10, -0.10]
    dr_list = [0.0, 0.5, -0.5, 1.0, -1.0]
    dj_list = [0.0, 0.10, -0.10, 0.20, -0.20]

    def _clip(e: float, r: float, j: float) -> Tuple[float, float, float]:
        e = max(0.0, min(0.45, e))
        r = max(1.5, min(6.5, r))
        j = max(0.0, min(0.50, j))
        # snap to stable decimals to reduce duplicates
        return (round(e, 3), round(r, 2), round(j, 3))

    # Deduplicate deterministically.
    seen: Dict[Tuple[int, int, int], bool] = {}
    uniq: List[Tuple[float, float, float]] = []
    for (e0, r0, j0) in seeds:
        for de in de_list:
            for dr in dr_list:
                for dj in dj_list:
                    e, r, j = _clip(float(e0) + de, float(r0) + dr, float(j0) + dj)
                    key = (int(round(1000 * e)), int(round(100 * r)), int(round(1000 * j)))
                    if key in seen:
                        continue
                    seen[key] = True
                    uniq.append((e, r, j))

    # Hard pruning: keep only the first N in lexicographic order for determinism.
    uniq = sorted(uniq)[: max(1, max_candidates)]

    prog = ProgressEvery("full_fusion_wormhole_adaptive", total=len(uniq))
    prog.start()

    best_delay = None  # (score, params, oracle)
    best_emit = None

    memo: Dict[Tuple[int, int, int, int], Oracle] = {}
    rows: List[str] = []
    for i, (e, r, j) in enumerate(uniq, start=1):
        prog.maybe(i, extra=f"eps={e:.3f} r={r:.2f} jr={j:.3f}")
        mkey = (
            int(round(1000 * e)),
            int(round(100 * r)),
            int(round(1000 * j)),
            int(steps),
        )
        o = memo.get(mkey)
        if o is None:
            o = _run_metrics(ptr_eps=e, ptr_radius=r, ptr_jump_rate0=j, steps=steps, dt=dt)
            memo[mkey] = o
        if o.e_wh > ewh_budget + 1e-9:
            continue
        # objectives
        score_delay = o.d_delay_trap
        score_emit = o.d_emit
        cand = (e, r, j)
        if best_delay is None or (score_delay, -o.e_wh) > (best_delay[0], -best_delay[2].e_wh):
            best_delay = (score_delay, cand, o)
        if best_emit is None or (score_emit, -o.e_wh) > (best_emit[0], -best_emit[2].e_wh):
            best_emit = (score_emit, cand, o)

        rows.append(
            " & ".join(
                [
                    _fmt(e, 3),
                    _fmt(r, 2),
                    _fmt(j, 3),
                    _fmt(o.e_wh, 6),
                    _fmt(o.d_delay_trap, 6),
                    _fmt(o.d_delaywh_trap, 6),
                    _fmt(o.d_emit, 6),
                    _fmt(o.jump_rate, 6),
                ]
            )
            + r" \\"
        )

    prog.done(extra=f"kept_rows={len(rows)} budget={ewh_budget:.3f}")

    write_lines(generated_dir() / "full_fusion_wormhole_adaptive_rows.tex", rows if rows else ["% (no rows)"])

    if best_delay is None or best_emit is None:
        summary = [
            r"\paragraph{Audit summary (adaptive wormhole search).} \AuditTag No feasible candidates under the declared $E_{\mathrm{wh}}$ budget."
        ]
        write_lines(generated_dir() / "full_fusion_wormhole_adaptive_summary.tex", summary)
        return

    sd, (ed, rd, jd), od = best_delay
    se, (ee, re, je), oe = best_emit

    # Run two full tagged experiments to produce full tables/figures.
    _run_full(tag="opt_delay", ptr_eps=ed, ptr_radius=rd, ptr_jump_rate0=jd)
    _run_full(tag="opt_emit", ptr_eps=ee, ptr_radius=re, ptr_jump_rate0=je)

    summary = [
        r"\paragraph{Audit summary (adaptive wormhole search with full reruns).} \AuditTag "
        r"We search a bounded deterministic candidate set under an explicit budget $E_{\mathrm{wh}}\le "
        + _fmt(ewh_budget, 3)
        + r"$ and select two recommended configurations: "
        r"(A) maximize $\Delta\tau_{\mathrm{trap}}$ and (B) maximize $\Delta E_{\mathrm{emit}}$. "
        r"Full reruns are written with tags \texttt{opt\_delay} and \texttt{opt\_emit} "
        r"to avoid overwriting the default artifacts.",
        rf"\noindent A (opt\_delay): eps={_fmt(ed,3)}, r={_fmt(rd,2)}, jump={_fmt(jd,3)}, "
        rf"$E_{{\mathrm{{wh}}}}={_fmt(od.e_wh,6)}$, $\Delta\tau_{{\mathrm{{trap}}}}={_fmt(od.d_delay_trap,6)}$, "
        rf"$\Delta E_{{\mathrm{{emit}}}}={_fmt(od.d_emit,6)}$.",
        rf"\noindent B (opt\_emit): eps={_fmt(ee,3)}, r={_fmt(re,2)}, jump={_fmt(je,3)}, "
        rf"$E_{{\mathrm{{wh}}}}={_fmt(oe.e_wh,6)}$, $\Delta E_{{\mathrm{{emit}}}}={_fmt(oe.d_emit,6)}$, "
        rf"$\Delta\tau_{{\mathrm{{trap}}}}={_fmt(oe.d_delay_trap,6)}$.",
    ]
    write_lines(generated_dir() / "full_fusion_wormhole_adaptive_summary.tex", summary)


if __name__ == "__main__":
    main()

