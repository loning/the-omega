# -*- coding: utf-8 -*-
"""
Scattering-process vs black-hole-process equivalence audit (toy, deterministic).

Purpose (CS language):
  Compare two discrete tick-time queue processes under a common audit vocabulary:
    - saturation/backlog (trap-like behavior) via queue-length exceedance fraction,
    - external record algebra A_out via an emitted record stream,
    - a simple compressibility proxy on the record stream.

Models:
  (1) Scattering queue: same as exp_scattering_process_delay_queue_sim.py
      (2-channel S(omega) proxy, Wigner--Smith delay sets service cost).
  (2) Black-hole queue (toy): an internal microstate queue with one radiation emission per tick;
      absorption is periodic; the outside sees only a stable-type record stream w_t in X_m.

This script does NOT claim a theorem-level equivalence. It provides an auditable, reproducible
comparison artifact for the interface narrative "unsaturated delay vs saturated delay/horizon".

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.

Outputs (LaTeX fragments):
  - sections/generated/scattering_bh_queue_equivalence_rows.tex
  - sections/generated/scattering_bh_queue_equivalence_summary.tex
"""

from __future__ import annotations

import math
import zlib
from dataclasses import dataclass
from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines
from protocol_kernel import fold_m


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


class _LCG:
    def __init__(self, seed: int) -> None:
        self._s = int(seed) & 0xFFFFFFFFFFFFFFFF

    def u01(self) -> float:
        self._s = (6364136223846793005 * self._s + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        return float((self._s >> 11) & ((1 << 53) - 1)) / float(1 << 53)

    def randint(self, n: int) -> int:
        if n <= 0:
            raise ValueError("n must be positive")
        return int(self.u01() * float(n))


def _compress_ratio_ascii(s: str) -> float:
    b = s.encode("ascii", errors="ignore")
    if not b:
        return float("nan")
    c = zlib.compress(b, level=9)
    return float(len(c) / float(len(b)))


@dataclass(frozen=True)
class ScatStats:
    arrival_period: int
    service_scale: float
    loss_amp: float
    eta_min: float
    mean_tau: float
    frac_abs: float
    max_q: int
    frac_over_q: float
    comp_ratio: float


def _run_scattering_queue(
    *,
    ticks: int,
    omega_grid: List[float],
    arrival_period: int,
    service_scale: float,
    loss_amp: float,
    q_star: int,
    seed: int,
) -> ScatStats:
    # Import locally to keep dependency explicit and avoid code duplication.
    from exp_scattering_process_delay_queue_sim import (  # type: ignore
        ScatteringModel,
        _eta,
        _tau_ws_trace,
        _simulate_case,
        cap_select_scattering_carrier,
    )

    base, _gamma_ref, _abslog_ref, _gap_ref, _scope_ref = cap_select_scattering_carrier(
        loss_amp=float(loss_amp), omega_center=1.35
    )

    stats, record = _simulate_case(
        m=base,
        omega_grid=omega_grid,
        ticks=int(ticks),
        arrival_period=int(arrival_period),
        service_scale=float(service_scale),
        q_star=int(q_star),
        seed=int(seed),
    )

    # Deterministic diagnostics on the declared band.
    eta_min = min(_eta(w, base) for w in omega_grid)
    mean_tau = float(sum(_tau_ws_trace(w, base) for w in omega_grid) / float(len(omega_grid)))

    return ScatStats(
        arrival_period=int(stats["arrival_period"]),
        service_scale=float(stats["service_scale"]),
        loss_amp=float(stats["loss_amp"]),
        eta_min=float(eta_min),
        mean_tau=float(mean_tau),
        frac_abs=float(stats["frac_abs"]),
        max_q=int(stats["max_q"]),
        frac_over_q=float(stats["frac_over_q"]),
        comp_ratio=float(_compress_ratio_ascii(record)),
    )


@dataclass(frozen=True)
class BHStats:
    m: int
    arrival_period: int
    absorb_batch: int
    leak_amp: float
    max_q: int
    frac_over_q: float
    frac_leak: float
    comp_ratio: float


def _rmse(xs: List[float]) -> float:
    ys = [float(x) for x in xs if math.isfinite(float(x))]
    if not ys:
        return float("nan")
    return float(math.sqrt(sum(y * y for y in ys) / float(len(ys))))


def _cap_select_bh_knobs(
    *,
    targets: List[Tuple[float, float, float, float]],  # per ap: (frac_over_q, comp_ratio, frac_abs, max_q)
    ticks: int,
    m: int,
    arrival_periods: List[int],
    q_star: int,
    seed: int,
    absorb_batch_family: List[int],
    leak_amp_family: List[float],
) -> Tuple[int, float, float, float]:
    """
    CAP-select BH knobs from explicit bounded families by matching the lossy-scattering audit targets.

    Objective (audit-level):
      minimize RMSE over the stacked diffs:
        (frac_over_q_BH - frac_over_q_SC_loss),
        (comp_ratio_BH - comp_ratio_SC_loss),
        (frac_leak_BH - frac_abs_SC_loss).
        (log(1+max_q_BH) - log(1+max_q_SC_loss)).

    Tie-break:
      - smaller absorb_batch
      - smaller leak_amp
    Returns (absorb_batch*, leak_amp*, rmse*, second_best_gap).
    """
    if len(arrival_periods) != len(targets):
        raise ValueError("arrival_periods/targets length mismatch")

    scored: List[Tuple[Tuple[float, int, float], int, float, float]] = []
    for ab in absorb_batch_family:
        if int(ab) <= 0:
            continue
        for la in leak_amp_family:
            if float(la) < 0.0:
                continue
            diffs: List[float] = []
            for ap, (t_over, t_comp, t_abs, t_mq) in zip(arrival_periods, targets):
                bh = _run_bh_queue(
                    ticks=int(ticks),
                    m=int(m),
                    arrival_period=int(ap),
                    absorb_batch=int(ab),
                    leak_amp=float(la),
                    q_star=int(q_star),
                    seed=int(seed),
                )
                diffs.append(float(bh.frac_over_q) - float(t_over))
                diffs.append(float(bh.comp_ratio) - float(t_comp))
                diffs.append(float(bh.frac_leak) - float(t_abs))
                # Only enforce max_q matching in the saturated regime (horizon-like phase).
                # In this toy, we treat the extreme-load case (arrival_period=1) as the saturated regime.
                # Otherwise, this term would dominate and incorrectly force near-threshold shapes to align.
                if int(ap) == 1:
                    diffs.append(float(math.log1p(float(bh.max_q))) - float(math.log1p(float(t_mq))))
            e = _rmse(diffs)
            key = (float(e), int(ab), float(la))
            scored.append((key, int(ab), float(la), float(e)))

    if not scored:
        raise RuntimeError("empty CAP family for BH knobs")
    scored.sort(key=lambda x: x[0])
    best = scored[0]
    second = scored[1] if len(scored) > 1 else None
    gap = float((second[3] - best[3]) if second is not None else float("nan"))
    return int(best[1]), float(best[2]), float(best[3]), float(gap)


def _run_bh_queue(
    *,
    ticks: int,
    m: int,
    arrival_period: int,
    absorb_batch: int,
    leak_amp: float,
    q_star: int,
    seed: int,
) -> BHStats:
    rng = _LCG(int(seed))
    q: List[int] = []  # microstates N
    out: List[str] = []  # stable-type record stream in X_m plus explicit leak token "X" (ASCII)

    ap = max(1, int(arrival_period))
    ab = max(1, int(absorb_batch))
    max_q = 0
    over_q = 0
    n_emit = 0
    n_leak = 0

    for t in range(int(ticks)):
        # periodic absorption (enqueue) on the same clock as scattering arrivals
        if t % ap == 0:
            # batch absorption makes backlog possible even when ap=1 (arrival rate > service rate)
            for _ in range(int(ab)):
                q.append(int(rng.randint(1 << int(m))))

        # one emission per tick if queue nonempty
        if q:
            N = int(q.pop(0))
            # Leak model (toy): per-emission loss probability leak_amp (interface knob),
            # aligned with the scattering-side absorption fraction.
            leak_p = float(max(0.0, min(1.0, float(leak_amp))))
            if rng.u01() < leak_p:
                out.append("X")
                n_leak += 1
            else:
                w = str(fold_m(int(N), int(m)))
                out.append(w)
            n_emit += 1

        max_q = max(max_q, len(q))
        if len(q) > int(q_star):
            over_q += 1

    frac_over_q = float(over_q / float(ticks)) if ticks > 0 else float("nan")
    frac_leak = float(n_leak / float(n_emit)) if n_emit > 0 else float("nan")
    comp_ratio = _compress_ratio_ascii("|".join(out))
    return BHStats(
        m=int(m),
        arrival_period=int(ap),
        absorb_batch=int(ab),
        leak_amp=float(leak_amp),
        max_q=int(max_q),
        frac_over_q=float(frac_over_q),
        frac_leak=float(frac_leak),
        comp_ratio=float(comp_ratio),
    )


def main() -> None:
    out_dir = generated_dir()
    rows_path = out_dir / "scattering_bh_queue_equivalence_rows.tex"
    sum_path = out_dir / "scattering_bh_queue_equivalence_summary.tex"

    ticks = 6000
    q_star = 50
    seed = 20260112
    omega_grid = [0.6 + 0.02 * i for i in range(81)]

    # Shared arrival periods to compare unsaturated vs saturated regimes.
    arrival_periods = [8, 4, 1]

    # Scattering model knobs (fixed service_scale; optional loss window).
    service_scale = 0.60
    loss_amp = 0.35

    # BH record uses stable types at the anchor scale m=6.
    # CAP-select (absorb_batch, leak_amp) from an explicit bounded family to match the lossy-scattering audit targets.
    m_bh = 6
    absorb_batch_family = [1, 2, 3, 4]
    # Include a small family around the scattering absorption fraction (~0.09 in this toy) to allow matching.
    leak_amp_family = [0.0, 0.05, 0.091, 0.10, 0.20, 0.35]

    rows: List[str] = []
    # First pass: compute lossy-scattering targets per arrival period.
    targets: List[Tuple[float, float, float, float]] = []
    for ap in arrival_periods:
        scat_l = _run_scattering_queue(
            ticks=ticks,
            omega_grid=omega_grid,
            arrival_period=int(ap),
            service_scale=float(service_scale),
            loss_amp=float(loss_amp),
            q_star=q_star,
            seed=seed,
        )
        targets.append((float(scat_l.frac_over_q), float(scat_l.comp_ratio), float(scat_l.frac_abs), float(scat_l.max_q)))

    absorb_batch, leak_amp, rmse_bh, gap_bh = _cap_select_bh_knobs(
        targets=targets,
        ticks=ticks,
        m=m_bh,
        arrival_periods=arrival_periods,
        q_star=q_star,
        seed=seed,
        absorb_batch_family=absorb_batch_family,
        leak_amp_family=leak_amp_family,
    )

    for ap in arrival_periods:
        scat_u = _run_scattering_queue(
            ticks=ticks,
            omega_grid=omega_grid,
            arrival_period=int(ap),
            service_scale=float(service_scale),
            loss_amp=0.0,
            q_star=q_star,
            seed=seed,
        )
        scat_l = _run_scattering_queue(
            ticks=ticks,
            omega_grid=omega_grid,
            arrival_period=int(ap),
            service_scale=float(service_scale),
            loss_amp=float(loss_amp),
            q_star=q_star,
            seed=seed,
        )
        bh = _run_bh_queue(
            ticks=ticks,
            m=m_bh,
            arrival_period=int(ap),
            absorb_batch=int(absorb_batch),
            leak_amp=float(leak_amp),
            q_star=q_star,
            seed=seed,
        )

        # Row: compare saturation and compressibility proxies across models.
        rows.append(
            " & ".join(
                [
                    str(int(ap)),
                    # scattering (unitary)
                    _fmt(scat_u.eta_min, 6),
                    _fmt(scat_u.mean_tau, 6),
                    str(int(scat_u.max_q)),
                    _fmt(scat_u.frac_over_q, 6),
                    _fmt(scat_u.comp_ratio, 6),
                    # scattering (lossy)
                    _fmt(scat_l.eta_min, 6),
                    _fmt(scat_l.frac_abs, 6),
                    str(int(scat_l.max_q)),
                    _fmt(scat_l.frac_over_q, 6),
                    _fmt(scat_l.comp_ratio, 6),
                    # BH queue
                    str(int(bh.max_q)),
                    _fmt(bh.frac_over_q, 6),
                    _fmt(bh.frac_leak, 6),
                    _fmt(bh.comp_ratio, 6),
                ]
            )
            + r" \\"
        )

    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])
    write_lines(
        sum_path,
        [
            r"\paragraph{Scattering vs black-hole queue equivalence (toy).} \AuditTag "
            + r"We compare (i) a delay-driven scattering queue (two-channel $S(\omega)$ proxy, with Wigner--Smith delay setting a tick-time service cost) "
            + r"to (ii) a black-hole-like internal queue emitting one stable-type record $w_t\in X_m$ per tick. "
            + r"The shared control parameter is the periodic arrival rate (one job per $p$ ticks). "
            + r"Trap-like saturation is audited by the fraction of ticks where the internal queue length exceeds a fixed threshold $q_\star$, "
            + r"and by the maximum observed queue length. "
            + r"External-record structure is summarized by a simple compressibility proxy (zlib compression ratio) on the emitted record stream.",
            r"\paragraph{Scope.} \AuditTag "
            + r"This is an interface-level comparison artifact (CS model). It does not assert a theorem-level equivalence between scattering and black-hole physics.",
            r"\paragraph{Determinism.} \AuditTag "
            + rf"Parameters are fixed (ticks={ticks}, q\_star={q_star}, m={m_bh}, grid={len(omega_grid)}). "
            + rf"BH knobs are CAP-selected from a bounded family (absorb\_batch in {absorb_batch_family}, leak\_amp in {leak_amp_family}) "
            + rf"to match the lossy-scattering audit targets across arrival periods (RMSE={rmse_bh:.6f}, gap={gap_bh:.6f}); "
            + rf"selected: absorb\_batch={absorb_batch}, leak\_amp={leak_amp:.3f}. "
            + r"Loss is reported via an S1-style $\eta_{\min}$ gate and an absorption fraction proxy in the lossy scattering case.",
        ],
    )


if __name__ == "__main__":
    main()

