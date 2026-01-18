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
import json
import math
import zlib
from dataclasses import dataclass
from typing import List, Tuple

from common_paths import generated_dir, paper_root
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


def _read_scattering_phase_registry_gamma_target() -> Tuple[float, str, int, List[str]]:
    """
    Match-anchor for the scattering toy carrier:
    read the vendored registry and extract a benchmark resonance gamma (proxy units).
    We use the benchmark entry to avoid importing assumptions about physical unit conventions.
    """
    p = paper_root() / "data" / "k4_matching" / "scattering_phase_registry.json"
    reg = json.loads(p.read_text(encoding="utf-8"))
    excluded_units: List[str] = []
    excluded = 0
    for d in list(reg.get("datasets", [])):
        if str(d.get("id", "")).strip() == "breit_wigner_single_resonance_demo":
            res = list(d.get("resonances", []) or [])
            if not res:
                break
            g = float(res[0].get("gamma", float("nan")))
            if math.isfinite(g) and g > 0.0:
                # Count resonance-tagged datasets that are not in proxy_E units (not comparable without Match dictionary).
                for dd in list(reg.get("datasets", [])):
                    for rr in list(dd.get("resonances", []) or []):
                        u = str(rr.get("gamma_unit", "")).strip()
                        if u and u != "proxy_E":
                            excluded += 1
                            if u not in excluded_units:
                                excluded_units.append(u)
                return float(g), "breit_wigner_single_resonance_demo", int(excluded), excluded_units
    # Fallback: keep the script total-order deterministic even if registry changes.
    return 1.0, "fallback_gamma_1", int(excluded), excluded_units


def cap_select_scattering_carrier(
    *, loss_amp: float, omega_center: float
) -> Tuple[ScatteringModel, float, float, float, str]:
    """
    CAP-select a minimal scattering carrier from an explicit bounded family by matching the
    triangle-audit linewidth proxy convention tau_gamma ~ 4/gamma on the benchmark registry.

    Returns (model, gamma_ref, abslog, gap).
    """
    # Prefer a materialized carrier registry artifact (audit/match-layer input) if present.
    try:
        import json as _json
        from common_paths import paper_root as _paper_root
        regp = _paper_root() / "data" / "k4_matching" / "scattering_carrier_registry.json"
        if regp.is_file():
            reg = _json.loads(regp.read_text(encoding="utf-8"))
            c = dict(reg.get("carrier", {}) or {})
            sp = dict(c.get("selected_params", {}) or {})
            r1 = dict(sp.get("r1", {}) or {})
            r2 = dict(sp.get("r2", {}) or {})
            th = float(sp.get("mix_theta", 0.0))
            g1 = float(r1.get("gamma", 0.5))
            o2 = float(r2.get("omega0", omega_center + 10.0))
            g2 = float(r2.get("gamma", 10.0))
            m_reg = ScatteringModel(
                mix_theta=float(th),
                r1=Resonance(omega0=float(omega_center), gamma=float(g1)),
                r2=Resonance(omega0=float(o2), gamma=float(g2)),
                loss_amp=float(loss_amp),
                loss_center=float(omega_center),
                loss_width=0.22,
            )
            return m_reg, 1.0, 0.0, 0.0, "carrier_source=registry"
    except Exception:
        pass

    # Prefer M2 multi-dataset carrier selection if enabled (Match dictionary provides coverage).
    try:
        from exp_scattering_carrier_cap_select_multi_dataset import (  # type: ignore
            cap_select_scattering_carrier_m2,
        )
    except Exception:
        cap_select_scattering_carrier_m2 = None  # type: ignore

    if cap_select_scattering_carrier_m2 is not None:
        m2_model, m2_note = cap_select_scattering_carrier_m2()
        if m2_model is not None:
            # Override only the carrier shape; keep the requested loss window parameters.
            m2 = ScatteringModel(
                mix_theta=float(m2_model.mix_theta),
                r1=Resonance(omega0=float(omega_center), gamma=float(m2_model.r1.gamma)),
                r2=m2_model.r2,
                loss_amp=float(loss_amp),
                loss_center=float(omega_center),
                loss_width=0.22,
            )
            # Report placeholder diagnostics (not benchmark-abslog), since the carrier is already selected by M2.
            return m2, 1.0, 0.0, 0.0, f"{m2_note}; carrier_source=M2"

    gamma_ref, did_ref, excluded, excluded_units = _read_scattering_phase_registry_gamma_target()
    tau_target = 4.0 / float(gamma_ref)
    eps = 1e-12

    # Explicit bounded family (Iface/CAP knob set).
    mix_family = [0.0, 0.37, 0.79]
    # Interpret Resonance.gamma as the "g" in delta=atan2(g, w0-w), i.e. gamma_ref ≈ 2g for BW.
    g1_family = [0.5 * gamma_ref, 0.25 * gamma_ref, 0.125 * gamma_ref, 0.08]
    # Make the second resonance either far-away or very broad so it does not contaminate the benchmark.
    r2_family = [
        Resonance(omega0=float(omega_center + 10.0), gamma=10.0),
        Resonance(omega0=float(omega_center + 2.0), gamma=5.0),
    ]

    scored: List[Tuple[Tuple[float, float, float, float], ScatteringModel, float]] = []
    for th in mix_family:
        for g1 in g1_family:
            for r2 in r2_family:
                m = ScatteringModel(
                    mix_theta=float(th),
                    r1=Resonance(omega0=float(omega_center), gamma=float(g1)),
                    r2=r2,
                    loss_amp=float(loss_amp),
                    loss_center=float(omega_center),
                    loss_width=0.22,
                )
                tau = float(_tau_ws_trace(float(omega_center), m))
                abslog = abs(math.log((abs(tau) + eps) / (abs(tau_target) + eps)))
                # tie-breaks are encoded into the key in a deterministic order
                key = (float(abslog), float(th), float(g1), float(r2.gamma))
                scored.append((key, m, float(abslog)))

    scored.sort(key=lambda x: x[0])
    best_key, best_model, best_abslog = scored[0]
    second_abslog = float(scored[1][2]) if len(scored) > 1 else float("nan")
    gap = float(second_abslog - float(best_abslog)) if math.isfinite(second_abslog) else float("nan")
    scope = (
        f"carrier_source=M1; registry_anchor={did_ref}, gamma_unit=proxy_E; "
        f"excluded_resonance_entries={excluded}, excluded_gamma_units={excluded_units}"
    )
    return best_model, float(gamma_ref), float(best_abslog), float(gap), str(scope)


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

    omega_grid = [0.6 + 0.02 * i for i in range(81)]  # deterministic grid
    omega_center = 1.35
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
    carrier_notes: List[str] = []
    for cid, arrival_period, service_scale, loss_amp in cases:
        m, gamma_ref, abslog_ref, gap_ref, scope_ref = cap_select_scattering_carrier(
            loss_amp=float(loss_amp), omega_center=float(omega_center)
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
        carrier_notes.append(
            f"Case {cid}: carrier note: {scope_ref}; "
            f"omega0={omega_center:.2f}, gamma_ref={gamma_ref:.6f}, abslog={abslog_ref:.6f}, gap={gap_ref:.6f}."
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
            + r"The scattering carrier $S(\omega)$ is CAP-selected from an explicit bounded family. "
            + r"If the matching dictionary provides eligible cross-unit targets (M2), the carrier is selected by the multi-dataset CAP audit; "
            + r"otherwise it falls back to benchmark-only anchoring (M1). "
            + r"The purpose is to provide an explicit computational interpretation of the delay dictionary, "
            + r"not to claim a theorem-level scattering construction.",
            r"\paragraph{Run notes (deterministic).} \AuditTag " + " ".join(notes),
            r"\paragraph{Carrier selection notes (deterministic).} \AuditTag " + " ".join(carrier_notes),
        ],
    )


if __name__ == "__main__":
    main()

