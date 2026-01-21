# -*- coding: utf-8 -*-
"""
Full fusion experiment (audit-facing, deterministic):
  - Force generation: Phi=-gamma*c^2*(chi-chi0), F=-∇Phi=gamma*c^2∇chi
  - Propagation: damped telegraph/Klein–Gordon evolution for chi(x,t)
  - Relaxation: particle viscous damping -> convergence to a new periodic orbit
  - BH-like: budget-triggered chi-horizon + trapped subset + leakage/emit ledger
  - Wormhole-like: protocol pointer jumps (finite nonlocal couplings) with explicit cost ledger
  - Wave/particle + measurement: two-path interference readout with decoherence parameter
  - Scattering delay: one-channel Breit–Wigner delay benchmark (unitary reference)

Contract with the paper:
  - All of this is INTERFACE/AUDIT language: we do not claim microscopic derivations.
  - We enforce "no free energy" by explicit ledgers: E_tot = E_part + E_field + E_emit + E_wh_cost,
    where E_wh_cost is a bookkeeping cost for maintaining nonlocal pointer channels.
  - We keep the scattering benchmark unitary by construction and treat it as a readout dictionary.

Outputs (LaTeX fragments):
  - sections/generated/full_fusion_rows.tex
  - sections/generated/full_fusion_nowh_rows.tex
  - sections/generated/full_fusion_compare_rows.tex
  - sections/generated/full_fusion_summary.tex

Optional figure (requires matplotlib):
  - figures/full_fusion.png

Dependencies:
  - numpy (required)
  - matplotlib (optional)
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np

from common_paths import figures_dir, generated_dir
from common_tex import write_lines


def _fmt(x: float, nd: int = 6) -> str:
    return f"{float(x):.{int(nd)}f}"


def _ceil_div(a: int, b: int) -> int:
    if b <= 0:
        raise ValueError("b must be positive")
    return (a + b - 1) // b


def _roll_laplacian(u: np.ndarray, h: float) -> np.ndarray:
    inv_h2 = 1.0 / (h * h)
    return (
        np.roll(u, 1, axis=0)
        + np.roll(u, -1, axis=0)
        + np.roll(u, 1, axis=1)
        + np.roll(u, -1, axis=1)
        - 4.0 * u
    ) * inv_h2


def _roll_grad(u: np.ndarray, h: float) -> Tuple[np.ndarray, np.ndarray]:
    gx = (np.roll(u, -1, axis=1) - np.roll(u, 1, axis=1)) / (2.0 * h)
    gy = (np.roll(u, -1, axis=0) - np.roll(u, 1, axis=0)) / (2.0 * h)
    return gx, gy


def _bilinear_sample(u: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    side = int(u.shape[0])
    x0 = np.floor(x).astype(int) % side
    y0 = np.floor(y).astype(int) % side
    x1 = (x0 + 1) % side
    y1 = (y0 + 1) % side
    fx = x - np.floor(x)
    fy = y - np.floor(y)
    v00 = u[y0, x0]
    v10 = u[y0, x1]
    v01 = u[y1, x0]
    v11 = u[y1, x1]
    v0 = v00 * (1.0 - fx) + v10 * fx
    v1 = v01 * (1.0 - fx) + v11 * fx
    return v0 * (1.0 - fy) + v1 * fy


def _wrap_pos(p: np.ndarray, side: float) -> np.ndarray:
    return np.mod(p, side)


def _torus_delta(d: np.ndarray, side: float) -> np.ndarray:
    return d - side * np.round(d / side)


def _switch01(t: float, t0: float, w: float) -> float:
    return 0.5 * (1.0 + math.tanh((t - float(t0)) / float(w)))


def _breit_wigner_delay(omega: float, omega0: float, Gamma: float) -> float:
    return float(Gamma) / ((omega - omega0) ** 2 + (float(Gamma) / 2.0) ** 2)


def _autocorr_period_estimate(x: np.ndarray, dt: float, min_lag: int, max_lag: int) -> float:
    if x.size < max_lag + 2:
        return float("nan")
    x0 = x - float(np.mean(x))
    denom = float(np.dot(x0, x0))
    if denom <= 0.0:
        return float("nan")
    best = (0.0, -1)
    for lag in range(int(min_lag), int(max_lag) + 1):
        c = float(np.dot(x0[:-lag], x0[lag:])) / denom
        if c > best[0]:
            best = (c, lag)
    if best[1] < 0:
        return float("nan")
    return float(best[1]) * float(dt)


@dataclass(frozen=True)
class Row:
    t: float
    e_tot: float
    e_part: float
    e_field: float
    e_emit: float
    e_wh: float
    horizon_frac: float
    delay_free: float
    delay_trap: float
    delay_wh_free: float
    delay_wh_trap: float
    vis_free: float
    vis_trap: float
    dist_free: float
    dist_trap: float
    wh_jump_rate: float
    mean_r: float
    std_r: float


def main() -> None:
    mode = os.environ.get("FULL_FUSION_MODE", "").strip().lower()  # "" | "metrics"
    if mode not in ("", "metrics"):
        raise ValueError("FULL_FUSION_MODE must be '' or 'metrics'")
    tag = os.environ.get("FULL_FUSION_TAG", "").strip()
    if tag and any(c in tag for c in " /\\\t\n\r"):
        raise ValueError("FULL_FUSION_TAG must not contain whitespace or path separators")

    # -----------------------
    # Deterministic parameters (auditable).
    # -----------------------
    # Allow scanning some interface knobs via environment variables while keeping
    # the default manuscript instance unchanged.
    n = int(os.environ.get("FULL_FUSION_N", "6"))
    if n <= 0:
        raise ValueError("FULL_FUSION_N must be positive")
    side = int(2**n)
    h = 1.0
    dt = float(os.environ.get("FULL_FUSION_DT", "0.02"))
    steps = int(os.environ.get("FULL_FUSION_STEPS", "8000"))
    sample_every = int(os.environ.get("FULL_FUSION_SAMPLE_EVERY", "400"))
    if mode == "metrics":
        sample_every = max(1, steps)  # only final snapshot

    # Force dictionary.
    gamma = 1.0
    c2 = 1.0
    chi0 = 0.0
    kappa = 0.02

    # Field propagation (damped KG / telegraph).
    c_field = 6.0
    alpha = 0.9
    omega_relax = 2.0

    # Particles.
    n_particles = 18
    mass = 1.0
    eta = 0.35

    # Environment switch (new orbit center).
    center0 = (0.25 * side, 0.25 * side)
    center1 = (0.68 * side, 0.55 * side)
    t_switch = 40.0
    switch_width = 3.0

    # BH-like high-chi bump.
    bh_center = (0.52 * side, 0.78 * side)
    bh_amp = 2.5
    bh_sigma = 4.0

    # Protocol horizon budget (keep region small to compare free vs trapped).
    i_obs = int(os.environ.get("FULL_FUSION_I_OBS", "64"))
    margin_c = int(os.environ.get("FULL_FUSION_MARGIN_C", "16"))
    m_window = int(os.environ.get("FULL_FUSION_M_WINDOW", "6"))
    if i_obs <= 0 or margin_c <= 0 or m_window <= 0:
        raise ValueError("FULL_FUSION_I_OBS, FULL_FUSION_MARGIN_C, FULL_FUSION_M_WINDOW must be positive integers")

    # Leakage ledger (toy, but resource-accounted).
    leak_base = 0.08
    leak_delay_scale = 12.0
    rad_kick = 0.02

    # Wormhole-like pointer jumps (protocol shortcut) with explicit cost ledger.
    # Use a fixed finite family of pointer pairs on the screen.
    ptr_pairs: Sequence[Tuple[Tuple[int, int], Tuple[int, int]]] = [
        ((8, 8), (48, 40)),
        ((12, 50), (52, 12)),
        ((30, 10), (10, 30)),
    ]
    ptr_eps = float(os.environ.get("FULL_FUSION_PTR_EPS", "0.35"))  # coupling strength
    ptr_cost_lambda = 0.15  # cost coefficient for ledger
    ptr_radius = float(os.environ.get("FULL_FUSION_PTR_RADIUS", "3.5"))  # neighborhood size (cells)
    ptr_jump_rate0 = float(os.environ.get("FULL_FUSION_PTR_JUMP_RATE0", "0.22"))  # baseline hazard
    ptr_jump_cost_lambda = 0.9  # cost factor for pointer-jump events (energy-like)

    # Scattering-delay readout (unitary benchmark).
    omega_probe = 1.0
    Gamma0 = 1.0
    beta_shift = 0.8
    # Wormhole-induced extra scattering channel (interface-only):
    # an additional Breit–Wigner-like delay term activated near pointer endpoints.
    Gamma_wh = 0.8
    omega_wh0 = 0.7
    beta_wh = 0.35

    # Wave/particle readout: two-path interference + decoherence ("measurement strength").
    # decoh=0 -> full interference; decoh=1 -> full mixture.
    # Let decoh increase for trapped particles (record coupling stronger in traps).
    decoh_free = 0.15
    decoh_trap = 0.85
    path_offset = np.array([5.0, 0.0], dtype=float)  # second path samples chi at shifted position

    # Grid.
    xs = np.arange(side, dtype=float)
    ys = np.arange(side, dtype=float)
    xx, yy = np.meshgrid(xs, ys)

    def chi_eq_harmonic(center: Tuple[float, float]) -> np.ndarray:
        cx, cy = center
        dx = _torus_delta(xx - float(cx), float(side))
        dy = _torus_delta(yy - float(cy), float(side))
        r2 = dx * dx + dy * dy
        phi = 0.5 * float(kappa) * r2
        return float(chi0) - phi / (float(gamma) * float(c2))

    def chi_eq(t: float) -> np.ndarray:
        s = _switch01(t, t0=t_switch, w=switch_width)
        a = chi_eq_harmonic(center0)
        b = chi_eq_harmonic(center1)
        return (1.0 - s) * a + s * b

    def bh_bump() -> np.ndarray:
        cx, cy = bh_center
        dx = _torus_delta(xx - float(cx), float(side))
        dy = _torus_delta(yy - float(cy), float(side))
        r2 = dx * dx + dy * dy
        return float(bh_amp) * np.exp(-0.5 * r2 / (float(bh_sigma) ** 2))

    required_sites = _ceil_div(int(margin_c) * int(i_obs), int(m_window))
    required_sites_capped = min(required_sites, side * side)

    def horizon_region(chi_grid: np.ndarray) -> Tuple[np.ndarray, float, float]:
        flat = chi_grid.reshape(-1)
        idx = np.arange(flat.size, dtype=int)
        order = np.lexsort((idx, -flat))
        chosen = order[:required_sites_capped]
        mask = np.zeros_like(flat, dtype=bool)
        mask[chosen] = True
        chi_star = float(flat[chosen[-1]]) if chosen.size > 0 else float("inf")
        frac = float(chosen.size) / float(flat.size)
        return mask.reshape((side, side)), chi_star, frac

    # Pointer bookkeeping: map endpoints to their partner.
    endpoint_partner: Dict[Tuple[int, int], Tuple[int, int]] = {}
    endpoints: List[Tuple[int, int]] = []
    for (a, b) in ptr_pairs:
        aa = (int(a[0]) % side, int(a[1]) % side)
        bb = (int(b[0]) % side, int(b[1]) % side)
        endpoint_partner[aa] = bb
        endpoint_partner[bb] = aa
        endpoints.append(aa)
        endpoints.append(bb)

    def _near_any_endpoint(pos_xy: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns:
          - near: boolean mask for particles within ptr_radius of some endpoint (torus metric)
          - nearest_endpoint_idx: index into `endpoints` for the nearest endpoint (arbitrary for ties)
        """
        px = pos_xy[:, 0].reshape((-1, 1))
        py = pos_xy[:, 1].reshape((-1, 1))
        ex = np.array([e[0] for e in endpoints], dtype=float).reshape((1, -1))
        ey = np.array([e[1] for e in endpoints], dtype=float).reshape((1, -1))
        dx = _torus_delta(px - ex, float(side))
        dy = _torus_delta(py - ey, float(side))
        d2 = dx * dx + dy * dy
        j = np.argmin(d2, axis=1)
        dmin = np.sqrt(d2[np.arange(d2.shape[0]), j])
        return dmin <= float(ptr_radius), j

    def phi_from_chi(chi_grid: np.ndarray) -> np.ndarray:
        return -float(gamma) * float(c2) * (chi_grid - float(chi0))

    def field_energy(chi_grid: np.ndarray, pi_grid: np.ndarray, chi_eq_grid: np.ndarray) -> float:
        gx, gy = _roll_grad(chi_grid, h=h)
        dens = 0.5 * (
            pi_grid**2
            + (float(c_field) ** 2) * (gx**2 + gy**2)
            + (float(omega_relax) ** 2) * ((chi_grid - chi_eq_grid) ** 2)
        )
        return float(np.sum(dens) * (h * h))

    def particle_energy(pos_xy: np.ndarray, vel_xy: np.ndarray, phi_grid: np.ndarray) -> float:
        x = pos_xy[:, 0]
        y = pos_xy[:, 1]
        phi_s = _bilinear_sample(phi_grid, x=x, y=y)
        kin = 0.5 * float(mass) * float(np.sum(vel_xy[:, 0] ** 2 + vel_xy[:, 1] ** 2))
        pot = float(np.sum(phi_s))
        return float(kin + pot)

    def torus_r(pos_xy: np.ndarray, center: Tuple[float, float]) -> np.ndarray:
        d = pos_xy - np.array(center, dtype=float).reshape((1, 2))
        d[:, 0] = _torus_delta(d[:, 0], float(side))
        d[:, 1] = _torus_delta(d[:, 1], float(side))
        return np.sqrt(d[:, 0] ** 2 + d[:, 1] ** 2)
    def simulate(*, ptr_eps_value: float) -> Tuple[List[Row], float, np.ndarray]:
        # Initialize field (eq + BH bump) + deterministic impulse.
        chi = chi_eq(0.0) + bh_bump()
        pi = np.zeros_like(chi)
        impulse = np.zeros_like(chi)
        impulse[side // 3, side // 4] = 1.0
        pi += 0.6 * impulse

        # Initialize particles on a ring around center0.
        omega_orbit = math.sqrt(float(kappa) / float(mass))
        r0 = 0.18 * side
        angles = np.linspace(0.0, 2.0 * math.pi, n_particles, endpoint=False)
        pos = np.zeros((n_particles, 2), dtype=float)
        vel = np.zeros((n_particles, 2), dtype=float)
        cx0, cy0 = center0
        for i, th in enumerate(angles):
            pos[i, 0] = cx0 + r0 * math.cos(th)
            pos[i, 1] = cy0 + r0 * math.sin(th)
            v = omega_orbit * r0
            vel[i, 0] = -v * math.sin(th)
            vel[i, 1] = +v * math.cos(th)
        pos = _wrap_pos(pos, float(side))

        e_emit = 0.0
        e_wh = 0.0
        wh_jump_count = 0
        wh_jump_exposure = 0

        tail_start = int(0.5 * steps)
        tail_cos: List[float] = []
        rows: List[Row] = []

        for step in range(steps + 1):
            t = float(step) * float(dt)
            chi_eq_t = chi_eq(t) + bh_bump()

            hmask, _chi_star, hfrac = horizon_region(chi)
            ix = np.floor(pos[:, 0]).astype(int) % side
            iy = np.floor(pos[:, 1]).astype(int) % side
            in_trap = hmask[iy, ix]

            chi_p = _bilinear_sample(chi, x=pos[:, 0], y=pos[:, 1])
            omega0_eff = beta_shift * chi_p
            tau0 = np.array([_breit_wigner_delay(omega_probe, float(w0), Gamma0) for w0 in omega0_eff], dtype=float)

            # Wormhole-induced extra scattering channel: only active near endpoints.
            near_ep, near_idx = _near_any_endpoint(pos)
            tau_wh = np.zeros_like(tau0)
            if float(ptr_eps_value) != 0.0 and np.any(near_ep):
                # Use a second BW delay term with parameters modulated by local chi and coupling strength.
                # This is an interface dictionary: "shortcut channel adds an extra resonance-like phase contribution."
                w0_wh = float(omega_wh0) + float(beta_wh) * chi_p[near_ep]
                tau_wh_term = np.array(
                    [_breit_wigner_delay(omega_probe, float(w0), float(Gamma_wh)) for w0 in w0_wh], dtype=float
                )
                tau_wh[near_ep] = (float(ptr_eps_value) ** 2) * tau_wh_term

            tau = tau0 + tau_wh

            chi_p2 = _bilinear_sample(
                chi,
                x=_wrap_pos(pos + path_offset, float(side))[:, 0],
                y=_wrap_pos(pos + path_offset, float(side))[:, 1],
            )
            dphi = (chi_p - chi_p2)
            I_coh = 2.0 + 2.0 * np.cos(dphi)
            I_mix = 2.0 * np.ones_like(I_coh)
            decoh = np.where(in_trap, float(decoh_trap), float(decoh_free))
            _I = (1.0 - decoh) * I_coh + decoh * I_mix

            V = 1.0 - decoh
            D = np.sqrt(np.maximum(0.0, 1.0 - V * V))

            if step % sample_every == 0 or step == steps:
                phi = phi_from_chi(chi)
                ef = field_energy(chi, pi, chi_eq_t)
                ep = particle_energy(pos, vel, phi)
                rr = torus_r(pos, center=center1)
                free_tau = float(np.mean(tau[~in_trap])) if np.any(~in_trap) else 0.0
                trap_tau = float(np.mean(tau[in_trap])) if np.any(in_trap) else 0.0
                free_tau_wh = float(np.mean(tau_wh[~in_trap])) if np.any(~in_trap) else 0.0
                trap_tau_wh = float(np.mean(tau_wh[in_trap])) if np.any(in_trap) else 0.0
                free_V = float(np.mean(V[~in_trap])) if np.any(~in_trap) else 0.0
                trap_V = float(np.mean(V[in_trap])) if np.any(in_trap) else 0.0
                free_D = float(np.mean(D[~in_trap])) if np.any(~in_trap) else 0.0
                trap_D = float(np.mean(D[in_trap])) if np.any(in_trap) else 0.0
                wh_jump_rate = float(wh_jump_count) / (float(wh_jump_exposure) * float(dt) + 1e-12)
                rows.append(
                    Row(
                        t=t,
                        e_tot=float(ef + ep + e_emit + e_wh),
                        e_part=float(ep),
                        e_field=float(ef),
                        e_emit=float(e_emit),
                        e_wh=float(e_wh),
                        horizon_frac=float(hfrac),
                        delay_free=float(free_tau),
                        delay_trap=float(trap_tau),
                        delay_wh_free=float(free_tau_wh),
                        delay_wh_trap=float(trap_tau_wh),
                        vis_free=float(free_V),
                        vis_trap=float(trap_V),
                        dist_free=float(free_D),
                        dist_trap=float(trap_D),
                        wh_jump_rate=float(wh_jump_rate),
                        mean_r=float(np.mean(rr)),
                        std_r=float(np.std(rr)),
                    )
                )

            if step == steps:
                break

            if step >= tail_start:
                d0 = pos[0, :] - np.array(center1, dtype=float)
                dx0 = float(_torus_delta(np.array([d0[0]]), float(side))[0])
                dy0 = float(_torus_delta(np.array([d0[1]]), float(side))[0])
                theta = math.atan2(dy0, dx0)
                tail_cos.append(math.cos(theta))

            lap = _roll_laplacian(chi, h=h)
            accel = (float(c_field) ** 2) * lap - (float(omega_relax) ** 2) * (chi - chi_eq_t) - float(alpha) * pi
            pi = pi + float(dt) * accel
            chi = chi + float(dt) * pi

            if float(ptr_eps_value) != 0.0:
                for (a, b) in ptr_pairs:
                    ax, ay = int(a[0]) % side, int(a[1]) % side
                    bx, by = int(b[0]) % side, int(b[1]) % side
                    da = float(chi[ay, ax] - chi[by, bx])
                    e_wh += float(ptr_cost_lambda) * (float(ptr_eps_value) ** 2) * (da * da) * float(dt)
                    ca = float(chi[ay, ax])
                    cb = float(chi[by, bx])
                    chi[ay, ax] = (1.0 - float(ptr_eps_value)) * ca + float(ptr_eps_value) * cb
                    chi[by, bx] = (1.0 - float(ptr_eps_value)) * cb + float(ptr_eps_value) * ca
                    pa = float(pi[ay, ax])
                    pb = float(pi[by, bx])
                    pi[ay, ax] = (1.0 - float(ptr_eps_value)) * pa + float(ptr_eps_value) * pb
                    pi[by, bx] = (1.0 - float(ptr_eps_value)) * pb + float(ptr_eps_value) * pa

            gx, gy = _roll_grad(chi, h=h)
            fx = float(gamma) * float(c2) * _bilinear_sample(gx, x=pos[:, 0], y=pos[:, 1])
            fy = float(gamma) * float(c2) * _bilinear_sample(gy, x=pos[:, 0], y=pos[:, 1])

            # Wormhole-assisted leakage channel (protocol pointer-jump exit events).
            # This is an explicit exit-channel augmentation, not an energy source:
            # any jump across the readout geometry pays an energy-like cost ledger.
            if float(ptr_eps_value) != 0.0:
                eligible = in_trap & near_ep
                if np.any(eligible):
                    wh_jump_exposure += int(np.sum(eligible))
                    # Deterministic "coin flip" without RNG: uses a bounded sinusoid.
                    # u in [0,1), one value per particle.
                    ii = np.arange(n_particles, dtype=float)
                    u = 0.5 * (1.0 + np.sin(0.137 * float(step) + 0.731 * ii + 0.11 * float(ptr_eps_value)))
                    p = min(0.8, float(ptr_jump_rate0) * float(ptr_eps_value) ** 2 * float(dt))
                    do_jump = eligible & (u < p)
                    if np.any(do_jump):
                        # Jump to partner endpoint of nearest endpoint.
                        for idx_p in np.where(do_jump)[0]:
                            e = endpoints[int(near_idx[idx_p])]
                            partner = endpoint_partner[e]
                            # Energy-like cost: absolute potential gap across the jump.
                            phi_grid = phi_from_chi(chi)
                            phi_old = float(_bilinear_sample(phi_grid, x=np.array([pos[idx_p, 0]]), y=np.array([pos[idx_p, 1]]))[0])
                            phi_new = float(_bilinear_sample(phi_grid, x=np.array([partner[0]]), y=np.array([partner[1]]))[0])
                            e_wh += float(ptr_jump_cost_lambda) * abs(phi_new - phi_old)
                            # Apply pointer jump (position update); keep velocity (protocol shortcut).
                            pos[idx_p, 0] = float(partner[0])
                            pos[idx_p, 1] = float(partner[1])
                            wh_jump_count += 1
                        pos = _wrap_pos(pos, float(side))

            if np.any(in_trap):
                tau_trap = tau[in_trap]
                rate = float(leak_base) / (1.0 + float(np.mean(tau_trap)) / float(leak_delay_scale))
                kin_trap = 0.5 * float(mass) * float(np.sum(vel[in_trap, 0] ** 2 + vel[in_trap, 1] ** 2))
                dE = float(rate) * float(dt) * kin_trap
                e_emit += dE
                vel[in_trap, :] *= (1.0 - min(0.5, float(rate) * float(dt)))
                cx, cy = bh_center
                dx = _torus_delta(xx - float(cx), float(side))
                dy = _torus_delta(yy - float(cy), float(side))
                r2 = dx * dx + dy * dy
                pulse = float(rad_kick) * float(dE) * np.exp(-0.5 * r2 / (float(2.5) ** 2))
                pi += pulse

            ax = fx / float(mass) - float(eta) * vel[:, 0]
            ay = fy / float(mass) - float(eta) * vel[:, 1]
            vel[:, 0] = vel[:, 0] + float(dt) * ax
            vel[:, 1] = vel[:, 1] + float(dt) * ay
            pos[:, 0] = pos[:, 0] + float(dt) * vel[:, 0]
            pos[:, 1] = pos[:, 1] + float(dt) * vel[:, 1]
            pos = _wrap_pos(pos, float(side))

            vel[:, 0] += 1e-5 * math.sin(0.1 * t)
            vel[:, 1] += 1e-5 * math.cos(0.1 * t)

        tail_arr = np.array(tail_cos, dtype=float)
        T0 = 2.0 * math.pi / (math.sqrt(float(kappa) / float(mass)) + 1e-12)
        lag0 = int(max(20, round(T0 / float(dt))))
        max_lag = min(int(lag0 * 2), int(max(60, tail_arr.size - 10)))
        min_lag = max(10, int(lag0 // 3))
        T_est = _autocorr_period_estimate(tail_arr, dt=dt, min_lag=min_lag, max_lag=max_lag)
        return rows, float(T_est), chi

    rows, T_est, chi = simulate(ptr_eps_value=float(ptr_eps))
    rows_nowh, T_est_nowh, _chi_nowh = simulate(ptr_eps_value=0.0)

    if mode == "metrics":
        r_on = rows[-1]
        r_off = rows_nowh[-1]
        payload = {
            "t": r_on.t,
            "n": n,
            "m_window": m_window,
            "i_obs": i_obs,
            "margin_c": margin_c,
            "horizon_frac_on": r_on.horizon_frac,
            "horizon_frac_off": r_off.horizon_frac,
            "ptr_eps": ptr_eps,
            "ptr_radius": ptr_radius,
            "ptr_jump_rate0": ptr_jump_rate0,
            "E_emit_on": r_on.e_emit,
            "E_emit_off": r_off.e_emit,
            "E_wh_on": r_on.e_wh,
            "delay_free_on": r_on.delay_free,
            "delay_trap_on": r_on.delay_trap,
            "delay_wh_free_on": r_on.delay_wh_free,
            "delay_wh_trap_on": r_on.delay_wh_trap,
            "delay_free_off": r_off.delay_free,
            "delay_trap_off": r_off.delay_trap,
            "delay_wh_free_off": r_off.delay_wh_free,
            "delay_wh_trap_off": r_off.delay_wh_trap,
            "vis_free_on": r_on.vis_free,
            "vis_trap_on": r_on.vis_trap,
            "dist_free_on": r_on.dist_free,
            "dist_trap_on": r_on.dist_trap,
            "wh_jump_rate_on": r_on.wh_jump_rate,
            "T_est_on": T_est,
            "T_est_off": T_est_nowh,
        }
        print(json.dumps(payload, sort_keys=True))
        return

    # Output prefix (avoid overwriting the default artifacts when doing multiple full runs).
    prefix = "full_fusion" if not tag else f"full_fusion_{tag}"

    # Write rows (wormhole-on).
    out_lines: List[str] = []
    for r in rows:
        out_lines.append(
            " & ".join(
                [
                    _fmt(r.t, 2),
                    _fmt(r.e_tot, 6),
                    _fmt(r.e_part, 6),
                    _fmt(r.e_field, 6),
                    _fmt(r.e_emit, 6),
                    _fmt(r.e_wh, 6),
                    _fmt(r.horizon_frac, 6),
                    _fmt(r.delay_free, 6),
                    _fmt(r.delay_trap, 6),
                    _fmt(r.delay_wh_free, 6),
                    _fmt(r.delay_wh_trap, 6),
                    _fmt(r.vis_free, 6),
                    _fmt(r.vis_trap, 6),
                    _fmt(r.dist_free, 6),
                    _fmt(r.dist_trap, 6),
                    _fmt(r.wh_jump_rate, 6),
                    _fmt(r.mean_r, 4),
                    _fmt(r.std_r, 4),
                ]
            )
            + r" \\"
        )
    write_lines(generated_dir() / f"{prefix}_rows.tex", out_lines if out_lines else ["% (no rows)"])

    # Write rows (wormhole-off counterfactual).
    out_lines_nowh: List[str] = []
    for r in rows_nowh:
        out_lines_nowh.append(
            " & ".join(
                [
                    _fmt(r.t, 2),
                    _fmt(r.e_tot, 6),
                    _fmt(r.e_part, 6),
                    _fmt(r.e_field, 6),
                    _fmt(r.e_emit, 6),
                    _fmt(r.e_wh, 6),
                    _fmt(r.horizon_frac, 6),
                    _fmt(r.delay_free, 6),
                    _fmt(r.delay_trap, 6),
                    _fmt(r.delay_wh_free, 6),
                    _fmt(r.delay_wh_trap, 6),
                    _fmt(r.vis_free, 6),
                    _fmt(r.vis_trap, 6),
                    _fmt(r.dist_free, 6),
                    _fmt(r.dist_trap, 6),
                    _fmt(r.wh_jump_rate, 6),
                    _fmt(r.mean_r, 4),
                    _fmt(r.std_r, 4),
                ]
            )
            + r" \\"
        )
    write_lines(generated_dir() / f"{prefix}_nowh_rows.tex", out_lines_nowh if out_lines_nowh else ["% (no rows)"])

    # One-row compare (final snapshot).
    r_on = rows[-1]
    r_off = rows_nowh[-1]
    cmp = [
        " & ".join(
            [
                _fmt(r_on.t, 2),
                _fmt(r_on.e_emit, 6),
                _fmt(r_off.e_emit, 6),
                _fmt(r_on.e_wh, 6),
                _fmt(r_on.delay_free - r_off.delay_free, 6),
                _fmt(r_on.delay_trap - r_off.delay_trap, 6),
                _fmt(r_on.delay_wh_free - r_off.delay_wh_free, 6),
                _fmt(r_on.delay_wh_trap - r_off.delay_wh_trap, 6),
                _fmt(r_on.vis_free - r_off.vis_free, 6),
                _fmt(r_on.vis_trap - r_off.vis_trap, 6),
                _fmt(r_on.dist_free - r_off.dist_free, 6),
                _fmt(r_on.dist_trap - r_off.dist_trap, 6),
                _fmt(r_on.wh_jump_rate - r_off.wh_jump_rate, 6),
            ]
        )
        + r" \\"
    ]
    write_lines(generated_dir() / f"{prefix}_compare_rows.tex", cmp)

    # Summary.
    summary = [
        r"\paragraph{Audit summary (full fusion: BH-like horizon, wormhole-like shortcuts, and measurement).} \AuditTag "
        r"We combine: (i) force $F=-\nabla\Phi$ from $\Phi=-\gamma c^2(\chi-\chi_0)$, (ii) a propagating damped field "
        r"$\chi_{tt}+\alpha\chi_t=c_f^2\Delta\chi-\omega^2(\chi-\chi_{\mathrm{eq}}(t))$ with a smooth equilibrium shift, "
        r"(iii) a BH-like high-$\chi$ bump and a budget-triggered horizon proxy $m|\mathcal R_\star|\ge cI_{\mathrm{obs}}$, "
        r"(iv) leakage/evaporation bookkeeping that decreases trapped kinetic energy and accumulates $E_{\mathrm{emit}}(t)$, "
        r"(v) wormhole-like pointer-jump couplings as finite nonlocal mixings with an explicit cost ledger $E_{\mathrm{wh}}(t)$ "
        r"(no free energy), and (vi) wave/particle readout via a two-path interference model with a decoherence parameter "
        r"(free vs trapped) that suppresses interference visibility. "
        r"The tables report $E_{\mathrm{tot}}=E_{\mathrm{part}}+E_{\mathrm{field}}+E_{\mathrm{emit}}+E_{\mathrm{wh}}$, "
        r"horizon occupancy, mean delay proxies (free vs trapped), the wormhole-induced extra delay component "
        r"$\tau_{\mathrm{wh}}$ (reported separately), and an explicit pointer-jump exit-channel rate (wormhole-assisted leakage). "
        r"Measurement complementarity proxies "
        r"(visibility $V$ and distinguishability $D$) satisfy $V^2+D^2\le 1$ by construction. "
        r"A counterfactual run with wormhole coupling turned off ($\varepsilon_{\mathrm{ptr}}=0$) is reported to isolate "
        r"how pointer shortcuts redistribute delays/leakage under an explicit $E_{\mathrm{wh}}$ ledger. "
        r"A relaxation proxy (radius stats) is reported as the orbit family converges to a new periodic orbit. "
        rf"Late-time period estimate: $T_{{\mathrm{{est}}}}={_fmt(T_est,3)}$ (wormhole on), "
        rf"$T_{{\mathrm{{est,off}}}}={_fmt(T_est_nowh,3)}$ (wormhole off).",
    ]
    write_lines(generated_dir() / f"{prefix}_summary.tex", summary)

    # Optional figure.
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return

    fig = plt.figure(figsize=(12.5, 7.5))
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.imshow(chi, cmap="viridis", origin="lower")
    ax1.set_title("final chi(x) (BH bump + wormhole mixing)")
    ax1.set_xticks([])
    ax1.set_yticks([])

    ax2 = fig.add_subplot(2, 2, 2)
    tt = np.array([r.t for r in rows], dtype=float)
    ax2.plot(tt, [r.e_tot for r in rows], label="E_tot")
    ax2.plot(tt, [r.e_part for r in rows], label="E_part")
    ax2.plot(tt, [r.e_field for r in rows], label="E_field")
    ax2.plot(tt, [r.e_emit for r in rows], label="E_emit")
    ax2.plot(tt, [r.e_wh for r in rows], label="E_wh")
    ax2.set_title("energy ledgers")
    ax2.set_xlabel("t")
    ax2.grid(True, alpha=0.2)
    ax2.legend(fontsize=8, loc="best")

    ax3 = fig.add_subplot(2, 2, 3)
    ax3.plot(tt, [r.delay_free for r in rows], label="delay free")
    ax3.plot(tt, [r.delay_trap for r in rows], label="delay trapped")
    ax3.plot(tt, [r.vis_free for r in rows], "--", label="vis free")
    ax3.plot(tt, [r.vis_trap for r in rows], "--", label="vis trapped")
    ax3.plot(tt, [r.delay_wh_free for r in rows], ":", label="delay_wh free")
    ax3.plot(tt, [r.delay_wh_trap for r in rows], ":", label="delay_wh trapped")
    ax3.set_title("delay (incl. wormhole channel) + visibility")
    ax3.set_xlabel("t")
    ax3.grid(True, alpha=0.2)
    ax3.legend(fontsize=8, loc="best")

    ax4 = fig.add_subplot(2, 2, 4)
    ax4.plot(tt, [r.horizon_frac for r in rows], label="horizon fraction")
    ax4.set_title("budget-triggered horizon occupancy")
    ax4.set_xlabel("t")
    ax4.grid(True, alpha=0.2)
    ax4.legend(fontsize=8, loc="best")

    figures_dir().mkdir(parents=True, exist_ok=True)
    out_png = figures_dir() / f"{prefix}.png"
    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()

