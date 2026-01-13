# -*- coding: utf-8 -*-
"""
Toy scattering-process simulation as a discrete tick-time queue with Wigner--Smith delay.

Goal:
  Provide a fully deterministic, self-contained programmatic model that:
    - builds a unitary (or lossy) 2x2 scattering matrix S(omega),
    - computes a Wigner--Smith time-delay proxy tau_WS(omega),
    - simulates a tick-time "processing" queue whose service time scales with tau_WS,
    - emits an external record stream (A_out) and audit summaries.

This script is deliberately *not* a derivation of scattering from the folding core.
It is an auditable interface toy model that turns the paper's delay dictionary into
an explicit computational process.

Design goals:
  - Deterministic output (no timestamps).
  - English-only output.
  - Standard-library only.

Outputs (LaTeX fragments):
  - sections/generated/scattering_process_delay_queue_rows.tex
  - sections/generated/scattering_process_delay_queue_summary.tex
"""

from __future__ import annotations

import cmath
import math
import zlib
from dataclasses import dataclass
from typing import List, Tuple

from common_paths import generated_dir
from common_tex import write_lines
from protocol_kernel import fold_m


def _clamp01(x: float) -> float:
    return float(0.0 if x < 0.0 else (1.0 if x > 1.0 else x))


def _fmt(x: float, digits: int = 6) -> str:
    if not math.isfinite(x):
        return "nan"
    return f"{float(x):.{int(digits)}f}"


class _LCG:
    """
    Tiny deterministic RNG (LCG), sufficient for audit-only toy sampling.
    """

    def __init__(self, seed: int) -> None:
        self._s = int(seed) & 0xFFFFFFFFFFFFFFFF

    def u01(self) -> float:
        # 64-bit LCG parameters (Numerical Recipes-like; deterministic only)
        self._s = (6364136223846793005 * self._s + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        # Use high bits for better quality.
        return float((self._s >> 11) & ((1 << 53) - 1)) / float(1 << 53)


@dataclass(frozen=True)
class Resonance:
    omega0: float
    gamma: float


@dataclass(frozen=True)
class ScatteringModel:
    """
    Two-channel toy model: S(omega) = U diag(e^{2i delta1}, e^{2i delta2}) U^T,
    with a fixed mixing angle and optional multiplicative loss factor sqrt(eta(omega)).
    """

    mix_theta: float
    r1: Resonance
    r2: Resonance
    loss_amp: float
    loss_center: float
    loss_width: float


def _delta(omega: float, r: Resonance) -> float:
    # Smooth arctan phase shift in (0, pi): delta = atan2(gamma, omega0-omega).
    return float(math.atan2(float(r.gamma), float(r.omega0) - float(omega)))


def _ddelta_domega(omega: float, r: Resonance) -> float:
    # d/domega atan2(g, w0-w) = g / ((w-w0)^2 + g^2)
    dw = float(omega) - float(r.omega0)
    g = float(r.gamma)
    return float(g / (dw * dw + g * g))


def _eta(omega: float, m: ScatteringModel) -> float:
    # A bounded "loss window" (absorption) centered near loss_center.
    if m.loss_width <= 0:
        return 1.0
    z = (float(omega) - float(m.loss_center)) / float(m.loss_width)
    return _clamp01(1.0 - float(m.loss_amp) * math.exp(-z * z))


def _unitary_S(omega: float, m: ScatteringModel) -> List[List[complex]]:
    th = float(m.mix_theta)
    c = float(math.cos(th))
    s = float(math.sin(th))
    U = [[complex(c), complex(-s)], [complex(s), complex(c)]]
    d1 = _delta(omega, m.r1)
    d2 = _delta(omega, m.r2)
    e1 = cmath.exp(2.0j * complex(d1))
    e2 = cmath.exp(2.0j * complex(d2))

    # S = U diag(e1,e2) U^T (U is real orthogonal here).
    # Compute explicitly for stability and determinism.
    S00 = (c * c) * e1 + (s * s) * e2
    S11 = (s * s) * e1 + (c * c) * e2
    S01 = (c * s) * (e1 - e2)
    S10 = S01
    return [[S00, S01], [S10, S11]]


def _S_lossy(omega: float, m: ScatteringModel) -> List[List[complex]]:
    S = _unitary_S(omega, m)
    fac = math.sqrt(_eta(omega, m))
    return [[complex(fac) * S[0][0], complex(fac) * S[0][1]], [complex(fac) * S[1][0], complex(fac) * S[1][1]]]


def _probs_from_S(S: List[List[complex]]) -> List[List[float]]:
    p00 = float(abs(S[0][0]) ** 2)
    p01 = float(abs(S[0][1]) ** 2)
    p10 = float(abs(S[1][0]) ** 2)
    p11 = float(abs(S[1][1]) ** 2)
    return [[p00, p01], [p10, p11]]


def _tau_ws_trace(omega: float, m: ScatteringModel) -> float:
    # For constant mixing, Tr Q = 2*(d(delta1)/domega + d(delta2)/domega).
    return float(2.0 * (_ddelta_domega(omega, m.r1) + _ddelta_domega(omega, m.r2)))


@dataclass
class Job:
    omega: float
    omega_bin: int
    in_ch: int
    rem: int
    eta: float
    probs: List[List[float]]
    u_abs: float
    u_out: float


def _compress_ratio_ascii(s: str) -> float:
    b = s.encode("ascii", errors="ignore")
    if not b:
        return float("nan")
    c = zlib.compress(b, level=9)
    return float(len(c) / float(len(b)))


def _simulate_case(
    *,
    m: ScatteringModel,
    omega_grid: List[float],
    ticks: int,
    arrival_period: int,
    service_scale: float,
    q_star: int,
    seed: int,
) -> Tuple[dict, str]:
    rng = _LCG(int(seed))
    q: List[Job] = []

    # Unified record alphabet: stable-type words in X_6 (via Fold_6) plus an explicit loss token "X".
    # This avoids an arbitrary projection and makes the record token generation a protocol-kernel map.
    m_rec = 6
    modN = 1 << int(m_rec)

    out_records: List[str] = []
    max_q = 0
    over_q = 0
    n_emit = 0
    n_abs = 0
    tau_sum = 0.0
    eta_sum = 0.0
    s_sum = 0.0
    n_jobs = 0
    eta_min = 1.0

    ap = max(1, int(arrival_period))
    for t in range(int(ticks)):
        if t % ap == 0:
            omega_bin = int((t // ap) % len(omega_grid))
            omega = float(omega_grid[omega_bin])
            in_ch = int((t // ap) % 2)

            tau = _tau_ws_trace(omega, m)
            # Service time in ticks: at least 1 tick per job.
            s = max(1, int(math.ceil(float(service_scale) * float(tau))))

            eta_val = _eta(omega, m)
            eta_min = min(float(eta_min), float(eta_val))
            S = _S_lossy(omega, m)
            probs = _probs_from_S(S)

            q.append(
                Job(
                    omega=omega,
                    omega_bin=int(omega_bin),
                    in_ch=int(in_ch),
                    rem=int(s),
                    eta=float(eta_val),
                    probs=probs,
                    u_abs=rng.u01(),
                    u_out=rng.u01(),
                )
            )

        # Queue processing (single-server).
        if q:
            q[0].rem -= 1
            if q[0].rem <= 0:
                job = q.pop(0)
                n_jobs += 1
                tau_sum += float(_tau_ws_trace(job.omega, m))
                eta_sum += float(job.eta)
                s_sum += float(max(1, job.rem + 1))  # at completion rem is <=0; record nominal minimum

                absorbed = (job.u_abs >= job.eta)  # absorption probability = 1-eta
                if absorbed:
                    n_abs += 1
                    tok = "X"
                else:
                    # Outgoing channel sampling from row in_ch.
                    p0 = float(job.probs[job.in_ch][0])
                    out_ch = 0 if job.u_out < p0 else 1
                    # Deterministic folding into X_6:
                    #   N = (omega_bin * 4 + 2*in_ch + out_ch) mod 2^6, then tok = Fold_6(N).
                    N = (int(job.omega_bin) * 4 + int(job.in_ch) * 2 + int(out_ch)) % int(modN)
                    tok = str(fold_m(int(N), int(m_rec)))
                n_emit += 1
                # External record token (ASCII, stable for zlib metrics).
                out_records.append(str(tok))

        max_q = max(int(max_q), int(len(q)))
        if len(q) > int(q_star):
            over_q += 1

    mean_tau = float(tau_sum / n_jobs) if n_jobs > 0 else float("nan")
    mean_eta = float(eta_sum / n_jobs) if n_jobs > 0 else float("nan")
    frac_abs = float(n_abs / n_emit) if n_emit > 0 else float("nan")
    frac_over_q = float(over_q / float(ticks)) if ticks > 0 else float("nan")
    record_stream = "|".join(out_records)
    comp_ratio = _compress_ratio_ascii(record_stream)

    stats = {
        "ticks": int(ticks),
        "grid": int(len(omega_grid)),
        "arrival_period": int(ap),
        "service_scale": float(service_scale),
        "loss_amp": float(m.loss_amp),
        "eta_min": float(eta_min),
        "mean_tau": float(mean_tau),
        "mean_eta": float(mean_eta),
        "frac_abs": float(frac_abs),
        "max_q": int(max_q),
        "frac_over_q": float(frac_over_q),
        "comp_ratio": float(comp_ratio),
        "n_emit": int(n_emit),
    }
    return stats, record_stream


def main() -> None:
    out = generated_dir()
    rows_path = out / "scattering_process_delay_queue_rows.tex"
    sum_path = out / "scattering_process_delay_queue_summary.tex"

    # Fixed toy scattering model.
    model_base = ScatteringModel(
        mix_theta=0.37,
        r1=Resonance(omega0=1.0, gamma=0.08),
        r2=Resonance(omega0=1.7, gamma=0.12),
        loss_amp=0.0,
        loss_center=1.35,
        loss_width=0.22,
    )

    omega_grid = [0.6 + 0.02 * i for i in range(81)]  # deterministic grid
    ticks = 6000
    q_star = 50
    seed = 20260112

    cases = [
        ("A", 8, 0.60, 0.00),  # low load (scattering-like)
        ("B", 4, 0.40, 0.00),  # medium load (near-threshold but stable)
        ("C", 1, 0.60, 0.00),  # saturated / backlog regime (trap-like)
        ("D", 1, 0.60, 0.35),  # saturated + loss window (S1 gate triggers)
    ]

    rows: List[str] = []
    notes: List[str] = []
    for cid, arrival_period, service_scale, loss_amp in cases:
        m = ScatteringModel(
            mix_theta=model_base.mix_theta,
            r1=model_base.r1,
            r2=model_base.r2,
            loss_amp=float(loss_amp),
            loss_center=model_base.loss_center,
            loss_width=model_base.loss_width,
        )
        stats, _ = _simulate_case(
            m=m,
            omega_grid=omega_grid,
            ticks=int(ticks),
            arrival_period=int(arrival_period),
            service_scale=float(service_scale),
            q_star=int(q_star),
            seed=int(seed),
        )

        # S1-like diagnostic: eta_min near 1 means approximately unitary on the band.
        s1_flag = "ok" if stats["eta_min"] >= 0.999 else "loss"
        rows.append(
            " & ".join(
                [
                    str(cid),
                    str(int(arrival_period)),
                    _fmt(float(service_scale), 3),
                    _fmt(float(loss_amp), 3),
                    s1_flag,
                    _fmt(float(stats["eta_min"]), 6),
                    _fmt(float(stats["mean_tau"]), 6),
                    _fmt(float(stats["mean_eta"]), 6),
                    _fmt(float(stats["frac_abs"]), 6),
                    str(int(stats["max_q"])),
                    _fmt(float(stats["frac_over_q"]), 6),
                    _fmt(float(stats["comp_ratio"]), 6),
                ]
            )
            + r" \\"
        )

        notes.append(
            f"Case {cid}: arrival_period={arrival_period}, scale={service_scale:.3f}, loss_amp={loss_amp:.3f}, "
            f"eta_min={stats['eta_min']:.6f}, max_q={stats['max_q']}, "
            f"frac_over_q={stats['frac_over_q']:.6f}."
        )

    rows.append(r"\bottomrule")
    write_lines(rows_path, rows if rows else ["% (no rows)"])
    write_lines(
        sum_path,
        [
            r"\paragraph{Toy scattering-process simulation (delay$\rightarrow$queue).} \AuditTag "
            + r"We simulate a two-channel scattering proxy via a bounded-frequency $2\times 2$ matrix $S(\omega)$ and "
            + r"use the trace Wigner--Smith delay proxy $\tau_{\mathrm{WS}}(\omega)=\mathrm{Tr}\,Q(\omega)$ to set a discrete "
            + r"tick-time service cost for an internal single-server queue. "
            + r"The external record algebra is a single emitted stream in the stable alphabet $X_6$ "
            + r"(plus an explicit loss token \texttt{X} when a lossy window is enabled). "
            + r"Backlog/saturation is summarized by the maximum queue length and the fraction of ticks exceeding a fixed threshold $q_\star$; "
            + r"loss/approximate-unitarity is summarized by $\eta_{\min}$ on the declared band (S1-style gate).",
            r"\paragraph{Audit notes.} \AuditTag "
            + rf"Parameters are fixed and deterministic (ticks={ticks}, grid={len(omega_grid)}, q\_star={q_star}). "
            + r"The load is controlled by an explicit arrival period (one job every $p$ ticks). "
            + r"The purpose is to provide an explicit computational interpretation of the delay dictionary, "
            + r"not to claim a theorem-level scattering construction.",
            r"\paragraph{Run notes (deterministic).} \AuditTag " + " ".join(notes),
        ],
    )


if __name__ == "__main__":
    main()

